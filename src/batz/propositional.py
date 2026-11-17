"""Decisor semántico para lógica proposicional (sin cuantificadores ni términos).

Una fórmula proposicional solo tiene `⊥`, predicados de aridad 0 y conectivos. Ahí
la validez ES decidible: la tabla de verdad da el veredicto exacto. Este módulo
sirve de oráculo para contrastar el buscador de pruebas y para dar contramodelos.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Optional

from .ast import (
    And, Bottom, Eq, Iff, Implies, Not, Or, Pred, _Binary, _Quant,
)
from .errors import BatzError
from .model import FiniteModel
from .semantics import is_countermodel


def is_propositional(f):
    if isinstance(f, Bottom):
        return True
    if isinstance(f, Pred):
        return not f.args
    if isinstance(f, Not):
        return is_propositional(f.operand)
    if isinstance(f, _Binary):
        return is_propositional(f.left) and is_propositional(f.right)
    return False  # cuantificadores, igualdad


def atoms(f):
    """Letras proposicionales (predicados 0-arios) ordenadas por nombre."""
    if isinstance(f, Pred):
        return {f.name}
    if isinstance(f, Not):
        return atoms(f.operand)
    if isinstance(f, _Binary):
        return atoms(f.left) | atoms(f.right)
    return set()


def value(f, v):
    """Valor de `f` bajo la valuación `v` (dict letra→bool); implementación directa."""
    if isinstance(f, Bottom):
        return False
    if isinstance(f, Pred):
        return v[f.name]
    if isinstance(f, Not):
        return not value(f.operand, v)
    a, b = value(f.left, v), value(f.right, v)
    if isinstance(f, And):
        return a and b
    if isinstance(f, Or):
        return a or b
    if isinstance(f, Implies):
        return (not a) or b
    return a == b  # Iff


def valuations(names):
    names = sorted(names)
    for bits in itertools.product([False, True], repeat=len(names)):
        yield dict(zip(names, bits))


def truth_table(f):
    """Lista de `(valuación, valor)` en orden estándar (F antes que V)."""
    if not is_propositional(f):
        raise BatzError("semantic", "not_propositional", "la fórmula no es proposicional", getattr(f, "span", None))
    return [(v, value(f, v)) for v in valuations(atoms(f))]


def valuation_model(v):
    """Modelo de un elemento cuyos predicados 0-arios valen lo que dice `v`."""
    return FiniteModel([0], predicates={n: (0, [()] if b else []) for n, b in v.items()})


def literals(v):
    """Premisas del lema de Kalmár: `p` si `v(p)` es verdadero, `¬p` si es falso."""
    return tuple(Pred(n) if b else Not(Pred(n)) for n, b in sorted(v.items()))


def kalmar_sequent(f, v):
    """`(premisas, meta)` del lema de Kalmár: literales de `v` ⊢ `f` si vale, `¬f` si no."""
    return literals(v), (f if value(f, v) else Not(f))


@dataclass(frozen=True)
class PropVerdict:
    """Veredicto exacto de `premisas ⊨ conclusión` en lógica proposicional.

    `status`: `proved` (certificado aceptado por el checker) o `counterexample` (modelo
    verificado). En lógica proposicional siempre se da uno de los dos: el buscador
    heurístico se intenta primero y el algoritmo de Kalmár, completo, es el respaldo.
    `unknown` solo aparece con demasiadas letras (`max_atoms`).
    """

    status: str
    entails: Optional[bool]
    premises_satisfiable: Optional[bool]
    countermodel: Optional[FiniteModel] = None
    certificate: object = None
    reason: Optional[str] = None
    method: Optional[str] = None  # "search" o "kalmar": quién produjo el certificado

    def to_dict(self):
        from .serialize import result_to_dict
        return result_to_dict(self.status, self.certificate, self.countermodel, self.reason, None, None, self.method)


def decide(premises, conclusion, config=None, max_atoms=16):
    from .proof import prove  # import tardío: el decisor no depende del buscador al cargarse

    formulas = [*premises, conclusion]
    for f in formulas:
        if not is_propositional(f):
            raise BatzError("semantic", "not_propositional", "la fórmula no es proposicional", getattr(f, "span", None))
    names = set().union(*(atoms(f) for f in formulas))
    if len(names) > max_atoms:
        return PropVerdict("unknown", None, None, reason="too_many_atoms")

    counter, satisfiable = None, False
    for v in valuations(names):
        if all(value(p, v) for p in premises):
            satisfiable = True
            if not value(conclusion, v):
                counter = v
                break
    if counter is not None:
        model = valuation_model({n: counter[n] for n in sorted(names)})
        if not is_countermodel(model, premises, conclusion):  # el evaluador de Fase 2 confirma
            raise AssertionError("contramodelo no verificado: bug en el decisor")
        return PropVerdict("counterexample", False, True, countermodel=model)
    if not satisfiable:  # premisas insatisfacibles: todo se sigue
        satisfiable = any(all(value(p, v) for p in premises) for v in valuations(names))
    res = prove(tuple(premises), conclusion, config)
    if res.status == "proved":
        return PropVerdict("proved", True, satisfiable, certificate=res.certificate, method="search")
    from .proof.kalmar import kalmar_prove  # respaldo completo
    from .proof.checker import verify

    cert = kalmar_prove(premises, conclusion, max_atoms=max_atoms)
    verify(cert)
    return PropVerdict("proved", True, satisfiable, certificate=cert, method="kalmar")
