"""Banco fijo y tutor de deducción natural; el checker verifica cada prefijo.

El cliente solo envía fórmulas, reglas y referencias. Los contextos se calculan
aquí y nunca se aceptan del navegador. Una hipótesis abierta no gana una misión.
"""
from __future__ import annotations

from .ast import (And, Bottom, Const, Eq, Exists, Forall, Func, Iff, Implies,
                  Not, Or, Pred, Var, is_term_name)
from .errors import LogosError
from .parser import parse, parse_term
from .practice_bank import CATEGORIES, EXERCISES, step
from .printer import to_string
from .proof.certificate import ProofCertificate, ProofError, ProofStep
from .proof.checker import _apply, verify
from .symbols import Signature, check
from .transform import alpha_equiv


# label, explanation, number of ordered references, additional parameters
RULES = {
    "and_e1": ("∧E₁ · Extraer izquierda", "De A ∧ B obtienes A.", 1, []),
    "and_e2": ("∧E₂ · Extraer derecha", "De A ∧ B obtienes B.", 1, []),
    "and_i": ("∧I · Unir", "De A y B, en ese orden, obtienes A ∧ B.", 2, []),
    "imp_e": ("→E · Aplicar implicación", "Cita primero A → B y después A para obtener B.", 2, []),
    "assume": ("Hipótesis · Suponer", "Introduce una hipótesis temporal. Debes descargarla antes de terminar, salvo que sea una premisa.", 0, []),
    "imp_i": ("→I · Demostrar implicación", "Cita una línea B que depende de A y escribe A → B. Se descarga la hipótesis A.", 1, []),
    "not_e": ("¬E · Obtener contradicción", "Cita primero A y después ¬A para obtener ⊥.", 2, []),
    "not_i": ("¬I · Demostrar negación", "De una contradicción que depende de A concluyes ¬A, descargando A.", 1, []),
    "or_e": ("∨E · Resolver por casos", "Cita A ∨ B, una conclusión C bajo A, y la misma C bajo B. Se descargan A y B.", 3, []),
    "or_i1": ("∨I₁ · Añadir alternativa derecha", "De A obtienes A ∨ B.", 1, []),
    "or_i2": ("∨I₂ · Añadir alternativa izquierda", "De B obtienes A ∨ B.", 1, []),
    "all_e": ("∀E · Particularizar", "De ∀x A(x), elige un término t y obtén A(t).", 1, ["term"]),
    "ex_i": ("∃I · Presentar testigo", "De A(t) obtienes ∃x A(x). Indica el término t que usaste como testigo.", 1, ["term"]),
    "eq_e": ("=E · Sustituir iguales", "Cita primero s = t y después A(s). Escribe A(t), e indica la plantilla A(x) y su variable x.", 2, ["var", "template"]),
    "eq_i": ("=I · Reflexividad", "Todo término es igual a sí mismo: t = t. Indica el término t.", 0, ["term"]),
    "all_i": ("∀I · Generalizar", "De A(y) obtienes ∀x A(x), si y no es libre en las hipótesis de las que depende la línea ni en la conclusión.", 1, ["var"]),
    "ex_e": ("∃E · Usar testigo nuevo", "Cita ∃x A(x) y una conclusión C bajo A(y). La variable nueva y no puede escapar en C ni en las otras hipótesis.", 2, ["var"]),
    "bot_e": ("⊥E · Desde contradicción", "De ⊥ puedes obtener cualquier fórmula.", 1, []),
    "raa": ("RAA · Reducción al absurdo", "De una contradicción bajo ¬A concluyes A y descargas ¬A.", 1, []),
    "iff_i": ("↔I · Equivalencia", "Cita A → B y B → A para obtener A ↔ B.", 2, []),
    "iff_e1": ("↔E₁ · Hacia la derecha", "Cita A ↔ B y A para obtener B.", 2, []),
    "iff_e2": ("↔E₂ · Hacia la izquierda", "Cita A ↔ B y B para obtener A.", 2, []),
}


def _bad(message):
    raise ProofError("practice_input", message)


def _text(value, label="expresión", empty=False):
    if not isinstance(value, str) or len(value) > 500 or (not empty and not value.strip()):
        _bad(f"La {label} debe ser texto de entre 1 y 500 caracteres.")
    if value.count("(") > 60 or value.count("¬") > 60:
        _bad("La expresión es demasiado profunda para este ejercicio.")
    return value.strip()


def term_reading(t):
    if isinstance(t, (Var, Const)):
        return "cero" if t.name == "cero" else t.name
    args = [term_reading(a) for a in t.args]
    if t.name == "s":
        return f"el sucesor de ({args[0]})"
    if t.name == "suma":
        return f"la suma de ({args[0]}) y ({args[1]})"
    return f"{t.name} aplicado a ({', '.join(args)})"


def reading(f):
    """Lectura composicional: los paréntesis preservan el alcance, sin LLM."""
    if isinstance(f, Pred):
        return f"Se cumple {f.name}" if not f.args else f"Se cumple {f.name} para ({', '.join(term_reading(a) for a in f.args)})"
    if isinstance(f, Eq):
        return f"({term_reading(f.left)}) es igual a ({term_reading(f.right)})"
    if isinstance(f, Bottom):
        return "Contradicción"
    if isinstance(f, Not):
        return f"No es cierto que ({reading(f.operand)})"
    if isinstance(f, (Forall, Exists)):
        prefix = f"Para todo {f.var}" if isinstance(f, Forall) else f"Existe un {f.var} tal que"
        return f"{prefix}: ({reading(f.body)})"
    a, b = reading(f.left), reading(f.right)
    if isinstance(f, Implies):
        return f"Si ({a}), entonces ({b})"
    connector = "y" if isinstance(f, And) else "o, o ambos" if isinstance(f, Or) else "si y solo si"
    return f"({a}) {connector} ({b})"


