import dataclasses
import random
import unittest

from batz import FiniteModel, BatzError, evaluate, explain, holds, parse
from helpers import close, rand_formula, rand_model


MODEL = FiniteModel(
    [0, 1], constants={"a": 0},
    functions={"f": (1, {(0,): 1, (1,): 0})},
    predicates={"P": (1, [(0,)]), "Q": (1, [])},
)


class ExplainTests(unittest.TestCase):
    def explain_text(self, text, env=None):
        return explain(MODEL, evaluate(MODEL, parse(text, {"a"}), env))

    def test_quantifier_templates(self):
        for text, marker, count in [
            ("∃x P(x)", "Testigo", 1),
            ("∀x P(x)", "Contraejemplo", 1),
            ("∀x (P(x) ∨ ¬P(x))", "Se revisaron los 2", 2),
            ("∃x Q(x)", "Se revisaron los 2", 2),
        ]:
            with self.subTest(text=text):
                e = self.explain_text(text)
                self.assertIn(marker, e.summary)
                self.assertEqual(len(e.children), count)
                if count == 2:
                    self.assertEqual(len(e.details), 2)

    def test_connective_templates(self):
        cases = [
            ("P(a) ∧ Q(a)", False, 1), ("P(a) ∧ P(a)", True, 2),
            ("P(a) ∨ Q(a)", True, 1), ("Q(a) ∨ Q(a)", False, 2),
            ("P(a) → Q(a)", False, 2), ("Q(a) → P(a)", True, 1),
            ("P(a) → P(a)", True, 1), ("P(a) ↔ P(a)", True, 2),
            ("P(a) ↔ Q(a)", False, 2), ("¬P(a)", False, 1),
            ("⊥", False, 0),
        ]
        for text, value, children in cases:
            with self.subTest(text=text):
                e = self.explain_text(text)
                self.assertIs(e.value, value)
                self.assertEqual(len(e.children), children)
                self.assertEqual(e.to_dict()["value"], value)
                self.assertEqual(e.span, (0, len(text)))

    def test_atoms_and_intermediate_terms(self):
        e = self.explain_text("P(f(a))")
        self.assertFalse(e.value)
        self.assertIn("(1) no pertenece", e.summary)
        self.assertIn("f(a) = 1", e.details)
        eq = self.explain_text("f(f(a)) = a")
        self.assertTrue(eq.value)
        self.assertEqual(eq.details, ("f(a) = 1", "f(f(a)) = 0"))

    def test_open_formula_and_tamper_rejection(self):
        e = self.explain_text("P(x)", {"x": 0})
        self.assertTrue(e.value)
        trace = evaluate(MODEL, parse("P(a)", {"a"}))
        with self.assertRaises(BatzError) as cm:
            explain(MODEL, dataclasses.replace(trace, value=False))
        self.assertEqual(cm.exception.code, "invalid_trace")

    def test_explanation_agrees_with_semantics_on_generated_formulas(self):
        rng = random.Random(211)
        for _ in range(200):
            formula = close(rand_formula(rng, rng.randint(0, 4)))
            model = rand_model(rng)
            explanation = explain(model, evaluate(model, formula))
            self.assertIs(explanation.value, holds(model, formula))


if __name__ == "__main__":
    unittest.main()
