# Guía para revisar Bat’z (catedrático)

Esta guía responde a una pregunta: **dado cada requisito del plan del proyecto, ¿dónde se ve en la aplicación, dónde está el código y qué prueba lo cubre?** Los requisitos salen de [`docs/plans/PLAN_MM3032.md`](plans/PLAN_MM3032.md) (§1, §2, §3 y §5), que a su vez resume el enunciado `MM3032 - Proyecto.pdf`; el PDF no está en el repositorio, así que no se citan requisitos que el plan no recoge. Bat’z se llamaba LOGOS: los archivos de pruebas y la documentación histórica pueden conservar ese nombre.

Para ejecutarlo sin instalar nada propio, ver el [README](../README.md#probar-en-1-minuto). Las rutas de código son `src/batz/…` y las de pruebas, `tests/…`. Las pruebas de Python se ejecutan con `PYTHONPATH=src:tests python3 -m unittest discover -s tests` (325 pruebas, 1 omitida) y las de Node con `node --test tests/frontend/app/*.test.mjs` (48).

## 1. Criterios de la rúbrica y dónde se cubren

| Criterio (plan §1) | Puntos | Dónde mirar |
|---|---|---|
| Evaluación semántica y justificación | 30 | Tabla de requisitos 1–3, 6 y 7 (abajo). Evaluar → resultado → «Ver por qué» y «Árbol» |
| Análisis sintáctico | 10 | Requisitos 3 y 7; errores con posición en la fórmula |
| Interfaz gráfica | 10 | Requisitos 1, 2, 4 y 5; la aplicación completa |
| Defensa individual | 30 | [`DEFENSA.md`](DEFENSA.md): cada módulo y 15 preguntas con respuesta |
| Aportes creativos | 20 | Sección 3 de esta guía |

## 2. Los siete requerimientos del núcleo (plan §2)

| # | Requisito del plan | Dónde se ve en la app | Dónde está el código | Qué prueba lo cubre |
|---|---|---|---|---|
| 1 | **Lenguaje configurable** (constantes, símbolos funcionales y predicados con aridad; el plan presenta las constantes como funciones de aridad 0) | **Evaluar modelo**, paso 1 «Construye el modelo»: tabla de símbolos con nombre, tipo y aridad | `symbols.py` (`Signature`, `check` con `strict=True`, `parse_checked`); `server.py` (`_signature`) | `tests/test_transform_symbols.py` (firmas y aridades); `tests/test_project_m1.py` (`test_invalid_interpretations`, `test_predicate_zero_arity_rejected_at_project_boundary`) |
| 2 | **Interpretación** (dominio no vacío, funciones totales, relaciones no vacías, coincidencia exacta con la firma) | Paso 1: dominio y una tabla por símbolo (celda por cada `Dⁿ`; casillas por cada tupla); «Verificar» queda bloqueado si falta algo, y el dominio vacío o una relación vacía dan su propio mensaje | `interpretation.py` (`build_interpretation`); `model.py` (`FiniteModel`) | `tests/test_project_m1.py` (`StrictInterpretation`, `test_empty_domain_has_its_own_message`); `tests/test_semantics.py` (`ModelAndSymbolErrors`) |
| 3 | **Todos los conectivos** `¬ ∧ ∨ → ↔ ∀ ∃` (además `⊥`, `=`, `≠`; ASCII y Unicode) | Los botones de símbolos sobre el campo de la fórmula y el teclado; la ayuda («Guía de símbolos») lista las equivalencias ASCII | `lexer.py`, `parser.py`, `ast.py`, `printer.py`; `semantics.py` (`evaluate`) | `tests/test_lexer_parser.py` (precedencias, asociatividad, equivalentes ASCII, errores con posición); `tests/test_printer_roundtrip.py`; `tests/test_semantics.py` (`ConnectiveTruthTables`, `QuantifierSemantics`, comparación contra un oráculo) |
| 4 | **Variables libres y entorno** | Paso 2: al escribir la fórmula aparecen las variables libres con un selector de elementos de `D`; el entorno se valida antes de evaluar | `transform.py` (`free_vars`); `project.py` (`libres`, `evaluar`); `/api/free` | `tests/test_project_m1.py` (`test_free_variables_and_input_errors`, `test_environment_only_assigns_variables`); `tests/test_semantics.py` (`OpenFormulas`) |
| 5 | **Interfaz gráfica** (botones `¬ ∧ ∨ → ∀ ∃ ( )` y teclado) | Toda la aplicación: asistente de tres pasos de Evaluar, con el teclado lógico, tablas editables y mensajes en español | `src/batz/web/` (`index.html`, `app.js`, `features/`, `styles/`); `server.py` | `tests/test_project_integration.py` (`LocalHTTP`: un servidor real sirve la interfaz y la API); `tests/frontend/app/*.test.mjs` (lógica pura del frontend). **No hay prueba automática del DOM:** el recorrido visual se verificó a mano con Playwright (ver [`validation/ENSAYO-MM3032.md`](validation/ENSAYO-MM3032.md) y el plan §6) |
| 6 | **Resultado y explicación** (testigo, contraejemplo o comprobación completa; la explicación nunca contradice el valor) | Paso 3 «Resultado»: veredicto Verdadero/Falso, «Ver por qué» (árbol de razones), «Árbol» (evaluación y estructura) y «Explicación guiada» | `semantics.py` (`evaluate` y `check_trace`); `explain.py`; `story.py`; `tree.py` | `tests/test_semantics.py` (`Traces`: `check_trace` rechaza trazas manipuladas); `tests/test_explain.py`; `tests/test_story.py`; `tests/test_tree.py` (cada valor coincide con sus hijos) |
| 7 | **Validación**: una entrada inválida nunca muestra Verdadero ni Falso | Escribir `P(a,a)`, un símbolo no declarado o dejar una celda vacía: aparece el diagnóstico (con la posición subrayada) y ningún veredicto | `project.py` (`evaluar` devuelve `invalid_input` sin valor ni traza); `errors.py` (`LogosError`, diagnósticos); `symbols.py` | `tests/test_project_integration.py` (`test_negative_matrix`: sintaxis, símbolo no declarado, aridad, dominio vacío, tupla inválida, asignación faltante y fuera de `D`); `tests/test_project_m1.py` (`test_malformed_formula_and_environment`) |

El plan §6 deja constancia de una auditoría contra el PDF (2026-11-11) con 30 fórmulas y 23 interpretaciones inválidas, y de la decisión sobre predicados 0-arios (aridad ≥ 1 en el perfil del proyecto; `DEFENSA.md`, pregunta 8).

## 3. Aportes creativos (plan §5)

El plan recomienda tres (visualizador del árbol, buscador de contramodelos, exportación JSON) y propone tener implementados y justificados dos o tres. Hay además otros que ya existían o se añadieron.

| Aporte | Dónde se ve | Código | Pruebas |
|---|---|---|---|
| **Visualizador del árbol de evaluación** (colapsable, valores V/F, una rama por elemento) | Evaluar → resultado → «Árbol»; también en cada lectura del español y en Demostrar | `tree.py`; visor SVG en `web/app.js` | `tests/test_tree.py` |
| **Buscador de contramodelos** («un modelo donde sea falsa»), con cotas y `unknown` honesto | Evaluar, paso 2, botón «Buscar dónde sea falsa»; Demostrar cuando «no se sigue» | `countermodels.py`, `modelfinder.py` | `tests/test_countermodels.py`, `tests/test_modelfinder.py` |
| **Exportar e importar JSON** y archivos de texto `.logos` | «Exportar JSON»; «Importar modelo» o soltar el archivo en la página; `ejemplos/grafo.logos` y `ejemplos/personas.logos` | `serialize.py`, `modelfile.py`; `/api/load` | `tests/test_modelfile.py`, `tests/test_serialize.py` |
| **Demostrar**: verificador independiente de pruebas por deducción natural (vista Fitch) y decisión proposicional (Kalmár) | Demostrar → «Buscar prueba» | `proof/` (`checker.py`, `search.py`, `kalmar.py`, `fitch.py`), `propositional.py` | `tests/test_proof_checker.py`, `tests/test_proof_search.py`, `tests/test_fitch.py`, `tests/test_propositional.py`, `tests/test_class_fixtures.py` |
| **Segundo motor** (resolución) como contraste independiente | En Demostrar, bajo la prueba: «Los dos motores coinciden» | `resolution/` | `tests/test_resolution.py` |
| **Español controlado** con todas las lecturas, diccionario y etiquetador | Evaluar, paso 2: «O escríbela en español»; sección Diccionario | `spanish*.py`, `lexicon.py`, `spanish_tagger.py` | `tests/test_spanish.py`, `tests/test_spanish_full.py` (los 51 casos), `tests/test_lexicon.py`, `tests/test_synonyms.py`, `tests/test_spanish_tagger.py` |
| **Explicación guiada** con avatar 3D y voz opcional | «Explicación guiada» en Evaluar, Demostrar y Cuadernos | `story.py`, `proof_story.py`; `web/features/explanation-player/`, `web/story3d.js`; `voice_output.py` | `tests/test_story.py`, `tests/test_proof_story.py`, `tests/test_voice_output.py`, `tests/frontend/app/voices.test.mjs`; `tests/frontend/player/check.cjs` (navegador, opcional) |
| **Cuadernos**: preguntas a tus propias fuentes, con cita y prueba | Cuadernos → «Crear el cuaderno de ejemplo» → «¿Juan aprueba?» | `notebook.py` | `tests/test_notebook.py` |
| **Practicar**: 50 demostraciones interactivas con tutor | Practicar | `practice.py`, `practice_bank.py`; `web/practice.js` | `tests/test_practice.py` |

## 4. Garantías de corrección que conviene comprobar

| Afirmación | Cómo se garantiza | Dónde verlo |
|---|---|---|
| «Demostrada» solo con una prueba revisada por un verificador **independiente del buscador** | `proof/checker.py` no importa el buscador; `proved` exige certificado aceptado | `tests/test_proof_checker.py` (escanea los imports del checker); `docs/architecture/ARCHITECTURE.md` §3 |
| «Contramodelo» solo si el evaluador lo confirma | Cada hallazgo se reevalúa con `is_countermodel` (el evaluador de la fase 2, no el buscador) | `tests/test_countermodels.py` |
| **Inconcluso no es falso ni demostrado** | La búsqueda es incompleta por diseño (la validez en primer orden es indecidible): al agotar límites responde `unknown` | Demostrar → tarjeta «A veces la búsqueda no decide»; [`specs/JSON_CONTRACTS.md`](specs/JSON_CONTRACTS.md) §8.3 |
| La explicación no inventa el resultado | `explain` y `build_story` llaman antes a `check_trace`; el árbol se lee de la misma traza | `tests/test_explain.py`, `tests/test_tree.py` |
| Dos motores independientes | Deducción natural (motor A) y resolución (motor B); el B solo contrasta y nunca convierte `unknown` en `proved` | `docs/DEFENSA.md` (fila `resolution/`); `tests/test_resolution.py` |

## 5. Orden sugerido para una revisión de 15 a 20 minutos

1. Leer el [README](../README.md) y seguir su «Recorrido de 5 minutos».
2. Recorrer la tabla de la sección 2 de este documento escribiendo una **fórmula no preparada** sobre el modelo del ejemplo y prediciendo el valor a mano antes de pulsar «Verificar» (el plan §6 pide ensayar así).
3. Probar entradas inválidas de la matriz del requisito 7.
4. Mirar uno de los aportes de la sección 3 con el que se quiera profundizar, y su prueba.
5. Ejecutar las pruebas (sección «Pruebas» del README).

## 6. Lo que el plan deja pendiente

Está en [`validation/REVISION-EQUIPO.md`](validation/REVISION-EQUIPO.md) y en el plan §7–§8: la fecha de entrega y de defensa, la revisión cruzada firmada por personas, el ensayo audible en un equipo con voz española, la confirmación humana del diccionario (el léxico lo generó un asistente y no tiene revisión humana) y una prueba en un teléfono real. No son defectos del código: son tareas de personas.
