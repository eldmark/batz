"""Lexer de FOL: tokens con offsets y errores localizables."""
from __future__ import annotations

from dataclasses import dataclass

from .ast import RESERVED, Span
from .errors import BatzError

IDENT, LPAREN, RPAREN, COMMA = "IDENT", "LPAREN", "RPAREN", "COMMA"
NOT, AND, OR, IMPLIES, IFF = "NOT", "AND", "OR", "IMPLIES", "IFF"
FORALL, EXISTS, EQ, NEQ, EOF = "FORALL", "EXISTS", "EQ", "NEQ", "EOF"
BOTTOM = "BOTTOM"

# Más largos primero: `<->` antes que `->`, `!=` antes que `!`.
_SYMBOLS = [
    ("_|_", BOTTOM), ("⊥", BOTTOM),
    ("<->", IFF), ("/\\", AND), ("\\/", OR), ("->", IMPLIES), ("!=", NEQ),
    ("¬", NOT), ("~", NOT), ("!", NOT),
    ("∧", AND), ("&", AND),
    ("∨", OR), ("|", OR),
    ("→", IMPLIES), ("↔", IFF),
    ("∀", FORALL), ("∃", EXISTS),
    ("≠", NEQ), ("=", EQ),
    ("(", LPAREN), (")", RPAREN), (",", COMMA),
]
_KEYWORDS = {"forall": FORALL, "exists": EXISTS}
assert set(_KEYWORDS) == RESERVED


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    span: Span


def tokenize(text):
    toks, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        for sym, kind in _SYMBOLS:
            if text.startswith(sym, i):
                toks.append(Token(kind, sym, Span(i, i + len(sym))))
                i += len(sym)
                break
        else:
            if c.isalpha():
                j = i + 1
                while j < n and (text[j].isalnum() or text[j] in "_'"):
                    j += 1
                word = text[i:j]
                if not (c.isupper() or c.islower()):
                    raise BatzError(
                        "lexical", "caseless_identifier",
                        f"el identificador {word!r} debe empezar con mayúscula (predicado) o minúscula (término)",
                        Span(i, j), text,
                    )
                toks.append(Token(_KEYWORDS.get(word, IDENT), word, Span(i, j)))
                i = j
            else:
                raise BatzError(
                    "lexical", "unexpected_char",
                    f"carácter inesperado {c!r}", Span(i, i + 1), text,
                )
    toks.append(Token(EOF, "", Span(n, n)))
    return toks
