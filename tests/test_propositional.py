import random
import unittest

from logos import (And, Bottom, FiniteModel, Iff, Implies, LogosError, Not, Or, Pred,
                   decide, is_countermodel, is_propositional, is_true, kalmar_sequent, parse,
                   truth_table)
from logos.proof import SearchConfig, prove, verify
from logos.propositional import atoms, valuations, value


def rand_prop(rng, depth, names="ABC"):
    if depth <= 0 or rng.random() < 0.25:
        return Bottom() if rng.random() < 0.05 else Pred(rng.choice(names))
    k = rng.choice(["not", "and", "or", "implies", "iff"])
    if k == "not":
        return Not(rand_prop(rng, depth - 1, names))
    cls = {"and": And, "or": Or, "implies": Implies, "iff": Iff}[k]
    return cls(rand_prop(rng, depth - 1, names), rand_prop(rng, depth - 1, names))


class TruthTables(unittest.TestCase):
    def test_classification(self):
        self.assertTrue(is_propositional(parse("A → (B ∨ ¬C) ∧ ⊥")))
        for text in ["P(x)", "∀x A", "a = b", "A ∧ ∃x B"]:
            self.assertFalse(is_propositional(parse(text)), text)
        self.assertRaises(LogosError, truth_table, parse("P(x)"))

    def test_known_tables(self):
        def col(text):
            return [val for _, val in truth_table(parse(text))]
        self.assertEqual(col("A ∧ B"), [False, False, False, True])
        self.assertEqual(col("A ∨ B"), [False, True, True, True])
        self.assertEqual(col("A → B"), [True, True, False, True])
        self.assertEqual(col("A ↔ B"), [True, False, False, True])
        self.assertEqual(col("¬A"), [True, False])
        self.assertEqual(col("A ∨ ¬A"), [True, True])
        self.assertEqual(col("A ∧ ¬A"), [False, False])
        self.assertEqual(col("⊥"), [False])

    def test_value_agrees_with_semantic_evaluator(self):
        rng = random.Random(8)
        for _ in range(300):
            f = rand_prop(rng, 4)
            for v in valuations(atoms(f)):
                model = FiniteModel([0], predicates={n: (0, [()] if b else []) for n, b in v.items()})
                self.assertEqual(value(f, v), is_true(model, f))


class Decide(unittest.TestCase):
    def d(self, prem, concl):
        return decide([parse(p, propositional=True) for p in prem], parse(concl, propositional=True))

    def test_class_exercises(self):
        cases = [(["p → q"], "¬q → ¬p"), (["p ∨ q", "p → r", "q → r"], "r"), (["p ∧ q"], "q ∧ p")]
        for prem, concl in cases:
            v = self.d(prem, concl)
            self.assertEqual((v.status, v.entails), ("proved", True), (prem, concl))
            verify(v.certificate)

    def test_countermodel_is_verified(self):
        v = self.d(["A → B"], "B → A")
        self.assertEqual((v.status, v.entails), ("counterexample", False))
        self.assertTrue(is_countermodel(v.countermodel, [parse("A → B")], parse("B → A")))
        self.assertTrue(is_true(v.countermodel, parse("¬A ∧ B")))

    def test_inconsistent_premises_are_detected_exactly(self):
        v = self.d(["A", "¬A"], "B")
        self.assertEqual((v.status, v.premises_satisfiable), ("proved", False))
        self.assertTrue(self.d(["A → B"], "B → A").premises_satisfiable)
        self.assertFalse(self.d(["⊥"], "A").premises_satisfiable)

    def test_not_propositional_and_limits(self):
        self.assertRaises(LogosError, self.d, ["∀x P(x)"], "A")
        big = [Pred(f"A{i}") for i in range(20)]
        v = decide([], Or(big[0], Not(big[0])), max_atoms=0)
        self.assertEqual((v.status, v.reason), ("unknown", "too_many_atoms"))


