"""Prueba proposicional completa y determinista: lema de Kalmár + análisis por casos.

Para toda consecuencia tautológica `Γ ⊨ φ` construye un certificado de `Γ ⊢ φ`:
1. Para cada valuación `v`, `kal(f, v)` deriva `f` (si `v(f)` es verdadera) o `¬f`
   (si es falsa) a partir de los literales de `v`, recorriendo `f` de las hojas a la raíz.
2. Con `v` fija, si alguna premisa es falsa se deduce `⊥` y de ahí `φ`; si no, `φ` es verdadera.
3. Se combinan las `2ⁿ` valuaciones con `p ∨ ¬p` y `∨E`, una letra a la vez.

No hace búsqueda: el certificado crece como `2ⁿ`, así que se limita el número de letras.
La corrección no se asume: el checker verifica el resultado como cualquier otro.
"""
from __future__ import annotations

from ..ast import And, Bottom, Iff, Implies, Not, Or, Pred
from ..errors import BatzError
from ..propositional import atoms, is_propositional, value
from .search import (
    BOT, and_e, and_i, assume, bot_e, iff_e, iff_i, imp_e, imp_i, linearize, not_e,
    not_i, or_e, or_i, raa,
)


def _lem(p):
    """`⊢ p ∨ ¬p`."""
    goal = Or(p, Not(p))
    nd = assume(Not(goal))
    np_ = not_i(not_e(or_i(assume(p), goal, 1), nd), Not(p))
    return raa(not_e(or_i(np_, goal, 2), nd), goal)


def _imp(x, y, v):
    """`x → y` (verdadera bajo `v`) desde los literales de `v`."""
    f = Implies(x, y)
    if not value(x, v):
        return imp_i(bot_e(not_e(assume(x), kal(x, v)), y), f)
    return imp_i(kal(y, v), f)  # descarga vacua de x


def kal(f, v):
    """Derivación de `f` si `v(f)`, de `¬f` si no, a partir de los literales de `v`."""
    val = value(f, v)
    if isinstance(f, Bottom):
        return not_i(assume(BOT), Not(f))
    if isinstance(f, Pred):
        return assume(f if val else Not(f))
    if isinstance(f, Not):
        k = kal(f.operand, v)
        if not value(f.operand, v):
            return k
        return not_i(not_e(k, assume(f)), Not(f))  # ¬¬operand
    a, b = f.left, f.right
    va, vb = value(a, v), value(b, v)
    if isinstance(f, And):
        if va and vb:
            return and_i(kal(a, v), kal(b, v))
        side, j = (1, a) if not va else (2, b)
        return not_i(not_e(and_e(assume(f), side), kal(j, v)), Not(f))
    if isinstance(f, Or):
        if va:
            return or_i(kal(a, v), f, 1)
        if vb:
            return or_i(kal(b, v), f, 2)
        bot = or_e(assume(f), not_e(assume(a), kal(a, v)), not_e(assume(b), kal(b, v)), BOT)
        return not_i(bot, Not(f))
    if isinstance(f, Implies):
        if val:
            return _imp(a, b, v)
        return not_i(not_e(imp_e(assume(f), kal(a, v)), kal(b, v)), Not(f))
    if isinstance(f, Iff):
        if val:
            return iff_i(_imp(a, b, v), _imp(b, a, v), f)
        if va:
            mp = iff_e(assume(f), kal(a, v), 1)
            return not_i(not_e(mp, kal(b, v)), Not(f))
        mp = iff_e(assume(f), kal(b, v), 2)
        return not_i(not_e(mp, kal(a, v)), Not(f))
    raise TypeError(f"nodo desconocido: {f!r}")


def kalmar_prove(premises, conclusion, max_atoms=10):
    """Certificado de `premises ⊢ conclusion` si es consecuencia tautológica.

    Lanza `BatzError` si no es proposicional, si hay demasiadas letras o si no
    es consecuencia tautológica (entonces no existe prueba).
    """
    premises = tuple(premises)
    for f in (*premises, conclusion):
        if not is_propositional(f):
            raise BatzError("semantic", "not_propositional", "la fórmula no es proposicional")
    names = sorted(set().union(*(atoms(f) for f in (*premises, conclusion))))
    if len(names) > max_atoms:
        raise BatzError("semantic", "too_many_atoms", f"más de {max_atoms} letras: el certificado crecería como 2^n")

    def leaf(v):
        for g in premises:
            if not value(g, v):
                return bot_e(not_e(assume(g), kal(g, v)), conclusion)
        if not value(conclusion, v):
            raise BatzError("semantic", "not_a_consequence", "la conclusión no se sigue de las premisas")
        return kal(conclusion, v)

    def branch(i, v):
        if i == len(names):
            return leaf(v)
        return or_e(_lem(Pred(names[i])), branch(i + 1, {**v, names[i]: True}),
                    branch(i + 1, {**v, names[i]: False}), conclusion)

    return linearize(branch(0, {}), premises, conclusion)
