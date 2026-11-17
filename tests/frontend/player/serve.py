"""Servidor exclusivo de la demo/pruebas. No modifica Handler ni sirve datos personales."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
WEB = HERE.parents[2] / "src/logos/web"


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path in ("/", "/preview.html"):
            target = HERE / "preview.html"
        elif path in ("/fixtures.json", "/preview.js"):
            target = HERE / path.lstrip("/")
        else:
            target = (WEB / path.lstrip("/")).resolve()
            if not target.is_relative_to(WEB) or target.suffix not in {".js", ".css", ".glb", ".woff2", ".svg"}:
                self.send_error(404)
                return
        if not target.is_file():
            self.send_error(404)
            return
        mime = {".js": "text/javascript", ".json": "application/json", ".css": "text/css",
                ".glb": "model/gltf-binary"}.get(target.suffix, self.guess_type(str(target)))
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8877)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"http://127.0.0.1:{server.server_port}", flush=True)
    server.serve_forever()
