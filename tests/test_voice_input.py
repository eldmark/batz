import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from logos.server import handle_api
from logos.voice_input import VoiceInputError, availability, transcribe


class LocalVoice(unittest.TestCase):
    def test_unavailable_is_explicit(self):
        with patch.dict(os.environ, {"LOGOS_WHISPER_CLI": "", "LOGOS_WHISPER_MODEL": ""}):
            with patch("logos.voice_input.shutil.which", return_value=None):
                self.assertFalse(availability()["available"])
                self.assertFalse(handle_api("/api/voice/status", {})["available"])
                with self.assertRaises(VoiceInputError) as cm: transcribe(b"a" * 200)
                self.assertEqual(cm.exception.code, "voice_unavailable")

    def test_local_transcript_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            binary, model = Path(temp) / "whisper-cli", Path(temp) / "ggml-base.bin"
            binary.touch(); model.touch()
            calls = []
            def fake_run(args, **kwargs):
                calls.append(args)
                if "-of" in args:
                    Path(args[args.index("-of") + 1] + ".txt").write_text("Juan lee.\n", encoding="utf-8")
            with patch.dict(os.environ, {"LOGOS_WHISPER_CLI": str(binary), "LOGOS_WHISPER_MODEL": str(model)}):
                with patch("logos.voice_input.shutil.which", return_value="/usr/bin/ffmpeg"):
                    with patch("logos.voice_input.subprocess.run", side_effect=fake_run):
                        self.assertEqual(transcribe(b"a" * 200), "Juan lee.")
            self.assertIn("es", calls[1])
            self.assertEqual(len(calls), 2)

    def test_rejects_oversize_before_process(self):
        with self.assertRaises(VoiceInputError) as cm: transcribe(b"x" * 5_000_001)
        self.assertEqual(cm.exception.code, "invalid_audio")


if __name__ == "__main__": unittest.main()
