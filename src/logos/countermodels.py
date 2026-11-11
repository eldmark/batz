"""Búsqueda acotada de contramodelos para sentencias del perfil MM3032."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from time import monotonic

from .errors import LogosError
from .explain import Explanation, explain
from .interpretation import _signature, build_interpretation
from .model import FiniteModel
from .semantics import evaluate, is_countermodel
from .story import Story, build_story
from .symbols import Signature, parse_checked
from .transform import free_vars


@dataclass(frozen=True)
class CountermodelConfig:
    max_size: int = 3
    max_candidates: int = 5000
    timeout: float = 2.0
    max_table_rows: int = 12

    def __post_init__(self):
        if (type(self.max_size) is not int or not 1 <= self.max_size <= 5 or
            type(self.max_candidates) is not int or not 1 <= self.max_candidates <= 100_000 or
            type(self.timeout) not in (int, float) or not 0 < self.timeout <= 30 or
            type(self.max_table_rows) is not int or not 1 <= self.max_table_rows <= 20):
            raise ValueError("límites de búsqueda inválidos")


@dataclass(frozen=True)
class CountermodelSearch:
    status: str  # found | unknown
    model: FiniteModel | None
    explanation: Explanation | None
    explored: int
    completed_sizes: tuple[int, ...]
    reason: str | None = None
    story: Story | None = None

    def to_dict(self):
        result = {"status": self.status, "explored": self.explored,
                  "completed_sizes": list(self.completed_sizes)}
        if self.status == "found":
            result["model"] = self.model.to_dict()
            result["explanation"] = self.explanation.to_dict()
            result["story"] = self.story.to_dict()
        else:
            result["reason"] = self.reason
        return result


def _models(signature, domain):
    """Enumera estructuras estrictas sin almacenar el producto cartesiano completo."""
    parts = ([("constant", name, 0) for name in sorted(signature.constants)] +
             [("function", name, arity) for name, arity in sorted(signature.functions.items())] +
             [("predicate", name, arity) for name, arity in sorted(signature.predicates.items())])
    constants, functions, predicates = {}, {}, {}

    def options(kind, arity):
        if kind == "constant":
            yield from domain
            return
        keys = tuple(product(domain, repeat=arity))
        if kind == "function":
            for outputs in product(domain, repeat=len(keys)):
                yield (arity, dict(zip(keys, outputs)))
        else:
            # Una relación vacía está excluida por el perfil MM3032.
            for mask in range(1, 1 << len(keys)):
                yield (arity, [key for i, key in enumerate(keys) if mask & (1 << i)])

    def walk(index):
        if index == len(parts):
            yield FiniteModel(domain, constants, functions, predicates)
            return
        kind, name, arity = parts[index]
        target = {"constant": constants, "function": functions, "predicate": predicates}[kind]
        for option in options(kind, arity):
            target[name] = option
            yield from walk(index + 1)
        target.pop(name, None)

    yield from walk(0)


def find_countermodel(signature: Signature, text: str,
                      config: CountermodelConfig | None = None) -> CountermodelSearch:
    """Busca un modelo estricto que falsifique una sentencia.

    `unknown` solo informa que no apareció dentro de los límites explorados.
    Un hallazgo se reconstruye, se verifica semánticamente y se explica.
    """
    _signature(signature)
    if not isinstance(text, str):
        raise LogosError("syntactic", "expected_formula", "la fórmula debe ser texto")
    formula = parse_checked(text, signature, strict=True)
    variables = sorted(free_vars(formula))
    if variables:
        raise LogosError("semantic", "unassigned_variable",
                         f"la búsqueda requiere una sentencia; variables libres: {', '.join(variables)}",
                         formula.span, text)
    cfg = config or CountermodelConfig()
    if not isinstance(cfg, CountermodelConfig):
        raise ValueError("config debe ser CountermodelConfig")
    explored = 0
    completed = []
    deadline = monotonic() + cfg.timeout
    for size in range(1, cfg.max_size + 1):
        if any(size ** arity > cfg.max_table_rows for arity in
               (*signature.functions.values(), *signature.predicates.values())):
            return CountermodelSearch("unknown", None, None, explored, tuple(completed), "table_limit")
        for model in _models(signature, tuple(range(size))):
            if explored >= cfg.max_candidates:
                return CountermodelSearch("unknown", None, None, explored, tuple(completed), "candidate_limit")
            if monotonic() >= deadline:
                return CountermodelSearch("unknown", None, None, explored, tuple(completed), "timeout")
            explored += 1
            if not is_countermodel(model, [], formula):
                continue
            # Revalidación del perfil y de la traza antes de presentar un hallazgo.
            checked = build_interpretation(signature, model.to_dict())
            trace = evaluate(checked, formula)
            explanation = explain(checked, trace)
            if trace.value is not False:
                raise AssertionError("el hallazgo no falsifica la fórmula")
            return CountermodelSearch("found", checked, explanation, explored, tuple(completed),
                                      story=build_story(checked, trace))
        completed.append(size)
    return CountermodelSearch("unknown", None, None, explored, tuple(completed), "size_limit")
