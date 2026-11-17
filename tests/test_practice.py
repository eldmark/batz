"""El banco y las entradas del tutor pasan por el checker real."""
import copy
import unittest

from logos.errors import LogosError
from logos.practice import CATEGORIES, EXERCISES, api, build, catalog, step
from logos.server import handle_api


class PracticeTests(unittest.TestCase):
    def test_all_fifty_reference_proofs_and_their_prefixes(self):
        self.assertEqual(len(EXERCISES), 50)
        self.assertEqual([e['id'] for e in EXERCISES], [f'{n:02}' for n in range(1, 51)])
        for ex in EXERCISES:
            with self.subTest(exercise=ex['id']):
                self.assertFalse(build(ex, [])['complete'])
                for n in range(1, len(ex['solution']) + 1):
                    result = build(ex, ex['solution'][:n])
                    self.assertEqual(result['complete'], n == len(ex['solution']))
                    self.assertTrue(all(line['reading'] for line in result['lines']))

    def test_alternative_proof_is_accepted(self):
        # Obtiene Q y reconstruye la conjunción antes de recuperar P.
        moves = [step('Q', 'and_e2', [1]), step('P', 'and_e1', [1]),
                 step('Q ∧ P', 'and_i', [2, 3]), step('P', 'and_e2', [4])]
        self.assertTrue(build(EXERCISES[0], moves)['complete'])

    def test_assuming_the_goal_does_not_win(self):
        for ex in EXERCISES:
            with self.subTest(exercise=ex['id']):
                result = build(ex, [step(ex['goal'], 'assume')])
                self.assertFalse(result['complete'])
                self.assertTrue(result['open_goal'])
                self.assertTrue(result['lines'][-1]['pending'])

    def test_dependency_is_not_erased_by_client_context(self):
        move = step('P', 'assume')
        move['context'] = []  # El cliente no controla el contexto.
        result = build(EXERCISES[0], [move])
        self.assertFalse(result['complete'])
        self.assertEqual(result['lines'][-1]['pending'][0]['formula'], 'P')

    def test_wrong_inference_and_bad_references_rejected(self):
        invalid = [step('Q', 'and_e1', [1]), step('P', 'and_e1', [True]),
                   step('P', 'and_e1', [2]), step('P', 'and_e1', [-1]),
                   step('P', 'and_e1', ['1']), step('P', 'and_e1', [1, 1]),
                   step('P', 'unknown', [1])]
        for move in invalid:
            with self.subTest(move=move), self.assertRaises(LogosError):
                build(EXERCISES[0], [move])

    def test_unknown_symbols_and_wrong_arities_rejected(self):
        for text in ['Z', 'P(a)', 'P ∧', '∀a P(a)']:
            with self.subTest(text=text), self.assertRaises(LogosError):
                build(EXERCISES[0], [step(text, 'assume')])

    def test_universal_cannot_generalize_a_dependent_variable(self):
        moves = [step('P(y)', 'assume'), step('∀x P(x)', 'all_i', [3], var='y')]
        with self.assertRaises(LogosError):
            build(EXERCISES[6], moves)

    def test_equality_template_is_checked(self):
        move = copy.deepcopy(EXERCISES[8]['solution'][0])
        move['params']['template'] = 'P(a)'
        with self.assertRaises(LogosError):
            build(EXERCISES[8], [move])

    def test_disjunction_requires_both_cases(self):
        moves = EXERCISES[16]['solution'][:2]
        moves = moves + [step('R', 'or_e', [1, 5, 5])]
        result = build(EXERCISES[16], moves)
        self.assertFalse(result['complete'])
        self.assertTrue(result['open_goal'])

    def test_catalog_does_not_leak_solutions_and_preview_handles_partial_input(self):
        data = catalog()
        self.assertEqual(len(data['exercises']), 50)
        self.assertTrue(all('solution' not in e and 'hints' not in e for e in data['exercises']))
        self.assertFalse(api('preview', {'exercise':'01', 'formula':'P ∧'})['valid'])
        self.assertTrue(api('preview', {'exercise':'01', 'formula':'P'})['valid'])
        self.assertFalse(api('preview', {'exercise':'01', 'formula':''})['valid'])

    def test_input_limits_and_http_dispatch(self):
        for moves in [None, {}, [step('P','assume')] * 101]:
            with self.assertRaises(LogosError):
                build(EXERCISES[0], moves)
        for data in [{'exercise':'missing'}, {'exercise':'01', 'moves':[None]}]:
            with self.assertRaises(LogosError):
                api('check', data)
        response = handle_api('/api/practice/check', {'exercise':'01', 'moves':EXERCISES[0]['solution']})
        self.assertEqual(response['status'], 'ok')
        self.assertTrue(response['complete'])

    def test_categories_ranges_and_content_are_distinct(self):
        self.assertEqual([c['title'] for c in CATEGORIES], ['Introducción', 'Desafío', 'Modo Leyenda'])
        self.assertEqual([sum(e['category'] == c['id'] for e in EXERCISES) for c in CATEGORIES], [10, 30, 10])
        self.assertEqual(len({e['revision'] for e in EXERCISES}), 50)
        for e in EXERCISES:
            self.assertEqual(len(e['hints']), 3)
            self.assertNotIn(e['goal'], e['premises'])
            if e['category'] == 'introduction':
                self.assertLessEqual(len(e['solution']), 2)
            if e['category'] == 'legend':
                self.assertGreaterEqual(len(e['solution']), 10)
        self.assertEqual(catalog()['total'], 50)
        self.assertEqual(catalog()['categories'], CATEGORIES)

    def test_existential_witness_cannot_escape(self):
        # De ∃x P(x) no se puede elegir libremente P(u) como conclusión.
        ex = EXERCISES[26]
        moves = [step('P(u)', 'assume'), step('P(u)', 'ex_e', [2, 3], var='u')]
        with self.assertRaises(LogosError):
            build(ex, moves)

    def test_final_legend_constructs_its_lemmas(self):
        ex = EXERCISES[-1]
        self.assertEqual(len(ex['premises']), 5)
        self.assertEqual(sum(m['rule'] == 'imp_e' for m in ex['solution']), 3)
        self.assertGreater(len(ex['solution']), 40)
        self.assertTrue(build(ex, ex['solution'])['complete'])


if __name__ == '__main__':
    unittest.main()
