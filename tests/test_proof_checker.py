import ast as pyast
import copy
import dataclasses
import pathlib
import random
import unittest

from batz import Var, parse, parse_term
from batz.proof import ProofCertificate, ProofError, ProofStep, is_valid, verify
from batz.proof.certificate import RULES
from proof_corpus import VALID
from semantic_helpers import certificate_steps_sound, countermodel, small_models


def cert(premises, conclusion, steps, consts=()):
    f = lambda t: parse(t, consts)
    out = []
    for i, (formula, ctx, rule, refs, params) in enumerate(steps, 1):
        ps = {}
        for k, v in params.items():
            ps[k] = v if k == "var" else parse_term(v, consts) if k == "term" else f(v)
        out.append(ProofStep(i, f(formula), tuple(f(c) for c in ctx), rule, tuple(refs), ps))
    return ProofCertificate(tuple(f(p) for p in premises), f(conclusion), tuple(out))


def code(c):
    with unittest.TestCase().assertRaises(ProofError) as cm:
        verify(c)
    return cm.exception.code


def A(f, ctx, rule="assume", refs=(), **params):
    return (f, ctx, rule, refs, params)


GOOD = {
    "and_comm": cert(["A ∧ B"], "B ∧ A", [
        A("A ∧ B", ["A ∧ B"]), A("B", ["A ∧ B"], "and_e2", [1]),
        A("A", ["A ∧ B"], "and_e1", [1]), A("B ∧ A", ["A ∧ B"], "and_i", [2, 3])]),
    "or_comm": cert(["A ∨ B"], "B ∨ A", [
        A("A ∨ B", ["A ∨ B"]), A("A", ["A"]), A("B ∨ A", ["A"], "or_i2", [2]),
        A("B", ["B"]), A("B ∨ A", ["B"], "or_i1", [4]),
        A("B ∨ A", ["A ∨ B"], "or_e", [1, 3, 5])]),
    "identity": cert([], "A → A", [A("A", ["A"]), A("A → A", [], "imp_i", [1])]),
    "vacuous_discharge": cert(["A"], "B → A", [A("A", ["A"]), A("B → A", ["A"], "imp_i", [1])]),
    "contraposition": cert(["A → B"], "¬B → ¬A", [
        A("A → B", ["A → B"]), A("A", ["A"]), A("B", ["A → B", "A"], "imp_e", [1, 2]),
        A("¬B", ["¬B"]), A("⊥", ["A → B", "A", "¬B"], "not_e", [3, 4]),
        A("¬A", ["A → B", "¬B"], "not_i", [5]), A("¬B → ¬A", ["A → B"], "imp_i", [6])]),
    "dne_raa": cert(["¬¬A"], "A", [
        A("¬¬A", ["¬¬A"]), A("¬A", ["¬A"]), A("⊥", ["¬A", "¬¬A"], "not_e", [2, 1]),
        A("A", ["¬¬A"], "raa", [3])]),
    "explosion": cert(["A", "¬A"], "B", [
        A("A", ["A"]), A("¬A", ["¬A"]), A("⊥", ["A", "¬A"], "not_e", [1, 2]),
        A("B", ["A", "¬A"], "bot_e", [3])]),
    "iff_swap": cert(["A ↔ B"], "B ↔ A", [
        A("A ↔ B", ["A ↔ B"]), A("A", ["A"]), A("B", ["A ↔ B", "A"], "iff_e1", [1, 2]),
        A("A → B", ["A ↔ B"], "imp_i", [3]), A("B", ["B"]), A("A", ["A ↔ B", "B"], "iff_e2", [1, 5]),
        A("B → A", ["A ↔ B"], "imp_i", [6]), A("B ↔ A", ["A ↔ B"], "iff_i", [7, 4])]),
    "forall_and": cert(["∀x (P(x) ∧ Q(x))"], "∀x P(x)", [
        A("∀x (P(x) ∧ Q(x))", ["∀x (P(x) ∧ Q(x))"]),
        A("P(y) ∧ Q(y)", ["∀x (P(x) ∧ Q(x))"], "all_e", [1], term="y"),
        A("P(y)", ["∀x (P(x) ∧ Q(x))"], "and_e1", [2]),
        A("∀x P(x)", ["∀x (P(x) ∧ Q(x))"], "all_i", [3], var="y")]),
    "exists_and": cert(["∃x (P(x) ∧ Q(x))"], "∃x P(x)", [
        A("∃x (P(x) ∧ Q(x))", ["∃x (P(x) ∧ Q(x))"]), A("P(y) ∧ Q(y)", ["P(y) ∧ Q(y)"]),
        A("P(y)", ["P(y) ∧ Q(y)"], "and_e1", [2]),
        A("∃x P(x)", ["P(y) ∧ Q(y)"], "ex_i", [3], term="y"),
        A("∃x P(x)", ["∃x (P(x) ∧ Q(x))"], "ex_e", [1, 4], var="y")]),
    "eq_sym": cert(["a = b"], "b = a", [
        A("a = b", ["a = b"]), A("a = a", [], "eq_i", [], term="a"),
        A("b = a", ["a = b"], "eq_e", [1, 2], var="x", template="x = a")], consts=("a", "b")),
    "alpha_renamed": cert(["∀x P(x)"], "∀y P(y)", [
        A("∀x P(x)", ["∀x P(x)"]), A("P(z)", ["∀x P(x)"], "all_e", [1], term="z"),
        A("∀y P(y)", ["∀x P(x)"], "all_i", [2], var="z")]),
}


