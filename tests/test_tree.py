"""Árboles para el visor: estructura y evaluación, sin lógica propia (se leen de la traza verificada)."""
import unittest

from batz import FiniteModel, evaluate, parse
from batz.server import handle_api
from batz.tree import MAX_NODES, semantic_tree, syntax_tree

SIG = {"constants": [], "functions": {"s": 1}, "predicates": {"P": 1, "R": 2}}
MODEL = {"domain": [0, 1], "functions": {"s": {"arity": 1, "table": [[[0], 1], [[1], 0]]}},
         "predicates": {"P": {"arity": 1, "tuples": [[0]]}, "R": {"arity": 2, "tuples": [[0, 1]]}}}


def walk(tree):
    yield tree
    for child in tree["children"]:
        yield from walk(child)


class SyntaxTree(unittest.TestCase):
    def test_shape_and_leaf_kinds(self):
        t = syntax_tree(parse("∀x (P(x) → ∃y R(x, s(y)))"))
        self.assertEqual((t["label"], t["kind"]), ("∀x", "quantifier"))
        self.assertEqual(t["children"][0]["label"], "→")
        exists = t["children"][0]["children"][1]
        self.assertEqual(exists["label"], "∃y")
        atom = exists["children"][0]
        self.assertEqual((atom["label"], atom["kind"]), ("R", "pred"))
        self.assertEqual([(c["label"], c["kind"]) for c in atom["children"]], [("x", "var"), ("s", "func")])
        self.assertEqual(atom["children"][1]["children"][0]["label"], "y")

    def test_every_connective_and_special_atoms(self):
        for text, label in [("¬P(a)", "¬"), ("P(a) ∧ P(b)", "∧"), ("P(a) ∨ P(b)", "∨"), ("P(a) ↔ P(b)", "↔"), ("a = b", "="), ("⊥", "⊥")]:
            with self.subTest(text=text):
                self.assertEqual(syntax_tree(parse(text, {"a", "b"}))["label"], label)

    def test_propositional_letters_keep_the_users_spelling(self):
        t = syntax_tree(parse("P → Q", propositional=False), {"P": "p", "Q": "q"})
        self.assertEqual([c["label"] for c in t["children"]], ["p", "q"])
        self.assertEqual(t["formula"], "p → q")


class SemanticTree(unittest.TestCase):
    def setUp(self):
        self.model = FiniteModel([0, 1], predicates={"P": (1, [(0,)]), "R": (2, [(0, 1)])})
        self.trace = evaluate(self.model, parse("∀x (P(x) → ∃y R(x, y))"))

    def test_values_come_from_the_verified_trace(self):
        t = semantic_tree(self.trace)
        self.assertIs(t["value"], True)
        self.assertEqual(t["nodes"], len(list(walk(t))))
        self.assertEqual([c["edge"] for c in t["children"]], ["x = 0", "x = 1"])      # una rama por elemento de D
        leaf = t["children"][0]["children"][0]
        self.assertEqual((leaf["label"], leaf["values"], leaf["relation"], leaf["value"]), ("P(x)", [0], "P", True))
        self.assertEqual(leaf["assignment"], [["x", 0]])

    def test_every_node_value_is_consistent_with_its_children(self):
        t = semantic_tree(self.trace)
        for n in walk(t):
            vals = [c["value"] for c in n["children"]]
            if n["label"].startswith("∀"):
                self.assertEqual(n["value"], all(vals))
            elif n["label"].startswith("∃"):
                self.assertEqual(n["value"], any(vals))
            elif n["label"] == "→":
                self.assertEqual(n["value"], (not vals[0]) or vals[1])

    def test_large_trees_are_cut_and_say_so(self):
        big = FiniteModel(list(range(8)), predicates={"R": (2, [(0, 0)])})
        trace = evaluate(big, parse("∀x ∀y ∀z R(x, y)"), {})
        t = semantic_tree(trace, limit=50)
        self.assertLessEqual(t["nodes"], 50 + 3 * 8)      # el corte puede dejar hermanos pendientes: límite + profundidad × |D|
        self.assertTrue(any("truncated" in n for n in walk(t)))
        self.assertGreater(MAX_NODES, 100)


class Api(unittest.TestCase):
    def test_evaluate_returns_both_views(self):
        r = handle_api("/api/evaluate", {"signature": SIG, "interpretation": MODEL, "formula": "∀x (P(x) → P(s(x)))", "assignment": {}})
        self.assertIs(r["value"], False)
        self.assertEqual((r["tree"]["label"], r["syntax"]["label"]), ("∀x", "∀x"))
        self.assertIs(r["tree"]["value"], False)

    def test_parse_and_spanish_carry_a_syntax_tree(self):
        r = handle_api("/api/parse", {"formulas": ["∀x (P(x) → Q(x))", "P(a"], "constants": []})
        self.assertEqual(r["results"][0]["tree"]["label"], "∀x")
        self.assertNotIn("tree", r["results"][1])                  # una fórmula con error de sintaxis no tiene árbol
        prop = handle_api("/api/parse", {"formulas": ["p → q", "¬q → ¬p"], "constants": []})
        self.assertEqual([c["label"] for c in prop["results"][1]["tree"]["children"]], ["¬", "¬"])
        s = handle_api("/api/spanish", {"text": "Todos los estudiantes leen un libro"})
        self.assertTrue(all(reading["tree"]["label"] in ("∀x", "∃y") for reading in s["readings"]))


if __name__ == "__main__":
    unittest.main()
