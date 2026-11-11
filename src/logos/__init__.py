"""LOGOS: lexer, parser, AST y semántica finita de lógica de primer orden."""
from .ast import (
    And, Bottom, Const, Eq, Exists, Forall, Formula, Func, Iff, Implies, Not, Or, Pred,
    Span, Term, Var,
)
from .errors import LogosError
from .spanish import SpanishReading, SpanishResult, translate_spanish
from .story import Story, StoryEvent, build_story
from .proof_story import ProofNarration, build_proof_narration
from .countermodels import CountermodelConfig, CountermodelSearch, find_countermodel
from .explain import Explanation, explain
from .model import FiniteModel
from .interpretation import build_interpretation
from .project import Resultado, evaluar, libres
from .parser import parse, parse_term
from .printer import to_string
from .propositional import PropVerdict, decide, is_propositional, kalmar_sequent, truth_table
from .semantics import Trace, check_trace, eval_term, evaluate, holds, is_countermodel, is_true
from .symbols import Signature, check, parse_checked
from .transform import (
    alpha_equiv, alpha_rename, bound_vars, free_vars, is_closed,
    rename_bound_canonical, substitute,
)

__all__ = [
    "And", "Bottom", "Const", "Eq", "Exists", "Forall", "Formula", "Func", "Iff", "Implies",
    "Not", "Or", "Pred", "Span", "Term", "Var", "LogosError", "parse", "parse_term",
    "to_string", "Signature", "check", "parse_checked", "alpha_equiv", "alpha_rename",
    "FiniteModel", "build_interpretation", "Resultado", "evaluar", "libres", "CountermodelConfig", "CountermodelSearch", "find_countermodel", "SpanishReading", "SpanishResult", "translate_spanish", "Story", "StoryEvent", "build_story", "ProofNarration", "build_proof_narration", "Explanation", "explain", "Trace", "check_trace", "eval_term", "evaluate", "holds",
    "is_countermodel", "is_true",
    "PropVerdict", "decide", "is_propositional", "kalmar_sequent", "truth_table",
    "bound_vars", "free_vars", "is_closed", "rename_bound_canonical", "substitute",
]
