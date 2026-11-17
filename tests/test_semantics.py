import dataclasses
import itertools
import random
import unittest

from batz import (And, Bottom, Const, Eq, Exists, FiniteModel, Forall, Func, Iff, Implies,
                   BatzError, Not, Or, Pred, Var, check_trace, evaluate, holds,
                   is_countermodel, is_true, parse, to_string)
from helpers import all_models, close, rand_formula, rand_model


def m(domain, preds=None, consts=None, funcs=None):
    return FiniteModel(domain, consts or {}, funcs or {},
                       {n: (a, t) for n, (a, t) in (preds or {}).items()})


def code_of(fn, *a, **k):
    with unittest.TestCase().assertRaises(BatzError) as cm:
        fn(*a, **k)
    return cm.exception.code


def oracle(f, model, env):
    """Implementación independiente (cierres de Python) para contrastar."""
    def term(t):
        if isinstance(t, Var):
            return env[t.name]
        if isinstance(t, Const):
            return model.constants[t.name]
        return model.functions[t.name].table[tuple(term(a) for a in t.args)]
    k = type(f).__name__
    if k == "Bottom":
        return False
    if k == "Pred":
        return tuple(map(term, f.args)) in model.predicates[f.name].tuples
    if k == "Eq":
        return term(f.left) == term(f.right)
    if k == "Not":
        return not oracle(f.operand, model, env)
    if k == "And":
        return all([oracle(f.left, model, env), oracle(f.right, model, env)])
    if k == "Or":
        return any([oracle(f.left, model, env), oracle(f.right, model, env)])
    if k == "Implies":
        return (not oracle(f.left, model, env)) | oracle(f.right, model, env)
    if k == "Iff":
        return bool(oracle(f.left, model, env)) is bool(oracle(f.right, model, env))
    pick = all if k == "Forall" else any
    return pick([oracle(f.body, model, {**env, f.var: d}) for d in model.domain])


class ConnectiveTruthTables(unittest.TestCase):
    TABLES = {  # (A, B) -> valor
        "A ∧ B": {(1, 1): 1, (1, 0): 0, (0, 1): 0, (0, 0): 0},
        "A ∨ B": {(1, 1): 1, (1, 0): 1, (0, 1): 1, (0, 0): 0},
        "A → B": {(1, 1): 1, (1, 0): 0, (0, 1): 1, (0, 0): 1},
        "A ↔ B": {(1, 1): 1, (1, 0): 0, (0, 1): 0, (0, 0): 1},
    }

    def test_tables(self):
        for text, table in self.TABLES.items():
            for (a, b), want in table.items():
                model = m([0], {"A": (0, [()] if a else []), "B": (0, [()] if b else [])})
                with self.subTest(text=text, a=a, b=b):
                    self.assertEqual(is_true(model, parse(text)), bool(want))

    def test_negation(self):
        self.assertTrue(is_true(m([0], {"A": (0, [])}), parse("¬A")))
        self.assertFalse(is_true(m([0], {"A": (0, [()])}), parse("¬A")))

    def test_random_propositional_vs_python(self):
        rng = random.Random(5)
        names = "ABC"
        def gen(d):
            if d == 0 or rng.random() < 0.25:
                return rng.choice(names)
            op = rng.choice(["not", "and", "or", "imp", "iff"])
            if op == "not":
                return ("not", gen(d - 1))
            return (op, gen(d - 1), gen(d - 1))
        def py(t, v):
            if isinstance(t, str):
                return v[t]
            o = t[0]
            if o == "not":
                return not py(t[1], v)
            a, b = py(t[1], v), py(t[2], v)
            return {"and": a and b, "or": a or b, "imp": (not a) or b, "iff": a == b}[o]
        def ast(t):
            if isinstance(t, str):
                return Pred(t)
            if t[0] == "not":
                return Not(ast(t[1]))
            cls = {"and": And, "or": Or, "imp": Implies, "iff": Iff}[t[0]]
            return cls(ast(t[1]), ast(t[2]))
        for _ in range(300):
            t = gen(4)
            for bits in itertools.product([False, True], repeat=3):
                v = dict(zip(names, bits))
                model = m([0], {n: (0, [()] if v[n] else []) for n in names})
                self.assertEqual(is_true(model, ast(t)), py(t, v), t)


