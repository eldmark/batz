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

    def test_inverse_scope_for_any_pair_of_quantifiers(self):
        # ∃ en el sujeto y ∀ en el objeto también tiene dos lecturas, con valores distintos.
        result = translate_spanish("Algún profesor admira a cada estudiante")
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual([r.text for r in result.readings],
                         ["∃x (Profesor(x) ∧ ∀y (Estudiante(y) → Admirar2(x, y)))",
                          "∀y (Estudiante(y) → ∃x (Profesor(x) ∧ Admirar2(x, y)))"])
        model = {"domain": [0, 1, 2, 3], "predicates": {
            "Profesor": {"arity": 1, "tuples": [[0], [1]]},
            "Estudiante": {"arity": 1, "tuples": [[2], [3]]},
            "Admirar2": {"arity": 2, "tuples": [[0, 2], [1, 3]]}}}
        self.assertEqual([evaluar(r.signature, model, r.text).value for r in result.readings], [False, True])
        # Un numeral también cambia de alcance: «al menos dos» estudiantes con el mismo libro o no.
        self.assertEqual(translate_spanish("Al menos dos estudiantes leen un libro").status, "ambiguous")

    def test_equivalent_orders_and_islands_are_not_asked(self):
        # ∀∀ y ∃∃ dicen lo mismo en cualquier orden; «ningún» no reparte su negación.
        for text in ("Todos los estudiantes leyeron todos los libros", "Un estudiante lee un libro",
                     "Ningún estudiante lee un libro", "Juan lee un libro"):
            with self.subTest(text=text):
                self.assertEqual(translate_spanish(text).status, "single")
        # El «un libro» de la relativa es isla: en las dos lecturas queda dentro de la restricción.
        result = translate_spanish("Todo estudiante que lee un libro admira a algún profesor")
        self.assertEqual(len(result.readings), 2)
        for reading in result.readings:
            self.assertIn("Estudiante(x) ∧ ∃z (Libro(z) ∧ Leer2(x, z))", reading.text)

    def test_outside_fragment_rejected(self):
        for text in ("", "El estudiante lee", "Juan lea", "Todos los estudiantes lee", "Juan lee 😊", "Juan, lee"):
            with self.subTest(text=text):
                with self.assertRaises(LogosError) as cm:
                    translate_spanish(text)
                self.assertEqual(cm.exception.code, "unsupported_spanish")

    def test_unknown_word_reports_its_span(self):
        # Desde el etiquetador entrenado, «Juan corre» se acepta declarando el supuesto sobre «corre».
        accepted = translate_spanish("Juan barrita")
        self.assertEqual([a["word"] for a in accepted.assumptions], ["barrita"])
        # Si ni con la categoría propuesta hay análisis, se señala la palabra desconocida.
        with self.assertRaises(LogosError) as cm:
            translate_spanish("Juan barrita los")
        self.assertEqual((cm.exception.span.start, cm.exception.span.end), (5, 12))


if __name__ == "__main__":
    unittest.main()
