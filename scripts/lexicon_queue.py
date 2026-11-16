#!/usr/bin/env python3
"""Cola de palabras candidatas para el diccionario (un archivo de texto que hace de búfer).

    PYTHONPATH=src python3 scripts/lexicon_queue.py mine texto.txt     # mete en la cola las palabras que no están
    PYTHONPATH=src python3 scripts/lexicon_queue.py push gato perro    # mete palabras sueltas
    PYTHONPATH=src python3 scripts/lexicon_queue.py status
    PYTHONPATH=src python3 scripts/lexicon_queue.py next -n 30         # saca las 30 primeras con la propuesta del modelo
    PYTHONPATH=src python3 scripts/lexicon_queue.py accept datos/propuestas.tsv [--base]
    PYTHONPATH=src python3 scripts/lexicon_queue.py discard palabra…

La cola (`datos/cola_lexico.txt`) guarda `palabra<TAB>veces<TAB>origen`, en orden de llegada. `next` no borra nada:
escribe `datos/propuestas.tsv` con lo que el modelo cree de cada palabra para que alguien lo revise y corrija.
`accept` añade las filas revisadas al diccionario (al del usuario, o al base con `--base`) y las saca de la cola.
La cola y las propuestas viven en `datos/`, que no se sube al repositorio: pueden salir de textos personales.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from logos import LogosError, lexicon  # noqa: E402
from logos import spanish_tagger as tagger  # noqa: E402
from logos.spanish_cyk import grammar  # noqa: E402

QUEUE = ROOT / "datos" / "cola_lexico.txt"
PROPOSALS = ROOT / "datos" / "propuestas.tsv"
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
# palabras funcionales y formas de «ser/estar/haber»: no son entradas de diccionario
STOP = set("""a al algo algunas algunos ante antes aquel aquella aquello aquí así aun aunque bajo bien cada casi como con
contra cual cuales cualquier cuando cuanto de del desde donde dos durante e el ella ellas ello ellos en entre era eran eres
es esa esas ese eso esos esta estaba estaban estamos están estar estas este esto estos estoy fue fueron ha había habían han
hasta hay la las le les lo los más me mi mis mismo mucho muy nada ni no nos nosotros o otra otras otro otros para pero poco
por porque pues que qué quien quienes se sea sean según ser si sí sido sin sino sobre solo somos son soy su sus también
tan tanto te tengo ti tiene toda todas todo todos tras tu tus un una unas uno unos usted ustedes va y ya yo él ésta
entonces luego además mientras siempre nunca ahora hoy ayer mañana aquí allí cómo cuál dónde cuándo tres cuatro cinco
the of and to in is for that with this""".split())


def read_queue():
    rows = []
    if QUEUE.is_file():
        for line in QUEUE.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                word, count, origin = (line.split("\t") + ["1", ""])[:3]
                rows.append([word, int(count) if count.isdigit() else 1, origin])
    return rows


def write_queue(rows):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    head = "# Cola de palabras candidatas para el diccionario: palabra, veces vista, origen. No se sube al repositorio.\n"
    QUEUE.write_text(head + "".join(f"{w}\t{c}\t{o}\n" for w, c, o in rows), encoding="utf-8")


def known_forms():
    forms = {w for phrase in grammar()[0] for w in phrase}
    lemmas = {e.lemma.casefold() for e in lexicon.entries()}      # los infinitivos no son formas de la gramática
    return forms | lemmas | STOP


def not_a_dictionary_word(word):
    """Formas que el diccionario no guarda: adverbios en -mente, gerundios y verbos en 1ª o 2ª persona."""
    if word.endswith("mente") and len(word) > 7:
        return "adverbio"
    if word.endswith(("ando", "iendo", "yendo")) and len(word) > 6:
        return "gerundio"
    if word.endswith(("amos", "emos", "imos", "aste", "iste", "áis", "éis")) and len(word) > 5:
        return "verbo en otra persona"
    return None


def enqueue(words, origin):
    rows = read_queue()
    position = {r[0]: r for r in rows}
    known = known_forms()
    added = 0
    for raw in words:
        word = raw.casefold()
        if len(word) < 3 or word in known or not word.isalpha() or not_a_dictionary_word(word):
            continue
        if word in position:
            position[word][1] += 1
        else:
            row = [word, 1, origin]; rows.append(row); position[word] = row; added += 1
    write_queue(rows)
    return added, len(rows)


def propose(word):
    """Fila de propuesta para una palabra: lema, categoría, género/uso, confianza.

    Primero reglas de terminación que el modelo no ve (está entrenado con formas conjugadas dentro
    de frases); el modelo solo opina cuando ninguna regla aplica. El lema conserva las tildes.
    """
    for tail, lemma_tail in (("ciones", "ción"), ("siones", "sión"), ("dades", "dad"), ("tudes", "tud")):
        if word.endswith(tail):
            return word[:-len(tail)] + lemma_tail, "N", "F", 0.9
    if word.endswith(("ción", "sión", "dad", "tad", "tud", "eza", "encia", "ancia")):
        return word, "N", "F", 0.9
    if word.endswith(("ar", "er", "ir")) and len(word) > 4 and not word.endswith(("ular", "iliar", "olar")):
        return word, "V", "T", 0.6           # infinitivo: el uso (con o sin objeto) hay que revisarlo
    tag, probability = tagger.probabilities([word], 0, frozenset())[0]
    kind, _, form = tag.partition("_")
    category = {"N": "N", "Adj": "ADJ", "NProp": "NP"}.get(kind, "V")
    feature = form[0] if category == "N" else form if category == "NP" else ("T" if "VT" in kind else "I") if category == "V" else "-"
    lemma = tagger.guess_predicate(word, tag).lower()
    if lexicon.plain(lemma) == lexicon.plain(word):
        lemma = word                         # mismo lema: se respeta la escritura con tildes
    return lemma, category, feature, probability


def cmd_mine(args):
    text = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
    # una palabra con mayúscula en mitad de frase suele ser nombre propio: se deja pasar tal cual para revisarla
    added, total = enqueue(WORD.findall(text), args.origin or Path(args.file).name)
    print(f"{added} palabras nuevas en la cola; {total} pendientes")


def cmd_push(args):
    added, total = enqueue(args.words, args.origin or "manual")
    print(f"{added} palabras nuevas en la cola; {total} pendientes")


def cmd_status(_):
    rows = read_queue()
    print(f"{len(rows)} palabras pendientes en {QUEUE.relative_to(ROOT)}")
    for word, count, origin in sorted(rows, key=lambda r: -r[1])[:15]:
        print(f"  {word:<18} ×{count}  {origin}")
    print("diccionario:", lexicon.counts())


def cmd_next(args):
    rows = read_queue()[: args.n]
    lines = ["# Propuestas del modelo para revisar. Corrige lema, categoría (N ADJ V NP), género/uso y extra;",
             "# borra las filas que no quieras. Después: lexicon_queue.py accept datos/propuestas.tsv",
             "# lema\tcategoría\tgénero/uso\textra\tpalabra en la cola\tconfianza"]
    for word, _, _ in rows:
        lemma, category, feature, p = propose(word)
        lines.append(f"{lemma}\t{category}\t{feature}\t\t{word}\t{p:.0%}")
    PROPOSALS.parent.mkdir(parents=True, exist_ok=True)
    PROPOSALS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[3:]))
    print(f"\n{len(rows)} propuestas en {PROPOSALS.relative_to(ROOT)}")


def cmd_accept(args):
    done, failed = set(), 0
    base_lines, fresh = [], set()
    for line in Path(args.file).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        lemma, category, feature, extra, source = (line.split("\t") + ["", "", "", ""])[:5]
        try:
            if args.base:
                entry = lexicon._validate(lemma, category, feature or "-", extra)
                key = (entry.lemma.casefold(), entry.category, entry.feature, entry.symbol)
                if key in fresh or any((e.lemma.casefold(), e.category, e.feature, e.symbol) == key for e in lexicon.entries()):
                    raise LogosError("semantic", "duplicate_lexicon", "ya está")
                fresh.add(key)
                base_lines.append("\t".join((entry.lemma, entry.category, entry.feature, entry.extra)))
            else:
                lexicon.add(lemma, category, feature or "-", extra)
            done.add((source or lemma).casefold())
        except LogosError as exc:
            failed += 1
            done.add((source or lemma).casefold()) if exc.code == "duplicate_lexicon" else None
            print(f"  no se añadió «{lemma}»: {exc.message}")
    if base_lines:
        with lexicon.BASE.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(base_lines) + "\n")
        lexicon.reload()
    write_queue([r for r in read_queue() if r[0] not in done])
    print(f"{len(base_lines) if args.base else len(done) - failed} añadidas, {failed} rechazadas; {len(read_queue())} siguen en la cola")


def cmd_discard(args):
    drop = {w.casefold() for w in args.words}
    rows = [r for r in read_queue() if r[0] not in drop]
    write_queue(rows)
    print(f"{len(rows)} pendientes")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("mine"); s.add_argument("file"); s.add_argument("--origin"); s.set_defaults(fn=cmd_mine)
    s = sub.add_parser("push"); s.add_argument("words", nargs="+"); s.add_argument("--origin"); s.set_defaults(fn=cmd_push)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("next"); s.add_argument("-n", type=int, default=30); s.set_defaults(fn=cmd_next)
    s = sub.add_parser("accept"); s.add_argument("file"); s.add_argument("--base", action="store_true"); s.set_defaults(fn=cmd_accept)
    s = sub.add_parser("discard"); s.add_argument("words", nargs="+"); s.set_defaults(fn=cmd_discard)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