class QuantifierSemantics(unittest.TestCase):
    def test_conversa_no_autorizada(self):
        # Caso estrella de la Fase 4: un elemento a, P(a)=falso, Q(a)=verdadero
        model = m(["a"], {"P": (1, []), "Q": (1, [("a",)])})
        prem, concl = parse("∀x (P(x) → Q(x))"), parse("∀x (Q(x) → P(x))")
        self.assertTrue(is_true(model, prem))
        self.assertFalse(is_true(model, concl))
        self.assertTrue(is_countermodel(model, [prem], concl))

    def test_forall_exists_basic(self):
        model = m([1, 2, 3], {"P": (1, [(1,), (2,)])}, consts={"a": 1, "b": 2})
        self.assertTrue(is_true(model, parse("∃x P(x)")))
        self.assertFalse(is_true(model, parse("∀x P(x)")))
        self.assertTrue(is_true(model, parse("∃x ¬P(x)")))
        self.assertTrue(is_true(model, parse("∀x (P(x) → x = a ∨ x = b)", {"a", "b"})))

    def test_alternating_quantifiers(self):
        cycle = m([1, 2], {"R": (2, [(1, 2), (2, 1)])})
        self.assertTrue(is_true(cycle, parse("∀x ∃y R(x, y)")))
        self.assertFalse(is_true(cycle, parse("∃y ∀x R(x, y)")))
        lt = m([0, 1, 2], {"L": (2, [(a, b) for a in range(3) for b in range(3) if a < b])})
        self.assertFalse(is_true(lt, parse("∀x ∃y L(x, y)")))     # el 2 no tiene mayor
        self.assertTrue(is_true(lt, parse("∃x ∀y (L(x, y) ∨ x = y)")))  # el 0 es mínimo
        self.assertTrue(is_true(lt, parse("∀x ∃y (L(x, y) ∨ L(y, x))")))
        self.assertFalse(is_true(lt, parse("∃x ∀y L(x, y)")))

    def test_vacuous_and_nonempty_domain(self):
        model = m([0], {"P": (1, [])})
        self.assertTrue(is_true(model, parse("∀x (P(x) → P(x))")))
        self.assertFalse(is_true(model, parse("∃x P(x)")))
        self.assertTrue(is_true(model, parse("∀x P(x) → ∃x P(x)")))

    def test_shadowing(self):
        model = m([0, 1], {"P": (1, [(0,)]), "Q": (1, [(1,)])})
        # ∀x (P(x) ∧ ∃x Q(x)): falla porque P(1) es falsa; con x interna no confundida
        self.assertFalse(is_true(model, parse("∀x (P(x) ∧ ∃x Q(x))")))
        self.assertTrue(is_true(model, parse("∃x (P(x) ∧ ∃x Q(x))")))
        self.assertTrue(is_true(model, parse("∃x (P(x) ∧ ∃x (Q(x) ∧ ¬P(x)))")))

    def test_equality_counts_elements(self):
        for n in range(1, 5):
            model = m(list(range(n)))
            at_least_2 = parse("∃x ∃y x ≠ y")
            exactly_1 = parse("∀x ∀y x = y")
            self.assertEqual(is_true(model, at_least_2), n >= 2)
            self.assertEqual(is_true(model, exactly_1), n == 1)
            at_least_3 = parse("∃x ∃y ∃z (x ≠ y ∧ y ≠ z ∧ x ≠ z)")
            self.assertEqual(is_true(model, at_least_3), n >= 3)

    def test_functions_and_constants(self):
        succ = {(i,): (i + 1) % 3 for i in range(3)}
        model = m([0, 1, 2], consts={"a": 0}, funcs={"f": (1, succ)})
        self.assertTrue(is_true(model, parse("∀x f(f(f(x))) = x", {"a"})))
        self.assertFalse(is_true(model, parse("∃x f(x) = x", {"a"})))
        self.assertTrue(is_true(model, parse("f(f(a)) ≠ a ∧ ∀x ∃y f(y) = x", {"a"})))

    def test_elements_may_be_strings_and_ints(self):
        model = m(["1", 1], {"P": (1, [(1,)])})
        self.assertTrue(is_true(model, parse("∃x P(x) ∧ ∃x ¬P(x)")))
        self.assertTrue(is_true(model, parse("∃x ∃y x ≠ y")))


