"""Motor B (resolución): corrección frente a tres oráculos independientes."""
import random
import unittest

from batz import And, Implies, Not, Or, Iff, Pred, Bottom, parse
from batz.propositional import atoms, valuations, value
from batz.resolution import ResolutionConfig, contrast, resolve, resolve_text
from batz.resolution.clausify import Clausifier, clause_text
from batz.resolution.prover import normalize, unify
from helpers import close, rand_formula
from proof_corpus import INVALID, VALID
from semantic_helpers import countermodel, small_models

FAST = ResolutionConfig(timeout=3)


def rand_prop(rng, depth):
    if depth <= 0 or rng.random() < 0.25:
        return Bottom() if rng.random() < 0.06 else Pred(rng.choice("ABCD"))
    kind = rng.choice([Not, And, Or, Implies, Iff])
    if kind is Not:
        return Not(rand_prop(rng, depth - 1))
    return kind(rand_prop(rng, depth - 1), rand_prop(rng, depth - 1))


class Unification(unittest.TestCase):
    def test_mgu_and_occurs_check(self):
        self.assertEqual(unify("?x", ("a",), {}), {"?x": ("a",)})
        self.assertEqual(unify(("f", "?x"), ("f", ("a",)), {}), {"?x": ("a",)})
        self.assertIsNone(unify("?x", ("f", "?x"), {}))            # x no unifica con f(x)
        self.assertIsNone(unify(("f", "?x"), ("g", "?x"), {}))
        self.assertIsNone(unify(("a",), ("b",), {}))
        s = unify(("g", "?x", "?y"), ("g", "?y", ("a",)), {})
        self.assertIsNotNone(s)
        self.assertIsNone(unify(("g", "?x", "?x"), ("g", ("a",), ("b",)), {}))

    def test_variants_normalize_equal(self):
        a = frozenset([(True, "P", ("?k",)), (False, "Q", ("?k", "?m"))])
        b = frozenset([(False, "Q", ("?u", "?w")), (True, "P", ("?u",))])
        self.assertEqual(normalize(a), normalize(b))


class Clausification(unittest.TestCase):
    def texts(self, formula, constants=(), negate=False):
        return sorted(clause_text(c) for c in Clausifier().add(parse(formula, constants), negate))

    def test_shapes(self):
        self.assertEqual(self.texts("A → B"), ["B ∨ ¬A"])
        self.assertEqual(self.texts("A ∧ ¬A"), ["A", "¬A"])
        self.assertEqual(self.texts("A ∨ ¬A"), [])                 # tautología: se descarta
        self.assertEqual(self.texts("⊥"), ["□"])
        self.assertEqual(self.texts("¬⊥"), [])
        self.assertEqual(self.texts("∀x P(x)"), ["P(x1)"])
        self.assertEqual(self.texts("∃x P(x)"), ["P(sk1)"])
        self.assertEqual(self.texts("∀x ∃y R(x, y)"), ["R(x1, sk1(x1))"])   # Skolem depende de x
        self.assertEqual(self.texts("∃y ∀x R(x, y)"), ["R(x1, sk1)"])
        self.assertEqual(self.texts("∀x P(x)", negate=True), ["¬P(sk1)"])

    def test_free_variable_is_an_arbitrary_constant(self):
        self.assertEqual(self.texts("P(y)"), ["P(y)"])
        self.assertEqual(resolve_text(["P(y)"], "∀x P(x)").status, "saturated")
        self.assertEqual(resolve_text(["∀x P(x)"], "P(y)").status, "refuted")


class Corpus(unittest.TestCase):
    def test_every_valid_sequent_is_refuted(self):
        for premises, conclusion, constants in VALID:
            with self.subTest(sequent=(premises, conclusion)):
                self.assertEqual(resolve_text(premises, conclusion, constants, FAST).status, "refuted")

    def test_no_invalid_sequent_is_refuted(self):
        unknown = 0
        for premises, conclusion, constants in INVALID:
            with self.subTest(sequent=(premises, conclusion)):
                status = resolve_text(premises, conclusion, constants, ResolutionConfig(timeout=1)).status
                self.assertNotEqual(status, "refuted")
                unknown += status == "unknown"
        self.assertLessEqual(unknown, 2)  # solo los dos de igualdad, que no saturan

    def test_refutation_is_a_checkable_trace(self):
        r = resolve_text(["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", ("a",))
        self.assertEqual(r.steps[-1].clause, "□")
        for step in r.steps:
            self.assertTrue(all(parent < step.id for parent in step.parents))
            self.assertEqual(bool(step.parents), step.rule in ("resolve", "factor"))
        self.assertIn("negated_conclusion", {s.rule for s in r.steps})


class Oracles(unittest.TestCase):
    def test_propositional_agrees_with_truth_tables(self):
        """En lógica proposicional la resolución decide: refuta sii la tabla dice válido."""
        rng = random.Random(7)
        seen = {"refuted": 0, "saturated": 0}
        for _ in range(250):
            premises = [rand_prop(rng, 2) for _ in range(rng.randint(0, 2))]
            conclusion = rand_prop(rng, 3)
            names = set().union(*(atoms(f) for f in [*premises, conclusion]))
            valid = all(value(conclusion, v) for v in valuations(names) if all(value(p, v) for p in premises))
            status = resolve(premises, conclusion, FAST).status
            self.assertEqual(status, "refuted" if valid else "saturated", (premises, conclusion))
            seen[status] += 1
        self.assertGreater(min(seen.values()), 20)

    def test_first_order_refutations_have_no_small_countermodel(self):
        """Corrección: si B refuta, ningún modelo pequeño falsifica el secuente."""
        rng = random.Random(11)
        refuted = 0
        for _ in range(160):
            premises = [close(rand_formula(rng, 2)) for _ in range(rng.randint(0, 2))]
            conclusion = close(rand_formula(rng, 2))
            result = resolve(premises, conclusion, ResolutionConfig(timeout=0.5, max_clauses=1500))
            if result.status == "refuted":
                refuted += 1
                models = small_models([*premises, conclusion], sizes=(1, 2), per_size=40, seed=3)
                self.assertIsNone(countermodel(premises, conclusion, models), (premises, conclusion))
            elif result.status == "saturated":
                pass  # satisfacible con la negación: no hay nada que un modelo finito deba cumplir
        self.assertGreater(refuted, 15)


class ContrastMatrix(unittest.TestCase):
    def test_engines_agree_on_the_corpus(self):
        verdicts = {}
        for premises, conclusion, constants in VALID[:40] + INVALID[:12]:
            c = contrast([parse(p, constants) for p in premises], parse(conclusion, constants),
                         resolution_config=FAST)
            verdicts.setdefault(c.verdict, []).append((premises, conclusion))
        self.assertNotIn("soundness_alarm", verdicts)
        self.assertIn("consistent", verdicts)

    def test_contrast_reports_shape(self):
        d = contrast([parse("A → B"), parse("A")], parse("B")).to_dict()
        self.assertEqual(d["verdict"], "consistent")
        self.assertEqual(d["engine_b"]["status"], "refuted")
        self.assertEqual(d["engine_b"]["steps"][-1]["clause"], "□")


if __name__ == "__main__":
    unittest.main()
