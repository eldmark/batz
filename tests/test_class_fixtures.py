"""Ejercicios reales de clase (ver docs/testing/ACCEPTANCE_FIXTURES.md)."""
import unittest

from batz import decide, kalmar_sequent, parse, to_string
from batz.proof import SearchConfig, format_certificate, prove_text, verify
from batz.proof.kalmar import kalmar_prove
from proof_corpus import CLASS_KALMAR, CLASS_SEQUENTS

CFG = SearchConfig(max_depth=8, timeout=10)


class ClassSequents(unittest.TestCase):
    def test_both_methods_prove_them(self):
        for name, prem, concl in CLASS_SEQUENTS:
            with self.subTest(name):
                r = prove_text(prem, concl, config=CFG, propositional=True)
                self.assertEqual(r.status, "proved")
                verify(r.certificate)
                ps = [parse(p, propositional=True) for p in prem]
                verify(kalmar_prove(ps, parse(concl, propositional=True)))
                v = decide(ps, parse(concl, propositional=True), CFG)
                self.assertEqual((v.status, v.entails), ("proved", True))


class ClassKalmar(unittest.TestCase):
    def test_kalmar_sequent_matches_the_class_convention(self):
        for name, formula, val, prem, goal in CLASS_KALMAR:
            with self.subTest(name):
                f = parse(formula, propositional=True)
                premises, meta = kalmar_sequent(f, {k.upper(): b for k, b in val.items()})
                self.assertEqual([to_string(p) for p in premises], [p.upper() for p in prem])
                self.assertEqual(to_string(meta), to_string(parse(goal, propositional=True)))

    def test_every_class_kalmar_exercise_is_provable_both_ways(self):
        for name, formula, val, prem, goal in CLASS_KALMAR:
            with self.subTest(name):
                r = prove_text(prem, goal, config=CFG, propositional=True)
                self.assertEqual(r.status, "proved")
                verify(r.certificate)
                ps = [parse(p, propositional=True) for p in prem]
                verify(kalmar_prove(ps, parse(goal, propositional=True)))

    def test_wrong_goal_is_not_provable_from_the_valuation(self):
        # Con p=V, q=F, la fórmula p→q es falsa: probar p→q desde p, ¬q es imposible.
        r = prove_text(["p", "¬q"], "p → q", config=CFG, propositional=True)
        self.assertEqual(r.status, "unknown")
        v = decide([parse("P"), parse("¬Q")], parse("P → Q"))
        self.assertEqual(v.status, "counterexample")

    def test_output_is_readable_for_narration(self):
        r = prove_text(["p ∨ q", "p → r", "q → r"], "r", config=CFG, propositional=True)
        text = format_certificate(r.certificate)
        self.assertIn("∨E", text)
        self.assertIn("Conclusión: R", text)


if __name__ == "__main__":
    unittest.main()
