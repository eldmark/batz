import unittest

from logos import (And, Const, Eq, Exists, Forall, Func, Iff, Implies, LogosError,
                   Not, Or, Pred, Var, parse, parse_term)
from logos.lexer import tokenize


def err(text, **kw):
    with unittest.TestCase().assertRaises(LogosError) as cm:
        parse(text, **kw)
    return cm.exception


class LexerTests(unittest.TestCase):
    def test_offsets(self):
        toks = tokenize("P(x) ∧ Q")
        self.assertEqual([(t.text, t.span.start, t.span.end) for t in toks[:-1]],
                         [("P", 0, 1), ("(", 1, 2), ("x", 2, 3), (")", 3, 4), ("∧", 5, 6), ("Q", 7, 8)])

    def test_ascii_equivalents(self):
        self.assertEqual(parse("forall x (P(x) -> ~Q(x) & R(x,x) | S)"),
                         parse("∀x (P(x) → ¬Q(x) ∧ R(x,x) ∨ S)"))
        self.assertEqual(parse("A /\\ B \\/ C <-> !D"), parse("A ∧ B ∨ C ↔ ¬D"))

    def test_neq(self):
        self.assertEqual(parse("x != y"), Not(Eq(Var("x"), Var("y"))))
        self.assertEqual(parse("x ≠ y"), parse("x != y"))

    def test_unexpected_char(self):
        e = err("P(x) $ Q")
        self.assertEqual((e.stage, e.code, e.span.start), ("lexical", "unexpected_char", 5))

    def test_digit_start_and_caseless(self):
        self.assertEqual(err("P(1)").code, "unexpected_char")
        self.assertEqual(err("P(日本)").code, "caseless_identifier")

    def test_reserved_words(self):
        e = err("forall")
        self.assertEqual(e.stage, "syntactic")
        self.assertEqual(parse("forallx = forallx"), Eq(Var("forallx"), Var("forallx")))


class ParserTests(unittest.TestCase):
    P, Q = Pred("P"), Pred("Q")

    def test_basic_atoms(self):
        self.assertEqual(parse("P"), Pred("P"))
        self.assertEqual(parse("P(x)"), Pred("P", (Var("x"),)))
        self.assertEqual(parse("R(f(x), g(a, y))", constants={"a"}),
                         Pred("R", (Func("f", (Var("x"),)), Func("g", (Const("a"), Var("y"))))))
        self.assertEqual(parse("x = f(y)"), Eq(Var("x"), Func("f", (Var("y"),))))

    def test_precedence_and_over_or_over_implies(self):
        A, B, C, D = (Pred(n) for n in "ABCD")
        self.assertEqual(parse("A ∨ B ∧ C"), Or(A, And(B, C)))
        self.assertEqual(parse("A ∧ B ∨ C"), Or(And(A, B), C))
        self.assertEqual(parse("A ∨ B → C"), Implies(Or(A, B), C))
        self.assertEqual(parse("A → B ↔ C → D"), Iff(Implies(A, B), Implies(C, D)))
        self.assertEqual(parse("¬A ∧ B"), And(Not(A), B))

    def test_associativity(self):
        A, B, C = (Pred(n) for n in "ABC")
        self.assertEqual(parse("A → B → C"), Implies(A, Implies(B, C)))
        self.assertEqual(parse("A ∧ B ∧ C"), And(And(A, B), C))
        self.assertEqual(parse("A ∨ B ∨ C"), Or(Or(A, B), C))
        self.assertEqual(err("A ↔ B ↔ C").code, "non_associative")
        self.assertEqual(parse("(A ↔ B) ↔ C"), Iff(Iff(A, B), C))

    def test_quantifier_binds_tight(self):  # [D-1]
        f = parse("∀x P(x) → Q(x)")
        px, qx = Pred("P", (Var("x"),)), Pred("Q", (Var("x"),))
        self.assertEqual(f, Implies(Forall("x", px), qx))
        self.assertEqual(parse("∀x (P(x) → Q(x))"), Forall("x", Implies(px, qx)))

    def test_adversarial_quantifiers(self):
        self.assertEqual(parse("∀x P(x)"), Forall("x", Pred("P", (Var("x"),))))
        f = parse("∀x ∃y R(x, y)")
        self.assertEqual(f, Forall("x", Exists("y", Pred("R", (Var("x"), Var("y"))))))
        self.assertEqual(parse("¬∀x P(x)"), Not(Forall("x", Pred("P", (Var("x"),)))))

    def test_shadowing(self):
        f = parse("∀x (P(x) ∧ ∃x Q(x))")
        px, qx = Pred("P", (Var("x"),)), Pred("Q", (Var("x"),))
        self.assertEqual(f, Forall("x", And(px, Exists("x", qx))))

    def test_constants_and_free_vars(self):
        self.assertEqual(parse("P(a)", constants={"a"}), Pred("P", (Const("a"),)))
        self.assertEqual(parse("P(a)"), Pred("P", (Var("a"),)))
        e = err("∀a P(a)", constants={"a"})
        self.assertEqual((e.stage, e.code), ("semantic", "quantified_constant"))

    def test_bound_name_scope_ends(self):
        f = parse("(∀x P(x)) ∧ P(x) ∧ Q(a)", constants={"a"})
        self.assertEqual(f.left.right, Pred("P", (Var("x"),)))

    def test_parse_term(self):
        self.assertEqual(parse_term("f(x, a)", constants={"a"}), Func("f", (Var("x"), Const("a"))))
        self.assertRaises(LogosError, parse_term, "f(x) y")

    def test_spans(self):
        f = parse("P(x) ∧ (Q ∨ R)")
        self.assertEqual((f.span.start, f.span.end), (0, 14))
        self.assertEqual((f.left.span.start, f.left.span.end), (0, 4))

    def test_errors_are_localized(self):
        cases = {
            "(P ∧ Q": ("unclosed_paren", 0),
            "P ∧ Q)": ("unmatched_paren", 5),
            "P ∧": ("expected_formula", 3),
            "∧ P": ("expected_formula", 0),
            "P → → Q": ("expected_formula", 4),
            "∀ P(x)": ("expected_variable", 2),
            "∀x": ("expected_formula", 2),
            "P(x,)": ("expected_term", 4),
            "P()": ("expected_term", 2),
            "P(x y)": ("unexpected_token", 4),
            "P Q": ("unexpected_token", 2),
            "x": ("expected_formula", 1),
            "P(X)": ("expected_term", 2),
            "x = P": ("expected_term", 4),
            "": ("expected_formula", 0),
        }
        for text, (code, pos) in cases.items():
            with self.subTest(text=text):
                e = err(text)
                self.assertEqual((e.code, e.span.start), (code, pos))
                self.assertEqual(e.to_diagnostic()["status"], "invalid_input")

    def test_diagnostic_line_col(self):
        d = err("P ∧\n  Q Q").to_diagnostic()
        self.assertEqual((d["line"], d["column"]), (2, 5))


