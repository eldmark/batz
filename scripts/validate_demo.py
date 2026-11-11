"""Ensayo local reproducible de LOGOS MM3032.

Ejecutar con PYTHONPATH=src python3 scripts/validate_demo.py --seed 20261102.
Solo usa HTTP local y la biblioteca estándar.
"""
from __future__ import annotations

import argparse
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import random
import statistics
import threading
import sys
from time import perf_counter
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from logos.server import Handler


class QuietHandler(Handler):
    def log_message(self, format, *args):
        pass


def source_digest():
    root = Path(__file__).resolve().parents[1]
    paths = [p for p in (root / "src" / "logos").rglob("*")
             if p.is_file() and p.suffix in {".py", ".js", ".css", ".html"}]
    paths.append(Path(__file__).resolve())
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def request(url, path, payload=None):
    if payload is None:
        with urlopen(url + path, timeout=10) as response:
            return response.status, response.read()
    req = Request(url + path, json.dumps(payload).encode(),
                  {"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        try:
            return error.code, json.load(error)
        finally:
            error.close()


def generate_formulas(rng, count):
    atoms = ["P(a)", "P(b)", "Q(a)", "Q(b)", "∀x P(x)", "∃x Q(x)",
             "∀x (P(x) → Q(x))", "∃x (P(x) ∧ Q(x))"]
    formulas = []
    for _ in range(count):
        a, b = rng.sample(atoms, 2)
        op = rng.choice(["∧", "∨", "→", "↔"])
        formulas.append(f"({a}) {op} ({b})")
    return formulas


def run(seed):
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        # Esta interpretación es distinta del ejemplo cargado por la UI.
        signature = {"constants": ["a", "b"], "functions": {},
                     "predicates": {"P": 1, "Q": 1}}
        model = {"domain": [0, 1, 2], "constants": {"a": 0, "b": 2},
                 "predicates": {"P": {"arity": 1, "tuples": [[0], [2]]},
                                "Q": {"arity": 1, "tuples": [[1], [2]]}}}
        for path, marker in (("/", b"LOGOS"), ("/app.js", b"searchCountermodel"),
                             ("/style.css", b".card"), ("/story3d.js", b"createStoryScene"),
                             ("/vendor/three.module.js", b"three.core.js"),
                             ("/vendor/three.core.js", b"Vector3")):
            status, body = request(url, path)
            assert status == 200 and marker in body, path
        html = request(url, "/")[1].decode()
        assert "https://" not in html and "http://" not in html

        status, checked = request(url, "/api/validate", {
            "signature": signature, "interpretation": model})
        assert status == 200 and checked["status"] == "ok"
        canonical = checked["model"]

        rng = random.Random(seed)
        formulas = generate_formulas(rng, 12)
        samples = []
        for formula in formulas:
            status, result = request(url, "/api/evaluate", {
                "signature": signature, "interpretation": canonical, "formula": formula})
            assert status == 200 and result["status"] == "ok", (formula, result)
            assert result["value"] is result["explanation"]["value"]
            assert result["story"]["events"] and result["story"]["events"][0]["trace_path"] == "0"
            assert all(event["verified_by"] == {"trace_path": event["trace_path"]}
                       for event in result["story"]["events"])
            samples.append({"formula": formula, "value": result["value"]})

        invalid_cases = [
            ("P(a,a)", canonical, "arity_mismatch"),
            ("P(x)", canonical, "unassigned_variable"),
            ("Q(a)", {**canonical, "predicates": {**canonical["predicates"],
                                                   "Q": {"arity": 1, "tuples": []}}}, "invalid_model"),
        ]
        for formula, interpretation, code in invalid_cases:
            status, result = request(url, "/api/evaluate", {
                "signature": signature, "interpretation": interpretation, "formula": formula})
            assert status == 400 and result["status"] == "invalid_input"
            assert result["errors"][0]["code"] == code and "value" not in result

        simple = {"constants": [], "functions": {}, "predicates": {"P": 1}}
        status, found = request(url, "/api/countermodel", {
            "signature": simple, "formula": "∀x P(x)", "max_size": 2})
        assert status == 200 and found["status"] == "found"
        status, rechecked = request(url, "/api/evaluate", {
            "signature": simple, "interpretation": found["model"], "formula": "∀x P(x)"})
        assert status == 200 and rechecked["value"] is False
        assert found["story"]["events"]
        status, unknown = request(url, "/api/countermodel", {
            "signature": simple, "formula": "∀x P(x)", "max_size": 1})
        assert status == 200 and unknown["status"] == "unknown" and "model" not in unknown

        status, spanish = request(url, "/api/spanish", {
            "text": "Todos los estudiantes leyeron un libro"})
        assert status == 200 and spanish["status"] == "ambiguous" and len(spanish["readings"]) == 2
        scope_model = {"domain": [0, 1], "predicates": {
            "Estudiante": {"arity": 1, "tuples": [[0], [1]]},
            "Libro": {"arity": 1, "tuples": [[0], [1]]},
            "Leer2": {"arity": 2, "tuples": [[0, 0], [1, 1]]}}}
        scope_values = []
        for reading in spanish["readings"]:
            status, result = request(url, "/api/evaluate", {
                "signature": reading["signature"], "interpretation": scope_model,
                "formula": reading["formula"]})
            assert status == 200 and result["status"] == "ok"
            scope_values.append(result["value"])
        assert scope_values == [True, False]

        status, proof = request(url, "/api/proof", {
            "premises": ["P → Q", "P"], "conclusion": "Q"})
        assert status == 200 and proof["status"] == "proved"
        assert len(proof["story"]["events"]) == len(proof["certificate"]["steps"])
        assert all(event["verified_by"] == {"certificate_step": event["step_id"]}
                   for event in proof["story"]["events"])
        status, unproved = request(url, "/api/proof", {
            "premises": ["P"], "conclusion": "Q"})
        assert status == 200 and unproved["status"] == "unknown" and "story" not in unproved

        durations = []
        benchmark = {"signature": signature, "interpretation": canonical,
                     "formula": "∀x (P(x) → ∃y Q(y))"}
        for _ in range(100):
            start = perf_counter()
            status, result = request(url, "/api/evaluate", benchmark)
            assert status == 200 and result["status"] == "ok"
            durations.append((perf_counter() - start) * 1000)
        durations.sort()
        return {
            "seed": seed, "status": "passed", "transport": "HTTP local 127.0.0.1",
            "python": sys.version.split()[0], "source_sha256": source_digest(),
            "external_assets": False, "generated_formulas": samples,
            "negative_cases": [code for _, _, code in invalid_cases],
            "countermodel": {"status": found["status"], "size": len(found["model"]["domain"]),
                             "unknown_at_size_1": unknown["status"]},
            "spanish_scope": {"status": spanish["status"], "values": scope_values},
            "narration": {"evaluation_events_verified": True,
                          "proof_events": len(proof["story"]["events"]),
                          "unproved_has_no_story": "story" not in unproved,
                          "three_local_assets": True},
            "benchmark": {"requests": 100, "median_ms": round(statistics.median(durations), 2),
                          "p95_ms": round(durations[94], 2), "max_ms": round(durations[-1], 2)},
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.seed)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
