# Contratos JSON de Bat’z (versión 1)

> Estado: actualizado contra el código de la rama de entrega (leyendo `server.py` y los módulos, y ejecutando `handle_api` sobre casos reales). Todos los contratos de este documento están **[implementado]**. `schema_version` actual: `"1"`. Un consumidor debe rechazar cualquier otra versión. El proyecto se llamaba LOGOS antes de llamarse Bat’z; el paquete es `batz`.

Hay **dos vocabularios de resultado** que no deben mezclarse: el de `serialize.result_to_dict` (§7, sobre «de biblioteca»: `counterexample`, `diagnostic`) y el de la API local (§8: `refuted`, `errors`, `found`, `ok`).

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
| syntactic | `expected_formula`, `expected_term`, `expected_variable`, `unexpected_token`, `unmatched_paren`, `unclosed_paren`, `non_associative`, `unsupported_spanish` |
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

## 5. Contramodelo **[implementado]**

Lo producen dos búsquedas acotadas de `countermodels.py`, con dos formas de `to_dict()`. En ambas **un contramodelo refuta; su ausencia no prueba**: `status: "unknown"` nunca afirma validez universal.

### 5.1 De una sentencia: `CountermodelSearch.to_dict()` (`/api/countermodel`)

```json
{"schema_version": "1", "status": "found", "explored": 3, "completed_sizes": [1],
 "log": [{"size": 1, "explored": 1, "example": "a = 0, P = {0}, Q = {0}"}],
 "model": { "...FiniteModel..." },
 "explanation": { "formula": "∀x (Q(x) → P(x))", "value": false, "summary": "…", "span": [0, 17],
                  "details": ["…"], "assignment": [], "children": [ "..." ] },
 "story": {"schema_version": "1", "events": [ "...§6..." ]}}
```

- `status` ∈ `found`, `unknown`. Con `unknown` no hay `model`, `explanation` ni `story`; hay `reason` ∈ `size_limit`, `candidate_limit`, `timeout`, `table_limit`.
- `explored`: interpretaciones revisadas; `completed_sizes`: tamaños de dominio agotados por completo.
- `log`: bitácora por tamaño (`size`, `explored`, `example`: un candidato descartado). El avatar la narra.
- `explanation.value` es `false`: lo calcula el evaluador sobre el modelo, no el buscador. `explanation.assignment` es una lista de pares `[variable, elemento]`.
- Solo sentencias y el perfil estricto MM3032 (relaciones no vacías, aridad ≥ 1). `max_size` entre 1 y 3.
- No existen los campos `search`, `minimal_in_explored` ni `assignment` como mapa que proponía el borrador de Fase 0.

### 5.2 De una consecuencia: `ConsequenceSearch.to_dict()` (dentro de `/api/proof`)

Premisas verdaderas y conclusión falsa, con semántica estándar (admite relaciones vacías), dominios de 1 a 3 elementos.

```json
{"status": "found", "explored": 3, "completed_sizes": [0],
 "log": [ "..." ],
 "model": { "...FiniteModel..." },
 "assignment": [["x", 1]],
 "premises": [{"formula": "∀x ∃y Ama(x, y)", "value": true, "summary": "…"}],
 "explanation": { "...explicación de la conclusión, value=false..." },
 "signature": {"constants": [], "functions": {}, "predicates": {"Ama": 2}},
 "loadable": true,
 "story": {"events": [ "...eventos search, premise y de evaluación..." ]}}
```

- `assignment` es una **lista de pares** `[variable, elemento]` (no un mapa).
- `loadable` indica si cabe en las tablas del modo Evaluar (sin relaciones vacías ni aridad 0); si es `false`, la interfaz no ofrece «Abrir en Evaluar».
- `status: "unknown"`: solo `status`, `explored`, `completed_sizes`, `log` y `reason`.
- Estos objetos **no** llevan `schema_version`; lo lleva el sobre que los contiene, salvo el de `/api/countermodel`, que sí lo añade.

## 6. `ExplanationEvent` **[implementado]**

Los eventos viven en `story.events` (guion de una evaluación, de un contramodelo o de una prueba). Los construyen `story.py`, `proof_story.py` y `countermodels.py`, y los consume el reproductor (`docs/specs/EXPLANATION_PLAYER.md`). El navegador los pasa tal cual; ningún evento se inventa en el cliente.

Guion: `{"schema_version": "1", "events": [...]}`; el de una prueba añade `"kind": "proof"`.

### 6.1 Evento semántico (evaluación)

