"""Evaluación de términos y fórmulas en un modelo finito (docs/specs/SEMANTICS.md)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .ast import (
    And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred, Var,
    _Binary, _Quant,
)
from .errors import BatzError
from .transform import free_vars


def _err(code, message, node=None):
    return BatzError("semantic", code, message, getattr(node, "span", None))


# --- validación previa ------------------------------------------------------

def _check_term(model, t):
    if isinstance(t, Const):
        if t.name not in model.constants:
            raise _err("missing_interpretation", f"el modelo no interpreta la constante '{t.name}'", t)
    elif isinstance(t, Func):
        fn = model.functions.get(t.name)
        if fn is None:
            raise _err("missing_interpretation", f"el modelo no interpreta la función '{t.name}'", t)
        if fn.arity != len(t.args):
            raise _err("model_arity_mismatch", f"la función '{t.name}' tiene aridad {fn.arity} en el modelo y se usa con {len(t.args)}", t)
        for a in t.args:
            _check_term(model, a)


def _check_symbols(model, f):
    if isinstance(f, Bottom):
        return
    if isinstance(f, Pred):
        rel = model.predicates.get(f.name)
        if rel is None:
            raise _err("missing_interpretation", f"el modelo no interpreta el predicado '{f.name}'", f)
        if rel.arity != len(f.args):
            raise _err("model_arity_mismatch", f"el predicado '{f.name}' tiene aridad {rel.arity} en el modelo y se usa con {len(f.args)}", f)
        for a in f.args:
            _check_term(model, a)
    elif isinstance(f, Eq):
        _check_term(model, f.left)
        _check_term(model, f.right)
    elif isinstance(f, Not):
        _check_symbols(model, f.operand)
    elif isinstance(f, _Binary):
        _check_symbols(model, f.left)
        _check_symbols(model, f.right)
    elif isinstance(f, _Quant):
        _check_symbols(model, f.body)
    else:
        raise TypeError(f"nodo desconocido: {f!r}")


def _prepare(model, f, assignment):
    """Valida símbolos y asignación; devuelve la asignación como dict nuevo."""
    s = dict(assignment or {})
    dset = set(model.domain)
    for var, val in s.items():
        if val not in dset:
            raise _err("invalid_assignment", f"'{var}' vale {val!r}, que no está en el dominio")
    _check_symbols(model, f)
    missing = sorted(free_vars(f) - set(s))
    if missing:
        raise _err("unassigned_variable", f"falta asignar la(s) variable(s) libre(s): {', '.join(missing)}", f)
    return s


# --- términos y fórmulas ----------------------------------------------------

def eval_term(model, t, assignment):
    if isinstance(t, Var):
        return assignment[t.name]
    if isinstance(t, Const):
        return model.constants[t.name]
    return model.functions[t.name].table[tuple(eval_term(model, a, assignment) for a in t.args)]


def _holds(model, f, s):
    if isinstance(f, Bottom):
        return False
    if isinstance(f, Pred):
        return tuple(eval_term(model, a, s) for a in f.args) in model.predicates[f.name].tuples
    if isinstance(f, Eq):
        return eval_term(model, f.left, s) == eval_term(model, f.right, s)
    if isinstance(f, Not):
        return not _holds(model, f.operand, s)
    if isinstance(f, And):
        return _holds(model, f.left, s) and _holds(model, f.right, s)
    if isinstance(f, Or):
        return _holds(model, f.left, s) or _holds(model, f.right, s)
    if isinstance(f, Implies):
        return (not _holds(model, f.left, s)) or _holds(model, f.right, s)
    if isinstance(f, Iff):
        return _holds(model, f.left, s) == _holds(model, f.right, s)
    if isinstance(f, Forall):
        return all(_holds(model, f.body, {**s, f.var: d}) for d in model.domain)
    if isinstance(f, Exists):
        return any(_holds(model, f.body, {**s, f.var: d}) for d in model.domain)
    raise TypeError(f"nodo desconocido: {f!r}")


def holds(model, f, assignment=None):
    """¿`model, assignment ⊨ f`? Las fórmulas abiertas exigen asignación explícita."""
    return _holds(model, f, _prepare(model, f, assignment))


def is_true(model, sentence):
    """Verdad de una sentencia (fórmula cerrada) en el modelo."""
    fv = free_vars(sentence)
    if fv:
        raise _err("unassigned_variable", f"no es una sentencia: variable(s) libre(s) {', '.join(sorted(fv))}", sentence)
    return holds(model, sentence)


def is_countermodel(model, premises, conclusion):
    """¿El modelo hace verdaderas todas las premisas y falsa la conclusión?

    Refuta `premises ⊨ conclusion`. Todas las fórmulas deben ser sentencias.
    """
    return all(is_true(model, p) for p in premises) and not is_true(model, conclusion)


# --- trazas -----------------------------------------------------------------

@dataclass(frozen=True)
class Trace:
    """Nodo del árbol de evaluación (sin cortocircuito).

    `assignment`: pares `(variable, elemento)` de las variables libres de `formula`.
    `term_values`: valor de cada argumento (solo átomos).
    `element`: elemento instanciado, en los hijos de un cuantificador.
    """

    formula: object
    value: bool
    assignment: tuple
    children: tuple = ()
    term_values: tuple = ()
    element: Optional[object] = None


def _restrict(f, s):
    return tuple(sorted((v, s[v]) for v in free_vars(f)))


def _trace(model, f, s, element=None):
    assign = _restrict(f, s)
    if isinstance(f, Bottom):
        return Trace(f, False, assign, (), (), element)
    if isinstance(f, Pred):
        vals = tuple(eval_term(model, a, s) for a in f.args)
        return Trace(f, vals in model.predicates[f.name].tuples, assign, (), vals, element)
    if isinstance(f, Eq):
        vals = (eval_term(model, f.left, s), eval_term(model, f.right, s))
        return Trace(f, vals[0] == vals[1], assign, (), vals, element)
    if isinstance(f, Not):
        c = _trace(model, f.operand, s)
        return Trace(f, not c.value, assign, (c,), (), element)
    if isinstance(f, _Binary):
        l, r = _trace(model, f.left, s), _trace(model, f.right, s)
        return Trace(f, _combine(f, l.value, r.value), assign, (l, r), (), element)
    kids = tuple(_trace(model, f.body, {**s, f.var: d}, element=d) for d in model.domain)
    vals = [k.value for k in kids]
    return Trace(f, all(vals) if isinstance(f, Forall) else any(vals), assign, kids, (), element)


def _combine(f, a, b):
    if isinstance(f, And):
        return a and b
    if isinstance(f, Or):
        return a or b
    if isinstance(f, Implies):
        return (not a) or b
    return a == b  # Iff


def evaluate(model, f, assignment=None):
    """Evalúa y devuelve la traza completa; `trace.value` es el resultado."""
    return _trace(model, f, _prepare(model, f, assignment))


def _bad_trace(message, node):
    return BatzError("semantic", "invalid_trace", message, getattr(node.formula, "span", None))


def check_trace(model, trace):
    """Re-verifica cada nodo de la traza localmente. Lanza `invalid_trace` si falla."""
    f = trace.formula
    _check_symbols(model, f)
    s = dict(trace.assignment)
    if set(s) != set(free_vars(f)) or any(v not in set(model.domain) for v in s.values()):
        raise _bad_trace("la asignación del nodo no corresponde a las variables libres", trace)

    if isinstance(f, Bottom):
        if trace.children or trace.term_values or trace.value is not False:
            raise _bad_trace("⊥ debe valer falso y no tener hijos", trace)
        return

    if isinstance(f, (Pred, Eq)):
        args = f.args if isinstance(f, Pred) else (f.left, f.right)
        vals = tuple(eval_term(model, a, s) for a in args)
        value = vals in model.predicates[f.name].tuples if isinstance(f, Pred) else vals[0] == vals[1]
        if trace.children or trace.term_values != vals or trace.value != value:
            raise _bad_trace("átomo inconsistente con el modelo", trace)
        return

    if isinstance(f, Not):
        kids = [f.operand]
    elif isinstance(f, _Binary):
        kids = [f.left, f.right]
    else:
        kids = [f.body] * len(model.domain)
    if len(trace.children) != len(kids) or trace.term_values:
        raise _bad_trace("número de hijos incorrecto", trace)

    for i, (child, sub) in enumerate(zip(trace.children, kids)):
        if child.formula != sub:
            raise _bad_trace("el hijo no corresponde a la subfórmula", trace)
        if isinstance(f, _Quant):
            d = model.domain[i]
            if child.element != d or dict(child.assignment) != {
                v: x for v, x in {**s, f.var: d}.items() if v in free_vars(sub)
            }:
                raise _bad_trace("instanciación incorrecta del cuantificador", trace)
        else:
            if child.element is not None or dict(child.assignment) != {v: s[v] for v in free_vars(sub)}:
                raise _bad_trace("asignación del hijo incorrecta", trace)
        check_trace(model, child)

    vals = [c.value for c in trace.children]
    if isinstance(f, Not):
        value = not vals[0]
    elif isinstance(f, Forall):
        value = all(vals)
    elif isinstance(f, Exists):
        value = any(vals)
    else:
        value = _combine(f, vals[0], vals[1])
    if trace.value != value:
        raise _bad_trace("el valor del nodo no se sigue de sus hijos", trace)
