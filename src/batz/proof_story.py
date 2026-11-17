"""Guion determinista para certificados aceptados por el checker independiente.

Se narra en el orden y con la numeración de la vista Fitch (`proof/fitch.py`), para que «la
línea 3» signifique lo mismo en la derivación y en el paso a paso. Cada evento cita el paso
del certificado que lo justifica.
"""
from __future__ import annotations

from dataclasses import dataclass

from .errors import SCHEMA_VERSION
from .printer import to_string
from .proof import ProofCertificate, verify
from .proof.fitch import DISCHARGE, fitch_layout


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
    lines: tuple = ()

    show: object = to_string

    def to_dict(self):
        return {"schema_version": SCHEMA_VERSION, "kind": "proof",
                "events": list(self.events), "fitch": [line.to_dict(self.show) for line in self.lines]}


def _refs(refs):
    names = [f"{r[0]}–{r[1]}" if isinstance(r, tuple) else str(r) for r in refs]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " y " + names[-1]


def _text(line, by_n, show):
    formula = None if line.formula is None else show(line.formula)
    if line.rule == "premise":
        return f"Partimos de la premisa {formula}."
    if line.rule == "hyp" and line.flag:
        return f"Tomamos un {line.flag} nuevo y suponemos {formula}: es el testigo del existencial."
    if line.rule == "hyp":
        return f"Suponemos {formula} y abrimos una caja; al cerrarla, esa hipótesis se descarga."
    if line.rule == "flag":
        return f"Tomamos un {line.flag} cualquiera: no aparece en ninguna hipótesis abierta."
    if line.rule == "reit":
        return f"Repetimos {formula} de la línea {_refs(line.refs)} para cerrar la caja con ella."
    name = RULE_NAMES[line.rule]
    if line.rule == "or_e":
        return (f"Las dos cajas, {_refs(line.refs[1:])}, llegan a {formula}; con la disyunción de la "
                f"línea {line.refs[0]}, por {name} vale {formula}.")
    if line.rule == "ex_e":
        witness = by_n[line.refs[1][0]].flag
        return (f"La caja {_refs(line.refs[1:])} llega a {formula}, que no menciona a {witness}; "
                f"por {name} vale {formula} fuera de la caja.")
    if line.rule in DISCHARGE:
        return f"Cerramos la caja {_refs(line.refs)}: por {name} obtenemos {formula}."
    if line.refs:
        return f"Con la regla de {name} y la línea {_refs(line.refs)}, obtenemos {formula}." if len(line.refs) == 1 \
            else f"Con la regla de {name} y las líneas {_refs(line.refs)}, obtenemos {formula}."
    return f"Por {name}, obtenemos {formula}."


def build_proof_narration(certificate: ProofCertificate, show=to_string) -> ProofNarration:
    """No construye eventos si cualquier paso del certificado es inválido.

    `show` convierte cada fórmula en texto; en lógica proposicional deja las letras como se escribieron."""
    verify(certificate)
    lines = fitch_layout(certificate)
    by_n = {line.n: line for line in lines}
    # Quién cierra cada caja: cita su paso la línea que la presenta sin paso propio.
    closer = {}
    for line in lines:
        for ref in line.refs:
            if isinstance(ref, tuple):
                closer[ref[0]] = line.step
    events = []
    for line in lines:
        step_id = line.step if line.step is not None else (line.steps[0] if line.steps else closer.get(line.n))
        if step_id is None:
            continue  # premisa que la prueba no usa
        hyps = [show(l.formula) for l in lines
                if l.rule == "hyp" and l.box and l.box[-1] in line.box and l.n <= line.n]
        events.append({
            "id": len(events) + 1, "step_id": step_id, "line": line.n, "trace_path": f"p{line.n}",
            "kind": "proof", "formula": None if line.formula is None else show(line.formula),
            "value": None, "text_es": _text(line, by_n, show), "span": None, "assignment": {},
            "element": None, "relation": None, "term_values": [], "rule": line.rule,
            "rule_label": line.label, "refs": [f"{r[0]}–{r[1]}" if isinstance(r, tuple) else str(r) for r in line.refs],
            "context": hyps, "depth": line.depth, "steps": list(line.steps),
            "verified_by": {"certificate_step": step_id},
        })
    return ProofNarration(certificate, tuple(events), tuple(lines), show)
