"""La chuleta de reglas (rules-guide.json) debe coincidir con RULES y cada ejemplo debe ser una prueba verificada."""
import json
import unittest
from pathlib import Path

from batz import practice

GUIDE = Path(__file__).resolve().parents[1] / "src/batz/web/features/practice-tutorial/rules-guide.json"


class RulesGuideTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = json.loads(GUIDE.read_text(encoding="utf-8"))

    def test_families_partition_the_22_rules(self):
        listed = [r for f in self.guide["families"] for r in f["rules"]]
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(set(listed), set(practice.RULES))
        self.assertEqual(len(listed), 22)

    def test_every_rule_has_a_verified_example(self):
        self.assertEqual(set(self.guide["examples"]), set(practice.RULES))
        for rule, e in self.guide["examples"].items():
            with self.subTest(rule=rule):
                goal = e["moves"][-1]["formula"]
                ex = {"premises": e["premises"], "goal": goal, "constants": e["constants"]}
                result = practice.build(ex, e["moves"])
                self.assertTrue(result["complete"], "el ejemplo debe ser una prueba completa de su última línea")
                line = result["lines"][e["focus"] - 1]
                self.assertEqual(line["rule"], rule, "la línea señalada debe usar la regla del ejemplo")
                self.assertEqual(len(result["lines"]), len(e["premises"]) + len(e["moves"]))

    def test_catalog_still_carries_the_rules(self):
        rules = practice.api("catalog", {})["rules"]
        self.assertEqual(set(rules), set(practice.RULES))
        for r in rules.values():
            self.assertTrue(r["label"] and r["help"])


if __name__ == "__main__":
    unittest.main()
