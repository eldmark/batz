"""Parser descendente recursivo de FOL (gramática en docs/specs/FORMAL_LANGUAGE.md)."""
from __future__ import annotations

from . import lexer as L
from .ast import (
    And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies, Not, Or, Pred, Span, Var,
    is_pred_name, is_term_name,
)
from .errors import BatzError

_TOKEN_NAMES = {
    L.EOF: "el final de la entrada", L.LPAREN: "'('", L.RPAREN: "')'", L.COMMA: "','",
    L.NOT: "'¬'", L.AND: "'∧'", L.OR: "'∨'", L.IMPLIES: "'→'", L.IFF: "'↔'",
    L.BOTTOM: "'⊥'", L.FORALL: "'∀'", L.EXISTS: "'∃'", L.EQ: "'='", L.NEQ: "'≠'",
}


def _describe(tok):
    return _TOKEN_NAMES.get(tok.kind) or repr(tok.text)


class _Parser:
    def __init__(self, text, constants, propositional=False):
        self.text = text
        self.propositional = propositional
        self.letters = {}  # modo proposicional: nombre en mayúscula -> (original, span)
        self.toks = L.tokenize(text)
        self.i = 0
        self.constants = frozenset(constants)
        self.bound = []
        self.prev_end = 0

    # --- utilidades -------------------------------------------------------
    def peek(self):
        return self.toks[self.i]

    def next(self):
        tok = self.toks[self.i]
        if tok.kind != L.EOF:
            self.i += 1
        self.prev_end = tok.span.end
        return tok

    def error(self, code, message, span):
        return BatzError("syntactic", code, message, span, self.text)

    def expect(self, kind, what):
        tok = self.peek()
        if tok.kind != kind:
            raise self.error("unexpected_token", f"se esperaba {what} y se encontró {_describe(tok)}", tok.span)
        return self.next()

    def span_from(self, start):
        return Span(start, self.prev_end)

    # --- fórmulas ---------------------------------------------------------
    def parse_all(self):
        f = self.iff()
        tok = self.peek()
        if tok.kind == L.RPAREN:
            raise self.error("unmatched_paren", "')' sin su '(' correspondiente", tok.span)
        if tok.kind != L.EOF:
            raise self.error("unexpected_token", f"{_describe(tok)} inesperado después de una fórmula completa", tok.span)
        return f

    def iff(self):
        start = self.peek().span.start
        left = self.implies()
        if self.peek().kind == L.IFF:
            self.next()
            right = self.implies()
            if self.peek().kind == L.IFF:
                raise self.error("non_associative", "'↔' no es asociativo: usa paréntesis", self.peek().span)
            return Iff(left, right, self.span_from(start))
        return left

    def implies(self):
        start = self.peek().span.start
        left = self.or_()
        if self.peek().kind == L.IMPLIES:
            self.next()
            right = self.implies()
            return Implies(left, right, self.span_from(start))
        return left

    def or_(self):
        start = self.peek().span.start
        left = self.and_()
        while self.peek().kind == L.OR:
            self.next()
            left = Or(left, self.and_(), self.span_from(start))
        return left

    def and_(self):
        start = self.peek().span.start
        left = self.unary()
        while self.peek().kind == L.AND:
            self.next()
            left = And(left, self.unary(), self.span_from(start))
        return left

    def unary(self):
        tok = self.peek()
        start = tok.span.start
        if tok.kind == L.NOT:
            self.next()
            return Not(self.unary(), self.span_from(start))
        if tok.kind in (L.FORALL, L.EXISTS):
            self.next()
            vtok = self.peek()
            if vtok.kind != L.IDENT or not is_term_name(vtok.text):
                raise self.error("expected_variable", f"se esperaba una variable (minúscula) después de {_describe(tok)}", vtok.span)
            if vtok.text in self.constants:
                raise BatzError("semantic", "quantified_constant", f"'{vtok.text}' es una constante y no se puede cuantificar", vtok.span, self.text)
            self.next()
            self.bound.append(vtok.text)
            try:
                body = self.unary()
            finally:
                self.bound.pop()
            cls = Forall if tok.kind == L.FORALL else Exists
            return cls(vtok.text, body, self.span_from(start))
        if tok.kind == L.LPAREN:
            self.next()
            inner = self.iff()
            close = self.peek()
            if close.kind != L.RPAREN:
                if close.kind == L.EOF:
                    raise self.error("unclosed_paren", "paréntesis sin cerrar", tok.span)
                raise self.error("unexpected_token", f"se esperaba ')' y se encontró {_describe(close)}", close.span)
            self.next()
            return inner
        if tok.kind == L.BOTTOM:
            self.next()
            return Bottom(self.span_from(start))
        if tok.kind == L.IDENT:
            if is_pred_name(tok.text):
                return self.pred_atom()
            if self.propositional and self.toks[self.i + 1].kind not in (L.LPAREN, L.EQ, L.NEQ):
                return self.letter(tok)
            return self.eq_atom()
        raise self.error("expected_formula", f"se esperaba una fórmula y se encontró {_describe(tok)}", tok.span)

    def letter(self, tok):
        """Modo proposicional: `p` se lee como la letra `P` (predicado de aridad 0)."""
        self.next()
        name = tok.text[0].upper() + tok.text[1:]
        self.note_letter(name, tok.text, tok.span)
        return Pred(name, (), tok.span)

    def note_letter(self, name, original, span):
        seen = self.letters.setdefault(name, (original, span))
        if seen[0] != original:
            raise BatzError("semantic", "letter_collision",
                             f"'{seen[0]}' y '{original}' se leerían como la misma letra '{name}'", span, self.text)

    def pred_atom(self):
        tok = self.next()
        if self.propositional and self.peek().kind != L.LPAREN:
            self.note_letter(tok.text, tok.text, tok.span)
        args = ()
        if self.peek().kind == L.LPAREN:
            args = self.arguments()
        return Pred(tok.text, args, self.span_from(tok.span.start))

    def eq_atom(self):
        start = self.peek().span.start
        left = self.term()
        op = self.peek()
        if op.kind not in (L.EQ, L.NEQ):
            raise self.error("expected_formula", f"'{left_name(left)}' es un término, no una fórmula: se esperaba '=' o '≠' y se encontró {_describe(op)}", op.span)
        self.next()
        eq = Eq(left, self.term(), self.span_from(start))
        return eq if op.kind == L.EQ else Not(eq, eq.span)

    # --- términos ---------------------------------------------------------
    def arguments(self):
        self.expect(L.LPAREN, "'('")
        args = [self.term()]
        while self.peek().kind == L.COMMA:
            self.next()
            args.append(self.term())
        close = self.peek()
        if close.kind != L.RPAREN:
            raise self.error("unexpected_token", f"se esperaba ',' o ')' y se encontró {_describe(close)}", close.span)
        self.next()
        return tuple(args)

    def term(self):
        tok = self.peek()
        if tok.kind != L.IDENT:
            raise self.error("expected_term", f"se esperaba un término y se encontró {_describe(tok)}", tok.span)
        if not is_term_name(tok.text):
            raise self.error("expected_term", f"'{tok.text}' empieza con mayúscula: es un predicado, no un término", tok.span)
        self.next()
        if self.peek().kind == L.LPAREN:
            args = self.arguments()
            return Func(tok.text, args, self.span_from(tok.span.start))
        if tok.text in self.bound:
            return Var(tok.text, tok.span)
        if tok.text in self.constants:
            return Const(tok.text, tok.span)
        return Var(tok.text, tok.span)  # variable libre


def left_name(term):
    return getattr(term, "name", "?")


def parse(text, constants=(), propositional=False):
    """Parsea una fórmula. `constants`: nombres que se leen como constantes.

    Con `propositional=True`, una minúscula suelta en posición de fórmula (`p`, `q`)
    es una letra proposicional: se lee como el predicado 0-ario de nombre en
    mayúscula (`p` → `P`). Mezclar `p` y `P` en una entrada es un error.
    """
    return _Parser(text, constants, propositional).parse_all()


def parse_term(text, constants=()):
    p = _Parser(text, constants)
    t = p.term()
    tok = p.peek()
    if tok.kind != L.EOF:
        raise p.error("unexpected_token", f"{_describe(tok)} inesperado después de un término", tok.span)
    return t
