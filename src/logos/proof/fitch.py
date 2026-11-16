"""Vista Fitch de un certificado ya verificado: una caja por cada hipótesis que se descarga.

Solo cambia la presentación. El certificado usa contextos explícitos (Γ ⊢ φ); aquí se
reordena y se renumera en líneas con cajas: cada hipótesis que una regla descarga abre una
caja (→I, ¬I, RAA, ∨E, ∃E) y la variable nueva de ∀I y ∃E queda marcada al comienzo de la
suya. Los pasos que no dependen de lo que supone una caja se escriben antes de abrirla, para
poder reutilizarlos después de cerrarla.

Cada línea cita el paso del certificado que la justifica. `check_layout` comprueba que la
disposición es fiel: toda referencia apunta a una línea o caja visible y coincide con el
paso del certificado, y cada caja empieza con lo que su regla descarga.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..ast import Not, Var
from ..printer import to_string
from ..transform import alpha_equiv, free_vars, substitute
from .checker import verify
from .render import RULE_SYMBOLS

# Reglas que descargan algo: cada una cierra una o dos cajas.
DISCHARGE = frozenset({"imp_i", "not_i", "raa", "or_e", "ex_e", "all_i"})


@dataclass
class FitchLine:
    n: int
    depth: int
    formula: object | None    # None en la línea que solo presenta la variable nueva de ∀I
    rule: str                 # premise | hyp | flag | reit | regla del certificado
    refs: tuple = ()          # números de línea, o (inicio, fin) de una caja cerrada
    step: int | None = None   # paso del certificado que justifica la línea
    steps: list = field(default_factory=list)  # todos los pasos que la línea representa
    flag: str | None = None   # variable nueva de la caja que empieza en esta línea
    box: tuple = ()           # cajas abiertas en esta línea, de fuera hacia dentro
    box_start: bool = False

    @property
    def label(self):
        names = {"premise": "Premisa", "hyp": "Hipótesis", "flag": "Variable nueva", "reit": "Reiteración"}
        return names.get(self.rule) or RULE_SYMBOLS.get(self.rule, self.rule)

    def to_dict(self, show=to_string):
        """`show` convierte una fórmula en texto (por ejemplo, con las letras como se escribieron)."""
        return {"n": self.n, "depth": self.depth,
                "formula": None if self.formula is None else show(self.formula),
                "rule": self.rule, "label": self.label,
                "refs": [f"{r[0]}–{r[1]}" if isinstance(r, tuple) else str(r) for r in self.refs],
                "step": self.step, "steps": list(self.steps), "flag": self.flag,
                "box": list(self.box), "box_start": self.box_start}


def discharged(step, steps):
    """Lo que supone cada caja que cierra `step` (None: caja de ∀I, sin hipótesis)."""
    c = step.formula
    if step.rule == "imp_i": return [c.left]
    if step.rule == "not_i": return [c.operand]
    if step.rule == "raa": return [Not(c)]
    if step.rule == "or_e":
        disjunction = steps[step.refs[0]].formula
        return [disjunction.left, disjunction.right]
    if step.rule == "ex_e":
        existential = steps[step.refs[0]].formula
        return [substitute(existential.body, {existential.var: Var(step.params["var"])})]
    if step.rule == "all_i": return [None]
    return []


class _Frame:
    def __init__(self, box_id, hyp=None):
        self.id, self.hyp = box_id, hyp
        self.hyp_line = None
        self.memo = {}   # paso del certificado → línea de esta caja que lo prueba


class _Layout:
    def __init__(self, cert):
        self.steps = {s.id: s for s in cert.steps}
        self.lines: list[FitchLine] = []
        self.frames = [_Frame(0)]
        self.next_box = 1
        self.premise_lines = []
        for premise in cert.premises:
            if not any(alpha_equiv(premise, f) for f, _ in self.premise_lines):
                self.premise_lines.append((premise, self.emit(premise, "premise").n))

    # ── líneas y cajas ──
    def emit(self, formula, rule, refs=(), step=None, flag=None):
        frame = self.frames[-1]
        line = FitchLine(len(self.lines) + 1, len(self.frames) - 1, formula, rule, tuple(refs), step,
                         [step] if step is not None else [], flag, tuple(f.id for f in self.frames[1:]))
        line.box_start = frame.id != 0 and not any(l.box and l.box[-1] == frame.id for l in self.lines)
        self.lines.append(line)
        return line

    def open_box(self, hyp=None, flag=None):
        frame = _Frame(self.next_box, hyp)
        self.next_box += 1
        self.frames.append(frame)
        if hyp is not None:
            frame.hyp_line = self.emit(hyp, "hyp", flag=flag).n
        elif flag is not None:
            self.emit(None, "flag", flag=flag)
        return frame

    def close_box(self, frame):
        self.frames.pop()
        inside = [l.n for l in self.lines if frame.id in l.box]
        return inside[0], inside[-1]

    def lookup(self, sid):
        for frame in reversed(self.frames):
            if sid in frame.memo:
                return frame.memo[sid]
        return None

    def remember(self, sid, n):
        self.frames[-1].memo[sid] = n
        line = self.lines[n - 1]
        if sid not in line.steps:
            line.steps.append(sid)

    def open_hyps(self):
        return [f for f, _ in self.premise_lines] + [fr.hyp for fr in self.frames if fr.hyp is not None]

    # ── recorrido del certificado ──
    def ancestors(self, sid):
        seen, stack = set(), [sid]
        while stack:
            s = stack.pop()
            if s not in seen:
                seen.add(s)
                stack.extend(self.steps[s].refs)
        return seen

    def hoist(self, sid, flag=None):
        """Antes de abrir una caja, escribe los antecesores que no dependen de lo que ella supone."""
        closure = self.ancestors(sid)
        fresh = {self.steps[s].params["var"] for s in closure if self.steps[s].rule in ("all_i", "ex_e")}
        if flag:
            fresh.add(flag)
        hyps = self.open_hyps()
        for s in sorted(closure):
            step = self.steps[s]
            if s == sid or step.rule == "assume":
                continue
            if all(any(alpha_equiv(c, h) for h in hyps) for c in step.context) and not free_vars(step.formula) & fresh:
                self.render(s)

    def render(self, sid):
        hit = self.lookup(sid)
        if hit is not None:
            return hit
        step = self.steps[sid]
        if step.rule == "assume":
            for frame in reversed(self.frames):
                if frame.hyp is not None and alpha_equiv(frame.hyp, step.formula):
                    self.remember(sid, frame.hyp_line)
                    return frame.hyp_line
            for formula, n in self.premise_lines:
                if alpha_equiv(formula, step.formula):
                    self.remember(sid, n)
                    return n
            raise AssertionError(f"la hipótesis del paso {sid} no está abierta")
        if step.rule in DISCHARGE:
            n = self.discharge(step)
        else:
            n = self.emit(step.formula, step.rule, [self.render(r) for r in step.refs], sid).n
        self.remember(sid, n)
        return n

    def subproof(self, premise_id, hyp=None, flag=None):
        """Caja que supone `hyp` (o marca `flag`) y termina en el paso `premise_id`."""
        self.hoist(premise_id, flag)
        frame = self.open_box(hyp, flag)
        n = self.render(premise_id)
        last = self.lines[-1]
        if last.n != n or not last.box or last.box[-1] != frame.id:
            # La conclusión de la caja ya estaba escrita: se repite dentro para cerrarla con ella.
            self.emit(self.steps[premise_id].formula, "reit", [n], premise_id)
        return self.close_box(frame)

    def discharge(self, step):
        hyps = discharged(step, self.steps)
        if step.rule == "or_e":
            first = self.render(step.refs[0])
            left = self.subproof(step.refs[1], hyp=hyps[0])
            right = self.subproof(step.refs[2], hyp=hyps[1])
            refs = [first, left, right]
        elif step.rule == "ex_e":
            first = self.render(step.refs[0])
            refs = [first, self.subproof(step.refs[1], hyp=hyps[0], flag=step.params["var"])]
        elif step.rule == "all_i":
            refs = [self.subproof(step.refs[0], flag=step.params["var"])]
        else:
            refs = [self.subproof(step.refs[0], hyp=hyps[0])]
        return self.emit(step.formula, step.rule, refs, step.id).n


def fitch_layout(cert):
    """Líneas Fitch de un certificado. Lanza `ProofError` si el certificado no se verifica."""
    verify(cert)
    layout = _Layout(cert)
    final = layout.render(cert.steps[-1].id)
    if layout.lines[-1].n != final:  # la conclusión ya estaba escrita (por ejemplo, era una premisa)
        layout.emit(cert.steps[-1].formula, "reit", [final], cert.steps[-1].id)
    return layout.lines


def check_layout(lines, cert):
    """Problemas de fidelidad de la vista Fitch frente al certificado (lista vacía si es fiel)."""
    problems = []
    steps = {s.id: s for s in cert.steps}
    by_n = {line.n: line for line in lines}

    def visible(target, at):
        return target.n < at.n and at.box[:len(target.box)] == target.box

    def closed_box(first, last, at):
        a, b = by_n.get(first), by_n.get(last)
        if a is None or b is None or not a.box or b.box[:len(a.box)] != a.box or not b.n < at.n:
            return False
        inner, parent = a.box[-1], a.box[:-1]
        members = [l.n for l in lines if inner in l.box]
        return members[0] == first and members[-1] == last and at.box[:len(parent)] == parent and inner not in at.box

    for line in lines:
        for ref in line.refs:
            if isinstance(ref, tuple):
                if not closed_box(*ref, line):
                    problems.append(f"línea {line.n}: la caja {ref[0]}–{ref[1]} no está cerrada y visible")
            elif ref not in by_n or not visible(by_n[ref], line):
                problems.append(f"línea {line.n}: la línea {ref} no es visible")
        if line.rule == "premise" and not any(alpha_equiv(line.formula, p) for p in cert.premises):
            problems.append(f"línea {line.n}: no es una premisa")
        if line.rule in ("premise", "hyp", "flag"):
            continue
        step = steps[line.step]
        if line.rule == "reit":
            if len(line.refs) != 1 or not alpha_equiv(by_n[line.refs[0]].formula, line.formula):
                problems.append(f"línea {line.n}: la reiteración no copia la línea citada")
            continue
        if step.rule != line.rule or not alpha_equiv(step.formula, line.formula):
            problems.append(f"línea {line.n}: no coincide con el paso {step.id} del certificado")
            continue
        if step.rule in DISCHARGE:
            boxes = [r for r in line.refs if isinstance(r, tuple)]
            plain = [r for r in line.refs if not isinstance(r, tuple)]
            hyps = discharged(step, steps)
            ends = [steps[r].formula for r in step.refs][-len(hyps):]
            if len(boxes) != len(hyps):
                problems.append(f"línea {line.n}: se esperaban {len(hyps)} caja(s)")
                continue
            for (first, last), hyp, end in zip(boxes, hyps, ends):
                start = by_n[first]
                if hyp is None and start.rule != "flag":
                    problems.append(f"línea {line.n}: la caja {first}–{last} debe empezar con la variable nueva")
                if hyp is not None and (start.rule != "hyp" or not alpha_equiv(start.formula, hyp)):
                    problems.append(f"línea {line.n}: la caja {first}–{last} no supone lo que la regla descarga")
                if not alpha_equiv(by_n[last].formula, end):
                    problems.append(f"línea {line.n}: la caja {first}–{last} no termina en la premisa de la regla")
            if plain and not alpha_equiv(by_n[plain[0]].formula, steps[step.refs[0]].formula):
                problems.append(f"línea {line.n}: la línea {plain[0]} no es la premisa principal de la regla")
        else:
            cited = [by_n[r].formula for r in line.refs]
            wanted = [steps[r].formula for r in step.refs]
            if len(cited) != len(wanted) or not all(alpha_equiv(a, b) for a, b in zip(cited, wanted)):
                problems.append(f"línea {line.n}: las líneas citadas no son las del paso {step.id}")
    if not lines or lines[-1].depth != 0 or lines[-1].formula is None or not alpha_equiv(lines[-1].formula, cert.conclusion):
        problems.append("la última línea no es la conclusión fuera de toda caja")
    covered = {s for line in lines for s in line.steps}
    missing = [s.id for s in cert.steps if s.id not in covered and s.rule != "assume"]
    if missing:
        problems.append(f"pasos del certificado sin línea: {missing}")
    return problems


__all__ = ["DISCHARGE", "FitchLine", "check_layout", "discharged", "fitch_layout"]
