"""Contratos de entrada del evaluador MM3032."""
import copy
import json
import unittest

from logos import Signature, build_interpretation, evaluar, libres
from logos.errors import LogosError


SIG = Signature(constants={"a"}, functions={"f": 1}, predicates={"P": 1})
DATA = {
    "domain": [0, 1],
    "constants": {"a": 0},
    "functions": {"f": {"arity": 1, "table": [[[0], 1], [[1], 0]]}},
    "predicates": {"P": {"arity": 1, "tuples": [[0]]}},
}


class StrictInterpretation(unittest.TestCase):
    def test_valid_model_and_result(self):
        result = evaluar(SIG, DATA, "∀x (P(x) → P(f(f(x))))")
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.value)
        self.assertIsNotNone(result.trace)
        self.assertEqual(result.errors, ())
        self.assertTrue(evaluar(SIG, json.dumps(DATA), "P(a)").value)

    def test_invalid_interpretations(self):
        changes = [
            ("domain", []),
            ("domain", [0, 0]),
            ("domain", "01"),
            ("constants", {}),
            ("constants", {"a": 2}),
            ("constants", {"a": False}),
            ("constants", {"a": 0, "b": 1}),
            ("functions", {"f": {"arity": 1, "table": [[[0], 1]]}}),
            ("functions", {"f": {"arity": 1, "table": [[[0], 1], [[1], 2]]}}),
            ("functions", {"f": {"arity": 1, "table": [[[0], 1], [[0], 0], [[1], 0]]}}),
            ("predicates", {"P": {"arity": 1, "tuples": []}}),
            ("predicates", {"P": {"arity": 1, "tuples": [[2]]}}),
            ("predicates", {"P": {"arity": 1, "tuples": [[False]]}}),
            ("predicates", {"P": {"arity": 1, "tuples": [[0, 1]]}}),
            ("predicates", {"P": {"arity": 2, "tuples": [[0]]}}),
            ("predicates", {"P": {"arity": 1, "tuples": [[0]]}, "Q": {"arity": 1, "tuples": [[0]]}}),
        ]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(DATA)
                data[field] = value
                result = evaluar(SIG, data, "P(a)")
                self.assertEqual(result.status, "invalid_input")
                self.assertIsNone(result.value)
                self.assertIsNone(result.trace)
                self.assertEqual(result.errors[0]["code"], "invalid_model")

    def test_predicate_zero_arity_rejected_at_project_boundary(self):
        with self.assertRaises(LogosError) as cm:
            build_interpretation(Signature(predicates={"P": 0}),
                                 {"domain": [0], "predicates": {"P": {"arity": 0, "tuples": [[]]}}})
        self.assertEqual(cm.exception.code, "invalid_model")

    def test_free_variables_and_input_errors(self):
        self.assertEqual(libres("P(x) ∧ ∀x P(x)", SIG), ("x",))
        self.assertEqual(libres("P(x) ∧ ∀x P(x)"), ("x",))
        for formula, env, code in [
            ("P(x)", None, "unassigned_variable"),
            ("P(x)", {"x": 3}, "invalid_assignment"),
            ("Q(a)", None, "undeclared_symbol"),
            ("P(a, a)", None, "arity_mismatch"),
            ("P(", None, "expected_term"),
        ]:
            with self.subTest(formula=formula):
                result = evaluar(SIG, DATA, formula, env)
                self.assertEqual(result.status, "invalid_input")
                self.assertIsNone(result.value)
                self.assertIsNone(result.trace)
                self.assertEqual(result.errors[0]["code"], code)

    def test_malformed_formula_and_environment(self):
        for text, env, code in [
            (None, None, "expected_formula"),
            ("P(a)", [0], "invalid_assignment"),
            ("P(x)", {"x": False}, "invalid_assignment"),
        ]:
            result = evaluar(SIG, DATA, text, env)
            self.assertEqual(result.status, "invalid_input")
            self.assertIsNone(result.value)
            self.assertIsNone(result.trace)
            self.assertEqual(result.errors[0]["code"], code)
        result = evaluar(SIG, "{", "P(a)")
        self.assertEqual(result.status, "invalid_input")
        self.assertEqual(result.errors[0]["code"], "invalid_model")


if __name__ == "__main__":
    unittest.main()


class AuditFixes(unittest.TestCase):
    def test_empty_domain_has_its_own_message(self):
        data = copy.deepcopy(DATA); data["domain"] = []
        error = evaluar(SIG, data, "P(a)").errors[0]
        self.assertEqual(error["code"], "invalid_model")
        self.assertIn("vacío", error["message"])

    def test_environment_only_assigns_variables(self):
        for name in ("a", "f", "P", "1x"):
            with self.subTest(name=name):
                result = evaluar(SIG, DATA, "P(x)", {"x": 0, name: 1})
                self.assertEqual(result.status, "invalid_input")
                self.assertIsNone(result.value)
                self.assertEqual(result.errors[0]["code"], "invalid_assignment")
        # s asigna todas las variables; las que no son libres no cambian el valor
        self.assertTrue(evaluar(SIG, DATA, "P(x)", {"x": 0, "y": 1}).value)

    def test_undeclared_message_agrees_in_gender(self):
        self.assertIn("declarada", evaluar(SIG, DATA, "P(g(a))").errors[0]["message"])
        self.assertIn("declarado", evaluar(SIG, DATA, "Q(a)").errors[0]["message"])

    def test_explanation_carries_instance_environment(self):
        e = evaluar(SIG, DATA, "∀x (P(x) ∨ ¬P(x))").explanation.to_dict()
        self.assertEqual([c["assignment"] for c in e["children"]], [[["x", 0]], [["x", 1]]])
        self.assertEqual(e["assignment"], [])
