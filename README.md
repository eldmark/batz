# LOGOS

Laboratorio de lógica de primer orden. Plan vigente del proyecto MM3032 (evaluador semántico): `docs/plans/PLAN_MM3032.md`. Fases originales en `docs/`.

## Fases 1 a 3: compilador, semántica finita y pruebas (`src/logos/`)

```
PYTHONPATH=src:tests python3 -m unittest discover -s tests
```

Solo librería estándar de Python (≥ 3.10). Sintaxis y símbolos: `docs/specs/FORMAL_LANGUAGE.md`. Semántica: `docs/specs/SEMANTICS.md`. Cálculo de pruebas: `docs/specs/PROOF_CALCULUS.md`. Contratos JSON: `docs/specs/JSON_CONTRACTS.md`. Arquitectura, plan y decisiones: `docs/architecture/`, `docs/plans/`, `docs/decisions/`.

```python
from logos import parse, to_string, substitute, Var
f = parse("∀x (P(x) → Q(x))")
to_string(f, ascii=True)   # 'forall x (P(x) -> Q(x))'
from logos import FiniteModel, is_true, evaluate
m = FiniteModel(["a"], predicates={"P": (1, []), "Q": (1, [("a",)])})
is_true(m, parse("∀x (Q(x) → P(x))"))   # False: contramodelo de la conversa
```

```python
from logos.proof import prove_text, format_certificate
r = prove_text(["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", constants=["a"])
r.status                          # 'proved' (solo si el checker aceptó el certificado)
print(format_certificate(r.certificate))
```

El buscador (`proof/search.py`) es incompleto: devuelve `unknown` (nunca "falso") al agotar profundidad, nodos o tiempo. El checker (`proof/checker.py`) no depende del buscador.

Lógica proposicional (siempre hay veredicto: prueba o contramodelo verificado):

```python
from logos import decide, parse
v = decide([parse("p → q", propositional=True)], parse("¬q → ¬p", propositional=True))
v.status, v.method                # ('proved', 'search'); el respaldo completo es 'kalmar'
```
