#!/usr/bin/env python3
"""Entrena el etiquetador de palabras fuera del léxico (regresión logística, descenso de gradiente).

    PYTHONPATH=src python3 scripts/train_spanish_tagger.py            # entrena, ajusta y escribe pesos + informe
    PYTHONPATH=src python3 scripts/train_spanish_tagger.py --quick    # rejilla reducida

Datos: frases generadas con las plantillas de abajo a partir de los lemas del diccionario base
(`src/logos/lexicon.tsv`). Las etiquetas son correctas por construcción. La partición es **por lema**:
validación y prueba usan palabras que el modelo nunca vio, que es justo el caso de uso.
Las frases de clase (`docs/specs/espanol/frases_clase.tsv`) solo se usan como prueba final.
Necesita numpy para entrenar; la inferencia (`logos.spanish_tagger`) no.
"""
import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from logos.spanish_cyk import grammar  # noqa: E402
from logos.spanish_tagger import TAGS, features  # noqa: E402

OUT = ROOT / "src/logos/spanish_tagger.json"
REPORT = ROOT / "docs/validation/ETIQUETADOR-ESPANOL.md"
CLASS = ROOT / "docs/specs/espanol/frases_clase.tsv"

def lexemes():
    """Lemas del diccionario base con sus formas etiquetadas: {clase: [ {etiqueta: [formas]} ]}."""
    from logos import lexicon
    lex = {"NM": [], "NF": [], "ADJ": [], "VI": [], "VT": [], "PM": [], "PF": []}
    for e in lexicon._read(lexicon.BASE, "base"):
        forms = e.forms()
        if e.category == "N":
            for g in ("MF" if e.feature == "C" else e.feature):
                lex["N" + g].append({t: f for t, f in forms.items() if t.startswith(f"N_{g}")})
        elif e.category == "ADJ":
            lex["ADJ"].append(forms)
        elif e.category == "V":
            for kind in ("VI", "VT"):
                own = {t: f for t, f in forms.items() if t.startswith(kind)}
                if own:
                    lex[kind].append(own)
        else:
            for g in e.feature:
                lex["P" + g].append({f"NProp_{g}": [e.lemma]})
    return lex


# Plantillas: cada hueco es (clase, etiqueta). El género/número de los huecos concuerda con la plantilla.
def templates(g, n):
    """Plantillas para un sujeto de género g (M/F) y número n (S/P)."""
    N, A = ("NM" if g == "M" else "NF", f"N_{g}{n}"), ("ADJ", f"Adj_{g}{n}")
    VIx, VTx = ("VI", f"VI_{n}"), ("VT", f"VT_{n}")
    VIs, VTs = ("VI", f"VIsub_{n}"), ("VT", f"VTsub_{n}")
    P = ("PM", "NProp_M") if g == "M" else ("PF", "NProp_F")
    OM, OF = ("NM", "N_MS"), ("NF", "N_FS")
    OMP, OFP = ("NM", "N_MP"), ("NF", "N_FP")
    PO = [("PM", "NProp_M"), ("PF", "NProp_F")]
    det = {"MS": ["todo", "cada", "algún", "un", "ningún"], "FS": ["toda", "cada", "alguna", "una", "ninguna"],
           "MP": ["todos los", "algunos", "los", "dos", "tres"], "FP": ["todas las", "algunas", "las", "dos", "tres"]}[g + n]
    cop = "es" if n == "S" else "son"
    out = []
    for d in det:
        out += [[d, N, VIx], [d, N, A, VIx], [d, N, VTx, "un", OM], [d, N, VTx, "una", OF], [d, N, VTx, "a", PO[0]],
                [d, N, VTx, "a", PO[1]], [d, N, cop, A], [d, N, "que", VIx, VTx, "un", OM], [d, N, "no", VIx],
                [d, N, VTx, "a", "todos los", OMP], [d, N, VTx, "a", "todas las", OFP], [d, N, A, cop, A],
                [d, N, "que", VTx, "a", PO[0], VIx], [d, N, VIx, "y", VIx], [d, N, VIx, "o", VTx, "un", OM]]
    if n == "S":
        indef = "un" if g == "M" else "una"
        out += [[P, VIx], [P, VTx, "un", OM], [P, VTx, "una", OF], [P, VTx, "a", PO[0]], [P, VTx, "a", PO[1]],
                [P, "es", A], [P, "es", indef, N], [P, "no", VIx], [P, "no", VTx, "ningún", OM], [P, "se", VTx],
                ["si", P, VIx, ",", "entonces", PO[1], VIx], [P, VIx, "y", PO[0], VTx, "un", OM],
                ["hay", indef, N, "que", VIx], ["hay", indef, N, A], ["no", "hay", "ningún" if g == "M" else "ninguna", N, "que", VIs],
                ["no", "hay", "ningún" if g == "M" else "ninguna", N, "que", VTs, "a", PO[0]], ["solo", P, VIx],
                ["no", "es", "cierto", "que", P, VIx], [P, "es", A, "y", A]]
    else:
        out += [["solo", "los" if g == "M" else "las", N, VIx], ["hay", N, "que", VTx, "a", PO[1]],
                [P, "y", PO[1], VIx], ["al", "menos", "dos", N, VIx], ["exactamente", "tres", N, VTx, "un", OM]]
    return out


