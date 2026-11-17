# Arquitectura de Bat’z

> Estado: actualizado a la rama de entrega. Todos los módulos de la tabla existen y tienen pruebas. Este documento es la vista de diseño (flujo, reglas de dependencia, dos caminos de prueba); el recorrido por el código, con funciones y límites, está en [`docs/ARQUITECTURA.md`](../ARQUITECTURA.md). El proyecto se llamaba Bat’z antes del renombrado a Bat’z; el paquete Python es `batz` (`src/batz/`).

## 1. Flujo de datos

```
texto formal ──► lexer ──► parser ──► FormulaAST ──┬─► semántica (modelo finito) ──► verdad / traza
                                                   ├─► decisor proposicional (tabla de verdad) ──► contramodelo verificado
español controlado ──► gramática CYK + léxico ─────┤
voz (whisper.cpp, opcional) ─► español controlado  ├─► motor A: deducción natural ──► ProofCertificate ─┐
                                                   └─► motor B: resolución, solo oráculo de contraste   │
                                                                                                         ▼
UI web / voz / Three.js ◄── story.py, proof_story.py, explain.py ◄── resultado verificado ◄── checker independiente
```

El español y la voz **no son motores**: son adaptadores de entrada que producen el mismo `FormulaAST` que el parser formal. Nada aguas abajo sabe de dónde vino la fórmula.

## 2. Módulos (`src/batz/`)

Todos existen. «Hecho» significa con código y pruebas en `tests/`.

| Módulo | Estado | Responsabilidad | Depende de |
|---|---|---|---|
| `ast.py` | hecho | Nodos inmutables; los constructores rechazan nodos mal formados | — |
| `errors.py` | hecho | `BatzError` (nombre conservado del código anterior) y el contrato `Diagnostic` | — |
| `lexer.py`, `parser.py` | hecho | Tokens con offsets; parser descendente; modo opcional `propositional` | ast, errors |
| `printer.py` | hecho | Texto canónico Unicode/ASCII, `parse(print(f)) == f` | ast |
| `transform.py` | hecho | Libres/ligadas, alfa-equivalencia, sustitución sin captura | ast |
| `symbols.py` | hecho | Tabla de símbolos, aridades, firma, `parse_checked` | ast, parser |
| `model.py`, `semantics.py` | hecho | `FiniteModel`, evaluación, trazas verificables, `check_trace`, `is_countermodel` | ast, transform |
| `interpretation.py` | hecho | `build_interpretation`: modelo estricto del proyecto (dominio no vacío, funciones totales, relaciones no vacías, coincidencia exacta con la firma) | model, symbols |
| `project.py` | hecho | Fachada `evaluar` / `libres`: única puerta de la interfaz para evaluar; `invalid_input` nunca lleva valor | interpretation, semantics, explain, story |
| `explain.py` | hecho | Explicación determinista (testigo, contraejemplo, comprobación completa); verifica la traza antes de narrar | semantics |
| `story.py`, `proof_story.py` | hecho | Guiones de eventos para el reproductor (evaluación, contramodelo, pruebas), cada evento con su respaldo verificado | semantics, proof |
| `tree.py` | hecho | Árboles sintáctico y de evaluación para el visor, leídos de la traza ya verificada | semantics |
| `propositional.py` | hecho | Decisor exacto por tabla de verdad, lema de Kalmár (`kalmar_sequent`) | semantics |
| `serialize.py` | hecho | JSON versionado de `FormulaAST` y sobre de resultado (`result_to_dict`) | ast, printer |
| `proof/certificate.py` | hecho | `ProofCertificate`, `ProofStep`, `ProofError` | ast, parser |
| `proof/checker.py` | hecho | **Checker independiente** | ast, transform, certificate |
| `proof/search.py` | hecho | Motor A: búsqueda en deducción natural | ast, transform, certificate |
| `proof/kalmar.py` | hecho | Prueba proposicional completa y determinista | propositional, search (solo constructores) |
| `proof/fitch.py` | hecho | Vista Fitch del certificado; `check_layout` comprueba su fidelidad | certificate |
| `proof/render.py` | hecho | Texto legible de un certificado (`format_certificate`) | certificate |
| `proof/__init__.py` | hecho | `prove`, `prove_text`, `find_inconsistency`; compone buscador + checker | todo lo anterior |
| `resolution/` (`clausify.py`, `prover.py`) | hecho | Motor B: forma clausal, unificación y resolución con factorización; solo oráculo de contraste | ast, transform |
| `countermodels.py` | hecho | Buscador de contramodelos finitos con cotas explícitas (sentencias y consecuencias); revalida cada hallazgo | model, semantics |
| `modelfinder.py` | hecho | Búsqueda de modelos desplegando cuantificadores sobre dominios pequeños (muchas premisas, Cuadernos) | model, semantics |
| `modelfile.py` | hecho | Lee archivos `.logos` y JSON con un modelo y sus fórmulas | errors |
| `lexicon.py`, `lexicon.tsv` | hecho | Diccionario del español: lemas, flexión, sinónimos, sentidos, formas derivadas y altas del usuario | errors |
| `spanish_tagger.py`, `spanish_tagger.json` | hecho | Propone la categoría de palabras fuera del léxico; la gramática decide si encaja y la interfaz declara el supuesto | — |
| `spanish.py`, `spanish_cyk.py`, `spanish_semantics.py`, `spanish_grammar.txt` | hecho | Español controlado: análisis con CYK, lecturas múltiples y composición de fórmulas | ast, parser, lexicon |
| `notebook.py` | hecho | Cuadernos: fuentes en español, premisas con cita y respuestas con prueba o contramodelo | spanish, proof, resolution, modelfinder |
| `practice.py`, `practice_bank.py` | hecho | Practicar: 50 ejercicios y tutor que recalcula los contextos en el servidor | proof |
| `voice_input.py` | hecho | Transcripción local opcional (whisper.cpp + ffmpeg) | — |
| `voice_output.py` | hecho | Voz local opcional (espeak-ng) que genera el WAV de la narración | — |
| `server.py` | hecho | Servidor HTTP local, API JSON y lista controlada de archivos estáticos | todo lo anterior |
| `web/` | hecho | Interfaz en JavaScript nativo (módulos ES), Three.js en `web/vendor/`, avatar GLB | — (consume JSON) |

