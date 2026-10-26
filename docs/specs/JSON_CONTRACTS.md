# Contratos JSON de LOGOS (versión 1)

> Estado: borrador de Fase 0. Los contratos marcados **[implementado]** tienen código y pruebas; los marcados **[definido]** fijan el formato pero se implementan en su fase. `schema_version` actual: `"1"`. Un consumidor debe rechazar cualquier otra versión.

## Principios

- Todo objeto raíz lleva `schema_version`.
- Las fórmulas se serializan en **texto canónico** (`printer.to_string`) o como **árbol con ids estables**; nunca ambas sin comprobar que coinciden.
- Los ids de pasos son enteros `1..n` consecutivos. Los ids de nodos de fórmula son rutas desde la raíz (`"0"`, `"0.1"`, `"0.1.0"`), deterministas.
- Los **offsets** son índices de caracteres (code points) sobre el texto original.
- Los consumidores deben ignorar campos desconocidos solo dentro de la misma `schema_version`; un cambio incompatible sube la versión.

## 1. `Diagnostic` **[implementado]**

Todo error de entrada, de modelo o de certificado.

```json
{"schema_version": "1", "status": "invalid_input", "stage": "syntactic",
 "code": "unclosed_paren", "message": "paréntesis sin cerrar",
 "span": [0, 1], "line": 1, "column": 1}
```

`stage ∈ {lexical, syntactic, semantic, proof}`. `span`, `line`, `column` pueden faltar o ser `null`. Los errores de certificado añaden `"step": <id | null>`.

Códigos estables:

| stage | códigos |
|---|---|
| lexical | `unexpected_char`, `caseless_identifier` |
| syntactic | `expected_formula`, `expected_term`, `expected_variable`, `unexpected_token`, `unmatched_paren`, `unclosed_paren`, `non_associative` |
| semantic | `quantified_constant`, `letter_collision`, `arity_mismatch`, `undeclared_symbol`, `symbol_kind_clash`, `invalid_model`, `missing_interpretation`, `model_arity_mismatch`, `unassigned_variable`, `invalid_assignment`, `invalid_trace`, `invalid_ast`, `not_propositional`, `too_many_atoms`, `not_a_consequence` |
| proof | `invalid_certificate`, `empty`, `bad_ids`, `unknown_rule`, `bad_refs`, `bad_params`, `malformed_step`, `wrong_shape`, `formula_mismatch`, `rule_violation`, `context_mismatch`, `eigenvariable`, `wrong_conclusion`, `open_assumption` |

## 2. `FormulaAST` **[implementado]** (`serialize.formula_to_dict` / `formula_from_dict`)

```json
{"schema_version": "1", "text": "∀x P(x)",
 "tree": {"id": "0", "kind": "forall", "var": "x", "span": [0, 7],
          "body": {"id": "0.0", "kind": "pred", "name": "P",
                   "args": [{"id": "0.0.0", "kind": "var", "name": "x"}]}}}
```

| `kind` | campos |
|---|---|
| `var`, `const` | `name` |
| `func`, `pred` | `name`, `args` (lista de nodos) |
| `bottom` | — |
| `eq` | `left`, `right` |
| `not` | `operand` |
| `and`, `or`, `implies`, `iff` | `left`, `right` |
| `forall`, `exists` | `var`, `body` |

`span` es opcional (solo si el árbol vino de texto). Al cargar se **reconstruye y valida**: id inconsistente, `kind` desconocido, nombre inválido, o `text` que no coincide con el árbol dan `invalid_ast`.

## 3. `FiniteModel` **[implementado]**

```json
{"schema_version": "1", "domain": [1, 2], "constants": {"a": 1},
 "functions": {"f": {"arity": 1, "table": [[[1], 2], [[2], 1]]}},
 "predicates": {"R": {"arity": 2, "tuples": [[1, 2], [2, 1]]}, "S": {"arity": 0, "tuples": []}}}
```

Dominio no vacío de `int` o `str` sin repetir; tablas de funciones **totales**; aridad 0 de predicado: `[[]]` (verdadero) o `[]` (falso). Orden canónico: dominio en su orden, símbolos por nombre, tablas y tuplas por posición en el dominio.

## 4. `ProofStep` y `ProofCertificate` **[implementado]**

```json
{"schema_version": "1", "constants": ["a"],
 "premises": ["∀x (P(x) → Q(x))", "P(a)"], "conclusion": "Q(a)",
 "steps": [
   {"id": 1, "formula": "∀x (P(x) → Q(x))", "context": ["∀x (P(x) → Q(x))"], "rule": "assume", "refs": [], "params": {}},
   {"id": 2, "formula": "P(a) → Q(a)", "context": ["∀x (P(x) → Q(x))"], "rule": "all_e", "refs": [1], "params": {"term": "a"}}
 ]}
```

- `constants` fija qué identificadores sin paréntesis se leen como constantes al reconstruir (regla D-2).
- `rule` ∈ las 22 reglas de `PROOF_CALCULUS.md`.
- `params`: `var` (nombre), `term` (texto de término), `template` (texto de fórmula). Cada regla admite **exactamente** los suyos.
- `context` es declarativo: el checker lo **recalcula** y exige coincidencia.

## 5. `Countermodel` **[definido; se implementa en Fase 4]**

```json
{"schema_version": "1",
 "model": { "...FiniteModel..." },
 "assignment": {"x": 1},
 "premises": [{"formula": "∀x (P(x) → Q(x))", "value": true}],
 "conclusion": {"formula": "∀x (Q(x) → P(x))", "value": false},
 "search": {"explored_sizes": [1, 2], "max_size": 3, "minimal_in_explored": true}}
```

`value` lo calcula el evaluador, no el buscador. `search` separa «no se encontró hasta tamaño N» de «válido en toda FOL»: **un contramodelo refuta; su ausencia no prueba**. `minimal_in_explored` significa mínimo en cardinalidad del dominio dentro de lo explorado, nada más.

## 6. `ExplanationEvent` **[definido; se implementa en Fase 7]**

```json
{"schema_version": "1", "id": 7, "step_ref": 4, "kind": "apply_rule",
 "rule": "imp_e", "text_es": "Como P(a) y P(a)→Q(a), concluimos Q(a).",
 "highlight": ["0.0", "0.1"], "verified_by": {"certificate_step": 4}}
```

Cada evento narrado cita un paso verificado (`verified_by`) o una evaluación verificable. Un evento sin respaldo se rechaza al construir. `text_es` sale de plantillas deterministas; ningún TTS ni LLM agrega contenido matemático.

## 7. Sobre de resultado **[implementado]** (`result_to_dict`)

```json
{"schema_version": "1", "status": "proved", "method": "kalmar",
 "certificate": { "...ProofCertificate..." }}
```

| `status` | Campos presentes | Garantía |
|---|---|---|
| `proved` | `certificate` | El checker lo aceptó |
| `counterexample` | `countermodel` | El evaluador lo confirmó |
| `inconsistent` | `certificate` (conclusión `⊥`) | El checker lo aceptó |
| `unknown` | `reason` (`depth`, `budget`, `checker_rejected`, `too_many_atoms`) | **No** significa falso |
| `invalid_input` | `diagnostic` | Error localizado |

`method` ∈ `search`, `kalmar` (quién produjo el certificado) y `nodes` (nodos explorados) son opcionales y solo informativos.
