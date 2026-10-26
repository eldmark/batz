"""Pretty-printer canónico: parentetiza lo mínimo, compatible con el parser."""
from __future__ import annotations

from .ast import (
    And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred, Var,
)

# Precedencias: mayor liga más fuerte.
_IFF, _IMPLIES, _OR, _AND, _UNARY, _ATOM = 1, 2, 3, 4, 5, 6

_UNI = {"not": "¬", "and": "∧", "or": "∨", "implies": "→", "iff": "↔",
        "forall": "∀", "exists": "∃", "neq": "≠", "bot": "⊥"}
_ASCII = {"not": "~", "and": "&", "or": "|", "implies": "->", "iff": "<->",
          "forall": "forall ", "exists": "exists ", "neq": "!=", "bot": "_|_"}


def to_string(node, ascii=False):
    """Texto canónico de un término o fórmula (Unicode, o ASCII con `ascii=True`)."""
    sym = _ASCII if ascii else _UNI
    return _fmt(node, sym, 0)


def _terms(args, sym):
    return ", ".join(_fmt(a, sym, 0) for a in args)


def _prec(f):
    if isinstance(f, Iff):
        return _IFF
    if isinstance(f, Implies):
        return _IMPLIES
    if isinstance(f, Or):
        return _OR
    if isinstance(f, And):
        return _AND
    if isinstance(f, (Not, Forall, Exists)):
        return _UNARY
    return _ATOM


def _fmt(n, sym, min_prec):
    if isinstance(n, (Var, Const)):
        return n.name
    if isinstance(n, Func):
        return f"{n.name}({_terms(n.args, sym)})"
    if isinstance(n, Bottom):
        return sym["bot"]
    if isinstance(n, Pred):
        return n.name if not n.args else f"{n.name}({_terms(n.args, sym)})"
    if isinstance(n, Eq):
        return f"{_fmt(n.left, sym, 0)} = {_fmt(n.right, sym, 0)}"

    prec = _prec(n)
    if isinstance(n, Not):
        if isinstance(n.operand, Eq):
            e = n.operand
            text = f"{_fmt(e.left, sym, 0)} {sym['neq']} {_fmt(e.right, sym, 0)}"
        else:
            text = sym["not"] + _fmt(n.operand, sym, _UNARY)
    elif isinstance(n, (Forall, Exists)):
        q = sym["forall" if isinstance(n, Forall) else "exists"]
        text = f"{q}{n.var} {_fmt(n.body, sym, _UNARY)}"
    else:
        # Mínimo de precedencia de cada hijo según asociatividad.
        if isinstance(n, Iff):
            lmin = rmin = _IMPLIES  # no asociativo
        elif isinstance(n, Implies):
            lmin, rmin = _OR, _IMPLIES  # derecha
        elif isinstance(n, Or):
            lmin, rmin = _OR, _AND  # izquierda
        else:
            lmin, rmin = _AND, _UNARY
        op = sym["iff" if isinstance(n, Iff) else "implies" if isinstance(n, Implies)
                 else "or" if isinstance(n, Or) else "and"]
        text = f"{_fmt(n.left, sym, lmin)} {op} {_fmt(n.right, sym, rmin)}"
    return text if prec >= min_prec else f"({text})"