class OpenFormulas(unittest.TestCase):
    model = m([1, 2], {"P": (1, [(1,)]), "R": (2, [(1, 2)])}, consts={"a": 1})

    def test_requires_assignment(self):
        f = parse("P(x)")
        self.assertEqual(code_of(holds, self.model, f), "unassigned_variable")
        self.assertEqual(code_of(is_true, self.model, f), "unassigned_variable")
        self.assertEqual(code_of(evaluate, self.model, f, {"y": 1}), "unassigned_variable")

    def test_with_assignment(self):
        f = parse("P(x)")
        self.assertTrue(holds(self.model, f, {"x": 1}))
        self.assertFalse(holds(self.model, f, {"x": 2}))
        g = parse("∃y R(x, y)")
        self.assertTrue(holds(self.model, g, {"x": 1}))
        self.assertFalse(holds(self.model, g, {"x": 2}))

    def test_assignment_must_be_in_domain(self):
        self.assertEqual(code_of(holds, self.model, parse("P(x)"), {"x": 9}), "invalid_assignment")

    def test_extra_assignment_is_ignored(self):
        self.assertTrue(holds(self.model, parse("P(x)"), {"x": 1, "z": 2}))
        self.assertTrue(holds(self.model, parse("∀x (P(x) → x = a)", {"a"}), {"x": 2}))  # x ligada


class ModelAndSymbolErrors(unittest.TestCase):
    def test_missing_interpretation(self):
        model = m([0], {"P": (1, [])})
        self.assertEqual(code_of(is_true, model, parse("∃x Q(x)")), "missing_interpretation")
        self.assertEqual(code_of(is_true, model, parse("P(a)", {"a"})), "missing_interpretation")
        self.assertEqual(code_of(is_true, model, parse("∃x P(f(x))")), "missing_interpretation")

    def test_missing_symbol_has_span(self):
        with self.assertRaises(BatzError) as cm:
            is_true(m([0], {"P": (1, [])}), parse("∃x Q(x)"))
        self.assertEqual(cm.exception.span.start, 3)

    def test_arity_mismatch_with_model(self):
        model = m([0], {"P": (1, [])}, funcs={"f": (1, {(0,): 0})})
        self.assertEqual(code_of(is_true, model, parse("∃x P(x, x)")), "model_arity_mismatch")
        self.assertEqual(code_of(is_true, model, parse("∃x P(f(x, x))")), "model_arity_mismatch")

    def test_invalid_models(self):
        bad = [
            lambda: FiniteModel([]),
            lambda: FiniteModel([1, 1]),
            lambda: FiniteModel([True]),
            lambda: FiniteModel([1.5]),
            lambda: FiniteModel([0], {"a": 7}),
            lambda: FiniteModel([0], {"A": 0}),
            lambda: FiniteModel([0, 1], functions={"f": (1, {(0,): 0})}),          # tabla parcial
            lambda: FiniteModel([0, 1], functions={"f": (1, {(0,): 0, (1,): 5})}),
            lambda: FiniteModel([0], functions={"f": (0, {(): 0})}),
            lambda: FiniteModel([0], {"f": 0}, {"f": (1, {(0,): 0})}),
            lambda: FiniteModel([0], predicates={"P": (1, [(3,)])}),
            lambda: FiniteModel([0], predicates={"P": (2, [(0,)])}),
            lambda: FiniteModel([0], predicates={"p": (1, [])}),
        ]
        for make in bad:
            with self.subTest(make=make):
                self.assertEqual(code_of(make), "invalid_model")

    def test_serialization_roundtrip(self):
        rng = random.Random(3)
        for _ in range(50):
            model = rand_model(rng)
            self.assertEqual(FiniteModel.from_dict(model.to_dict()), model)
        self.assertEqual(code_of(FiniteModel.from_dict, {"schema_version": "9", "domain": [0]}), "invalid_model")


class Oracle(unittest.TestCase):
    def test_random_sentences_match_oracle(self):
        rng = random.Random(99)
        for _ in range(1500):
            f = close(rand_formula(rng, rng.randint(0, 4)))
            model = rand_model(rng)
            self.assertEqual(is_true(model, f), oracle(f, model, {}), to_string(f))

    def test_open_formulas_match_oracle(self):
        rng = random.Random(100)
        for _ in range(800):
            f = rand_formula(rng, rng.randint(0, 4))
            model = rand_model(rng)
            env = {v: rng.choice(model.domain) for v in "xyzw"}
            self.assertEqual(holds(model, f, env), oracle(f, model, env), to_string(f))