class PositiveCertificates(unittest.TestCase):
    def test_hand_written_certificates_are_accepted(self):
        for name, c in GOOD.items():
            with self.subTest(name=name):
                verify(c)
                self.assertIsNone(certificate_steps_sound(c))

    def test_context_order_and_duplicates_are_irrelevant(self):
        c = GOOD["contraposition"]
        steps = list(c.steps)
        steps[4] = dataclasses.replace(steps[4], context=tuple(reversed(steps[4].context)) + steps[4].context)
        verify(dataclasses.replace(c, steps=tuple(steps)))

    def test_json_roundtrip(self):
        for name, c in GOOD.items():
            with self.subTest(name=name):
                d = c.to_dict()
                back = ProofCertificate.from_dict(d)
                verify(back)
                self.assertEqual(back.to_dict(), d)


class NegativeCertificates(unittest.TestCase):
    def test_structure(self):
        g = GOOD["identity"]
        self.assertEqual(code(dataclasses.replace(g, steps=())), "empty")
        s = list(g.steps)
        s[1] = dataclasses.replace(s[1], id=3)
        self.assertEqual(code(dataclasses.replace(g, steps=tuple(s))), "bad_ids")
        for bad in ([2], [5], [0], [-1], [True]):
            s = list(g.steps)
            s[1] = dataclasses.replace(s[1], refs=tuple(bad))
            self.assertEqual(code(dataclasses.replace(g, steps=tuple(s))), "bad_refs", bad)
        s = list(g.steps)
        s[1] = dataclasses.replace(s[1], rule="magic")
        self.assertEqual(code(dataclasses.replace(g, steps=tuple(s))), "unknown_rule")
        s = list(g.steps)
        s[0] = dataclasses.replace(s[0], refs=(1,))
        self.assertEqual(code(dataclasses.replace(g, steps=tuple(s))), "bad_refs")

    def test_wrong_shape_and_formula(self):
        self.assertEqual(code(cert(["A"], "A", [A("A", ["A"]), A("A", ["A"], "and_e1", [1])])), "wrong_shape")
        self.assertEqual(code(cert(["A ∧ B"], "A", [A("A ∧ B", ["A ∧ B"]), A("B", ["A ∧ B"], "and_e1", [1])])), "formula_mismatch")
        self.assertEqual(code(cert(["A → B", "B"], "A", [
            A("A → B", ["A → B"]), A("B", ["B"]), A("A", ["A → B", "B"], "imp_e", [1, 2])])), "formula_mismatch")
        self.assertEqual(code(cert(["A"], "B ∨ C", [A("A", ["A"]), A("B ∨ C", ["A"], "or_i1", [1])])), "formula_mismatch")

    def test_context_must_match_exactly(self):
        base = GOOD["and_comm"]
        for new_ctx in ([], ["A ∧ B", "C"]):
            s = list(base.steps)
            s[3] = dataclasses.replace(s[3], context=tuple(parse(c) for c in new_ctx))
            self.assertEqual(code(dataclasses.replace(base, steps=tuple(s))), "context_mismatch")

    def test_conclusion_and_open_assumptions(self):
        g = GOOD["identity"]
        self.assertEqual(code(dataclasses.replace(g, conclusion=parse("B → B"))), "wrong_conclusion")
        self.assertEqual(code(cert([], "A", [A("A", ["A"])])), "open_assumption")
        self.assertEqual(code(dataclasses.replace(GOOD["and_comm"], premises=())), "open_assumption")

    def test_spurious_params_are_rejected(self):
        g = GOOD["and_comm"]
        s = list(g.steps)
        s[3] = dataclasses.replace(s[3], params={"term": parse_term("y")})
        self.assertEqual(code(dataclasses.replace(g, steps=tuple(s))), "bad_params")
        h = GOOD["forall_and"]
        s = list(h.steps)
        s[3] = dataclasses.replace(s[3], params={"var": "y", "term": parse_term("y")})
        self.assertEqual(code(dataclasses.replace(h, steps=tuple(s))), "bad_params")

    def test_missing_and_bad_params(self):
        self.assertEqual(code(cert(["∀x P(x)"], "P(a)", [A("∀x P(x)", ["∀x P(x)"]),
                         A("P(a)", ["∀x P(x)"], "all_e", [1])], ("a",))), "bad_params")
        c = cert(["∀x P(x)"], "∀y P(y)", [A("∀x P(x)", ["∀x P(x)"]),
                 A("P(z)", ["∀x P(x)"], "all_e", [1], term="z"), A("∀y P(y)", ["∀x P(x)"], "all_i", [2], var="Z")])
        self.assertEqual(code(c), "bad_params")
        c = cert([], "t = t", [A("t = t", [], "eq_i", [], term="t")])
        s = (dataclasses.replace(c.steps[0], params={"term": "t"}),)  # str en vez de Term
        self.assertEqual(code(dataclasses.replace(c, steps=s)), "bad_params")

    def test_eigenvariable_forall_in_context(self):
        # P(y) ⊢ ∀x P(x) es inválido: y libre en una hipótesis abierta
        c = cert(["P(y)"], "∀x P(x)", [A("P(y)", ["P(y)"]), A("∀x P(x)", ["P(y)"], "all_i", [1], var="y")])
        self.assertEqual(code(c), "eigenvariable")

    def test_eigenvariable_forall_in_conclusion(self):
        c = cert(["∀z R(z, z)"], "∀x R(x, y)", [
            A("∀z R(z, z)", ["∀z R(z, z)"]), A("R(y, y)", ["∀z R(z, z)"], "all_e", [1], term="y"),
            A("∀x R(x, y)", ["∀z R(z, z)"], "all_i", [2], var="y")])
        self.assertEqual(code(c), "eigenvariable")
        self.assertIsNotNone(countermodel(list(c.premises), c.conclusion, small_models([*c.premises, c.conclusion], (2,))))

    def test_eigenvariable_exists_in_conclusion(self):
        c = cert(["∃x P(x)"], "P(y)", [A("∃x P(x)", ["∃x P(x)"]), A("P(y)", ["P(y)"]),
                 A("P(y)", ["∃x P(x)"], "ex_e", [1, 2], var="y")])
        self.assertEqual(code(c), "eigenvariable")

    def test_eigenvariable_exists_in_other_hypothesis(self):
        c = cert(["∃x P(x)", "Q(y)"], "∃x (P(x) ∧ Q(x))", [
            A("∃x P(x)", ["∃x P(x)"]), A("P(y)", ["P(y)"]), A("Q(y)", ["Q(y)"]),
            A("P(y) ∧ Q(y)", ["P(y)", "Q(y)"], "and_i", [2, 3]),
            A("∃x (P(x) ∧ Q(x))", ["P(y)", "Q(y)"], "ex_i", [4], term="y"),
            A("∃x (P(x) ∧ Q(x))", ["∃x P(x)", "Q(y)"], "ex_e", [1, 5], var="y")])
        self.assertEqual(code(c), "eigenvariable")

    def test_eigenvariable_exists_in_own_premise(self):
        c = cert(["∃x R(x, y)"], "∃z R(z, z)", [
            A("∃x R(x, y)", ["∃x R(x, y)"]), A("R(y, y)", ["R(y, y)"]),
            A("∃z R(z, z)", ["R(y, y)"], "ex_i", [2], term="y"),
            A("∃z R(z, z)", ["∃x R(x, y)"], "ex_e", [1, 3], var="y")])
        self.assertEqual(code(c), "eigenvariable")

    def test_capture_errors(self):
        # ∀E ingenuo capturaría y: ∀x∃y R(x,y) ⊬ ∃y R(y,y)
        c = cert(["∀x ∃y R(x, y)"], "∃y R(y, y)", [A("∀x ∃y R(x, y)", ["∀x ∃y R(x, y)"]),
                 A("∃y R(y, y)", ["∀x ∃y R(x, y)"], "all_e", [1], term="y")])
        self.assertEqual(code(c), "formula_mismatch")
        c = cert(["R(y, y)"], "∃x ∃y R(x, y)", [A("R(y, y)", ["R(y, y)"]),
                 A("∃x ∃y R(x, y)", ["R(y, y)"], "ex_i", [1], term="y")])
        self.assertEqual(code(c), "formula_mismatch")

    def test_wrong_witness_and_equality(self):
        c = cert(["P(a)"], "∃x P(x)", [A("P(a)", ["P(a)"]), A("∃x P(x)", ["P(a)"], "ex_i", [1], term="b")], ("a", "b"))
        self.assertEqual(code(c), "formula_mismatch")
        c = cert(["a = b"], "b = a", [A("a = b", ["a = b"]), A("a = a", [], "eq_i", [], term="b"),
                 A("b = a", ["a = b"], "eq_e", [1, 2], var="x", template="x = a")], ("a", "b"))
        self.assertEqual(code(c), "formula_mismatch")
        c = cert(["a = b"], "b = a", [A("a = b", ["a = b"]), A("a = a", [], "eq_i", [], term="a"),
                 A("b = a", ["a = b"], "eq_e", [1, 2], var="x", template="a = x")], ("a", "b"))
        self.assertEqual(code(c), "formula_mismatch")

    def test_discharge_misuse(self):
        # RAA descarga ¬A, no otra cosa: aquí el contexto declarado olvida descargar
        c = cert(["¬¬A"], "A", [A("¬¬A", ["¬¬A"]), A("¬A", ["¬A"]), A("⊥", ["¬A", "¬¬A"], "not_e", [2, 1]),
                 A("A", ["¬A", "¬¬A"], "raa", [3])])
        self.assertEqual(code(c), "context_mismatch")
        # reductio sin descargar: A ⊢ ⊥ no da ¬B
        c = cert(["A", "¬A"], "¬B", [A("A", ["A"]), A("¬A", ["¬A"]), A("⊥", ["A", "¬A"], "not_e", [1, 2]),
                 A("¬B", ["A", "¬A"], "not_i", [3])])
        verify(c)  # válido: descarga vacua de B (de ⊥ se sigue todo)
        self.assertIsNone(certificate_steps_sound(c))

    def test_from_dict_rejects_malformed(self):
        d = GOOD["identity"].to_dict()
        for mutate in (lambda x: x.pop("steps"), lambda x: x.update(schema_version="0"),
                       lambda x: x["steps"][0].update(formula="A ∧"),
                       lambda x: x["steps"][1].update(params={"zzz": "x"})):
            bad = copy.deepcopy(d)
            mutate(bad)
            with self.subTest():
                self.assertRaises(ProofError, ProofCertificate.from_dict, bad)


