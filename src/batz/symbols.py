"""Tabla de símbolos y validación de aridad."""
from __future__ import annotations

from dataclasses import dataclass, field

from .ast import Bottom, Const, Eq, Func, Pred, Var, _Binary, _Quant, Not
from .errors import BatzError
from .parser import parse


@dataclass(frozen=True)
class Signature:
    """Símbolos declarados: constantes y aridades de funciones y predicados."""

    constants: frozenset = frozenset()
    functions: dict = field(default_factory=dict)
    predicates: dict = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "constants", frozenset(self.constants))
        object.__setattr__(self, "functions", dict(self.functions))
        object.__setattr__(self, "predicates", dict(self.predicates))


def _err(code, message, node, source):
    return BatzError("semantic", code, message, getattr(node, "span", None), source)


def check(f, signature=None, strict=False, source=None):
    """Valida aridades y uso coherente de símbolos; devuelve la firma inferida.

    - Sin firma, la aridad de cada símbolo es la de su primer uso.
    - Con `strict=True`, todo símbolo (excepto variables) debe estar declarado.
    - Un nombre no puede ser a la vez variable, constante y función.
    """
    sig = signature or Signature()
    funcs, preds = dict(sig.functions), dict(sig.predicates)
    consts = set(sig.constants)
    kinds = {c: "constante" for c in consts} | {n: "función" for n in funcs}

    def claim(name, kind, node):
        old = kinds.setdefault(name, kind)
        if old != kind:
            raise _err("symbol_kind_clash", f"'{name}' se usa como {old} y como {kind}", node, source)

    def arity(table, name, n, node, what):
        if name in table:
            if table[name] != n:
                raise _err("arity_mismatch", f"{what} '{name}' tiene aridad {table[name]} pero se usa con {n} argumento(s)", node, source)
        elif strict:
            raise _err("undeclared_symbol", f"{what} '{name}' no está {'declarada' if what.startswith('la') else 'declarado'}", node, source)
        else:
            table[name] = n

    def term(t):
        if isinstance(t, Var):
            claim(t.name, "variable", t)
        elif isinstance(t, Const):
            if strict and t.name not in consts:
                raise _err("undeclared_symbol", f"la constante '{t.name}' no está declarada", t, source)
            consts.add(t.name)
            claim(t.name, "constante", t)
        else:
            claim(t.name, "función", t)
            arity(funcs, t.name, len(t.args), t, "la función")
            for a in t.args:
                term(a)

    def walk(g):
        if isinstance(g, Bottom):
            return
        if isinstance(g, Pred):
            arity(preds, g.name, len(g.args), g, "el predicado")
            for a in g.args:
                term(a)
        elif isinstance(g, Eq):
            term(g.left)
            term(g.right)
        elif isinstance(g, Not):
            walk(g.operand)
        elif isinstance(g, _Binary):
            walk(g.left)
            walk(g.right)
        elif isinstance(g, _Quant):
            claim(g.var, "variable", g)
            walk(g.body)
        else:
            raise TypeError(f"nodo desconocido: {g!r}")

    walk(f)
    return Signature(frozenset(consts), funcs, preds)


def parse_checked(text, signature=None, strict=False):
    """Parsea y valida con la firma; las constantes declaradas se leen como tales."""
    consts = signature.constants if signature else ()
    f = parse(text, consts)
    check(f, signature, strict, source=text)
    return f
