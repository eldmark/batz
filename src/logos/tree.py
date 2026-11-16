"""Árboles de una fórmula para dibujarlos: el sintáctico (estructura) y el semántico (evaluación).

Ambos son diccionarios anidados `{"label", "kind", "children", …}` sin lógica propia: el
árbol semántico se lee de la traza que `check_trace` ya aceptó, nunca se recalcula aquí.
"""
from __future__ import annotations

import re

from .ast import And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred, Var
from .printer import to_string

MAX_NODES = 500
_BINARY = {And: "∧", Or: "∨", Implies: "→", Iff: "↔"}


def _term(t):
    if isinstance(t, Var):
        return {"label": t.name, "kind": "var", "children": []}
    if isinstance(t, Const):
        return {"label": t.name, "kind": "const", "children": []}
    return {"label": t.name, "kind": "func", "children": [_term(a) for a in t.args]}


def syntax_tree(f, letters=None):
    """Estructura de la fórmula: conectivo o cuantificador en la raíz, átomos con sus términos como hojas.

    `letters` (opcional): letras proposicionales como las escribió la persona (`P` → `p`).
    """
    names = letters or {}
    full = re.sub(r"[A-Za-z_][A-Za-z0-9_]*", lambda m: names.get(m.group(0), m.group(0)), to_string(f)) if names else to_string(f)
    if isinstance(f, Bottom):
        return {"label": "⊥", "kind": "bottom", "formula": full, "children": []}
    if isinstance(f, Pred):
        return {"label": names.get(f.name, f.name), "kind": "pred", "formula": full, "children": [_term(a) for a in f.args]}
    if isinstance(f, Eq):
        return {"label": "=", "kind": "eq", "formula": full, "children": [_term(f.left), _term(f.right)]}
    if isinstance(f, Not):
        return {"label": "¬", "kind": "not", "formula": full, "children": [syntax_tree(f.operand, letters)]}
    if isinstance(f, (Forall, Exists)):
        return {"label": ("∀" if isinstance(f, Forall) else "∃") + f.var, "kind": "quantifier", "formula": full,
                "children": [syntax_tree(f.body, letters)]}
    return {"label": _BINARY[type(f)], "kind": "connective", "formula": full,
            "children": [syntax_tree(f.left, letters), syntax_tree(f.right, letters)]}


def _label(f):
    if isinstance(f, (Pred, Eq, Bottom)):
        return to_string(f)                       # una hoja semántica es el átomo completo, con sus valores
    if isinstance(f, Not):
        return "¬"
    if isinstance(f, (Forall, Exists)):
        return ("∀" if isinstance(f, Forall) else "∃") + f.var
    return _BINARY[type(f)]


def semantic_tree(trace, limit=MAX_NODES):
    """Árbol de evaluación: valor de cada nodo; bajo un cuantificador, una rama por elemento del dominio."""
    count = [0]

    def walk(node, edge=None):
        count[0] += 1
        f = node.formula
        out = {"label": _label(f), "kind": "quantifier" if isinstance(f, (Forall, Exists)) else
               "atom" if isinstance(f, (Pred, Eq, Bottom)) else "not" if isinstance(f, Not) else "connective",
               "value": bool(node.value), "formula": to_string(f),
               "assignment": [[v, e] for v, e in node.assignment]}
        if edge is not None:
            out["edge"] = edge
        if node.term_values:
            out["values"] = list(node.term_values)
            if isinstance(f, Pred):
                out["relation"] = f.name
        if count[0] >= limit and node.children:
            out["children"] = []
            out["truncated"] = len(node.children)
            return out
        quant = isinstance(f, (Forall, Exists))
        out["children"] = [walk(c, f"{f.var} = {c.element!r}" if quant else None) for c in node.children]
        return out

    tree = walk(trace)
    tree["nodes"] = count[0]
    return tree
