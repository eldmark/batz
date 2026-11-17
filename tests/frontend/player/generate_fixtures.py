"""Genera guiones con los motores y verificadores reales, sin modificar datos de usuario."""
import copy
import json
from pathlib import Path

from batz import parse
from batz.countermodels import find_consequence_countermodel
from batz.server import handle_api


def fixtures():
    signature = {"constants": [], "functions": {}, "predicates": {"P": 1, "Q": 1}}
    model = {"domain": [0, 1], "functions": {}, "constants": {}, "predicates": {
        "P": {"arity": 1, "tuples": [[0], [1]]}, "Q": {"arity": 1, "tuples": [[0]]}}}
    result = {}
    for name, formula in [("evaluation", "∀x (P(x) → Q(x))"), ("true", "∃x (P(x) ∧ Q(x))")]:
        response = handle_api("/api/evaluate", {"signature": signature, "interpretation": model, "formula": formula})
        assert response["status"] == "ok", response
        result[name] = {"resultId": name, "origin": "evaluate", "kind": "evaluation",
                        "title": "Evaluación semántica", "story": response["story"], "model": response["model"]}
    proof = handle_api("/api/proof", {"premises": ["∀x (P(x) → Q(x))", "P(a)"], "conclusion": "Q(a)", "constants": ["a"]})
    assert proof["status"] == "proved", proof
    result["proof"] = {"resultId": "proof", "origin": "prove", "kind": "proof", "title": "Demostración",
                       "story": proof["story"], "model": None}
    countermodel = find_consequence_countermodel([parse("∀x ∃y R(x, y)")], parse("∃y ∀x R(x, y)")).to_dict()
    assert countermodel["status"] == "found", countermodel
    result["countermodel"] = {"resultId": "countermodel", "origin": "prove", "kind": "countermodel",
                              "title": "Contramodelo", "story": countermodel["story"], "model": countermodel["model"]}
    result["notebook"] = copy.deepcopy(result["proof"])
    result["notebook"].update(resultId="notebook", origin="notebook", title="Prueba desde las premisas del cuaderno")
    result["empty"] = {"resultId": "empty", "origin": "evaluate", "kind": "evaluation",
                       "title": "Sin recorrido", "story": {"events": []}, "model": None}
    return result


if __name__ == "__main__":
    path = Path(__file__).with_name("fixtures.json")
    path.write_text(json.dumps(fixtures(), ensure_ascii=False, indent=2) + "\n")
    print(path)
