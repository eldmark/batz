"""Motor B: resolución como oráculo de contraste del motor A (deducción natural).

Nunca produce `proved`: ese estado exige un certificado aceptado por el checker. Sirve para
detectar discrepancias entre dos algoritmos independientes (ver `contrast`).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..errors import LogosError
from ..parser import parse
from .prover import ResolutionConfig, ResolutionResult, Step, refute, resolve

# (motor A, motor B) → (veredicto, explicación)
_MATRIX = {
    ("proved", "refuted"): ("consistent", "Deducción natural la probó y resolución la refutó por un camino distinto."),
    ("proved", "saturated"): ("soundness_alarm", "A probó algo que B muestra satisfacible con la negación: hay un error en uno de los dos."),
    ("proved", "unknown"): ("no_information", "A probó; B agotó sus límites."),
    ("unknown", "refuted"): ("completeness_gap", "B encontró refutación y A no encontró prueba: hueco de completitud del buscador de A."),
    ("unknown", "saturated"): ("consistent", "Deducción natural no halló prueba y resolución saturó sin contradicción: la consecuencia no vale."),
    ("unknown", "unknown"): ("no_information", "Ninguno decidió dentro de los límites."),
}


@dataclass(frozen=True)
class Contrast:
    verdict: str   # consistent | soundness_alarm | completeness_gap | no_information
    message: str
    engine_a: str
    engine_b: ResolutionResult

    def to_dict(self):
        return {"verdict": self.verdict, "message": self.message, "engine_a": self.engine_a,
                "engine_b": self.engine_b.to_dict()}


def resolve_text(premises, conclusion, constants=(), config=None):
    """Como `resolve`, con fórmulas en texto. Lanza `LogosError` si no se pueden leer."""
    return resolve([parse(p, constants) for p in premises], parse(conclusion, constants), config)


def contrast(premises, conclusion, proof_config=None, resolution_config=None):
    """Corre los dos motores sobre el mismo secuente y clasifica el resultado."""
    from ..proof import prove
    a = prove(premises, conclusion, proof_config)
    b = resolve(premises, conclusion, resolution_config)
    status_a = "proved" if a.status == "proved" else "unknown"
    verdict, message = _MATRIX[(status_a, b.status)]
    return Contrast(verdict, message, a.status, b)


__all__ = ["Contrast", "LogosError", "ResolutionConfig", "ResolutionResult", "Step", "contrast",
           "refute", "resolve", "resolve_text"]
