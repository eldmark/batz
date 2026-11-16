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
_ACCENT_ONE = _ACCENT


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
        """Símbolo lógico: el lema sin tildes. Un sinónimo usa el de su palabra principal
        (`sin=perro` → `Perro`); una palabra con varios sentidos lleva el suyo (`Banco_asiento`)."""
        opts = self.options()
        base = plain((opts.get("sin") or self.lemma).casefold())
        if self.category != "NP":
            base = base[:1].upper() + base[1:]
        if opts.get("sentido") and not opts.get("sin"):
            base += "_" + plain(opts["sentido"].casefold())
        return base

    @property
    def gloss(self):
        opts = self.options()
        if opts.get("dim"):
            return "diminutivo de " + opts["dim"]
        if opts.get("part"):
            return "participio de " + opts["part"]
        if opts.get("sin"):
            return "sinónimo de " + opts["sin"].replace("_", ", sentido ")
        return opts.get("sentido", "")

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
                "symbol": self.symbol, "gloss": self.gloss, "forms": flat, "source": self.source}


# --- flexión ----------------------------------------------------------------

def _groups(word):
    """Grupos de vocales de la palabra: [(inicio, fin)] (aproximación a las sílabas)."""
    out, start = [], None
    for k, ch in enumerate(word + " "):
        if ch in VOWELS and start is None:
            start = k
        elif ch not in VOWELS and start is not None:
            out.append((start, k)); start = None
    return out


def _stress_penultimate(word):
    """Pone tilde en la sílaba penúltima de una palabra llana terminada en consonante (examen → exámenes)."""
    groups = _groups(word)
    if len(groups) < 2:
        return word
    a, b = groups[-2]
    chunk = word[a:b]
    accents = {"a": "á", "e": "é", "o": "ó", "i": "í", "u": "ú"}
    strong = [k for k, ch in enumerate(chunk) if ch in "aeo"]
    at = strong[0] if strong else len(chunk) - 1             # diptongo: la tilde va en la vocal fuerte
    return word[:a] + chunk[:at] + accents[chunk[at]] + chunk[at + 1:] + word[b:]


def plural(word):
    if word.endswith("z"):
        return word[:-1] + "ces"
    for tail in ("ón", "án", "én", "ín", "és", "ún"):
        if word.endswith(tail) and len(word) > 3:
            return word[:-2] + tail.translate(_ACCENT) + "es"
    if word[-1] in VOWELS:
        return word + "s"
    if word.endswith("s"):
        groups = _groups(word)
        last = word[groups[-1][0]:groups[-1][1]] if groups else ""
        if last and last[-1] in "áéíóú":                      # autobús → autobuses, país → países
            at = groups[-1][1] - 1
            hiatus = at > 0 and word[at - 1] in VOWELS            # país conserva la tilde; autobús la pierde
            return (word if hiatus else word[:at] + last[-1].translate(_ACCENT_ONE) + word[at + 1:]) + "es"
        return word + "es" if len(groups) <= 1 else word    # mes → meses, pero paraguas, crisis, lunes no cambian
    if word.endswith("n") and len(_groups(word)) >= 2 and not any(ch in "áéíóú" for ch in word):
        return _stress_penultimate(word) + "es"               # joven → jóvenes, origen → orígenes
    if word[-1] in "tcgbpkfm":                                # bit → bits, chalet → chalets, iceberg → icebergs
        return word + "s"
    return word + "es"


def feminine(word):
    if word.endswith("o"):
        return word[:-1] + "a"
    for tail in ("or", "ón", "án", "ín", "és", "ol"):  # -ol: gentilicios como español → española
        if word.endswith(tail):
            return word[:-len(tail)] + tail.translate(_ACCENT) + "a"
    return word


def _change(stem, change, preterite=False):
    """Cambio de raíz en la última vocal afectada: o→ue, e→ie, e→i (y o→u / e→i en el pasado de -ir)."""
    target, new = {"ue": ("o", "u" if preterite else "ue"), "ie": ("e", "i" if preterite else "ie"),
                   "i": ("e", "i")}[change]
    i = stem.rfind(target)
    return stem if i < 0 else stem[:i] + new + stem[i + 1:]


# Verbos en -iar que acentúan la i (los demás, como cambiar o estudiar, no).
STRESSED_IAR = frozenset("""enviar guiar confiar fiar variar criar liar vaciar espiar ampliar resfriar enfriar fotografiar
desafiar rociar expiar aliar contrariar estriar aviar ansiar autografiar cartografiar desvariar desviar chirriar averiar
desconfiar""".split())


