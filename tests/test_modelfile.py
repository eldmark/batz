"""Archivos preparados, revisión de sintaxis por lotes y contraste en la API."""
import unittest
from pathlib import Path

from logos.errors import LogosError
from logos.modelfile import parse_model_file
from logos.server import handle_api

ROOT = Path(__file__).resolve().parents[1]
TEXT = """
# comentario
dominio: 0, 1
constante a = 0
funcion f/1: 0 -> 1, 1 -> 0
predicado P/1: 0
predicado R/2: (0, 1), (1, 0)
formula: ∀x R(x, f(x)) | espera: verdadero
formula: P(x) | x = 1 | espera: verdadero
formula: P(a,
"""


class ModelFile(unittest.TestCase):
    def test_text_format(self):
        package = parse_model_file(TEXT)
        self.assertEqual(package["signature"], {"constants": ["a"], "functions": {"f": 1}, "predicates": {"P": 1, "R": 2}})
        self.assertEqual(package["interpretation"]["functions"]["f"]["table"], [[[0], 1], [[1], 0]])
        self.assertEqual(package["interpretation"]["predicates"]["R"]["tuples"], [[0, 1], [1, 0]])
        self.assertEqual(package["formulas"][1]["assignment"], {"x": 1})
        self.assertIs(package["formulas"][0]["expected"], True)

    def test_strings_and_quotes(self):
        package = parse_model_file('dominio: Ana, "1", 2\npredicado P/1: Ana, "1"\n')
        self.assertEqual(package["interpretation"]["domain"], ["Ana", "1", 2])
        self.assertEqual(package["interpretation"]["predicates"]["P"]["tuples"], [["Ana"], ["1"]])

    def test_malformed_lines_name_the_line(self):
        for text, fragment in [("", "vacío"), ("predicado P/1: 0", "dominio"),
                               ("dominio: 0\nrelacion P/1: 0", "línea 2"),
                               ("dominio: 0\nfuncion f/1: 0", "línea 2"),
                               ("dominio: 0\npredicado P: 0", "línea 2"),
                               ("dominio: 0\nformula: P(x) | x", "línea 2"),
                               ("dominio: 0\nformula: P(x) | espera: quizá", "línea 2")]:
            with self.subTest(text=text):
                with self.assertRaises(LogosError) as ctx:
                    parse_model_file(text)
                self.assertIn(fragment, ctx.exception.message)

    def test_load_evaluates_each_formula_and_compares(self):
        loaded = handle_api("/api/load", {"text": TEXT})
        rows = loaded["results"]
        self.assertEqual([r["status"] for r in rows], ["ok", "ok", "invalid_input"])
        self.assertTrue(rows[0]["value"] and rows[0]["matches"])
        self.assertFalse(rows[1]["value"])            # P(1) es falso…
        self.assertIs(rows[1]["matches"], False)      # …y el archivo esperaba verdadero
        self.assertNotIn("value", rows[2])            # entrada inválida: sin valor de verdad

    def test_load_rejects_invalid_models(self):
        with self.assertRaises(LogosError):           # relación vacía
            handle_api("/api/load", {"text": "dominio: 0\npredicado P/1:\n"})
        with self.assertRaises(LogosError):           # función parcial
            handle_api("/api/load", {"text": "dominio: 0, 1\nfuncion f/1: 0 -> 1\n"})

    def test_json_export_round_trip(self):
        loaded = handle_api("/api/load", {"text": TEXT})
        import json
        again = handle_api("/api/load", {"text": json.dumps({
            "schema_version": "1", "signature": loaded["signature"], "interpretation": loaded["model"],
            "formula": "∃x P(x)"})})
        self.assertEqual(again["model"], loaded["model"])
        self.assertTrue(again["results"][0]["value"])

    def test_shipped_examples_match_their_expectations(self):
        for path in sorted((ROOT / "ejemplos").glob("*.logos")):
            with self.subTest(file=path.name):
                rows = handle_api("/api/load", {"text": path.read_text(encoding="utf-8")})["results"]
                self.assertTrue(rows)
                self.assertFalse([r for r in rows if r.get("matches") is False])


class ProofModeApi(unittest.TestCase):
    def test_parse_reports_each_formula(self):
        r = handle_api("/api/parse", {"formulas": ["∀x (P(x) → Q(x))", "P(a", "P(a, b)", "Q(y)"], "constants": ["a", "b"]})
        ok = [x["ok"] for x in r["results"]]
        self.assertEqual(ok, [True, False, False, True])
        self.assertEqual(r["results"][1]["error"]["span"], [3, 3])
        self.assertEqual(r["results"][2]["error"]["code"], "arity_mismatch")   # P ya era unario
        self.assertEqual(r["results"][3]["free"], ["y"])

    def test_proof_carries_second_engine(self):
        proved = handle_api("/api/proof", {"premises": ["P → Q", "P"], "conclusion": "Q", "constants": []})
        self.assertEqual((proved["status"], proved["contrast"]["verdict"]), ("proved", "consistent"))
        self.assertEqual(proved["contrast"]["engine_b"]["steps"][-1]["clause"], "□")
        invalid = handle_api("/api/proof", {"premises": ["P → Q"], "conclusion": "Q → P", "constants": []})
        self.assertEqual(invalid["status"], "unknown")                           # nunca «falso» por A
        self.assertEqual(invalid["contrast"]["engine_b"]["status"], "saturated")


if __name__ == "__main__":
    unittest.main()