def generate(lex, rng, count):
    """Frases con huecos rellenos: lista de (palabras, [(posición, etiqueta)])."""
    sentences = []
    all_templates = [t for g in "MF" for n in "SP" for t in templates(g, n)]
    for _ in range(count):
        words, gold = [], []
        for slot in rng.choice(all_templates):
            if isinstance(slot, str):
                words.extend(slot.split())
                continue
            cls, tag = slot
            form = rng.choice(rng.choice(lex[cls])[tag])
            gold.append((len(words), tag)); words.append(form)
        if words[0][0].islower():
            words[0] = words[0].capitalize()
        sentences.append((words, gold))
    return sentences


def closed_class():
    lexicon = grammar()[0]
    open_heads = set(TAGS)
    closed = set()
    for phrase, heads in lexicon.items():
        if not heads & open_heads:
            closed.update(phrase)
    return closed | {"cierto", "menos", "sumo", "bien", "lo", "al", "del", "de", "el", "la"}


def encode(sentences, closed, index, grow):
    rows, labels = [], []
    for words, gold in sentences:
        for pos, tag in gold:
            ids = []
            for f in features(words, pos, closed):
                if f not in index and grow:
                    index[f] = len(index)
                if f in index:
                    ids.append(index[f])
            rows.append(ids); labels.append(TAGS.index(tag))
    width = max(len(r) for r in rows)
    X = np.full((len(rows), width), -1, dtype=np.int32)
    for i, r in enumerate(rows):
        X[i, :len(r)] = r
    return X, np.array(labels)


def scores(W, X):
    padded = np.vstack([W, np.zeros((1, W.shape[1]))])  # el índice -1 apunta a la fila de ceros
    return padded[X].sum(axis=1)


def accuracy(W, X, y):
    return float((scores(W, X).argmax(axis=1) == y).mean())


