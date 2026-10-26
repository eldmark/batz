"""Certificado de prueba (deducción natural) y su serialización canónica."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..ast import Const, Eq, Formula, Func, Pred, Term, _Binary, _Quant, Not
from ..errors import SCHEMA_VERSION, LogosError
from ..parser import parse, parse_term
from ..printer import to_string

RULES = (
    "assume", "and_i", "and_e1", "and_e2", "or_i1", "or_i2", "or_e", "imp_i", "imp_e",
    "not_i", "not_e", "bot_e", "raa", "iff_i", "iff_e1", "iff_e2",
    "all_i", "all_e", "ex_i", "ex_e", "eq_i", "eq_e",
)


class ProofError(LogosError):
    """Certificado inválido; `step` es el id del paso que falla (None si es global)."""

    def __init__(self, code, message, step=None):
        super().__init__("proof", code, message)
        self.step = step

    def to_diagnostic(self):
        d = super().to_diagnostic()
        d["step"] = self.step
        return d

    def __str__(self):
        where = "" if self.step is None else f" (paso {self.step})"
        return f"[proof:{self.code}] {self.message}{where}"


@dataclass(frozen=True)
class ProofStep:
    """`context ⊢ formula` por `rule` aplicada a los pasos `refs`.

    `params`: `var` (str), `term` (Term), `template` (Formula), según la regla.
    """

    id: int
    formula: Formula
    context: tuple
    rule: str
    refs: tuple = ()
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProofCertificate:
    premises: tuple
    conclusion: Formula
    steps: tuple

    def __post_init__(self):
        object.__setattr__(self, "premises", tuple(self.premises))
        object.__setattr__(self, "steps", tuple(self.steps))

    # --- serialización canónica -------------------------------------------
    def constants(self):
        names = set()
        for f in (*self.premises, self.conclusion):
            _consts(f, names)
        for s in self.steps:
            _consts(s.formula, names)
            for c in s.context:
                _consts(c, names)
            for p in s.params.values():
                if isinstance(p, (Term, Formula)):
                    _consts(p, names)
        return sorted(names)

    def to_dict(self):
        def step(s):
            params = {}
            for k in sorted(s.params):
                v = s.params[k]
                params[k] = v if isinstance(v, str) else to_string(v)
            return {"id": s.id, "formula": to_string(s.formula),
                    "context": [to_string(c) for c in s.context], "rule": s.rule,
                    "refs": list(s.refs), "params": params}
        return {
            "schema_version": SCHEMA_VERSION,
            "constants": self.constants(),
            "premises": [to_string(p) for p in self.premises],
            "conclusion": to_string(self.conclusion),
            "steps": [step(s) for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d):
        try:
            if d["schema_version"] != SCHEMA_VERSION:
                raise ProofError("invalid_certificate", f"schema_version no soportada: {d['schema_version']!r}")
            consts = d.get("constants", [])
            f = lambda text: parse(text, consts)
            steps = []
            for s in d["steps"]:
                params = {}
                for k, v in s.get("params", {}).items():
                    params[k] = (v if k == "var" else parse_term(v, consts) if k == "term"
                                 else f(v) if k == "template" else None)
                    if params[k] is None:
                        raise ProofError("invalid_certificate", f"parámetro desconocido {k!r}", s.get("id"))
                steps.append(ProofStep(s["id"], f(s["formula"]), tuple(f(c) for c in s["context"]),
                                       s["rule"], tuple(s["refs"]), params))
            return cls(tuple(f(p) for p in d["premises"]), f(d["conclusion"]), tuple(steps))
        except ProofError:
            raise
        except (KeyError, TypeError, ValueError, LogosError) as e:
            raise ProofError("invalid_certificate", f"certificado mal formado: {e}") from e


def _consts(node, acc):
    if isinstance(node, Const):
        acc.add(node.name)
    elif isinstance(node, (Func, Pred)):
        for a in node.args:
            _consts(a, acc)
    elif isinstance(node, Eq):
        _consts(node.left, acc)
        _consts(node.right, acc)
    elif isinstance(node, Not):
        _consts(node.operand, acc)
    elif isinstance(node, _Binary):
        _consts(node.left, acc)
        _consts(node.right, acc)
    elif isinstance(node, _Quant):
        _consts(node.body, acc)