MONOSYLLABIC_PRETERITE = frozenset("guiar criar fiar liar piar triar".split())


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
    if cls == "ar" and (inf in STRESSED_IAR or (stem.endswith("u") and not stem.endswith(("gu", "qu")))):
        # El acento cae en la i/u de la raíz: enviar → envía, evaluar → evalúa (pero cambiar → cambia).
        accented = stem[:-1] + ("í" if stem.endswith("i") else "ú")
        sub = accented
        pret = stem + ("o" if inf in MONOSYLLABIC_PRETERITE else "ó")      # guio, crio, fio: sin tilde
        return (accented + "a", accented + "an", sub + "e", sub + "en", pret, stem + "aron")
    if cls == "ar" and stem.endswith("gu"):                              # averiguar → averigüe
        return (stem + "a", stem + "an", stem[:-1] + "üe", stem[:-1] + "üen", stem + "ó", stem + "aron")
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
    if stem.endswith(("ñ", "ll")):                                      # bullir → bulló, tañer → tañó
        return (present + "e", present + "en", sub + "a", sub + "an", past + "ó", past + "eron")
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


IRREGULAR_PARTICIPLES = {
    "abrir": "abierto", "cubrir": "cubierto", "descubrir": "descubierto", "decir": "dicho", "predecir": "predicho",
    "contradecir": "contradicho", "escribir": "escrito", "describir": "descrito", "inscribir": "inscrito",
    "transcribir": "transcrito", "hacer": "hecho", "deshacer": "deshecho", "rehacer": "rehecho", "satisfacer": "satisfecho",
    "morir": "muerto", "poner": "puesto", "componer": "compuesto", "proponer": "propuesto", "suponer": "supuesto",
    "imponer": "impuesto", "exponer": "expuesto", "oponer": "opuesto", "reponer": "repuesto", "resolver": "resuelto",
    "disolver": "disuelto", "volver": "vuelto", "devolver": "devuelto", "envolver": "envuelto", "romper": "roto",
    "ver": "visto", "prever": "previsto", "freír": "frito", "imprimir": "impreso", "proveer": "provisto",
}
NO_DIMINUTIVE = frozenset("""día mano mapa planeta problema idioma sistema tema programa clima poema drama diploma cometa pijama
tranvía foto moto radio disco""".split())


def _derived(base):
    """Entradas que se deducen de las demás por reglas: diminutivos y participios. No se guardan en ningún archivo.

    - Diminutivo (`perro` → `perrito`): comparte el símbolo de su palabra, porque un perrito es un perro.
    - Participio (`leer` → `leído`): adjetivo con símbolo propio (`Leido`); no es lo mismo «leyó» que «está leído».
    Se omite toda forma que el diccionario ya conoce con esa categoría, para no crear ambigüedad nueva.
    """
    known = {}
    for e in base:
        try:
            for tag, values in e.forms().items():
                known.setdefault(tag.split("_")[0], set()).update(values)
        except LogosError:
            continue
    adj, noun = known.get("Adj", set()), known.get("N", set())
    out = []
    for e in base:
        opts = e.options()
        if e.category == "N" and e.feature in ("M", "F") and not opts.get("sin") and not opts.get("sentido"):
            w = e.lemma.casefold()
            if (w in NO_DIMINUTIVE or len(w) < 3 or not w.endswith(("o", "a")) or (w.endswith("o") != (e.feature == "M"))
                    or w[-2] in VOWELS or w.endswith(("ito", "ita", "illo", "illa"))):
                continue          # gimnasio y mosquito no hacen «gimnasiito» ni «mosquitito»
            stem = w[:-1]
            stem = stem[:-1] + "qu" if stem.endswith("c") else stem + "u" if stem.endswith("g") else stem[:-1] + "c" if stem.endswith("z") else stem
            dim = stem + ("ito" if e.feature == "M" else "ita")
            if dim not in noun and plural(dim) not in noun and all(ch.isalpha() for ch in dim):
                out.append(Entry(dim, "N", e.feature, f"sin={e.lemma.casefold()};dim={e.lemma.casefold()}", "auto"))
                noun.add(dim); noun.add(plural(dim))
        elif e.category == "V" and e.feature in ("T", "IT") and not opts.get("formas") or e.category == "V" and e.feature in ("T", "IT") and e.lemma in IRREGULAR_PARTICIPLES:
            inf = e.lemma.casefold()
            part = IRREGULAR_PARTICIPLES.get(inf)
            if part is None:
                stem, cls = inf[:-2], plain(inf[-2:])
                if cls == "ar":
                    part = stem + "ado"
                elif cls in ("er", "ir"):
                    part = stem + ("ído" if stem[-1:] in "aeo" and not stem.endswith(("gu", "qu")) else "ido")
                else:
                    continue
            forms = {part, part[:-1] + "a", plural(part), plural(part[:-1] + "a")}
            if forms & adj or not all(ch.isalpha() for ch in part):
                continue
            out.append(Entry(part, "ADJ", "-", f"part={inf}", "auto"))
            adj |= forms
    return out


