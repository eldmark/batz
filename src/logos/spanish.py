"""Español controlado a FOL mediante gramática y composición verificable.

Se conservan todas las lecturas distintas; el usuario escoge antes de evaluar.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import product

from .ast import Span
from .errors import LogosError
from .printer import to_string
from .spanish_cyk import grammar, parse
from .spanish_semantics import readings as compose_readings
from .symbols import check, parse_checked
from . import lexicon


@lru_cache(maxsize=1)
def _builtin_words():
    """Palabras que trae el archivo de gramática: conservan su símbolo de siempre."""
    from .spanish_cyk import GRAMMAR
    words = set()
    for line in GRAMMAR.read_text(encoding="utf-8").splitlines():
        if "->" in line:
            for alternative in line.split("->", 1)[1].split("|"):
                parts = alternative.split()
                if len(parts) == 1 and parts[0][:1].islower():
                    words.add((parts[0],))
    return frozenset(words)


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
    assumptions: tuple = ()  # palabras fuera del léxico y la categoría que se les supuso

    def to_dict(self):
        return {"status": self.status, "readings": [r.to_dict() for r in self.readings],
                "assumptions": list(self.assumptions)}


def _propose(text, tokens, vocabulary):
    """Categorías que el etiquetador propone para las palabras fuera del léxico."""
    from . import spanish_tagger as tagger
    if not tagger.available():
        return [], {}
    originals = [text[t.span.start:t.span.end] for t in tokens]
    closed = vocabulary - {w for phrase, heads in grammar()[0].items() if heads & set(tagger.TAGS) for w in phrase}
    extra, by_word = [], {}
    for i, token in enumerate(tokens):
        if token.text in vocabulary:
            continue
        for tag, probability in tagger.suggest(originals, i, closed):
            extra.append((i, tag))
            by_word.setdefault(i, []).append({"word": originals[i], "tag": tag, "label": tagger.TAG_NAMES[tag],
                                              "probability": round(probability, 3),
                                              "symbol": tagger.guess_predicate(token.text, tag)})
    return extra, by_word


def _agreement_hint(text, tokens):
    """Si cambiar el género de un adjetivo hace que la frase se pueda analizar, lo sugiere."""
    from . import lexicon
    for token in tokens:
        word = token.text
        other = None
        for entry in lexicon.find(word):
            if entry.category != "ADJ":
                continue
            forms = entry.forms()
            for a, b in (("Adj_MS", "Adj_FS"), ("Adj_FS", "Adj_MS"), ("Adj_MP", "Adj_FP"), ("Adj_FP", "Adj_MP")):
                if word in forms[a] and forms[b][0] != word:
                    other = forms[b][0]
        if other is None:
            continue
        candidate = text[:token.span.start] + other + text[token.span.end:]
        try:
            if parse(candidate)[1]:
                return (f"«{text[token.span.start:token.span.end]}» no concuerda en género con su sujeto. "
                        f"¿Quisiste decir «{other}»?", token.span)
        except LogosError:
            continue
    return None


def _used_tags(tree, found):
    if tree.text and not tree.children:
        found.add((tree.start, tree.symbol))
    for child in tree.children:
        _used_tags(child, found)
    return found


def translate_spanish(text: str) -> SpanishResult:
    if not isinstance(text, str):
        raise LogosError("syntactic", "unsupported_spanish", "Escribe una frase en español", Span(0, 0), "")
    tokens, trees = parse(text)
    vocabulary = {word for phrase in grammar()[0] for word in phrase} | {"a", "el", "de"}
    proposals = {}
    if not trees and any(t.text not in vocabulary for t in tokens):
        # Palabras fuera del léxico: el etiquetador propone su categoría y la gramática decide si encaja.
        extra, proposals = _propose(text, tokens, vocabulary)
        if extra:
            tokens, trees = parse(text, extra)
    if not trees:
        hint = _agreement_hint(text, tokens)
        if not hint and tokens[0].text in ("los", "las", "el", "la"):
            # La especificación rechaza el artículo solo: no dice si se habla de todos o de algunos.
            hint = (f"«{text[tokens[0].span.start:tokens[0].span.end]}» solo no dice cuántos: empieza con «todos los», "
                    "«algunos», «ningún» o «un».", tokens[0].span)
        if hint:
            raise LogosError("syntactic", "unsupported_spanish", hint[0], hint[1], text)
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
    used = set()
    for tree in trees:
        _used_tags(tree, used)
    assumptions = [a for i, options in sorted(proposals.items()) for a in options if (i, a["tag"]) in used]
    from . import spanish_semantics
    spanish_semantics.EXTRA.clear()
    for a in assumptions:
        key = "V" if a["tag"].startswith("V") else a["tag"].split("_")[0]
        if key != "NProp":
            spanish_semantics.EXTRA[(key, a["word"].casefold())] = a["symbol"]
    # Palabras con varios sentidos: una lectura por combinación, nunca una elegida en silencio.
    builtin = {phrase[0] for phrase in _builtin_words()}
    ambiguous = {}
    for position, tag in sorted(used):
        kind = "V" if tag.startswith("V") else tag.split("_")[0]
        word = tokens[position].text
        if kind == "NProp" or word in builtin:
            continue
        options = lexicon.senses(kind, word)
        if len(options) > 1:
            ambiguous[(kind, word)] = options
    keys = list(ambiguous)
    combos = list(product(*(ambiguous[k] for k in keys)))[:16] or [()]
    for combo in combos:
        spanish_semantics.SENSE.clear()
        spanish_semantics.SENSE.update({k: sym for k, (sym, _) in zip(keys, combo)})
        chosen = "; ".join(f"«{k[1]}» como {gloss}" for k, (_, gloss) in zip(keys, combo))
        for tree in trees:
            for formula, note in compose_readings(tree):
                formula = replace(formula, span=Span(0, len(text)))
                sig = check(formula)
                rendered = to_string(formula)
                parse_checked(rendered, sig, strict=True)
                if rendered not in seen:
                    seen.add(rendered)
                    readings.append(SpanishReading(f"r{len(readings) + 1}", formula, rendered, sig,
                                                   f"{note}: {chosen}" if chosen else note))
    spanish_semantics.SENSE.clear()
    spanish_semantics.EXTRA.clear()
    return SpanishResult("ambiguous" if len(readings) > 1 else "single", tuple(readings), tuple(assumptions))
