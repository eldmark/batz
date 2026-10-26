"""Checker independiente de certificados de deducción natural.

Implementa la tabla de docs/specs/PROOF_CALCULUS.md regla por regla. No importa
el buscador ni confía en nada de él: recalcula el contexto de cada paso.
"""
from __future__ import annotations

from ..ast import (
    And, Bottom, Eq, Exists, Forall, Iff, Implies, Not, Or, Term, Var, Formula,
    is_term_name,
)
from ..transform import alpha_equiv, free_vars, substitute
from .certificate import RULES, ProofCertificate, ProofError


# --- conjuntos de fórmulas salvo alfa-equivalencia ---------------------------

def _has(ctx, f):
    return any(alpha_equiv(c, f) for c in ctx)


def _union(*ctxs):
    out = []
    for ctx in ctxs:
        for f in ctx:
            if not _has(out, f):
                out.append(f)
    return tuple(out)


def _discharge(ctx, f):
    return tuple(c for c in ctx if not alpha_equiv(c, f))


def _same_set(a, b):
    return all(_has(b, f) for f in a) and all(_has(a, f) for f in b)


def _fv(ctx):
    out = set()
    for f in ctx:
        out |= free_vars(f)
    return out


class _Step:
    """Contexto de verificación de un paso: ayuda a fallar con mensaje y paso."""

    def __init__(self, step):
        self.step = step

    def need(self, cond, message, code="rule_violation"):
        if not cond:
            raise ProofError(code, message, self.step.id)

    def kind(self, f, cls, what):
        self.need(isinstance(f, cls), f"se esperaba {what}", "wrong_shape")
        return f

    def same(self, a, b, message):
        self.need(alpha_equiv(a, b), message, "formula_mismatch")


_PARAMS = {"all_i": {"var"}, "ex_e": {"var"}, "all_e": {"term"}, "ex_i": {"term"},
           "eq_i": {"term"}, "eq_e": {"var", "template"}}


