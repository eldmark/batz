# Decisiones, auditoría y preguntas abiertas

> Estado: Fase 0, 2026-10-21. Tres secciones: (1) auditoría de los documentos del roadmap, (2) registro de decisiones (ADR), (3) preguntas abiertas para el equipo.

## 1. Auditoría de consistencia y factibilidad del roadmap

Hallazgos al leer `00-README-ROADMAP.md` … `10-PROMPT-PARA-CLAUDE.md`. Severidad: **A** bloquea o puede invalidar resultados, **M** hay que decidirlo antes de la fase afectada, **B** aclaración.

| # | Sev. | Hallazgo | Resolución / dónde se decide |
|---|---|---|---|
| H1 | A | `08-FASE-7` y `09-FASE-8` exigen una demo «sin servicios externos» y a la vez UI en Three.js; el núcleo está en Python. No se dice cómo llega al navegador offline | **Q1** |
| H2 | M | `09-FASE-8` pide «comparar con herramientas formales de referencia». Contradice «sin servicios externos» si se entiende como uso en la demo | Solo como contraste **en desarrollo y offline**; motor B (`IMPLEMENTATION_PLAN.md` §3) cubre la intención sin dependencias |
| H3 | M | `09-FASE-8` habla de «contramodelo mínimo»: ¿mínimo en qué sentido? | Mínimo **en cardinalidad del dominio dentro del rango explorado** (`JSON_CONTRACTS.md` §5). No se afirma otra minimalidad |
| H4 | M | `01-FASE-0` define `inconsistent` como «diagnóstico adicional» sin precisarlo | Ahora es `premisas ⊢ ⊥` con certificado aceptado (ADR-003). Para lo proposicional, además, se conoce exactamente por tabla de verdad |
| H5 | M | `04-FASE-3` deja elegir resolución o deducción natural; la Fase 4 y 8 no dicen cuál esperan | ADR-002: deducción natural. La resolución queda como oráculo (motor B) |
| H6 | M | El roadmap supone tres revisores/integrantes; no consta cuántas personas hay ni quién revisa | **Q3** |
| H7 | M | No hay fecha de entrega: no se puede fijar calendario ni recortes | **Q2** |
| H8 | M | `06-FASE-5` y `SPANISH_CONTROLLED.md` no definen cómo se escriben los nombres: en el núcleo, minúscula = término y mayúscula = predicado | El adaptador debe generar `Estudiante`, `juan` (ADR-007); la tabla de léxico lo hace explícito |
| H9 | M | **Las clases escriben las letras proposicionales en minúscula (`p → q`)**; el lenguaje formal las rechaza. Un ejercicio de clase no se puede teclear tal cual | ADR-006 / **Q4** |
| H10 | B | `01-FASE-0` pide «funciones n-arias como extensión explícita con tests»: ya están (`Func`, aridad fija) | Cumplido |
| H11 | B | `03-FASE-2`: «fórmulas abiertas requieren asignación explícita» | Implementado: `unassigned_variable` |
| H12 | B | No se fija el tratamiento del nombre propio frente a la igualdad: ¿`juan` y `pedro` son distintos? | ADR-008: **sin** supuesto de nombres únicos ni de dominio cerrado |
| H13 | B | `10-PROMPT` pide parar tras la Fase 0 hasta aprobación. Se avanzó a Fases 1–3 por pedido explícito del usuario | Registrado en `IMPLEMENTATION_PLAN.md` §1; el gate de revisión sigue abierto |

**Requisitos imposibles detectados:** ninguno por sí mismo. Sí es imposible (y el roadmap ya lo advierte) decidir validez general de FOL; todo el diseño trata `unknown` como resultado legítimo.

## 2. Registro de decisiones (ADR)

