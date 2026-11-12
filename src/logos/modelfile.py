"""Archivos preparados: un modelo y sus fórmulas en texto plano, para no teclearlos en la interfaz.

    # comentario
    dominio: 0, 1, 2
    constante a = 0
    funcion f/1: 0 -> 1, 1 -> 2, 2 -> 0
    predicado P/1: 0, 2
    predicado R/2: (0, 1), (1, 2)
    formula: ∀x (P(x) → ∃y R(x, y))
    formula: P(x) | x = 0 | espera: verdadero

Devuelve el mismo paquete que «Exportar JSON» (firma + interpretación), más la lista de fórmulas.
La validación matemática la hace después `build_interpretation`; aquí solo se lee la forma.
"""
from __future__ import annotations

import json
import re

from .errors import LogosError

_HEAD = re.compile(r"^(dominio|constante|funci[oó]n|predicado|f[oó]rmula)\b\s*(.*)$", re.IGNORECASE)
_TRUE, _FALSE = {"verdadero", "v", "true", "1"}, {"falso", "f", "false", "0"}


def _bad(line_no, message):
    raise LogosError("syntactic", "invalid_model_file", f"línea {line_no}: {message}")


def _value(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return int(text) if re.fullmatch(r"-?\d+", text) else text


def _tuple(text, line_no):
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    parts = [p for p in (x.strip() for x in text.split(",")) if p]
    if not parts:
        _bad(line_no, "tupla vacía")
    return [_value(p) for p in parts]


def _split_items(text):
    """Separa por comas que no estén dentro de paréntesis."""
    items, depth, current = [], 0, ""
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            items.append(current)
            current = ""
        else:
            current += ch
    return [i.strip() for i in items + [current] if i.strip()]


def _name_arity(text, line_no, what):
    m = re.fullmatch(r"\s*([A-Za-z][\w']*)\s*/\s*(\d+)\s*", text)
    if not m:
        _bad(line_no, f"se esperaba «{what} nombre/aridad: …»")
    return m.group(1), int(m.group(2))


def _formula(rest, line_no):
    parts = [p.strip() for p in rest.lstrip(":").split("|")]
    if not parts[0]:
        _bad(line_no, "falta la fórmula")
    entry = {"formula": parts[0], "assignment": {}, "line": line_no}
    for part in parts[1:]:
        expect = re.fullmatch(r"espera\s*:\s*(\S+)", part, re.IGNORECASE)
        if expect:
            word = expect.group(1).lower()
            if word not in _TRUE | _FALSE:
                _bad(line_no, "«espera:» admite verdadero o falso")
            entry["expected"] = word in _TRUE
            continue
        for pair in _split_items(part):
            if "=" not in pair:
                _bad(line_no, f"asignación inválida: «{pair}» (usa x = 0)")
            var, val = pair.split("=", 1)
            entry["assignment"][var.strip()] = _value(val)
    return entry


def parse_model_file(text):
    """Texto plano o JSON exportado → `{"signature", "interpretation", "formulas"}`."""
    if not isinstance(text, str) or not text.strip():
        raise LogosError("syntactic", "invalid_model_file", "el archivo está vacío")
    if text.lstrip().startswith("{"):
        return _from_json(text)
    signature = {"constants": [], "functions": {}, "predicates": {}}
    model = {"domain": None, "constants": {}, "functions": {}, "predicates": {}}
    formulas = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = _HEAD.match(line)
        if not m:
            _bad(line_no, "se esperaba dominio, constante, funcion, predicado o formula")
        kind, rest = m.group(1).lower().replace("ó", "o"), m.group(2)
        if kind == "formula":
            formulas.append(_formula(rest, line_no))
            continue
        if kind == "dominio":
            body = rest.lstrip(":").strip().strip("{}[]")
            model["domain"] = [_value(p) for p in _split_items(body)]
        elif kind == "constante":
            if "=" not in rest:
                _bad(line_no, "se esperaba «constante a = valor»")
            name, val = rest.split("=", 1)
            signature["constants"].append(name.strip())
            model["constants"][name.strip()] = _value(val)
        else:
            if ":" not in rest:
                _bad(line_no, f"falta «:» después de {kind} nombre/aridad")
            head, body = rest.split(":", 1)
            name, arity = _name_arity(head, line_no, kind)
            if kind == "funcion":
                table = []
                for item in _split_items(body):
                    if "->" not in item and "→" not in item:
                        _bad(line_no, f"entrada de función inválida: «{item}» (usa 0 -> 1)")
                    args, val = re.split(r"->|→", item, maxsplit=1)
                    table.append([_tuple(args, line_no), _value(val)])
                signature["functions"][name] = arity
                model["functions"][name] = {"arity": arity, "table": table}
            else:
                signature["predicates"][name] = arity
                model["predicates"][name] = {"arity": arity,
                                              "tuples": [_tuple(i, line_no) for i in _split_items(body)]}
    if model["domain"] is None:
        raise LogosError("syntactic", "invalid_model_file", "falta la línea «dominio: …»")
    return {"signature": signature, "interpretation": model, "formulas": formulas}


def _from_json(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LogosError("syntactic", "invalid_model_file", f"JSON inválido: {exc.msg}")
    if not isinstance(data, dict) or not isinstance(data.get("signature"), dict):
        raise LogosError("syntactic", "invalid_model_file", "el JSON no tiene «signature»")
    model = data.get("interpretation", data.get("model"))
    if not isinstance(model, dict):
        raise LogosError("syntactic", "invalid_model_file", "el JSON no tiene «interpretation»")
    formulas = []
    raw = data.get("formulas")
    if raw is None and isinstance(data.get("formula"), str) and data["formula"].strip():
        raw = [data["formula"]]
    for i, item in enumerate(raw or [], 1):
        if isinstance(item, str):
            item = {"formula": item}
        if not isinstance(item, dict) or not isinstance(item.get("formula"), str):
            raise LogosError("syntactic", "invalid_model_file", f"fórmula {i} inválida en el JSON")
        entry = {"formula": item["formula"], "assignment": item.get("assignment") or {}, "line": i}
        if isinstance(item.get("expected"), bool):
            entry["expected"] = item["expected"]
        formulas.append(entry)
    return {"signature": {"constants": list(data["signature"].get("constants", [])),
                          "functions": dict(data["signature"].get("functions", {})),
                          "predicates": dict(data["signature"].get("predicates", {}))},
            "interpretation": model, "formulas": formulas}
