"""Síntesis local opcional (voice_output): voces, validación, caché y la ruta HTTP, con un espeak-ng simulado."""
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from logos import voice_output
from logos.server import Handler, handle_api

FAKE = '''#!{python}
import sys, wave, io, os, json
log = os.environ["FAKE_ESPEAK_LOG"]
if sys.argv[1].startswith("--voices"):
    print("Pty Language Age/Gender VoiceName File Other Languages")
    print(" 5  es  --/M  Spanish_(Spain)  roa/es")
    print(" 5  es-419  --/M  Spanish_(Latin_America)  roa/es-419")
    sys.exit(0)
text = sys.stdin.buffer.read().decode()
with open(log, "a") as handle:
    handle.write(json.dumps({"args": sys.argv[1:], "text": text}) + "\\n")
buffer = io.BytesIO()
with wave.open(buffer, "wb") as wav:
    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000); wav.writeframes(b"\\x00\\x00" * 800)
sys.stdout.buffer.write(buffer.getvalue())
'''


class FakeEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        bin_dir = Path(self.tmp.name) / "bin"; bin_dir.mkdir()
        exe = bin_dir / "espeak-ng"; exe.write_text(FAKE.replace("{python}", sys.executable, 1)); exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
        self.log = Path(self.tmp.name) / "log.jsonl"
        patcher = mock.patch.dict(os.environ, {"PATH": str(bin_dir), "FAKE_ESPEAK_LOG": str(self.log)})
        patcher.start(); self.addCleanup(patcher.stop)
        voice_output._cache.clear()

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []


class Parsing(unittest.TestCase):
    def test_duplicate_language_rows_become_one_entry(self):
        listing = ("Pty Language Age/Gender VoiceName File Other\n"
                   " 5  es-es  --/M  Spanish_(Spain)  roa/es-es\n"
                   " 5  es-es  --/M  Spanish_(Spain)  roa/es-es-x-v2\n"
                   " 5  es-mx  --/M  Spanish_(Mexico)  roa/es-mx\n")
        ids = [v["id"] for v in voice_output.parse_voices(listing)]
        self.assertEqual(ids, ["es-es", "es-es+f3", "es-mx", "es-mx+f3"])


class Voices(FakeEngine):
    def test_lists_spanish_voices_in_spanish_with_a_female_variant(self):
        status = voice_output.availability()
        self.assertTrue(status["available"])
        ids = [v["id"] for v in status["voices"]]
        self.assertEqual(ids, ["es", "es+f3", "es-419", "es-419+f3"])
        self.assertIn("Español (Latinoamérica) · femenina", [v["label"] for v in status["voices"]])

    def test_api_route_reports_voices(self):
        response = handle_api("/api/voice/voices", {})
        self.assertEqual((response["status"], response["available"]), ("ok", True))

    def test_without_engine_it_says_how_to_install(self):
        with mock.patch.dict(os.environ, {"PATH": ""}):
            status = voice_output.availability()
            self.assertFalse(status["available"])
            self.assertIn("espeak-ng", status["hint"])
            with self.assertRaises(voice_output.VoiceOutputError) as raised:
                voice_output.synthesize("hola", "es")
            self.assertEqual(raised.exception.code, "voice_unavailable")


class Synthesis(FakeEngine):
    def test_returns_wav_and_caches_identical_requests(self):
        first = voice_output.synthesize("Hola mundo", "es", 1.0)
        self.assertTrue(first.startswith(b"RIFF"))
        self.assertEqual(voice_output.synthesize("Hola mundo", "es", 1.0), first)
        self.assertEqual(len(self.calls()), 1)

    def test_rate_is_clamped_and_converted_to_words_per_minute(self):
        voice_output.synthesize("uno", "es", 99)
        voice_output.synthesize("dos", "es", 0.01)
        speeds = [c["args"][c["args"].index("-s") + 1] for c in self.calls()]
        self.assertEqual(speeds, ["330", "82"])

    def test_text_is_cleaned_and_limited(self):
        voice_output.synthesize("Hola\x00 \x07 mundo\n\n  otra", "es")
        self.assertEqual(self.calls()[0]["text"], "Hola mundo otra")
        for bad in ("", "   ", 5, None):
            with self.assertRaises(voice_output.VoiceOutputError):
                voice_output.synthesize(bad, "es")
        with self.assertRaises(voice_output.VoiceOutputError) as raised:
            voice_output.synthesize("a" * 601, "es")
        self.assertEqual(raised.exception.code, "text_too_long")

    def test_voice_id_is_validated_before_running_anything(self):
        for bad in ("es; rm -rf /", "../es", "es\n", "", "es+" + "x" * 30, "fr", 3, None):
            with self.subTest(voice=bad), self.assertRaises(voice_output.VoiceOutputError):
                voice_output.synthesize("hola", bad)
        self.assertEqual(self.calls(), [])


class Http(FakeEngine):
    def setUp(self):
        super().setUp()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def post(self, route, payload):
        return urlopen(Request(self.base + route, json.dumps(payload).encode(), {"Content-Type": "application/json"}))

    def test_speak_returns_audio_wav(self):
        with self.post("/api/voice/speak", {"text": "Hola", "voice": "es", "rate": 1}) as response:
            self.assertEqual(response.headers["Content-Type"], "audio/wav")
            self.assertTrue(response.read().startswith(b"RIFF"))

    def test_speak_errors_are_json(self):
        with self.assertRaises(HTTPError) as raised:
            self.post("/api/voice/speak", {"text": "Hola", "voice": "xx; ls"})
        self.assertEqual(raised.exception.code, 400)
        self.assertEqual(json.loads(raised.exception.read())["errors"][0]["code"], "invalid_voice")
        with mock.patch.dict(os.environ, {"PATH": ""}), self.assertRaises(HTTPError) as raised:
            self.post("/api/voice/speak", {"text": "Hola", "voice": "es"})
        self.assertEqual(raised.exception.code, 503)


if __name__ == "__main__":
    unittest.main()
