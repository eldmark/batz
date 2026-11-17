# Arquitectura técnica de Bat’z (paquete `logos`)

Resumen técnico de cómo funciona cada parte del código. Se escribió leyendo el
código de la rama `rediseno/claude-interfaz` (commit `d478163`); donde algo no se
leyó en detalle se dice. Las referencias son `archivo` y función o clase. Las
afirmaciones sobre ejecución (315 pruebas de Python, 41 de Node) se comprobaron
al escribir este documento; las demás salen de leer el código.

Convenciones: «motor A» es la deducción natural (`proof/`), «motor B» es la
resolución (`resolution/`). «Inconcluso» (`unknown`) nunca significa «falso»
ni «demostrado».

---

## 1. Visión general

Bat’z es una aplicación local de lógica de primer orden. Python estándar en el
servidor, JavaScript nativo con módulos ES en el navegador. No hay frameworks,
bundler, CDN ni servicios externos; Three.js va copiado en `web/vendor/`.
(Solo el script de entrenamiento `scripts/train_spanish_tagger.py` necesita
numpy, y solo para regenerar los pesos; la inferencia no.)

### 1.1 Mapa de directorios

| Ruta | Contenido |
|---|---|
| `evaluador.py` | Punto de entrada: añade `src/` a `sys.path` y llama a `logos.server.main`. |
| `src/logos/*.py` | Núcleo lógico y servidor (sección 2 y 3). |
| `src/logos/proof/` | Certificados, checker, buscador, Kalmár, vista Fitch, render de texto. |
| `src/logos/resolution/` | Motor B: forma clausal (`clausify.py`) y resolución (`prover.py`). |
| `src/logos/lexicon.tsv`, `spanish_grammar.txt`, `spanish_tagger.json` | Datos del español: léxico base (6137 líneas), gramática (136 líneas), pesos del etiquetador. |
| `src/logos/web/` | Frontend servido tal cual (sección 4). |
| `src/logos/web/app.js` | Shell y lógica de pantalla (2322 líneas, un solo módulo). |
| `src/logos/web/app/navigation.js` | Rutas puras (sin DOM). |
| `src/logos/web/features/*` | Módulos por función: `home`, `evaluator`, `export`, `explanation-player`, `learn`, `people`, `tour`. |
| `src/logos/web/story3d.js` | Escena Three.js del reproductor (avatar, dominio, labios). |
| `src/logos/web/practice.js`, `practice.css` | Modo Practicar: script clásico (IIFE, no módulo). |
| `src/logos/web/tokens.css`, `style.css`, `styles/*.css` | Hojas de estilo (sección 4.9). |
| `src/logos/web/vendor/`, `fonts/`, `avatar/logos.glb`, `img/` | Three.js, fuentes locales woff2, avatar, retratos y marca. |
| `tests/` | `unittest` de Python (30 archivos `test_*.py` más `helpers.py`, `semantic_helpers.py`, `proof_corpus.py`). |
| `tests/frontend/app/*.test.mjs` | Pruebas Node de lógica pura del frontend. |
| `tests/frontend/player/` | Demo y pruebas de navegador del reproductor (Playwright externo). |
| `scripts/` | Auditoría de léxico, cola de léxico, informe de español, entrenamiento del etiquetador, ensayo de demo, instaladores de voz, validación de Practicar en navegador. |
| `docs/` | Fases originales (`00`–`10`), `specs/`, `plans/`, `architecture/`, `decisions/`, `validation/`, `testing/`. |
| `datos/` | Datos del usuario en tiempo de ejecución (`.gitkeep`; el resto está en `.gitignore`): `lexico_usuario.tsv`, `cuadernos/*.json`. |
| `ejemplos/*.logos` | Paquetes de ejemplo para «Importar modelo» (`grafo.logos`, `personas.logos`). |
| `assets/avatar/` | Fuente Blender del avatar y scripts de construcción (`realista/`). No se sirve. |
| `Dockerfile`, `docker-compose.yml` | Imagen `python:3.12-slim`; el compose publica solo en `127.0.0.1` y monta `./datos`. |

### 1.2 Flujo general

```
 NAVEGADOR (http://127.0.0.1:PUERTO/)                 SERVIDOR (server.py, ThreadingHTTPServer)
 ┌────────────────────────────────────────┐          ┌───────────────────────────────────────────┐
 │ index.html ── <script type=module>     │  GET     │ Handler.do_GET: lista controlada de       │
 │   app.js  (shell, Evaluar, Demostrar,  │ ───────► │ recursos estáticos (WEB / nombre)         │
 │            Cuadernos, Diccionario)     │          │                                           │
 │   features/*  (home, learn, tour, …)   │  POST    │ Handler.do_POST ── valida ruta y tamaño   │
 │   explanation-player + story3d.js      │  JSON    │   └► handle_api(route, data)              │
 │ practice.js (script clásico)           │ ───────► │        ├ /api/evaluate|free|validate|load │
 │                                        │ ◄─────── │        │    └► project.evaluar ─► semantics│
 │ localStorage: progreso y preferencias  │  JSON    │        │       explain, story, tree       │
 │ (nunca fórmulas ni modelos)            │          │        ├ /api/countermodel ─► countermodels│
 └────────────────────────────────────────┘          │        ├ /api/proof ─► read_problem,      │
                                                     │        │    propositional | proof | Kalmár │
                                                     │        │    | resolution | countermodels   │
                                                     │        ├ /api/spanish ─► spanish ─► lexicon│
                                                     │        │    spanish_cyk, spanish_semantics │
                                                     │        │    spanish_tagger                 │
                                                     │        ├ /api/notebook/* ─► notebook ──────┼─► datos/cuadernos/*.json
                                                     │        ├ /api/lexicon/*  ─► lexicon ───────┼─► datos/lexico_usuario.tsv
                                                     │        ├ /api/practice/* ─► practice       │
                                                     │        └ /api/voice/* ─► voice_input ──────┼─► whisper-cli + ffmpeg (opcional, local)
                                                     └───────────────────────────────────────────┘
```

Todo lo que el navegador dibuja como «verificado» viene de una comprobación en
Python: una traza revisada por `check_trace`, un certificado aceptado por
`proof.checker.verify`, o un contramodelo reevaluado con `is_countermodel`.
El navegador solo hace validaciones de comodidad (nombres no vacíos, tablas
≤ 1024 filas) que el servidor repite.

### 1.3 Cómo arrancar y probar

```
python3 evaluador.py [--port 8765] [--no-browser] [--host 127.0.0.1]
PYTHONPATH=src:tests python3 -m unittest discover -s tests
node --test tests/frontend/app/*.test.mjs
```

`main` intenta el puerto pedido; si está ocupado usa uno libre (`port 0`) en
silencio y lo imprime. Con `node --test tests/frontend/app` (directorio) Node 24
falla, hay que pasar los archivos.

---

## 2. Núcleo lógico en Python

### 2.1 Lenguaje formal: `ast.py`, `lexer.py`, `parser.py`, `printer.py`, `errors.py`

