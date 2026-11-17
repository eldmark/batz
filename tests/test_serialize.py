import copy
import json
import random
import unittest

from batz import BatzError, parse, to_string
from batz.serialize import formula_from_dict, formula_to_dict
from helpers import rand_formula


def walk(node):
    yield node
    for k in ("args",):
        for c in node.get(k, []):
            yield from walk(c)
    for k in ("left", "right", "operand", "body"):
        if k in node:
            yield from walk(node[k])


class FormulaJson(unittest.TestCase):
    def test_roundtrip_random(self):
        rng = random.Random(5)
        for _ in range(500):
            f = rand_formula(rng, rng.randint(0, 5))
            d = formula_to_dict(f)
            self.assertEqual(formula_from_dict(json.loads(json.dumps(d))), f)
            self.assertEqual(d["text"], to_string(f))

    def test_ids_are_stable_unique_and_paths(self):
        f = parse("∀x (P(x) → ∃y R(x, f(y)))")
        d = formula_to_dict(f)
        ids = [n["id"] for n in walk(d["tree"])]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(d["tree"]["id"], "0")
        self.assertEqual(d["tree"]["body"]["id"], "0.0")
        self.assertEqual(formula_to_dict(f), formula_to_dict(parse("∀x (P(x) → ∃y R(x, f(y)))")))

    def test_spans_optional_and_only_from_text(self):
        d = formula_to_dict(parse("P ∧ Q"))
        self.assertEqual(d["tree"]["span"], [0, 5])
        self.assertNotIn("span", formula_to_dict(parse("P ∧ Q"), spans=False)["tree"])

    def test_invalid_trees_are_rejected(self):
        good = formula_to_dict(parse("∀x P(x)"))
        def mut(fn):
            d = copy.deepcopy(good)
            fn(d)
            return d
        bad = [
            mut(lambda d: d.update(schema_version="9")),
            mut(lambda d: d.pop("tree")),
            mut(lambda d: d["tree"].update(kind="magic")),
            mut(lambda d: d["tree"].update(var="X")),
            mut(lambda d: d["tree"]["body"].update(id="0.5")),
            mut(lambda d: d["tree"]["body"].update(name="p")),
            mut(lambda d: d["tree"]["body"]["args"][0].update(kind="bottom")),
            mut(lambda d: d.update(text="∃x P(x)")),
            mut(lambda d: d["tree"].pop("body")),
        ]
        for d in bad:
            with self.subTest(d=d):
                with self.assertRaises(BatzError) as cm:
                    formula_from_dict(d)
                self.assertEqual(cm.exception.code, "invalid_ast")


if __name__ == "__main__":
    unittest.main()


class ResultEnvelope(unittest.TestCase):
    def test_envelopes_are_json_and_reload(self):
        from batz import FiniteModel, decide
        from batz.proof import ProofCertificate, SearchConfig, prove_text, verify
        r = prove_text(["p → q", "p"], "q", propositional=True)
        d = json.loads(json.dumps(r.to_dict()))
        self.assertEqual(d["status"], "proved")
        verify(ProofCertificate.from_dict(d["certificate"]))
        v = decide([parse("A → B")], parse("B → A"))
        d = json.loads(json.dumps(v.to_dict()))
        self.assertEqual(d["status"], "counterexample")
        self.assertEqual(FiniteModel.from_dict(d["countermodel"]), v.countermodel)
        bad = prove_text(["A ∧"], "A").to_dict()
        self.assertEqual((bad["status"], bad["diagnostic"]["stage"]), ("invalid_input", "syntactic"))
        self.assertEqual(prove_text([], "A").to_dict()["status"], "unknown")
        from batz.serialize import result_to_dict
        self.assertRaises(ValueError, result_to_dict, "maybe")
