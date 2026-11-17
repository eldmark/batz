"""Síntesis de voz local y opcional, para equipos cuyo navegador no ofrece voces en español.

En Windows y macOS el navegador expone las voces del sistema. En Linux solo las ve si hay
`speech-dispatcher` con un sintetizador, y a menudo no hay ninguna. Esta pieza usa `espeak-ng`
(si está instalado) para generar el audio en el propio equipo: el texto no sale de la máquina.
Sin `espeak-ng` el servicio informa que no está disponible y la interfaz sigue sin audio.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import threading
from collections import OrderedDict

MAX_CHARS = 600
MAX_AUDIO_BYTES = 8_000_000
TIMEOUT_SECONDS = 15
RATE_RANGE = (0.5, 2.0)
BASE_WPM = 165
INSTALL_HINT = ("Instala espeak-ng para oír la narración en este equipo: "
                "Arch/CachyOS «sudo pacman -S espeak-ng», Debian/Ubuntu «sudo apt install espeak-ng», "
                "Fedora «sudo dnf install espeak-ng».")

_VOICE_ID = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{1,8})?(?:\+[a-z]{1,8}[0-9]?)?$")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_cache: "OrderedDict[tuple, bytes]" = OrderedDict()
_lock = threading.Lock()


class VoiceOutputError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def engine_path() -> str | None:
    return shutil.which("espeak-ng") or shutil.which("espeak")


def _spanish_name(raw: str) -> str:
    name = raw.replace("_", " ")
    return (name.replace("Spanish (Latin America)", "Español (Latinoamérica)")
                .replace("Spanish (Spain)", "Español (España)").replace("Spanish", "Español"))


def parse_voices(listing: str) -> list[dict]:
    """Lee la salida de `espeak-ng --voices=es`: una fila por voz tras la cabecera."""
    voices: list[dict] = []
    for line in listing.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4 or not re.match(r"^es(?:-|$)", parts[1]):
            continue
        language, name = parts[1], _spanish_name(parts[3])
        voices.append({"id": language, "label": f"{name} · masculina", "lang": language})
        voices.append({"id": f"{language}+f3", "label": f"{name} · femenina", "lang": language})
    return voices


def voices() -> list[dict]:
    binary = engine_path()
    if not binary:
        return []
    try:
        done = subprocess.run([binary, "--voices=es"], capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_voices(done.stdout) if done.returncode == 0 else []


def availability() -> dict:
    binary = engine_path()
    listed = voices() if binary else []
    return {"available": bool(listed), "engine": "espeak-ng" if listed else None,
            "voices": listed, "hint": None if listed else INSTALL_HINT}


def _clean(text) -> str:
    if not isinstance(text, str):
        raise VoiceOutputError("invalid_text", "El texto debe ser una cadena.")
    text = " ".join(_CONTROL.sub(" ", text).split())
    if not text:
        raise VoiceOutputError("invalid_text", "No hay texto que leer.")
    if len(text) > MAX_CHARS:
        raise VoiceOutputError("text_too_long", f"El texto supera {MAX_CHARS} caracteres.")
    return text


def synthesize(text, voice: str, rate: float = 1.0) -> bytes:
    """WAV con el texto leído. `voice` debe ser una de las que lista `voices()`."""
    text = _clean(text)
    if not isinstance(voice, str) or not _VOICE_ID.match(voice):
        raise VoiceOutputError("invalid_voice", "Voz no válida.")
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        raise VoiceOutputError("invalid_rate", "Velocidad no válida.") from None
    rate = min(max(rate, RATE_RANGE[0]), RATE_RANGE[1])
    binary = engine_path()
    if not binary:
        raise VoiceOutputError("voice_unavailable", INSTALL_HINT)
    if voice not in {item["id"] for item in voices()}:
        raise VoiceOutputError("invalid_voice", "Esa voz no está instalada.")
    key = (voice, round(rate, 2), text)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    command = [binary, "-v", voice, "-s", str(round(BASE_WPM * rate)), "--stdout", "--stdin"]
    try:
        done = subprocess.run(command, input=text.encode("utf-8"), capture_output=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise VoiceOutputError("synthesis_failed", "La síntesis tardó demasiado.") from None
    except OSError:
        raise VoiceOutputError("voice_unavailable", INSTALL_HINT) from None
    audio = done.stdout
    if done.returncode != 0 or not audio.startswith(b"RIFF") or len(audio) > MAX_AUDIO_BYTES:
        raise VoiceOutputError("synthesis_failed", "No se pudo generar el audio.")
    with _lock:
        _cache[key] = audio
        while len(_cache) > 64:
            _cache.popitem(last=False)
    return audio
