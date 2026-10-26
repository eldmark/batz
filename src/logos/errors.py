"""Errores localizables del compilador (contrato `invalid_input`)."""
from __future__ import annotations

SCHEMA_VERSION = "1"


class LogosError(Exception):
    """Error léxico, sintáctico o semántico con ubicación en el texto."""

    def __init__(self, stage, code, message, span=None, source=None):
        super().__init__(message)
        self.stage = stage  # "lexical" | "syntactic" | "semantic"
        self.code = code
        self.message = message
        self.span = span
        self.source = source

    def __str__(self):
        if self.span is None:
            return f"[{self.stage}:{self.code}] {self.message}"
        line, col = self.line_col()
        return f"[{self.stage}:{self.code}] {self.message} (línea {line}, columna {col})"

    def line_col(self):
        """Línea y columna (desde 1) del inicio del span; (1, inicio+1) sin fuente."""
        if self.span is None:
            return None
        if self.source is None:
            return 1, self.span.start + 1
        before = self.source[: self.span.start]
        return before.count("\n") + 1, self.span.start - (before.rfind("\n") + 1) + 1

    def to_diagnostic(self):
        d = {
            "schema_version": SCHEMA_VERSION,
            "status": "invalid_input",
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
            "span": None if self.span is None else [self.span.start, self.span.end],
        }
        if self.span is not None:
            d["line"], d["column"] = self.line_col()
        return d
