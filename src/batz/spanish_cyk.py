"""Gramática española acotada: tokenización con spans y CYK con cierre unario.

Conserva todas las derivaciones hasta el límite explícito. Nunca escoge un árbol.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from collections import deque
import re

from .ast import Span
from .errors import BatzError


GRAMMAR = Path(__file__).with_name("spanish_grammar.txt")
WORD = re.compile(r"[^\W_]+|,|[.;:¿?¡!]", re.UNICODE)
MAX_TREES = 512


@dataclass(frozen=True)
class Token:
    text: str
    span: Span


@dataclass(frozen=True)
class Tree:
    symbol: str
    children: tuple["Tree", ...] = ()
    text: str = ""
    start: int = 0
    end: int = 0


def tokenize(text: str) -> tuple[Token, ...]:
    if not isinstance(text, str) or not text.strip():
        raise BatzError("syntactic", "unsupported_spanish", "Escribe una frase en español", Span(0, 0), text or "")
    result = []
    pos = 0
    for match in WORD.finditer(text):
        gap = text[pos:match.start()]
        if gap.strip():
            raise BatzError("syntactic", "unsupported_spanish", "Carácter fuera del español controlado", Span(pos, match.start()), text)
        word = match.group().casefold()
        if word in (".", ";", ":", "¿", "?", "¡", "!"):
            pos = match.end(); continue
        if word == "del":
            result.extend((Token("de", Span(*match.span())), Token("el", Span(*match.span()))))
        elif word == "al" and not text[match.end():].lstrip().casefold().startswith("menos"):
            result.extend((Token("a", Span(*match.span())), Token("el", Span(*match.span()))))
        else:
            result.append(Token(word, Span(*match.span())))
        pos = match.end()
    if text[pos:].strip():
        raise BatzError("syntactic", "unsupported_spanish", "Carácter fuera del español controlado", Span(pos, len(text)), text)
    if not result:
        raise BatzError("syntactic", "unsupported_spanish", "Escribe una frase en español", Span(0, len(text)), text)
    if len(result) > 40:
        raise BatzError("syntactic", "unsupported_spanish", "La frase supera el límite de 40 palabras", Span(0, len(text)), text)
    return tuple(result)


@lru_cache(maxsize=1)
def grammar():
    lines = GRAMMAR.read_text(encoding="utf-8").splitlines()
    rules = []
    heads = {line.split("->", 1)[0].strip() for line in lines if "->" in line}
    for line in lines:
        if "->" not in line: continue
        head, body = (s.strip() for s in line.split("->", 1))
        for alternative in body.split("|"):
            words = tuple(alternative.strip().split())
            rules.append((head, words))
    lex, unary, binary = {}, {}, {}
    for head, words in rules:
        if all(word in heads for word in words):
            if len(words) == 1:
                unary.setdefault(words[0], set()).add(head)
            elif len(words) == 2:
                binary.setdefault(words, set()).add(head)
            else:
                # Right binarization. Synthetic nodes are removed from final trees.
                tail = words[-1]
                for i in range(len(words) - 2, 0, -1):
                    aux = f"@{head}:{words}:{i}"
                    binary.setdefault((words[i], tail), set()).add(aux)
                    tail = aux
                binary.setdefault((words[0], tail), set()).add(head)
        else:
            lex.setdefault(words, set()).add(head)
    # Diccionario: cada forma flexionada entra con su categoría. Las palabras que ya trae la
    # gramática conservan sus categorías y símbolos (de ellas dependen los 51 casos).
    from . import lexicon
    builtin = {phrase[0] for phrase in lex if len(phrase) == 1}
    for tag, forms in lexicon.grammar_forms().items():
        for form in forms:
            if form not in builtin:
                lex.setdefault((form,), set()).add(tag)
    return lex, unary, binary


@lru_cache(maxsize=1)
def _automaton():
    """Aho-Corasick sobre palabras y expresiones fijas del léxico."""
    lex = grammar()[0]
    edges, failure, outputs = [{}], [0], [[]]
    for phrase in sorted(lex):
        state = 0
        for word in phrase:
            if word not in edges[state]:
                edges[state][word] = len(edges)
                edges.append({}); failure.append(0); outputs.append([])
            state = edges[state][word]
        outputs[state].append(phrase)
    pending = deque(edges[0].values())
    while pending:
        state = pending.popleft()
        for word, child in edges[state].items():
            parent = failure[state]
            while parent and word not in edges[parent]: parent = failure[parent]
            failure[child] = edges[parent].get(word, 0)
            outputs[child].extend(outputs[failure[child]])
            pending.append(child)
    return edges, failure, outputs


def _lexical_hits(tokens):
    edges, failure, outputs = _automaton()
    state = 0
    for end, token in enumerate(tokens, 1):
        while state and token.text not in edges[state]: state = failure[state]
        state = edges[state].get(token.text, 0)
        for phrase in outputs[state]:
            yield end - len(phrase), len(phrase), phrase


def parse(text: str, extra=()) -> tuple[tuple[Token, ...], tuple[Tree, ...]]:
    """`extra`: pares (posición, categoría) para palabras fuera del léxico que alguien propuso."""
    tokens = tokenize(text)
    lex, unary, binary = grammar()
    n = len(tokens)
    table = [[{} for _ in range(n + 1)] for _ in range(n)]

    def add(cell, symbol, pointer):
        pointers = cell.setdefault(symbol, [])
        if pointer not in pointers: pointers.append(pointer)

    def close(cell):
        pending = list(cell)
        while pending:
            child = pending.pop()
            for head in sorted(unary.get(child, ())):
                pointer = ("u", child)
                if pointer not in cell.get(head, ()):
                    add(cell, head, pointer)
                    pending.append(head)

    for start, length, words in _lexical_hits(tokens):
        cell = table[start][length]
        for head in sorted(lex[words]): add(cell, head, ("w", " ".join(words)))
        close(cell)
    for position, head in extra:
        cell = table[position][1]
        add(cell, head, ("w", tokens[position].text))
        close(cell)
    for length in range(1, n + 1):
        for start in range(n - length + 1):
            cell = table[start][length]
            for split in range(1, length):
                for left in table[start][split]:
                    for right in table[start + split][length - split]:
                        for head in sorted(binary.get((left, right), ())):
                            add(cell, head, ("b", split, left, right))
            close(cell)

    @lru_cache(maxsize=None)
    def build(symbol, start, length):
        result = []
        for pointer in table[start][length].get(symbol, ()):
            kind = pointer[0]
            if kind == "w":
                result.append(Tree(symbol, text=pointer[1], start=start, end=start + length))
            elif kind == "u":
                result.extend(Tree(symbol, (child,), start=start, end=start + length)
                              for child in build(pointer[1], start, length))
            else:
                _, split, left, right = pointer
                for a in build(left, start, split):
                    for b in build(right, start + split, length - split):
                        children = (a,) + (b.children if b.symbol.startswith("@") else (b,))
                        result.append(Tree(symbol, children, start=start, end=start + length))
                        if len(result) > MAX_TREES: break
                    if len(result) > MAX_TREES: break
            if len(result) > MAX_TREES: break
        return tuple(result)

    roots = build("S", 0, n)
    if len(roots) > MAX_TREES:
        raise BatzError("syntactic", "unsupported_spanish", "Demasiadas lecturas; reformula la frase", Span(0, len(text)), text)
    return tokens, roots
