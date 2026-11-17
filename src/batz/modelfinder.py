"""Búsqueda de un modelo finito por instanciación, para conjuntos con muchas fórmulas.

`countermodels.py` enumera interpretaciones completas: sirve para pocas premisas y es fácil de
narrar, pero con una docena de predicados no pasa de dominios de un elemento. Aquí, para cada
tamaño de dominio, los cuantificadores se despliegan sobre los elementos (∀ como conjunción,
∃ como disyunción) y queda un problema proposicional sobre átomos `P(0, 1)`, que se resuelve
con retroceso y propagación de las disyunciones de una sola opción.

Es una heurística de búsqueda, no un decisor: todo modelo que devuelve se vuelve a evaluar
con el evaluador de la Fase 2 (`is_true`) antes de entregarse, y no encontrar uno no dice nada.

Orden de la búsqueda: primero dominios donde cada nombre propio es un individuo distinto
(un contramodelo donde «Juan» y «María» son la misma persona se entiende peor); después,
dominios de 1 en adelante permitiendo que varios nombres coincidan.
"""
from __future__ import annotations

from itertools import product
from time import monotonic

from .ast import And, Bottom, Const, Eq, Exists, Forall, Iff, Implies, Not, Or, Pred, Var
from .model import FiniteModel
from .semantics import is_true
from .symbols import Signature, check
from .transform import free_vars

MAX_NODES = 150_000   # nodos del problema proposicional de un intento (tamaño × constantes)


class _GiveUp(Exception):
    """Límite de tiempo o de tamaño: se abandona el intento sin afirmar nada."""


class _Grounder:
    def __init__(self, size, constants, deadline):
        self.domain = range(size)
        self.constants = constants
        self.deadline = deadline
        self.nodes = 0

    def count(self, n=1):
        self.nodes += n
        if self.nodes > MAX_NODES or (self.nodes & 1023 == 0 and monotonic() >= self.deadline):
            raise _GiveUp

    def term(self, t, env):
        if isinstance(t, Var):
            return env[t.name]
        if isinstance(t, Const):
            return self.constants[t.name]
        raise _GiveUp  # símbolos de función: los cubre la enumeración de `countermodels.py`

    def all_of(self, items):
        out = []
        for item in items:
            if item is False:
                return False
            if item is True:
                continue
            out.extend(item[1]) if item[0] == "and" else out.append(item)
        return True if not out else out[0] if len(out) == 1 else ("and", out)

    def any_of(self, items):
        out = []
        for item in items:
            if item is True:
                return True
            if item is False:
                continue
            out.extend(item[1]) if item[0] == "or" else out.append(item)
        return False if not out else out[0] if len(out) == 1 else ("or", out)

    def ground(self, f, env, want):
        """Forma normal negativa de «`f` vale `want`» en el dominio: True, False, literal, and u or."""
        self.count()
        g = self.ground
        if isinstance(f, Pred):
            return ("lit", (f.name, tuple(self.term(a, env) for a in f.args)), want)
        if isinstance(f, Eq):
            return (self.term(f.left, env) == self.term(f.right, env)) == want
        if isinstance(f, Bottom):
            return not want
        if isinstance(f, Not):
            return g(f.operand, env, not want)
        if isinstance(f, (And, Or)):
            parts = (g(f.left, env, want), g(f.right, env, want))
            return self.all_of(parts) if isinstance(f, And) == want else self.any_of(parts)
        if isinstance(f, Implies):
            parts = (g(f.left, env, not want), g(f.right, env, want))
            return self.any_of(parts) if want else self.all_of(parts)
        if isinstance(f, Iff):
            same = lambda a, b: self.all_of((g(f.left, env, a), g(f.right, env, b)))
            return self.any_of((same(True, want), same(False, not want)))
        if isinstance(f, (Forall, Exists)):
            parts = (g(f.body, {**env, f.var: d}, want) for d in self.domain)
            return self.all_of(parts) if isinstance(f, Forall) == want else self.any_of(parts)
        raise TypeError(f"nodo desconocido: {f!r}")


def _satisfy(todo, ors, val, deadline):
    """Extiende la valuación `val` (átomo → bool) para cumplir `todo` y las disyunciones `ors`."""
    if monotonic() >= deadline:
        raise _GiveUp
    todo, ors = list(todo), list(ors)
    while True:
        while todo:
            item = todo.pop()
            if item[0] == "lit":
                if val.setdefault(item[1], item[2]) != item[2]:
                    return None
            elif item[0] == "and":
                todo.extend(item[1])
            else:
                ors.append(item[1])
        pending = []
        for options in ors:
            open_options, done = [], False
            for option in options:
                known = val.get(option[1]) if option[0] == "lit" else None
                if known is None:
                    open_options.append(option)
                elif known == option[2]:
                    done = True
                    break
            if done:
                continue
            if not open_options:
                return None
            if len(open_options) == 1:
                todo.append(open_options[0])   # una sola opción: es obligatoria
            else:
                pending.append(open_options)
        ors = pending
        if not todo:
            break
    if not ors:
        return val
    # Se ramifica por la disyunción más corta; los literales negativos primero dejan relaciones pequeñas.
    at = min(range(len(ors)), key=lambda i: len(ors[i]))
    rest = ors[:at] + ors[at + 1:]
    for option in sorted(ors[at], key=lambda o: (o[0] != "lit", o[0] == "lit" and o[2])):
        found = _satisfy([option], rest, dict(val), deadline)
        if found is not None:
            return found
    return None


def _groupings(names, size):
    """Valores de las constantes sin repetir casos simétricos: cada una usa un valor ya visto o el siguiente."""
    def walk(i, used):
        if i == len(names):
            yield ()
            return
        for value in range(min(used + 1, size)):
            for rest in walk(i + 1, max(used, value + 1)):
                yield (value, *rest)
    for values in walk(0, 0):
        yield dict(zip(names, values))


def find_model(formulas, constants=(), max_size=4, timeout=2.0):
    """Un `FiniteModel` donde todas las sentencias de `formulas` son verdaderas, o None.

    None significa «no apareció dentro de los límites», nunca «no existe».
    """
    formulas = list(formulas)
    sig = Signature(constants=frozenset(constants))
    for f in formulas:
        sig = check(f, sig)
    if sig.functions or any(free_vars(f) for f in formulas):
        return None
    names = sorted(sig.constants)
    deadline = monotonic() + timeout
    attempts = [(size, dict(zip(names, range(len(names)))))            # nombres distintos, individuos distintos
                for size in range(max(len(names), 1), max(len(names), 1) + 2)]
    attempts += [(size, values) for size in range(1, max_size + 1) for values in _groupings(names, size)
                 if len(set(values.values())) < len(names)]
    for size, values in attempts:
        grounder = _Grounder(size, values, deadline)
        try:
            problem = [grounder.ground(f, {}, True) for f in formulas]
            if any(item is False for item in problem):
                continue
            val = _satisfy([item for item in problem if item is not True], [], {}, deadline)
        except _GiveUp:
            if monotonic() >= deadline:
                return None
            continue   # este tamaño no cabe: quizá uno más pequeño sí
        if val is None:
            continue
        predicates = {name: (arity, [args for (pred, args), value in val.items() if value and pred == name])
                      for name, arity in sig.predicates.items()}
        model = FiniteModel(tuple(range(size)), values, {}, predicates)
        if not all(is_true(model, f) for f in formulas):   # el evaluador de la Fase 2 tiene la última palabra
            raise AssertionError("el modelo hallado no satisface las fórmulas")
        return model
    return None
