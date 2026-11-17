"""Etiquetador entrenado: propone la categoría de palabras fuera del léxico; la gramática decide."""
import os
import tempfile
import unittest
from pathlib import Path

# El diccionario del usuario no debe influir en las pruebas ni ensuciarse con ellas.
os.environ["BATZ_LEXICON"] = str(Path(tempfile.mkdtemp()) / "lexico_usuario.tsv")

from batz import BatzError, parse_checked, translate_spanish
from batz import spanish_semantics, spanish_tagger as tagger

ROOT = Path(__file__).resolve().parents[1]


class Tagger(unittest.TestCase):
    def test_weights_ship_with_measured_accuracy(self):
        self.assertTrue(tagger.available())
        meta = tagger.meta()
        self.assertGreaterEqual(meta["test_accuracy"], 0.90)          # palabras nunca vistas
        self.assertGreaterEqual(meta["test_accuracy_coarse"], 0.97)

    def test_predicate_guess(self):
        for word, tag, symbol in [("perros", "N_MP", "Perro"), ("hombres", "N_MP", "Hombre"), ("flores", "N_FP", "Flor"),
                                  ("luces", "N_FP", "Luz"), ("altas", "Adj_FP", "Alto"), ("mortales", "Adj_MP", "Mortal"),
                                  ("ladran", "VI_P", "Ladrar"), ("ladra", "VI_S", "Ladrar"), ("ladren", "VIsub_P", "Ladrar"),
                                  ("come", "VT_S", "Comer"), ("aprobaron", "VI_P", "Aprobar"), ("vuela", "VI_S", "Volar"), ("piensan", "VI_P", "Pensar"), ("Sócrates", "NProp_M", "socrates")]:
            with self.subTest(word=word):
                self.assertEqual(tagger.guess_predicate(word, tag), symbol)

    def test_unknown_words_are_proposed_and_reported(self):
        result = translate_spanish("Todos los tlacuaches barritan")       # ninguna de las dos está en el diccionario
        self.assertEqual([r.text for r in result.readings], ["∀x (Tlacuache(x) → Barritar(x))"])
        self.assertEqual([(a["word"], a["tag"]) for a in result.assumptions], [("tlacuaches", "N_MP"), ("barritan", "VI_P")])
        for a in result.assumptions:
            self.assertTrue(0 < a["probability"] <= 1)
        reading = result.readings[0]
        self.assertEqual(reading.formula, parse_checked(reading.text, reading.signature, strict=True))
        self.assertEqual(spanish_semantics.EXTRA, {})                 # no queda estado entre frases

    def test_lexicon_phrases_need_no_assumptions(self):
        result = translate_spanish("Todos los estudiantes leen un libro")
        self.assertEqual(result.assumptions, ())
        self.assertEqual(len(result.readings), 2)

    def test_grammar_still_rejects_nonsense_with_unknown_words(self):
        for phrase in ("Tlacuaches los todos barritan", "Todos los tlacuaches barrita", "Zzz qqq www"):
            with self.subTest(phrase=phrase):
                with self.assertRaises(BatzError):
                    translate_spanish(phrase)

    def test_singular_and_plural_share_the_predicate(self):
        a = translate_spanish("Algún tlacuache barrita").readings[0].text
        b = translate_spanish("Todos los tlacuaches barritan").readings[0].text
        self.assertIn("Tlacuache(x)", a); self.assertIn("Barritar(x)", a)
        self.assertIn("Tlacuache(x)", b); self.assertIn("Barritar(x)", b)

    def test_class_phrases(self):
        rows = [l.split("\t") for l in (ROOT / "docs/specs/espanol/frases_clase.tsv").read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
        good = 0
        for phrase, expected in rows:
            try:
                got = [r.text for r in translate_spanish(phrase).readings]
                good += expected in got
            except BatzError:
                good += expected == "RECHAZA"
        self.assertGreaterEqual(good, len(rows) - 2, f"{good}/{len(rows)}")


if __name__ == "__main__":
    unittest.main()
