"""Oráculo semántico por fuerza bruta para validar pasos y secuentes en modelos pequeños."""
import itertools
import random

from logos import FiniteModel, check, free_vars, holds


def signature_of(formulas):
    consts, funcs, preds = set(), {}, {}
    for f in formulas:
        sig = check(f)
        consts |= set(sig.constants)
        funcs.update(sig.functions)
        preds.update(sig.predicates)
    return sorted(consts), funcs, preds


def small_models(formulas, sizes=(1, 2), per_size=60, seed=0):
    consts, funcs, preds = signature_of(formulas)
    rng = random.Random(seed)
    for n in sizes:
        dom = list(range(n))
        comps = []  # (tipo, nombre, aridad, opciones)
        for c in consts:
            comps.append(("c", c, 0, dom))
        for f, k in sorted(funcs.items()):
            keys = list(itertools.product(dom, repeat=k))
            comps.append(("f", f, k, [dict(zip(keys, vals)) for vals in itertools.product(dom, repeat=len(keys))]))
        for p, k in sorted(preds.items()):
            keys = list(itertools.product(dom, repeat=k))
            comps.append(("p", p, k, [frozenset(t for t, b in zip(keys, bits) if b)
                                      for bits in itertools.product([0, 1], repeat=len(keys))]))
        total = 1
        for c in comps:
            total *= len(c[3])
        combos = (itertools.product(*[c[3] for c in comps]) if total <= per_size
                  else (tuple(rng.choice(c[3]) for c in comps) for _ in range(per_size)))
        for combo in combos:
            cs, fs, ps = {}, {}, {}
            for (kind, name, k, _), val in zip(comps, combo):
                {"c": cs, "f": fs, "p": ps}[kind][name] = val if kind == "c" else (k, val)
            yield FiniteModel(dom, cs, fs, ps)


def countermodel(premises, conclusion, models):
    """Primer (modelo, asignación) que satisface las premisas y falsifica la conclusión; o None."""
    fv = sorted(set().union(*(free_vars(f) for f in [*premises, conclusion])))
    for m in models:
        for vals in itertools.product(m.domain, repeat=len(fv)):
            s = dict(zip(fv, vals))
            if all(holds(m, p, s) for p in premises) and not holds(m, conclusion, s):
                return m, s
    return None


def certificate_steps_sound(cert, **kw):
    """Devuelve el primer paso `(id, modelo, asignación)` cuyo secuente `ctx ⊨ fórmula` falla; o None."""
    formulas = [*cert.premises, cert.conclusion] + [s.formula for s in cert.steps] + \
               [c for s in cert.steps for c in s.context]
    models = list(small_models(formulas, **kw))
    for step in cert.steps:
        bad = countermodel(list(step.context), step.formula, models)
        if bad:
            return step.id, bad[0], bad[1]
    return None
