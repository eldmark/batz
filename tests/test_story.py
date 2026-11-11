import dataclasses
import unittest

from logos import FiniteModel, LogosError, build_story, evaluate, parse


class StoryTests(unittest.TestCase):
    def test_events_cite_every_verified_trace_node(self):
        model = FiniteModel([0, 1], predicates={"P": (1, [(0,)])})
        trace = evaluate(model, parse("∀x P(x)"))
        story = build_story(model, trace)
        self.assertEqual([e.trace_path for e in story.events], ["0", "0.0", "0.1"])
        self.assertEqual([e.value for e in story.events], [False, True, False])
        self.assertEqual([e.element for e in story.events], [None, 0, 1])
        self.assertEqual([e.id for e in story.events], [1, 2, 3])
        for event in story.to_dict()["events"]:
            self.assertEqual(event["verified_by"], {"trace_path": event["trace_path"]})
            self.assertTrue(event["text_es"])

    def test_tampered_trace_cannot_be_narrated(self):
        model = FiniteModel([0], predicates={"P": (1, [(0,)])})
        trace = evaluate(model, parse("P(x)"), {"x": 0})
        forged = dataclasses.replace(trace, value=False)
        with self.assertRaises(LogosError) as cm:
            build_story(model, forged)
        self.assertEqual(cm.exception.code, "invalid_trace")


if __name__ == "__main__":
    unittest.main()