class SearchVersusSemantics(unittest.TestCase):
    """El oráculo exacto contra el buscador, sobre secuentes proposicionales aleatorios."""

    def test_search_is_complete_and_sound_on_propositional_sequents(self):
        rng = random.Random(2026)
        proved = refuted = 0
        for _ in range(600):
            prem = tuple(rand_prop(rng, 2) for _ in range(rng.randint(0, 2)))
            concl = rand_prop(rng, 3)
            v = decide(prem, concl, SearchConfig(max_depth=8, timeout=10))
            self.assertNotEqual(v.status, "unknown", (prem, concl))
            if v.status == "proved":
                proved += 1
                verify(v.certificate)
            else:
                refuted += 1
                self.assertEqual(prove(prem, concl, SearchConfig(max_depth=6, timeout=5)).status, "unknown")
        self.assertGreater(proved, 100)
        self.assertGreater(refuted, 100)

    def test_kalmar_lemma_through_the_prover(self):
        """Lema de Kalmár: literales de la valuación ⊢ φ (si vale) o ¬φ (si no)."""
        rng = random.Random(11)
        for _ in range(400):
            f = rand_prop(rng, 4)
            for v in rng.sample(list(valuations(atoms(f))) or [{}], k=min(2, 2 ** len(atoms(f)))):
                prem, goal = kalmar_sequent(f, v)
                r = prove(prem, goal, SearchConfig(max_depth=8, timeout=10))
                self.assertEqual(r.status, "proved", (f, v))
                verify(r.certificate)


if __name__ == "__main__":
    unittest.main()


class KalmarProver(unittest.TestCase):
    """Segundo camino: algoritmo de Kalmár, completo y determinista, contra el buscador."""

    def test_every_tautological_consequence_gets_a_checked_certificate(self):
        from logos.proof.kalmar import kalmar_prove
        rng = random.Random(404)
        proved = 0
        for _ in range(500):
            prem = tuple(rand_prop(rng, 2, "AB") for _ in range(rng.randint(0, 2)))
            concl = rand_prop(rng, 3, "AB")
            valid = all(value(concl, v) for v in valuations(atoms(concl) | set().union(*map(atoms, prem), set()))
                        if all(value(p, v) for p in prem))
            if not valid:
                with self.assertRaises(LogosError) as cm:
                    kalmar_prove(prem, concl)
                self.assertEqual(cm.exception.code, "not_a_consequence")
                continue
            cert = kalmar_prove(prem, concl)
            verify(cert)
            proved += 1
        self.assertGreater(proved, 150)

    def test_both_methods_agree_on_the_class_exercises(self):
        from logos.proof.kalmar import kalmar_prove
        cases = [(["p → q"], "¬q → ¬p"), (["p ∨ q", "p → r", "q → r"], "r"),
                 ([], "(p → q) ∨ (q → p)"), ([], "((p → q) → p) → p"), (["p ↔ ¬p"], "q"), ([], "¬(p ∨ q) ↔ ¬p ∧ ¬q")]
        for prem, concl in cases:
            ps = [parse(p, propositional=True) for p in prem]
            c = parse(concl, propositional=True)
            a = prove(tuple(ps), c, SearchConfig(max_depth=8))
            b = kalmar_prove(ps, c)
            self.assertEqual(a.status, "proved", (prem, concl))
            verify(a.certificate)
            verify(b)

    def test_found_search_gap_is_covered_by_kalmar(self):
        prem = [parse("C ↔ A")]
        concl = parse("(B ∨ A) ∧ A ∧ (¬B ↔ C ∨ B) ∨ (¬¬C ∨ ((B ↔ C) ∨ B))")
        v = decide(prem, concl, SearchConfig(max_depth=8, timeout=5))
        self.assertEqual(v.status, "proved")
        verify(v.certificate)

    def test_limits(self):
        from logos.proof.kalmar import kalmar_prove
        self.assertEqual(self._code(kalmar_prove, [], parse("∀x A")), "not_propositional")
        self.assertEqual(self._code(kalmar_prove, [], parse("A ∨ ¬A"), max_atoms=0), "too_many_atoms")

    @staticmethod
    def _code(fn, *a, **k):
        with unittest.TestCase().assertRaises(LogosError) as cm:
            fn(*a, **k)
        return cm.exception.code


if __name__ == "__main__":
    unittest.main()
