"""Texto legible de un certificado (traza para el depurador matemático)."""
from __future__ import annotations

from ..printer import to_string

_NAMES = {
    "assume": "Hipótesis", "and_i": "∧I", "and_e1": "∧E₁", "and_e2": "∧E₂",
    "or_i1": "∨I₁", "or_i2": "∨I₂", "or_e": "∨E", "imp_i": "→I", "imp_e": "→E",
    "not_i": "¬I", "not_e": "¬E", "bot_e": "⊥E", "raa": "RAA", "iff_i": "↔I",
    "iff_e1": "↔E₁", "iff_e2": "↔E₂", "all_i": "∀I", "all_e": "∀E", "ex_i": "∃I",
    "ex_e": "∃E", "eq_i": "=I", "eq_e": "=E",
}


def format_certificate(cert):
    lines = ["Premisas: " + (", ".join(to_string(p) for p in cert.premises) or "(ninguna)"),
             "Conclusión: " + to_string(cert.conclusion), ""]
    for s in cert.steps:
        ctx = ", ".join(to_string(c) for c in s.context)
        why = _NAMES.get(s.rule, s.rule)
        if s.refs:
            why += " " + ",".join(map(str, s.refs))
        for k in ("var", "term"):
            if k in s.params:
                why += f" [{k}={s.params[k] if isinstance(s.params[k], str) else to_string(s.params[k])}]"
        lines.append(f"{s.id:>3}. {to_string(s.formula)}    ({why})    {{{ctx}}}")
    return "\n".join(lines)
