import unittest

from logos import (CountermodelConfig, LogosError, Signature, build_interpretation,
                   find_countermodel, is_countermodel, parse)


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


if __name__ == "__main__":
    unittest.main()
