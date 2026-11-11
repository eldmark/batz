"""Explicaciones deterministas de trazas semánticas verificadas."""
from __future__ import annotations

from dataclasses import dataclass

from .ast import And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred, Var
from .printer import to_string
from .semantics import Trace, check_trace, eval_term


@dataclass(frozen=True)
class Explanation:
    formula: str
    value: bool
    summary: str
    span: tuple[int, int] | None
    details: tuple[str, ...] = ()
    children: tuple["Explanation", ...] = ()
    assignment: tuple = ()  # entorno de las variables libres de este nodo

    def to_dict(self):
        return {
            "formula": self.formula,
            "value": self.value,
            "summary": self.summary,
            "span": list(self.span) if self.span is not None else None,
            "details": list(self.details),
            "assignment": [[var, value] for var, value in self.assignment],
            "children": [child.to_dict() for child in self.children],
        }


def _term_steps(model, term, assignment):
    if isinstance(term, (Var, Const)):
        return ()
    steps = tuple(s for arg in term.args for s in _term_steps(model, arg, assignment))
    return steps + (f"{to_string(term)} = {eval_term(model, term, assignment)!r}",)


def _tuple(values):
    """Notación matemática de una tupla: (0) y (0, 1), no la de Python."""
    return "(" + ", ".join(repr(v) for v in values) + ")"


def _make(trace, summary, details=(), children=()):
    span = trace.formula.span
    return Explanation(to_string(trace.formula), trace.value, summary,
                       None if span is None else (span.start, span.end),
                       tuple(details), tuple(children), tuple(trace.assignment))


def _explain(model, trace):
    f, value, kids = trace.formula, trace.value, trace.children
    if isinstance(f, Bottom):
        return _make(trace, "⊥ es siempre falso.")
    if isinstance(f, (Pred, Eq)):
        args = f.args if isinstance(f, Pred) else (f.left, f.right)
        details = tuple(s for term in args for s in _term_steps(model, term, dict(trace.assignment)))
        if isinstance(f, Pred):
            relation = f"{f.name}ᴵ"
            summary = (f"La tupla {_tuple(trace.term_values)} pertenece a {relation}." if value else
                       f"La tupla {_tuple(trace.term_values)} no pertenece a {relation}.")
        else:
            summary = (f"{trace.term_values[0]!r} y {trace.term_values[1]!r} son el mismo elemento." if value else
                       f"{trace.term_values[0]!r} y {trace.term_values[1]!r} son elementos distintos.")
        return _make(trace, summary, details)
    if isinstance(f, Not):
        return _make(trace, "La negación invierte el valor de su subfórmula.",
                     children=(_explain(model, kids[0]),))
    if isinstance(f, (Forall, Exists)):
        if isinstance(f, Forall) and value or isinstance(f, Exists) and not value:
            table = tuple(f"{f.var} = {child.element!r}: {'V' if child.value else 'F'}" for child in kids)
            summary = (f"Se revisaron los {len(kids)} elementos de D; todos satisfacen la fórmula." if value else
                       f"Se revisaron los {len(kids)} elementos de D; ninguno satisface la fórmula.")
            return _make(trace, summary, table, tuple(_explain(model, child) for child in kids))
        selected = next(child for child in kids if child.value == value)
        summary = (f"Testigo: {f.var} = {selected.element!r} satisface la fórmula." if value else
                   f"Contraejemplo: {f.var} = {selected.element!r} no satisface la fórmula.")
        return _make(trace, summary, children=(_explain(model, selected),))
    if isinstance(f, And):
        selected = kids if value else (next(child for child in kids if not child.value),)
        summary = "Ambas partes son verdaderas." if value else "Una parte es falsa."
    elif isinstance(f, Or):
        selected = (next(child for child in kids if child.value),) if value else kids
        summary = "Una parte es verdadera." if value else "Ambas partes son falsas."
    elif isinstance(f, Implies):
        if not value:
            selected = kids
            summary = "El antecedente es verdadero y el consecuente es falso."
        elif not kids[0].value:
            selected = (kids[0],)
            summary = "El antecedente es falso; la implicación es verdadera."
        else:
            selected = (kids[1],)
            summary = "El consecuente es verdadero; la implicación es verdadera."
    elif isinstance(f, Iff):
        selected = kids
        summary = "Ambas partes tienen el mismo valor." if value else "Las partes tienen valores distintos."
    else:
        raise TypeError(f"fórmula desconocida: {f!r}")
    return _make(trace, summary, children=tuple(_explain(model, child) for child in selected))


def explain(model, trace: Trace) -> Explanation:
    """Verifica toda la traza antes de producir una sola explicación."""
    check_trace(model, trace)
    return _explain(model, trace)
