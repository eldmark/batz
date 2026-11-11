import dataclasses
import unittest

from logos import parse
from logos.proof import ProofError, prove_text
from logos.proof_story import build_proof_narration


class ProofNarrationTests(unittest.TestCase):
    def test_every_phrase_has_a_verified_certificate_step(self):
        result = prove_text(["P → Q", "P"], "Q")
        self.assertEqual(result.status, "proved")
        story = build_proof_narration(result.certificate).to_dict()
        self.assertEqual(story["kind"], "proof")
        self.assertEqual(len(story["events"]), len(result.certificate.steps))
        for event in story["events"]:
            self.assertEqual(event["verified_by"], {"certificate_step": event["step_id"]})
            self.assertIsNone(event["value"])
            self.assertTrue(event["text_es"])

    def test_forged_certificate_is_not_narrated(self):
        result = prove_text(["P → Q", "P"], "Q")
        cert = result.certificate
        last = dataclasses.replace(cert.steps[-1], formula=parse("R"))
        forged = dataclasses.replace(cert, steps=cert.steps[:-1] + (last,))
        with self.assertRaises(ProofError):
            build_proof_narration(forged)


if __name__ == "__main__":
    unittest.main()
