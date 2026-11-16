"""Predicados automáticos: diminutivos y participios se deducen del diccionario, sin guardarse."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ["LOGOS_LEXICON"] = str(Path(tempfile.mkdtemp()) / "lexico_usuario.tsv")

from logos import lexicon, translate_spanish
from logos.lexicon import _derived, _read


class Derived(unittest.TestCase):
    def test_diminutive_shares_the_symbol_of_its_word(self):
        for phrase, formula in [("Todo perrito ladra", "∀x (Perro(x) → Ladrar(x))"),
                                ("Toda casita es grande", "∀x (Casa(x) → Grande(x))"),
                                ("Algún amiguito duerme", "∃x (Amigo(x) ∧ Dormir(x))")]:
            with self.subTest(phrase=phrase):
                self.assertIn(formula, [r.text for r in translate_spanish(phrase).readings])

    def test_diminutive_spelling(self):
        names = {e.lemma: e.options()["dim"] for e in lexicon.entries() if e.options().get("dim")}
        self.assertEqual(names["tacita"], "taza")        # z → c
        self.assertEqual(names["amiguito"], "amigo")     # g → gu
        self.assertEqual(names["perrito"], "perro")
        for bad in ("gimnasiito", "mosquitito", "dita", "problemita"):
            self.assertNotIn(bad, names)

    def test_participles_become_adjectives_with_their_own_symbol(self):
        self.assertEqual([r.text for r in translate_spanish("Todo libro leído es útil").readings], ["∀x (Libro(x) ∧ Leido(x) → Util(x))"])
        self.assertEqual([r.text for r in translate_spanish("Toda frase escrita es larga").readings], ["∀x (Frase(x) ∧ Escrito(x) → Largo(x))"])
        sym = {e.lemma: e.symbol for e in lexicon.entries() if e.options().get("part")}
        self.assertEqual(sym["leído"], "Leido")
        self.assertEqual(sym["escrito"], "Escrito")
        self.assertEqual(sym["hecho"], "Hecho")
        self.assertEqual(sym["comprado"], "Comprado")

    def test_a_word_the_dictionary_already_has_is_not_duplicated(self):
        derived = {e.lemma for e in lexicon.entries() if e.source == "auto"}
        for word in ("cansado", "abierto", "cerrado", "mosquito"):
            self.assertNotIn(word, derived)
        forms = [f for e in lexicon.entries() if e.category == "ADJ" and not e.options().get("sentido") for tag in ("Adj_MS",) for f in e.forms().get(tag, [])]
        self.assertEqual(len(forms), len(set(forms)), "un adjetivo aparece dos veces")

    def test_derived_entries_are_not_stored_or_removable(self):
        base_lines = [l for l in lexicon.BASE.read_text(encoding="utf-8").splitlines() if l.startswith("perrito")]
        self.assertEqual(base_lines, [])
        self.assertFalse(lexicon.remove("perrito", "N"))
        self.assertGreater(lexicon.counts()["auto"], 1000)

    def test_derivation_is_deterministic(self):
        base = _read(lexicon.BASE, "base")
        self.assertEqual([e.lemma for e in _derived(base)], [e.lemma for e in _derived(base)])


if __name__ == "__main__":
    unittest.main()