| Módulo | Responsabilidad e invariantes |
|---|---|
| `ast.py` | Nodos inmutables (`@dataclass(frozen=True)`): `Var`, `Const`, `Func`, `Pred`, `Eq`, `Bottom`, `Not`, `And`, `Or`, `Implies`, `Iff`, `Forall`, `Exists`. Los constructores validan en `__post_init__`: términos en minúscula inicial y no reservados (`forall`, `exists`), predicados en mayúscula, `Func` con al menos un argumento, hijos del tipo correcto. `Span` va en un campo con `compare=False`, así que dos fórmulas con distinta posición son iguales. Solo hay `Bottom`; `≠` se representa como `Not(Eq)`. |
| `lexer.py` | `tokenize(text)` devuelve tokens con offsets. Admite Unicode y ASCII (`¬ ~ !`, `∧ & /\`, `∨ \| \/`, `→ ->`, `↔ <->`, `∀ forall`, `∃ exists`, `≠ !=`, `⊥ _\|_`). Los símbolos más largos van primero en la tabla. Un identificador sin mayúscula ni minúscula (`caseless_identifier`) es error léxico. |
| `parser.py` | Descendente recursivo, clase `_Parser`. Precedencia de menor a mayor: `↔` (no asociativo, encadenarlo es `non_associative`), `→` (asocia a la derecha), `∨`, `∧` (a la izquierda), unarios `¬ ∀ ∃`. Un cuantificador liga solo el siguiente unario (`∀x P(x) ∧ Q` es `(∀x P(x)) ∧ Q`). Un nombre en minúscula es variable salvo que esté en `constants` (parámetro de `parse`) o en un cuantificador. Cuantificar una constante es `quantified_constant`. `modo propositional=True`: una minúscula suelta en posición de fórmula (`p`) se lee como el predicado 0-ario `P`; `p` y `P` en la misma entrada dan `letter_collision`. |
| `printer.py` | `to_string(f, ascii=False)`: texto canónico con el mínimo de paréntesis según la tabla de precedencias. Round-trip `parse(to_string(f)) == f` (probado en `test_printer_roundtrip.py`). |
| `errors.py` | `LogosError(stage, code, message, span, source)` con `to_diagnostic()` → `{schema_version, status:"invalid_input", stage, code, message, span, line, column}`. `stage`: `lexical`, `syntactic`, `semantic`. `ProofError` (en `proof/certificate.py`) hereda de él y añade `step`. |

### 2.2 Símbolos y firmas: `symbols.py`, `interpretation.py`

- `Signature(constants, functions, predicates)`: constantes y aridades.
- `check(f, signature, strict, source)` recorre la fórmula y devuelve la firma
  inferida. Sin firma, la aridad de cada símbolo es la de su primer uso
  (`arity_mismatch` si cambia). Con `strict=True` todo símbolo no variable debe
  estar declarado (`undeclared_symbol`). Un mismo nombre no puede ser variable,
  constante y función (`symbol_kind_clash`).
- `parse_checked(text, signature, strict)` = `parse` con las constantes de la firma
  + `check`.
- `interpretation.build_interpretation(signature, data)` es el perfil estricto
  «MM3032» sobre `FiniteModel`: exige exactamente los símbolos de la firma,
  predicados de aridad ≥ 1 y relaciones **no vacías**, tablas de función
  completas, elementos solo `int` o `str`, tipos exactos (no `bool`). `FiniteModel`
  en sí es más permisivo (acepta relaciones vacías y aridad 0): la búsqueda de
  contramodelos de consecuencia lo usa, y por eso un contramodelo puede no ser
  «cargable» en Evaluar (`ConsequenceSearch.loadable`).

### 2.3 Modelos y semántica: `model.py`, `semantics.py`

- `FiniteModel(domain, constants, functions, predicates)` valida: dominio no
  vacío y sin repetidos, funciones **totales** (la tabla debe tener exactamente
  `|D|^aridad` entradas), valores en `D`. `to_dict`/`from_dict` es el formato
  JSON versionado (`schema_version: "1"`), con orden canónico.
- `semantics.py`:
  - `holds(model, f, assignment)`: evaluación recursiva. `∀` y `∃` recorren todo
    el dominio con `all`/`any` sobre `{**s, var: d}`. Valida antes que los símbolos
    estén interpretados con la aridad correcta y que toda variable libre esté
    asignada (`missing_interpretation`, `model_arity_mismatch`,
    `unassigned_variable`, `invalid_assignment`).
  - `is_true` exige sentencia; `is_countermodel(model, premises, conclusion)` es
    «premisas verdaderas y conclusión falsa».
  - `evaluate` construye una `Trace` (árbol completo, **sin cortocircuito**): cada
    nodo lleva fórmula, valor, asignación restringida a sus libres, hijos,
    `term_values` (en átomos) y `element` (en hijos de un cuantificador).
  - `check_trace` es un verificador local e independiente de `evaluate`: revisa
    cada nodo contra el modelo (átomos recalculados, número de hijos, instanciación
    de cuantificadores en el orden del dominio, valor del nodo según sus hijos).
    Lanza `invalid_trace`.

### 2.4 Transformaciones: `transform.py`

`free_vars`, `bound_vars`, `all_var_names`, `substitute` (simultánea, sin captura:
renombra con `fresh_name` la variable cuantificada si capturaría), `alpha_equiv`
(compara con niveles de profundidad, sin renombrar), `alpha_rename` (falla si
provoca captura), `rename_bound_canonical` (v1, v2…). El checker de pruebas depende
de `alpha_equiv`, `free_vars` y `substitute`.

### 2.5 Árboles para dibujar: `tree.py`

- `syntax_tree(f, letters)`: dict anidado `{label, kind, formula, children}`.
  `letters` restituye cómo escribió la persona las letras proposicionales
  (`P` → `p`).
- `semantic_tree(trace, limit=500)`: lee la traza que ya aceptó `check_trace`; no
  recalcula. Bajo un cuantificador pone una rama por elemento con `edge: "x = 0"`.
  Al llegar a 500 nodos corta con `truncated: <n hijos omitidos>` y reporta
  `nodes`. El frontend avisa del corte en el visor.

### 2.6 Explicaciones e historias

- `explain.py`: `explain(model, trace)` **primero llama `check_trace`**, después
  `_explain` produce `Explanation(formula, value, summary, span, details, children,
  assignment)`. Es determinista y selectivo: un `∧` verdadero muestra ambos hijos,
  uno falso solo el hijo falso; un `∃` verdadero muestra el testigo, un `∀` falso
  el contraejemplo; `→` falsa muestra ambos; `¬` baja a su operando.
- `story.py`: `build_story(model, trace)` (también tras `check_trace`) recorre la
  traza en preorden y emite un `StoryEvent` por nodo: `id`, `trace_path` ("0",
  "0.1", …), `kind` (`predicate`, `equality`, `quantifier`, `bottom`, `connective`),
  `formula`, `value`, `text_es` (el `summary` de `_explain`), `span`, `assignment`,
  `element`, `relation`, `term_values`, `verified_by: {trace_path}`.
- `proof_story.py`: `build_proof_narration(cert, show)` llama a `verify` y a
  `fitch_layout`; emite un evento por línea Fitch citable con `kind: "proof"`,
  `step_id`, `line`, `rule`, `rule_label`, `refs`, `context` (hipótesis abiertas),
  `depth`, `steps`, `verified_by: {certificate_step}` y `trace_path: "p<línea>"`.
  Los números de línea son los de la vista Fitch. Una premisa que la prueba no
  usa no genera evento.

### 2.7 Lógica proposicional: `propositional.py`

- `is_propositional(f)`: solo `⊥`, predicados 0-arios y conectivos (sin igualdad ni
  cuantificadores).
- `truth_table`, `valuations` (F antes que V, letras por orden alfabético),
  `value` (evaluación directa), `valuation_model` (modelo de un elemento).
- `kalmar_sequent(f, v)`: premisas = literales de `v`, meta = `f` o `¬f` según su
  valor (el lema de Kalmár como en la clase).
- `decide(premises, conclusion, config, max_atoms=16)`: recorre las 2ⁿ valuaciones;
  si encuentra una que hace verdaderas las premisas y falsa la conclusión, devuelve
  `counterexample` tras **reconfirmarlo con `is_countermodel`** (si no coincidiera,
  `AssertionError`: es un bug del decisor). Si no la hay, intenta `prove` (motor A)
  y cae a `kalmar_prove`; ambos certificados pasan por el checker. Más de
  `max_atoms` letras da `unknown` con `too_many_atoms`.
  (Nota: el servidor no llama a `decide`; implementa su propio flujo, ver 3.3.)

### 2.8 Deducción natural: `proof/`

| Archivo | Papel |
|---|---|
| `certificate.py` | `ProofStep(id, formula, context, rule, refs, params)`, `ProofCertificate(premises, conclusion, steps)` y su JSON canónico (`to_dict`/`from_dict`, con `constants`). 22 reglas en `RULES`. `params`: `var`, `term` o `template` según regla. |
| `checker.py` | **Checker independiente**. Solo importa `ast`, `transform` y `certificate` (no el buscador). `verify(cert)` recalcula el contexto de cada paso con `_apply` (una función por regla, comparando salvo alfa-equivalencia) y exige que coincida con el declarado (`context_mismatch`); los ids deben ser 1..n consecutivos; las refs apuntan solo hacia atrás; el último paso debe ser la conclusión y no puede quedar abierta ninguna hipótesis que no sea premisa (`open_assumption`). Condiciones de variable propia en `∀I` y `∃E` (`eigenvariable`). Un error trae el `step` culpable. |
| `search.py` | Buscador dirigido por la meta (motor A). Construye `Deriv` y los linealiza (`linearize`) a certificado. `SearchConfig(max_depth=6, max_nodes=200_000, timeout=10.0)`; `search()` hace profundización iterativa sobre la profundidad de «decisiones con elección», memoriza fallos (`failed`) por (hechos, meta, profundidad), satura hechos, y como máximo 14 términos candidatos para instanciar. Devuelve `(certificado|None, motivo, nodos)`; motivos `depth` o `budget`. Es incompleto a propósito. No usa el checker. |
| `__init__.py` | `prove`, `prove_text`, `find_inconsistency`. `_run` **verifica el certificado** antes de devolver `proved`/`inconsistent`; si el checker lo rechaza, `unknown` con `reason="checker_rejected"`. `prove_text(..., propositional=True)` parsea todas las fórmulas juntas para detectar colisiones `p`/`P`. |
| `kalmar.py` | `kalmar_prove`: prueba proposicional completa y determinista. `kal(f, v)` deriva `f` o `¬f` desde los literales de `v` por inducción en `f`; una rama por valuación se combina con `p ∨ ¬p` (`_lem`) y `∨E`. El certificado crece como 2ⁿ, por eso `max_atoms` (10 por defecto; el servidor usa 6). Lanza `LogosError` si no es proposicional, hay demasiadas letras o no es consecuencia. No hay búsqueda: el resultado igual pasa por el checker. |
| `fitch.py` | Vista Fitch: `fitch_layout(cert)` reordena y renumera el certificado en líneas con cajas (una por hipótesis descargada por `→I`, `¬I`, RAA, `∨E`, `∃E`; `∀I` marca la variable nueva). `check_layout` comprueba que la disposición es fiel al certificado. **No leí el cuerpo del algoritmo de disposición**, solo su cabecera y la interfaz (`FitchLine`, `discharged`). |
| `render.py` | `format_certificate`: texto plano para depurar; `RULE_SYMBOLS` (∧I, →E…). |

### 2.9 Motor B, resolución: `resolution/`

- `clausify.py`: `_nnf` (forma normal negativa), `Clausifier` (Skolem
  `sk<n>(universales en alcance)`, variables `?n`, distribución de `∨` sobre `∧`
  con cota `max_clauses`; `TooManyClauses` si se pasa). Las variables libres se
  tratan como constantes arbitrarias pero fijas (`v:x`). `equality_axioms()`
  añade reflexividad, simetría, transitividad y congruencia por cada símbolo
  usado, solo si la entrada usa `=`. Representación propia, independiente del AST.
- `prover.py`: `refute` implementa resolución binaria con factorización y cola
  de prioridad por peso (con una elección por antigüedad cada `age_ratio=5`),
  eliminación de tautologías y subsunción por cláusula unitaria. Límites:
  `max_clauses=6000`, `max_literals=8`, `max_depth=6` de términos, `timeout=5`.
  Resultados: `refuted` (cláusula vacía, con la prueba renumerada), `saturated`
  (no quedan inferencias y no se podó nada), `unknown` (`timeout`,
  `clause_limit`, `cnf_limit`, o `pruned` si se descartaron cláusulas por tamaño
  y por tanto no se puede afirmar saturación).
- `__init__.py`: `resolve_text`, `contrast(premises, conclusion)` y la tabla
  `_MATRIX` (estado de A, estado de B) → veredicto: `consistent`,
  `soundness_alarm` (A probó y B saturó), `completeness_gap` (A no probó y B
  refutó), `no_information`. **B nunca produce `proved`**: solo contrasta.

### 2.10 Búsqueda de contramodelos: `countermodels.py`, `modelfinder.py`

Dos buscadores distintos, con propósito distinto.

`countermodels.py` enumera interpretaciones completas, tamaño de dominio por
tamaño, `_models(signature, domain, allow_empty, skip_strict)`:

- `find_countermodel(signature, text, config)`: busca un modelo del perfil
  estricto (relaciones no vacías) donde una **sentencia** sea falsa. Si hay
  variables libres, `unassigned_variable`.
- `find_consequence_countermodel(premises, conclusion, constants, config)`: busca
  un modelo (y asignación para las variables libres) donde valen las premisas y
  falla la conclusión. En cada tamaño prueba primero las estructuras estrictas
  y luego las que tienen alguna relación vacía.
- `CountermodelConfig(max_size=3, max_candidates=5000, timeout=2.0,
  max_table_rows=12)`; `__post_init__` impone techos duros (tamaño ≤ 5, candidatos
  ≤ 100 000, timeout ≤ 30 s, filas ≤ 20). La variante de consecuencia usa por
  defecto `max_size=3, max_candidates=20_000, max_table_rows=16`.
- Antes de enumerar un tamaño, si alguna tabla pasaría de `max_table_rows`
  (`size ** aridad`), devuelve `unknown/table_limit`. Otros motivos de `unknown`:
  `candidate_limit`, `timeout`, `size_limit`.
- **Todo hallazgo se reevalúa** con el evaluador de la Fase 2 (traza verificada
  vía `evaluate`) y si no refutara, `AssertionError`. `unknown` solo dice que no
  apareció dentro de lo explorado.
- Deja una bitácora `log` (tamaño, candidatos, un ejemplo descartado) con la que
  `search_events` construye los eventos `kind: "search"` y `kind: "premise"` que
  el reproductor narra antes del hallazgo (`_join_story` renumera los ids).

`modelfinder.py` (`find_model`) es otra estrategia, usada por Cuadernos: para
cada tamaño de dominio despliega los cuantificadores sobre los elementos (`∀`
como conjunción, `∃` como disyunción), queda un problema proposicional sobre
átomos `P(0, 1)` y lo resuelve con retroceso y propagación de disyunciones de
una opción (`_satisfy`). Primero prueba dominios con cada constante en un
individuo distinto, después permite coincidencias. Rechaza símbolos de función
(`_GiveUp`; los cubre la enumeración) y fórmulas con variables libres (devuelve
`None`). Límite de `MAX_NODES = 150_000` por intento y `timeout`. Es heurística:
`None` no dice nada. Todo modelo devuelto se reverifica con `is_true`.

### 2.11 Fachada del proyecto: `project.py`

`libres(texto, firma)` devuelve las variables libres que la interfaz debe pedir.
`evaluar(firma, interpretacion, texto, entorno)` hace: `build_interpretation` →
`parse_checked(strict=True)` → validar el entorno (valores `int|str`; que las
claves sean variables y no símbolos declarados) → `evaluate` → `explain` y
`build_story` (ambos verifican la traza). Devuelve `Resultado(status, value,
trace, explanation, story, model, errors)`; ante un `LogosError` devuelve
`status="invalid_input"` y **ningún valor** ni traza.

### 2.12 Serialización: `serialize.py`

`formula_to_dict`/`formula_from_dict` (árbol con ids por ruta `"0.1.0"`; al
leer se comprueba id, esquema y que `text` coincida) y `result_to_dict` (sobre
de resultado con `status` ∈ `proved`, `counterexample`, `unknown`,
`inconsistent`, `invalid_input`). Lo usa `PropVerdict.to_dict` y
`ProofResult.to_dict`; el servidor actual construye sus propios sobres (ver 3.3).

### 2.13 Archivos `.logos`: `modelfile.py`

`parse_model_file(text)` acepta texto plano o JSON exportado (si empieza con `{`).
Líneas: `dominio:`, `constante a = v`, `funcion f/n: a -> v, …`,
`predicado P/n: tuplas`, `formula: texto | x = 0 | espera: verdadero`;
`#` comenta. Solo lee la forma; la validación matemática la hace después
`build_interpretation`. Devuelve `{signature, interpretation, formulas}` (cada
fórmula con `assignment`, `line` y `expected` opcional).

### 2.14 Español controlado: `spanish.py`, `spanish_cyk.py`, `spanish_semantics.py`, `lexicon.py`, `spanish_tagger.py`

Flujo de `translate_spanish(text)`:

1. `spanish_cyk.tokenize`: minúsculas, separa `del`→`de el` y `al`→`a el`
   (salvo «al menos»), descarta signos, rechaza caracteres ajenos, máximo 40
   palabras.
2. `spanish_cyk.grammar()` (cacheada) lee `spanish_grammar.txt`
   (reglas `X -> a | b c …`), binariza a la derecha, y añade al léxico cada forma
   flexionada del diccionario (`lexicon.grammar_forms`) con su categoría,
   respetando las palabras que ya trae la gramática. `_automaton` es un Aho-Corasick
   sobre palabras y expresiones fijas.
3. `parse`: CYK con cierre de reglas unarias que **conserva todas las derivaciones**
   (hasta `MAX_TREES = 512`, si no, «Demasiadas lecturas»); nunca escoge un árbol.
4. Si no hay árbol y hay palabras fuera del vocabulario,
   `spanish_tagger` (regresión logística con pesos en JSON; solo inferencia)
   **propone** categorías; se reparsea con esas categorías. Lo supuesto sale en
   `assumptions` con su probabilidad y se muestra al usuario. La gramática decide
   si encaja; el etiquetador no decide nada lógico.
5. Sin árbol: sugerencia de concordancia de género (`_agreement_hint`), aviso de
   artículo solo, «Palabra fuera del léxico» o «Frase fuera de la gramática
   controlada» (`unsupported_spanish`).
6. `spanish_semantics.readings(tree)` compone fórmulas (`Composer`). Genera varias
   lecturas cuando hay ambigüedad real: numeral a secas («al menos» o
   «exactamente»), alcance sujeto/objeto de la oración principal (se invierte el
   orden de los cuantificadores y se explica con notas fijas `SCOPE_NOTES`),
   y «todos … no …» (ninguno / no todos).
7. Palabras con varios sentidos (`lexicon.senses`): una lectura por combinación de
   sentidos (hasta 16). Cada fórmula se imprime y se vuelve a parsear con la
   firma estricta (`parse_checked`) y se deduplican por texto.

Resultado: `SpanishResult(status single|ambiguous, readings, assumptions)`.
**Nunca elige una lectura en silencio.**

Detalle importante: `spanish_semantics.EXTRA` y `SENSE` son **diccionarios globales**
que `translate_spanish` llena y vacía durante la composición.

`lexicon.py`: `Entry(lemma, category N|ADJ|V|NP, feature, extra, source)`.
`forms()` genera plural (reglas ortográficas y excepciones `pl=`), femenino,
y para verbos las seis formas (`conjugate`; presente, subjuntivo y pasado de
él y de ellos; con irregulares por `cambio=` o `formas=`). El símbolo lógico es el
lema sin tildes (`duermen` → `Dormir`); `sin=` hace sinónimos y `sentido=` crea
símbolos distintos para sentidos distintos (`Banco_asiento`). `_derived` añade
sin guardar diminutivos y participios. El léxico base es `lexicon.tsv`
(`source="base"`); las palabras añadidas por el usuario se guardan en
`datos/lexico_usuario.tsv` o en `LOGOS_LEXICON` (`source="usuario"`). `add` valida
(`_validate`: una palabra, solo letras, categoría, rasgos, formas generables),
rechaza duplicados exactos, escribe el TSV (añadiendo) y recarga y precalienta
las cachés (`reload`, `warm_up`). `remove` solo quita entradas del usuario.
Las cachés son `lru_cache`.

### 2.15 Cuadernos: `notebook.py`

Un cuaderno es un JSON en `datos/cuadernos/c<12 hex>.json` (o `LOGOS_NOTEBOOKS`)
con `version`, `title`, `created`, `updated`, `sources` (cada una con `id` `f<n>`,
`title`, `text`, `enabled`, `choices`) y `chat`. **En disco solo van textos y
lecturas elegidas**; el análisis y las respuestas se recalculan en cada petición.

- `split_sentences` parte por `. ; ! ?` y por línea; reconoce viñetas y números de
  lista; devuelve offsets.
- `_analyze` por oración: pregunta (`?`) → rechazada; si `translate_spanish`
  falla → rechazada con el motivo y su span; una lectura y sin supuestos →
  premisa; varias lecturas o palabras supuestas → «por elegir» hasta que la
  persona elija (`choices` se indexa por el texto de la oración); mientras tanto no
  se usa.
- `_premises`: premisas distintas de las fuentes activas, **con la cita** de todas
  las oraciones que dicen exactamente lo mismo; `check` impone aridad coherente
  entre oraciones (error con la oración culpable) y un máximo de 80 premisas.
- `ask(raw, question, formula)`: `question_statement` quita «¿Se sigue que…?»;
  traduce; si es ambigua o supone palabras pide elegir (`answer: "choose"`).
  Después, para la meta y luego para su negación, llama a `_prove`:
  1. resolución 2 s: si satura, no se sigue (se descarta rápido);
  2. si refuta, `_related` (premisas conectadas por símbolos) y `_core` (quita
     premisas mientras la resolución siga derivando) orientan qué premisas pasar;
  3. `prove` del motor A (`PROOF_CONFIG`: profundidad 6, 20 000 nodos, 3 s).
  **«Se sigue» lo afirma solo un certificado aceptado**; la resolución solo orienta.
  `_proof_view` rehace la prueba con solo las premisas usadas, numera citas y
  adjunta el contraste A/B.
  Respuestas: `follows`, `contradicts`, `undecided` (ni la pregunta ni su negación
  se siguen y hay modelo/saturación de ambos lados), `not_follows`, `unknown`,
  `empty` (sin premisas), `choose`. Si resolución también deriva lo contrario,
  marca `inconsistent` (las fuentes se contradicen). Sin pruebas, `_model_view` usa
  `find_model` para el contramodelo y el testigo, nombrando los individuos con
  las constantes (`_named`) y reverificando con `is_countermodel`.
- Límites: 60 cuadernos, 20 fuentes, 20 000 caracteres por fuente, 150 oraciones
  por fuente (`truncated` en la vista), 80 premisas, título 80, pregunta 300,
  historial 40. Escritura atómica (`.tmp` + `replace`), identificadores validados
  con regex (sin rutas arbitrarias). `api(action, data)` serializa todo con un
  `RLock` global porque «el traductor usa estado global».
- Acciones: `list`, `create`, `import`, `get`, `export`, `delete`, `ask`,
  `rename`, `source-add`, `source-remove`, `source-toggle`, `choose`,
  `clear-chat`. Tras cambiar fuentes o elecciones, los veredictos del historial
  se vacían (`turn["answer"] = ""`).

### 2.16 Practicar: `practice.py`, `practice_bank.py`

`practice_bank.py` define 50 ejercicios (`EXERCISES`), tres categorías (1–10,
11–40, 41–50), pistas y soluciones de referencia construidas por funciones
(`Proof.add` calcula las referencias al redactar; no se genera nada al jugar).
Cada ejercicio lleva `revision` = SHA-256 (12 hex) de su especificación.

`practice.build(ex, moves)`: el cliente envía solo fórmulas, reglas, referencias y
parámetros; **los contextos los calcula el servidor** con `checker._apply` para
cada jugada nueva y luego `verify` revisa toda la prueba como certificado
(prefijo). Una prueba está `complete` si el último paso es el objetivo
(alfa-equivalente) y su contexto solo contiene premisas; entonces se verifica
además contra las premisas reales. No exige coincidir con la solución de
referencia. Límites: 100 jugadas propias, 500 caracteres por expresión, ≤ 60
paréntesis o negaciones. `api`: `catalog`, `preview` (lectura en español
composicional con `reading`), `check`, `hint`, `solution`.

### 2.17 Voz: `voice_input.py`

Transcripción opcional **local** con `whisper-cli` + modelo `ggml-*.bin` +
`ffmpeg`, localizados por variables `LOGOS_WHISPER_CLI` y `LOGOS_WHISPER_MODEL`
o en la carpeta de voz del usuario (`~/.local/share/logos/voz` o
`%LOCALAPPDATA%\LOGOS\voz`). Una variable definida manda aunque apunte a un
archivo inexistente. `transcribe(audio)`: acepta 100 B – 5 MB, convierte con
ffmpeg (15 s de límite) y transcribe (60 s) dentro de un directorio temporal.
`availability()` nunca devuelve rutas absolutas. El texto transcrito **no se
traduce solo**: la interfaz lo deja en el campo y la persona pulsa «Mostrar
lecturas».

---

## 3. Servidor: `server.py`

`ThreadingHTTPServer` con `Handler(BaseHTTPRequestHandler)`; `log_message` está
silenciado. Constantes: `MAX_BODY = 1_000_000`, `PROOF_CONFIG` (profundidad 6,
20 000 nodos, 3 s), `KALMAR_ATOMS = 6`, `TRUTH_TABLE_ATOMS = 12`.

### 3.1 `do_GET`: lista controlada

Un diccionario literal `files` mapea ruta pública → (ruta relativa a `web/`,
MIME). Si la ruta no está, 404. Solo se sirven los archivos enumerados: no hay
resolución de rutas arbitrarias, así que no hay recorrido de directorios.
Excepción: `/fonts/<archivo>.woff2`, donde se toma solo `Path(path).name` y se
exige que sea `.woff2` y exista en `web/fonts/`. `/favicon.ico` responde 204.
Se lee el archivo en cada petición (sin caché ni `Cache-Control`).

Por qué una lista: el servidor es local y puede publicarse en `0.0.0.0` dentro
de Docker; enumerar los recursos evita servir por accidente `index.html`
variantes, créditos (`img/CREDITOS.md`), la marca (`img/batz-*.svg`) o cualquier
archivo que aparezca en `web/`. Consecuencia: **cada módulo o imagen nuevos
hay que registrarlos a mano**. Comprobé con un script que todos los `import`,
`href`, `src` y `url()` del frontend actual apuntan a rutas registradas, y que
los únicos archivos de `web/` no servidos son `img/CREDITOS.md` y los tres
`img/batz-*.svg` (la marca va inline en `index.html`).

### 3.2 `do_POST`

1. La ruta debe estar en la lista literal (`/api/free`, `validate`, `evaluate`,
   `countermodel`, `spanish`, `proof`, `parse`, `load`, `lexicon/{search,suggest,
   preview,add,remove}`, `voice/{status,transcribe}`) o empezar por
   `/api/notebook/` o `/api/practice/`. Si no, `send_error(404)` (cuerpo HTML).
2. `Content-Length` obligatorio y `0 < size <= 1 MB` (5 MB para
   `voice/transcribe`); si no, 413 con JSON. No admite `Transfer-Encoding: chunked`.
3. `voice/transcribe` exige `Content-Type: audio/webm` (415 si no) y lee el cuerpo
   crudo; el resto parsea JSON y llama a `handle_api(route, data)`.
4. El código HTTP es 200 si `response["status"]` ∈ `ok, found, unknown, single,
   ambiguous, proved, refuted` y 400 en otro caso (`invalid_input`).
5. Se capturan `VoiceInputError` (503 si `voice_unavailable`, si no 400),
   `json.JSONDecodeError`, `LogosError` (incluye `ProofError`), `TypeError`,
   `ValueError` (esta incluye `UnicodeDecodeError`). Todos devuelven 400 con
   `{schema_version, status:"invalid_input", errors:[diagnóstico]}`.
   **No se captura** `AssertionError` (los bugs detectados por reverificación),
   `KeyError`, `OSError`, `RecursionError`: la excepción llega a
   `socketserver`, que imprime el traceback y cierra la conexión sin respuesta;
   el frontend lo ve como fallo de `fetch`/JSON.

### 3.3 `handle_api(route, data)`

Independiente del transporte (las pruebas lo llaman directamente). Exige que
`data` sea un objeto.

| Ruta | Entrada | Qué hace |
|---|---|---|
| `/api/free` | `signature`, `formula` | `project.libres`: variables libres que hay que asignar. |
| `/api/validate` | `signature`, `interpretation` | `build_interpretation`; devuelve el modelo canónico. |
| `/api/evaluate` | `signature`, `interpretation`, `formula`, `assignment` | `project.evaluar`. Respuesta `ok`: `value`, `explanation`, `story`, `tree` (semántico), `syntax` (sintáctico), `model`. Si hay error: `invalid_input` con `errors`, sin valor. |
| `/api/countermodel` | `signature`, `formula`, `max_size` (1–3) | `find_countermodel`; `found` con `model`, `explanation`, `story`, `log`; `unknown` con `reason`, `explored`, `completed_sizes`. El servidor limita `max_size` a 3 aunque `CountermodelConfig` admita 5. |
| `/api/spanish` | `text` | `translate_spanish(...).to_dict()`: `single`/`ambiguous`, `readings` (cada una con `tree`), `assumptions`. **Sin bloqueo** sobre el estado global del traductor. |
| `/api/proof` | `premises` (≤ 8, ≤ 200 car.), `conclusion` (≤ 200), `constants` | Ver 3.4. |
| `/api/parse` | `formulas` (≤ 12, ≤ 400 car.), `constants` | Revisión sintáctica de varias fórmulas a la vez (modo Demostrar mientras se escribe); devuelve por cada una `ok`, `text`, `free`, `tree` o `error`, y `mode`. Si todas son proposicionales con letras, las muestra como letras. |
| `/api/load` | `text` (archivo `.logos` o JSON exportado) | `parse_model_file`, valida con `build_interpretation`, evalúa hasta 200 fórmulas con `evaluar`; cada fila trae `value`, `summary`, y `expected`/`matches` si el archivo lo declara. |
| `/api/lexicon/*` | ver 2.14 | `search` (60 por página, filtros `category` y `source`, `offset`), `suggest` (si la palabra no está, propone con el etiquetador), `preview`, `add`, `remove`. |
| `/api/notebook/*`, `/api/practice/*` | ver 2.15, 2.16 | Delegan en `notebook.api` y `practice.api`. |
| `/api/voice/status`, `/api/voice/transcribe` | — | `availability()` / `transcribe(audio)`. |

### 3.4 `/api/proof` en detalle

1. Valida tipos y tamaños.
2. `read_problem(premises, conclusion, constants)`: intenta parsear en primer
   orden; si falla, reintenta con `_Parser(..., propositional=True)` y exige que
   todas las fórmulas sean proposicionales y que no haya colisión `p`/`P`
   (guarda cómo escribió cada letra en `letters`). Si no, devuelve el primer error.
   Con la lectura en primer orden decide `mode`: `propositional` si todas lo son,
   `first_order` si no. Después `check` por fórmula con una firma compartida
   (aridad coherente). Un `LogosError` da `invalid_input`.
3. `second = resolve(ps, c, ResolutionConfig(timeout=2))`: **el motor B siempre
   se ejecuta** como segunda opinión; nunca convierte `unknown` en `proved`.
4. `_prove_propositional` (≤ 12 letras): recorre la tabla de verdad; si halla
   valuación que refuta, la reconfirma con `is_countermodel` y responde
   `status: "refuted"` con `valuation` (lista de pares `[letra, bool]`),
   `premises`, `conclusion`. Si no, `prove` (motor A); si no prueba y hay ≤ 6
   letras, `kalmar_prove` + `verify`; con más, `unknown` con
   `too_many_atoms_for_kalmar` (la consecuencia vale pero no se construye
   certificado). Más de 12 letras: `unknown/too_many_atoms`.
5. `_prove_first_order`: `prove`; si falla y B refutó, `unknown` sin buscar
   contramodelo; si no, `find_consequence_countermodel`. `found` → `status:
   "refuted"` con `countermodel` (el `to_dict` de `ConsequenceSearch`);
   si no, `unknown` con `reason` (`depth`, `budget`), `nodes` y `search`.
6. `proved` → `{status, mode, method, certificate, fitch, story, contrast}`
   (`story` re-llama `verify` vía `build_proof_narration`); `contrast` =
   `{verdict, message, engine_b}` de la matriz de 2.9.
   Ojo con el nombre: aquí el estado es `refuted`, no `counterexample`.

Peor caso de latencia por petición, sumando topes: resolución 2 s + prueba 3 s +
contramodelos 2 s.

### 3.5 Esquema JSON y variables de entorno

Esquema: `docs/specs/JSON_CONTRACTS.md` (ver discrepancias en la sección 9). Toda
respuesta lleva `schema_version: "1"`.

| Variable | Dónde se lee | Efecto |
|---|---|---|
| `LOGOS_NOTEBOOKS` | `notebook.folder()` | Carpeta de cuadernos (por defecto `datos/cuadernos/` bajo la raíz del repo). |
| `LOGOS_LEXICON` | `lexicon.user_path()` | Archivo TSV de palabras del usuario (por defecto `datos/lexico_usuario.tsv`). |
| `LOGOS_WHISPER_CLI`, `LOGOS_WHISPER_MODEL` | `voice_input` | Rutas de la voz local. |
| `LOGOS_PORT` | solo `docker-compose.yml` | Puerto publicado en `127.0.0.1` del anfitrión. |

### 3.6 Límites resumidos

Cuerpo 1 MB (5 MB audio); `/api/proof`: 8 premisas × 200 caracteres;
`/api/parse`: 12 fórmulas × 400; `/api/load`: 200 fórmulas; frase en español: 40
palabras y 512 árboles; cuaderno: ver 2.15; práctica: 100 jugadas; voz: 5 MB.

---

## 4. Frontend: `src/logos/web`

### 4.1 Carga y estructura

`index.html` carga 14 hojas CSS (4.8) y `app.js` como `type="module"` y
`practice.js` como script clásico con `defer`. El cuerpo tiene `data-mode`, una
barra lateral (`#sidebar`, `#nav` con siete enlaces `#tab-<id>`), la barra
superior (título, importar, ejemplo, ayuda), el panel de ayuda con la guía de
símbolos y el modo presentación, `#toasts` y `<main>` con una sección por modo:
`#mode-home`, `#mode-practice`, `#mode-evaluate` (3 paneles de asistente),
`#mode-prove`, `#mode-learn`, `#mode-person`, `#mode-dictionary`,
`#mode-notebook` (3 paneles). Cambiar de modo es mostrar/ocultar secciones
(`hidden`); no hay recarga. Las importaciones son rutas absolutas (`/features/…`)
que el servidor tiene registradas.

### 4.2 `app/navigation.js`

Funciones puras: `ROUTES` (home, evaluate, prove, practice, notebook,
dictionary, learn y tres páginas de persona `godel`, `turing`, `church` con
`nav: false` y la clave `person`), `routeFromHash`, `hashFor`, `titleFor`,
`isKnownHash`, `personFor`. Un hash desconocido o vacío va a Inicio; el antiguo
`#practicar` sigue válido. Probado en `tests/frontend/app/navigation.test.mjs`.

### 4.3 `app.js` por secciones

(Los números de línea son aproximados al commit indicado.)

| Líneas | Sección | Qué hace |
|---|---|---|
| 1–27 | Importaciones y estado | `$`, referencias de DOM y variables de módulo: `domain`, `preparedSignature`, `freeVariables`, contadores de revisión `evalInputs`, `proofInputs`, tokens de petición `freeRequest`, `searchRequest`. |
| 28–145 | Ayudantes de UI | `toast` (con acción «Deshacer»), `countUp`, `withBusy` (deshabilita el botón y evita doble envío), `verdictElement`, `placePill` (píldora deslizante de pestañas, con `ResizeObserver`), preferencia de movimiento reducido. |
| 146–201 | Explicación guiada | `explanations[origen]` (una instancia del reproductor por módulo: `evaluate`, `prove`, `notebook`), `showStory`, `clearStory`, `highlightStep`, `pauseExplanations` (ver 4.4). |
| 202–470 | Constructor de modelos | `addSymbol`, `signature()` (nombres únicos, aridad 1–5), `readDomain` (acepta JSON, `{a, b}` o `0, 1`), `prepare` (genera tablas de constantes, funciones y predicados; límite 1024 filas por tabla), `interpretation()` (lee las tablas y exige relaciones no vacías), `refreshReady`. |
| 473–515 | Cliente y fórmulas | `api(route, payload)` (POST JSON, devuelve `response.json()`), `showSpan` (resalta el tramo con error o el del paso en curso), `updateFree` (consulta `/api/free` y crea un selector por variable libre; descarta con `freeRequest`). |
| 517–690 | Visor de árboles | SVG propio sin dependencias: `prepareTree`, `layoutTree`, `treeCanvas`, `treeViewer({semantic, syntax})` con dos vistas (Evaluación y Estructura), `treeToggle`, `explanationElement` (explicación plegable). |
| 691–773 | `evaluateFormula` | Ver 5.3. |
| 774–870 | Asistente de Evaluar | Pasos 1 Modelo → 2 Fórmula → 3 Resultado: `setStep`, `updateStepper`, `modelIsReady`. El paso 2 exige modelo listo y el 3 un resultado vigente (`evalDone`); si no, `setStep` retrocede. `loadExample` carga un caso (con «Deshacer» vía `snapshotEvaluate`/`restoreEvaluate`), `useSpanishReading`. |
| 905–1002 | Importar/exportar | `exportJSON` (descarga `logos-interpretacion.json`), `applyPackage(payload, model)` (reconstruye símbolos, dominio y tablas desde un paquete), `batchRow` y `loadFile` (≤ 500 kB; vía `/api/load`; arrastrar y soltar en toda la página). |
| 1002–1135 | Contramodelo y español | `searchCountermodel` (`/api/countermodel`, descarta con `searchRequest`, «Cargar este modelo en las tablas»), `showSpanishReadings` (`/api/spanish`; muestra supuestos y ofrece «Añadir al diccionario»), `recordSpanish` (MediaRecorder `audio/webm`, 12 s máximo, `/api/voice/transcribe`; el texto queda en el campo para confirmar). |
| 1135–1347 | Demostrar | `proofInput`, `scheduleProofCheck`/`checkProofSyntax` (debounce de 220 ms a `/api/parse`, con `proofCheckRequest` para descartar; cada fórmula con su estado, árbol y «Ir a la entrada»), `proveFormula` (ver 5.4), `fitchElement`, `valuationElement`, `truthList`, `contrastElement`, `openInEvaluate`. |
| 1348–1634 | Diccionario | Estado `dictState`, búsqueda con filtros y paginación (`/api/lexicon/search`), detalle, formulario de alta con `preview`, consulta de palabra (`suggest`), vuelta al módulo de origen (`dictRenderOrigin`), `openDictionaryWith(word)`. |
| 1636–2075 | Cuadernos | Tres paneles: fuentes, preguntas y evidencia. `nbCall` (`/api/notebook/<acción>`), `setNotebook`, `nbChange`, visor de oraciones con estado (premisa, por elegir, rechazada), citas con retorno, `askNotebook` (descarta con `nbAskRev`), historial, exportar/importar, `confirmClick` (borrar pide un segundo toque). |
| 2076–2136 | Navegación | `MODES`, `SECTION_HELP`, `setMode(mode)` y `go(mode)` (ver 4.5). |
| 2138–2190 | Menú, barra lateral, presentación | `openMenu`/`closeMenu` con trampa de foco, `setSidebarCollapsed` (`localStorage`), contracción automática en 901–1100 px, `setPresenting`. |
| 2191–2221 | `runExercise` | Ejercicios de Inicio: navega y carga datos coherentes con «Deshacer». |
| 2222–2322 | Cableado | `setPane` (pestañas en teléfono para Cuadernos), todos los `addEventListener`, teclado de símbolos (`buildKeyboard`, `floatKeyboard` pegado sobre el teclado del sistema), `initLearn`, arranque (`setMode(routeFromHash(...))`) y `createTour`. |

### 4.4 Descarte de respuestas obsoletas

Las respuestas llegan asíncronas; el patrón es el mismo en todas partes: un
contador se incrementa **cada vez que cambia una entrada relevante**, la petición
guarda el valor al salir y, al volver, descarta el resultado si no coincide.

| Contador | Se incrementa en | Se compara en |
|---|---|---|
| `evalInputs` | `invalidateTables`, `loadExample`, cambios en la interpretación y la asignación, entrada de la fórmula, lectura en español elegida | `evaluateFormula` |
| `proofInputs` | entrada en premisas/conclusión/constantes, `runExercise`, `loadProofSample` | `proveFormula` (y `lastProof.rev` para permitir exportar solo un resultado vigente) |
| `nbAskRev` | `clearNotebookAnswer` (cambia pregunta, fuentes o cuaderno) | `askNotebook` |
| `freeRequest`, `searchRequest`, `proofCheckRequest`, `dictState.request`, `dictPreviewRequest` | al lanzar cada petición del mismo tipo | al volver la misma petición |

`clearStory(origin, motivo)` llama a `player.invalidate(motivo)` del módulo y
retira los resaltados externos (`.fitch li.current`, `showSpan`); la explicación
queda visible pero marcada «desactualizada» y sin poder avanzar. `invalidateTables`,
`prepare`, `searchCountermodel`, `evaluateFormula` y los `change` de las tablas la
llaman con `'evaluate'`. Salir de un módulo llama a `pauseExplanations` (pausa y sale de
pantalla completa, conservando el paso).

### 4.5 Navegación por hash

`go(mode)` hace `history.pushState` del hash (`hashFor`), `setMode` y emite
`logos-route`. `hashchange` (Atrás/Adelante) llama solo a `setMode`.
`setMode(mode)`: muestra la sección, marca `aria-current` en el enlace, fija
título y texto de ayuda, muestra u oculta «Importar modelo» y «Ejemplo», cierra
el menú, pausa explicaciones si hubo cambio, y por modo: `prove` →
`checkProofSyntax`, `dictionary` → primera búsqueda, `notebook` →
`openNotebookMode` (abre el último cuaderno recordado o el más reciente),
`practice` → dispara el evento `logos-practice` que arranca `practice.js`.
Al cambiar, vuelve al inicio de la página y enfoca el título.

### 4.6 `features/`

| Módulo | Contenido |
|---|---|
| `home/home.js` | `renderHome(host, {go, runExercise})`: titular, tarjetas de herramientas (`CARDS`), tres ejercicios guiados (`EXERCISES`), conexiones con Gödel/Turing (`CONNECTIONS`, cada una carga un caso en Demostrar), contadores. `PRACTICE_COUNT = 50` es una constante a mano (coincide hoy con `len(EXERCISES)`). |
| `home/carousel.js` | Carrusel Gödel/Turing/Church sin autoavance; ayudas puras (`stepIndex`, `swipeDelta`, `keyIndex`); diapositivas inactivas con `inert`. |
| `home/motion.js` | `braid()` (hilo SVG trenzado) y `enhanceHome` (aparición escalonada con `IntersectionObserver`, contadores, foco de luz). No se activa con `prefers-reduced-motion`. |
| `evaluator/examples.js` | 18 casos de ejemplo agrupados (`EXAMPLE_GROUPS`) con modelo, fórmula y `expected`; `examplePackage(example)` lo convierte en el paquete `{signature, model, formula}`; `SPANISH_PHRASES`. |
| `export/export.js` | Funciones puras que construyen un HTML autónomo (`buildEvaluationHtml`, `buildProofHtml`, `modelHtml`, `fitchHtml`; todo escapado con `esc`); `download` (Blob) y `printHtml` (iframe oculto con `srcdoc`). |
| `explanation-player/index.js` | `createExplanationPlayer` (ver 5.1). |
| `explanation-player/events.js` | Ayudas de presentación: `valueLabel`, `focusValues`, `eventLabel`, `eventVerdict`, `caseIndex` (salta al caso real del guion dentro del cuantificador), `domainPresentation`, `localSpanishVoice` (solo voces locales `es-*`, prefiere latinoamericanas), `readingTime`. No evalúa nada. |
| `explanation-player/fullscreen.js` | Pantalla completa de una sola instancia, con API nativa y respaldo (clase `ep-fallback-fullscreen` y `overflow:hidden`); restaura scroll y foco al salir; Escape sale. |
| `explanation-player/player.css` | Estilos `ep-*`. |
| `learn/data.js`, `deck.js`, `timeline.js`, `learn.js` | «Aprender»: datos de historia (`HISTORY`) y tarjetas (`CARDS`) sin lógica; `deck.js` (progreso en `localStorage`, cola, barajado, saneado), `timeline.js` (navegación y accesibilidad de la línea de tiempo, funciones puras), `learn.js` (`initLearn`, construye el DOM). |
| `people/people.js`, `bios.js`, `person.js` | Datos de personas (años, crédito, licencia, retrato; `image: null` muestra iniciales), biografías (`BIO_SLUGS` = godel, turing, church), `renderPerson` y `portrait`. Los enlaces de crédito llevan `rel="noopener noreferrer"`. |
| `tour/tour.js` | Recorrido de primer acceso. `readTourState`/`writeTourState`/`shouldOfferTour` son puras; `createTour` pinta una tarjeta flotante y señala elementos con `.tour-target`. Solo se ofrece en Inicio y una vez. |

`practice.js` (fuera de `features/`) es el tutor de Practicar: carga el catálogo
(`/api/practice/catalog`), mantiene el progreso en `localStorage`, **revalida las
pruebas guardadas contra el servidor al arrancar** (una marca local no cuenta
como completada), migra por `revision` (guarda hasta 3 intentos previos en
`previous` si cambió el enunciado) y llama a `preview`, `check`, `hint` y
`solution`.

### 4.7 `story3d.js` (escena Three.js)

`createStoryScene(container, model, {onPick, onReady, onError})`: `WebGLRenderer`,
un arco de esferas para el dominio (máximo 12 elementos; si hay más lanza error y
el reproductor cae al 2D), aristas de las relaciones binarias, y el avatar
(`/avatar/logos.glb`, cargado con `GLTFLoader`). `setEvent(event)` resalta los
elementos del paso y elige el gesto (`Senala`, `Explica`, `Piensa`, `Saluda`);
`verdict(value)` reacciona al valor final; `talking`/`say`/`syllableCount`
sincronizan los labios por sílabas español con los morph targets `Boca_abierta`
y `Boca_redonda`; `dispose` libera geometrías, materiales, texturas, esqueletos y
el renderer. Respeta `prefers-reduced-motion` y detiene el bucle al ocultarse.
Exporta `syllables(word)`. No hay lógica matemática: solo dibuja el evento.

### 4.8 Estilos

`tokens.css` define la paleta (escalas `brand`, `accent`, `support`, `signal`,
`neutral`, estados) y los roles semánticos (`--canvas`, `--surface`, `--text`,
`--emph-N-*`, `--focus-ring`, …). `style.css` (661 líneas) contiene las
`@font-face` locales (Literata, IBM Plex Sans, JetBrains Mono NL), las variables
de espaciado/tipografía y la base de componentes. Orden de carga en
`index.html` (el posterior gana en igualdad de especificidad):

| # | Hoja | Cabecera / función |
|---|---|---|
| 1 | `tokens.css` | Paleta y roles. No se modifica. |
| 2 | `style.css` | Base, fuentes, componentes comunes. |
| 3 | `styles/shell.css` | Estructura: sidebar, barra superior, Inicio. |
| 4 | `styles/thread.css` | Motivos de «hilo» (variable `--thread`, separadores). |
| 5 | `styles/motion.css` | Micro-interacciones solo bajo `prefers-reduced-motion: no-preference`. |
| 6 | `styles/evaluator.css` | Asistente de tres pasos de Evaluar. |
| 7 | `features/explanation-player/player.css` | Reproductor (clases `ep-*`). |
| 8 | `styles/tour.css` | Tarjeta del recorrido. |
| 9 | `styles/dictionary.css` | Diccionario (dos columnas ≥ 1024 px; panel que reemplaza resultados por debajo). |
| 10 | `practice.css` | Taller de Practicar (acotado a `body[data-mode=practice]` y `.practice`). |
| 11 | `styles/responsive.css` | Ajustes responsive de Demostrar y Cuadernos. |
| 12 | `styles/home.css` | Inicio (hilo, titular, tarjetas, banner). |
| 13 | `styles/learn.css` | Aprender. |
| 14 | `styles/people.css` | Retratos y páginas de personas. |

Nota sobre el orden: `responsive.css` se carga antes que `home.css`, `learn.css`
y `people.css`, así que lo que esas tres definan con la misma especificidad
prevalece sobre `responsive.css`.

### 4.9 Recursos

| Ruta | Detalle |
|---|---|
| `avatar/logos.glb` | Avatar usado por `story3d.js`. Se genera con los scripts de `assets/avatar/realista/` (Blender, MediaPipe) a partir de `logos-avatar.blend`. No se sustituye. |
| `fonts/*.woff2` | Literata, IBM Plex Sans, JetBrains Mono (400 y 600), con sus licencias. |
| `vendor/` | `three.module.js`, `three.core.js`, `GLTFLoader.js`, `BufferGeometryUtils.js`, `SkeletonUtils.js` y `LICENSE-three.txt`. |
| `img/` | Retratos en escala de grises (copias locales con créditos en `img/CREDITOS.md`), marca `batz-*.svg`. |

### 4.10 `localStorage`

Todas las claves, encontradas con `grep` en `src/logos/web`:

| Clave | Quién | Contenido |
|---|---|---|
| `logos-sidebar` | `app.js` | `collapsed` o `expanded`. |
| `logos-cuaderno` | `app.js` | Id del último cuaderno abierto. |
| `logos-recorrido` | `tour/tour.js` | `completado` u `omitido`. |
| `logos-tarjetas` | `learn/deck.js` | `{v:1, known:[], review:[]}` de las tarjetas de teoría. |
| `logos.practice.v1` | `practice.js` | Progreso por ejercicio: jugadas, borrador, pistas, `revision`, `previous`. |

Todas las lecturas y escrituras están dentro de `try/catch`; sin almacenamiento
la aplicación funciona durante la sesión. No se guardan fórmulas, modelos ni
cuadernos en el navegador (los cuadernos viven en el servidor).

---

## 5. Contratos entre piezas

### 5.1 API pública del reproductor (`docs/specs/EXPLANATION_PLAYER.md`)

```js
const player = createExplanationPlayer({host, onStepChange, onStateChange});
player.load({resultId, origin, kind, title, story, model});
player.open(); player.pause(); player.minimize(); player.invalidate(motivo);
player.close(); player.clear(); player.getSnapshot(); player.destroy();
```

Implementación (`explanation-player/index.js`):

- `load`: exige `resultId` string. **El mismo `resultId` no hace nada** (conserva
  paso y estado); uno nuevo pausa, sale de pantalla completa, libera la escena,
  copia el payload con `structuredClone`, deja el índice en 0 y emite
  `onStepChange`. Rechaza `story.schema_version` distinto de `"1"`.
- Un guion sin eventos deja el estado `empty`, no se puede abrir y no emite
  `onStepChange`.
- `getSnapshot()` devuelve `{resultId, origin, kind, status: empty|ready|stale,
  presentation: closed|minimized|expanded, index, total, playing, voiceEnabled,
  threeDEnabled, rate}`.
- Audio desactivado por defecto; velocidades 0,75/1/1,25/1,5. La narración usa
  `speechSynthesis` con una voz española **local** o, si no hay, avanza por
  temporizador (`readingTime`). Solo un reproductor activo habla (`activePlayer`
  de módulo). Los callbacks viejos se invalidan con un contador `run`. Se pausa al
  ocultarse la pestaña.
- La escena 3D se importa dinámicamente (`import('../../story3d.js')`) solo al
  abrir; un `sceneGeneration` evita que una carga pendiente recree una escena
  tras `clear`, `load` o `destroy`. Si falla (sin WebGL, GLB, dominio > 12), queda
  el texto y la vista 2D (botones del dominio navegables con teclado).
- **Método adicional no contemplado en el contrato**: `exitFullscreen()`, que
  `app.js` usa en `pauseExplanations`.

Uso desde `app.js`: `explanationFor(origin)` crea una instancia por módulo
con el host `#player-evaluate`, `#player-prove` o `#player-notebook`;
`onStepChange` comprueba `resultId === entry.id` y llama a `highlightStep`
(en pruebas resalta `.fitch li[data-line=N]`; en Evaluar enmarca el `span` del
evento sobre la fórmula, salvo eventos `search` y `premise`); `onStateChange`
limpia resaltados cuando el reproductor deja de estar expandido y listo.
`showStory(story, model, host, {origin, kind, title})` hace `load` y añade el
botón «Explicación guiada» (`open` + scroll). `payload.model` es `null` en
pruebas.

### 5.2 Formato de paquete de ejemplos / importación

Un «paquete» es `{signature, interpretation|model, formula|formulas}`:

```json
{"schema_version": "1",
 "signature": {"constants": ["a"], "functions": {"s": 1}, "predicates": {"P": 1, "R": 2}},
 "interpretation": {"domain": [0,1,2], "constants": {"a": 0},
   "functions": {"s": {"arity": 1, "table": [[[0], 1], [[1], 2], [[2], 0]]}},
   "predicates": {"P": {"arity": 1, "tuples": [[0],[2]]},
                  "R": {"arity": 2, "tuples": [[0,1],[1,2],[2,0]]}}},
 "formula": "∀x ∃y R(x, y)"}
```

- «Exportar JSON» (`exportJSON`) genera exactamente eso (con `formula`).
- «Importar modelo» acepta eso o un `.logos` (2.13); `/api/load` devuelve
  `{signature, model, results}` y `applyPackage` rellena la interfaz.
- Los ejemplos de `features/evaluator/examples.js` usan otra forma compacta
  (`domain`, `constants`, `functions: {s: tabla}`, `predicates: {P: tuplas}`);
  `examplePackage` la convierte al paquete de arriba (deduce las aridades del
  primer elemento, por eso cada función o predicado debe tener al menos una
  fila).
- Cuadernos: `{version, title, created, sources, chat}`; `import` crea un cuaderno
  nuevo con esos datos limpiados por `_clean`.

### 5.3 Evaluación, de extremo a extremo

1. El usuario construye el modelo: `addSymbol` → `signature()`; «Preparar tablas»
   (`prepare`) crea selectores y casillas; `interpretation()` lee el JSON
   `{domain, constants, functions:{f:{arity, table}}, predicates:{P:{arity, tuples}}}`.
2. Escribir la fórmula dispara `updateFree()` → `POST /api/free`
   `{signature, formula}` → `project.libres` → `{status:"ok", variables:[…]}`; se
   crean los selectores de asignación.
3. «Verificar» → `evaluateFormula()` → `POST /api/evaluate`
   `{signature, interpretation, formula, assignment}`.
4. `handle_api` → `evaluar`: `build_interpretation` → `parse_checked(strict)` →
   `evaluate` (traza) → `explain` y `build_story` (que ejecutan `check_trace`) →
   `semantic_tree` y `syntax_tree`.
5. Respuesta: `{status:"ok", value, explanation, story, tree, syntax, model}`.
6. El navegador, si `rev === evalInputs`, pinta el veredicto, «Ver por qué»
   (`explanationElement`, visor de árbol) y `showStory(...)` carga el reproductor;
   `setStep(3)`. Si hubo error, `invalid_input` con `errors[0]` (`message`, `span`)
   se marca en la fórmula con `showSpan`.

### 5.4 Demostración, de extremo a extremo

1. Mientras se escribe, `scheduleProofCheck` → `POST /api/parse` `{formulas,
   constants}` → por fórmula `{ok, text, free, tree}` o `{ok:false, error}` y
   `mode`.
2. «Buscar prueba» → `proveFormula` → `POST /api/proof`
   `{premises:[…], conclusion, constants:[…]}` (3.4).
3. Según `status`:
   - `proved`: `fitch` (líneas con `n`, `depth`, `formula`, `rule`, `label`,
     `refs`, `box`…) y `story` (eventos `kind:"proof"`), más `contrast`. Se pinta
     `fitchElement`, `contrastElement` y `showStory(result.story, null, …)`.
   - `refuted` proposicional: `valuation` (pares), `premises`, `conclusion`; se
     pinta una tabla de valuación y `truthList`.
   - `refuted` de primer orden: `countermodel` (`model`, `assignment`,
     `premises`, `explanation`, `signature`, `loadable`, `story`, `log`). Botón
     «Abrir en Evaluar» (`openInEvaluate`, solo si `loadable`).
   - `unknown`: «Búsqueda inconclusa», con la razón (`PROOF_LIMITS`). Si B saturó,
     el rótulo es «No se sigue» (hay un modelo, aunque no apareció entre 1 y 3
     elementos).
4. `lastProof = {premises, conclusion, result, rev}` permite exportar con
   `buildProofHtml` solo mientras `rev === proofInputs`.

---

## 6. Pruebas

### 6.1 Python (`unittest`; 315 pruebas, 1 omitida, unos 37 s)

`PYTHONPATH=src:tests python3 -m unittest discover -s tests`. Se omite una
prueba solo de Windows (nombres cortos 8.3) y puede omitirse una de Cuadernos
si no hay etiquetador.

| Archivo | Cubre |
|---|---|
| `test_lexer_parser.py` | Léxico, precedencias, asociatividad, errores con spans, modo proposicional. |
| `test_printer_roundtrip.py` | Texto canónico, ASCII, round-trip adversarial y como igualdad estructural, nodos inválidos, inmutabilidad, spans fuera de la igualdad. |
| `test_transform_symbols.py` | Libres/ligadas, sustitución sin captura, alfa-equivalencia, firmas, aridades. |
| `test_semantics.py` | Evaluación, modelos inválidos, trazas, `check_trace` rechazando trazas manipuladas. |
| `test_serialize.py`, `test_project_m1.py` | Serialización del AST y fachada `evaluar`/`libres`. |
| `test_explain.py`, `test_story.py`, `test_tree.py` | Explicaciones, historias, árboles (corte a 500 nodos, valores de la traza verificada). |
| `test_propositional.py` | Tablas de verdad, `decide`, Kalmár frente a la tabla. |
| `test_proof_checker.py` | Cada regla del checker: aceptaciones y rechazos con el paso culpable; que el checker no importe el buscador. |
| `test_proof_search.py`, `proof_corpus.py` | Buscador sobre secuentes válidos e inválidos. |
| `test_fitch.py`, `test_proof_story.py` | Vista Fitch fiel al certificado y guion de pruebas. |
| `test_resolution.py` | Motor B y matriz de contraste. |
| `test_countermodels.py`, `test_modelfinder.py` | Búsquedas acotadas, límites, `unknown` sin afirmar validez, modelos reverificados. |
| `test_class_fixtures.py` | Ejercicios de clase (`docs/testing/ACCEPTANCE_FIXTURES.md`): ambos métodos y la convención de Kalmár. |
| `test_modelfile.py` | Archivos `.logos`/JSON. |
| `test_spanish.py`, `test_spanish_full.py`, `test_spanish_tagger.py` | Gramática, lecturas ambiguas, 51 casos de la especificación, etiquetador. |
| `test_lexicon.py`, `test_lexicon_audit.py`, `test_derived.py`, `test_synonyms.py` | Flexión, alta/baja de palabras, auditoría, diminutivos/participios, sinónimos y sentidos. |
| `test_notebook.py` | Oraciones, premisas con cita, respuestas, límites, API (vía `handle_api`). |
| `test_practice.py` | Tutor: reglas, contextos del servidor, jugadas inválidas, soluciones de los 50 ejercicios. |
| `test_voice_input.py` | Localización de ejecutables y de modelos, límites de audio (con procesos simulados). |
| `test_project_integration.py` | Casos de clase de primer orden, matriz negativa y un `ThreadingHTTPServer` real en puerto efímero (sirve la UI, `/api/free`, `/evaluate`, `/countermodel`, `/spanish`, `/proof`). |

### 6.2 Node (`node --test tests/frontend/app/*.test.mjs`; 41 pruebas)

`bios`, `export`, `learn` (17), `navigation` (6), `people`, `tour`: solo lógica
pura (rutas, estado del recorrido, progreso de tarjetas, construcción de HTML de
exportación, datos). No hay DOM.

### 6.3 Navegador (opcionales, requieren Playwright externo)

- `tests/frontend/player/` (`check.cjs`, `preview.html`, `fixtures.json`,
  `generate_fixtures.py`, `serve.py`): demo aislada y recorridos del reproductor
  con voz y escena simuladas (carreras, cancelaciones, pantalla completa, WebGL
  inexistente, GLB fallido).
- `scripts/validate_practice_browser.cjs`: validación de Practicar.
- `scripts/validate_demo.py`: ensayo HTTP local reproducible (solo biblioteca
  estándar).
- `scripts/report_spanish.py --check`: falla si algún caso de español no cumple.

### 6.4 Qué no cubren

- **No hay pruebas automáticas de `app.js` ni de `practice.js`** (ni de la
  lógica de descarte de respuestas, ni del asistente de Evaluar, Cuadernos o
  Diccionario en el navegador). Las comprobaciones de navegador que se citan en
  `docs/plans/entregas/INTEGRACION.md` se hicieron a mano con Playwright y no
  están en el repositorio como suite.
- No hay prueba que verifique que cada archivo del frontend está registrado en
  `do_GET` (solo se comprueban cinco recursos); ver 3.1.
- No hay prueba de `do_GET` con rutas hostiles, de límites de tamaño del cuerpo
  ni de códigos de error HTTP (`413`, `415`, `404`).
- No hay pruebas de concurrencia (varias peticiones a la vez, estado global del
  traductor).
- Las pruebas de voz simulan los ejecutables; no hay prueba con whisper real.
- No se prueba la calidad de la voz del navegador ni dispositivos táctiles reales.
- El checker se prueba contra casos escritos a mano y el corpus; no hay una
  verificación formal de la corrección del checker.

---

## 7. Seguridad y privacidad

- **Solo local por defecto.** `--host` es `127.0.0.1`. Docker publica
  `127.0.0.1:${LOGOS_PORT}:8765`; el contenedor escucha en `0.0.0.0` porque lo
  exige Docker, pero el mapeo del compose lo limita al anfitrión.
- **Lista controlada de archivos estáticos** (3.1); sin listado de directorios.
- **Sin red externa en tiempo de ejecución.** No hay `fetch` a otros orígenes:
  los tres `fetch` del frontend van a rutas relativas (`api`, `practice`,
  `voice/transcribe`); las URLs `http(s)://` que hay en JS son espacios de nombres
  SVG y enlaces de crédito de retratos (`target=_blank rel=noopener noreferrer`,
  que el usuario debe pulsar). Three.js, fuentes y avatar son locales.
- **Datos locales.** Cuadernos y léxico del usuario viven en `datos/` (o las
  rutas de entorno) en el equipo; `datos/*` está en `.gitignore`. El navegador
  guarda solo preferencias y progreso (4.10). Sin analítica.
- **Voz local.** El audio se procesa con ffmpeg y whisper.cpp locales dentro de un
  directorio temporal que se borra; `availability()` no filtra rutas absolutas.
- **Validación de entrada.** Tamaños, tipos y límites explícitos en cada ruta
  (3.6); identificadores de cuaderno validados por regex; archivos de cuaderno
  escritos con `.tmp` + `replace`; el cliente de Practicar nunca aporta contextos
  de prueba ni marcas de éxito. El frontend construye el DOM con `textContent`;
  los pocos `innerHTML` son cadenas SVG constantes. La exportación HTML escapa
  `& < > " '`.
- **Límites conocidos:**
  - El servidor **no comprueba `Origin` ni `Host`** y no exige que el
    `Content-Type` de los POST JSON sea `application/json`. Una página web
    cualquiera abierta en el mismo equipo podría enviar peticiones (por ejemplo
    `text/plain`) a `127.0.0.1:<puerto>` y modificar `datos/` (borrar o crear
    cuadernos, añadir palabras al léxico). No lo probé; se deduce de leer
    `do_POST`.
  - No hay autenticación; con `--host 0.0.0.0` cualquiera en la red puede usar y
    modificar los datos.
  - Las excepciones no capturadas (3.2) se imprimen con traceback en la terminal.
  - Procesamiento CPU intensivo en hilos del mismo intérprete (GIL): una
    búsqueda de 7 s ocupa la CPU, aunque no bloquea aceptar otras conexiones.
  - Los scripts `scripts/instalar_voz.*` descargan whisper.cpp y un modelo (con
    verificación de commit y SHA-256 según su cabecera); el de Linux/macOS está
    declarado «SIN PROBAR» en un sistema real.
  - Los retratos con licencia CC BY-SA exigen mostrar el crédito; el código lo
    hace con `needsVisibleCredit`.

---

## 8. Límites y deuda técnica comprobados

Solo lo que se vio leyendo o ejecutando.

### 8.1 Defectos reales

1. **La exportación de un contramodelo proposicional muestra una valuación
   incorrecta.** `export.js` (`buildProofHtml`) hace
   `Object.entries(result.valuation)`, pero `/api/proof` devuelve `valuation` como
   lista de pares `[letra, bool]` (`server._prove_propositional`). Con
   `[['p',true],['q',true],['r',false]]` el HTML exportado dice
   «0 = V, 1 = V, 2 = V» (lo comprobé ejecutando `buildProofHtml` en Node). La
   pantalla (`valuationElement`) sí itera pares y es correcta. La prueba
   `export.test.mjs` no cubre este caso.
2. **`app.js`, manejador de entrada de `proof-premises`/`proof-conclusion`/
   `proof-constants`:** llama a `clearStory()` **sin argumento**. Como
   `explanations[undefined]` no existe, no hace nada: al editar las premisas la
   explicación guiada de Demostrar no se marca como desactualizada por esa vía
   (sí se incrementa `proofInputs`, se vacía `#proof-result` y se re-revisa la
   sintaxis, pero el reproductor en `#player-prove` conserva su resultado sin
   aviso hasta el siguiente `proveFormula`). Las demás rutas usan `clearStory('prove')`.
3. **Estado global del traductor sin bloqueo en `/api/spanish`.**
   `spanish_semantics.EXTRA` y `SENSE` son globales que `translate_spanish` llena y
   vacía; el servidor es `ThreadingHTTPServer`. `notebook.api` los protege con un
   `RLock`, pero `/api/spanish` y `lexicon.add/remove` (`reload`) no lo toman, así
   que dos peticiones simultáneas podrían mezclar sentidos. No lo reproduje.
4. **Excepciones sin capturar en `do_POST`** (`AssertionError`, `KeyError`,
   `OSError`, `RecursionError`): sin respuesta HTTP ni JSON de error (3.2).

### 8.2 Deuda de estructura

- `app.js` es monolítico: 2322 líneas, 140 funciones de primer nivel en un solo módulo, con
  estado compartido de módulo (`domain`, `preparedSignature`, `nb`, `dictState`…).
  Solo la navegación, la exportación y los datos están separados y probados.
- Código y comentarios de estado antiguo: `style.css` conserva `.dict-table` (y
  su regla responsive) y `.lab-grid`, que no aparecen en `index.html` ni en
  ningún JS (comprobado por búsqueda); el diccionario actual usa
  `styles/dictionary.css`. En `app.js` la condición
  `document.body.dataset.sidebarManual` nunca puede ser verdadera: nadie la
  asigna.
- `PRACTICE_COUNT = 50` en `features/home/home.js` se mantiene a mano
  (comentario incluido); hoy coincide con `len(practice_bank.EXERCISES)` = 50, pero
  ninguna prueba lo vigila.
- `do_GET` reconstruye el diccionario de 63 rutas en cada petición y no manda
  `Cache-Control`; la lista se mantiene a mano (3.1).
- `server.py` importa privados de otros módulos (`_Parser`, `_MATRIX`,
  `lexicon._validate`); `notebook.py` importa `_MATRIX`.
- El servidor no usa `propositional.decide` ni `result_to_dict`: construye sus
  propios sobres con estados (`refuted`) distintos de los de `serialize.py`
  (`counterexample`). Hay dos vocabularios de resultado.
- `notebook._view` y `ask` re-traducen todas las oraciones de todas las fuentes
  en cada llamada (sin caché); con 20 fuentes de 150 oraciones cada petición
  repite ese análisis. Es deliberado (siempre se ve el estado actual del
  diccionario) pero cuesta.
- `spanish_semantics.py` mantiene tablas `NOUN`, `ADJ`, `VERB`, `PLURAL`… con
  palabras de la especificación inicial junto al léxico general (`lexicon`); la
  precedencia entre ambos está en `Composer.nominal`.
- El etiquetador y el léxico dependen de `plain()` de `spanish_tagger.py`
  (acoplamiento léxico → etiquetador).
- Búsqueda: el motor A es incompleto por diseño y sus límites (profundidad 6,
  20 000 nodos, 3 s en el servidor) son fijos en el código; no hay forma de
  ampliarlos desde la UI. El tope de 3 elementos para contramodelos y los 12
  elementos máximos de la escena 3D también.
- `fitch.py` (280 líneas) y `spanish_semantics.py` (387) concentran bastante
  lógica con pocos comentarios más allá de las cabeceras.
- El contrato `docs/specs/EXPLANATION_PLAYER.md` y los documentos de
  `docs/plans/` describen el reparto de trabajo entre agentes, no la arquitectura
  actual.

---

## 9. Discrepancias entre documentación y código

| Documento | Dice | El código |
|---|---|---|
| `docs/architecture/ARCHITECTURE.md` §2 | `countermodel.py` «Fase 4», `spanish/` «Fase 5» y `explain/` «Fase 7» están planeados. | Existen como `countermodels.py` (+ `modelfinder.py`), `spanish.py`/`spanish_cyk.py`/`spanish_semantics.py` y `explain.py`/`story.py`/`proof_story.py`. La tabla tampoco lista `project.py`, `interpretation.py`, `modelfinder.py`, `notebook.py`, `practice*.py`, `voice_input.py`, `tree.py`, `story.py`, `proof_story.py`, `proof/fitch.py` ni `proof/render.py`. |
| `docs/architecture/ARCHITECTURE.md` §5 | La interfaz será React + Three.js/R3F; el modo de llegar al navegador está pendiente (Q1). | Servidor local en `server.py` con JavaScript nativo, sin React; Three.js va copiado en `web/vendor/`. |
| `docs/specs/JSON_CONTRACTS.md` §5 | Contramodelo con `assignment` como mapa y bloque `search` (`explored_sizes`, `max_size`, `minimal_in_explored`); «se implementa en Fase 4». | `CountermodelSearch.to_dict()` devuelve `status`, `explored`, `completed_sizes`, `log`, `model`, `explanation`, `story`; `ConsequenceSearch.to_dict()` añade `assignment` como lista de pares, `premises`, `signature`, `loadable`. No hay `search` ni `minimal_in_explored`. |
| `JSON_CONTRACTS.md` §6 | Evento con `step_ref`, `kind: "apply_rule"`, `highlight`. | Los eventos reales usan `trace_path`, `kind` ∈ `predicate`, `equality`, `quantifier`, `connective`, `bottom`, `proof`, `search`, `premise`, y para pruebas `step_id`, `line`, `rule`, `rule_label`, `refs`, `context`, `depth`, `steps`; no existen `step_ref` ni `highlight`. |
| `JSON_CONTRACTS.md` §7 | `status` ∈ `proved`, `counterexample`, `inconsistent`, `unknown`, `invalid_input`; error en `diagnostic`. | `/api/proof` responde `proved`, `refuted`, `unknown` o `invalid_input`, con `errors` (lista) en lugar de `diagnostic`, y campos propios (`mode`, `fitch`, `story`, `contrast`, `valuation`, `countermodel`, `search`). `counterexample` y `diagnostic` solo salen de `serialize.result_to_dict`. |
| `JSON_CONTRACTS.md` §8 | Lista solo `free`, `validate`, `evaluate`, `countermodel`, `spanish`, `proof` (y `story`). | El servidor tiene además `/api/parse`, `/api/load`, `/api/lexicon/*`, `/api/notebook/*`, `/api/practice/*` y `/api/voice/*`, sin documentar en ese archivo. `/api/evaluate` también devuelve `tree` y `syntax`. |
| `docs/specs/EXPLANATION_PLAYER.md` (cabecera) | «Los módulos y métodos siguientes todavía no existen en la base `40e636a`». | Existen (`index.js`, `events.js`, `fullscreen.js`, `player.css`, `story3d.js`) y `app.js` los usa. El reproductor añade `exitFullscreen()`, no listado en §3. |
| `README.md` y `AGENTS.md` | El rediseño está «documentado y pendiente de implementación»; «la barra superior cambia entre cinco modos»; botones «Ejemplo» y «Cargar archivo». | En esta rama la interfaz está implementada con barra lateral y siete secciones (Inicio, Evaluar modelo, Demostrar, Practicar, Cuadernos, Diccionario, Aprender); los botones se llaman «Cargar ejemplo» e «Importar modelo». Los comentarios de `ejemplos/*.logos` también dicen «Cargar archivo». El README también habla de `#practicar`; la ruta actual es `#/practicar` (el antiguo se tolera). |
| `docs/plans/entregas/INTEGRACION.md` | `navigation.test.mjs` tiene 4 pruebas. | Tiene 6 (se añadieron las rutas de personas). |
