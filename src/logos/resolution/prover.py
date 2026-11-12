"""Resolución binaria con factorización (motor B): un oráculo de contraste, no un decisor.

`refuted`   se derivó la cláusula vacía de premisas ∪ {¬conclusión}: la consecuencia vale.
`saturated` no quedan inferencias y no apareció la vacía: el conjunto es satisfacible.
`unknown`   se agotó un límite. No dice nada sobre la validez.
"""
from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from itertools import count

from .clausify import Clausifier, TooManyClauses, clause_text, is_tautology, is_var


@dataclass(frozen=True)
class ResolutionConfig:
    max_clauses: int = 6000
    max_literals: int = 8      # cláusulas más largas se descartan (se anota: impide «saturated»)
    max_depth: int = 6         # anidamiento máximo de términos
    timeout: float = 5.0
    age_ratio: int = 5         # cada n-ésima elección es por antigüedad: mantiene la búsqueda justa


@dataclass(frozen=True)
class Step:
    id: int
    clause: str
    rule: str           # premise | negated_conclusion | equality_axiom | resolve | factor
    parents: tuple = ()

    def to_dict(self):
        return {"id": self.id, "clause": self.clause, "rule": self.rule, "parents": list(self.parents)}


@dataclass(frozen=True)
class ResolutionResult:
    status: str                 # refuted | saturated | unknown
    reason: str | None = None   # timeout | clause_limit | cnf_limit | pruned
    steps: tuple = ()           # solo con `refuted`: la refutación, de las entradas a □
    generated: int = 0
    kept: int = 0

    def to_dict(self):
        return {"status": self.status, "reason": self.reason, "generated": self.generated,
                "kept": self.kept, "steps": [s.to_dict() for s in self.steps]}


# --- unificación -------------------------------------------------------------

def walk(t, s):
    while is_var(t) and t in s:
        t = s[t]
    return t


def occurs(v, t, s):
    t = walk(t, s)
    if is_var(t):
        return t == v
    return any(occurs(v, a, s) for a in t[1:])


def unify(a, b, s):
    """Unificador más general (con comprobación de ocurrencia) o None."""
    a, b = walk(a, s), walk(b, s)
    if a == b:
        return s
    if is_var(a):
        return None if occurs(a, b, s) else {**s, a: b}
    if is_var(b):
        return None if occurs(b, a, s) else {**s, b: a}
    if a[0] != b[0] or len(a) != len(b):
        return None
    for x, y in zip(a[1:], b[1:]):
        s = unify(x, y, s)
        if s is None:
            return None
    return s


def unify_args(xs, ys, s=None):
    s = {} if s is None else s
    for x, y in zip(xs, ys):
        s = unify(x, y, s)
        if s is None:
            return None
    return s


def apply(t, s):
    t = walk(t, s)
    return t if is_var(t) else (t[0], *(apply(a, s) for a in t[1:]))


def apply_clause(clause, s):
    return frozenset((sign, pred, tuple(apply(a, s) for a in args)) for sign, pred, args in clause)


def rename(clause, suffix):
    def r(t):
        return f"{t}_{suffix}" if is_var(t) else (t[0], *(r(a) for a in t[1:]))
    return frozenset((sign, pred, tuple(r(a) for a in args)) for sign, pred, args in clause)


def _shape(t):
    return "?" if is_var(t) else (t[0], *(_shape(a) for a in t[1:]))


def normalize(clause):
    """Renombra variables de forma canónica: dos variantes de una cláusula quedan iguales."""
    order = sorted(clause, key=lambda l: (l[1], l[0], repr(tuple(_shape(a) for a in l[2])), repr(l[2])))
    names = {}

    def r(t):
        if is_var(t):
            return names.setdefault(t, f"?{len(names) + 1}")
        return (t[0], *(r(a) for a in t[1:]))
    return frozenset((sign, pred, tuple(r(a) for a in args)) for sign, pred, args in order)


def depth(t):
    return 0 if is_var(t) or len(t) == 1 else 1 + max(depth(a) for a in t[1:])


def weight(clause):
    def size(t):
        return 1 if is_var(t) else 1 + sum(size(a) for a in t[1:])
    return sum(1 + sum(size(a) for a in args) for _, _, args in clause)


# --- inferencias -------------------------------------------------------------

def factors(clause):
    lits = list(clause)
    for i, (s1, p1, a1) in enumerate(lits):
        for s2, p2, a2 in lits[i + 1:]:
            if s1 == s2 and p1 == p2:
                u = unify_args(a1, a2)
                if u is not None:
                    yield apply_clause(clause, u)


def resolvents(c1, c2):
    for s1, p1, a1 in c1:
        for s2, p2, a2 in c2:
            if p1 == p2 and s1 != s2:
                u = unify_args(a1, a2)
                if u is not None:
                    yield apply_clause((c1 - {(s1, p1, a1)}) | (c2 - {(s2, p2, a2)}), u)