def _apply(step, forms, ctxs):
    """Devuelve el contexto que la regla produce para este paso."""
    st, rule, c = _Step(step), step.rule, step.formula
    p = step.params
    arity = {"assume": 0, "eq_i": 0, "and_i": 2, "or_e": 3, "imp_e": 2, "not_e": 2,
             "iff_i": 2, "iff_e1": 2, "iff_e2": 2, "ex_e": 2, "eq_e": 2}.get(rule, 1)
    st.need(len(forms) == arity, f"la regla {rule} usa {arity} referencia(s)", "bad_refs")
    st.need(set(p) == _PARAMS.get(rule, set()),
            f"la regla {rule} admite exactamente los parámetros {sorted(_PARAMS.get(rule, set()))}", "bad_params")

    def param(name, cls):
        st.need(name in p and isinstance(p[name], cls), f"falta el parámetro '{name}'", "bad_params")
        return p[name]

    if rule == "assume":
        return (c,)

    if rule == "and_i":
        a = st.kind(c, And, "una conjunción")
        st.same(a.left, forms[0], "el primer conyunto no coincide con la referencia")
        st.same(a.right, forms[1], "el segundo conyunto no coincide con la referencia")
        return _union(*ctxs)
    if rule in ("and_e1", "and_e2"):
        a = st.kind(forms[0], And, "una conjunción como premisa")
        st.same(a.left if rule == "and_e1" else a.right, c, "la conclusión no es el conyunto")
        return ctxs[0]

    if rule in ("or_i1", "or_i2"):
        o = st.kind(c, Or, "una disyunción")
        st.same(o.left if rule == "or_i1" else o.right, forms[0], "la premisa no es el disyunto")
        return ctxs[0]
    if rule == "or_e":
        o = st.kind(forms[0], Or, "una disyunción como primera premisa")
        st.same(forms[1], c, "la segunda premisa no concluye C")
        st.same(forms[2], c, "la tercera premisa no concluye C")
        return _union(ctxs[0], _discharge(ctxs[1], o.left), _discharge(ctxs[2], o.right))

    if rule == "imp_i":
        i = st.kind(c, Implies, "una implicación")
        st.same(i.right, forms[0], "la premisa no es el consecuente")
        return _discharge(ctxs[0], i.left)
    if rule == "imp_e":
        i = st.kind(forms[0], Implies, "una implicación como primera premisa")
        st.same(i.left, forms[1], "la segunda premisa no es el antecedente")
        st.same(i.right, c, "la conclusión no es el consecuente")
        return _union(*ctxs)

    if rule == "not_i":
        n = st.kind(c, Not, "una negación")
        st.kind(forms[0], Bottom, "⊥ como premisa")
        return _discharge(ctxs[0], n.operand)
    if rule == "not_e":
        n = st.kind(forms[1], Not, "una negación como segunda premisa")
        st.same(n.operand, forms[0], "las premisas no son A y ¬A")
        st.kind(c, Bottom, "⊥ como conclusión")
        return _union(*ctxs)
    if rule == "bot_e":
        st.kind(forms[0], Bottom, "⊥ como premisa")
        return ctxs[0]
    if rule == "raa":
        st.kind(forms[0], Bottom, "⊥ como premisa")
        return _discharge(ctxs[0], Not(c))

    if rule == "iff_i":
        b = st.kind(c, Iff, "un bicondicional")
        st.same(Implies(b.left, b.right), forms[0], "la primera premisa no es A→B")
        st.same(Implies(b.right, b.left), forms[1], "la segunda premisa no es B→A")
        return _union(*ctxs)
    if rule in ("iff_e1", "iff_e2"):
        b = st.kind(forms[0], Iff, "un bicondicional como primera premisa")
        src, dst = (b.left, b.right) if rule == "iff_e1" else (b.right, b.left)
        st.same(src, forms[1], "la segunda premisa no es el lado esperado")
        st.same(dst, c, "la conclusión no es el otro lado")
        return _union(*ctxs)

    if rule == "all_i":
        q = st.kind(c, Forall, "un universal")
        y = param("var", str)
        st.need(is_term_name(y), f"variable propia inválida: {y!r}", "bad_params")
        st.same(substitute(q.body, {q.var: Var(y)}), forms[0], "la premisa no es ψ[x:=y]")
        st.need(y not in _fv(ctxs[0]), f"'{y}' es libre en las hipótesis abiertas", "eigenvariable")
        st.need(y not in free_vars(c), f"'{y}' es libre en la conclusión", "eigenvariable")
        return ctxs[0]
    if rule == "all_e":
        q = st.kind(forms[0], Forall, "un universal como premisa")
        t = param("term", Term)
        st.same(substitute(q.body, {q.var: t}), c, "la conclusión no es ψ[x:=t]")
        return ctxs[0]
    if rule == "ex_i":
        q = st.kind(c, Exists, "un existencial")
        t = param("term", Term)
        st.same(substitute(q.body, {q.var: t}), forms[0], "la premisa no es ψ[x:=t]")
        return ctxs[0]
    if rule == "ex_e":
        q = st.kind(forms[0], Exists, "un existencial como primera premisa")
        y = param("var", str)
        st.need(is_term_name(y), f"variable propia inválida: {y!r}", "bad_params")
        st.same(forms[1], c, "la segunda premisa no concluye C")
        rest = _discharge(ctxs[1], substitute(q.body, {q.var: Var(y)}))
        st.need(y not in _fv(ctxs[0]), f"'{y}' es libre en las hipótesis de ∃xψ", "eigenvariable")
        st.need(y not in _fv(rest), f"'{y}' es libre en otras hipótesis abiertas", "eigenvariable")
        st.need(y not in free_vars(c), f"'{y}' es libre en la conclusión", "eigenvariable")
        st.need(y not in free_vars(forms[0]), f"'{y}' es libre en ∃xψ", "eigenvariable")
        return _union(ctxs[0], rest)

    if rule == "eq_i":
        t = param("term", Term)
        st.same(Eq(t, t), c, "la conclusión no es t = t")
        return ()
    if rule == "eq_e":
        e = st.kind(forms[0], Eq, "una igualdad como primera premisa")
        x = param("var", str)
        phi = param("template", Formula)
        st.need(is_term_name(x), f"variable de plantilla inválida: {x!r}", "bad_params")
        st.same(substitute(phi, {x: e.left}), forms[1], "la segunda premisa no es φ[x:=s]")
        st.same(substitute(phi, {x: e.right}), c, "la conclusión no es φ[x:=t]")
        return _union(*ctxs)

    raise ProofError("unknown_rule", f"regla desconocida: {rule!r}", step.id)


def verify(cert):
    """Acepta el certificado o lanza `ProofError` con el paso culpable."""
    if not isinstance(cert, ProofCertificate):
        raise ProofError("invalid_certificate", "no es un ProofCertificate")
    if not cert.steps:
        raise ProofError("empty", "el certificado no tiene pasos")
    forms, ctxs = {}, {}
    for n, step in enumerate(cert.steps, 1):
        if step.id != n:
            raise ProofError("bad_ids", f"los ids deben ser consecutivos desde 1 (se esperaba {n})", step.id)
        if step.rule not in RULES:
            raise ProofError("unknown_rule", f"regla desconocida: {step.rule!r}", step.id)
        for r in step.refs:
            if not isinstance(r, int) or isinstance(r, bool) or not 1 <= r < n:
                raise ProofError("bad_refs", f"referencia inválida {r!r}: debe apuntar a un paso anterior", step.id)
        try:
            computed = _apply(step, [forms[r] for r in step.refs], [ctxs[r] for r in step.refs])
        except (ValueError, TypeError) as e:
            raise ProofError("malformed_step", f"paso mal formado: {e}", step.id) from e
        if not _same_set(computed, step.context):
            raise ProofError("context_mismatch", "el contexto declarado no coincide con el que produce la regla", step.id)
        forms[n], ctxs[n] = step.formula, computed
    last = cert.steps[-1]
    if not alpha_equiv(last.formula, cert.conclusion):
        raise ProofError("wrong_conclusion", "el último paso no es la conclusión del certificado", last.id)
    for f in ctxs[last.id]:
        if not _has(cert.premises, f):
            raise ProofError("open_assumption", "queda abierta una hipótesis que no es premisa", last.id)


def is_valid(cert):
    try:
        verify(cert)
    except ProofError:
        return False
    return True