class SemanticLaws(unittest.TestCase):
    """Equivalencias y no-implicaciones comprobadas en TODOS los modelos pequeños."""

    def valid(self, text, sizes=(1, 2, 3), **kw):
        f = parse(text)
        for n in sizes:
            for model in all_models(n, **kw):
                if not is_true(model, f):
                    return False
        return True

    def test_valid_laws(self):
        laws = [
            "¬∀x P(x) ↔ ∃x ¬P(x)",
            "¬∃x P(x) ↔ ∀x ¬P(x)",
            "∀x (P(x) ∧ Q(x)) ↔ ∀x P(x) ∧ ∀x Q(x)",
            "∃x (P(x) ∨ Q(x)) ↔ ∃x P(x) ∨ ∃x Q(x)",
            "∀x P(x) → ∃x P(x)",
            "∃y ∀x R(x, y) → ∀x ∃y R(x, y)",
            "∀x ∀y R(x, y) ↔ ∀y ∀x R(x, y)",
            "∀x P(x) ∨ ∀x Q(x) → ∀x (P(x) ∨ Q(x))",
            "∃x (P(x) ∧ Q(x)) → ∃x P(x) ∧ ∃x Q(x)",
            "∀x (P(x) → Q(x)) → (∀x P(x) → ∀x Q(x))",
        ]
        for law in laws:
            with self.subTest(law=law):
                self.assertTrue(self.valid(law, unary=("P", "Q"), binary=("R",)))

    def test_invalid_have_countermodels(self):
        nonlaws = [
            "∀x (P(x) → Q(x)) → ∀x (Q(x) → P(x))",
            "∀x ∃y R(x, y) → ∃y ∀x R(x, y)",
            "∀x (P(x) ∨ Q(x)) → ∀x P(x) ∨ ∀x Q(x)",
            "∃x P(x) ∧ ∃x Q(x) → ∃x (P(x) ∧ Q(x))",
            "(∀x P(x) → ∀x Q(x)) → ∀x (P(x) → Q(x))",
            "∃x P(x) → ∀x P(x)",
        ]
        for text in nonlaws:
            with self.subTest(text=text):
                self.assertFalse(self.valid(text, unary=("P", "Q"), binary=("R",)))


class Traces(unittest.TestCase):
    def test_trace_value_matches_holds_and_checks(self):
        rng = random.Random(21)
        for _ in range(500):
            f = close(rand_formula(rng, rng.randint(0, 4)))
            model = rand_model(rng)
            tr = evaluate(model, f)
            self.assertEqual(tr.value, holds(model, f))
            check_trace(model, tr)

    def test_quantifier_children_cover_domain(self):
        model = m([5, 6, 7], {"P": (1, [(6,)])})
        tr = evaluate(model, parse("∃x P(x)"))
        self.assertEqual([c.element for c in tr.children], [5, 6, 7])
        self.assertEqual([c.value for c in tr.children], [False, True, False])
        self.assertTrue(tr.value)
        self.assertEqual(tr.children[1].term_values, (6,))

    def test_tampered_traces_rejected(self):
        model = m([0, 1], {"P": (1, [(0,)]), "R": (2, [(0, 1)])})
        f = parse("∀x (P(x) → ∃y R(x, y)) ∧ ¬∀x P(x)")
        tr = evaluate(model, f)
        check_trace(model, tr)

        def flip(t):  # cambia el valor de un nodo
            return dataclasses.replace(t, value=not t.value)

        def deep(t, path, fn):
            if not path:
                return fn(t)
            kids = list(t.children)
            kids[path[0]] = deep(kids[path[0]], path[1:], fn)
            return dataclasses.replace(t, children=tuple(kids))

        tampered = [
            flip(tr),
            deep(tr, [0], flip),
            deep(tr, [0, 0, 1], flip),
            deep(tr, [1, 0], flip),
            dataclasses.replace(tr, children=tr.children[:1]),
            deep(tr, [0, 0], lambda q: dataclasses.replace(q, children=q.children[::-1])),
            deep(tr, [0, 0, 0], lambda a: dataclasses.replace(a, term_values=(1,))),
            deep(tr, [0, 0], lambda q: dataclasses.replace(
                q, children=(dataclasses.replace(q.children[0], element=1),) + q.children[1:])),
        ]
        for bad in tampered:
            with self.subTest():
                self.assertEqual(code_of(check_trace, model, bad), "invalid_trace")


if __name__ == "__main__":
    unittest.main()
