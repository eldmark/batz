"""Contrato JSON de `FormulaAST` (docs/specs/JSON_CONTRACTS.md): árbol con ids estables."""
from __future__ import annotations

from .ast import (
    And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred, Span, Var,
    _Binary, _Quant,
)
from .errors import SCHEMA_VERSION, LogosError
from .printer import to_string

_BINARY = {"and": And, "or": Or, "implies": Implies, "iff": Iff}
_QUANT = {"forall": Forall, "exists": Exists}
_KIND = {And: "and", Or: "or", Implies: "implies", Iff: "iff", Forall: "forall", Exists: "exists"}


def _bad(message):
    return LogosError("semantic", "invalid_ast", message)


def formula_to_dict(f, spans=True):
    """`{schema_version, text, tree}`; cada nodo lleva `id` (ruta desde la raíz, p. ej. "0.1.0")."""
    return {"schema_version": SCHEMA_VERSION, "text": to_string(f), "tree": _node(f, "0", spans)}


def _node(n, path, spans):
    kids = lambda items: [_node(c, f"{path}.{i}", spans) for i, c in enumerate(items)]
    d = {"id": path}
    if isinstance(n, Var):
        d.update(kind="var", name=n.name)
    elif isinstance(n, Const):
        d.update(kind="const", name=n.name)
    elif isinstance(n, Func):
        d.update(kind="func", name=n.name, args=kids(n.args))
    elif isinstance(n, Bottom):
        d.update(kind="bottom")
    elif isinstance(n, Pred):
        d.update(kind="pred", name=n.name, args=kids(n.args))
    elif isinstance(n, Eq):
        d.update(kind="eq", left=_node(n.left, path + ".0", spans), right=_node(n.right, path + ".1", spans))
    elif isinstance(n, Not):
        d.update(kind="not", operand=_node(n.operand, path + ".0", spans))
    elif isinstance(n, _Binary):
        d.update(kind=_KIND[type(n)], left=_node(n.left, path + ".0", spans),
                 right=_node(n.right, path + ".1", spans))
    elif isinstance(n, _Quant):
        d.update(kind=_KIND[type(n)], var=n.var, body=_node(n.body, path + ".0", spans))
    else:
        raise TypeError(f"nodo desconocido: {n!r}")
    if spans and n.span is not None:
        d["span"] = [n.span.start, n.span.end]
    return d


def formula_from_dict(d):
    """Reconstruye y valida. Rechaza esquemas ajenos, ids inconsistentes y nodos mal formados."""
    try:
        if d["schema_version"] != SCHEMA_VERSION:
            raise _bad(f"schema_version no soportada: {d['schema_version']!r}")
        f = _build(d["tree"], "0")
        if "text" in d and d["text"] != to_string(f):
            raise _bad("el texto no coincide con el árbol")
        return f
    except LogosError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise _bad(f"AST mal formado: {e}") from e


def _build(d, path):
    if d["id"] != path:
        raise _bad(f"id inconsistente: {d['id']!r} (se esperaba {path!r})")
    span = Span(*d["span"]) if "span" in d else None
    kind = d["kind"]
    sub = lambda key, i: _build(d[key], f"{path}.{i}")
    subs = lambda key: tuple(_build(c, f"{path}.{i}") for i, c in enumerate(d[key]))
    if kind == "var":
        return Var(d["name"], span)
    if kind == "const":
        return Const(d["name"], span)
    if kind == "func":
        return Func(d["name"], subs("args"), span)
    if kind == "bottom":
        return Bottom(span)
    if kind == "pred":
        return Pred(d["name"], subs("args"), span)
    if kind == "eq":
        return Eq(sub("left", 0), sub("right", 1), span)
    if kind == "not":
        return Not(sub("operand", 0), span)
    if kind in _BINARY:
        return _BINARY[kind](sub("left", 0), sub("right", 1), span)
    if kind in _QUANT:
        return _QUANT[kind](d["var"], sub("body", 0), span)
    raise _bad(f"kind desconocido: {kind!r}")


def result_to_dict(status, certificate=None, countermodel=None, reason=None, diagnostic=None,
                   nodes=None, method=None):
    """Sobre de resultado versionado que consume la UI (ver JSON_CONTRACTS.md)."""
    if status not in ("proved", "counterexample", "unknown", "inconsistent", "invalid_input"):
        raise ValueError(f"status desconocido: {status!r}")
    d = {"schema_version": SCHEMA_VERSION, "status": status}
    if certificate is not None:
        d["certificate"] = certificate.to_dict()
    if countermodel is not None:
        d["countermodel"] = countermodel.to_dict()
    for key, val in (("reason", reason), ("diagnostic", diagnostic), ("nodes", nodes), ("method", method)):
        if val is not None:
            d[key] = val
    return d
