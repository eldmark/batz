#!/usr/bin/env python3
"""Genera docs/validation/ESPANOL-51-CASOS.md: cada frase de la especificación, lo esperado y lo obtenido.

    PYTHONPATH=src python3 scripts/report_spanish.py            # escribe el documento
    PYTHONPATH=src python3 scripts/report_spanish.py --check    # falla si algún caso no cumple
"""
import argparse
import sys
from pathlib import Path

from logos import LogosError, parse_checked, translate_spanish
from logos.spanish_cyk import parse

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "docs/specs/espanol/casos_borde.txt"
OUT = ROOT / "docs/validation/ESPANOL-51-CASOS.md"


def run_case(expected, phrase):
    _, trees = parse(phrase)
    row = {"phrase": phrase, "expected": expected, "trees": len(trees), "readings": [], "error": None}
    try:
        result = translate_spanish(phrase)
        for r in result.readings:
            # cada lectura debe volver a leerse como fórmula bien formada con su propia firma
            assert parse_checked(r.text, r.signature, strict=True) == r.formula
            row["readings"].append((r.text, r.note))
    except LogosError as exc:
        row["error"] = exc.message
    if expected == 0:
        row["ok"] = not trees and row["error"] is not None and not row["readings"]
    else:
        row["ok"] = len(trees) >= expected and bool(row["readings"]) and row["error"] is None
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rows, section = [], "General"
    for line in CASES.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            section = line.lstrip("# ").strip() or section
            continue
        if line.strip():
            expected, phrase = line.split("|", 1)
            rows.append((section, run_case(int(expected), phrase.strip())))
    failed = [r for _, r in rows if not r["ok"]]
    accepted = [r for _, r in rows if r["expected"]]
    ambiguous = [r for r in accepted if len(r["readings"]) > 1]
    lines = [
        "# Español controlado: los 51 casos de la especificación",
        "",
        "> Documento generado por `scripts/report_spanish.py`. No se edita a mano: se vuelve a generar.",
        "",
        f"**Resultado: {len(rows) - len(failed)} de {len(rows)} casos cumplen.** "
        f"{len(accepted)} frases se aceptan ({len(ambiguous)} con más de una lectura) y "
        f"{len(rows) - len(accepted)} se rechazan a propósito.",
        "",
        "Cómo se lee cada fila:",
        "",
        "- **Esperado** es el número mínimo de árboles sintácticos distintos que fija la especificación; `0` significa que la frase debe rechazarse.",
        "- **Lecturas** son las fórmulas distintas que se le ofrecen a la persona. Nunca se elige una en silencio.",
        "- Una frase aceptada cumple si tiene al menos los árboles esperados, produce alguna lectura y cada lectura vuelve a leerse como fórmula bien formada. Una rechazada cumple si no produce ningún árbol ni ninguna lectura.",
        "",
        "| # | Frase | Esperado | Árboles | Lecturas | Cumple |",
        "|---|---|---|---|---|---|",
    ]
    for i, (_, r) in enumerate(rows, 1):
        if r["readings"]:
            cell = "<br>".join(f"`{text}`" for text, _ in r["readings"])
        else:
            cell = f"rechazada: {r['error']}"
        lines.append(f"| {i} | {r['phrase']} | {r['expected']} | {r['trees']} | {cell} | {'sí' if r['ok'] else '**NO**'} |")
    lines += ["", "## Frases con más de una lectura", ""]
    for r in ambiguous:
        lines.append(f"**{r['phrase']}**")
        lines.append("")
        for text, note in r["readings"]:
            lines.append(f"- `{text}` — {note}")
        lines.append("")
    lines += ["## Cómo repetir la comprobación", "", "```bash",
              "PYTHONPATH=src python3 scripts/report_spanish.py --check",
              "PYTHONPATH=src:tests python3 -m unittest tests.test_spanish_full", "```", ""]
    if args.check:
        for r in failed:
            print("NO CUMPLE:", r["phrase"], r)
        print(f"{len(rows) - len(failed)}/{len(rows)} casos cumplen")
        sys.exit(1 if failed else 0)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(rows) - len(failed)}/{len(rows)} casos cumplen")


if __name__ == "__main__":
    main()