def _subsumed_by_unit(clause, units):
    """¿Algún literal de la cláusula es instancia de una cláusula unitaria ya conservada?"""
    for sign, pred, args in clause:
        for unit_args in units.get((sign, pred), ()):
            if _match(unit_args, args) is not None:
                return True
    return False


def _match(pattern, target, s=None):
    """Emparejamiento en un solo sentido: instancia `pattern` hasta igualar `target`."""
    s = {} if s is None else s
    for p, t in zip(pattern, target):
        if is_var(p):
            if s.setdefault(p, t) != t:
                return None
        elif is_var(t) or p[0] != t[0] or len(p) != len(t):
            return None
        else:
            s = _match(p[1:], t[1:], s)
            if s is None:
                return None
    return s


# --- bucle de cláusula dada --------------------------------------------------

def refute(clauses, config=None, labels=None):
    """Busca la cláusula vacía. `clauses`: iterable de cláusulas; `labels`: regla de cada entrada."""
    cfg = config or ResolutionConfig()
    deadline = time.monotonic() + cfg.timeout
    ids, origin, by_id = {}, {}, {}
    tick, heap, queue_age = count(), [], []
    units, active = {}, []
    generated, pruned = 0, False

    def keep(clause, rule, parents=()):
        nonlocal pruned
        clause = normalize(clause)
        if clause in ids or is_tautology(clause):
            return None
        if len(clause) > cfg.max_literals or any(depth(a) > cfg.max_depth for _, _, args in clause for a in args):
            pruned = True
            return None
        if clause and _subsumed_by_unit(clause, units):
            return None
        n = len(ids) + 1
        ids[clause], origin[n], by_id[n] = n, (rule, parents), clause
        heapq.heappush(heap, (weight(clause), next(tick), n))
        queue_age.append(n)
        return n

    def proof(n):
        order, seen = [], set()

        def visit(k):
            if k in seen:
                return
            seen.add(k)
            for parent in origin[k][1]:
                visit(parent)
            order.append(k)
        visit(n)
        renumber = {k: i + 1 for i, k in enumerate(order)}
        return tuple(Step(renumber[k], clause_text(by_id[k]), origin[k][0],
                          tuple(renumber[p] for p in origin[k][1])) for k in order)

    for i, clause in enumerate(clauses):
        n = keep(clause, labels[i] if labels else "premise")
        if n is not None and not by_id[n]:
            return ResolutionResult("refuted", None, proof(n), generated, len(ids))

    done, picks, age_cursor = set(), 0, 0
    while heap:
        if time.monotonic() > deadline:
            return ResolutionResult("unknown", "timeout", (), generated, len(ids))
        if len(ids) > cfg.max_clauses:
            return ResolutionResult("unknown", "clause_limit", (), generated, len(ids))
        picks += 1
        given = None
        if picks % cfg.age_ratio == 0:  # la más antigua pendiente
            while age_cursor < len(queue_age) and queue_age[age_cursor] in done:
                age_cursor += 1
            if age_cursor < len(queue_age):
                given = queue_age[age_cursor]
        if given is None:
            while heap:
                _, _, candidate = heapq.heappop(heap)
                if candidate not in done:
                    given = candidate
                    break
            if given is None:
                break
        done.add(given)
        clause = by_id[given]
        if len(clause) == 1:
            sign, pred, args = next(iter(clause))
            units.setdefault((sign, pred), []).append(args)
        fresh = rename(clause, "g")
        new = [(f, "factor", (given,)) for f in factors(clause)]
        for other in active + [given]:
            for r in resolvents(fresh, by_id[other]):
                new.append((r, "resolve", (given, other)))
        active.append(given)
        for derived, rule, parents in new:
            generated += 1
            n = keep(derived, rule, parents)
            if n is not None and not by_id[n]:
                return ResolutionResult("refuted", None, proof(n), generated, len(ids))
    if pruned:  # se descartaron cláusulas por tamaño: no se puede afirmar saturación
        return ResolutionResult("unknown", "pruned", (), generated, len(ids))
    return ResolutionResult("saturated", None, (), generated, len(ids))


def resolve(premises, conclusion, config=None):
    """¿`premises ⊨ conclusion`? Refuta premisas ∪ {¬conclusión}. Fórmulas como AST."""
    cfg = config or ResolutionConfig()
    cl = Clausifier(max_clauses=cfg.max_clauses)
    clauses, labels = [], []
    try:
        for p in premises:
            for c in cl.add(p):
                clauses.append(c); labels.append("premise")
        for c in cl.add(conclusion, negate=True):
            clauses.append(c); labels.append("negated_conclusion")
    except TooManyClauses:
        return ResolutionResult("unknown", "cnf_limit")
    for c in cl.equality_axioms():
        clauses.append(c); labels.append("equality_axiom")
    return refute(clauses, cfg, labels)
