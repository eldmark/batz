"""CYK con cierre unario sobre gramática solo binarizada (sin eliminar unitarias)."""
import sys
sys.path.insert(0, "/home/dmark123/Documents/homework/teoria_de_compu/proyecto_2-tdlc/src")
from proyecto_2_tdlc.parser import parse_grammar_text
from proyecto_2_tdlc.grammar import Grammar, to_cnf
from proyecto_2_tdlc.cyk import ParseNode
import re
def tok(s):
    s = s.lower().replace(",", " , ")
    s = re.sub(r"\bal\b(?! menos\b)", "a el", s); s = re.sub(r"\bdel\b", "de el", s)
    return [t.strip(".¿?¡!") for t in s.split() if t.strip(".¿?¡!")]

g, _ = to_cnf(Grammar.from_dict(parse_grammar_text(open(sys.argv[1]).read())))
lex, bins, uns = {}, {}, {}
for h, alts in g.productions.items():
    for p in alts:
        if len(p) == 2: bins.setdefault(p, set()).add(h)
        elif p[0] in g.productions: uns.setdefault(p[0], set()).add(h)
        else: lex.setdefault(p[0], set()).add(h)

def close(cell):
    pend = list(cell)
    while pend:
        b = pend.pop()
        for h in uns.get(b, ()):
            if ("u", b) not in cell.setdefault(h, []):
                cell[h].append(("u", b)); pend.append(h)

def parse(t):
    n = len(t); T = [[{} for _ in range(n)] for _ in range(n)]
    for i, w in enumerate(t):
        for h in lex.get(w, ()): T[i][0].setdefault(h, []).append(("w",))
        close(T[i][0])
    for ln in range(2, n + 1):
        for i in range(n - ln + 1):
            c = T[i][ln - 1]
            for k in range(1, ln):
                for b in T[i][k - 1]:
                    for cc in T[i + k][ln - k - 1]:
                        for h in bins.get((b, cc), ()): c.setdefault(h, []).append(("b", k, b, cc))
            close(c)
    return T

def trees(s, i, ln, t, T):
    out = []
    for bp in T[i][ln - 1].get(s, []):
        if bp[0] == "w": out.append(ParseNode(s, (), t[i]))
        elif bp[0] == "u": out += [ParseNode(s, (x,)) for x in trees(bp[1], i, ln, t, T)]
        else:
            _, k, b, c = bp
            out += [ParseNode(s, (l, r)) for l in trees(b, i, k, t, T) for r in trees(c, i + k, ln - k, t, T)]
    return out

if __name__ == "__main__":
    for line in open(sys.argv[2]):
        if not line.strip() or line.startswith("#"): continue
        esp, frase = line.split("|", 1); t = tok(frase)
        ts = trees(g.start, 0, len(t), t, parse(t)) if t else []
        # Árboles que solo difieren en el género dan la misma fórmula: no es ambigüedad.
        d = sorted({re.sub(r"_[MF]([SP])\b", r"_\1", x.collapsed().bracketed()) for x in ts})
        ok = "OK " if str(len(d)) == esp.strip() else "XX "
        print(f"{ok}{len(d)} (esp {esp.strip()}) {frase.strip()}")
        if ok == "XX " or "-v" in sys.argv:
            for x in d: print("      ", x)