def _signature(ex):
    sig = Signature(constants=ex["constants"])
    for text in [*ex["premises"], ex["goal"]]:
        sig = check(parse(text, ex["constants"]), sig)
    return sig


def _formula(text, ex):
    f = parse(_text(text), ex["constants"])
    check(f, _signature(ex), strict=True)
    return f


def _payload(f):
    return {"formula": to_string(f), "reading": reading(f)}


def build(ex, moves):
    """Valida toda la prueba; no requiere que coincida con la solución de referencia."""
    if not isinstance(moves, list) or len(moves) > 100:
        _bad("La demostración admite como máximo 100 pasos propios.")
    premises = tuple(_formula(p, ex) for p in ex["premises"])
    steps = [ProofStep(i, p, (p,), "assume") for i, p in enumerate(premises, 1)]
    for move in moves:
        if not isinstance(move, dict):
            _bad("Cada paso debe ser un objeto.")
        rule, refs, raw_params = move.get("rule"), move.get("refs", []), move.get("params", {})
        if not isinstance(rule, str) or rule not in RULES:
            _bad("Selecciona una regla de inferencia válida.")
        if not isinstance(refs, list) or len(refs) != RULES[rule][2] or any(
                not isinstance(r, int) or isinstance(r, bool) or not 1 <= r <= len(steps) for r in refs):
            _bad(f"Esta regla necesita {RULES[rule][2]} referencia(s) a líneas anteriores, en el orden indicado.")
        if not isinstance(raw_params, dict) or set(raw_params) != set(RULES[rule][3]):
            _bad("Completa exactamente los parámetros que pide la regla.")
        params = {}
        for key, value in raw_params.items():
            value = _text(value, key)
            if key == "var":
                if not is_term_name(value) or value in ex["constants"]:
                    _bad("La variable debe comenzar en minúscula y no ser una constante del ejercicio.")
                params[key] = value
            elif key == "term":
                params[key] = parse_term(value, ex["constants"])
                check(Eq(params[key], params[key]), _signature(ex), strict=True)
            else:
                params[key] = _formula(value, ex)
        draft = ProofStep(len(steps) + 1, _formula(move.get("formula"), ex), (), rule, tuple(refs), params)
        context = _apply(draft, [steps[r - 1].formula for r in refs], [steps[r - 1].context for r in refs])
        steps.append(ProofStep(draft.id, draft.formula, context, rule, draft.refs, params))
    if steps:
        # El checker completo vuelve a comprobar reglas, referencias y contextos.
        verify(ProofCertificate(steps[-1].context, steps[-1].formula, tuple(steps)))
    goal = _formula(ex["goal"], ex)
    complete = bool(steps and alpha_equiv(steps[-1].formula, goal) and all(
        any(alpha_equiv(h, p) for p in premises) for h in steps[-1].context))
    if complete:
        verify(ProofCertificate(premises, goal, tuple(steps)))
    lines = []
    for s in steps:
        pending = [h for h in s.context if not any(alpha_equiv(h, p) for p in premises)]
        lines.append({"n": s.id, **_payload(s.formula), "rule": s.rule,
                      "label": "Premisa" if s.id <= len(premises) else RULES[s.rule][0],
                      "refs": list(s.refs), "pending": [_payload(h) for h in pending],
                      "premise": s.id <= len(premises)})
    at_goal = bool(steps and alpha_equiv(steps[-1].formula, goal))
    return {"lines": lines, "complete": complete, "open_goal": at_goal and not complete}


def catalog():
    result = []
    for ex in EXERCISES:
        result.append({k: v for k, v in ex.items() if k not in ("solution", "hints", "premises", "goal")}
                      | {"premises": [_payload(_formula(p, ex)) for p in ex["premises"]],
                         "goal": _payload(_formula(ex["goal"], ex)),
                         "hint_count": len(ex["hints"])})
    rules = {key: dict(label=v[0], help=v[1], refs=v[2], params=v[3]) for key, v in RULES.items()}
    return {"exercises": result, "rules": rules, "categories": CATEGORIES,
            "total": len(EXERCISES), "version": 2}


def api(action, data):
    if action == "catalog":
        return catalog()
    ex = next((e for e in EXERCISES if e["id"] == data.get("exercise")), None)
    if ex is None:
        _bad("El ejercicio no existe.")
    if action == "preview":
        text = _text(data.get("formula", ""), empty=True)
        if not text:
            return {"valid": False, "reading": "La lectura en español aparecerá aquí mientras escribes."}
        try:
            return {"valid": True, **_payload(_formula(text, ex))}
        except LogosError as exc:
            return {"valid": False, "reading": "Expresión en construcción", "message": exc.message}
    if action == "check":
        return build(ex, data.get("moves", []))
    if action == "hint":
        index = data.get("index", 0)
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(ex["hints"]):
            _bad("La pista no existe.")
        return {"hint": ex["hints"][index]}
    if action == "solution":
        return build(ex, ex["solution"])
    _bad("Acción de práctica desconocida.")
