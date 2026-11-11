"""Guion determinista para certificados aceptados por el checker independiente."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import SCHEMA_VERSION
from .printer import to_string
from .proof import ProofCertificate, verify


RULE_NAMES = {
    "assume": "hipótesis", "and_i": "introducción de conjunción",
    "and_e1": "eliminación de la primera conjunción", "and_e2": "eliminación de la segunda conjunción",
    "or_i1": "introducción de la primera disyunción", "or_i2": "introducción de la segunda disyunción",
    "or_e": "eliminación de disyunción", "imp_i": "introducción de implicación",
    "imp_e": "eliminación de implicación", "not_i": "introducción de negación",
    "not_e": "eliminación de negación", "bot_e": "eliminación de contradicción",
    "raa": "reducción al absurdo", "iff_i": "introducción de bicondicional",
    "iff_e1": "eliminación de bicondicional, primer sentido",
    "iff_e2": "eliminación de bicondicional, segundo sentido",
    "all_i": "introducción de universal", "all_e": "eliminación de universal",
    "ex_i": "introducción de existencial", "ex_e": "eliminación de existencial",
    "eq_i": "introducción de igualdad", "eq_e": "eliminación de igualdad",
}


@dataclass(frozen=True)
class ProofNarration:
    certificate: ProofCertificate
    events: tuple[dict, ...]

    def to_dict(self):
        return {"schema_version": SCHEMA_VERSION, "kind": "proof",
                "events": list(self.events)}


def build_proof_narration(certificate: ProofCertificate) -> ProofNarration:
    """No construye eventos si cualquier paso del certificado es inválido."""
    verify(certificate)
    events = []
    for step in certificate.steps:
        formula = to_string(step.formula)
        if step.rule == "assume":
            text = f"Tomamos {formula} como hipótesis."
        elif step.refs:
            refs = ", ".join(str(ref) for ref in step.refs)
            text = f"Con la regla de {RULE_NAMES[step.rule]} y los pasos {refs}, obtenemos {formula}."
        else:
            text = f"Por {RULE_NAMES[step.rule]}, obtenemos {formula}."
        events.append({
            "id": step.id, "step_id": step.id, "trace_path": f"p{step.id}",
            "kind": "proof", "formula": formula, "value": None,
            "text_es": text, "span": None, "assignment": {}, "element": None,
            "relation": None, "term_values": [], "rule": step.rule,
            "refs": list(step.refs), "context": [to_string(f) for f in step.context],
            "verified_by": {"certificate_step": step.id},
        })
    return ProofNarration(certificate, tuple(events))
