"""Búsqueda acotada de contramodelos.

Dos búsquedas con el mismo motor de enumeración:
- `find_countermodel`: un modelo estricto del perfil MM3032 que falsifique una sentencia.
- `find_consequence_countermodel`: un modelo de la semántica estándar (admite relaciones vacías
  y letras proposicionales) donde las premisas son verdaderas y la conclusión falsa.

`unknown` solo informa que no apareció dentro de los límites explorados; nunca es «válida».
Todo hallazgo se vuelve a evaluar con el evaluador de la Fase 2 antes de presentarse, y la
búsqueda deja una bitácora (tamaños, candidatos, un ejemplo descartado) para narrarla.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from time import monotonic

from .errors import BatzError, SCHEMA_VERSION
from .explain import Explanation, _explain, explain
from .interpretation import _signature, build_interpretation
from .model import FiniteModel
from .printer import to_string
from .semantics import evaluate, holds, is_countermodel
from .story import Story, build_story
from .symbols import Signature, check, parse_checked
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


# ── Bitácora y narración de la búsqueda ──

def _value(value):
    return f'"{value}"' if isinstance(value, str) else str(value)


def describe(model: FiniteModel, limit: int = 120):
    """Interpretación en una línea («a = 0, P = {0, 2}»), o None si no cabe en `limit`."""
    data = model.to_dict()
    parts = [f"{name} = {_value(value)}" for name, value in data["constants"].items()]
    for name, spec in data["functions"].items():
        cells = ", ".join(f"{name}({', '.join(map(_value, args))}) = {_value(out)}" for args, out in spec["table"])
        parts.append(cells)
    for name, spec in data["predicates"].items():
        if spec["arity"] == 0:
            parts.append(f"{name} {'verdadera' if spec['tuples'] else 'falsa'}")
        else:
            items = [_value(t[0]) if spec["arity"] == 1 else f"({', '.join(map(_value, t))})" for t in spec["tuples"]]
            parts.append(f"{name} = {{{', '.join(items)}}}" if items else f"{name} = ∅")
    text = ", ".join(parts)
    return text if len(text) <= limit else None


def _elements(n):
    return f"{n} elemento" if n == 1 else f"{n} elementos"


def _interpretations(n):
    return f"{n} interpretación" if n == 1 else f"{n} interpretaciones"


def search_events(log, goal, consequence=False):
    """Eventos del paso a paso que cuentan la búsqueda antes de mostrar el hallazgo."""
    if consequence:
        intro = "Busco un modelo donde todas las premisas sean verdaderas y la conclusión falsa. Empiezo por dominios pequeños."
    else:
        intro = f"Busco un modelo donde {goal} sea falsa. Empiezo por dominios pequeños."
    events = [{"kind": "search", "text_es": intro, "size": 0, "phase": "start"}]
    for entry in log:
        size, explored = entry["size"], entry["explored"]
        if entry.get("found"):
            what = "las premisas son verdaderas y la conclusión, falsa" if consequence else f"{goal} es falsa"
            text = (f"Con {_elements(size)}, la interpretación número {explored} sirve: en ella {what}. "
                    "Este es el contramodelo.")
            events.append({"kind": "search", "text_es": text, "size": size, "phase": "found"})
            continue
        if consequence:
            where = "en ella no" if explored == 1 else "en ninguna"
            text = (f"Con {_elements(size)} revisé {_interpretations(explored)}: {where} son verdaderas "
                    "las premisas con la conclusión falsa.")
        else:
            text = (f"Con {_elements(size)} revisé {_interpretations(explored)}: "
                    f"{'en ella' if explored == 1 else 'en todas'}, {goal} es verdadera.")
        if entry.get("example"):
            text += f" Por ejemplo, con {entry['example']} no sirve."
        events.append({"kind": "search", "text_es": text, "size": size, "phase": "none"})
    for i, event in enumerate(events):
        event.update({"trace_path": f"s{i}", "formula": goal, "value": None, "span": None, "assignment": {},
                      "element": None, "relation": None, "term_values": [],
                      "verified_by": {"countermodel_search": True}})
    return events


def _join_story(*parts):
    events = [event for part in parts for event in part]
    for i, event in enumerate(events):
        event["id"] = i + 1
    return {"schema_version": SCHEMA_VERSION, "events": events}


@dataclass(frozen=True)
class CountermodelSearch:
    status: str  # found | unknown
    model: FiniteModel | None
    explanation: Explanation | None
    explored: int
    completed_sizes: tuple[int, ...]
    reason: str | None = None
    story: Story | None = None
    log: tuple = ()
    goal: str | None = None

    def to_dict(self):
        result = {"status": self.status, "explored": self.explored,
                  "completed_sizes": list(self.completed_sizes), "log": list(self.log)}
        if self.status == "found":
            result["model"] = self.model.to_dict()
            result["explanation"] = self.explanation.to_dict()
            result["story"] = _join_story(search_events(self.log, self.goal), self.story.to_dict()["events"])
        else:
            result["reason"] = self.reason
        return result


# ── Enumeración ──

def _models(signature, domain, allow_empty=False, skip_strict=False):
    """Enumera estructuras sin almacenar el producto cartesiano completo.

    Sin `allow_empty` cada relación tiene al menos una tupla (perfil MM3032). Con `skip_strict`
    se omiten las que no tienen ninguna relación vacía: ya se revisaron en la pasada estricta.
    """
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
            for mask in range(0 if allow_empty else 1, 1 << len(keys)):
                yield (arity, [key for i, key in enumerate(keys) if mask & (1 << i)])

    def walk(index):
        if index == len(parts):
            if skip_strict and all(tuples for _, tuples in predicates.values()):
                return
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
        raise BatzError("syntactic", "expected_formula", "la fórmula debe ser texto")
    formula = parse_checked(text, signature, strict=True)
    variables = sorted(free_vars(formula))
    if variables:
        raise BatzError("semantic", "unassigned_variable",
                         f"la búsqueda requiere una sentencia; variables libres: {', '.join(variables)}",
                         formula.span, text)
    cfg = config or CountermodelConfig()
    if not isinstance(cfg, CountermodelConfig):
        raise ValueError("config debe ser CountermodelConfig")
    goal = to_string(formula)
    explored = 0
    completed, log = [], []
    deadline = monotonic() + cfg.timeout
    for size in range(1, cfg.max_size + 1):
        if any(size ** arity > cfg.max_table_rows for arity in
               (*signature.functions.values(), *signature.predicates.values())):
            return CountermodelSearch("unknown", None, None, explored, tuple(completed), "table_limit", log=tuple(log))
        in_size, example = 0, None
        for model in _models(signature, tuple(range(size))):
            if explored >= cfg.max_candidates:
                return CountermodelSearch("unknown", None, None, explored, tuple(completed), "candidate_limit", log=tuple(log))
            if monotonic() >= deadline:
                return CountermodelSearch("unknown", None, None, explored, tuple(completed), "timeout", log=tuple(log))
            explored += 1
            in_size += 1
            if not is_countermodel(model, [], formula):
                example = example or model
                continue
            # Revalidación del perfil y de la traza antes de presentar un hallazgo.
            checked = build_interpretation(signature, model.to_dict())
            trace = evaluate(checked, formula)
            explanation = explain(checked, trace)
            if trace.value is not False:
                raise AssertionError("el hallazgo no falsifica la fórmula")
            log.append({"size": size, "explored": in_size, "found": True})
            return CountermodelSearch("found", checked, explanation, explored, tuple(completed),
                                      story=build_story(checked, trace), log=tuple(log), goal=goal)
        completed.append(size)
        log.append({"size": size, "explored": in_size, "example": describe(example) if example else None})
    return CountermodelSearch("unknown", None, None, explored, tuple(completed), "size_limit", log=tuple(log))


# ── Consecuencia: premisas verdaderas y conclusión falsa ──

@dataclass(frozen=True)
class ConsequenceSearch:
    status: str  # found | unknown
    explored: int
    completed_sizes: tuple
    reason: str | None = None
    model: FiniteModel | None = None
    assignment: dict | None = None
    signature: Signature | None = None
    premises: tuple = ()
    conclusion: object = None
    log: tuple = ()

    @property
    def loadable(self):
        """¿Cabe en las tablas del modo Evaluar? Ese perfil no admite relaciones vacías ni aridad 0."""
        if self.model is None:
            return False
        return all(arity >= 1 and tuples for arity, tuples in
                   ((r.arity, r.tuples) for r in self.model.predicates.values()))

    def to_dict(self):
        result = {"status": self.status, "explored": self.explored,
                  "completed_sizes": list(self.completed_sizes), "log": list(self.log)}
        if self.status != "found":
            result["reason"] = self.reason
            return result
        model, s = self.model, self.assignment
        premise_events, premises = [], []
        for i, premise in enumerate(self.premises):
            trace = evaluate(model, premise, s or None)
            summary = _explain(model, trace).summary
            premises.append({"formula": to_string(premise), "value": trace.value, "summary": summary})
            premise_events.append({"kind": "premise", "trace_path": f"q{i}", "formula": to_string(premise),
                                   "value": trace.value, "text_es": f"La premisa {to_string(premise)} es verdadera: {summary}",
                                   "span": None, "assignment": dict(s), "element": None, "relation": None,
                                   "term_values": [], "verified_by": {"premise": i}})
        trace = evaluate(model, self.conclusion, s or None)
        story = build_story(model, trace).to_dict()["events"]
        for event in story:  # las rutas de la conclusión no chocan con las de la búsqueda
            event["formula_role"] = "conclusion"
        sig = self.signature
        result.update({
            "model": model.to_dict(), "assignment": [[k, v] for k, v in sorted(s.items())],
            "premises": premises, "explanation": explain(model, trace).to_dict(),
            "signature": {"constants": sorted(sig.constants), "functions": dict(sig.functions),
                          "predicates": dict(sig.predicates)},
            "loadable": self.loadable,
            "story": _join_story(search_events(self.log, to_string(self.conclusion), consequence=True),
                                 premise_events, story),
        })
        return result


def consequence_signature(formulas, constants=()):
    """Firma mínima de un conjunto de fórmulas: sus constantes, funciones y predicados."""
    sig = Signature(constants=frozenset(constants))
    for formula in formulas:
        sig = check(formula, sig)
    return sig


def find_consequence_countermodel(premises, conclusion, constants=(),
                                  config: CountermodelConfig | None = None) -> ConsequenceSearch:
    """Busca un modelo (y entorno, si hay variables libres) donde valen las premisas y falla la conclusión.

    En cada tamaño de dominio se prueban primero las estructuras sin relaciones vacías, que se
    pueden abrir en el modo Evaluar, y después las demás.
    """
    cfg = config or CountermodelConfig(max_size=3, max_candidates=20_000, timeout=2.0, max_table_rows=16)
    formulas = [*premises, conclusion]
    sig = consequence_signature(formulas, constants)
    variables = sorted(set().union(*(free_vars(f) for f in formulas)) - set(sig.constants))
    explored, completed, log = 0, [], []
    deadline = monotonic() + cfg.timeout

    def stop(reason):
        return ConsequenceSearch("unknown", explored, tuple(completed), reason, log=tuple(log))

    for size in range(1, cfg.max_size + 1):
        if any(size ** arity > cfg.max_table_rows for arity in (*sig.functions.values(), *sig.predicates.values())):
            return stop("table_limit")
        domain = tuple(range(size))
        in_size, example = 0, None
        for strict in (True, False):
            for model in _models(sig, domain, allow_empty=not strict, skip_strict=not strict):
                for values in product(domain, repeat=len(variables)):
                    if explored >= cfg.max_candidates:
                        return stop("candidate_limit")
                    if monotonic() >= deadline:
                        return stop("timeout")
                    explored += 1
                    in_size += 1
                    s = dict(zip(variables, values))
                    if not all(holds(model, p, s or None) for p in premises) or holds(model, conclusion, s or None):
                        if example is None and not variables:
                            example = model
                        continue
                    # El evaluador de la Fase 2 confirma el hallazgo con una traza verificada.
                    if not all(evaluate(model, p, s or None).value for p in premises) or evaluate(model, conclusion, s or None).value:
                        raise AssertionError("el hallazgo no refuta la consecuencia")
                    log.append({"size": size, "explored": in_size, "found": True})
                    return ConsequenceSearch("found", explored, tuple(completed), None, model, s, sig,
                                             tuple(premises), conclusion, tuple(log))
        completed.append(size)
        log.append({"size": size, "explored": in_size, "example": describe(example) if example else None})
    return stop("size_limit")
