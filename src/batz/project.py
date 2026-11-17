"""Fachada de evaluación para la interfaz del proyecto MM3032."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from .ast import is_term_name
from .errors import BatzError
from .explain import Explanation, explain
from .interpretation import _signature, build_interpretation
from .model import FiniteModel
from .semantics import Trace, evaluate
from .story import Story, build_story
from .symbols import Signature, parse_checked
from .transform import free_vars


@dataclass(frozen=True)
class Resultado:
    status: str
    value: bool | None = None
    trace: Trace | None = None
    explanation: Explanation | None = None
    story: Story | None = None
    model: FiniteModel | None = None
    errors: tuple[dict, ...] = ()


def libres(texto: str, firma: Signature | None = None) -> tuple[str, ...]:
    """Variables libres que la interfaz debe solicitar para esta fórmula."""
    if not isinstance(texto, str):
        raise BatzError("syntactic", "expected_formula", "la fórmula debe ser texto")
    strict = firma is not None
    firma = firma or Signature()
    _signature(firma)
    return tuple(sorted(free_vars(parse_checked(texto, firma, strict=strict))))


def evaluar(firma: Signature, interpretacion: dict, texto: str,
            entorno: dict | None = None) -> Resultado:
    """Solo retorna valor después de validar entrada y verificar la traza."""
    try:
        model = build_interpretation(firma, interpretacion)
        if not isinstance(texto, str):
            raise BatzError("syntactic", "expected_formula", "la fórmula debe ser texto")
        formula = parse_checked(texto, firma, strict=True)
        if entorno is not None and not isinstance(entorno, Mapping):
            raise BatzError("semantic", "invalid_assignment", "el entorno debe ser un objeto")
        if entorno is not None and any(type(v) not in (int, str) for v in entorno.values()):
            raise BatzError("semantic", "invalid_assignment", "el entorno contiene un valor no válido")
        declared = set(firma.constants) | set(firma.functions) | set(firma.predicates)
        for name in entorno or {}:
            if not is_term_name(name) or name in declared:
                raise BatzError("semantic", "invalid_assignment",
                                 f"'{name}' no es una variable: el entorno solo asigna variables")
        trace = evaluate(model, formula, entorno)
        explanation = explain(model, trace)
        story = build_story(model, trace)
        return Resultado("ok", trace.value, trace, explanation, story, model)
    except BatzError as exc:
        return Resultado("invalid_input", errors=(exc.to_diagnostic(),))
