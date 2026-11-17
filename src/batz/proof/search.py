"""Buscador de pruebas por deducción natural dirigido por la meta.

Construye derivaciones (`Deriv`) y las linealiza a un `ProofCertificate`. No usa
el checker: la aceptación la decide `proof.prove` verificando el resultado.
Es incompleto a propósito (FOL es indecidible): sin prueba hallada, devuelve None.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from functools import lru_cache

from ..ast import (
    And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred, Term, Var,
    _Binary, _Quant,
)
from ..transform import (
    all_var_names, fresh_name, free_vars, rename_bound_canonical, substitute,
)
from .certificate import ProofCertificate, ProofStep

BOT = Bottom()


@dataclass
class SearchConfig:
    max_depth: int = 6      # decisiones con elección (testigos, instancias, RAA...)
    max_nodes: int = 200_000
    timeout: float = 10.0   # segundos


class BudgetExceeded(Exception):
    pass


# --- derivaciones -------------------------------------------------------------

@dataclass(eq=False)
class Deriv:
    rule: str
    formula: object
    refs: tuple = ()
    params: dict = field(default_factory=dict)


def assume(a): return Deriv("assume", a)
def and_i(x, y): return Deriv("and_i", And(x.formula, y.formula), (x, y))
def and_e(d, side): return Deriv(f"and_e{side}", (d.formula.left, d.formula.right)[side - 1], (d,))
def or_i(d, goal, side): return Deriv(f"or_i{side}", goal, (d,))
def or_e(dor, da, db, goal): return Deriv("or_e", goal, (dor, da, db))
def imp_i(d, goal): return Deriv("imp_i", goal, (d,))
def imp_e(dimp, da): return Deriv("imp_e", dimp.formula.right, (dimp, da))
def not_i(d, goal): return Deriv("not_i", goal, (d,))
def not_e(da, dn): return Deriv("not_e", BOT, (da, dn))
def bot_e(d, goal): return Deriv("bot_e", goal, (d,))
def raa(d, goal): return Deriv("raa", goal, (d,))
def iff_i(d1, d2, goal): return Deriv("iff_i", goal, (d1, d2))
def iff_e(di, dx, side):
    f = di.formula
    return Deriv(f"iff_e{side}", f.right if side == 1 else f.left, (di, dx))
def all_i(d, goal, y): return Deriv("all_i", goal, (d,), {"var": y})
def all_e(d, t): return Deriv("all_e", substitute(d.formula.body, {d.formula.var: t}), (d,), {"term": t})
def ex_i(d, goal, t): return Deriv("ex_i", goal, (d,), {"term": t})
def ex_e(dex, dc, y, goal): return Deriv("ex_e", goal, (dex, dc), {"var": y})
def eq_i(t): return Deriv("eq_i", Eq(t, t), (), {"term": t})
def eq_e(deq, dphi, x, template):
    return Deriv("eq_e", substitute(template, {x: deq.formula.right}), (deq, dphi),
                 {"var": x, "template": template})


@lru_cache(maxsize=None)
def canon(f):
    return rename_bound_canonical(f)


# --- términos candidatos y reescritura ----------------------------------------

def _collect(node, consts, funcs):
    if isinstance(node, Const):
        consts.add(node.name)
    elif isinstance(node, Func):
        funcs[node.name] = len(node.args)
        for a in node.args:
            _collect(a, consts, funcs)
    elif isinstance(node, Pred):
        for a in node.args:
            _collect(a, consts, funcs)
    elif isinstance(node, Eq):
        _collect(node.left, consts, funcs)
        _collect(node.right, consts, funcs)
    elif isinstance(node, Not):
        _collect(node.operand, consts, funcs)
    elif isinstance(node, _Binary):
        _collect(node.left, consts, funcs)
        _collect(node.right, consts, funcs)
    elif isinstance(node, _Quant):
        _collect(node.body, consts, funcs)


def _replace(node, old, new):
    """Reemplaza las ocurrencias del término `old` por `new` (sin pasar bajo ligaduras de sus variables)."""
    if node == old:
        return new
    if isinstance(node, Func):
        return Func(node.name, tuple(_replace(a, old, new) for a in node.args))
    if isinstance(node, Pred):
        return Pred(node.name, tuple(_replace(a, old, new) for a in node.args))
    if isinstance(node, Eq):
        return Eq(_replace(node.left, old, new), _replace(node.right, old, new))
    if isinstance(node, Not):
        return Not(_replace(node.operand, old, new))
    if isinstance(node, _Binary):
        return type(node)(_replace(node.left, old, new), _replace(node.right, old, new))
    if isinstance(node, _Quant):
        if node.var in _term_vars(old):
            return node
        return type(node)(node.var, _replace(node.body, old, new))
    return node


def _term_vars(t):
    if isinstance(t, Var):
        return {t.name}
    if isinstance(t, Func):
        return set().union(*(_term_vars(a) for a in t.args))
    return set()


# --- el buscador ---------------------------------------------------------------

class Search:
    def __init__(self, formulas, cfg):
        self.cfg = cfg
        self.nodes = 0
        self.deadline = time.monotonic() + cfg.timeout
        self.avoid = set()
        for f in formulas:
            self.avoid |= all_var_names(f)
        self.counter = 0
        self.failed = set()
        self.default_var = None

    def tick(self):
        self.nodes += 1
        if self.nodes > self.cfg.max_nodes or (self.nodes % 64 == 0 and time.monotonic() > self.deadline):
            raise BudgetExceeded

    def fresh(self):
        while True:
            self.counter += 1
            name = f"u{self.counter}"
            if name not in self.avoid:
                self.avoid.add(name)
                return name

    def candidates(self, facts, goal):
        consts, funcs, vars_ = set(), {}, set()
        for f in [d.formula for d in facts] + [goal]:
            _collect(f, consts, funcs)
            vars_ |= free_vars(f)
        base = [Const(c) for c in sorted(consts)] + [Var(v) for v in sorted(vars_)]
        if not base:
            if self.default_var is None:
                self.default_var = self.fresh()
            base = [Var(self.default_var)]
        terms = list(base)
        for name, k in sorted(funcs.items()):
            for args in itertools.product(base[:5], repeat=k):
                terms.append(Func(name, args))
        return terms[:14]

    # --- entrada con memo de fallos ---
    def solve(self, facts, goal, d, done=frozenset()):
        self.tick()
        facts = self.saturate(facts)
        key = (frozenset(canon(f.formula) for f in facts), canon(goal), d, done)
        if key in self.failed:
            return None
        result = self._solve(facts, goal, d, done)
        if result is None:
            self.failed.add(key)
        return result

    def saturate(self, facts):
        out, by = [], {}

        def add(dv):
            k = canon(dv.formula)
            if k in by:
                return False
            by[k] = dv
            out.append(dv)
            return True

        for f in facts:
            add(f)
        changed = True
        while changed:
            changed = False
            for f in list(out):
                fm = f.formula
                if isinstance(fm, And):
                    changed |= add(and_e(f, 1))
                    changed |= add(and_e(f, 2))
                elif isinstance(fm, Implies) and canon(fm.left) in by:
                    changed |= add(imp_e(f, by[canon(fm.left)]))
                elif isinstance(fm, Iff):
                    if canon(fm.left) in by:
                        changed |= add(iff_e(f, by[canon(fm.left)], 1))
                    if canon(fm.right) in by:
                        changed |= add(iff_e(f, by[canon(fm.right)], 2))
                    # A↔B equivale a las dos implicaciones: así se usa aunque no haya un lado aún
                    changed |= add(imp_i(iff_e(f, assume(fm.left), 1), Implies(fm.left, fm.right)))
                    changed |= add(imp_i(iff_e(f, assume(fm.right), 2), Implies(fm.right, fm.left)))
        return tuple(out)

    def _solve(self, facts, goal, d, done):
        by = {canon(f.formula): f for f in facts}
        if canon(goal) in by:
            return by[canon(goal)]
        if isinstance(goal, Eq) and goal.left == goal.right:
            return eq_i(goal.left)
        bot = self.find_bottom(facts, by)
        if bot is not None:
            return bot if isinstance(goal, Bottom) else bot_e(bot, goal)

        # --- reglas de introducción invertibles ---
        if isinstance(goal, And):
            l = self.solve(facts, goal.left, d, done)
            r = l and self.solve(facts, goal.right, d, done)
            return and_i(l, r) if r else None
        if isinstance(goal, Implies):
            a = assume(goal.left)
            r = self.solve(facts + (a,), goal.right, d, done)
            return imp_i(r, goal) if r else None
        if isinstance(goal, Not):
            a = assume(goal.operand)
            r = self.solve(facts + (a,), BOT, d, done)
            return not_i(r, goal) if r else None
        if isinstance(goal, Iff):
            l = self.solve(facts, Implies(goal.left, goal.right), d, done)
            r = l and self.solve(facts, Implies(goal.right, goal.left), d, done)
            return iff_i(l, r, goal) if r else None
        if isinstance(goal, Forall):
            y = self.fresh()
            r = self.solve(facts, substitute(goal.body, {goal.var: Var(y)}), d, done)
            return all_i(r, goal, y) if r else None

        # --- eliminaciones invertibles: casos ---
        for f in facts:
            k = canon(f.formula)
            if isinstance(f.formula, Exists) and k not in done:
                y = self.fresh()
                a = assume(substitute(f.formula.body, {f.formula.var: Var(y)}))
                r = self.solve(facts + (a,), goal, d, done | {k})
                return ex_e(f, r, y, goal) if r else None
        for f in facts:
            k = canon(f.formula)
            if isinstance(f.formula, Or) and k not in done:
                da = self.solve(facts + (assume(f.formula.left),), goal, d, done | {k})
                if not da:
                    return None
                db = self.solve(facts + (assume(f.formula.right),), goal, d, done | {k})
                return or_e(f, da, db, goal) if db else None

        if d <= 0:
            return None
        return self.choices(facts, by, goal, d, done)

    def find_bottom(self, facts, by):
        for f in facts:
            if isinstance(f.formula, Bottom):
                return f
        for f in facts:
            if isinstance(f.formula, Not) and canon(f.formula.operand) in by:
                return not_e(by[canon(f.formula.operand)], f)
        return None

    # --- reglas con elección: cuestan profundidad ---
    def choices(self, facts, by, goal, d, done):
        # ¬A en las hipótesis con meta ⊥: probar A
        if isinstance(goal, Bottom):
            for f in facts:
                if isinstance(f.formula, Not):
                    r = self.solve(facts, f.formula.operand, d - 1, done)
                    if r:
                        return not_e(r, f)
        if isinstance(goal, Or):
            r = self.solve(facts, goal.left, d - 1, done)
            if r:
                return or_i(r, goal, 1)
            r = self.solve(facts, goal.right, d - 1, done)
            if r:
                return or_i(r, goal, 2)
        if isinstance(goal, Exists):
            for t in self.candidates(facts, goal):
                r = self.solve(facts, substitute(goal.body, {goal.var: t}), d - 1, done)
                if r:
                    return ex_i(r, goal, t)
        # instanciar universales
        for f in facts:
            if isinstance(f.formula, Forall):
                for t in self.candidates(facts, goal):
                    new = all_e(f, t)
                    if canon(new.formula) in by:
                        continue
                    r = self.solve(facts + (new,), goal, d - 1, done)
                    if r:
                        return r
        # modus ponens probando el antecedente
        imps = [f for f in facts if isinstance(f.formula, Implies)]
        imps.sort(key=lambda f: canon(f.formula.right) != canon(goal))
        for f in imps:
            if canon(f.formula.right) in by:
                continue
            a = self.solve(facts, f.formula.left, d - 1, done)
            if a:
                r = self.solve(facts + (imp_e(f, a),), goal, d - 1, done)
                if r:
                    return r
        r = self.rewrite(facts, by, goal, d, done)
        if r:
            return r
        # reducción al absurdo
        if not isinstance(goal, Bottom):
            a = assume(Not(goal))
            r = self.solve(facts + (a,), BOT, d - 1, done)
            if r:
                return raa(r, goal)
        return None

    # --- igualdad ---
    def sym(self, deq):
        s, t = deq.formula.left, deq.formula.right
        x = self.fresh()
        return eq_e(deq, eq_i(s), x, Eq(Var(x), s))  # φ = (x = s): φ[s] es s=s, φ[t] es t=s

    def rewrite(self, facts, by, goal, d, done):
        eqs = [f for f in facts if isinstance(f.formula, Eq) and f.formula.left != f.formula.right]
        if not eqs:
            return None
        for e in eqs:
            for deq in (e, self.sym(e)):
                s, t = deq.formula.left, deq.formula.right
                # meta: reemplazar t por s y probar eso
                g2 = _replace(goal, t, s)
                if g2 != goal:
                    x = self.fresh()
                    template = _replace(goal, t, Var(x))
                    r = self.solve(facts, g2, d - 1, done)
                    if r:
                        return eq_e(deq, r, x, template)
                # hipótesis: reescribir s por t
                for f in facts:
                    if f is e:
                        continue
                    f2 = _replace(f.formula, s, t)
                    if f2 == f.formula:
                        continue
                    x = self.fresh()
                    template = _replace(f.formula, s, Var(x))
                    new = eq_e(deq, f, x, template)
                    if canon(new.formula) in by:
                        continue
                    r = self.solve(facts + (new,), goal, d - 1, done)
                    if r:
                        return r
        return None


# --- linealización ---------------------------------------------------------------

def _ctx_has(ctx, f):
    return any(canon(c) == canon(f) for c in ctx)


def _union(*ctxs):
    out = []
    for ctx in ctxs:
        for f in ctx:
            if not _ctx_has(out, f):
                out.append(f)
    return tuple(out)


def _minus(ctx, f):
    return tuple(c for c in ctx if canon(c) != canon(f))


def _context(d, ctxs):
    r, f = d.rule, d.formula
    if r == "assume":
        return (f,)
    if r in ("eq_i",):
        return ()
    if r in ("and_e1", "and_e2", "or_i1", "or_i2", "bot_e", "all_i", "all_e", "ex_i"):
        return ctxs[0]
    if r == "imp_i":
        return _minus(ctxs[0], f.left)
    if r == "not_i":
        return _minus(ctxs[0], f.operand)
    if r == "raa":
        return _minus(ctxs[0], Not(f))
    if r == "or_e":
        o = d.refs[0].formula
        return _union(ctxs[0], _minus(ctxs[1], o.left), _minus(ctxs[2], o.right))
    if r == "ex_e":
        q = d.refs[0].formula
        inst = substitute(q.body, {q.var: Var(d.params["var"])})
        return _union(ctxs[0], _minus(ctxs[1], inst))
    return _union(*ctxs)  # and_i, imp_e, not_e, iff_*, eq_e


def linearize(deriv, premises, conclusion):
    steps, ids, ctx_of, keys = [], {}, {}, {}

    def emit(d):
        if id(d) in ids:
            return ids[id(d)]
        refs = tuple(emit(c) for c in d.refs)
        ctx = _context(d, [ctx_of[r] for r in refs])
        pkey = tuple(sorted(
            (k, v if isinstance(v, (str, Term)) else canon(v)) for k, v in d.params.items()))
        key = (d.rule, canon(d.formula), refs, pkey)
        if key in keys:
            ids[id(d)] = keys[key]
            return keys[key]
        n = len(steps) + 1
        steps.append(ProofStep(n, d.formula, ctx, d.rule, refs, dict(d.params)))
        ctx_of[n] = ctx
        ids[id(d)] = keys[key] = n
        return n

    emit(deriv)
    return ProofCertificate(tuple(premises), conclusion, tuple(steps))


def search(premises, conclusion, config=None):
    """Devuelve `(certificado | None, motivo, nodos)`; motivo: None, 'depth' o 'budget'."""
    import sys
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))
    cfg = config or SearchConfig()
    s = Search([*premises, conclusion], cfg)
    facts = tuple(assume(p) for p in premises)
    try:
        for depth in range(cfg.max_depth + 1):
            deriv = s.solve(facts, conclusion, depth)
            if deriv is not None:
                return linearize(deriv, premises, conclusion), None, s.nodes
    except BudgetExceeded:
        return None, "budget", s.nodes
    return None, "depth", s.nodes
