"""Estructuras finitas de primer orden (ver docs/specs/SEMANTICS.md)."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import NamedTuple

from .ast import is_pred_name, is_term_name
from .errors import SCHEMA_VERSION, LogosError


class Function(NamedTuple):
    arity: int
    table: dict


class Relation(NamedTuple):
    arity: int
    tuples: frozenset


def _bad(message):
    return LogosError("semantic", "invalid_model", message)


@dataclass(frozen=True, eq=False)
class FiniteModel:
    """Dominio no vacío con interpretaciones totales.

    `functions`: `{nombre: (aridad, {args: valor})}`.
    `predicates`: `{nombre: (aridad, {tuplas})}`.
    """

    domain: tuple
    constants: dict
    functions: dict
    predicates: dict

    def __init__(self, domain, constants=None, functions=None, predicates=None):
        dom = tuple(domain)
        if not dom:
            raise _bad("el dominio no puede ser vacío")
        for e in dom:
            if isinstance(e, bool) or not isinstance(e, (int, str)):
                raise _bad(f"elemento de dominio no soportado: {e!r} (solo int o str)")
        if len(set(dom)) != len(dom):
            raise _bad("el dominio tiene elementos repetidos")
        dset = set(dom)

        consts = dict(constants or {})
        for name, val in consts.items():
            if not is_term_name(name):
                raise _bad(f"nombre de constante inválido: {name!r}")
            if val not in dset:
                raise _bad(f"la constante '{name}' vale {val!r}, que no está en el dominio")

        funcs = {}
        for name, (arity, table) in (functions or {}).items():
            if not is_term_name(name):
                raise _bad(f"nombre de función inválido: {name!r}")
            if name in consts:
                raise _bad(f"'{name}' es constante y función a la vez")
            if not isinstance(arity, int) or isinstance(arity, bool) or arity < 1:
                raise _bad(f"la función '{name}' necesita aridad >= 1")
            tbl = {tuple(k): v for k, v in dict(table).items()}
            expected = set(product(dom, repeat=arity))
            if set(tbl) != expected:
                raise _bad(f"la tabla de '{name}' debe ser total: {len(expected)} entradas exactas")
            for k, v in tbl.items():
                if v not in dset:
                    raise _bad(f"'{name}{k}' vale {v!r}, que no está en el dominio")
            funcs[name] = Function(arity, tbl)

        preds = {}
        for name, (arity, tuples) in (predicates or {}).items():
            if not is_pred_name(name):
                raise _bad(f"nombre de predicado inválido: {name!r}")
            if not isinstance(arity, int) or isinstance(arity, bool) or arity < 0:
                raise _bad(f"el predicado '{name}' necesita aridad >= 0")
            ext = frozenset(tuple(t) for t in tuples)
            for t in ext:
                if len(t) != arity or any(e not in dset for e in t):
                    raise _bad(f"la tupla {t!r} de '{name}' no está en D^{arity}")
            preds[name] = Relation(arity, ext)

        object.__setattr__(self, "domain", dom)
        object.__setattr__(self, "constants", consts)
        object.__setattr__(self, "functions", funcs)
        object.__setattr__(self, "predicates", preds)

    def __eq__(self, other):
        return isinstance(other, FiniteModel) and self.to_dict() == other.to_dict()

    __hash__ = None

    # --- serialización canónica -------------------------------------------
    def to_dict(self):
        pos = {e: i for i, e in enumerate(self.domain)}
        key = lambda t: tuple(pos[e] for e in t)
        return {
            "schema_version": SCHEMA_VERSION,
            "domain": list(self.domain),
            "constants": {n: self.constants[n] for n in sorted(self.constants)},
            "functions": {
                n: {"arity": f.arity,
                    "table": [[list(k), f.table[k]] for k in sorted(f.table, key=key)]}
                for n, f in sorted(self.functions.items())
            },
            "predicates": {
                n: {"arity": r.arity, "tuples": [list(t) for t in sorted(r.tuples, key=key)]}
                for n, r in sorted(self.predicates.items())
            },
        }

    @classmethod
    def from_dict(cls, d):
        if d.get("schema_version") != SCHEMA_VERSION:
            raise _bad(f"schema_version no soportada: {d.get('schema_version')!r}")
        return cls(
            d["domain"],
            d.get("constants", {}),
            {n: (f["arity"], {tuple(k): v for k, v in f["table"]})
             for n, f in d.get("functions", {}).items()},
            {n: (r["arity"], r["tuples"]) for n, r in d.get("predicates", {}).items()},
        )