class IndependenceAndFuzz(unittest.TestCase):
    def test_checker_does_not_import_search(self):
        path = pathlib.Path(__file__).parent.parent / "src/batz/proof/checker.py"
        tree = pyast.parse(path.read_text(encoding="utf-8"))
        mods = set()
        for node in pyast.walk(tree):
            if isinstance(node, pyast.ImportFrom):
                mods.add((node.module or "") + "|" + ",".join(a.name for a in node.names))
            elif isinstance(node, pyast.Import):
                mods.update(a.name for a in node.names)
        self.assertFalse([m for m in mods if "search" in m or "semantics" in m or "model" in m], mods)

    def test_accepted_mutants_are_always_semantically_sound(self):
        """Si el checker acepta un certificado alterado, la conclusión debe seguirse de las premisas."""
        from batz.proof import prove_text
        rng = random.Random(1234)
        base = []
        for prem, concl, consts in VALID[::3]:
            r = prove_text(prem, concl, consts)
            self.assertEqual(r.status, "proved")
            base.append(r.certificate)
        accepted = rejected = 0
        for c in base:
            pool_f = [s.formula for s in c.steps] + list(c.premises)
            pool_t = [Var(v) for v in "xyzuw"]
            models = list(small_models([*c.premises, c.conclusion, *pool_f], (1, 2), per_size=40))
            for _ in range(60):
                steps = list(c.steps)
                i = rng.randrange(len(steps))
                s = steps[i]
                kind = rng.choice(["rule", "ref", "formula", "param", "ctx_drop", "ctx_add", "premise", "conclusion"])
                prem, concl = c.premises, c.conclusion
                if kind == "rule":
                    s = dataclasses.replace(s, rule=rng.choice(RULES))
                elif kind == "ref" and s.refs:
                    refs = list(s.refs)
                    refs[rng.randrange(len(refs))] = rng.randint(1, max(1, s.id - 1))
                    s = dataclasses.replace(s, refs=tuple(refs))
                elif kind == "formula":
                    s = dataclasses.replace(s, formula=rng.choice(pool_f))
                elif kind == "param":
                    params = dict(s.params) or {"var": "y"}
                    k = rng.choice(list(params))
                    params[k] = (rng.choice("xyzuw") if k == "var" else rng.choice(pool_t) if k == "term"
                                 else rng.choice(pool_f))
                    s = dataclasses.replace(s, params=params)
                elif kind == "ctx_drop" and s.context:
                    ctx = list(s.context)
                    ctx.pop(rng.randrange(len(ctx)))
                    s = dataclasses.replace(s, context=tuple(ctx))
                elif kind == "ctx_add":
                    s = dataclasses.replace(s, context=s.context + (rng.choice(pool_f),))
                elif kind == "premise" and prem:
                    prem = prem[:-1]
                elif kind == "conclusion":
                    concl = rng.choice(pool_f)
                steps[i] = s
                mutant = ProofCertificate(prem, concl, tuple(steps))
                if mutant == c:
                    continue  # mutación nula: no cuenta
                try:
                    verify(mutant)
                except ProofError:
                    rejected += 1
                    continue
                accepted += 1
                self.assertIsNone(countermodel(list(mutant.premises), mutant.conclusion, models), kind)
                self.assertIsNone(certificate_steps_sound(mutant, sizes=(1, 2), per_size=20), kind)
        self.assertGreater(rejected, 10 * accepted)  # el fuzz de verdad rompe cosas
        self.assertGreater(rejected, 1000)


if __name__ == "__main__":
    unittest.main()
