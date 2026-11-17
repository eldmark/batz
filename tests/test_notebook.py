"""Cuadernos: oraciones con cita, lecturas que elige la persona y preguntas con prueba o contramodelo."""
import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ["LOGOS_LEXICON"] = str(Path(tempfile.mkdtemp()) / "lexico_usuario.tsv")
os.environ["LOGOS_NOTEBOOKS"] = tempfile.mkdtemp()

from logos import FiniteModel, LogosError, is_true, parse
from logos import notebook
from logos.server import handle_api

CLASS = """Apuntes de la clase.
- Todo estudiante que estudia aprueba.
- Juan es un estudiante. Juan estudia.
María es una estudiante; Pedro es un profesor.
Ningún profesor estudia.
Todos los estudiantes leen un libro.
El examen fue difícil para muchos.
¿Quién aprueba?
"""
SOCRATES = "Todos los hombres son mortales. Sócrates es un hombre."


def call(action, **data):
    return handle_api("/api/notebook/" + action, data)


def new_notebook(*sources):
    book = call("create", title="Prueba")["notebook"]
    for title, text in sources:
        book = call("source-add", id=book["id"], title=title, text=text)["notebook"]
    return book


def sentence_text(source, sentence):
    start, end = sentence["span"]
    return source["text"][start:end]


class Sentences(unittest.TestCase):
    def test_split_keeps_offsets_and_skips_list_markers(self):
        text = "- Juan lee. María estudia;\n2) Pedro escribe\n\n   ...\nAna duerme!"
        pieces = [text[a:b] for a, b in notebook.split_sentences(text)]
        self.assertEqual(pieces, ["Juan lee.", "María estudia;", "Pedro escribe", "Ana duerme!"])

    def test_each_sentence_is_premise_pending_or_rejected(self):
        source = new_notebook(("Apuntes", CLASS))["sources"][0]
        status = {sentence_text(source, s): s["status"] for s in source["sentences"]}
        self.assertEqual(status["Todo estudiante que estudia aprueba."], "premise")
        self.assertEqual(status["María es una estudiante;"], "premise")
        self.assertEqual(status["Todos los estudiantes leen un libro."], "choose")   # dos alcances: decide la persona
        self.assertEqual(status["El examen fue difícil para muchos."], "rejected")
        self.assertEqual(status["¿Quién aprueba?"], "rejected")
        self.assertEqual(source["counts"], {"premises": 6, "choose": 1, "rejected": 3})

    def test_rejection_points_at_the_word_in_the_source(self):
        source = new_notebook(("Apuntes", "Juan estudia.\nJuan xyzzea mucho."))["sources"][0]
        error = source["sentences"][1]["error"]
        self.assertEqual(source["text"][error["span"][0]:error["span"][1]], error["word"])
        self.assertIn(error["word"], "Juan xyzzea mucho.")

    def test_a_guessed_word_waits_for_confirmation(self):
        source = new_notebook(("Apuntes", "Todos los xilófonos zumban."))["sources"][0]
        sentence = source["sentences"][0]
        if sentence["status"] == "rejected":
            self.skipTest("sin etiquetador: la palabra desconocida se rechaza")
        self.assertEqual(sentence["status"], "choose")
        self.assertTrue(sentence["assumptions"])


