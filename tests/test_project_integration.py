"""Matriz negativa y ejercicios de primer orden por la fachada y la API local."""
import copy
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

from logos import Signature, evaluar
from logos.server import Handler


class ProjectFixtures(unittest.TestCase):
    def test_class_style_first_order_cases(self):
        cases = [
            (Signature(predicates={"P": 1, "Q": 1}),
             {"domain": [0, 1], "predicates": {"P": {"arity": 1, "tuples": [[0]]},
                                                 "Q": {"arity": 1, "tuples": [[0], [1]]}}},
             "∀x (P(x) → Q(x))", True),
            (Signature(predicates={"P": 1, "Q": 1}),
             {"domain": [0, 1], "predicates": {"P": {"arity": 1, "tuples": [[0]]},
                                                 "Q": {"arity": 1, "tuples": [[0], [1]]}}},
             "∀x (Q(x) → P(x))", False),
            (Signature(predicates={"R": 2}),
             {"domain": [0, 1], "predicates": {"R": {"arity": 2, "tuples": [[0, 1], [1, 0]]}}},
             "∀x ∃y R(x, y)", True),
            (Signature(predicates={"R": 2}),
             {"domain": [0, 1], "predicates": {"R": {"arity": 2, "tuples": [[0, 1], [1, 0]]}}},
             "∃y ∀x R(x, y)", False),
            (Signature(constants={"a"}, functions={"f": 1}, predicates={"P": 1}),
             {"domain": [0, 1], "constants": {"a": 0},
              "functions": {"f": {"arity": 1, "table": [[[0], 1], [[1], 0]]}},
              "predicates": {"P": {"arity": 1, "tuples": [[0]]}}},
             "P(f(f(a)))", True),
        ]
        for sig, model, formula, expected in cases:
            with self.subTest(formula=formula):
                result = evaluar(sig, model, formula)
                self.assertEqual(result.status, "ok")
                self.assertIs(result.value, expected)
                self.assertIs(result.explanation.value, expected)

    def test_negative_matrix(self):
        sig = Signature(constants={"a"}, predicates={"P": 1})
        base = {"domain": [0, 1], "constants": {"a": 0},
                "predicates": {"P": {"arity": 1, "tuples": [[0]]}}}
        cases = [
            ("P(", base, None, "expected_term"),
            ("Q(a)", base, None, "undeclared_symbol"),
            ("P(a,a)", base, None, "arity_mismatch"),
            ("P(a)", {**base, "domain": []}, None, "invalid_model"),
            ("P(a)", {**base, "predicates": {"P": {"arity": 1, "tuples": [[2]]}}}, None, "invalid_model"),
            ("P(x)", base, None, "unassigned_variable"),
            ("P(x)", base, {"x": 2}, "invalid_assignment"),
        ]
        for formula, model, env, code in cases:
            with self.subTest(code=code):
                result = evaluar(sig, model, formula, env)
                self.assertEqual(result.status, "invalid_input")
                self.assertIsNone(result.value)
                self.assertIsNone(result.trace)
                self.assertIsNone(result.explanation)
                self.assertEqual(result.errors[0]["code"], code)


class LocalHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        except PermissionError:
            raise unittest.SkipTest("el sandbox no permite abrir puertos locales")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, payload):
        req = Request(self.url + path, json.dumps(payload).encode(),
                      {"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            try:
                return error.code, json.load(error)
            finally:
                error.close()

    def test_serves_ui_and_api(self):
        with urlopen(self.url + "/", timeout=3) as response:
            self.assertIn(b"Evaluador sem", response.read())
        for asset in ("/app.js", "/style.css", "/story3d.js",
                      "/vendor/three.module.js", "/vendor/three.core.js"):
            with urlopen(self.url + asset, timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertTrue(response.read())
        payload = {"signature": {"constants": [], "functions": {}, "predicates": {"P": 1}},
                   "interpretation": {"domain": [0], "predicates": {"P": {"arity": 1, "tuples": [[0]]}}},
                   "formula": "P(x)", "assignment": {"x": 0}}
        status, free = self.request("/api/free", payload)
        self.assertEqual((status, free["variables"]), (200, ["x"]))
        status, result = self.request("/api/evaluate", payload)
        self.assertEqual((status, result["value"]), (200, True))
        self.assertEqual(result["explanation"]["value"], True)
        self.assertEqual(result["story"]["events"][0]["verified_by"], {"trace_path": "0"})
        self.assertEqual(result["model"]["domain"], [0])
        status, validated = self.request("/api/validate", payload)
        self.assertEqual(status, 200)
        self.assertEqual(validated["model"]["domain"], [0])
        bad = copy.deepcopy(payload); bad["assignment"] = {}
        status, result = self.request("/api/evaluate", bad)
        self.assertEqual(status, 400)
        self.assertEqual(result["status"], "invalid_input")
        self.assertNotIn("value", result)

    def test_countermodel_endpoint_and_roundtrip(self):
        sig = {"constants": [], "functions": {}, "predicates": {"P": 1}}
        status, found = self.request("/api/countermodel", {
            "signature": sig, "formula": "∀x P(x)", "max_size": 2})
        self.assertEqual((status, found["status"]), (200, "found"))
        self.assertFalse(found["explanation"]["value"])
        self.assertTrue(found["story"]["events"])
        status, checked = self.request("/api/validate", {
            "signature": sig, "interpretation": found["model"]})
        self.assertEqual(status, 200)
        self.assertEqual(checked["model"], found["model"])
        status, value = self.request("/api/evaluate", {
            "signature": sig, "interpretation": checked["model"], "formula": "∀x P(x)"})
        self.assertEqual((status, value["value"]), (200, False))
        status, unknown = self.request("/api/countermodel", {
            "signature": sig, "formula": "∀x P(x)", "max_size": 1})
        self.assertEqual((status, unknown["status"]), (200, "unknown"))
        self.assertNotIn("model", unknown)

    def test_spanish_readings_require_explicit_choice(self):
        status, result = self.request("/api/spanish", {
            "text": "Todos los estudiantes leyeron un libro"})
        self.assertEqual((status, result["status"]), (200, "ambiguous"))
        self.assertEqual(len(result["readings"]), 2)
        self.assertNotIn("selected", result)
        status, bad = self.request("/api/spanish", {"text": "El estudiante lee"})
        self.assertEqual((status, bad["status"]), (400, "invalid_input"))

    def test_proof_story_only_for_verified_certificate(self):
        status, result = self.request("/api/proof", {
            "premises": ["P → Q", "P"], "conclusion": "Q"})
        self.assertEqual((status, result["status"]), (200, "proved"))
        steps = {step["id"] for step in result["certificate"]["steps"]}
        for event in result["story"]["events"]:
            self.assertEqual(event["verified_by"], {"certificate_step": event["step_id"]})
            self.assertIn(event["step_id"], steps)
            self.assertIsNone(event["value"])
        self.assertEqual([e["line"] for e in result["story"]["events"]], [line["n"] for line in result["fitch"]])
        # Sin prueba no hay narración de prueba: «P ⊬ Q» se refuta con una valuación verificada.
        status, refuted = self.request("/api/proof", {
            "premises": ["P"], "conclusion": "Q"})
        self.assertEqual((status, refuted["status"]), (200, "refuted"))
        self.assertNotIn("story", refuted)


if __name__ == "__main__":
    unittest.main()
