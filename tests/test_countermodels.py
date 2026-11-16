import unittest

from logos import (CountermodelConfig, LogosError, Signature, build_interpretation,
                   find_countermodel, is_countermodel, parse)
from logos.countermodels import find_consequence_countermodel
from logos.semantics import holds


class CountermodelTests(unittest.TestCase):
    def test_finds_verified_minimum_with_nonempty_relation(self):
        sig = Signature(predicates={"P": 1})
        result = find_countermodel(sig, "∀x P(x)")
        self.assertEqual(result.status, "found")
        self.assertEqual(result.completed_sizes, (1,))
        self.assertEqual(len(result.model.domain), 2)
        self.assertTrue(result.model.predicates["P"].tuples)
        self.assertTrue(is_countermodel(result.model, [], parse("∀x P(x)")))
        self.assertFalse(result.explanation.value)
        self.assertEqual(build_interpretation(sig, result.model.to_dict()), result.model)
        self.assertEqual(result.to_dict()["model"], result.model.to_dict())

    def test_limits_never_claim_validity(self):
        sig = Signature(predicates={"P": 1})
        for cfg, reason in [
            (CountermodelConfig(max_size=1), "size_limit"),
            (CountermodelConfig(max_candidates=1), "candidate_limit"),
            (CountermodelConfig(max_table_rows=1), "table_limit"),
        ]:
            with self.subTest(reason=reason):
                result = find_countermodel(sig, "∀x P(x)", cfg)
                self.assertEqual(result.status, "unknown")
                self.assertEqual(result.reason, reason)
                self.assertIsNone(result.model)
                self.assertNotIn("model", result.to_dict())

    def test_closed_valid_formula_returns_unknown(self):
        result = find_countermodel(Signature(), "∀x x = x", CountermodelConfig(max_size=2))
        self.assertEqual(result.status, "unknown")
        self.assertEqual(result.completed_sizes, (1, 2))

    def test_open_and_undeclared_formula_rejected(self):
        for sig, text, code in [
            (Signature(predicates={"P": 1}), "P(x)", "unassigned_variable"),
            (Signature(), "Q(a)", "undeclared_symbol"),
        ]:
            with self.subTest(text=text):
                with self.assertRaises(LogosError) as cm:
                    find_countermodel(sig, text)
                self.assertEqual(cm.exception.code, code)

    def test_search_is_narrated_before_the_falsification(self):
        sig = Signature(predicates={"P": 1})
        data = find_countermodel(sig, "∀x P(x)").to_dict()
        self.assertEqual(data["log"], [{"size": 1, "explored": 1, "example": "P = {0}"},
                                       {"size": 2, "explored": 1, "found": True}])
        events = data["story"]["events"]
        self.assertEqual([e["kind"] for e in events[:3]], ["search", "search", "search"])
        self.assertEqual([e["size"] for e in events[:3]], [0, 1, 2])
        self.assertIn("Por ejemplo, con P = {0} no sirve.", events[1]["text_es"])
        self.assertEqual(events[3]["trace_path"], "0")  # luego, la evaluación verificada
        self.assertEqual([e["id"] for e in events], list(range(1, len(events) + 1)))


class ConsequenceCountermodelTests(unittest.TestCase):
    def search(self, premises, conclusion, constants=()):
        ps = [parse(p, constants) for p in premises]
        c = parse(conclusion, constants)
        return find_consequence_countermodel(ps, c, constants), ps, c

    def test_quantifier_swap_has_a_two_element_countermodel(self):
        result, ps, c = self.search(["∀x ∃y R(x, y)"], "∃y ∀x R(x, y)")
        self.assertEqual(result.status, "found")
        self.assertEqual(len(result.model.domain), 2)
        self.assertTrue(is_countermodel(result.model, ps, c))
        data = result.to_dict()
        self.assertTrue(data["loadable"])
        self.assertEqual([p["value"] for p in data["premises"]], [True])
        self.assertFalse(data["explanation"]["value"])
        kinds = [e["kind"] for e in data["story"]["events"]]
        self.assertEqual(kinds[:4], ["search", "search", "search", "premise"])

    def test_empty_relations_are_allowed_but_not_loadable(self):
        result, ps, c = self.search(["∀x P(x)"], "∃x Q(x)")
        self.assertEqual(result.status, "found")
        self.assertEqual(result.model.predicates["Q"].tuples, frozenset())
        self.assertFalse(result.loadable)

    def test_free_variables_get_an_assignment(self):
        result, ps, c = self.search(["P(x)"], "P(y)")
        self.assertEqual(result.status, "found")
        self.assertTrue(holds(result.model, ps[0], result.assignment))
        self.assertFalse(holds(result.model, c, result.assignment))

    def test_valid_consequence_never_gets_a_countermodel(self):
        result, _, _ = self.search(["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", ("a",))
        self.assertEqual(result.status, "unknown")
        self.assertEqual(result.to_dict()["reason"], "size_limit")


if __name__ == "__main__":
    unittest.main()
