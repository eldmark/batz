"""Los 51 casos de la gramática se deben traducir o rechazar sin inventar lecturas."""
import unittest
from pathlib import Path

from batz import BatzError, parse_checked, translate_spanish
from batz.spanish_cyk import parse


CASES = Path(__file__).resolve().parents[1] / "docs/specs/espanol/casos_borde.txt"


class SpanishFullCorpus(unittest.TestCase):
    def test_all_51_cases(self):
        lines = [line for line in CASES.read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.startswith("#")]
        self.assertEqual(len(lines), 51)
        for line in lines:
            expected, phrase = line.split("|", 1)
            with self.subTest(phrase=phrase):
                _, trees = parse(phrase)
                if int(expected): self.assertGreaterEqual(len(trees), int(expected))
                else: self.assertEqual(len(trees), 0)
                if not trees:
                    with self.assertRaises(BatzError): translate_spanish(phrase)
                    continue
                result = translate_spanish(phrase)
                self.assertTrue(result.readings)
                self.assertEqual(len({r.text for r in result.readings}), len(result.readings))
                for reading in result.readings:
                    self.assertEqual(reading.formula, parse_checked(reading.text, reading.signature, strict=True))

    def test_scope_and_numeral_choices(self):
        for phrase in ("Todos los estudiantes leyeron un libro",
                       "Todos los estudiantes no leen", "Dos estudiantes leen"):
            with self.subTest(phrase=phrase):
                result = translate_spanish(phrase)
                self.assertEqual(result.status, "ambiguous")
                self.assertEqual(len(result.readings), 2)


if __name__ == "__main__": unittest.main()
