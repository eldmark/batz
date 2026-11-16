"""Diccionario: flexión, lemas de verbos irregulares, género, altas del usuario y la frase del condicional."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ["LOGOS_LEXICON"] = str(Path(tempfile.mkdtemp()) / "lexico_usuario.tsv")

from logos import LogosError, lexicon, translate_spanish
from logos.lexicon import Entry, conjugate, feminine, plural
from logos.server import handle_api


class Inflection(unittest.TestCase):
    def test_plural_and_feminine(self):
        for word, expected in [("perro", "perros"), ("flor", "flores"), ("luz", "luces"), ("león", "leones"),
                               ("canción", "canciones"), ("país", "países"), ("rey", "reyes"), ("café", "cafés"), ("inglés", "ingleses")]:
            self.assertEqual(plural(word), expected)
        for word, expected in [("alto", "alta"), ("trabajador", "trabajadora"), ("inglés", "inglesa"), ("alemán", "alemana"),
                               ("español", "española"), ("mortal", "mortal"), ("feliz", "feliz"), ("valiente", "valiente")]:
            self.assertEqual(feminine(word), expected)

    def test_regular_and_orthographic_verbs(self):
        self.assertEqual(conjugate("cantar"), ("canta", "cantan", "cante", "canten", "cantó", "cantaron"))
        self.assertEqual(conjugate("comer"), ("come", "comen", "coma", "coman", "comió", "comieron"))
        self.assertEqual(conjugate("buscar")[2:4], ("busque", "busquen"))
        self.assertEqual(conjugate("pagar")[2], "pague")
        self.assertEqual(conjugate("cruzar")[2], "cruce")
        self.assertEqual(conjugate("proteger")[2], "proteja")
        self.assertEqual(conjugate("crecer")[2], "crezca")
        self.assertEqual(conjugate("construir"), ("construye", "construyen", "construya", "construyan", "construyó", "construyeron"))
        self.assertEqual(conjugate("leer")[4:], ("leyó", "leyeron"))

    def test_stem_changing_verbs(self):
        self.assertEqual(conjugate("dormir", {"cambio": "ue"}), ("duerme", "duermen", "duerma", "duerman", "durmió", "durmieron"))
        self.assertEqual(conjugate("pensar", {"cambio": "ie"})[:3], ("piensa", "piensan", "piense"))
        self.assertEqual(conjugate("pedir", {"cambio": "i"}), ("pide", "piden", "pida", "pidan", "pidió", "pidieron"))
        self.assertEqual(conjugate("seguir", {"cambio": "i"})[:3], ("sigue", "siguen", "siga"))
        self.assertEqual(conjugate("volver", {"cambio": "ue"})[4], "volvió")      # los -er no cambian en pasado

    def test_every_base_entry_inflects(self):
        self.assertGreater(lexicon.counts()["total"], 1400)
        for entry in lexicon.entries():
            forms = entry.forms()
            self.assertTrue(forms and all(f.isalpha() for values in forms.values() for f in values), entry.lemma)


class Lemmas(unittest.TestCase):
    def test_irregular_forms_reach_their_infinitive(self):
        for form, symbol in [("duermen", "Dormir"), ("quiso", "Querer"), ("tuvieron", "Tener"), ("vuelan", "Volar"),
                             ("mienten", "Mentir"), ("dijo", "Decir"), ("hizo", "Hacer"), ("persigue", "Perseguir"),
                             ("conozcan", "Conocer"), ("fueron", "Ir"), ("ríen", "Reir")]:
            with self.subTest(form=form):
                self.assertEqual(lexicon.symbol("V", form), symbol)

    def test_noun_gender_comes_from_the_dictionary(self):
        tags = lambda w: {t for e in lexicon.find(w) if e.category == "N" for t in e.forms()}
        self.assertEqual(tags("problema"), {"N_MS", "N_MP"})     # masculino aunque acabe en -a
        self.assertEqual(tags("mano"), {"N_FS", "N_FP"})         # femenino aunque acabe en -o
        self.assertEqual(tags("artista"), {"N_MS", "N_MP", "N_FS", "N_FP"})

    def test_sentences_use_real_lemmas_without_assumptions(self):
        for phrase, formula in [("Algún gato duerme", "∃x (Gato(x) ∧ Dormir(x))"),
                                ("Todos los hombres son mortales", "∀x (Hombre(x) → Mortal(x))"),
                                ("Ningún problema es fácil", "¬∃x (Problema(x) ∧ Facil(x))"),
                                ("Toda mano es pequeña", "∀x (Mano(x) → Pequeño(x))")]:
            with self.subTest(phrase=phrase):
                result = translate_spanish(phrase)
                self.assertEqual(result.assumptions, ())
                self.assertIn(formula, [r.text for r in result.readings])


class ConditionalWithImplicitSubject(unittest.TestCase):
    def test_indefinite_subject_is_general(self):
        for phrase in ("Si una persona es humana, entonces es mortal", "si una persona es humana entonces es mortal",
                       "Si una persona es humana, es mortal"):
            self.assertEqual([r.text for r in translate_spanish(phrase).readings], ["∀x (Persona(x) ∧ Humano(x) → Mortal(x))"])

    def test_proper_name_subject_is_an_implication(self):
        self.assertEqual([r.text for r in translate_spanish("Si Juan estudia, aprueba").readings], ["Estudiar(juan) → Aprobar(juan)"])

    def test_gender_disagreement_suggests_the_fix(self):
        with self.assertRaises(LogosError) as ctx:
            translate_spanish("si una persona es humano entonces es mortal")
        self.assertIn("humana", ctx.exception.message)
        self.assertEqual((ctx.exception.span.start, ctx.exception.span.end), (18, 24))
        with self.assertRaises(LogosError) as ctx:
            translate_spanish("María es alto")                 # la especificación sigue rechazándola
        self.assertIn("alta", ctx.exception.message)

    def test_bare_article_explains_itself(self):
        with self.assertRaises(LogosError) as ctx:
            translate_spanish("Los políticos mienten")
        self.assertIn("todos los", ctx.exception.message)


class UserWords(unittest.TestCase):
    def tearDown(self):
        path = lexicon.user_path()
        if path.is_file():
            path.unlink()
        lexicon.reload()

    def test_add_use_and_remove(self):
        before = translate_spanish("Todos los tlacuaches barritan")
        self.assertEqual(len(before.assumptions), 2)
        handle_api("/api/lexicon/add", {"lemma": "tlacuache", "category": "N", "feature": "M"})
        handle_api("/api/lexicon/add", {"lemma": "barritar", "category": "V", "feature": "I"})
        after = translate_spanish("Todos los tlacuaches barritan")
        self.assertEqual(after.assumptions, ())
        self.assertEqual(after.readings[0].text, "∀x (Tlacuache(x) → Barritar(x))")
        found = handle_api("/api/lexicon/search", {"query": "barrit"})
        self.assertEqual([(e["lemma"], e["source"]) for e in found["entries"]], [("barritar", "usuario")])
        self.assertTrue(handle_api("/api/lexicon/remove", {"lemma": "barritar", "category": "V"})["removed"])
        self.assertEqual([a["word"] for a in translate_spanish("Todos los tlacuaches barritan").assumptions], ["barritan"])

    def test_irregular_user_verb(self):
        handle_api("/api/lexicon/add", {"lemma": "caber", "category": "V", "feature": "I",
                                        "extra": "formas=cabe,caben,quepa,quepan,cupo,cupieron"})
        self.assertEqual(lexicon.symbol("V", "cupieron"), "Caber")

    def test_invalid_and_duplicate_entries_are_rejected(self):
        for payload in [{"lemma": "dos palabras", "category": "N", "feature": "M"}, {"lemma": "gato3", "category": "N", "feature": "M"},
                        {"lemma": "saltarín", "category": "V", "feature": "I"}, {"lemma": "mesa", "category": "N", "feature": ""},
                        {"lemma": "correr", "category": "V", "feature": "I", "extra": "formas=a,b"},
                        {"lemma": "perro", "category": "N", "feature": "M"}]:
            with self.subTest(payload=payload):
                with self.assertRaises(LogosError):
                    handle_api("/api/lexicon/add", payload)
        self.assertFalse(lexicon.user_path().is_file())

    def test_suggest_uses_the_model_only_for_unknown_words(self):
        known = handle_api("/api/lexicon/suggest", {"word": "duermen"})
        self.assertEqual((known["found"][0]["lemma"], known["proposal"]), ("dormir", None))
        unknown = handle_api("/api/lexicon/suggest", {"word": "barritan"})
        self.assertEqual((unknown["found"], unknown["proposal"]["category"], unknown["proposal"]["lemma"]), ([], "V", "barritar"))


if __name__ == "__main__":
    unittest.main()
