import unittest

from logos import parse
from logos.proof import (ProofCertificate, SearchConfig, find_inconsistency,
                         format_certificate, prove, prove_text, verify)
from proof_corpus import INVALID, VALID
from semantic_helpers import certificate_steps_sound, countermodel, small_models

CFG = SearchConfig(max_depth=7, timeout=20)


def label(prem, concl):
    return " , ".join(prem) + " ⊢ " + concl


class ValidSequents(unittest.TestCase):
    def test_every_valid_sequent_is_proved_and_certified(self):
        for prem, concl, consts in VALID:
            with self.subTest(sequent=label(prem, concl)):
                r = prove_text(prem, concl, consts, CFG)
                self.assertEqual(r.status, "proved", (r.reason, r.diagnostic))
                cert = r.certificate
                verify(cert)  # el checker lo acepta
                self.assertEqual(ProofCertificate.from_dict(cert.to_dict()).to_dict(), cert.to_dict())
                verify(ProofCertificate.from_dict(cert.to_dict()))
                ids = [(s.rule, s.formula, s.refs) for s in cert.steps]
                self.assertEqual(len(ids), len(set(ids)), "pasos duplicados")

    def test_every_step_of_every_proof_is_semantically_valid(self):
        """Corrección por fuerza bruta: ctx ⊨ fórmula en todos los modelos pequeños, para cada paso."""
        for prem, concl, consts in VALID:
            with self.subTest(sequent=label(prem, concl)):
                cert = prove_text(prem, concl, consts, CFG).certificate
                self.assertIsNone(certificate_steps_sound(cert, sizes=(1, 2), per_size=40))

    def test_conclusion_follows_in_small_models(self):
        for prem, concl, consts in VALID:
            with self.subTest(sequent=label(prem, concl)):
                ps = [parse(p, consts) for p in prem]
                c = parse(concl, consts)
                self.assertIsNone(countermodel(ps, c, small_models([*ps, c], (1, 2, 3), per_size=80)))


class InvalidSequents(unittest.TestCase):
    def test_invalid_are_never_proved_and_have_countermodels(self):
        cfg = SearchConfig(max_depth=6, timeout=10)
        for prem, concl, consts in INVALID:
            with self.subTest(sequent=label(prem, concl)):
                r = prove_text(prem, concl, consts, cfg)
                self.assertEqual(r.status, "unknown")
                self.assertIsNone(r.certificate)
                self.assertIn(r.reason, ("depth", "budget"))
                ps = [parse(p, consts) for p in prem]
                c = parse(concl, consts)
                cm = countermodel(ps, c, small_models([*ps, c], (1, 2, 3), per_size=400))
                self.assertIsNotNone(cm, "debería existir un contramodelo pequeño")

    def test_unknown_is_not_falsity(self):
        # Mismo estado `unknown` para algo válido que excede el presupuesto: no implica nada sobre su verdad.
        r = prove_text([], "∃x (D(x) → ∀y D(y))", config=SearchConfig(max_nodes=3))
        self.assertEqual((r.status, r.reason), ("unknown", "budget"))
        self.assertEqual(prove_text([], "∃x (D(x) → ∀y D(y))").status, "proved")


class Budgets(unittest.TestCase):
    def test_depth_limit(self):
        r = prove_text(["∀x P(x)"], "P(a)", ("a",), SearchConfig(max_depth=0))
        self.assertEqual((r.status, r.reason), ("unknown", "depth"))
        self.assertEqual(prove_text(["∀x P(x)"], "P(a)", ("a",), SearchConfig(max_depth=1)).status, "proved")

    def test_node_and_time_limits(self):
        hard = (["∀x ∃y R(x, y)"], "∃y ∀x R(x, y)")
        r = prove_text(*hard, config=SearchConfig(max_depth=7, max_nodes=50))
        self.assertEqual((r.status, r.reason), ("unknown", "budget"))
        r = prove_text(*hard, config=SearchConfig(max_depth=7, timeout=0.0))
        self.assertEqual((r.status, r.reason), ("unknown", "budget"))

    def test_deterministic(self):
        a = prove_text(*VALID[60][:2], config=CFG).certificate.to_dict()
        b = prove_text(*VALID[60][:2], config=CFG).certificate.to_dict()
        self.assertEqual(a, b)


class InputAndInconsistency(unittest.TestCase):
    def test_invalid_input(self):
        for prem, concl in [(["A ∧"], "A"), (["A"], "B ∨ (C"), ([], "∀x P(x) $")]:
            r = prove_text(prem, concl)
            self.assertEqual(r.status, "invalid_input")
            self.assertEqual(r.diagnostic["status"], "invalid_input")
            self.assertIsNotNone(r.diagnostic["span"])
        r = prove_text([], "∀a P(a)", constants=("a",))
        self.assertEqual((r.status, r.diagnostic["code"]), ("invalid_input", "quantified_constant"))

    def test_inconsistent_premises(self):
        cases = [(["A", "¬A"], ()), (["∀x P(x)", "∃x ¬P(x)"], ()), (["P(a)", "P(a) → Q(a)", "¬Q(a)"], ("a",)),
                 (["⊥"], ()), (["∀x ∃y R(x, y)", "¬∃y R(a, y)"], ("a",)),
                 (["a = b", "P(a)", "¬P(b)"], ("a", "b"))]
        for prem, consts in cases:
            with self.subTest(prem=prem):
                ps = [parse(p, consts) for p in prem]
                r = find_inconsistency(ps, CFG)
                self.assertEqual(r.status, "inconsistent")
                verify(r.certificate)
                self.assertEqual(r.certificate.conclusion, parse("⊥"))
                self.assertIsNone(countermodel(ps, parse("⊥"), small_models(ps + [parse("⊥")], (1, 2), per_size=60)))

    def test_consistent_premises_are_never_inconsistent(self):
        sets = [(["P(a)"], ("a",)), (["∀x P(x)", "∃x Q(x)"], ()), (["∀x ∃y R(x, y)"], ()),
                (["∃x P(x)", "∃x ¬P(x)"], ()), (["∀x (P(x) → Q(x))", "∃x P(x)", "∃x ¬Q(x)"], ())]
        for prem, consts in sets:
            with self.subTest(prem=prem):
                ps = [parse(p, consts) for p in prem]
                self.assertEqual(find_inconsistency(ps, SearchConfig(max_depth=5, timeout=10)).status, "unknown")

    def test_inconsistent_premises_prove_anything(self):
        r = prove_text(["A", "¬A"], "B")
        self.assertEqual(r.status, "proved")
        r = prove_text(["∀x P(x)", "∃x ¬P(x)"], "∀x ∀y x = y")
        self.assertEqual(r.status, "proved")


class Rendering(unittest.TestCase):
    def test_format_mentions_rules_and_steps(self):
        r = prove_text(["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", ("a",))
        text = format_certificate(r.certificate)
        for needle in ("Premisas:", "Conclusión: Q(a)", "∀E", "→E", "Hipótesis"):
            self.assertIn(needle, text)
        self.assertEqual(text.count("\n"), 2 + len(r.certificate.steps))


if __name__ == "__main__":
    unittest.main()
