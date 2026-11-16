"""Sinónimos (mismo símbolo), palabras con varios sentidos (una lectura por sentido) y la cola de palabras."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["LOGOS_LEXICON"] = str(Path(tempfile.mkdtemp()) / "lexico_usuario.tsv")

from logos import LogosError, lexicon, translate_spanish
from logos.server import handle_api

ROOT = Path(__file__).resolve().parents[1]


class Synonyms(unittest.TestCase):
    def test_synonyms_share_the_symbol_of_the_main_word(self):
        for phrase, formula in [("Todo can ladra", "∀x (Perro(x) → Ladrar(x))"),
                                ("Algún felino duerme", "∃x (Gato(x) ∧ Dormir(x))"),
                                ("Carlos estima a Lucía", "Respetar2(carlos, lucia)"),
                                ("Toda vivienda es amplia", "∀x (Casa(x) → Grande(x))"),
                                ("Todo muchacho es raudo", "∀x (Niño(x) → Rapido(x))")]:
            with self.subTest(phrase=phrase):
                self.assertIn(formula, [r.text for r in translate_spanish(phrase).readings])

    def test_a_synonym_pair_is_the_same_sentence_logically(self):
        a = [r.text for r in translate_spanish("Todo perro ladra").readings]
        b = [r.text for r in translate_spanish("Todo can ladra").readings]
        self.assertEqual(a, b)

    def test_every_synonym_points_at_an_existing_main_word(self):
        lemmas = {(e.lemma.casefold(), e.category) for e in lexicon.entries()}
        by_key = {(e.lemma.casefold(), e.category): e for e in lexicon.entries()}
        count = 0
        for e in lexicon.entries():
            main = e.options().get("sin")
            if not main:
                continue
            count += 1
            self.assertIn((main, e.category), lemmas, f"{e.lemma} → {main}")
            self.assertFalse(by_key[(main, e.category)].options().get("sin"), f"{e.lemma}: cadena de sinónimos")
        self.assertGreater(count, 500)

    def test_user_can_declare_a_synonym(self):
        handle_api("/api/lexicon/add", {"lemma": "galgo", "category": "N", "feature": "M", "extra": "sin=perro"})
        try:
            self.assertEqual([r.text for r in translate_spanish("Todo galgo ladra").readings], ["∀x (Perro(x) → Ladrar(x))"])
            found = handle_api("/api/lexicon/search", {"query": "galgo"})["entries"][0]
            self.assertEqual(found["gloss"], "sinónimo de perro")
        finally:
            lexicon.remove("galgo", "N")


class Senses(unittest.TestCase):
    def test_polysemous_word_gives_one_reading_per_sense(self):
        readings = translate_spanish("Juan compra un banco").readings
        self.assertEqual({r.text for r in readings},
                         {"∃x (Banco_asiento(x) ∧ Comprar2(juan, x))", "∃x (Banco_entidad(x) ∧ Comprar2(juan, x))"})
        self.assertTrue(all("«banco» como" in r.note for r in readings))

    def test_two_polysemous_words_give_the_product_of_senses(self):
        readings = translate_spanish("Todo ratón compra un banco").readings
        self.assertEqual(len(readings), 8)                                   # 2 sentidos × 2 sentidos × 2 alcances
        self.assertEqual(len({(("animal" in r.text), ("asiento" in r.text)) for r in readings}), 4)

    def test_unambiguous_words_do_not_multiply_readings(self):
        self.assertEqual(len(translate_spanish("Todos los hombres son mortales").readings), 1)
        self.assertEqual(len(translate_spanish("Todos los estudiantes leen un libro").readings), 2)   # solo el alcance

    def test_user_can_add_a_sense(self):
        handle_api("/api/lexicon/add", {"lemma": "pila", "category": "N", "feature": "F", "extra": "sentido=bateria"})
        handle_api("/api/lexicon/add", {"lemma": "pila", "category": "N", "feature": "F", "extra": "sentido=montón"})
        try:
            self.assertEqual({r.text for r in translate_spanish("Toda pila es grande").readings},
                             {"∀x (Pila_bateria(x) → Grande(x))", "∀x (Pila_monton(x) → Grande(x))"})
            with self.assertRaises(LogosError):        # el mismo sentido dos veces no se admite
                handle_api("/api/lexicon/add", {"lemma": "pila", "category": "N", "feature": "F", "extra": "sentido=bateria"})
        finally:
            lexicon.remove("pila", "N")


class Queue(unittest.TestCase):
    def run_queue(self, *args):
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        return subprocess.run([sys.executable, str(ROOT / "scripts/lexicon_queue.py"), *args], capture_output=True, text=True, env=env, cwd=ROOT)

    def test_queue_round_trip(self):
        queue = ROOT / "datos" / "cola_lexico.txt"
        backup = queue.read_bytes() if queue.is_file() else None
        sample = Path(tempfile.mkdtemp()) / "texto.txt"
        sample.write_text("El unicornio galopaba cerca del centauro. El unicornio estaba cansado, perro perro.", encoding="utf-8")
        try:
            queue.unlink(missing_ok=True)
            out = self.run_queue("mine", str(sample))
            self.assertEqual(out.returncode, 0, out.stderr)
            rows = [l.split("\t") for l in queue.read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
            words = {r[0]: int(r[1]) for r in rows}
            self.assertEqual(words.get("unicornio"), 2)                 # cuenta repeticiones
            self.assertNotIn("perro", words)                            # ya está en el diccionario
            self.assertNotIn("el", words)                               # palabra funcional
            self.assertIn("centauro", words)
            self.assertEqual(self.run_queue("discard", "centauro").returncode, 0)
            self.assertNotIn("centauro", queue.read_text(encoding="utf-8"))
        finally:
            queue.unlink(missing_ok=True)
            (ROOT / "datos" / "propuestas.tsv").unlink(missing_ok=True)
            if backup is not None:
                queue.write_bytes(backup)


if __name__ == "__main__":
    unittest.main()