```json
{"id": 2, "trace_path": "0.0", "kind": "predicate", "formula": "P(x)", "value": true,
 "text_es": "La tupla (0) pertenece a Pᴵ.", "span": [3, 7],
 "assignment": {"x": 0}, "element": 0, "relation": "P", "term_values": [0],
 "verified_by": {"trace_path": "0.0"}}
```

`kind` ∈ `predicate`, `equality`, `quantifier`, `connective`, `bottom`. `trace_path` es la ruta del nodo en la traza que `check_trace` ya aceptó; `verified_by.trace_path` repite esa ruta. `span` apunta al texto de la fórmula original. `element` distingue `0` de «sin elemento» (`null`).

### 6.2 Evento de prueba

Los campos comunes del §6.1 (con `value: null`, `span: null`, `trace_path: "p<n>"`) más:

```json
{"id": 1, "step_id": 1, "line": 1, "kind": "proof", "rule": "premise", "rule_label": "Premisa",
 "refs": [], "context": [], "depth": 0, "steps": [1],
 "verified_by": {"certificate_step": 1}}
```

`line` es el número de línea de la vista Fitch (`fitch[].n`); `step_id` y `steps`, los pasos del certificado que la línea representa; `depth`, la profundidad de cajas.

### 6.3 Eventos de búsqueda y de premisas (contramodelos)

- `{"kind": "search", "text_es": "…", "size": 1, "phase": "start" | "found" | "none"}`: progreso de la búsqueda. No es una inferencia verificada y solo trae esos campos.
- `{"kind": "premise", "trace_path": "q0", "formula": "…", "value": true, "text_es": "La premisa … es verdadera: …", "verified_by": {"premise": 0}, …}`: comprobación de una premisa antes de la conclusión. Los eventos de la conclusión llevan además `"formula_role": "conclusion"`.

Los `id` se renumeran `1..n` al unir las tres familias. No existen `step_ref`, `apply_rule` ni `highlight`, que proponía el borrador de Fase 0. Cada evento narrado cita algo verificado (`verified_by`); `text_es` sale de plantillas deterministas.

## 7. Sobre de resultado de la biblioteca **[implementado]** (`serialize.result_to_dict`)

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

**Este sobre no es el de `/api/proof`.** El servidor construye el suyo (§8.3) con `refuted` en lugar de `counterexample` y `errors` en lugar de `diagnostic`, y con campos propios de la interfaz. `counterexample` y `diagnostic` solo salen de `serialize.result_to_dict` (usada desde Python: `prove`, `decide`).

## 8. API local **[implementado]** (`batz.server`)

Servidor `ThreadingHTTPServer`; todas las rutas son `POST` con cuerpo JSON (≤ 1 MB; ≤ 5 MB para `voice/transcribe`) y `Content-Length` obligatorio. Las respuestas JSON llevan `schema_version: "1"` y `Cache-Control: no-store`.

**Códigos HTTP.** 200 cuando `status` ∈ `ok`, `found`, `unknown`, `single`, `ambiguous`, `proved`, `refuted`; 400 cuando es `invalid_input`; 413 por cuerpo vacío o demasiado grande; 415 por `Content-Type` incorrecto en `voice/transcribe`; 503 si una voz opcional no está disponible; 404 (HTML) para rutas desconocidas.

**Errores.** `{"schema_version": "1", "status": "invalid_input", "errors": [Diagnostic, ...]}` (siempre `errors`, una lista de objetos del §1; no `diagnostic`). Los errores de voz usan `{"code", "message"}` en lugar del diagnóstico completo. Un error nunca incluye `value`, `explanation` ni certificado.

### 8.1 Evaluar en un modelo

Entrada común: `signature` = `{"constants": [..], "functions": {nombre: aridad}, "predicates": {nombre: aridad}}`.

| Ruta | Entrada | Respuesta correcta |
|---|---|---|
| `/api/free` | `signature`, `formula` | `{status:"ok", variables:[…]}` (libres, ordenadas) |
| `/api/validate` | `signature`, `interpretation` (§3) | `{status:"ok", model}` (modelo canónico) |
| `/api/evaluate` | `signature`, `interpretation`, `formula`, `assignment` (mapa variable → elemento) | `{status:"ok", value, explanation, story, tree, syntax, model}` |
| `/api/countermodel` | `signature`, `formula`, `max_size` (1–3, por omisión 3) | §5.1 |

`/api/evaluate`: `explanation` es un árbol `{formula, value, summary, span, details, assignment, children}`; `story`, los eventos de §6.1; `tree`, el árbol de evaluación del visor (`label`, `kind` ∈ `quantifier`, `atom`, `not`, `connective`; `value`, `formula`, `assignment`, `edge`, `values`, `relation`, `children`, `truncated`; y `nodes` en la raíz; se corta a unos 500 nodos); `syntax`, el árbol sintáctico (`label`, `kind`, `formula`, `children`); `model`, el modelo canónico para la vista 3D. La explicación y el guion se generan **después** de verificar la traza.

