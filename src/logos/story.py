"""Guion de narración y eventos visuales derivados de una traza verificada."""
from __future__ import annotations

from dataclasses import dataclass

from .ast import Bottom, Eq, Exists, Forall, Pred
from .errors import SCHEMA_VERSION
from .explain import _explain
from .printer import to_string
from .semantics import Trace, check_trace


@dataclass(frozen=True)
class StoryEvent:
    id: int
    trace_path: str
    kind: str
    formula: str
    value: bool
    text_es: str
    span: tuple[int, int] | None
    assignment: tuple
    element: object | None
    relation: str | None
    term_values: tuple

    def to_dict(self):
        return {"id": self.id, "trace_path": self.trace_path, "kind": self.kind,
                "formula": self.formula, "value": self.value, "text_es": self.text_es,
                "span": list(self.span) if self.span is not None else None,
                "assignment": dict(self.assignment), "element": self.element,
                "relation": self.relation, "term_values": list(self.term_values),
                "verified_by": {"trace_path": self.trace_path}}


@dataclass(frozen=True)
class Story:
    events: tuple[StoryEvent, ...]

    def to_dict(self):
        return {"schema_version": SCHEMA_VERSION,
                "events": [event.to_dict() for event in self.events]}


def build_story(model, trace: Trace) -> Story:
    """Cada evento cita un nodo del árbol completo que `check_trace` aceptó."""
    check_trace(model, trace)
    events = []

    def walk(node, path):
        formula = node.formula
        if isinstance(formula, Pred):
            kind, relation = "predicate", formula.name
        elif isinstance(formula, Eq):
            kind, relation = "equality", None
        elif isinstance(formula, (Forall, Exists)):
            kind, relation = "quantifier", None
        elif isinstance(formula, Bottom):
            kind, relation = "bottom", None
        else:
            kind, relation = "connective", None
        span = getattr(formula, "span", None)
        events.append(StoryEvent(
            len(events) + 1, path, kind, to_string(formula), node.value,
            _explain(model, node).summary,
            None if span is None else (span.start, span.end),
            node.assignment, node.element, relation, node.term_values))
        for i, child in enumerate(node.children):
            walk(child, f"{path}.{i}")

    walk(trace, "0")
    return Story(tuple(events))
