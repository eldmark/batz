"""AST inmutable de FOL. Los constructores rechazan nodos mal formados."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

RESERVED = frozenset({"forall", "exists"})


@dataclass(frozen=True)
class Span:
    start: int
    end: int


def _ident_ok(name):
    return (
        isinstance(name, str)
        and name != ""
        and name[0].isalpha()
        and all(c.isalnum() or c in "_'" for c in name)
    )


def is_term_name(name):
    """Variable, constante o función: minúscula inicial y no reservada."""
    return _ident_ok(name) and name[0].islower() and name not in RESERVED


def is_pred_name(name):
    """Predicado: mayúscula inicial."""
    return _ident_ok(name) and name[0].isupper()


def _span_field():
    return field(default=None, compare=False, repr=False)


class Node:
    """Base común: términos y fórmulas."""


class Term(Node):
    pass


class Formula(Node):
    pass


@dataclass(frozen=True)
class Var(Term):
    name: str
    span: Optional[Span] = _span_field()

    def __post_init__(self):
        if not is_term_name(self.name):
            raise ValueError(f"nombre de variable inválido: {self.name!r}")


@dataclass(frozen=True)
class Const(Term):
    name: str
    span: Optional[Span] = _span_field()

    def __post_init__(self):
        if not is_term_name(self.name):
            raise ValueError(f"nombre de constante inválido: {self.name!r}")


@dataclass(frozen=True)
class Func(Term):
    name: str
    args: tuple
    span: Optional[Span] = _span_field()

    def __post_init__(self):
        if not is_term_name(self.name):
            raise ValueError(f"nombre de función inválido: {self.name!r}")
        object.__setattr__(self, "args", tuple(self.args))
        if not self.args:
            raise ValueError("una función necesita al menos un argumento")
        _check_terms(self.args)


@dataclass(frozen=True)
class Pred(Formula):
    name: str
    args: tuple = ()
    span: Optional[Span] = _span_field()

    def __post_init__(self):
        if not is_pred_name(self.name):
            raise ValueError(f"nombre de predicado inválido: {self.name!r}")
        object.__setattr__(self, "args", tuple(self.args))
        _check_terms(self.args)


@dataclass(frozen=True)
class Eq(Formula):
    left: Term
    right: Term
    span: Optional[Span] = _span_field()

    def __post_init__(self):
        _check_terms((self.left, self.right))


@dataclass(frozen=True)
class Bottom(Formula):
    """Falsedad `⊥`: nunca es verdadera en ninguna estructura."""

    span: Optional[Span] = _span_field()


@dataclass(frozen=True)
class Not(Formula):
    operand: Formula
    span: Optional[Span] = _span_field()

    def __post_init__(self):
        _check_formulas((self.operand,))


@dataclass(frozen=True)
class _Binary(Formula):
    left: Formula
    right: Formula
    span: Optional[Span] = _span_field()

    def __post_init__(self):
        _check_formulas((self.left, self.right))


@dataclass(frozen=True)
class And(_Binary):
    pass


@dataclass(frozen=True)
class Or(_Binary):
    pass


@dataclass(frozen=True)
class Implies(_Binary):
    pass


@dataclass(frozen=True)
class Iff(_Binary):
    pass


@dataclass(frozen=True)
class _Quant(Formula):
    var: str
    body: Formula
    span: Optional[Span] = _span_field()

    def __post_init__(self):
        if not is_term_name(self.var):
            raise ValueError(f"variable cuantificada inválida: {self.var!r}")
        _check_formulas((self.body,))


@dataclass(frozen=True)
class Forall(_Quant):
    pass


@dataclass(frozen=True)
class Exists(_Quant):
    pass


def _check_terms(items):
    for t in items:
        if not isinstance(t, Term):
            raise TypeError(f"se esperaba un término, no {type(t).__name__}")


def _check_formulas(items):
    for f in items:
        if not isinstance(f, Formula):
            raise TypeError(f"se esperaba una fórmula, no {type(f).__name__}")