### 8.2 Lectura de modelos, fórmulas y español

| Ruta | Entrada | Respuesta correcta |
|---|---|---|
| `/api/load` | `text`: archivo `.logos` o JSON exportado | `{status:"ok", signature, model, results:[…]}`. Cada fila: `formula`, `assignment`, `line` y, o bien `status:"ok"`, `value`, `summary` (más `expected` y `matches` si el archivo declara el valor esperado), o bien `status:"invalid_input"` con `error` (un diagnóstico). Hasta 200 fórmulas. |
| `/api/parse` | `formulas` (≤ 12, ≤ 400 caracteres), `constants` | `{status:"ok", mode, results:[…]}`; `mode` ∈ `first_order`, `propositional`. Por fórmula: `{ok:true, text, free, tree}` o `{ok:false, error}`. Es la revisión de sintaxis del modo Demostrar mientras se escribe. |
| `/api/spanish` | `text` | `{status:"single"|"ambiguous", readings:[{id, formula, note, tree, signature}], assumptions:[{word, tag, label, probability, symbol}]}`. Una frase fuera del fragmento: `invalid_input` con código `unsupported_spanish`. No devuelve una lectura elegida. |

### 8.3 Demostrar: `/api/proof`

Entrada: `premises` (≤ 8 textos de ≤ 200 caracteres), `conclusion` (≤ 200), `constants` (opcional). Un `status` de nivel superior:

| `status` | Cuándo | Campos |
|---|---|---|
| `proved` | Hay certificado aceptado por el checker | `mode`, `method` (`search` o `kalmar`), `certificate` (§4), `fitch`, `story` (eventos de §6.2, `kind:"proof"`), `contrast` |
| `refuted` | Se halló un contramodelo verificado (premisas verdaderas, conclusión falsa) | Proposicional: `mode`, `valuation` (lista de pares `[letra, bool]`), `premises` y `conclusion` (`{formula, value}`), `contrast`. Primer orden: `mode`, `countermodel` (§5.2), `contrast` |
| `unknown` | Se agotaron los límites: **no** significa falso ni demostrado | `mode`, `reason` (`depth`, `budget`, `too_many_atoms`, `too_many_atoms_for_kalmar`), `nodes` y `search` (§5.2, solo primer orden), `contrast` |
| `invalid_input` | Sintaxis, aridad o letras inválidas | `errors` (lista de diagnósticos) |

- `mode` ∈ `propositional`, `first_order`. En modo proposicional (todas las fórmulas son letras como `p → q`) siempre hay veredicto salvo con más de 12 letras (`too_many_atoms`) o, para la prueba, más de 6 (`too_many_atoms_for_kalmar`: la consecuencia vale pero no se construye certificado).
- `fitch`: lista de líneas `{n, depth, formula, rule, label, refs, step, steps, flag, box, box_start}`; `refs` son texto (`"3"`, `"4–7"`). `story` ya no lleva `fitch`.
- `contrast`: `{verdict, message, engine_b}`; `engine_b` = `{status, reason, generated, kept, steps}` del motor B (resolución), con `status` ∈ `refuted` (derivó la cláusula vacía: la consecuencia vale), `saturated` (no vale), `unknown`. El motor B solo contrasta: nunca convierte `unknown` en `proved`.
- El guion de una prueba vuelve a llamar al checker antes de narrar.

### 8.4 Diccionario del español: `/api/lexicon/*`

Todas devuelven `status:"ok"` más lo siguiente; una palabra inválida da `invalid_input`.

| Ruta | Entrada | Respuesta |
|---|---|---|
| `/search` | `query`, `category` (`N`, `ADJ`, `V`, `NP`), `source` (`base`, `usuario`, …), `offset` | `total`, `offset`, `counts` (`total`, `user`, `auto`, `by_category`), `entries` (60 como máximo) |
| `/suggest` | `word` (una sola palabra, solo letras) | `word`, `found` (entradas), `proposal` (`lemma`, `category`, `feature`, `probability`, `label`) o `null` si la palabra ya está o no hay etiquetador |
| `/preview` | `lemma`, `category`, `feature`, `extra` | `entry` validada, sin guardar |
| `/add` | los mismos | `entry`, `counts`; se guarda en el archivo de léxico del usuario |
| `/remove` | `lemma`, `category` | `removed` (bool), `counts` |

Una entrada: `{lemma, category, category_label, feature, feature_label, extra, symbol, gloss, forms, source}`.

### 8.5 Cuadernos: `/api/notebook/*`

