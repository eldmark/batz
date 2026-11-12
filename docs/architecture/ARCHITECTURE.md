# Arquitectura de LOGOS

> Estado: borrador de Fase 0 para revisión. Describe lo que **existe** (Fases 1–3 más el decisor proposicional) y lo que está **planeado**; cada módulo indica cuál es cuál.

## 1. Flujo de datos

```
texto formal ──► lexer ──► parser ──► FormulaAST ──┬─► semántica (modelo finito) ──► verdad / traza
                                                   ├─► decisor proposicional (tabla de verdad) ──► contramodelo verificado
español controlado ──► (adaptador, Fase 5) ────────┤
voz (Whisper, opcional) ─► español controlado      ├─► motor A: deducción natural ──► ProofCertificate ─┐
                                                   └─► motor B: resolución, solo oráculo de contraste   │
                                                                                                         ▼
UI / TTS / Three.js ◄── ExplanationBuilder (Fase 7) ◄── resultado verificado ◄──────────────── checker independiente
```

El español y la voz **no son motores**: son adaptadores de entrada que producen el mismo `FormulaAST` que el parser formal. Nada aguas abajo sabe de dónde vino la fórmula.

## 2. Módulos (`src/logos/`)

| Módulo | Estado | Responsabilidad | Depende de |
|---|---|---|---|
| `ast.py` | hecho | Nodos inmutables; los constructores rechazan nodos mal formados | — |
| `errors.py` | hecho | `LogosError` y el contrato `Diagnostic` | — |
| `lexer.py`, `parser.py` | hecho | Tokens con offsets; parser descendente; modo opcional `propositional` | ast, errors |
| `printer.py` | hecho | Texto canónico Unicode/ASCII, `parse(print(f)) == f` | ast |
| `transform.py` | hecho | Libres/ligadas, alfa-equivalencia, sustitución sin captura | ast |
| `symbols.py` | hecho | Tabla de símbolos, aridades, firma | ast, parser |
| `model.py`, `semantics.py` | hecho | `FiniteModel`, evaluación, trazas verificables, `is_countermodel` | ast, transform |
| `propositional.py` | hecho | Decisor exacto por tabla de verdad, lema de Kalmár (`kalmar_sequent`) | semantics |
| `serialize.py` | hecho | JSON versionado de `FormulaAST` y sobre de resultado | ast, printer |
| `proof/certificate.py` | hecho | `ProofCertificate`, `ProofStep`, `ProofError` | ast, parser |
| `proof/checker.py` | hecho | **Checker independiente** | ast, transform, certificate |
| `proof/search.py` | hecho | Motor A: búsqueda en deducción natural | ast, transform, certificate |
| `proof/kalmar.py` | hecho | Prueba proposicional completa y determinista | propositional, search (solo constructores) |
| `proof/__init__.py` | hecho | `prove`, `prove_text`, `find_inconsistency`; compone buscador + checker | todo lo anterior |
| `countermodel.py` | **Fase 4** | Buscador de contramodelos finitos con cotas explícitas | model, semantics |
| `resolution/` | hecho | Motor B: forma clausal, unificación y resolución con factorización; solo oráculo de contraste (`contrast`) | ast, transform |
| `spanish_tagger.py` | hecho | Propone la categoría de palabras fuera del léxico (modelo entrenado en `scripts/train_spanish_tagger.py`); la gramática decide si encaja y la interfaz declara el supuesto | — |
| `modelfile.py` | hecho | Lee archivos `.logos` y JSON con un modelo y sus fórmulas | errors |
| `spanish/` | **Fase 5** | Aho-Corasick, léxico, CYK, adaptador a `FormulaAST` | ast, parser |
| `explain/` | **Fase 7** | `ExplanationBuilder` determinista | certificado verificado |

## 3. Reglas de dependencia (se verifican)

1. **El checker no importa ni usa el buscador.** Hay una prueba que escanea los imports de `checker.py`. Solo así «aceptado por el checker» significa algo.
2. **`proved` e `inconsistent` solo existen con certificado aceptado.** `proof.__init__._run` verifica el certificado antes de afirmar; si el checker lo rechaza, el resultado es `unknown` con `reason = "checker_rejected"`.
3. **`counterexample` solo existe con modelo reevaluado** por `is_countermodel` (el evaluador de la Fase 2, no el que lo construyó).
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

- **Núcleo: Python estándar, sin dependencias externas.** Justificación: portable para tres personas, auditable, sin riesgo de instalación el día de la demo. Las pruebas usan `unittest` y generadores aleatorios propios porque `pytest` y `hypothesis` no estaban instalados y no se instalan dependencias sin aprobación.
- **Interfaz:** React + Three.js / React Three Fiber (Fase 6–7), consumiendo JSON. **Pendiente de decisión** (Q1 en `OPEN_QUESTIONS.md`): cómo llega el núcleo Python al navegador de forma offline (servidor local, Pyodide, o resultados precalculados + servidor).
- **Voz:** síntesis del navegador primero; Whisper opcional como entrada, siempre con confirmación.

## 6. Reparto sugerido (tres integrantes)

| Rol | Alcance | Ya cubierto en el código |
|---|---|---|
| A — compilador y lenguaje | lexer, parser, AST, gramática, español controlado | Fase 1; Fase 5 en borrador |
| B — motor lógico | semántica, pruebas, checker, contramodelos, motor B | Fases 2–3 |
| C — experiencia | frontend, renderer, voz, animación | nada aún |

Todos revisan los fixtures matemáticos y los contratos. La revisión cruzada es el gate real de cada fase (ver `IMPLEMENTATION_PLAN.md`).
