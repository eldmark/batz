"""Servidor local sin dependencias para el evaluador MM3032."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

from .errors import LogosError, SCHEMA_VERSION
from .countermodels import CountermodelConfig, find_countermodel
from .interpretation import build_interpretation
from .project import evaluar, libres
from .symbols import Signature
from .spanish import translate_spanish
from .proof import SearchConfig, prove_text
from .proof_story import build_proof_narration
from .voice_input import VoiceInputError, availability, transcribe

WEB = Path(__file__).with_name("web")
MAX_BODY = 1_000_000


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


def handle_api(route, data):
    """Procesa una solicitud JSON sin depender del transporte HTTP."""
    if not isinstance(data, dict):
        raise LogosError("syntactic", "expected_formula", "la solicitud debe ser un objeto")
    if route == "/api/spanish":
        return {"schema_version": SCHEMA_VERSION, **translate_spanish(data.get("text")).to_dict()}
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
        result = prove_text(premises, conclusion, constants=constants,
                            config=SearchConfig(max_depth=6, max_nodes=20_000, timeout=3))
        if result.status == "invalid_input":
            return {"schema_version": SCHEMA_VERSION, "status": "invalid_input",
                    "errors": [result.diagnostic]}
        if result.status == "unknown":
            return {"schema_version": SCHEMA_VERSION, "status": "unknown",
                    "reason": result.reason, "nodes": result.nodes}
        return {"schema_version": SCHEMA_VERSION, "status": "proved",
                "certificate": result.certificate.to_dict(),
                "story": build_proof_narration(result.certificate).to_dict()}
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
                 "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                 "/story3d.js": ("story3d.js", "text/javascript; charset=utf-8"),
                 "/style.css": ("style.css", "text/css; charset=utf-8"),
                 "/vendor/three.module.js": ("vendor/three.module.js", "text/javascript; charset=utf-8"),
                 "/vendor/three.core.js": ("vendor/three.core.js", "text/javascript; charset=utf-8"),
                 "/vendor/LICENSE-three.txt": ("vendor/LICENSE-three.txt", "text/plain; charset=utf-8")}
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
        if route not in ("/api/free", "/api/validate", "/api/evaluate", "/api/countermodel", "/api/spanish", "/api/proof", "/api/voice/status", "/api/voice/transcribe"):
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
            self._json(200 if response["status"] in ("ok", "found", "unknown", "single", "ambiguous", "proved") else 400, response)
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