Todas devuelven `status:"ok"` más lo indicado. Un cuaderno es `{id, title, created, updated, sources, chat, symbols}`; cada fuente, `{id, title, enabled, text, sentences, counts, truncated}`, y cada oración, `{i, span, status, formula, readings?, assumptions?}` con `status` ∈ `premise`, `choose`, `rejected`.

| Acción | Entrada | Respuesta |
|---|---|---|
| `list` | — | `notebooks` (`id`, `title`, `updated`, `sources`) |
| `create`, `import` | `title` / `notebook` (paquete exportado) | `notebook` |
| `get`, `rename`, `source-add`, `source-remove`, `source-toggle`, `choose`, `clear-chat` | `id` y los campos de cada una (`title`, `text`, `source`, `enabled`, `sentence`, `formula`) | `notebook` actualizado |
| `export` | `id` | `notebook`: `{version, title, created, sources, chat}` |
| `delete` | `id` | `notebooks` |
| `ask` | `id`, `question`, `formula` (la lectura elegida), `log` | Respuesta de la pregunta (abajo) |

`ask` devuelve `question`, `statement`, `answer` y, según este, más campos:

| `answer` | Significado | Campos extra |
|---|---|---|
| `choose` | La pregunta tiene varias lecturas o supuestos: hay que elegir | `readings`, `assumptions` |
| `empty` | Sin premisas utilizables | — |
| `follows` | Hay prueba verificada de la pregunta | `conclusion`, `premise_count`, `counts`, `source_count`, `new_symbols`, `proof` (`goal`, `fitch`, `story`, `contrast`), `cited` (`n`, `formula`, `cites`), `inconsistent` |
| `contradicts` | Hay prueba verificada de lo contrario | los mismos |
| `undecided` | Ni una ni otra; hay modelo donde es falsa y otro donde es verdadera | `countermodel`, `witness`, `engine_b` y los comunes |
| `not_follows` | No se sigue (hay contramodelo o el motor B saturó) | `countermodel`, `witness` (puede ser `null`) |
| `unknown` | Se agotaron los límites: sin respuesta | los comunes |

### 8.6 Practicar: `/api/practice/*`

El ejercicio se nombra con `exercise`, una cadena (`"01"`…`"50"`). El servidor recalcula los contextos; nunca confía en marcas de éxito del cliente.

| Acción | Entrada | Respuesta |
|---|---|---|
| `catalog` | — | `exercises` (cada uno: `id`, `title`, `topic`, `rules`, `constants`, `intro`, `category`, `revision`, `premises`, `goal`, `hint_count`), `rules` (por regla: `label`, `help`, `refs`, `params`), `categories`, `total`, `version` |
| `preview` | `exercise`, `formula` | `valid` y `reading` (lectura en español), o `valid:false` con `message` |
| `check` | `exercise`, `moves` (≤ 100) | `lines` (`n`, `formula`, `reading`, `rule`, `label`, `refs`, `pending`, `premise`), `complete`, `open_goal`; una jugada inválida da `invalid_input` con el motivo en `errors` |
| `hint` | `exercise`, `index` | `hint` |
| `solution` | `exercise` | lo mismo que `check` con la solución de referencia |

### 8.7 Voz: `/api/voice/*`

| Ruta | Entrada | Respuesta |
|---|---|---|
| `/api/voice/status` | `{}` | `{status:"ok", available, engine:"whisper.cpp local", language:"es", missing:[…]}`: transcripción opcional. Nunca incluye rutas absolutas. |
| `/api/voice/transcribe` | audio crudo, `Content-Type: audio/webm` (100 B – 5 MB) | `{status:"ok", text, confirmed:false}`. El texto no se traduce solo. 503 `voice_unavailable` si falta whisper.cpp o ffmpeg. |
| `/api/voice/voices` | `{}` | `{status:"ok", available, engine:"espeak-ng"\|null, voices:[{id, label, lang}], hint}`. `hint` explica cómo instalar `espeak-ng` cuando no hay voces. |
| `/api/voice/speak` | `{text, voice, rate}` (`text` ≤ 600 caracteres, `voice` una de `voices`, `rate` 0,5–2,0) | **Audio**: `Content-Type: audio/wav`, `Cache-Control: no-store`; no es JSON. Errores como JSON `invalid_input` con `errors[0].code` ∈ `invalid_text`, `text_too_long`, `invalid_voice`, `invalid_rate`, `synthesis_failed`; 503 con `voice_unavailable`. |

### 8.8 Archivos estáticos

`GET` solo para una lista controlada de archivos (`server.do_GET`); el resto es 404. Responden con `Cache-Control: no-cache`. Los recursos nuevos deben registrarse en esa lista.
