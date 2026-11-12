import unittest

from logos import LogosError, evaluar, parse_checked, translate_spanish


class ControlledSpanish(unittest.TestCase):
    def test_single_readings_are_well_formed(self):
        cases = [
            ("Juan lee.", "Leer(juan)"),
            ("Juan no lee", "¬Leer(juan)"),
            ("Todo estudiante lee", "∀x (Estudiante(x) → Leer(x))"),
            ("Todos los estudiantes leen", "∀x (Estudiante(x) → Leer(x))"),
            ("Algún estudiante lee", "∃x (Estudiante(x) ∧ Leer(x))"),
            ("Ningún estudiante lee", "¬∃x (Estudiante(x) ∧ Leer(x))"),
            ("Juan es Pedro", "juan = pedro"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                result = translate_spanish(text)
                self.assertEqual(result.status, "single")
                reading = result.readings[0]
                self.assertEqual(reading.text, expected)
                self.assertEqual(reading.formula, parse_checked(expected, reading.signature, strict=True))

    def test_ambiguity_is_never_chosen(self):
        for text in ("Juan es joven", "Todos los estudiantes leyeron un libro"):
            with self.subTest(text=text):
                result = translate_spanish(text)
                self.assertEqual(result.status, "ambiguous")
                self.assertEqual(len(result.readings), 2)
                self.assertNotEqual(result.readings[0].text, result.readings[1].text)
                self.assertEqual([r.id for r in result.readings], ["r1", "r2"])

    def test_scope_readings_can_have_different_values(self):
        result = translate_spanish("Todos los estudiantes leyeron un libro")
        model = {"domain": [0, 1], "predicates": {
            "Estudiante": {"arity": 1, "tuples": [[0], [1]]},
            "Libro": {"arity": 1, "tuples": [[0], [1]]},
            "Leer2": {"arity": 2, "tuples": [[0, 0], [1, 1]]}}}
        self.assertEqual([evaluar(r.signature, model, r.text).value for r in result.readings],
                         [True, False])

    def test_outside_fragment_rejected(self):
        for text in ("", "El estudiante lee", "Juan lea", "Todos los estudiantes lee", "Juan lee 😊", "Juan, lee"):
            with self.subTest(text=text):
                with self.assertRaises(LogosError) as cm:
                    translate_spanish(text)
                self.assertEqual(cm.exception.code, "unsupported_spanish")

    def test_unknown_word_reports_its_span(self):
        # Desde el etiquetador entrenado, «Juan corre» se acepta declarando el supuesto sobre «corre».
        accepted = translate_spanish("Juan corre")
        self.assertEqual([a["word"] for a in accepted.assumptions], ["corre"])
        # Si ni con la categoría propuesta hay análisis, se señala la palabra desconocida.
        with self.assertRaises(LogosError) as cm:
            translate_spanish("Juan corre los")
        self.assertEqual((cm.exception.span.start, cm.exception.span.end), (5, 10))


if __name__ == "__main__":
    unittest.main()