class Questions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = new_notebook(("Apuntes", CLASS), ("Clásico", SOCRATES))
        cls.id = cls.book["id"]

    def ask(self, question, **extra):
        return call("ask", id=self.id, question=question, log=False, **extra)

    def test_follows_with_a_proof_that_cites_only_what_it_uses(self):
        result = self.ask("¿Juan aprueba?")
        self.assertEqual(result["answer"], "follows")
        self.assertEqual([c["cites"][0]["text"] for c in result["cited"]],
                         ["Todo estudiante que estudia aprueba.", "Juan es un estudiante.", "Juan estudia."])
        self.assertTrue(all(c["cites"][0]["title"] == "Apuntes" for c in result["cited"]))
        self.assertFalse(result["inconsistent"])
        fitch = result["proof"]["fitch"]
        cited = {line["formula"]: line.get("cite") for line in fitch if line["rule"] == "premise"}
        self.assertEqual(cited, {c["formula"]: c["n"] for c in result["cited"]})
        self.assertEqual(fitch[-1]["formula"], "Aprobar(juan)")
        self.assertEqual(result["proof"]["contrast"]["verdict"], "consistent")

    def test_a_citation_leads_back_to_its_sentence(self):
        result = self.ask("¿Es verdad que Sócrates es mortal?")
        by_id = {source["id"]: source for source in self.book["sources"]}
        for premise in result["cited"]:
            for cite in premise["cites"]:
                source = by_id[cite["source"]]
                sentence = source["sentences"][cite["sentence"]]
                self.assertEqual(sentence_text(source, sentence), cite["text"])
                self.assertEqual(sentence["formula"], premise["formula"])

    def test_contradicts_when_the_negation_is_proved(self):
        result = self.ask("¿Se sigue que Pedro estudia?")
        self.assertEqual(result["answer"], "contradicts")
        self.assertEqual(result["proof"]["goal"], "¬Estudiar(pedro)")
        self.assertEqual({c["cites"][0]["text"] for c in result["cited"]},
                         {"Ningún profesor estudia.", "Pedro es un profesor."})

    def test_undecided_shows_a_model_of_each_side(self):
        result = self.ask("¿María aprueba?")
        self.assertEqual(result["answer"], "undecided")
        goal = parse("Aprobar(maria)", ("maria",))
        for key, expected in (("countermodel", False), ("witness", True)):
            found = result[key]
            model = FiniteModel.from_dict(found["model"])
            constants = found["signature"]["constants"]
            self.assertTrue(all(p["value"] for p in found["premises"]))
            self.assertEqual(len(found["premises"]), result["premise_count"])
            self.assertTrue(all(is_true(model, parse(p["formula"], constants)) for p in found["premises"]))
            self.assertEqual(is_true(model, goal), expected)
        # cada individuo lleva el nombre que lo denota
        self.assertEqual(result["countermodel"]["model"]["constants"]["maria"], "maria")

    def test_a_symbol_the_sources_never_mention_is_reported(self):
        result = self.ask("¿Sócrates estudia?")
        self.assertEqual(result["answer"], "undecided")
        self.assertEqual(result["new_symbols"], [])
        result = self.ask("¿Sócrates duerme?")
        self.assertEqual(result["new_symbols"], ["Dormir"])

    def test_an_ambiguous_question_waits_for_the_reading(self):
        result = self.ask("Juan es joven")
        self.assertEqual(result["answer"], "choose")
        self.assertEqual(len(result["readings"]), 2)
        chosen = self.ask("Juan es joven", formula=result["readings"][1]["formula"])
        self.assertEqual(chosen["conclusion"]["formula"], result["readings"][1]["formula"])
        self.assertEqual(chosen["answer"], "undecided")

    def test_a_question_outside_the_grammar_is_an_error(self):
        with self.assertRaises(LogosError):
            self.ask("¿Aprueba Juan?")

    def test_question_lead_ins_are_dropped(self):
        for question in ("¿Se sigue que Juan aprueba?", "¿es verdad que juan aprueba?", "Entonces, Juan aprueba.",
                         "¿Se deduce de las fuentes que Juan aprueba?"):
            self.assertEqual(notebook.question_statement(question).casefold(), "juan aprueba")
        self.assertEqual(notebook.question_statement("¿Juan aprueba?"), "Juan aprueba")


class Choices(unittest.TestCase):
    def test_an_ambiguous_sentence_is_used_only_after_choosing(self):
        book = new_notebook(("Apuntes", CLASS))
        ask = lambda: call("ask", id=book["id"], question="¿Juan lee un libro?")
        self.assertEqual(ask()["answer"], "undecided")
        self.assertEqual(ask()["counts"]["choose"], 1)
        source = book["sources"][0]
        pending = next(s for s in source["sentences"] if s["status"] == "choose")
        book = call("choose", id=book["id"], source=source["id"], sentence=pending["i"],
                    formula=pending["readings"][0]["formula"])["notebook"]
        self.assertEqual(book["sources"][0]["sentences"][pending["i"]]["status"], "premise")
        self.assertEqual([turn["answer"] for turn in book["chat"]], [""])   # el veredicto guardado ya no vale
        result = ask()
        self.assertEqual(result["answer"], "follows")
        self.assertIn("Todos los estudiantes leen un libro.", [c["cites"][0]["text"] for c in result["cited"]])
        # deshacer la elección la saca otra vez
        book = call("choose", id=book["id"], source=source["id"], sentence=pending["i"], formula=None)["notebook"]
        self.assertEqual(book["sources"][0]["sentences"][pending["i"]]["status"], "choose")
        with self.assertRaises(LogosError):
            call("choose", id=book["id"], source=source["id"], sentence=pending["i"], formula="P(a)")

    def test_a_disabled_source_is_not_used(self):
        book = new_notebook(("Clásico", SOCRATES))
        self.assertEqual(call("ask", id=book["id"], question="Sócrates es mortal")["answer"], "follows")
        call("source-toggle", id=book["id"], source="f1", enabled=False)
        self.assertEqual(call("ask", id=book["id"], question="Sócrates es mortal")["answer"], "empty")

    def test_contradictory_sources_are_flagged(self):
        book = new_notebook(("A", "Juan estudia."), ("B", "Juan no estudia."))
        result = call("ask", id=book["id"], question="¿Juan estudia?")
        self.assertEqual(result["answer"], "follows")
        self.assertTrue(result["inconsistent"])

    def test_the_same_statement_in_two_sources_cites_both(self):
        book = new_notebook(("A", "Juan estudia."), ("B", "Ana lee. Juan estudia."))
        result = call("ask", id=book["id"], question="¿Juan estudia?")
        self.assertEqual([(c["title"], c["sentence"]) for c in result["cited"][0]["cites"]], [("A", 0), ("B", 1)])

    def test_irrelevant_premises_do_not_hide_the_proof(self):
        names = ["Ana", "Luis", "Carlos", "Lucía", "Marta", "Pablo", "Elena", "Diego"]
        verbs = ["lee", "escribe", "duerme", "corre"]
        noise = " ".join(f"{name} {verb}." for name in names for verb in verbs)
        book = new_notebook(("Ruido", noise), ("Clásico", SOCRATES))
        start = time.monotonic()
        result = call("ask", id=book["id"], question="¿Sócrates es mortal?")
        self.assertEqual(result["answer"], "follows")
        self.assertEqual(result["premise_count"], 34)
        self.assertEqual(len(result["cited"]), 2)
        self.assertLess(time.monotonic() - start, 15)