## 3. Reglas de dependencia (se verifican)

1. **El checker no importa ni usa el buscador.** Hay una prueba que escanea los imports de `checker.py`. Solo así «aceptado por el checker» significa algo.
2. **`proved` e `inconsistent` solo existen con certificado aceptado.** `proof.__init__._run` verifica el certificado antes de afirmar; si el checker lo rechaza, el resultado es `unknown` con `reason = "checker_rejected"`.
3. **`counterexample` (y `refuted` en la API local) solo existe con modelo reevaluado** por `is_countermodel` (el evaluador de la Fase 2, no el que lo construyó).
4. **Ningún LLM ni umbral de confianza decide validez ni elige entre lecturas.** Los modelos de lenguaje, si se usan, solo proponen sugerencias que pasan por la gramática y la confirmación del usuario (ver `06-FASE-5-ESPANOL.md`).
5. **El frontend no contiene lógica.** Consume JSON versionado (`JSON_CONTRACTS.md`) y solo dibuja certificados aceptados o contramodelos verificados.
6. La semántica no se altera por conveniencia de la UI. Un cambio de semántica exige actualizar `SEMANTICS.md` y las pruebas que la respaldan.

## 4. Dos caminos de prueba

| Lógica | Camino 1 | Camino 2 | Qué se garantiza |
|---|---|---|---|
| **Proposicional** | Búsqueda en deducción natural (`search.py`) | Algoritmo de Kalmár (`kalmar.py`) + tabla de verdad como oráculo | **Siempre** hay veredicto: `proved` (certificado) o `counterexample` (modelo). `decide` intenta el buscador y cae a Kalmár. |
| **Primer orden** | Búsqueda en deducción natural | Motor B de resolución, solo contraste | **No** hay veredicto garantizado: la validez es indecidible. `unknown` es respuesta legítima. |

Los dos caminos se comparan en las pruebas: si uno prueba algo que el otro refuta, hay un bug de corrección. Si el buscador no prueba algo que Kalmár sí, queda registrado como hueco de completitud (ya pasó una vez: `docs/decisions/OPEN_QUESTIONS.md`, ADR-005).

## 5. Pila tecnológica

- **Núcleo y servidor: Python estándar, sin dependencias externas** (3.10 o posterior). Justificación: portable, auditable, sin riesgo de instalación el día de la demo. Las pruebas usan `unittest` y generadores aleatorios propios.
- **Interfaz: JavaScript nativo con módulos ES**, sin framework, bundler ni CDN. Las hojas de estilo son CSS plano con una paleta común (`tokens.css`). **Three.js** (0.187.0) y sus cargadores van copiados en `src/batz/web/vendor/` y el avatar es un GLB local (`web/avatar/logos.glb`); las fuentes son woff2 locales. La decisión Q1 de `OPEN_QUESTIONS.md` se resolvió con la opción (a): un servidor local (`http.server`) que sirve la interfaz y una API JSON.
- **Voz de salida:** primero las voces locales del navegador; si no hay, `espeak-ng` en el servidor (`voice_output.py`), también dentro de Docker.
- **Voz de entrada:** whisper.cpp opcional, siempre con confirmación de la persona antes de traducir.
- **Contenedor:** `Dockerfile` con `python:3.12-slim` y `espeak-ng`; `docker-compose.yml` lo publica en `127.0.0.1:8765`.

## 6. Estado del reparto

El reparto original en tres roles (compilador y lenguaje; motor lógico; experiencia) se cumplió: el lenguaje y el español controlado (rol A), la semántica, las pruebas y los contramodelos (rol B) y la interfaz, el reproductor y la voz (rol C) existen y están probados. Todos revisan los fixtures matemáticos y los contratos; la revisión cruzada firmada por personas sigue pendiente (`docs/validation/REVISION-EQUIPO.md`).
