"""Forma clausal: fórmulas de primer orden → conjunto de cláusulas (motor B).

Representación propia y mínima, independiente del AST y del motor A:
  término   variable `"?n"` (str) o tupla `(nombre, arg1, …)`; una constante es `(nombre,)`
  literal   `(signo, predicado, args)`; la igualdad es el predicado `"="`
  cláusula  `frozenset` de literales; la vacía es la contradicción
"""
from __future__ import annotations

from itertools import count

from ..ast import And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred, Var
from ..transform import free_vars

EQ = "="


class TooManyClauses(Exception):
    """La forma normal conjuntiva superó la cota: se informa como límite, no como resultado."""


def is_var(t):
    return isinstance(t, str)


def _nnf(f, positive=True):
    """Forma normal negativa como árbol ('and'|'or'|'all'|'ex'|'lit'|'true'|'false', …)."""
    if isinstance(f, Bottom):
        return ("false",) if positive else ("true",)
    if isinstance(f, (Pred, Eq)):
        return ("lit", positive, f)
    if isinstance(f, Not):
        return _nnf(f.operand, not positive)
    if isinstance(f, And):
        return ("and" if positive else "or", _nnf(f.left, positive), _nnf(f.right, positive))
    if isinstance(f, Or):
        return ("or" if positive else "and", _nnf(f.left, positive), _nnf(f.right, positive))
    if isinstance(f, Implies):  # A → B  ≡  ¬A ∨ B
        return ("or" if positive else "and", _nnf(f.left, not positive), _nnf(f.right, positive))
    if isinstance(f, Iff):  # (A → B) ∧ (B → A); negada: (A ∨ B) ∧ (¬A ∨ ¬B)
        if positive:
            return ("and", ("or", _nnf(f.left, False), _nnf(f.right, True)),
                    ("or", _nnf(f.right, False), _nnf(f.left, True)))
        return ("and", ("or", _nnf(f.left, True), _nnf(f.right, True)),
                ("or", _nnf(f.left, False), _nnf(f.right, False)))
    if isinstance(f, Forall):
        return ("all" if positive else "ex", f.var, _nnf(f.body, positive))
    if isinstance(f, Exists):
        return ("ex" if positive else "all", f.var, _nnf(f.body, positive))
    raise TypeError(f"nodo desconocido: {f!r}")


class Clausifier:
    """Acumula cláusulas de varias fórmulas con variables y funciones de Skolem sin repetir."""

    def __init__(self, max_clauses=4000):
        self._var = count(1)
        self._sk = count(1)
        self.max_clauses = max_clauses
        self.functions = {}   # nombre → aridad (incluye constantes, aridad 0, y Skolem)
        self.predicates = {}  # nombre → aridad
        self.uses_equality = False

    def _term(self, t, env):
        if isinstance(t, Var):
            # una variable libre vale un elemento arbitrario pero fijo: se trata como constante
            return env.get(t.name, (f"v:{t.name}",))
        if isinstance(t, Const):
            self.functions[t.name] = 0
            return (t.name,)
        self.functions[t.name] = len(t.args)
        return (t.name, *(self._term(a, env) for a in t.args))

    def _literal(self, positive, atom, env):
        if isinstance(atom, Eq):
            self.uses_equality = True
            return (positive, EQ, (self._term(atom.left, env), self._term(atom.right, env)))
        self.predicates[atom.name] = len(atom.args)
        return (positive, atom.name, tuple(self._term(a, env) for a in atom.args))

    def _cnf(self, node, env, universals):
        kind = node[0]
        if kind == "true":
            return []
        if kind == "false":
            return [frozenset()]
        if kind == "lit":
            return [frozenset([self._literal(node[1], node[2], env)])]
        if kind == "all":
            v = f"?{next(self._var)}"
            return self._cnf(node[2], {**env, node[1]: v}, universals + (v,))
        if kind == "ex":  # Skolem: el testigo depende de los universales en cuyo alcance está
            name = f"sk{next(self._sk)}"
            self.functions[name] = len(universals)
            return self._cnf(node[2], {**env, node[1]: (name, *universals)}, universals)
        left, right = self._cnf(node[1], env, universals), self._cnf(node[2], env, universals)
        if kind == "and":
            out = left + right
        else:  # distribución de ∨ sobre ∧
            if len(left) * len(right) > self.max_clauses:
                raise TooManyClauses
            out = [a | b for a in left for b in right]
        if len(out) > self.max_clauses:
            raise TooManyClauses
        return out

    def add(self, formula, negate=False):
        for v in free_vars(formula):
            self.functions[f"v:{v}"] = 0
        return [c for c in self._cnf(_nnf(formula, not negate), {}, ()) if not is_tautology(c)]

    def equality_axioms(self):
        """Reflexividad, simetría, transitividad y congruencia para cada símbolo usado."""
        if not self.uses_equality:
            return []
        x, y, z = "?x", "?y", "?z"
        eq = lambda a, b, sign=True: (sign, EQ, (a, b))
        axioms = [frozenset([eq(x, x)]),
                  frozenset([eq(x, y, False), eq(y, x)]),
                  frozenset([eq(x, y, False), eq(y, z, False), eq(x, z)])]
        for name, arity in self.functions.items():
            for i in range(arity):
                args = [f"?a{j}" for j in range(arity)]
                other = args[:i] + [y] + args[i + 1:]
                args[i] = x
                axioms.append(frozenset([eq(x, y, False), eq((name, *args), (name, *other))]))
        for name, arity in self.predicates.items():
            for i in range(arity):
                args = [f"?a{j}" for j in range(arity)]
                other = args[:i] + [y] + args[i + 1:]
                args[i] = x
                axioms.append(frozenset([eq(x, y, False), (False, name, tuple(args)), (True, name, tuple(other))]))
        return axioms


def is_tautology(clause):
    return any((not sign, pred, args) in clause for sign, pred, args in clause)


def term_text(t):
    if is_var(t):
        return f"x{t[1:]}" if t[1:].isdigit() else t[1:].replace("_g", "'")
    name = t[0][2:] if t[0].startswith("v:") else t[0]
    return name if len(t) == 1 else f"{name}({', '.join(term_text(a) for a in t[1:])})"


def literal_text(lit):
    sign, pred, args = lit
    if pred == EQ:
        return f"{term_text(args[0])} {'=' if sign else '≠'} {term_text(args[1])}"
    body = pred if not args else f"{pred}({', '.join(term_text(a) for a in args)})"
    return body if sign else f"¬{body}"


def clause_text(clause):
    return " ∨ ".join(sorted(literal_text(l) for l in clause)) if clause else "□"
