"""Cuadernos: fuentes en español, premisas con cita y preguntas con prueba o contramodelo.

Un cuaderno guarda textos («fuentes»). Cada fuente se parte en oraciones y cada oración pasa
por el traductor de español controlado (`spanish.py`):

- una sola lectura y ninguna palabra supuesta → es premisa;
- varias lecturas, o palabras que el etiquetador tuvo que suponer → espera a que la persona
  elija; mientras tanto no se usa (nunca se elige una lectura en silencio);
- fuera de la gramática → queda marcada con el motivo y no se usa.

Una pregunta se traduce igual y se contesta solo con las premisas de las fuentes activas:

    follows      hay prueba verificada de la pregunta
    contradicts  hay prueba verificada de su negación
    undecided    ni ella ni su negación se siguen (modelo verificado o resolución saturada)
    not_follows  no se sigue; de su negación no se pudo decir nada
    unknown      no se decidió dentro de los límites

Cada premisa que usa una prueba lleva la cita de su oración (fuente y posición). En disco solo
se guardan los textos y las lecturas elegidas: el análisis y las respuestas se recalculan, así
que lo que se muestra siempre viene del núcleo verificado y del diccionario actual.

Los archivos viven en `datos/cuadernos/` (o en la carpeta de `BATZ_NOTEBOOKS`).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

from .ast import Not
from .countermodels import ConsequenceSearch, consequence_signature
from .errors import BatzError
from .model import FiniteModel
from .modelfinder import find_model
from .printer import to_string
from .proof import SearchConfig, prove
from .proof_story import build_proof_narration
from .resolution import ResolutionConfig, resolve, _MATRIX as MATRIX
from .semantics import is_countermodel
from .spanish import translate_spanish
from .symbols import Signature, check

VERSION = 1
MAX_NOTEBOOKS = 60
MAX_SOURCES = 20
MAX_TEXT = 20_000        # caracteres por fuente
MAX_SENTENCES = 150      # oraciones analizadas por fuente
MAX_PREMISES = 80        # premisas distintas por pregunta
MAX_TITLE = 80
MAX_QUESTION = 300
MAX_CHAT = 40
PROOF_CONFIG = SearchConfig(max_depth=6, max_nodes=20_000, timeout=3)
_ID = re.compile(r"c[0-9a-f]{12}")
_LOCK = threading.RLock()   # el traductor usa estado global y los archivos se reescriben enteros


def _bad(message, code="invalid_notebook"):
    return BatzError("semantic", code, message)


# ── Archivos ──

def folder():
    custom = os.environ.get("BATZ_NOTEBOOKS")
    return Path(custom) if custom else Path(__file__).resolve().parents[2] / "datos" / "cuadernos"


def _path(notebook_id):
    if not isinstance(notebook_id, str) or not _ID.fullmatch(notebook_id):
        raise _bad("identificador de cuaderno inválido")
    return folder() / f"{notebook_id}.json"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(notebook_id):
    path = _path(notebook_id)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise _bad("Ese cuaderno ya no existe.", "unknown_notebook") from None
    except (OSError, json.JSONDecodeError):
        raise _bad("El archivo del cuaderno está dañado.") from None
    return _clean(raw, notebook_id)


def _save(raw):
    raw["updated"] = _now()
    path = _path(raw["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    temp.replace(path)   # nunca queda un archivo a medio escribir
    return raw


def _title(value, default):
    text = " ".join(value.split()) if isinstance(value, str) else ""
    return text[:MAX_TITLE] or default


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise _bad("La fuente no tiene texto.")
    if len(value) > MAX_TEXT:
        raise _bad(f"La fuente pasa de {MAX_TEXT} caracteres: pártela en varias.")
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _clean(raw, notebook_id):
    """Un cuaderno leído de disco o importado, reducido a lo que este módulo entiende."""
    if not isinstance(raw, dict) or not isinstance(raw.get("sources", []), list):
        raise _bad("El archivo no es un cuaderno de Bat’z.")
    sources, seen = [], set()
    for n, item in enumerate(raw.get("sources", [])[:MAX_SOURCES], 1):
        if not isinstance(item, dict):
            raise _bad("El archivo no es un cuaderno de Bat’z.")
        source_id = item.get("id")
        if not isinstance(source_id, str) or not re.fullmatch(r"f[1-9]\d{0,5}", source_id) or source_id in seen:
            source_id = next(f"f{k}" for k in range(n, n + MAX_SOURCES + 1) if f"f{k}" not in seen)
        seen.add(source_id)
        choices = item.get("choices") if isinstance(item.get("choices"), dict) else {}
        sources.append({"id": source_id, "title": _title(item.get("title"), f"Fuente {n}"), "text": _text(item.get("text")),
                        "enabled": item.get("enabled") is not False,
                        "choices": {k: v for k, v in choices.items() if isinstance(k, str) and isinstance(v, str)}})
    chat = []
    for turn in raw.get("chat", []) if isinstance(raw.get("chat"), list) else []:
        if isinstance(turn, dict) and isinstance(turn.get("question"), str) and isinstance(turn.get("answer"), str):
            chat.append({"question": turn["question"][:MAX_QUESTION],
                         "formula": turn["formula"] if isinstance(turn.get("formula"), str) else None,
                         "answer": turn["answer"][:20], "at": turn["at"] if isinstance(turn.get("at"), str) else ""})
    chat = chat[-MAX_CHAT:]
    stamp = lambda key: raw[key] if isinstance(raw.get(key), str) else _now()
    return {"version": VERSION, "id": notebook_id, "title": _title(raw.get("title"), "Cuaderno sin título"),
            "created": stamp("created"), "updated": stamp("updated"), "sources": sources, "chat": chat}


# ── Oraciones y premisas ──

_BULLET = re.compile(r"\s*(?:[-•*–—]|\d{1,3}[.)]|[A-Za-z]\))\s+")
_PIECE = re.compile(r"[^.;!?]+[.;!?]*")


def split_sentences(text):
    """Tramos `(inicio, fin)` de cada oración: una por punto, punto y coma, signo de cierre o línea."""
    spans, offset = [], 0
    for line in text.splitlines(keepends=True):
        bullet = _BULLET.match(line)
        for piece in _PIECE.finditer(line, bullet.end() if bullet else 0):
            raw = piece.group()
            if any(ch.isalpha() for ch in raw):
                start = offset + piece.start() + len(raw) - len(raw.lstrip())
                spans.append((start, offset + piece.start() + len(raw.rstrip())))
        offset += len(line)
    return spans


@dataclass
class Sentence:
    index: int
    span: tuple
    text: str
    readings: tuple = ()        # SpanishReading
    assumptions: tuple = ()     # palabras fuera del léxico y la categoría supuesta
    error: dict | None = None
    chosen: object = None       # la lectura que se usa como premisa

    @property
    def needs_choice(self):
        return len(self.readings) > 1 or bool(self.assumptions)

    @property
    def status(self):
        return "rejected" if self.error else "premise" if self.chosen else "choose"

    def to_dict(self):
        data = {"i": self.index, "span": list(self.span), "status": self.status,
                "formula": self.chosen.text if self.chosen else None}
        if self.needs_choice:
            data["readings"] = [{"formula": r.text, "note": r.note} for r in self.readings]
            data["assumptions"] = list(self.assumptions)
        if self.error:
            data["error"] = self.error
        return data


def _statement(text):
    """La oración sin el punto final: el traductor recibe solo la afirmación."""
    return text.rstrip(" \t.;!")


def _analyze(index, span, text, choices):
    sentence = Sentence(index, span, text)
    if "?" in text or "¿" in text:
        sentence.error = {"message": "Es una pregunta: no afirma nada, así que no se usa como premisa.", "span": None}
        return sentence
    try:
        result = translate_spanish(_statement(text))
    except BatzError as exc:
        where = None if exc.span is None else [span[0] + exc.span.start, span[0] + exc.span.end]
        sentence.error = {"message": exc.message, "span": where}
        if where and exc.message.startswith("Palabra fuera del léxico"):
            sentence.error["word"] = text[exc.span.start:exc.span.end]
        return sentence
    sentence.readings, sentence.assumptions = result.readings, result.assumptions
    if sentence.needs_choice:
        wanted = choices.get(_statement(text))
        sentence.chosen = next((r for r in result.readings if r.text == wanted), None)
    else:
        sentence.chosen = result.readings[0]
    return sentence


def analyze(source):
    """Las oraciones de una fuente con sus lecturas; las primeras `MAX_SENTENCES`."""
    text = source["text"]
    return [_analyze(i, span, text[span[0]:span[1]], source["choices"])
            for i, span in enumerate(split_sentences(text)[:MAX_SENTENCES])]


@dataclass
class Premise:
    formula: object
    text: str
    cites: list   # [(fuente, oración)] que dicen exactamente esto


def _premises(raw, analysis):
    """Premisas distintas de las fuentes activas, con sus citas, y las constantes que usan."""
    by_text, constants, known = {}, set(), Signature()
    for source in raw["sources"]:
        if not source["enabled"]:
            continue
        for sentence in analysis[source["id"]]:
            reading = sentence.chosen
            if reading is None:
                continue
            if reading.text not in by_text:
                if len(by_text) >= MAX_PREMISES:
                    raise _bad(f"Hay más de {MAX_PREMISES} premisas activas: desactiva alguna fuente.")
                try:
                    known = check(reading.formula, known)   # la aridad debe ser coherente entre oraciones
                except BatzError as exc:
                    raise _bad(f"«{sentence.text}» ({source['title']}) no encaja con las demás premisas: {exc.message}") from None
                by_text[reading.text] = Premise(reading.formula, reading.text, [])
                constants |= set(reading.signature.constants)
            by_text[reading.text].cites.append((source, sentence))
    return list(by_text.values()), constants, known


def _counts(sentences):
    count = lambda status: sum(1 for s in sentences if s.status == status)
    return {"premises": count("premise"), "choose": count("choose"), "rejected": count("rejected")}


def _view(raw):
    analysis = {source["id"]: analyze(source) for source in raw["sources"]}
    sources, symbols = [], Signature()
    for source in raw["sources"]:
        sentences = analysis[source["id"]]
        for sentence in sentences:
            if sentence.chosen and source["enabled"]:
                try:
                    symbols = check(sentence.chosen.formula, symbols)
                except BatzError:
                    pass   # el choque de aridad se informa al preguntar, con la oración que lo causa
        sources.append({"id": source["id"], "title": source["title"], "enabled": source["enabled"], "text": source["text"],
                        "sentences": [s.to_dict() for s in sentences], "counts": _counts(sentences),
                        "truncated": len(split_sentences(source["text"])) > MAX_SENTENCES})
    return {"id": raw["id"], "title": raw["title"], "created": raw["created"], "updated": raw["updated"],
            "sources": sources, "chat": raw["chat"],
            "symbols": {"constants": sorted(symbols.constants), "predicates": dict(sorted(symbols.predicates.items()))}}


# ── Operaciones sobre cuadernos ──

def list_notebooks():
    items = []
    for path in sorted(folder().glob("c*.json")):
        try:
            raw = _load(path.stem)
        except BatzError:
            continue   # un archivo ajeno o dañado no impide ver los demás
        items.append({"id": raw["id"], "title": raw["title"], "updated": raw["updated"], "sources": len(raw["sources"])})
    return sorted(items, key=lambda item: item["updated"], reverse=True)


def create(title=None, sources=(), chat=()):
    if len(list_notebooks()) >= MAX_NOTEBOOKS:
        raise _bad(f"Ya hay {MAX_NOTEBOOKS} cuadernos: borra alguno.")
    raw = _clean({"title": title, "sources": list(sources), "chat": list(chat)}, "c" + secrets.token_hex(6))
    return _save(raw)


def _source(raw, source_id):
    for source in raw["sources"]:
        if source["id"] == source_id:
            return source
    raise _bad("Esa fuente ya no está en el cuaderno.", "unknown_source")


def add_source(raw, title, text):
    if len(raw["sources"]) >= MAX_SOURCES:
        raise _bad(f"Un cuaderno admite hasta {MAX_SOURCES} fuentes.")
    text = _text(text)
    if not split_sentences(text):
        raise _bad("La fuente no tiene ninguna oración.")
    number = 1 + max((int(s["id"][1:]) for s in raw["sources"]), default=0)
    raw["sources"].append({"id": f"f{number}", "title": _title(title, f"Fuente {number}"), "text": text,
                           "enabled": True, "choices": {}})


def choose(raw, source_id, index, formula):
    """Fija la lectura de una oración ambigua; `formula=None` la deja sin elegir."""
    source = _source(raw, source_id)
    sentences = analyze(source)
    if type(index) is not int or not 0 <= index < len(sentences) or not sentences[index].needs_choice:
        raise _bad("Esa oración no tiene lecturas para elegir.")
    key = _statement(sentences[index].text)
    if formula is None:
        source["choices"].pop(key, None)
    elif any(r.text == formula for r in sentences[index].readings):
        source["choices"][key] = formula
    else:
        raise _bad("Esa lectura ya no está entre las de la oración.")


# ── Preguntas ──

_LEAD = re.compile(r"^[\s¿¡]*(?:(?:se sigue|se deduce|se concluye)(?: de (?:las|mis) fuentes)? que|"
                   r"es (?:verdad|cierto) que|entonces|por (?:lo )?tanto)[\s,]+", re.IGNORECASE)


def question_statement(question):
    """«¿Se sigue que Juan aprueba?» → «Juan aprueba»: la afirmación que se pone a prueba."""
    text = question.strip().strip("¿?¡!. \t")
    stripped = _LEAD.sub("", text)
    return stripped[:1].upper() + stripped[1:] if stripped != text else text


def _names(formula):
    sig = check(formula)
    return set(sig.constants) | set(sig.predicates)


def _related(premises, goal):
    """Premisas unidas a la pregunta por símbolos compartidos, directa o indirectamente."""
    reach, names, chosen = _names(goal), [_names(p.formula) for p in premises], set()
    grew = True
    while grew:
        grew = False
        for i, own in enumerate(names):
            if i not in chosen and (own & reach or not own):   # sin símbolos (solo igualdad): habla de todo
                chosen.add(i); reach |= own; grew = True
    return [p for i, p in enumerate(premises) if i in chosen]


def _refuted(premises, goal, timeout):
    return resolve([p.formula for p in premises], goal, ResolutionConfig(timeout=timeout)).status == "refuted"


def _core(premises, goal, budget=1.5):
    """Quita premisas mientras la resolución siga derivando la meta: deja las que hacen falta."""
    keep, at, end = list(premises), 0, monotonic() + budget
    while at < len(keep) and monotonic() < end:
        trial = keep[:at] + keep[at + 1:]
        if _refuted(trial, goal, 0.25):
            keep = trial
        else:
            at += 1
    return keep


def _prove(premises, goal):
    """Busca una prueba de `goal`. Devuelve `(certificado, premisas usadas, resultado de resolución)`.

    La resolución solo orienta: descarta rápido lo que no se sigue y señala qué premisas hacen
    falta. Que algo «se sigue» lo afirma únicamente un certificado aceptado por el verificador.
    """
    second = resolve([p.formula for p in premises], goal, ResolutionConfig(timeout=2))
    if second.status == "saturated":
        return None, [], second
    pools = []
    if second.status == "refuted":
        related = _related(premises, goal)
        pools.append(_core(related if _refuted(related, goal, 1) else premises, goal))
    else:
        pools.append(_related(premises, goal))
    pools.append(premises)
    tried = []
    for pool in pools:
        if pool in tried:
            continue
        tried.append(pool)
        result = prove([p.formula for p in pool], goal, PROOF_CONFIG)
        if result.status == "proved":
            return result.certificate, pool, second
    return None, [], second


def _proof_view(certificate, pool, goal):
    """Derivación Fitch con la cita de cada premisa, las premisas citadas y el contraste con resolución."""
    story = build_proof_narration(certificate).to_dict()
    fitch = story.pop("fitch")
    used = {line["formula"] for line in fitch if line["rule"] == "premise" and line["steps"]}
    if len(used) < len(pool):   # sobra alguna: se repite con lo justo para no listar premisas que no se usan
        again = prove([p.formula for p in pool if p.text in used], goal, PROOF_CONFIG)
        if again.status == "proved":
            pool = [p for p in pool if p.text in used]
            story = build_proof_narration(again.certificate).to_dict()
            fitch = story.pop("fitch")
    number = {premise.text: n for n, premise in enumerate(pool, 1)}
    for line in fitch:
        if line["rule"] == "premise" and line["formula"] in number:
            line["cite"] = number[line["formula"]]
    cited = [{"n": number[p.text], "formula": p.text, "cites": [_cite(source, sentence) for source, sentence in p.cites]}
             for p in pool]
    second = resolve([p.formula for p in pool], goal, ResolutionConfig(timeout=2))
    verdict, message = MATRIX[("proved", second.status)]
    return cited, {"goal": to_string(goal), "fitch": fitch, "story": story,
                   "contrast": {"verdict": verdict, "message": message, "engine_b": second.to_dict()}}


def _named(model):
    """El mismo modelo con cada individuo llamado como el nombre que lo denota: «Aprobar = {juan}» se lee solo.

    Los individuos sin nombre quedan numerados; si dos nombres coinciden, se llama «ana = luis».
    """
    names = {}
    for constant, value in sorted(model.constants.items()):
        names.setdefault(value, []).append(constant)
    label, spare = {}, 0
    for element in model.domain:
        if element in names:
            label[element] = " = ".join(names[element])
        else:
            spare += 1
            label[element] = spare
    return FiniteModel([label[e] for e in model.domain], {c: label[v] for c, v in model.constants.items()}, {},
                       {name: (r.arity, [tuple(label[e] for e in t) for t in r.tuples]) for name, r in model.predicates.items()})


def _model_view(premises, conclusion, constants, timeout=2.0):
    """Un modelo verificado de las premisas donde `conclusion` es falsa, con el formato de `/api/proof`."""
    formulas = [p.formula for p in premises]
    model = find_model([*formulas, Not(conclusion)], constants, timeout=timeout)
    if model is None:
        return None
    model = _named(model)
    if not is_countermodel(model, formulas, conclusion):
        raise AssertionError("el modelo renombrado dejó de refutar la consecuencia")
    sig = consequence_signature([*formulas, conclusion], constants)
    return ConsequenceSearch("found", 0, (), None, model, {}, sig, tuple(formulas), conclusion).to_dict()


def _cite(source, sentence):
    return {"source": source["id"], "title": source["title"], "sentence": sentence.index, "text": sentence.text}


def ask(raw, question, formula=None):
    """Contesta una pregunta con las premisas de las fuentes activas. No modifica el cuaderno."""
    if not isinstance(question, str) or not question.strip() or len(question) > MAX_QUESTION:
        raise _bad("Escribe una pregunta corta.")
    statement = question_statement(question)
    result = translate_spanish(statement)
    answer = {"question": question.strip(), "statement": statement}
    reading = result.readings[0]
    if len(result.readings) > 1 or result.assumptions:
        reading = next((r for r in result.readings if r.text == formula), None)
        if reading is None:
            return {**answer, "answer": "choose", "assumptions": list(result.assumptions),
                    "readings": [{"formula": r.text, "note": r.note} for r in result.readings]}
    goal = reading.formula
    analysis = {source["id"]: analyze(source) for source in raw["sources"]}
    premises, constants, known = _premises(raw, analysis)
    active = [s for source in raw["sources"] if source["enabled"] for s in analysis[source["id"]]]
    answer.update({"conclusion": {"formula": reading.text, "note": reading.note},
                   "premise_count": len(premises), "counts": _counts(active),
                   "source_count": sum(1 for source in raw["sources"] if source["enabled"])})
    if not premises:
        return {**answer, "answer": "empty"}
    try:
        check(goal, known)
    except BatzError as exc:
        raise _bad(f"La pregunta no encaja con las premisas: {exc.message}") from None
    constants |= set(reading.signature.constants)
    mentioned = set().union(*(_names(p.formula) for p in premises))
    answer["new_symbols"] = sorted(_names(goal) - mentioned)
    for target, kind in ((goal, "follows"), (Not(goal), "contradicts")):
        certificate, pool, second = _prove(premises, target)
        if certificate is not None:
            cited, proof = _proof_view(certificate, pool, target)
            answer.update({"answer": kind, "proof": proof, "cited": cited})
            # Si la resolución también deriva lo contrario, las fuentes se contradicen entre sí.
            other = Not(goal) if kind == "follows" else goal
            answer["inconsistent"] = _refuted(premises, other, 1)
            return answer
        answer.setdefault("engine_b", {})[kind] = second.status
    # Sin prueba de ninguna de las dos: se busca un modelo de cada lado.
    countermodel = _model_view(premises, goal, constants)
    witness = _model_view(premises, Not(goal), constants)
    engine = answer["engine_b"]
    not_follows = countermodel is not None or engine["follows"] == "saturated"
    not_refuted = witness is not None or engine["contradicts"] == "saturated"
    answer.update({"answer": "undecided" if not_follows and not_refuted else "not_follows" if not_follows else "unknown",
                   "countermodel": countermodel, "witness": witness})
    return answer


# ── Interfaz para el servidor ──

def _string(data, key, limit):
    value = data.get(key)
    return value[:limit] if isinstance(value, str) else None


def api(action, data):
    """Una acción de `/api/notebook/<acción>`; devuelve un diccionario listo para JSON."""
    with _LOCK:
        if action == "list":
            return {"notebooks": list_notebooks()}
        if action == "create":
            return {"notebook": _view(create(data.get("title")))}
        if action == "import":
            package = data.get("notebook")
            if not isinstance(package, dict):
                raise _bad("El archivo no es un cuaderno de Bat’z.")
            raw = create(package.get("title"), package.get("sources") or (), package.get("chat") or ())
            return {"notebook": _view(raw)}
        raw = _load(data.get("id"))
        if action == "get":
            return {"notebook": _view(raw)}
        if action == "export":
            return {"notebook": {key: raw[key] for key in ("version", "title", "created", "sources", "chat")}}
        if action == "delete":
            _path(raw["id"]).unlink(missing_ok=True)
            return {"notebooks": list_notebooks()}
        if action == "ask":
            result = ask(raw, data.get("question"), _string(data, "formula", 2000))
            if data.get("log") is not False and result["answer"] not in ("choose", "empty"):
                turn = {"question": result["question"], "formula": result["conclusion"]["formula"],
                        "answer": result["answer"], "at": _now()}
                same = lambda old: (old["question"], old["formula"]) == (turn["question"], turn["formula"])
                raw["chat"] = [*(old for old in raw["chat"] if not same(old)), turn][-MAX_CHAT:]
                _save(raw)
            return result
        if action == "rename":
            raw["title"] = _title(data.get("title"), raw["title"])
        elif action == "source-add":
            add_source(raw, data.get("title"), data.get("text"))
        elif action == "source-remove":
            raw["sources"].remove(_source(raw, data.get("source")))
        elif action == "source-toggle":
            _source(raw, data.get("source"))["enabled"] = data.get("enabled") is not False
        elif action == "choose":
            choose(raw, data.get("source"), data.get("sentence"), _string(data, "formula", 2000))
        elif action == "clear-chat":
            raw["chat"] = []
        else:
            raise BatzError("syntactic", "unexpected_token", "acción de cuaderno desconocida")
        if action in ("source-add", "source-remove", "source-toggle", "choose"):
            for turn in raw["chat"]:   # cambiaron las premisas: los veredictos guardados ya no valen
                turn["answer"] = ""
        return {"notebook": _view(_save(raw))}