class Storage(unittest.TestCase):
    def test_export_and_import_keep_sources_and_choices(self):
        book = new_notebook(("Apuntes", CLASS))
        source = book["sources"][0]
        pending = next(s for s in source["sentences"] if s["status"] == "choose")
        call("choose", id=book["id"], source="f1", sentence=pending["i"], formula=pending["readings"][1]["formula"])
        package = call("export", id=book["id"])["notebook"]
        copy = call("import", notebook=package)["notebook"]
        self.assertNotEqual(copy["id"], book["id"])
        self.assertEqual(copy["sources"][0]["text"], source["text"])
        self.assertEqual(copy["sources"][0]["sentences"][pending["i"]]["formula"], pending["readings"][1]["formula"])

    def test_source_ids_survive_removals(self):
        book = new_notebook(("A", "Juan lee."), ("B", "Ana lee."))
        book = call("source-remove", id=book["id"], source="f1")["notebook"]
        self.assertEqual([s["id"] for s in call("get", id=book["id"])["notebook"]["sources"]], ["f2"])
        book = call("source-add", id=book["id"], title="C", text="Luis lee.")["notebook"]
        self.assertEqual([s["id"] for s in book["sources"]], ["f2", "f3"])

    def test_history_keeps_one_turn_per_question(self):
        book = new_notebook(("Clásico", SOCRATES))
        for _ in range(2):
            call("ask", id=book["id"], question="¿Sócrates es mortal?")
        call("ask", id=book["id"], question="¿Sócrates es un hombre?")
        chat = call("get", id=book["id"])["notebook"]["chat"]
        self.assertEqual([(t["question"], t["answer"]) for t in chat],
                         [("¿Sócrates es mortal?", "follows"), ("¿Sócrates es un hombre?", "follows")])
        self.assertEqual(call("clear-chat", id=book["id"])["notebook"]["chat"], [])

    def test_rename_list_and_delete(self):
        book = new_notebook()
        call("rename", id=book["id"], title="  Semana   3 ")
        self.assertIn((book["id"], "Semana 3"), [(n["id"], n["title"]) for n in call("list")["notebooks"]])
        call("delete", id=book["id"])
        self.assertNotIn(book["id"], [n["id"] for n in call("list")["notebooks"]])
        with self.assertRaises(LogosError):
            call("get", id=book["id"])

    def test_invalid_input_is_rejected(self):
        book = new_notebook()
        for bad_id in ("../secreto", "c123", 7, None, "c00000000000g"):
            with self.subTest(id=bad_id), self.assertRaises(LogosError):
                call("get", id=bad_id)
        for text in ("", "   ", "…", "x" * (notebook.MAX_TEXT + 1), None):
            with self.subTest(text=str(text)[:10]), self.assertRaises(LogosError):
                call("source-add", id=book["id"], title="A", text=text)
        for package in (None, [], {"sources": "no"}, {"sources": [{"title": "A"}]}):
            with self.subTest(package=package), self.assertRaises(LogosError):
                call("import", notebook=package)
        with self.assertRaises(LogosError):
            call("no-existe", id=book["id"])
        with self.assertRaises(LogosError):
            call("source-remove", id=book["id"], source="f9")
        self.assertEqual(len(list(notebook.folder().glob("*.tmp"))), 0)


if __name__ == "__main__":
    unittest.main()
