"""Español controlado a FOL mediante gramática y composición verificable.

Se conservan todas las lecturas distintas; el usuario escoge antes de evaluar.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .ast import Span
from .errors import LogosError
from .printer import to_string
from .spanish_cyk import grammar, parse
from .spanish_semantics import readings as compose_readings
from .symbols import check, parse_checked


@dataclass(frozen=True)
class SpanishReading:
    id: str
    formula: object
    text: str
    signature: object
    note: str

    def to_dict(self):
        return {"id": self.id, "formula": self.text, "note": self.note,
                "signature": {"constants": sorted(self.signature.constants),
                              "functions": self.signature.functions,
                              "predicates": self.signature.predicates}}


@dataclass(frozen=True)
class SpanishResult:
    status: str  # single | ambiguous
    readings: tuple[SpanishReading, ...]

    def to_dict(self):
        return {"status": self.status, "readings": [r.to_dict() for r in self.readings]}


def translate_spanish(text: str) -> SpanishResult:
    if not isinstance(text, str):
        raise LogosError("syntactic", "unsupported_spanish", "Escribe una frase en español", Span(0, 0), "")
    tokens, trees = parse(text)
    if not trees:
        vocabulary = {word for phrase in grammar()[0] for word in phrase} | {"a", "el", "de"}
        for token in tokens:
            if token.text not in vocabulary:
                raise LogosError("syntactic", "unsupported_spanish",
                                 f"Palabra fuera del léxico: {text[token.span.start:token.span.end]}",
                                 token.span, text)
        raise LogosError("syntactic", "unsupported_spanish",
                         "Frase fuera de la gramática controlada; revisa concordancia o usa el editor formal",
                         Span(0, len(text)), text)
    readings = []
    seen = set()
    for tree in trees:
        for formula, note in compose_readings(tree):
            formula = replace(formula, span=Span(0, len(text)))
            sig = check(formula)
            rendered = to_string(formula)
            parse_checked(rendered, sig, strict=True)
            if rendered not in seen:
                seen.add(rendered)
                readings.append(SpanishReading(f"r{len(readings) + 1}", formula, rendered, sig, note))
    return SpanishResult("ambiguous" if len(readings) > 1 else "single", tuple(readings))
