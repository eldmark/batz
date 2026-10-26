"""Variables libres/ligadas, alfa-equivalencia, renombrado y sustitución sin captura."""
from __future__ import annotations

import re

from .ast import (
    And, Bottom, Const, Eq, Exists, Forall, Formula, Func, Iff, Implies, Not, Or, Pred, Term, Var,
    is_term_name, _Quant, _Binary,
)


def term_vars(t):
    """Nombres de variables que aparecen en un término."""
    if isinstance(t, Var):
        return frozenset({t.name})
    if isinstance(t, Func):
        return frozenset().union(*(term_vars(a) for a in t.args))
    return frozenset()


def free_vars(f):
    if isinstance(f, Bottom):
        return frozenset()
    if isinstance(f, Pred):
        return frozenset().union(*(term_vars(a) for a in f.args))
    if isinstance(f, Eq):
        return term_vars(f.left) | term_vars(f.right)
    if isinstance(f, Not):
        return free_vars(f.operand)
    if isinstance(f, _Binary):
        return free_vars(f.left) | free_vars(f.right)
    if isinstance(f, _Quant):
        return free_vars(f.body) - {f.var}
    raise TypeError(f"nodo desconocido: {f!r}")


def bound_vars(f):
    """Nombres cuantificados en algún punto de la fórmula."""
    if isinstance(f, (Pred, Eq, Bottom)):
        return frozenset()
    if isinstance(f, Not):
        return bound_vars(f.operand)
    if isinstance(f, _Binary):
        return bound_vars(f.left) | bound_vars(f.right)
    if isinstance(f, _Quant):
        return bound_vars(f.body) | {f.var}
    raise TypeError(f"nodo desconocido: {f!r}")


def all_var_names(f):
    """Todo nombre de variable (libre, ligada o cuantificada) que aparece."""
    return free_vars(f) | bound_vars(f) | _occurring_vars(f)


def _occurring_vars(f):
    if isinstance(f, Bottom):
        return frozenset()
    if isinstance(f, Pred):
        return frozenset().union(*(term_vars(a) for a in f.args))
    if isinstance(f, Eq):
        return term_vars(f.left) | term_vars(f.right)
    if isinstance(f, Not):
        return _occurring_vars(f.operand)
    if isinstance(f, _Binary):
        return _occurring_vars(f.left) | _occurring_vars(f.right)
    return _occurring_vars(f.body)


def is_closed(f):
    return not free_vars(f)


def fresh_name(base, avoid):
    """Nombre válido derivado de `base` que no está en `avoid`."""
    stem = re.sub(r"\d+$", "", base) or base
    k = 1
    while f"{stem}{k}" in avoid:
        k += 1
    name = f"{stem}{k}"
    assert is_term_name(name)
    return name


# --- sustitución ------------------------------------------------------------

def subst_term(t, mapping):
    if isinstance(t, Var):
        return mapping.get(t.name, t)
    if isinstance(t, Func):
        return Func(t.name, tuple(subst_term(a, mapping) for a in t.args))
    return t


def substitute(f, mapping):
    """Sustitución simultánea `f[x1:=t1, ...]` que evita la captura de variables.

    `mapping` va de nombres de variable a términos. Solo se sustituyen las
    ocurrencias libres; si un cuantificador capturaría una variable de un
    término insertado, su variable se renombra antes (alfa-conversión).
    """
    for name, t in mapping.items():
        if not is_term_name(name):
            raise ValueError(f"nombre de variable inválido: {name!r}")
        if not isinstance(t, Term):
            raise TypeError("la sustitución debe asignar términos")
    return _subst(f, dict(mapping))


def _subst(f, m):
    if not m or isinstance(f, Bottom):
        return f
    if isinstance(f, Pred):
        return Pred(f.name, tuple(subst_term(a, m) for a in f.args))
    if isinstance(f, Eq):
        return Eq(subst_term(f.left, m), subst_term(f.right, m))
    if isinstance(f, Not):
        return Not(_subst(f.operand, m))
    if isinstance(f, _Binary):
        return type(f)(_subst(f.left, m), _subst(f.right, m))
    if isinstance(f, _Quant):
        fv_body = free_vars(f.body)
        # Solo importan las variables libres del cuerpo, salvo la ligada.
        m2 = {k: t for k, t in m.items() if k != f.var and k in fv_body}
        if not m2:
            return f
        captured = frozenset().union(*(term_vars(t) for t in m2.values()))
        if f.var in captured:
            avoid = captured | all_var_names(f.body) | set(m2) | {f.var}
            new = fresh_name(f.var, avoid)
            return type(f)(new, _subst(f.body, {**m2, f.var: Var(new)}))
        return type(f)(f.var, _subst(f.body, m2))
    raise TypeError(f"nodo desconocido: {f!r}")


