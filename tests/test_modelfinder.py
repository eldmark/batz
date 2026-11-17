"""Buscador de modelos por instanciación: lo que devuelve satisface las fórmulas; None no afirma nada."""
import unittest

from batz import Not, is_true, parse
from batz.countermodels import find_consequence_countermodel
from batz.modelfinder import find_model


def formulas(texts, constants=()):
    return [parse(text, constants) for text in texts]


class FindModel(unittest.TestCase):
    def test_a_found_model_satisfies_every_formula(self):
        cases = [(["∀x ∃y R(x, y)", "¬∃y ∀x R(x, y)"], ()),
                 (["∀x (P(x) → Q(x))", "P(a)", "¬Q(b)"], ("a", "b")),
                 (["∃x ∃y x ≠ y", "∀x ∀y ∀z (x = y ∨ y = z ∨ x = z)"], ()),
                 (["P(a) ↔ ¬P(b)", "∀x (P(x) ∨ Q(x))", "¬∀x Q(x)"], ("a", "b")),
                 (["∀x (R(x, x) → ⊥)", "∃x ∃y (R(x, y) ∧ R(y, x))"], ())]
        for texts, constants in cases:
            with self.subTest(texts=texts):
                fs = formulas(texts, constants)
                model = find_model(fs, constants)
                self.assertIsNotNone(model)
                self.assertTrue(all(is_true(model, f) for f in fs))

    def test_unsatisfiable_or_only_infinite_gives_none(self):
        self.assertIsNone(find_model(formulas(["P(a) ↔ ¬P(a)"], ("a",)), ("a",)))
        self.assertIsNone(find_model(formulas(["∀x (P(x) → Q(x))", "P(a)", "¬Q(a)"], ("a",)), ("a",)))
        # orden estricto sin último elemento: solo tiene modelos infinitos
        serial = ["∀x ¬R(x, x)", "∀x ∃y R(x, y)", "∀x ∀y ∀z (R(x, y) ∧ R(y, z) → R(x, z))"]
        self.assertIsNone(find_model(formulas(serial)))

    def test_distinct_names_are_distinct_individuals_when_possible(self):
        model = find_model(formulas(["P(a)", "Q(b)", "Q(c)"], ("a", "b", "c")), ("a", "b", "c"))
        self.assertEqual(len(set(model.constants.values())), 3)

    def test_names_coincide_only_when_the_formulas_force_it(self):
        fs = formulas(["a = b", "P(a)"], ("a", "b"))
        model = find_model(fs, ("a", "b"))
        self.assertEqual(model.constants["a"], model.constants["b"])
        self.assertTrue(all(is_true(model, f) for f in fs))

    def test_function_symbols_and_open_formulas_are_out_of_scope(self):
        self.assertIsNone(find_model(formulas(["P(f(a))"], ("a",)), ("a",)))
        self.assertIsNone(find_model(formulas(["P(x)"])))

    def test_agrees_with_the_enumeration_on_small_sequents(self):
        sequents = [(["∀x ∃y Ama(x, y)"], "∃y ∀x Ama(x, y)", ()),
                    (["P(a) ∨ Q(a)"], "P(a)", ("a",)),
                    (["∀x (P(x) → Q(x))", "Q(a)"], "P(a)", ("a",)),
                    (["∃x P(x)", "∃x Q(x)"], "∃x (P(x) ∧ Q(x))", ()),
                    (["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", ("a",)),          # válida: ninguno encuentra
                    ([], "∀x (P(x) ∨ ¬P(x))", ())]
        for premises, conclusion, constants in sequents:
            with self.subTest(conclusion=conclusion):
                ps, c = formulas(premises, constants), parse(conclusion, constants)
                enumerated = find_consequence_countermodel(ps, c, constants).status == "found"
                model = find_model([*ps, Not(c)], constants)
                self.assertEqual(model is not None, enumerated)

    def test_many_predicates_do_not_stop_the_search(self):
        # doce predicados: la enumeración completa no pasa del primer tamaño; la instanciación sí
        names = [f"P{i}" for i in range(12)]
        texts = [f"∀x ({a}(x) → {b}(x))" for a, b in zip(names, names[1:])] + ["P0(a)", "¬P0(b)"]
        fs = formulas(texts, ("a", "b"))
        model = find_model([*fs, Not(parse("P11(b)", ("a", "b")))], ("a", "b"))
        self.assertIsNotNone(model)
        self.assertTrue(all(is_true(model, f) for f in fs))
        self.assertFalse(is_true(model, parse("P11(b)", ("a", "b"))))


if __name__ == "__main__":
    unittest.main()