| ADR | Decisión | Estado | Fecha |
|---|---|---|---|
| ADR-001 | **Núcleo en Python estándar, sin dependencias.** Pruebas con `unittest` y generadores propios | Aprobada implícitamente; revisable con Q1 | 2026-10-21 |
| ADR-002 | **Deducción natural** como cálculo único del motor A. Presentación con hipótesis abiertas explícitas (Prawitz), no Fitch lineal; la vista Fitch se genera al narrar | **Aprobada** (usuario) | 2026-10-21 |
| ADR-003 | `⊥` es átomo primitivo. `¬I`, `¬E`, `⊥E`, `RAA` lo usan; `inconsistent` = `⊢ ⊥` | Aplicada, comunicada al usuario | 2026-10-21 |
| ADR-004 | Las fórmulas se comparan **salvo alfa-equivalencia** (checker y buscador); la sustitución evita captura renombrando | Aplicada | 2026-10-21 |
| ADR-005 | **Dos caminos de prueba.** Proposicional: búsqueda + Kalmár + tabla de verdad como oráculo (siempre hay veredicto). Primer orden: búsqueda + motor B de resolución como oráculo (sin garantía) | Parcial: proposicional hecho; motor B pendiente | 2026-10-21 |
| ADR-006 | Modo opcional `propositional=True`: `p` se lee como `P`; mezclar `p` y `P` es `letter_collision` | **Propuesta, pendiente de aprobación** (Q4). Apagado por defecto | 2026-10-21 |
| ADR-007 | Convención de nombres: mayúscula = predicado; minúscula = variable/constante/función | Aprobada (D-2, con D-1) | 2026-10-21 |
| ADR-008 | Sin nombres únicos ni dominio cerrado: dos constantes distintas pueden denotar el mismo elemento | Aplicada | 2026-10-21 |
| D-1 | El cuantificador liga fuerte: `∀x P(x) → Q(x)` se lee `(∀x P(x)) → Q(x)` | **Aprobada** (usuario) | 2026-10-21 |
| D-2 | Constantes declaradas al parsear; un identificador sin ligar ni declarar es variable libre | **Aprobada** (usuario) | 2026-10-21 |

**Lección registrada (ADR-005):** el oráculo semántico encontró un hueco real del buscador heurístico (hipótesis `A ↔ B` sin un lado conocido) y otro caso difícil que solo Kalmár resolvió. Por eso en lógica proposicional el buscador no es la garantía: lo es el algoritmo de Kalmár.

## 3. Preguntas abiertas

| # | Pregunta | Por qué importa | Recomendación |
|---|---|---|---|
| **Q1** | ¿Cómo corre el núcleo Python en la demo offline? (a) servidor local, (b) Pyodide en el navegador, (c) reescribir el núcleo en TypeScript | Bloquea las Fases 6–8 y la regla «sin servicios externos» | **(a)** servidor local con `http.server` y resultados precalculados como respaldo. Reescribir el núcleo duplica el riesgo de corrección |
| **Q2** | ¿Fecha de la competencia y de los hitos? | Sin ella no hay calendario ni recortes | Fijarla y recalcular `IMPLEMENTATION_PLAN.md` §4 |
| **Q3** | ¿Cuántas personas son y quiénes revisan cada gate? | El gate exige «dos revisores» | Asignar revisores por fase y registrarlo aquí |
| **Q4** | ¿Aprobar ADR-006 (letras minúsculas en modo proposicional)? | Sin él los ejercicios de clase no se teclean tal cual | Aprobar. Alternativa: exigir mayúsculas y que la UI traduzca |
| **Q5** | ¿Qué alcance de primer orden se espera en la competencia (¿igualdad, funciones?) | Define el corpus y cuánto invertir en el motor B | Mantener igualdad y funciones (ya están); motor B solo si sobra tiempo |
| **Q6** | ¿La competencia pide también deducción natural **estilo Fitch** en pantalla? | El certificado es de hipótesis abiertas; la vista Fitch es una transformación | Implementarla en `ExplanationBuilder` (Fase 7) |
| **Q7** | ¿Conversaciones del cerebro como fuente de léxico? Hay datos personales mezclados | Privacidad al compartir el repositorio | Extraer solo ejercicios y vocabulario; nada de conversaciones completas en el repo |

## 4. Revisiones (gates)

| Documento | Revisor 1 | Revisor 2 | Fecha | Observaciones |
|---|---|---|---|---|
| `FORMAL_LANGUAGE.md` | — | — | — | — |
| `SEMANTICS.md` | — | — | — | — |
| `PROOF_CALCULUS.md` (argumento de corrección) | — | — | — | — |
| `JSON_CONTRACTS.md` | — | — | — | — |
| `ACCEPTANCE_FIXTURES.md` (fórmulas de referencia) | — | — | — | — |