# --- alfa-equivalencia y renombrado ----------------------------------------

def alpha_equiv(a, b):
    """¿Son iguales salvo el nombre de las variables ligadas?"""
    return _alpha(a, b, {}, {}, 0)


def _alpha_term(s, t, ea, eb):
    if isinstance(s, Var) and isinstance(t, Var):
        la, lb = ea.get(s.name), eb.get(t.name)
        if la is None and lb is None:
            return s.name == t.name
        return la == lb  # ambas ligadas al mismo nivel (si una es libre: None != int)
    if isinstance(s, Const) and isinstance(t, Const):
        return s.name == t.name
    if isinstance(s, Func) and isinstance(t, Func):
        return (
            s.name == t.name
            and len(s.args) == len(t.args)
            and all(_alpha_term(x, y, ea, eb) for x, y in zip(s.args, t.args))
        )
    return False


def _alpha(a, b, ea, eb, depth):
    if type(a) is not type(b):
        return False
    if isinstance(a, Bottom):
        return True
    if isinstance(a, Pred):
        return (
            a.name == b.name
            and len(a.args) == len(b.args)
            and all(_alpha_term(x, y, ea, eb) for x, y in zip(a.args, b.args))
        )
    if isinstance(a, Eq):
        return _alpha_term(a.left, b.left, ea, eb) and _alpha_term(a.right, b.right, ea, eb)
    if isinstance(a, Not):
        return _alpha(a.operand, b.operand, ea, eb, depth)
    if isinstance(a, _Binary):
        return _alpha(a.left, b.left, ea, eb, depth) and _alpha(a.right, b.right, ea, eb, depth)
    if isinstance(a, _Quant):
        return _alpha(a.body, b.body, {**ea, a.var: depth}, {**eb, b.var: depth}, depth + 1)
    raise TypeError(f"nodo desconocido: {a!r}")


def alpha_rename(q, new_name):
    """Renombra la variable de un cuantificador `q` a `new_name`.

    Falla si `new_name` es libre en el cuerpo o ya está ligada dentro de él
    (el renombrado cambiaría el significado).
    """
    if not isinstance(q, _Quant):
        raise TypeError("alpha_rename espera un cuantificador")
    if not is_term_name(new_name):
        raise ValueError(f"nombre inválido: {new_name!r}")
    if new_name == q.var:
        return q
    if new_name in free_vars(q.body) or new_name in bound_vars(q.body):
        raise ValueError(f"'{new_name}' provocaría captura o confusión de variables")
    return type(q)(new_name, _subst(q.body, {q.var: Var(new_name)}))


def rename_bound_canonical(f, prefix="v"):
    """Forma canónica: variables ligadas renombradas a v1, v2... por profundidad.

    Dos fórmulas son alfa-equivalentes si y solo si sus formas canónicas son
    iguales (siempre que `prefix` no choque con variables libres).
    """
    return _canon(f, {}, 0, prefix)


def _canon_term(t, env):
    if isinstance(t, Var):
        return Var(env[t.name]) if t.name in env else t
    if isinstance(t, Func):
        return Func(t.name, tuple(_canon_term(a, env) for a in t.args))
    return t


def _canon(f, env, depth, prefix):
    if isinstance(f, Bottom):
        return f
    if isinstance(f, Pred):
        return Pred(f.name, tuple(_canon_term(a, env) for a in f.args))
    if isinstance(f, Eq):
        return Eq(_canon_term(f.left, env), _canon_term(f.right, env))
    if isinstance(f, Not):
        return Not(_canon(f.operand, env, depth, prefix))
    if isinstance(f, _Binary):
        return type(f)(_canon(f.left, env, depth, prefix), _canon(f.right, env, depth, prefix))
    if isinstance(f, _Quant):
        new = f"{prefix}{depth + 1}"
        return type(f)(new, _canon(f.body, {**env, f.var: new}, depth + 1, prefix))
    raise TypeError(f"nodo desconocido: {f!r}")
