"""Utilidades de prueba: generador aleatorio de fórmulas (property-based sin dependencias)."""
import random

from logos import (And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or,
                   Pred, Var)

VARS = ["x", "y", "z", "w"]
CONSTS = ["a", "b"]
FUNCS = {"f": 1, "g": 2}
PREDS = {"P": 1, "Q": 1, "R": 2, "S": 0}


def rand_term(rng, depth, vars_=VARS):
    r = rng.random()
    if depth <= 0 or r < 0.5:
        return Var(rng.choice(vars_)) if rng.random() < 0.7 else Const(rng.choice(CONSTS))
    name = rng.choice(list(FUNCS))
    return Func(name, tuple(rand_term(rng, depth - 1, vars_) for _ in range(FUNCS[name])))


def rand_formula(rng, depth, vars_=VARS):
    if depth <= 0 or rng.random() < 0.2:
        if rng.random() < 0.08:
            return Bottom()
        if rng.random() < 0.2:
            return Eq(rand_term(rng, 1, vars_), rand_term(rng, 1, vars_))
        name = rng.choice(list(PREDS))
        return Pred(name, tuple(rand_term(rng, 1, vars_) for _ in range(PREDS[name])))
    kind = rng.choice(["not", "and", "or", "implies", "iff", "forall", "exists"])
    if kind == "not":
        return Not(rand_formula(rng, depth - 1, vars_))
    if kind in ("forall", "exists"):
        cls = Forall if kind == "forall" else Exists
        return cls(rng.choice(vars_), rand_formula(rng, depth - 1, vars_))
    cls = {"and": And, "or": Or, "implies": Implies, "iff": Iff}[kind]
    return cls(rand_formula(rng, depth - 1, vars_), rand_formula(rng, depth - 1, vars_))


# --- modelos ----------------------------------------------------------------
import itertools

from logos import FiniteModel, free_vars


def rand_model(rng, max_size=3):
    n = rng.randint(1, max_size)
    dom = list(range(n))
    return FiniteModel(
        dom,
        {c: rng.choice(dom) for c in CONSTS},
        {f: (k, {args: rng.choice(dom) for args in itertools.product(dom, repeat=k)})
         for f, k in FUNCS.items()},
        {p: (k, {t for t in itertools.product(dom, repeat=k) if rng.random() < 0.5})
         for p, k in PREDS.items()},
    )


def close(f):
    """Cierra una fórmula cuantificando universalmente sus variables libres."""
    from logos import Forall
    for v in sorted(free_vars(f), reverse=True):
        f = Forall(v, f)
    return f


def all_models(size, unary=("P", "Q"), binary=("R",)):
    """Todos los modelos de un tamaño con predicados unarios y binarios dados (sin constantes ni funciones)."""
    dom = list(range(size))
    pairs = list(itertools.product(dom, repeat=2))
    unary_ext = [frozenset((e,) for e in sub) for r in range(size + 1)
                 for sub in itertools.combinations(dom, r)]
    binary_ext = [frozenset(sub) for r in range(len(pairs) + 1)
                  for sub in itertools.combinations(pairs, r)]
    spaces = [unary_ext] * len(unary) + [binary_ext] * len(binary)
    for combo in itertools.product(*spaces):
        preds = {n: (1, combo[i]) for i, n in enumerate(unary)}
        preds.update({n: (2, combo[len(unary) + i]) for i, n in enumerate(binary)})
        yield FiniteModel(dom, {}, {}, preds)
