import dataclasses
import unittest

from batz import parse
from batz.proof import ProofError, prove_text
from batz.proof_story import build_proof_narration


class ProofNarrationTests(unittest.TestCase):
    def test_every_phrase_has_a_verified_certificate_step(self):
        result = prove_text(["P → Q", "P"], "Q")
        self.assertEqual(result.status, "proved")
        story = build_proof_narration(result.certificate).to_dict()
        self.assertEqual(story["kind"], "proof")
        ids = {s.id for s in result.certificate.steps}
        for event in story["events"]:
            self.assertEqual(event["verified_by"], {"certificate_step": event["step_id"]})
            self.assertIn(event["step_id"], ids)
            self.assertIsNone(event["value"])
            self.assertTrue(event["text_es"])
        # Toda la prueba queda narrada, en el orden y con los números de la vista Fitch.
        self.assertEqual({s for e in story["events"] for s in e["steps"]}, ids)
        self.assertEqual([e["line"] for e in story["events"]], [line["n"] for line in story["fitch"]])

    def test_boxes_are_narrated_with_fitch_line_numbers(self):
        result = prove_text([], "¬¬P → P")
        events = build_proof_narration(result.certificate).to_dict()["events"]
        self.assertEqual(events[0]["text_es"], "Suponemos ¬¬P y abrimos una caja; al cerrarla, esa hipótesis se descarga.")
        self.assertEqual(events[-1]["text_es"], "Cerramos la caja 1–4: por introducción de implicación obtenemos ¬¬P → P.")
        self.assertEqual(events[3]["context"], ["¬¬P"])

    def test_forged_certificate_is_not_narrated(self):
        result = prove_text(["P → Q", "P"], "Q")
        cert = result.certificate
        last = dataclasses.replace(cert.steps[-1], formula=parse("R"))
        forged = dataclasses.replace(cert, steps=cert.steps[:-1] + (last,))
        with self.assertRaises(ProofError):
            build_proof_narration(forged)


if __name__ == "__main__":
    unittest.main()
