"""Transcripción local opcional. El texto se confirma antes de traducirse.

Funciona sin variables de entorno si `scripts/instalar_voz.ps1` (Windows) o
`scripts/instalar_voz.sh` dejaron whisper.cpp y un modelo en la carpeta de voz
(`voice_dir()`). Orden de búsqueda:

- whisper-cli: LOGOS_WHISPER_CLI, luego el PATH, luego la carpeta de voz o una
  subcarpeta suya (hasta dos niveles).
- modelo: LOGOS_WHISPER_MODEL, luego el primero que exista en la carpeta de voz
  entre ggml-small.bin, ggml-base.bin y ggml-tiny.bin.
- ffmpeg: el PATH, luego la carpeta de voz y, en Windows, lo que dejó
  `winget install Gyan.FFmpeg`: su enlace en WinGet\\Links o, si Windows no
  permitió crearlo (sin modo de desarrollador), la carpeta del paquete. Un
  servidor abierto antes de la instalación no ve el PATH nuevo.

Una variable definida manda aunque apunte a un archivo que no existe: la
configuración explícita no se reemplaza en silencio.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

MODELS = ("ggml-small.bin", "ggml-base.bin", "ggml-tiny.bin")  # el primero que exista
_WINDOWS = os.name == "nt"


class VoiceInputError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def voice_dir() -> Path:
    """Carpeta por usuario de la voz local: %LOCALAPPDATA%\\LOGOS\\voz o ~/.local/share/logos/voz."""
    if _WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(base) / "LOGOS" / "voz"
    return Path.home() / ".local" / "share" / "logos" / "voz"


def _winget_dir() -> Path | None:
    base = os.environ.get("LOCALAPPDATA")
    return Path(base) / "Microsoft" / "WinGet" if _WINDOWS and base else None


def _exe(name: str) -> str:
    return name + ".exe" if _WINDOWS else name


def _usable(path: Path, executable: bool = True) -> bool:
    try:
        return path.is_file() and (not executable or _WINDOWS or os.access(path, os.X_OK))
    except OSError:
        return False


def _first(folder: Path, *patterns: str) -> Path | None:
    """Primer ejecutable que coincide con los patrones, en ese orden y luego alfabético."""
    try:
        candidates = [path for pattern in patterns for path in sorted(folder.glob(pattern))]
    except OSError:
        return None
    return next((path for path in candidates if _usable(path)), None)


def _search(folder: Path, name: str) -> Path | None:
    """`name` en `folder` o en sus subcarpetas de hasta dos niveles."""
    return _first(folder, name, f"*/{name}", f"*/*/{name}")


def _configured(variable: str) -> Path | None:
    path = Path(os.environ[variable])
    return path if _usable(path, executable=False) else None


def _whisper_cli() -> Path | None:
    if os.environ.get("LOGOS_WHISPER_CLI"):
        return _configured("LOGOS_WHISPER_CLI")
    on_path = shutil.which("whisper-cli")
    return Path(on_path) if on_path else _search(voice_dir(), _exe("whisper-cli"))


def _model() -> Path | None:
    if os.environ.get("LOGOS_WHISPER_MODEL"):
        return _configured("LOGOS_WHISPER_MODEL")
    folder = voice_dir()
    return next((folder / name for name in MODELS if _usable(folder / name, executable=False)), None)


def _ffmpeg() -> Path | None:
    on_path = shutil.which("ffmpeg")
    if on_path:
        return Path(on_path)
    winget = _winget_dir()
    return (_search(voice_dir(), _exe("ffmpeg"))
            or (_first(winget, "Links/ffmpeg.exe", "Packages/Gyan.FFmpeg*/*/bin/ffmpeg.exe") if winget else None))


def _tools() -> tuple[Path | None, Path | None, Path | None]:
    return tuple(path.absolute() if path else None for path in (_whisper_cli(), _model(), _ffmpeg()))


def _whisper_arg(path: Path, cwd: Path) -> str:
    """Ruta que whisper-cli sabe abrir desde `cwd`.

    En Windows whisper-cli recibe los argumentos en la página de códigos ANSI y abre
    los archivos como UTF-8, así que no encuentra una ruta con «á» o «ñ» (un perfil
    C:\\Users\\Lázaro, por ejemplo). Se usa la ruta relativa o el nombre corto 8.3 si
    alguno queda en ASCII.
    """
    text = str(path)
    if text.isascii() or not _WINDOWS:
        return text
    try:
        relative = os.path.relpath(text, cwd)
    except ValueError:  # otra unidad
        relative = text
    if relative.isascii():
        return relative
    import ctypes
    short = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.kernel32.GetShortPathNameW(text, short, len(short)) and short.value.isascii():
        return short.value
    return text


def availability() -> dict:
    """Estado para la API: nombres de archivo y piezas que faltan, nunca rutas absolutas."""
    binary, model, ffmpeg = _tools()
    status = {"available": bool(binary and model and ffmpeg),
              "engine": "whisper.cpp local", "language": "es"}
    if model:
        status["model"] = model.name
    missing = [name for name, path in (("whisper-cli", binary), ("model", model), ("ffmpeg", ffmpeg))
               if path is None]
    if missing:
        status["missing"] = missing
    return status


def transcribe(audio: bytes) -> str:
    if not isinstance(audio, bytes) or not 100 <= len(audio) <= 5_000_000:
        raise VoiceInputError("invalid_audio", "Grabación vacía o demasiado grande (máximo 5 MB).")
    binary, model, ffmpeg = _tools()
    if not (binary and model and ffmpeg):
        raise VoiceInputError("voice_unavailable",
                              "Instala la voz local con scripts/instalar_voz.ps1 (o .sh) "
                              "o configura LOGOS_WHISPER_CLI y LOGOS_WHISPER_MODEL en este equipo.")
    with tempfile.TemporaryDirectory(prefix="logos-voz-") as temp:
        folder = Path(temp)
        source, wav, out = folder / "recording.webm", folder / "recording.wav", folder / "transcript"
        source.write_bytes(audio)
        try:
            subprocess.run([str(ffmpeg), "-nostdin", "-v", "error", "-y", "-i", str(source),
                            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
                           capture_output=True, timeout=15, check=True)
            # Nombres relativos a la carpeta temporal: whisper-cli no abre rutas con acentos en Windows.
            subprocess.run([str(binary), "-m", _whisper_arg(model, folder), "-f", wav.name, "-l", "es",
                            "-otxt", "-of", out.name, "-np"],
                           cwd=folder, capture_output=True, timeout=60, check=True)
            result = out.with_suffix(".txt").read_text(encoding="utf-8").strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, UnicodeError) as exc:
            raise VoiceInputError("transcription_failed", "No se pudo transcribir la grabación localmente.") from exc
        if not result:
            raise VoiceInputError("empty_transcript", "No se detectó una frase. Prueba otra grabación.")
        return result