if __name__ == "__main__":
    unittest.main()


class BottomTests(unittest.TestCase):
    def test_bottom_parses_in_both_syntaxes(self):
        from logos import Bottom, to_string
        self.assertEqual(parse("⊥"), Bottom())
        self.assertEqual(parse("_|_"), Bottom())
        self.assertEqual(parse("P → ⊥"), Implies(Pred("P"), Bottom()))
        self.assertEqual(parse("¬⊥ ∧ ∀x (P(x) → _|_)"), parse("¬_|_ & forall x (P(x) -> ⊥)"))
        self.assertEqual(to_string(parse("P → ⊥")), "P → ⊥")
        self.assertEqual(to_string(parse("P → ⊥"), ascii=True), "P -> _|_")
        self.assertEqual(parse(to_string(parse("¬⊥ ∨ P"), ascii=True)), parse("¬⊥ ∨ P"))

    def test_bottom_is_not_a_term(self):
        self.assertEqual(err("⊥ = x").code, "unexpected_token")
        self.assertEqual(err("P(⊥)").code, "expected_term")


class PropositionalModeTests(unittest.TestCase):
    def test_lowercase_letters(self):
        self.assertEqual(parse("p → q", propositional=True), parse("P → Q"))
        self.assertEqual(parse("¬(p ∧ q) ∨ r1", propositional=True), parse("¬(P ∧ Q) ∨ R1"))

    def test_collision_p_and_P(self):
        with self.assertRaises(LogosError) as cm:
            parse("p → P", propositional=True)
        self.assertEqual((cm.exception.stage, cm.exception.code), ("semantic", "letter_collision"))

    def test_default_mode_unchanged(self):
        self.assertEqual(err("p → q").code, "expected_formula")

    def test_terms_and_equality_still_work(self):
        self.assertEqual(parse("x = y ∧ p", propositional=True), And(Eq(Var("x"), Var("y")), Pred("P")))
        self.assertEqual(parse("∀x (R(x) → q)", propositional=True),
                         Forall("x", Implies(Pred("R", (Var("x"),)), Pred("Q"))))
