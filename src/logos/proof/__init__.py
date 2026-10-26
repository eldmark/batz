"""Pruebas por deducción natural: certificados, checker independiente y buscador."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..ast import Bottom
from ..errors import LogosError
from ..parser import parse
from .certificate import ProofCertificate, ProofError, ProofStep
from .checker import is_valid, verify
from .render import format_certificate
from .search import SearchConfig, search


@dataclass(frozen=True)
class ProofResult:
    """`status`: proved | inconsistent | unknown | invalid_input.

    `proved` e `inconsistent` solo se devuelven con un certificado que el
    checker aceptó. `unknown` jamás significa «falso».
    """

    status: str
    certificate: Optional[ProofCertificate] = None
    reason: Optional[str] = None
    nodes: int = 0
    diagnostic: Optional[dict] = None

    def to_dict(self):
        from ..serialize import result_to_dict
        return result_to_dict(self.status, self.certificate, None, self.reason, self.diagnostic, self.nodes)


def _run(premises, conclusion, config, ok_status):
    cert, reason, nodes = search(premises, conclusion, config)
    if cert is None:
        return ProofResult("unknown", None, reason, nodes)
    try:
        verify(cert)
    except ProofError as e:  # error interno del buscador: nunca se afirma la prueba
        return ProofResult("unknown", None, "checker_rejected", nodes, e.to_diagnostic())
    return ProofResult(ok_status, cert, None, nodes)


def prove(premises, conclusion, config=None):
    """Busca `premises ⊢ conclusion`; las fórmulas son AST."""
    return _run(tuple(premises), conclusion, config, "proved")


def prove_text(premises, conclusion, constants=(), config=None, propositional=False):
    """Como `prove`, con fórmulas en texto. Los errores de entrada dan `invalid_input`."""
    try:
        if propositional:  # las letras de todas las fórmulas comparten la misma tabla
            ps, c = _parse_prop(premises, conclusion)
        else:
            ps = tuple(parse(p, constants) for p in premises)
            c = parse(conclusion, constants)
    except LogosError as e:
        return ProofResult("invalid_input", diagnostic=e.to_diagnostic())
    return prove(ps, c, config)


def _parse_prop(premises, conclusion):
    # Se parsea junto para detectar colisiones p/P entre fórmulas distintas.
    texts = [*premises, conclusion]
    parsed = [parse(t, (), propositional=True) for t in texts]
    parse(" ∧ ".join(f"({t})" for t in texts), (), propositional=True)
    return tuple(parsed[:-1]), parsed[-1]


def find_inconsistency(premises, config=None):
    """Busca `premises ⊢ ⊥`. `inconsistent` solo con certificado aceptado."""
    return _run(tuple(premises), Bottom(), config, "inconsistent")


__all__ = ["ProofCertificate", "ProofError", "ProofResult", "ProofStep", "SearchConfig",
           "find_inconsistency", "format_certificate", "is_valid", "prove", "prove_text", "verify"]