@lru_cache(maxsize=1)
def entries():
    base = _read(BASE, "base") + _read(user_path(), "usuario")
    return tuple(base + _derived(base))


@lru_cache(maxsize=1)
def _tables():
    """(etiqueta → formas, (clase semántica, forma) → [(símbolo, glosa)] sin repetir símbolo)."""
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
                known = symbols.setdefault((kind, form), [])
                if all(s != e.symbol for s, _ in known):
                    known.append((e.symbol, e.gloss or e.lemma))
    return by_tag, symbols


def grammar_forms():
    return _tables()[0]


def symbol(kind, form):
    """Símbolo lógico de una forma (`kind`: N, Adj o V), o None si no está en el diccionario."""
    found = _tables()[1].get((kind, form))
    return found[0][0] if found else None


def senses(kind, form):
    """Todos los símbolos que puede tener una forma: más de uno si la palabra tiene varios sentidos."""
    return tuple(_tables()[1].get((kind, form), ()))


@lru_cache(maxsize=1)
def _index():
    """Para buscar sin recalcular: por entrada, sus formas ya normalizadas; y forma → entradas."""
    rows, by_form = [], {}
    for e in entries():
        try:
            forms = {f for values in e.forms().values() for f in values}
        except LogosError:
            forms = set()
        words = {e.lemma.casefold(), e.options().get("sin", ""), *forms} - {""}
        rows.append((e, tuple(sorted(plain(w) for w in words))))
        for w in {e.lemma.casefold(), *forms}:
            by_form.setdefault(w, []).append(e)
    return rows, by_form


def warm_up():
    """Construye de antemano todo lo que tarda la primera vez (el servidor lo llama al arrancar)."""
    from . import spanish_cyk
    _tables(); _index(); spanish_cyk.grammar(); spanish_cyk._automaton()


def reload():
    entries.cache_clear(); _tables.cache_clear(); _index.cache_clear()
    from . import spanish_cyk
    spanish_cyk.grammar.cache_clear(); spanish_cyk._automaton.cache_clear()


def find(word):
    """Entradas cuyo lema o alguna forma coincide con la palabra."""
    return list(_index()[1].get(word.casefold().strip(), ()))


def search(query="", category="", source="", limit=60, offset=0):
    q = plain(query.casefold().strip())
    hits = []
    for e, haystack in _index()[0]:
        if category and e.category != category:
            continue
        if source and e.source != source:
            continue
        if q and not any(h.startswith(q) for h in haystack):
            continue
        hits.append(e)
    hits.sort(key=lambda e: (plain(e.lemma.casefold()), e.category))
    return len(hits), hits[offset:offset + limit]


def counts():
    out = {c: 0 for c in CATEGORIES}
    user = auto = 0
    for e in entries():
        out[e.category] += 1
        user += e.source == "usuario"
        auto += e.source == "auto"
    return {"total": len(entries()), "user": user, "auto": auto, "by_category": out}


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
    for key in ("sin", "sentido"):
        value = entry.options().get(key, "")
        if value and not all(ch.isalpha() or ch == "_" for ch in value):
            raise LogosError("semantic", "invalid_lexicon", f"«{key}» debe ser una palabra")
    for values in entry.forms().values():      # lanza si no se puede flexionar
        for form in values:
            if not form or not all(ch.isalpha() for ch in form):
                raise LogosError("semantic", "invalid_lexicon", f"forma inválida: «{form}»")
    return entry


def add(lemma, category, feature, extra=""):
    """Guarda una palabra del usuario y recarga la gramática. Devuelve la entrada."""
    entry = _validate(lemma, category, feature, extra)
    key = (entry.lemma.casefold(), entry.category, entry.feature, entry.symbol)   # otro sentido sí es otra entrada
    if any((e.lemma.casefold(), e.category, e.feature, e.symbol) == key for e in entries()):
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
    warm_up()
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
    warm_up()
    return True
