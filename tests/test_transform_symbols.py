import random
import unittest

from batz import (And, Const, Eq, Exists, Forall, Func, Implies, BatzError, Not,
                   Pred, Signature, Var, alpha_equiv, alpha_rename, bound_vars, check,
                   free_vars, is_closed, parse, parse_checked, rename_bound_canonical,
                   substitute, to_string)
from helpers import rand_formula, rand_term

x, y, z = Var("x"), Var("y"), Var("z")


class FreeBoundTests(unittest.TestCase):
    def test_free_bound(self):
        f = parse("∀x (P(x) ∧ R(x, y)) ∨ Q(z)")
        self.assertEqual(free_vars(f), {"y", "z"})
        self.assertEqual(bound_vars(f), {"x"})
        self.assertFalse(is_closed(f))
        self.assertTrue(is_closed(parse("∀x ∃y R(x, y)")))

    def test_shadowing_free_vars(self):
        self.assertEqual(free_vars(parse("P(x) ∧ ∀x Q(x)")), {"x"})
        self.assertEqual(free_vars(parse("∀x (Q(x) ∧ ∃x P(x))")), set())


class SubstitutionTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(substitute(parse("P(x) ∧ Q(y)"), {"x": Const("a")}), parse("P(a) ∧ Q(y)", {"a"}))

    def test_bound_not_replaced(self):
        f = parse("∀x P(x) ∧ P(x)")
        self.assertEqual(substitute(f, {"x": Const("a")}), parse("∀x P(x) ∧ P(a)", {"a"}))

    def test_capture_avoided(self):
        f = parse("∀y R(x, y)")
        g = substitute(f, {"x": y})  # ingenuamente daría ∀y R(y, y)
        self.assertIsInstance(g, Forall)
        self.assertNotEqual(g.var, "y")
        self.assertTrue(alpha_equiv(g, parse("∀w R(y, w)")))
        self.assertEqual(free_vars(g), {"y"})

    def test_capture_avoided_with_functions_and_nesting(self):
        f = parse("∃z ∀y (R(x, y) → Q(z))")
        g = substitute(f, {"x": Func("g", (y, z))})
        self.assertEqual(free_vars(g), {"y", "z"})
        self.assertTrue(alpha_equiv(g, parse("∃a ∀b (R(g(y, z), b) → Q(a))")))

    def test_simultaneous(self):
        f = parse("R(x, y)")
        self.assertEqual(substitute(f, {"x": y, "y": x}), parse("R(y, x)"))

    def test_no_op_when_not_free(self):
        f = parse("∀x P(x)")
        self.assertIs(substitute(f, {"x": Const("a")}), f)

    def test_fresh_name_avoids_everything(self):
        f = parse("∀y (R(x, y) ∧ Q(y1))")
        g = substitute(f, {"x": y})
        self.assertNotIn(g.var, {"y", "y1", "x"})
        self.assertEqual(free_vars(g), {"y", "y1"})

    def test_rejects_non_terms(self):
        self.assertRaises(TypeError, substitute, parse("P(x)"), {"x": Pred("Q")})


