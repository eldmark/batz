"""Etiquetador de palabras fuera del léxico del español controlado.

Regresión logística multinomial entrenada por descenso de gradiente (ver
`scripts/train_spanish_tagger.py`). Aquí solo está la inferencia, en Python estándar.

El etiquetador **propone** la categoría de una palabra desconocida; no decide nada lógico.
La frase con las categorías propuestas tiene que pasar por la misma gramática, y la persona
ve qué se supuso antes de usar la fórmula.
"""
from __future__ import annotations

import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path

WEIGHTS = Path(__file__).with_name("spanish_tagger.json")
TAGS = ("N_MS", "N_MP", "N_FS", "N_FP", "Adj_MS", "Adj_MP", "Adj_FS", "Adj_FP",
        "VI_S", "VI_P", "VT_S", "VT_P", "VIsub_S", "VIsub_P", "VTsub_S", "VTsub_P",
        "NProp_M", "NProp_F")
TAG_NAMES = {
    "N_MS": "sustantivo masculino singular", "N_MP": "sustantivo masculino plural",
    "N_FS": "sustantivo femenino singular", "N_FP": "sustantivo femenino plural",
    "Adj_MS": "adjetivo masculino singular", "Adj_MP": "adjetivo masculino plural",
    "Adj_FS": "adjetivo femenino singular", "Adj_FP": "adjetivo femenino plural",
    "VI_S": "verbo sin objeto, singular", "VI_P": "verbo sin objeto, plural",
    "VT_S": "verbo con objeto, singular", "VT_P": "verbo con objeto, plural",
    "VIsub_S": "verbo sin objeto en subjuntivo, singular", "VIsub_P": "verbo sin objeto en subjuntivo, plural",
    "VTsub_S": "verbo con objeto en subjuntivo, singular", "VTsub_P": "verbo con objeto en subjuntivo, plural",
    "NProp_M": "nombre propio masculino", "NProp_F": "nombre propio femenino",
}


def plain(word):
    """Sin tildes ni diéresis; conserva la ñ."""
    out = []
    for ch in word:
        if ch in "ñÑ":
            out.append(ch)
        else:
            out.append("".join(c for c in unicodedata.normalize("NFD", ch) if unicodedata.category(c) != "Mn"))
    return "".join(out)


def features(words, i, closed):
    """Rasgos de la palabra `i`. `words`: formas originales; `closed`: palabras funcionales conocidas."""
    raw = words[i]
    w = raw.casefold()

    def ctx(j):
        if j < 0:
            return "<ini>"
        if j >= len(words):
            return "<fin>"
        other = words[j].casefold()
        return other if other in closed else ("<may>" if words[j][:1].isupper() else "<abierta>")

    feats = ["sesgo", f"l={min(len(w), 9)}", f"ant={ctx(i - 1)}", f"sig={ctx(i + 1)}",
             f"ant2={ctx(i - 2)}", f"par={ctx(i - 1)}|{ctx(i + 1)}"]
    for n in (1, 2, 3, 4):
        if len(w) > n:
            feats.append(f"s{n}={w[-n:]}")
    if raw[:1].isupper():
        feats.append("may_ini" if i == 0 else "may")
    if plain(w) != w:
        feats.append("tilde")
    return feats


def guess_predicate(word, tag):
    """Nombre de símbolo para una palabra etiquetada: lema aproximado, sin tildes."""
    w = plain(word.casefold())
    kind, _, form = tag.partition("_")
    if kind == "NProp":
        return w
    if kind in ("N", "Adj"):
        if form.endswith("P"):
            if w.endswith("ces"):
                w = w[:-3] + "z"
            elif w.endswith("es") and len(w) > 3 and w[-3] not in "aeiou":
                w = w[:-2]
            elif w.endswith("s"):
                w = w[:-1]
        if kind == "Adj" and form.startswith("F"):
            if w.endswith("ora"):
                w = w[:-1]
            elif w.endswith("a"):
                w = w[:-1] + "o"
        return w.capitalize()
    # verbos: infinitivo aproximado a partir de la vocal temática
    if form == "P" and w.endswith("n"):
        w = w[:-1]
    subjunctive = "sub" in kind
    if w.endswith("a"):
        w = w[:-1] + ("er" if subjunctive else "ar")
    elif w.endswith("e"):
        w = w[:-1] + ("ar" if subjunctive else "er")
    return w.capitalize()


@lru_cache(maxsize=1)
def _model():
    data = json.loads(WEIGHTS.read_text(encoding="utf-8"))
    return data["tags"], data["weights"], data.get("meta", {})


def available():
    return WEIGHTS.is_file()


def meta():
    return _model()[2]


def probabilities(words, i, closed):
    tags, weights, _ = _model()
    scores = [0.0] * len(tags)
    for f in features(words, i, closed):
        for j, value in weights.get(f, ()):
            scores[j] += value
    top = max(scores)
    exps = [math.exp(s - top) for s in scores]
    total = sum(exps)
    return sorted(((tags[j], e / total) for j, e in enumerate(exps)), key=lambda x: -x[1])


def suggest(words, i, closed, floor=0.2, limit=2):
    """Las categorías más probables de la palabra `i`: la primera siempre, la segunda si no es remota."""
    ranked = probabilities(words, i, closed)
    out = [ranked[0]]
    for tag, p in ranked[1:limit]:
        if p >= floor:
            out.append((tag, p))
    return out
