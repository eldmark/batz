"""Servidor local sin dependencias para el evaluador MM3032."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

import re

from .errors import LogosError, SCHEMA_VERSION
from .countermodels import CountermodelConfig, find_consequence_countermodel, find_countermodel
from .interpretation import build_interpretation
from .project import evaluar, libres
from .symbols import Signature, check
from .parser import _Parser, parse
from .printer import to_string
from .transform import free_vars
from .modelfile import parse_model_file
from . import lexicon, notebook, practice, spanish_tagger as tagger
from .tree import semantic_tree, syntax_tree
from .symbols import parse_checked
from .propositional import atoms, is_propositional, valuation_model, valuations, value as prop_value
from .resolution import ResolutionConfig, resolve, _MATRIX as MATRIX
from .semantics import is_countermodel
from .spanish import translate_spanish
from .proof import SearchConfig, prove, verify
from .proof.kalmar import kalmar_prove
from .proof_story import build_proof_narration
from .voice_input import VoiceInputError, availability, transcribe

WEB = Path(__file__).with_name("web")
MAX_BODY = 1_000_000
PROOF_CONFIG = SearchConfig(max_depth=6, max_nodes=20_000, timeout=3)
KALMAR_ATOMS = 6       # el certificado de Kalmár crece como 2ⁿ: más letras, solo búsqueda
TRUTH_TABLE_ATOMS = 12  # 4096 filas: la tabla de verdad sigue siendo instantánea


def read_problem(premises, conclusion, constants):
    """Lee un problema del modo Demostrar: `(modo, premisas, conclusión, letras)`.

    Una minúscula suelta en posición de fórmula (`p → q`) solo puede ser una letra
    proposicional: si todas las fórmulas son proposicionales, el problema se decide completo
    (tabla de verdad y Kalmár). `letras` guarda cómo se escribió cada letra para mostrarla igual.
    """
    texts = [*premises, conclusion]
    try:
        parsed = [parse(text, constants) for text in texts]
    except LogosError as first_error:
        letters, parsed = {}, []
        try:
            for text in texts:
                reader = _Parser(text, (), propositional=True)
                parsed.append(reader.parse_all())
                for name, (original, span) in reader.letters.items():
                    if letters.setdefault(name, original) != original:
                        raise LogosError("semantic", "letter_collision",
                                         f"'{letters[name]}' y '{original}' se leerían como la misma letra '{name}'",
                                         span, text)
        except LogosError as exc:
            raise exc if exc.code == "letter_collision" else first_error
        if not all(is_propositional(f) for f in parsed):
            raise first_error
        return "propositional", parsed[:-1], parsed[-1], letters
    mode = "propositional" if all(is_propositional(f) for f in parsed) else "first_order"
    return mode, parsed[:-1], parsed[-1], {}


def _syntax_error(text, error):
    """El error más útil para una fórmula del modo Demostrar que no se lee en primer orden.

    Si se lee como fórmula proposicional, el problema es la mezcla con fórmulas de primer orden.
    Si tampoco, se informa el error que llega más lejos en el texto: quien escribe `p → ` está
    escribiendo una fórmula proposicional sin terminar, no un término mal puesto."""
    try:
        formula = parse(text, (), propositional=True)
    except LogosError as other:
        here = lambda e: e.span.start if e.span is not None else -1
        return (other if here(other) > here(error) else error).to_diagnostic()
    if is_propositional(formula):
        return LogosError("syntactic", "mixed_logic",
                          "Usa letras proposicionales, pero otras fórmulas son de primer orden: no se pueden mezclar.",
                          formula.span, text).to_diagnostic()
    return error.to_diagnostic()


def formula_text(letters):
    """Convierte fórmulas en texto con las letras proposicionales como las escribió el usuario."""
    if not letters:
        return to_string
    return lambda f: re.sub(r"[A-Za-z_][A-Za-z0-9_]*", lambda m: letters.get(m.group(0), m.group(0)), to_string(f))


def _contrast(engine_a, second, override=None):
    verdict, message = override or MATRIX[(engine_a, second.status)]
    return {"verdict": verdict, "message": message, "engine_b": second.to_dict()}


def _proved(cert, show, contrast, mode, method):
    story = build_proof_narration(cert, show).to_dict()
    return {"schema_version": SCHEMA_VERSION, "status": "proved", "mode": mode, "method": method,
            "certificate": cert.to_dict(), "fitch": story.pop("fitch"), "story": story, "contrast": contrast}


def _prove_propositional(ps, c, show, second):
    """Lógica proposicional: siempre hay veredicto dentro de los límites de letras."""
    names = set().union(*(atoms(f) for f in [*ps, c]))
    if len(names) > TRUTH_TABLE_ATOMS:
        return {"schema_version": SCHEMA_VERSION, "status": "unknown", "mode": "propositional",
                "reason": "too_many_atoms", "contrast": _contrast("unknown", second)}
    for v in valuations(names):
        if all(prop_value(p, v) for p in ps) and not prop_value(c, v):
            model = valuation_model(v)
            if not is_countermodel(model, ps, c):  # el evaluador de la Fase 2 lo confirma
                raise AssertionError("valuación no verificada")
            letter = lambda name: show(parse(name))
            return {"schema_version": SCHEMA_VERSION, "status": "refuted", "mode": "propositional",
                    "valuation": [[letter(n), v[n]] for n in sorted(names)],
                    "premises": [{"formula": show(p), "value": True} for p in ps],
                    "conclusion": {"formula": show(c), "value": False},
                    "contrast": _contrast("unknown", second)}
    result = prove(ps, c, PROOF_CONFIG)
    if result.status == "proved":
        return _proved(result.certificate, show, _contrast("proved", second), "propositional", "search")
    if len(names) > KALMAR_ATOMS:
        return {"schema_version": SCHEMA_VERSION, "status": "unknown", "mode": "propositional",
                "reason": "too_many_atoms_for_kalmar", "contrast": _contrast("unknown", second)}
    cert = kalmar_prove(ps, c, max_atoms=KALMAR_ATOMS)
    verify(cert)
    return _proved(cert, show, _contrast("proved", second), "propositional", "kalmar")


def _prove_first_order(ps, c, constants, show, second):
    result = prove(ps, c, PROOF_CONFIG)
    if result.status == "proved":
        return _proved(result.certificate, show, _contrast("proved", second), "first_order", "search")
    if second.status == "refuted":  # B la prueba: no tiene sentido buscar un contramodelo
        return {"schema_version": SCHEMA_VERSION, "status": "unknown", "mode": "first_order",
                "reason": result.reason, "nodes": result.nodes, "contrast": _contrast("unknown", second)}
    search = find_consequence_countermodel(ps, c, constants)
    if search.status == "found":
        return {"schema_version": SCHEMA_VERSION, "status": "refuted", "mode": "first_order",
                "countermodel": search.to_dict(), "contrast": _contrast("unknown", second)}
    return {"schema_version": SCHEMA_VERSION, "status": "unknown", "mode": "first_order",
            "reason": result.reason, "nodes": result.nodes, "search": search.to_dict(),
            "contrast": _contrast("unknown", second)}


def _signature(data):
    if not isinstance(data, dict):
        raise LogosError("semantic", "invalid_model", "la firma debe ser un objeto")
    constants = data.get("constants", [])
    functions = data.get("functions", {})
    predicates = data.get("predicates", {})
    if not isinstance(constants, list) or not all(isinstance(c, str) for c in constants):
        raise LogosError("semantic", "invalid_model", "las constantes deben ser una lista de nombres")
    if not isinstance(functions, dict) or not isinstance(predicates, dict):
        raise LogosError("semantic", "invalid_model", "funciones y predicados deben ser objetos")
    return Signature(constants=frozenset(constants), functions=functions, predicates=predicates)


def _lexicon_api(action, data):
    """Diccionario del español: buscar, proponer con el modelo, previsualizar, añadir y quitar."""
    text = lambda key, limit=60: (data.get(key) if isinstance(data.get(key), str) else "")[:limit]
    if action == "search":
        offset = data.get("offset") if type(data.get("offset")) is int and data.get("offset") >= 0 else 0
        total, hits = lexicon.search(text("query"), text("category", 4), text("source", 8), 60, offset)
        return {"total": total, "offset": offset, "counts": lexicon.counts(), "entries": [e.to_dict() for e in hits]}
    if action == "suggest":
        word = text("word").strip()
        if not word or not all(ch.isalpha() for ch in word):
            raise LogosError("semantic", "invalid_lexicon", "escribe una sola palabra, solo letras")
        found = [e.to_dict() for e in lexicon.find(word)]
        proposal = None
        if not found and tagger.available():
            tag, probability = tagger.probabilities([word], 0, frozenset())[0]
            kind, _, form = tag.partition("_")
            category = {"N": "N", "Adj": "ADJ", "NProp": "NP"}.get(kind, "V")
            feature = form[0] if category == "N" else form if category == "NP" else ("T" if "VT" in kind else "I") if category == "V" else "-"
            lemma = tagger.guess_predicate(word, tag)
            proposal = {"lemma": word if category == "NP" else lemma.lower(), "category": category, "feature": feature,
                        "probability": round(probability, 3), "label": tagger.TAG_NAMES[tag]}
        return {"word": word, "found": found, "proposal": proposal}
    fields = (text("lemma"), text("category", 4), text("feature", 4), text("extra", 200))
    if action == "preview":
        return {"entry": lexicon._validate(*fields).to_dict()}
    if action == "add":
        return {"entry": lexicon.add(*fields).to_dict(), "counts": lexicon.counts()}
    if action == "remove":
        return {"removed": lexicon.remove(fields[0], fields[1]), "counts": lexicon.counts()}
    raise LogosError("syntactic", "unexpected_token", "acción de diccionario desconocida")


def handle_api(route, data):
    """Procesa una solicitud JSON sin depender del transporte HTTP."""
    if not isinstance(data, dict):
        raise LogosError("syntactic", "expected_formula", "la solicitud debe ser un objeto")
    if route.startswith("/api/practice/"):
        return {"schema_version": SCHEMA_VERSION, "status": "ok", **practice.api(route.rsplit("/", 1)[1], data)}
    if route == "/api/spanish":
        return {"schema_version": SCHEMA_VERSION, **translate_spanish(data.get("text")).to_dict()}
    if route.startswith("/api/lexicon/"):
        return {"schema_version": SCHEMA_VERSION, "status": "ok", **_lexicon_api(route.rsplit("/", 1)[1], data)}
    if route.startswith("/api/notebook/"):
        return {"schema_version": SCHEMA_VERSION, "status": "ok", **notebook.api(route.rsplit("/", 1)[1], data)}
    if route == "/api/voice/status":
        return {"schema_version": SCHEMA_VERSION, "status": "ok", **availability()}
    if route == "/api/proof":
        premises, conclusion, constants = (data.get("premises"), data.get("conclusion"),
                                           data.get("constants", []))
        if (not isinstance(premises, list) or len(premises) > 8 or
            not all(isinstance(p, str) and len(p) <= 200 for p in premises) or
            not isinstance(conclusion, str) or len(conclusion) > 200 or
            not isinstance(constants, list) or not all(isinstance(c, str) for c in constants)):
            raise LogosError("syntactic", "expected_formula", "premisas, conclusión o constantes inválidas")
        try:
            mode, ps, c, letters = read_problem(premises, conclusion, constants)
            known = Signature()
            for f in [*ps, c]:
                known = check(f, known)  # la aridad debe ser coherente entre fórmulas
        except LogosError as exc:
            return {"schema_version": SCHEMA_VERSION, "status": "invalid_input", "errors": [exc.to_diagnostic()]}
        show = formula_text(letters)
        # Motor B: segunda opinión independiente. Nunca convierte un «unknown» en «proved».
        second = resolve(ps, c, ResolutionConfig(timeout=2))
        if mode == "propositional":
            return _prove_propositional(ps, c, show, second)
        return _prove_first_order(ps, c, constants, show, second)
    if route == "/api/parse":
        # Revisión sintáctica de varias fórmulas sin evaluarlas (modo de pruebas).
        formulas, constants = data.get("formulas"), data.get("constants", [])
        if (not isinstance(formulas, list) or len(formulas) > 12 or
            not all(isinstance(f, str) and len(f) <= 400 for f in formulas) or
            not isinstance(constants, list) or not all(isinstance(c, str) for c in constants)):
            raise LogosError("syntactic", "expected_formula", "lista de fórmulas inválida")
        if formulas:
            try:  # todas a la vez: si juntas son proposicionales, cada una se muestra como letra
                mode, ps, c, letters = read_problem(formulas[:-1], formulas[-1], constants)
                if mode == "propositional" and letters:
                    show = formula_text(letters)
                    return {"schema_version": SCHEMA_VERSION, "status": "ok", "mode": "propositional",
                            "results": [{"ok": True, "text": show(f), "free": [], "tree": syntax_tree(f, letters)} for f in [*ps, c]]}
            except LogosError:
                pass
        first_order = []
        for text in formulas:
            try:
                first_order.append(parse(text, constants))
            except LogosError:
                first_order.append(None)
        # Solo hay mezcla si alguna otra fórmula es de verdad de primer orden.
        mixed = any(f is not None and not is_propositional(f) for f in first_order)
        results, known = [], Signature()
        for text in formulas:
            try:
                f = parse(text, constants)
                known = check(f, known, source=text)  # la aridad debe ser coherente entre fórmulas
                results.append({"ok": True, "text": to_string(f), "free": sorted(free_vars(f)), "tree": syntax_tree(f)})
            except LogosError as exc:
                error = _syntax_error(text, exc)
                if error["code"] == "mixed_logic" and not mixed:
                    reader = _Parser(text, (), propositional=True)
                    f = reader.parse_all()
                    shown = formula_text({name: original for name, (original, _) in reader.letters.items()})
                    results.append({"ok": True, "text": shown(f), "free": [],
                                    "tree": syntax_tree(f, {n: o for n, (o, _) in reader.letters.items()})})
                else:
                    results.append({"ok": False, "error": error})
        mode = "first_order" if mixed else "propositional" if results and all(r["ok"] for r in results) else "first_order"
        return {"schema_version": SCHEMA_VERSION, "status": "ok", "mode": mode, "results": results}
    if route == "/api/load":
        package = parse_model_file(data.get("text"))
        sig = _signature(package["signature"])
        model = build_interpretation(sig, package["interpretation"])
        results = []
        for entry in package["formulas"][:200]:
            r = evaluar(sig, package["interpretation"], entry["formula"], entry["assignment"])
            row = {"formula": entry["formula"], "assignment": entry["assignment"], "line": entry["line"]}
            if r.status == "ok":
                row.update(status="ok", value=r.value, summary=r.explanation.summary)
                if "expected" in entry:
                    row.update(expected=entry["expected"], matches=entry["expected"] == r.value)
            else:
                row.update(status="invalid_input", error=r.errors[0])
            results.append(row)
        return {"schema_version": SCHEMA_VERSION, "status": "ok", "signature": package["signature"],
                "model": model.to_dict(), "results": results}
    sig = _signature(data.get("signature"))
    formula = data.get("formula")
    if route == "/api/free":
        if not isinstance(formula, str):
            raise LogosError("syntactic", "expected_formula", "la fórmula debe ser texto")
        return {"schema_version": SCHEMA_VERSION, "status": "ok", "variables": list(libres(formula, sig))}
    if route == "/api/validate":
        model = build_interpretation(sig, data.get("interpretation"))
        return {"schema_version": SCHEMA_VERSION, "status": "ok", "model": model.to_dict()}
    if route == "/api/evaluate":
        result = evaluar(sig, data.get("interpretation"), formula, data.get("assignment"))
        if result.status == "invalid_input":
            return {"schema_version": SCHEMA_VERSION, "status": "invalid_input", "errors": list(result.errors)}
        return {"schema_version": SCHEMA_VERSION, "status": "ok", "value": result.value,
                "explanation": result.explanation.to_dict(), "story": result.story.to_dict(),
                "tree": semantic_tree(result.trace), "syntax": syntax_tree(parse_checked(formula, sig, strict=True)),
                "model": result.model.to_dict()}
    if route == "/api/countermodel":
        max_size = data.get("max_size", 3)
        if type(max_size) is not int or not 1 <= max_size <= 3:
            raise LogosError("semantic", "invalid_model", "max_size debe estar entre 1 y 3")
        result = find_countermodel(sig, formula, CountermodelConfig(max_size=max_size))
        return {"schema_version": SCHEMA_VERSION, **result.to_dict()}
    raise LogosError("syntactic", "unexpected_token", "ruta desconocida")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # la demo no necesita bitácora de accesos en la terminal

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        files = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/practice.js": ("practice.js", "text/javascript; charset=utf-8"),
                 "/practice.css": ("practice.css", "text/css; charset=utf-8"),
                 "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                 "/story3d.js": ("story3d.js", "text/javascript; charset=utf-8"),
                 "/style.css": ("style.css", "text/css; charset=utf-8"),
                 "/features/explanation-player/index.js": ("features/explanation-player/index.js", "text/javascript; charset=utf-8"),
                 "/features/explanation-player/events.js": ("features/explanation-player/events.js", "text/javascript; charset=utf-8"),
                 "/features/explanation-player/fullscreen.js": ("features/explanation-player/fullscreen.js", "text/javascript; charset=utf-8"),
                 "/features/explanation-player/player.css": ("features/explanation-player/player.css", "text/css; charset=utf-8"),
                 "/features/evaluator/examples.js": ("features/evaluator/examples.js", "text/javascript; charset=utf-8"),
                 "/styles/evaluator.css": ("styles/evaluator.css", "text/css; charset=utf-8"),
                 "/styles/thread.css": ("styles/thread.css", "text/css; charset=utf-8"),
                 "/features/export/export.js": ("features/export/export.js", "text/javascript; charset=utf-8"),
                 "/styles/motion.css": ("styles/motion.css", "text/css; charset=utf-8"),
                 "/styles/shell.css": ("styles/shell.css", "text/css; charset=utf-8"),
                 "/styles/dictionary.css": ("styles/dictionary.css", "text/css; charset=utf-8"),
                 "/app/navigation.js": ("app/navigation.js", "text/javascript; charset=utf-8"),
                 "/features/home/home.js": ("features/home/home.js", "text/javascript; charset=utf-8"),
                 "/features/home/motion.js": ("features/home/motion.js", "text/javascript; charset=utf-8"),
                 "/styles/responsive.css": ("styles/responsive.css", "text/css; charset=utf-8"),
                 "/styles/home.css": ("styles/home.css", "text/css; charset=utf-8"),
                 "/styles/learn.css": ("styles/learn.css", "text/css; charset=utf-8"),
                 "/features/learn/learn.js": ("features/learn/learn.js", "text/javascript; charset=utf-8"),
                 "/features/learn/data.js": ("features/learn/data.js", "text/javascript; charset=utf-8"),
                 "/features/learn/deck.js": ("features/learn/deck.js", "text/javascript; charset=utf-8"),
                 "/img/godel.jpg": ("img/godel.jpg", "image/jpeg"),
                 "/img/turing.jpg": ("img/turing.jpg", "image/jpeg"),
                 "/img/people/aristoteles.jpg": ("img/people/aristoteles.jpg", "image/jpeg"),
                 "/img/people/leibniz.jpg": ("img/people/leibniz.jpg", "image/jpeg"),
                 "/img/people/boole.jpg": ("img/people/boole.jpg", "image/jpeg"),
                 "/img/people/frege.jpg": ("img/people/frege.jpg", "image/jpeg"),
                 "/img/people/peirce.jpg": ("img/people/peirce.jpg", "image/jpeg"),
                 "/img/people/schroder.jpg": ("img/people/schroder.jpg", "image/jpeg"),
                 "/img/people/peano.jpg": ("img/people/peano.jpg", "image/jpeg"),
                 "/img/people/russell.jpg": ("img/people/russell.jpg", "image/jpeg"),
                 "/img/people/whitehead.jpg": ("img/people/whitehead.jpg", "image/jpeg"),
                 "/img/people/lowenheim.jpg": ("img/people/lowenheim.jpg", "image/jpeg"),
                 "/img/people/skolem.jpg": ("img/people/skolem.jpg", "image/jpeg"),
                 "/img/people/hilbert.jpg": ("img/people/hilbert.jpg", "image/jpeg"),
                 "/img/people/ackermann.jpg": ("img/people/ackermann.jpg", "image/jpeg"),
                 "/img/people/bernays.jpg": ("img/people/bernays.jpg", "image/jpeg"),
                 "/img/people/godel.jpg": ("img/people/godel.jpg", "image/jpeg"),
                 "/img/people/turing.jpg": ("img/people/turing.jpg", "image/jpeg"),
                 "/img/people/tarski.jpg": ("img/people/tarski.jpg", "image/jpeg"),
                 "/img/people/gentzen.jpg": ("img/people/gentzen.jpg", "image/jpeg"),
                 "/img/people/robinson.jpg": ("img/people/robinson.jpg", "image/jpeg"),
                 "/features/people/people.js": ("features/people/people.js", "text/javascript; charset=utf-8"),
                 "/features/people/bios.js": ("features/people/bios.js", "text/javascript; charset=utf-8"),
                 "/features/people/person.js": ("features/people/person.js", "text/javascript; charset=utf-8"),
                 "/features/home/carousel.js": ("features/home/carousel.js", "text/javascript; charset=utf-8"),
                 "/styles/people.css": ("styles/people.css", "text/css; charset=utf-8"),
                 "/styles/tour.css": ("styles/tour.css", "text/css; charset=utf-8"),
                 "/features/tour/tour.js": ("features/tour/tour.js", "text/javascript; charset=utf-8"),
                 "/tokens.css": ("tokens.css", "text/css; charset=utf-8"),
                 "/vendor/three.module.js": ("vendor/three.module.js", "text/javascript; charset=utf-8"),
                 "/vendor/three.core.js": ("vendor/three.core.js", "text/javascript; charset=utf-8"),
                 "/vendor/GLTFLoader.js": ("vendor/GLTFLoader.js", "text/javascript; charset=utf-8"),
                 "/vendor/BufferGeometryUtils.js": ("vendor/BufferGeometryUtils.js", "text/javascript; charset=utf-8"),
                 "/vendor/SkeletonUtils.js": ("vendor/SkeletonUtils.js", "text/javascript; charset=utf-8"),
                 "/avatar/logos.glb": ("avatar/logos.glb", "model/gltf-binary"),
                 "/favicon.svg": ("favicon.svg", "image/svg+xml"),
                 "/vendor/LICENSE-three.txt": ("vendor/LICENSE-three.txt", "text/plain; charset=utf-8")}
        if path == "/favicon.ico":  # los navegadores lo piden aunque la página declare el SVG
            self.send_response(204)
            self.end_headers()
            return
        font = Path(path).name  # solo el nombre: sin rutas relativas
        if path == f"/fonts/{font}" and font.endswith(".woff2") and (WEB / "fonts" / font).is_file():
            files[path] = (f"fonts/{font}", "font/woff2")
        if path not in files:
            self.send_error(404)
            return
        name, mime = files[path]
        body = (WEB / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        route = urlsplit(self.path).path
        if route not in ("/api/free", "/api/validate", "/api/evaluate", "/api/countermodel", "/api/spanish", "/api/proof", "/api/parse", "/api/load", "/api/lexicon/search", "/api/lexicon/suggest", "/api/lexicon/preview", "/api/lexicon/add", "/api/lexicon/remove", "/api/voice/status", "/api/voice/transcribe") and not route.startswith(("/api/notebook/", "/api/practice/")):
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            limit = 5_000_000 if route == "/api/voice/transcribe" else MAX_BODY
            if not 0 < size <= limit:
                self._json(413, {"status": "invalid_input", "errors": [{"message": "solicitud demasiado grande o vacía"}]})
                return
            if route == "/api/voice/transcribe":
                if not self.headers.get("Content-Type", "").startswith("audio/webm"):
                    self._json(415, {"status": "invalid_input", "errors": [{"code": "invalid_audio", "message": "Se espera audio/webm."}]})
                    return
                response = {"schema_version": SCHEMA_VERSION, "status": "ok",
                            "text": transcribe(self.rfile.read(size)), "confirmed": False}
            else:
                data = json.loads(self.rfile.read(size))
                response = handle_api(route, data)
            self._json(200 if response["status"] in ("ok", "found", "unknown", "single", "ambiguous", "proved", "refuted") else 400, response)
        except VoiceInputError as exc:
            self._json(503 if exc.code == "voice_unavailable" else 400,
                       {"schema_version": SCHEMA_VERSION, "status": "invalid_input",
                        "errors": [{"code": exc.code, "message": str(exc)}]})
        except (json.JSONDecodeError, LogosError, TypeError, ValueError) as exc:
            diagnostic = exc.to_diagnostic() if isinstance(exc, LogosError) else {
                "schema_version": SCHEMA_VERSION, "status": "invalid_input", "stage": "syntactic",
                "code": "unexpected_token", "message": "solicitud JSON inválida", "span": None}
            self._json(400, {"schema_version": SCHEMA_VERSION, "status": "invalid_input", "errors": [diagnostic]})


def main(argv=None):
    parser = argparse.ArgumentParser(description="Interfaz local de LOGOS MM3032")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="no abrir el navegador")
    parser.add_argument("--host", default="127.0.0.1",
                        help="interfaz de escucha; solo Docker necesita 0.0.0.0")
    args = parser.parse_args(argv)
    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError:  # puerto ocupado: usar uno libre en vez de fallar en la demo
        server = ThreadingHTTPServer((args.host, 0), Handler)
    lexicon.warm_up()          # la primera frase o búsqueda no debe pagar la carga del diccionario
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"LOGOS disponible en {url}  (Ctrl+C para salir)", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
