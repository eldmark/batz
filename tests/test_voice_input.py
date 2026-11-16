from contextlib import contextmanager
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from logos import voice_input
from logos.server import handle_api
from logos.voice_input import VoiceInputError, availability, transcribe


def _tool(path: Path) -> Path:
    """Ejecutable de mentira; fuera de Windows también necesita el permiso de ejecución."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _model(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"modelo")
    return path


def _fake_run(calls):
    """Simula ffmpeg y whisper-cli; whisper-cli resuelve sus rutas desde `cwd`, como el real."""
    def run(args, cwd=None, **kwargs):
        args = list(args)
        if "-of" in args:
            folder = Path(cwd or ".")
            (folder / (args[args.index("-of") + 1] + ".txt")).write_text("Juan lee.\n", encoding="utf-8")
            model = args.index("-m") + 1
            args[model] = os.path.abspath(folder / args[model])
        calls.append(args)
    return run


@contextmanager
def isolated(folder: Path, on_path=None, winget=None, env=None):
    """Sin variables ni instalación real: PATH simulado, carpeta de voz y carpeta de winget de prueba."""
    on_path = on_path or {}
    with patch.dict(os.environ, {"LOGOS_WHISPER_CLI": "", "LOGOS_WHISPER_MODEL": "", **(env or {})}), \
         patch.object(voice_input, "voice_dir", return_value=folder), \
         patch.object(voice_input, "_winget_dir", return_value=winget), \
         patch.object(voice_input.shutil, "which", side_effect=on_path.get):
        yield


class LocalVoice(unittest.TestCase):
    def test_unavailable_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp, isolated(Path(temp) / "voz"):
            self.assertFalse(availability()["available"])
            status = handle_api("/api/voice/status", {})
            self.assertFalse(status["available"])
            self.assertEqual(status["missing"], ["whisper-cli", "model", "ffmpeg"])
            with self.assertRaises(VoiceInputError) as cm: transcribe(b"a" * 200)
            self.assertEqual(cm.exception.code, "voice_unavailable")

    def test_local_transcript_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            binary, model = Path(temp) / "whisper-cli", Path(temp) / "ggml-base.bin"
            binary.touch(); model.touch()
            calls = []
            with patch.dict(os.environ, {"LOGOS_WHISPER_CLI": str(binary), "LOGOS_WHISPER_MODEL": str(model)}):
                with patch("logos.voice_input.shutil.which", return_value="/usr/bin/ffmpeg"):
                    with patch("logos.voice_input.subprocess.run", side_effect=_fake_run(calls)):
                        self.assertEqual(transcribe(b"a" * 200), "Juan lee.")
            self.assertIn("es", calls[1])
            self.assertEqual(len(calls), 2)

    def test_rejects_oversize_before_process(self):
        with self.assertRaises(VoiceInputError) as cm: transcribe(b"x" * 5_000_001)
        self.assertEqual(cm.exception.code, "invalid_audio")


class Discovery(unittest.TestCase):
    """Encuentra whisper-cli, el modelo y ffmpeg sin variables de entorno."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.voz = self.root / "voz"

    def run_transcription(self):
        """Transcribe con procesos simulados y devuelve las órdenes ejecutadas."""
        calls = []
        with patch.object(voice_input.subprocess, "run", side_effect=_fake_run(calls)):
            self.assertEqual(transcribe(b"a" * 200), "Juan lee.")
        return calls

    def test_install_folder_works_without_env_vars(self):
        cli = _tool(self.voz / "whisper" / "Release" / voice_input._exe("whisper-cli"))
        ffmpeg = _tool(self.voz / voice_input._exe("ffmpeg"))
        _model(self.voz / "ggml-tiny.bin"); base = _model(self.voz / "ggml-base.bin")
        with isolated(self.voz):
            status = availability()
            calls = self.run_transcription()
        # La API recibe el nombre del modelo, nunca rutas absolutas.
        self.assertEqual(status, {"available": True, "engine": "whisper.cpp local", "language": "es",
                                  "model": "ggml-base.bin"})
        self.assertEqual(calls[0][0], str(ffmpeg))
        self.assertEqual(calls[1][:3], [str(cli), "-m", str(base)])

    def test_model_preference_is_small_then_base_then_tiny(self):
        self.voz.mkdir()
        with isolated(self.voz):
            self.assertNotIn("model", availability())
            for name in ("ggml-tiny.bin", "ggml-base.bin", "ggml-small.bin"):
                _model(self.voz / name)
                self.assertEqual(availability()["model"], name)

    def test_search_goes_at_most_two_folders_down(self):
        _tool(self.voz / "a" / "b" / "c" / voice_input._exe("whisper-cli"))
        _tool(self.voz / "ffmpeg" / "bin" / voice_input._exe("ffmpeg"))
        with isolated(self.voz):
            self.assertEqual(availability()["missing"], ["whisper-cli", "model"])

    def test_path_comes_before_install_folder(self):
        cli = _tool(self.root / "bin" / voice_input._exe("whisper-cli"))
        ffmpeg = _tool(self.root / "bin" / voice_input._exe("ffmpeg"))
        _tool(self.voz / voice_input._exe("whisper-cli")); _tool(self.voz / voice_input._exe("ffmpeg"))
        _model(self.voz / "ggml-base.bin")
        with isolated(self.voz, on_path={"whisper-cli": str(cli), "ffmpeg": str(ffmpeg)}):
            calls = self.run_transcription()
        self.assertEqual((calls[0][0], calls[1][0]), (str(ffmpeg), str(cli)))

    def test_env_vars_come_first(self):
        cli = _tool(self.root / "propio" / "mi-whisper")
        model = _model(self.root / "propio" / "mi-modelo.bin")
        on_path = {"whisper-cli": str(_tool(self.root / "bin" / voice_input._exe("whisper-cli"))),
                   "ffmpeg": str(_tool(self.root / "bin" / voice_input._exe("ffmpeg")))}
        _tool(self.voz / voice_input._exe("whisper-cli")); _model(self.voz / "ggml-small.bin")
        with isolated(self.voz, on_path=on_path,
                      env={"LOGOS_WHISPER_CLI": str(cli), "LOGOS_WHISPER_MODEL": str(model)}):
            self.assertEqual(availability()["model"], "mi-modelo.bin")
            calls = self.run_transcription()
        self.assertEqual(calls[1][:3], [str(cli), "-m", str(model)])

    def test_env_var_pointing_nowhere_is_not_replaced(self):
        _tool(self.voz / voice_input._exe("whisper-cli")); _tool(self.voz / voice_input._exe("ffmpeg"))
        _model(self.voz / "ggml-base.bin")
        with isolated(self.voz, env={"LOGOS_WHISPER_MODEL": str(self.root / "no-existe.bin")}):
            status = availability()
            with self.assertRaises(VoiceInputError) as cm: transcribe(b"a" * 200)
        self.assertEqual((status["available"], status["missing"]), (False, ["model"]))
        self.assertEqual(cm.exception.code, "voice_unavailable")

    def test_ffmpeg_falls_back_to_winget(self):
        _tool(self.voz / "whisper" / voice_input._exe("whisper-cli")); _model(self.voz / "ggml-base.bin")
        winget = self.root / "WinGet"
        with isolated(self.voz, winget=winget):
            self.assertEqual(availability()["missing"], ["ffmpeg"])
            # Sin modo de desarrollador winget no crea el enlace y deja ffmpeg en la carpeta del paquete.
            package = _tool(winget / "Packages" / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
                            / "ffmpeg-9.0.2-full_build" / "bin" / "ffmpeg.exe")
            self.assertTrue(availability()["available"])
            self.assertEqual(self.run_transcription()[0][0], str(package))
            link = _tool(winget / "Links" / "ffmpeg.exe")
            self.assertEqual(self.run_transcription()[0][0], str(link))

    def test_install_folder_per_platform(self):
        with patch.object(voice_input, "_WINDOWS", True), \
             patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)}):
            self.assertEqual(voice_input.voice_dir(), self.root / "LOGOS" / "voz")
            self.assertEqual(voice_input._winget_dir(), self.root / "Microsoft" / "WinGet")
        with patch.object(voice_input, "_WINDOWS", False):
            self.assertEqual(voice_input.voice_dir(), Path.home() / ".local" / "share" / "logos" / "voz")
            self.assertIsNone(voice_input._winget_dir())


class NonAsciiPaths(unittest.TestCase):
    """whisper-cli en Windows no abre rutas con acentos, como C:\\Users\\Lázaro\\..."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_model_path_relative_to_work_folder(self):
        model = _model(self.root / "Lázaro" / "voz" / "ggml-base.bin")
        work = self.root / "Lázaro" / "Temp" / "logos-voz-1"
        with patch.object(voice_input, "_WINDOWS", True):
            self.assertEqual(voice_input._whisper_arg(model, work), os.path.join("..", "..", "voz", "ggml-base.bin"))
        with patch.object(voice_input, "_WINDOWS", False):  # fuera de Windows la ruta UTF-8 funciona tal cual
            self.assertEqual(voice_input._whisper_arg(model, work), str(model))

    @unittest.skipUnless(os.name == "nt", "nombres cortos 8.3 solo en Windows")
    def test_model_path_short_name(self):
        model = _model(self.root / "Lázaro" / "ggml-base.bin")
        work = self.root / "trabajo"; work.mkdir()
        arg = voice_input._whisper_arg(model, work)
        if not arg.isascii():
            self.skipTest("este volumen no genera nombres cortos 8.3")
        self.assertTrue(os.path.samefile(arg, model))


if __name__ == "__main__": unittest.main()