def train(Xtr, ytr, Xva, yva, n_feats, lr, l2, epochs, batch, seed):
    """Descenso de gradiente por lotes sobre la entropía cruzada con penalización L2."""
    rng = np.random.default_rng(seed)
    W = np.zeros((n_feats, len(TAGS)))
    best = (-1.0, 0, None)
    history = []
    for epoch in range(1, epochs + 1):
        order = rng.permutation(len(ytr))
        step = lr / (1 + 0.05 * (epoch - 1))          # tasa de aprendizaje decreciente
        for start in range(0, len(order), batch):
            rows = order[start:start + batch]
            z = scores(W, Xtr[rows]); z -= z.max(axis=1, keepdims=True)
            p = np.exp(z); p /= p.sum(axis=1, keepdims=True)
            p[np.arange(len(rows)), ytr[rows]] -= 1    # gradiente de la pérdida respecto a los puntajes
            grad = np.zeros_like(W)
            for col in range(Xtr.shape[1]):
                ids = Xtr[rows, col]; ok = ids >= 0
                np.add.at(grad, ids[ok], p[ok])
            W -= step * (grad / len(rows) + l2 * W)
        acc = accuracy(W, Xva, yva)
        history.append(acc)
        if acc > best[0]:
            best = (acc, epoch, W.copy())
    return best, history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=3032)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    lex = lexemes()
    split = {"train": {}, "val": {}, "test": {}}
    for cls, items in lex.items():
        items = items[:]; rng.shuffle(items)
        a, b = int(len(items) * .7), int(len(items) * .85)
        split["train"][cls], split["val"][cls], split["test"][cls] = items[:a], items[a:b], items[b:]
    closed = closed_class()
    index = {}
    Xtr, ytr = encode(generate(split["train"], rng, 2000 if args.quick else 9000), closed, index, True)
    Xva, yva = encode(generate(split["val"], rng, 1500), closed, index, False)
    Xte, yte = encode(generate(split["test"], rng, 1500), closed, index, False)

    grid = [(lr, l2) for lr in ((0.5,) if args.quick else (0.1, 0.5, 2.0)) for l2 in ((1e-4,) if args.quick else (0.0, 1e-4, 1e-3))]
    rows, winner = [], None
    for lr, l2 in grid:
        (acc, epoch, W), history = train(Xtr, ytr, Xva, yva, len(index), lr, l2, 6 if args.quick else 14, 64, args.seed)
        rows.append((lr, l2, epoch, acc, history[-1]))
        print(f"lr={lr:<4} l2={l2:<6} mejor época {epoch:>2}  validación {acc:.3f}")
        if winner is None or acc > winner[0]:
            winner = (acc, lr, l2, epoch, W)
    acc, lr, l2, epoch, W = winner
    test_acc = accuracy(W, Xte, yte)
    pred = scores(W, Xte).argmax(axis=1)
    coarse = lambda t: t.split("_")[0].replace("sub", "")
    coarse_acc = float(np.mean([coarse(TAGS[a]) == coarse(TAGS[b]) for a, b in zip(pred, yte)]))
    confusions = {}
    for a, b in zip(pred, yte):
        if a != b:
            confusions[(TAGS[b], TAGS[a])] = confusions.get((TAGS[b], TAGS[a]), 0) + 1

    names = sorted(index, key=index.get)
    weights = {}
    for f, row in zip(names, W):
        kept = [[j, round(float(v), 3)] for j, v in enumerate(row) if abs(v) >= 0.02]
        if kept:
            weights[f] = kept
    meta = {"seed": args.seed, "lr": lr, "l2": l2, "epochs": epoch, "train_examples": int(len(ytr)),
            "features": len(index), "val_accuracy": round(acc, 4), "test_accuracy": round(test_acc, 4),
            "test_accuracy_coarse": round(coarse_acc, 4)}
    OUT.write_text(json.dumps({"tags": list(TAGS), "meta": meta, "weights": weights}, ensure_ascii=False,
                              separators=(",", ":")), encoding="utf-8")
    print(f"\nelegido lr={lr} l2={l2} época {epoch}: validación {acc:.3f}, prueba {test_acc:.3f} "
          f"(categoría gruesa {coarse_acc:.3f}); {len(weights)} rasgos con peso")

    # ── frases de clase: prueba final de extremo a extremo ──
    from logos import LogosError, translate_spanish
    from logos.spanish_tagger import _model
    _model.cache_clear()
    class_rows = []
    if CLASS.is_file():
        for line in CLASS.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            phrase, expected = (line.split("\t") + [""])[:2]
            try:
                result = translate_spanish(phrase)
                got = [r.text for r in result.readings]
                assumed = "; ".join(f"{a['word']}→{a['tag']} ({a['probability']:.0%})" for a in result.assumptions)
                ok = expected in got if expected else bool(got)
                class_rows.append((phrase, expected, " / ".join(got), assumed, ok))
            except LogosError as exc:
                class_rows.append((phrase, expected, f"rechazada: {exc.message}", "", expected == "RECHAZA"))
    lines = ["# Etiquetador de palabras fuera del léxico", "",
             "> Documento generado por `scripts/train_spanish_tagger.py`. No se edita a mano.", "",
             "## Qué hace", "",
             "La gramática del español controlado tiene un léxico cerrado. Cuando una frase trae una palabra que no está, "
             "el etiquetador propone su categoría (sustantivo, adjetivo, verbo con o sin objeto, nombre propio, con género y número). "
             "La frase se analiza con esa propuesta por la misma gramática, y la interfaz muestra qué se supuso. "
             "El etiquetador no elige entre lecturas ni decide nada lógico.", "",
             "## Modelo y datos", "",
             f"- Regresión logística multinomial, {len(TAGS)} etiquetas, {len(index)} rasgos (terminaciones de 1 a 4 letras, mayúscula, tilde, longitud y las palabras funcionales vecinas).",
             "- Entrenada por descenso de gradiente por lotes (64) sobre la entropía cruzada, con penalización L2 y tasa de aprendizaje decreciente.",
             f"- {len(ytr)} ejemplos de entrenamiento, generados con plantillas a partir de {sum(len(v) for v in lex.values())} lemas. Las etiquetas son correctas por construcción.",
             "- **Partición por lema** (70 % / 15 % / 15 %): validación y prueba solo contienen palabras que el modelo nunca vio.",
             "- Las conversaciones de clase no se usaron para entrenar: casi no contienen frases en lenguaje natural. Sirven de prueba final (abajo).", "",
             "## Ajuste de hiperparámetros", "",
             "| Tasa de aprendizaje | L2 | Mejor época | Exactitud en validación | Exactitud en la última época |", "|---|---|---|---|---|"]
    for r in rows:
        mark = " **← elegido**" if (r[0], r[1]) == (lr, l2) else ""
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]:.3f}{mark} | {r[4]:.3f} |")
    lines += ["", "## Resultado en palabras nunca vistas", "",
              f"- Exactitud con etiqueta completa (categoría, género y número): **{test_acc:.1%}** sobre {len(yte)} palabras.",
              f"- Exactitud de la categoría gruesa (sustantivo / adjetivo / verbo con objeto / verbo sin objeto / nombre): **{coarse_acc:.1%}**.", "",
              "Confusiones más frecuentes (real → propuesta):", ""]
    for (gold, got), n in sorted(confusions.items(), key=lambda x: -x[1])[:8]:
        lines.append(f"- {gold} → {got}: {n}")
    lines += ["", "La gramática corrige parte de estos errores: una etiqueta que no concuerda con el resto de la frase no produce ningún árbol, "
              "y por eso se prueban las dos más probables.", ""]
    if class_rows:
        good = sum(1 for r in class_rows if r[4])
        lines += ["## Frases de clase (prueba de extremo a extremo)", "",
                  f"**{good} de {len(class_rows)}** dan la fórmula esperada. Las frases y sus fórmulas esperadas están en `docs/specs/espanol/frases_clase.tsv`.", "",
                  "| Frase | Esperada | Obtenida | Supuestos | Cumple |", "|---|---|---|---|---|"]
        for phrase, expected, got, assumed, ok in class_rows:
            cell = " / ".join(f"`{g}`" for g in got.split(" / ")) if not got.startswith("rechazada") else got
            lines.append(f"| {phrase} | {'`' + expected + '`' if expected and expected != 'RECHAZA' else expected} | {cell} | {assumed} | {'sí' if ok else '**no**'} |")
        lines.append("")
    lines += ["## Límites", "",
              "- Distingue verbo con objeto de verbo sin objeto sobre todo por lo que sigue; al final de frase la forma no basta.",
              "- El nombre del predicado es un lema aproximado sin tildes (`perros` → `Perro`, `ladran` → `Ladrar`); con verbos irregulares puede no coincidir entre formas.",
              "- El diccionario base lo generó un modelo de lenguaje y no tiene revisión humana.",
              "- Estas cifras miden palabras que **no** están en el diccionario; las que sí están no pasan por el etiquetador.", "",
              "## Cómo repetir", "", "```bash", "PYTHONPATH=src python3 scripts/train_spanish_tagger.py", "```", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{REPORT.relative_to(ROOT)} escrito")


if __name__ == "__main__":
    main()
