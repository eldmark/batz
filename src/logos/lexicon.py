"""Diccionario del español controlado: lemas con categoría, género y formas flexionadas.

El léxico base (`lexicon.tsv`) viaja con el programa; las palabras que añade la persona se
guardan aparte (`datos/lexico_usuario.tsv`, o la ruta de `LOGOS_LEXICON`). De cada lema salen
sus formas y la categoría gramatical de cada una, que la gramática usa como entradas léxicas.
El símbolo lógico de una palabra es su lema sin tildes: `duermen` → `Dormir`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .errors import LogosError
from .spanish_tagger import plain

BASE = Path(__file__).with_name("lexicon.tsv")
CATEGORIES = {"N": "sustantivo", "ADJ": "adjetivo", "V": "verbo", "NP": "nombre propio"}
GENDERS = {"M": "masculino", "F": "femenino", "C": "masculino y femenino"}
USES = {"I": "sin objeto", "T": "con objeto", "IT": "con o sin objeto"}
VOWELS = "aeiouáéíóú"
_ACCENT = str.maketrans("áéíóú", "aeiou")


def user_path():
    custom = os.environ.get("LOGOS_LEXICON")
    return Path(custom) if custom else Path(__file__).resolve().parents[2] / "datos" / "lexico_usuario.tsv"


@dataclass(frozen=True)
class Entry:
    lemma: str
    category: str      # N | ADJ | V | NP
    feature: str       # género (N, NP) o uso (V); "-" en adjetivos
    extra: str = ""
    source: str = "base"

    @property
    def symbol(self):
        base = plain(self.lemma.casefold())
        return base if self.category == "NP" else base.capitalize()

    def options(self):
        out = {}
        for part in self.extra.split(";"):
            key, _, value = part.strip().partition("=")
            if key:
                out[key] = value
        return out

    def forms(self):
        """`{etiqueta gramatical: [formas]}` de este lema."""
        opts = self.options()
        w = self.lemma.casefold()
        if self.category == "NP":
            return {f"NProp_{g}": [w] for g in ("MF" if self.feature == "C" else self.feature)}
        if self.category == "N":
            many = opts.get("pl") or plural(w)
            return {tag: [form] for g in ("MF" if self.feature == "C" else self.feature)
                    for tag, form in ((f"N_{g}S", w), (f"N_{g}P", many))}
        if self.category == "ADJ":
            fem = w if "inv" in opts else feminine(w)
            return {"Adj_MS": [w], "Adj_MP": [opts.get("pl") or plural(w)], "Adj_FS": [fem],
                    "Adj_FP": [opts.get("pl") if fem == w and opts.get("pl") else plural(fem)]}
        s3, p3, sub_s, sub_p, pret_s, pret_p = conjugate(w, opts)
        out = {}
        for kind in (("VI",) if self.feature == "I" else ("VT",) if self.feature == "T" else ("VI", "VT")):
            out[f"{kind}_S"] = [s3, pret_s]
            out[f"{kind}_P"] = [p3, pret_p]
            out[f"{kind}sub_S"] = [sub_s]
            out[f"{kind}sub_P"] = [sub_p]
        return out

    def to_dict(self):
        forms = self.forms()
        flat = []
        for values in forms.values():
            for f in values:
                if f not in flat:
                    flat.append(f)
        feature = GENDERS.get(self.feature) if self.category in ("N", "NP") else USES.get(self.feature, "")
        return {"lemma": self.lemma, "category": self.category, "category_label": CATEGORIES[self.category],
                "feature": self.feature, "feature_label": feature or "", "extra": self.extra,
                "symbol": self.symbol, "forms": flat, "source": self.source}


# --- flexión ----------------------------------------------------------------

def plural(word):
    if word.endswith("z"):
        return word[:-1] + "ces"
    for tail in ("ón", "án", "én", "ín", "és", "ún"):
        if word.endswith(tail) and len(word) > 3:
            return word[:-2] + tail.translate(_ACCENT) + "es"
    return word + ("s" if word[-1] in VOWELS else "es")


def feminine(word):
    if word.endswith("o"):
        return word[:-1] + "a"
    for tail in ("or", "ón", "án", "ín", "és"):
        if word.endswith(tail):
            return word[:-len(tail)] + tail.translate(_ACCENT) + "a"
    return word


def _change(stem, change, preterite=False):
    """Cambio de raíz en la última vocal afectada: o→ue, e→ie, e→i (y o→u / e→i en el pasado de -ir)."""
    target, new = {"ue": ("o", "u" if preterite else "ue"), "ie": ("e", "i" if preterite else "ie"),
                   "i": ("e", "i")}[change]
    i = stem.rfind(target)
    return stem if i < 0 else stem[:i] + new + stem[i + 1:]


def conjugate(inf, opts=None):
    """(él presente, ellos presente, él subjuntivo, ellos subjuntivo, él pasado, ellos pasado)."""
    opts = opts or {}
    if opts.get("formas"):
        forms = [f.strip() for f in opts["formas"].split(",")]
        if len(forms) != 6 or not all(forms):
            raise LogosError("semantic", "invalid_lexicon", f"«formas» de {inf} debe traer seis formas")
        return tuple(forms)
    if len(inf) < 3 or plain(inf[-2:]) not in ("ar", "er", "ir"):
        raise LogosError("semantic", "invalid_lexicon", f"«{inf}» no es un infinitivo (-ar, -er, -ir)")
    stem, cls = inf[:-2], plain(inf[-2:])
    change = opts.get("cambio")
    present = _change(stem, change) if change else stem
    past = _change(stem, change, preterite=True) if change and cls == "ir" else stem
    if cls == "ar":
        sub = present
        if stem.endswith("c"): sub = present[:-1] + "qu"
        elif stem.endswith("g"): sub = present + "u"
        elif stem.endswith("z"): sub = present[:-1] + "c"
        return (present + "a", present + "an", sub + "e", sub + "en", stem + "ó", stem + "aron")
    sub = present
    if stem.endswith("gu"): sub = present[:-1]                       # seguir → siga
    elif stem.endswith("g"): sub = present[:-1] + "j"                 # proteger → proteja
    elif stem.endswith("c") and len(stem) > 1 and stem[-2] in VOWELS: sub = present[:-1] + "zc"   # crecer → crezca
    elif stem.endswith("c"): sub = present[:-1] + "z"                 # vencer → venza
    if stem.endswith("u") and not stem.endswith(("gu", "qu")) and cls == "ir":   # construir → construye
        return (stem + "ye", stem + "yen", stem + "ya", stem + "yan", stem + "yó", stem + "yeron")
    if stem[-1:] in ("e", "a", "o") and cls == "er":                  # leer → leyó
        return (stem + "e", stem + "en", stem + "a", stem + "an", stem + "yó", stem + "yeron")
    return (present + "e", present + "en", sub + "a", sub + "an", past + "ió", past + "ieron")


# --- carga ------------------------------------------------------------------

def _read(path, source):
    entries = []
    if not path.is_file():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cols = (line.split("\t") + ["", "", ""])[:4]
        lemma, category, feature, extra = (c.strip() for c in cols)
        if category in CATEGORIES and lemma:
            entries.append(Entry(lemma, category, feature or "-", extra, source))
    return entries


@lru_cache(maxsize=1)
def entries():
    return tuple(_read(BASE, "base") + _read(user_path(), "usuario"))


@lru_cache(maxsize=1)
def _tables():
    """(etiqueta → formas, (clase semántica, forma) → símbolo)."""
    by_tag, symbols = {}, {}
    for e in entries():
        try:
            forms = e.forms()
        except LogosError:
            continue
        kind = {"N": "N", "ADJ": "Adj", "V": "V", "NP": "NProp"}[e.category]
        for tag, values in forms.items():
            for form in values:
                by_tag.setdefault(tag, set()).add(form)
                symbols.setdefault((kind, form), e.symbol)
    return by_tag, symbols


def grammar_forms():
    return _tables()[0]


def symbol(kind, form):
    """Símbolo lógico de una forma (`kind`: N, Adj o V), o None si no está en el diccionario."""
    return _tables()[1].get((kind, form))


def reload():
    entries.cache_clear(); _tables.cache_clear()
    from . import spanish_cyk
    spanish_cyk.grammar.cache_clear(); spanish_cyk._automaton.cache_clear()


def find(word):
    """Entradas cuyo lema o alguna forma coincide con la palabra."""
    w = word.casefold().strip()
    out = []
    for e in entries():
        try:
            if e.lemma.casefold() == w or any(w in values for values in e.forms().values()):
                out.append(e)
        except LogosError:
            continue
    return out


def search(query="", category="", source="", limit=60, offset=0):
    q = plain(query.casefold().strip())
    hits = []
    for e in entries():
        if category and e.category != category:
            continue
        if source and e.source != source:
            continue
        if q:
            try:
                haystack = [e.lemma.casefold(), *(f for values in e.forms().values() for f in values)]
            except LogosError:
                haystack = [e.lemma.casefold()]
            if not any(plain(h).startswith(q) for h in haystack):
                continue
        hits.append(e)
    hits.sort(key=lambda e: (plain(e.lemma.casefold()), e.category))
    return len(hits), hits[offset:offset + limit]


def counts():
    out = {c: 0 for c in CATEGORIES}
    user = 0
    for e in entries():
        out[e.category] += 1
        user += e.source == "usuario"
    return {"total": len(entries()), "user": user, "by_category": out}


def _validate(lemma, category, feature, extra):
    lemma = (lemma or "").strip()
    if not lemma or not all(ch.isalpha() for ch in lemma) or len(lemma) > 40:
        raise LogosError("semantic", "invalid_lexicon", "el lema debe ser una sola palabra, solo letras")
    if category not in CATEGORIES:
        raise LogosError("semantic", "invalid_lexicon", "categoría desconocida")
    allowed = {"N": GENDERS, "NP": ("M", "F"), "V": USES, "ADJ": ("-",)}[category]
    if feature not in allowed:
        raise LogosError("semantic", "invalid_lexicon",
                         "falta el género" if category in ("N", "NP") else "falta indicar si el verbo lleva objeto")
    extra = (extra or "").strip()
    if "\t" in extra or "\n" in extra or len(extra) > 200:
        raise LogosError("semantic", "invalid_lexicon", "datos extra inválidos")
    entry = Entry(lemma if category == "NP" else lemma.casefold(), category, feature, extra, "usuario")
    for values in entry.forms().values():      # lanza si no se puede flexionar
        for form in values:
            if not form or not all(ch.isalpha() for ch in form):
                raise LogosError("semantic", "invalid_lexicon", f"forma inválida: «{form}»")
    return entry


def add(lemma, category, feature, extra=""):
    """Guarda una palabra del usuario y recarga la gramática. Devuelve la entrada."""
    entry = _validate(lemma, category, feature, extra)
    key = (entry.lemma.casefold(), entry.category, entry.feature)
    if any((e.lemma.casefold(), e.category, e.feature) == key for e in entries()):
        raise LogosError("semantic", "duplicate_lexicon", f"«{entry.lemma}» ya está en el diccionario con esa categoría")
    path = user_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.is_file()
        with path.open("a", encoding="utf-8") as fh:
            if new:
                fh.write("# Palabras añadidas desde la página de diccionario: lema, categoría, género o uso, extra.\n")
            fh.write("\t".join((entry.lemma, entry.category, entry.feature, entry.extra)) + "\n")
    except OSError as exc:
        raise LogosError("semantic", "invalid_lexicon", f"no se pudo guardar en {path}: {exc.strerror}")
    reload()
    return entry


def remove(lemma, category):
    """Quita una palabra añadida por el usuario (las del léxico base no se borran desde aquí)."""
    path = user_path()
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [l for l in lines if l.startswith("#") or (l.split("\t") + ["", ""])[:2] != [lemma, category]]
    if len(kept) == len(lines):
        return False
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    reload()
    return True