class AlphaTests(unittest.TestCase):
    def test_equiv(self):
        self.assertTrue(alpha_equiv(parse("∀x P(x)"), parse("∀y P(y)")))
        self.assertTrue(alpha_equiv(parse("∀x ∃y R(x, y)"), parse("∀a ∃b R(a, b)")))
        self.assertFalse(alpha_equiv(parse("∀x ∃y R(x, y)"), parse("∀x ∃y R(y, x)")))
        self.assertFalse(alpha_equiv(parse("∀x ∃y R(x, y)"), parse("∃y ∀x R(x, y)")))

    def test_free_variables_matter(self):
        self.assertFalse(alpha_equiv(parse("P(x)"), parse("P(y)")))
        self.assertFalse(alpha_equiv(parse("∀x R(x, y)"), parse("∀x R(x, x)")))
        self.assertFalse(alpha_equiv(parse("∀x R(x, y)"), parse("∀y R(y, y)")))

    def test_shadowing_equiv(self):
        self.assertTrue(alpha_equiv(parse("∀x ∀x P(x)"), parse("∀y ∀z P(z)")))
        self.assertFalse(alpha_equiv(parse("∀x ∀x P(x)"), parse("∀y ∀z P(y)")))

    def test_alpha_rename(self):
        q = parse("∀x R(x, y)")
        self.assertEqual(alpha_rename(q, "w"), parse("∀w R(w, y)"))
        self.assertRaises(ValueError, alpha_rename, q, "y")  # captura
        self.assertRaises(ValueError, alpha_rename, parse("∀x ∀w R(x, w)"), "w")

    def test_canonical_form_characterizes_alpha_equiv(self):
        rng = random.Random(7)
        for _ in range(300):
            a, b = rand_formula(rng, 3), rand_formula(rng, 3)
            self.assertEqual(alpha_equiv(a, b),
                             rename_bound_canonical(a) == rename_bound_canonical(b),
                             (to_string(a), to_string(b)))


class SubstitutionProperties(unittest.TestCase):
    def test_free_vars_of_substitution(self):
        rng = random.Random(11)
        for _ in range(400):
            f = rand_formula(rng, 3)
            t = rand_term(rng, 2)
            g = substitute(f, {"x": t})
            from batz.transform import term_vars
            fv = free_vars(f)
            expected = (fv - {"x"}) | (term_vars(t) if "x" in fv else frozenset())
            self.assertEqual(free_vars(g), expected, (to_string(f), to_string(t)))

    def test_identity_and_alpha_invariance(self):
        rng = random.Random(13)
        for _ in range(300):
            f = rand_formula(rng, 3)
            self.assertTrue(alpha_equiv(substitute(f, {"x": x}), f))
            t = rand_term(rng, 2)
            g = rename_bound_canonical(f, prefix="q")
            self.assertTrue(alpha_equiv(substitute(f, {"x": t}), substitute(g, {"x": t})),
                            (to_string(f), to_string(t)))


class SymbolTests(unittest.TestCase):
    def test_arity_mismatch_predicate(self):
        with self.assertRaises(BatzError) as cm:
            parse_checked("P(x) ∧ P(x, y)")
        e = cm.exception
        self.assertEqual((e.stage, e.code), ("semantic", "arity_mismatch"))
        self.assertEqual(e.span.start, 7)

    def test_arity_mismatch_function(self):
        with self.assertRaises(BatzError) as cm:
            parse_checked("Q(f(x)) ∧ Q(f(x, y))")
        self.assertEqual(cm.exception.code, "arity_mismatch")

    def test_declared_signature(self):
        sig = Signature(constants={"a"}, predicates={"P": 1}, functions={"f": 2})
        parse_checked("P(f(a, a))", sig, strict=True)
        with self.assertRaises(BatzError) as cm:
            parse_checked("P(a, a)", sig)
        self.assertEqual(cm.exception.code, "arity_mismatch")

    def test_strict_undeclared(self):
        sig = Signature(constants={"a"}, predicates={"P": 1})
        for text in ["Q(a)", "P(f(a))"]:
            with self.subTest(text=text):
                with self.assertRaises(BatzError) as cm:
                    parse_checked(text, sig, strict=True)
                self.assertEqual(cm.exception.code, "undeclared_symbol")

    def test_kind_clash(self):
        with self.assertRaises(BatzError) as cm:
            parse_checked("P(f) ∧ Q(f(x))")
        self.assertEqual(cm.exception.code, "symbol_kind_clash")

    def test_inferred_signature(self):
        sig = check(parse("∀x R(x, f(a)) ∧ S", {"a"}))
        self.assertEqual((sig.predicates, sig.functions, sig.constants),
                         ({"R": 2, "S": 0}, {"f": 1}, frozenset({"a"})))


if __name__ == "__main__":
    unittest.main()
