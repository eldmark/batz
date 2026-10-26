import random
import unittest

from logos import (And, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred,
                   Var, alpha_equiv, parse, to_string)
from helpers import CONSTS, rand_formula

A, B, C = Pred("A"), Pred("B"), Pred("C")


class PrinterTests(unittest.TestCase):
    def test_canonical_text(self):
        cases = {
            "P(x)∧Q(x)": "P(x) ∧ Q(x)",
            "forall x (P(x)->Q(x))": "∀x (P(x) → Q(x))",
            "~~A": "¬¬A",
            "x != y": "x ≠ y",
            "((A))": "A",
            "(A ∧ B) ∧ C": "A ∧ B ∧ C",
            "A ∧ (B ∧ C)": "A ∧ (B ∧ C)",
            "(A → B) → C": "(A → B) → C",
            "A → (B → C)": "A → B → C",
            "A ∨ (B ∧ C)": "A ∨ B ∧ C",
            "(A ∨ B) ∧ C": "(A ∨ B) ∧ C",
            "∀x P(x) ∧ Q": "∀x P(x) ∧ Q",
            "∀x (P(x) ∧ Q)": "∀x (P(x) ∧ Q)",
            "¬(A ∧ B)": "¬(A ∧ B)",
        }
        for src, out in cases.items():
            with self.subTest(src=src):
                self.assertEqual(to_string(parse(src)), out)

    def test_ascii(self):
        f = parse("∀x ∃y (P(x) → ¬Q(y) ∧ x ≠ y) ↔ A ∨ B")
        self.assertEqual(to_string(f, ascii=True),
                         "forall x exists y (P(x) -> ~Q(y) & x != y) <-> A | B")
        self.assertEqual(parse(to_string(f, ascii=True)), f)

    def test_roundtrip_adversarial(self):
        for src in ["∀x P(x)", "∀x(P(x)→Q(x))", "∀x ∃y ∀x R(x, y)", "¬∀x ¬P(x)",
                    "∀x P(x) → Q(x)", "(A ↔ B) ↔ (C ↔ A)", "A → (B ↔ C)", "(A ↔ B) → C",
                    "¬(x = y) ∧ ¬x = y", "∀x ∀x P(x)", "A ∨ B ∨ (C ∨ A)"]:
            with self.subTest(src=src):
                f = parse(src)
                self.assertEqual(parse(to_string(f)), f)


class RoundTripProperty(unittest.TestCase):
    def test_roundtrip_is_structural_equality(self):
        rng = random.Random(2024)
        for i in range(2000):
            f = rand_formula(rng, rng.randint(0, 5))
            for ascii_ in (False, True):
                text = to_string(f, ascii=ascii_)
                g = parse(text, constants=CONSTS)
                self.assertEqual(g, f, text)
                self.assertTrue(alpha_equiv(g, f))
            # el texto canónico es un punto fijo
            self.assertEqual(to_string(parse(to_string(f), CONSTS)), to_string(f))


class ConstructorTests(unittest.TestCase):
    def test_invalid_nodes_rejected(self):
        bad = [lambda: Var("X"), lambda: Var(""), lambda: Var("forall"), lambda: Const("1a"),
               lambda: Func("f", ()), lambda: Func("f", (Pred("P"),)), lambda: Pred("p"),
               lambda: Pred("P", (A,)), lambda: Not(Var("x")), lambda: And(A, Var("x")),
               lambda: Forall("X", A), lambda: Forall("x", Var("x")), lambda: Eq(A, B)]
        for make in bad:
            with self.subTest(make=make):
                with self.assertRaises((ValueError, TypeError)):
                    make()

    def test_immutable_and_hashable(self):
        f = parse("∀x P(x)")
        with self.assertRaises(Exception):
            f.var = "y"
        self.assertEqual(len({f, parse("∀x P(x)"), parse("∀y P(y)")}), 2)

    def test_spans_do_not_affect_equality(self):
        self.assertEqual(parse("P(x)"), parse("  P( x )"))


if __name__ == "__main__":
    unittest.main()
