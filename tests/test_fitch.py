"""La vista Fitch solo reordena el certificado: cada línea cita lo que el certificado cita."""
import dataclasses
import unittest

from batz import parse
from batz.parser import parse as parse_formula
from batz.proof import ProofError, SearchConfig, prove_text
from batz.proof.fitch import check_layout, fitch_layout
from batz.proof.kalmar import kalmar_prove
from batz.propositional import decide
from proof_corpus import CLASS_KALMAR, CLASS_SEQUENTS, VALID


class FitchLayoutTests(unittest.TestCase):
    def layout(self, premises, conclusion, constants=()):
        result = prove_text(premises, conclusion, constants=constants,
                            config=SearchConfig(max_depth=8, max_nodes=60_000, timeout=5))
        self.assertEqual(result.status, "proved", (premises, conclusion))
        lines = fitch_layout(result.certificate)
        self.assertEqual(check_layout(lines, result.certificate), [], (premises, conclusion))
        return lines, result.certificate

    def test_whole_corpus_lays_out_faithfully(self):
        for premises, conclusion, constants in VALID:
            with self.subTest(sequent=(premises, conclusion)):
                result = prove_text(premises, conclusion, constants=constants,
                                    config=SearchConfig(max_depth=8, max_nodes=60_000, timeout=5))
                if result.status != "proved":
                    continue  # el buscador es incompleto: la vista solo se pide para pruebas
                lines = fitch_layout(result.certificate)
                self.assertEqual(check_layout(lines, result.certificate), [])

    def test_kalmar_certificates_lay_out_faithfully(self):
        # Los certificados de Kalmár son largos y anidan muchas cajas: buena prueba de esfuerzo.
        sequents = [(p, c) for _, p, c in CLASS_SEQUENTS] + [(p, g) for _, _, _, p, g in CLASS_KALMAR]
        for premises, conclusion in sequents:
            with self.subTest(sequent=(premises, conclusion)):
                ps = [parse_formula(p, (), propositional=True) for p in premises]
                c = parse_formula(conclusion, (), propositional=True)
                cert = kalmar_prove(ps, c, max_atoms=8)
                lines = fitch_layout(cert)
                self.assertEqual(check_layout(lines, cert), [])
                self.assertEqual(decide(ps, c).status, "proved")

    def test_discharged_hypothesis_opens_and_closes_a_box(self):
        lines, _ = self.layout([], "¬¬P → P")
        self.assertEqual([(l.n, l.depth, l.rule) for l in lines],
                         [(1, 1, "hyp"), (2, 2, "hyp"), (3, 2, "not_e"), (4, 1, "raa"), (5, 0, "imp_i")])
        self.assertEqual(lines[-1].to_dict()["refs"], ["1–4"])
        self.assertEqual(lines[3].to_dict()["refs"], ["2–3"])
        self.assertEqual(lines[3].label, "RAA")

    def test_universal_introduction_marks_the_new_variable(self):
        lines, _ = self.layout(["∀x (P(x) → Q(x))"], "∀x (¬Q(x) → ¬P(x))")
        flag = next(l for l in lines if l.rule == "flag")
        self.assertTrue(flag.box_start)
        self.assertIsNone(flag.formula)
        # La instancia del universal usa la variable nueva: va dentro de la caja, no antes.
        instance = next(l for l in lines if l.rule == "all_e")
        self.assertEqual(instance.depth, 1)
        self.assertEqual(lines[-1].label, "∀I")

    def test_steps_independent_of_a_box_are_written_before_it(self):
        # P → R no depende de la hipótesis P de la caja de ∨E: se usa desde afuera.
        lines, _ = self.layout(["P ∨ Q", "P → R", "Q → R"], "R")
        self.assertEqual([l.depth for l in lines], [0, 0, 0, 1, 1, 1, 1, 0])
        self.assertEqual(lines[-1].to_dict()["refs"], ["1", "4–5", "6–7"])

    def test_every_certificate_step_has_a_line(self):
        lines, cert = self.layout(["∃x P(x)", "∀x (P(x) → Q(x))"], "∃x Q(x)")
        covered = {s for line in lines for s in line.steps}
        self.assertEqual(covered, {s.id for s in cert.steps})

    def test_forged_certificate_is_not_laid_out(self):
        result = prove_text(["P → Q", "P"], "Q")
        cert = result.certificate
        last = dataclasses.replace(cert.steps[-1], formula=parse("R"))
        with self.assertRaises(ProofError):
            fitch_layout(dataclasses.replace(cert, steps=cert.steps[:-1] + (last,)))

    def test_check_layout_catches_a_wrong_reference(self):
        lines, cert = self.layout(["P → Q", "P"], "Q")
        broken = [dataclasses.replace(l) for l in lines]
        broken[-1].refs = (2, 1)  # al revés: la regla →E cita primero la implicación
        self.assertTrue(check_layout(broken, cert))


if __name__ == "__main__":
    unittest.main()
