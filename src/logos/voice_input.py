"""Transcripción local opcional. El texto se confirma antes de traducirse."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


class VoiceInputError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def availability() -> dict:
    binary = os.environ.get("LOGOS_WHISPER_CLI") or shutil.which("whisper-cli")
    model = os.environ.get("LOGOS_WHISPER_MODEL")
    ffmpeg = shutil.which("ffmpeg")
    return {"available": bool(binary and Path(binary).is_file() and model and
                              Path(model).is_file() and ffmpeg),
            "engine": "whisper.cpp local", "language": "es"}


def transcribe(audio: bytes) -> str:
    if not isinstance(audio, bytes) or not 100 <= len(audio) <= 5_000_000:
        raise VoiceInputError("invalid_audio", "Grabación vacía o demasiado grande (máximo 5 MB).")
    if not availability()["available"]:
        raise VoiceInputError("voice_unavailable", "Configura whisper-cli y LOGOS_WHISPER_MODEL en este equipo.")
    binary = os.environ.get("LOGOS_WHISPER_CLI") or shutil.which("whisper-cli")
    model = os.environ["LOGOS_WHISPER_MODEL"]
    with tempfile.TemporaryDirectory(prefix="logos-voz-") as temp:
        folder = Path(temp)
        source, wav, out = folder / "recording.webm", folder / "recording.wav", folder / "transcript"
        source.write_bytes(audio)
        try:
            subprocess.run([shutil.which("ffmpeg"), "-nostdin", "-v", "error", "-y", "-i", str(source),
                            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
                           capture_output=True, timeout=15, check=True)
            subprocess.run([binary, "-m", model, "-f", str(wav), "-l", "es", "-otxt",
                            "-of", str(out), "-np"], capture_output=True, timeout=60, check=True)
            result = out.with_suffix(".txt").read_text(encoding="utf-8").strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, UnicodeError) as exc:
            raise VoiceInputError("transcription_failed", "No se pudo transcribir la grabación localmente.") from exc
        if not result:
            raise VoiceInputError("empty_transcript", "No se detectó una frase. Prueba otra grabación.")
        return result
