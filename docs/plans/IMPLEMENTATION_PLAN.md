# Plan de implementación

> **Vigente para el proyecto MM3032: `PLAN_MM3032.md`.** Este documento es el plan original de la competencia; sus fases 6–8 (3D, voz) quedan recortadas.

> Estado al **2026-10-21**. La fecha de la competencia no está en el repositorio, así que no hay calendario absoluto: las estimaciones son esfuerzo de una persona. Ver Q2 en `OPEN_QUESTIONS.md`.

## 1. Estado por fase

| Fase | Entregable | Estado | Gate (según el roadmap) |
|---|---|---|---|
| 0 | Contratos y especificación | **Documentos completos** (este lote); 3 decisiones abiertas | Dos revisores verifican especificación y fórmulas de referencia — **pendiente** |
| 1 | Lexer, parser, AST | Implementado, 77 pruebas de la fase | Precedencia, sustitución y round-trip pasan — **cumple en código**; falta revisión |
| 2 | Semántica e intérprete | Implementado | Resultados reproducibles y propiedades semánticas — **cumple en código** |
| 3 | Pruebas y checker | Implementado (motor A + Kalmár proposicional) | Certificados válidos aceptados, inválidos rechazados — **cumple**; falta revisar el argumento de corrección en prosa |
| 4 | Contramodelos | **Siguiente.** Proposicional ya resuelto por tabla de verdad | Todo contramodelo se verifica; límite ⇒ `unknown` |
| 5 | Español controlado | Gramática v0 y casos borde (prototipo); sin integración | Cada frase admitida produce AST bien formado |
| 6 | Interfaz | No iniciada | Integración con fixtures, accesibilidad |
| 7 | Voz y 3D | No iniciada | Cada frase narrada respaldada por un paso verificado |
| 8 | Validación y demo | No iniciada | Ensayo completo offline |

**Regla:** no se avanza de fase sin aprobar su gate. Las Fases 1–3 se implementaron antes de cerrar el gate de la Fase 0 por decisión explícita del usuario (2026-10-21); eso no sustituye la revisión.

## 2. Backlog por prioridad

### P0 — cerrar el núcleo matemático

| # | Tarea | Criterio de aceptación | Pruebas negativas | Riesgo | Rollback |
|---|---|---|---|---|---|
| P0-1 | **Revisión cruzada** de `FORMAL_LANGUAGE`, `SEMANTICS`, `PROOF_CALCULUS` y fixtures por dos personas | Firma de cada revisor en `OPEN_QUESTIONS.md`; observaciones resueltas | — | Error de corrección en prosa que la fuerza bruta no ve | Reabrir la regla afectada |
| P0-2 | **Buscador de contramodelos** (Fase 4): enumeración por tamaño con cotas, verificación con `is_countermodel`, contrato `Countermodel` | Todos los del corpus `INVALID` obtienen contramodelo ≤ N; los válidos nunca | Contramodelo falsificado rechazado; cota agotada ⇒ `unknown` | Explosión combinatoria | Límite de tamaño y tiempo como configuración |
| P0-3 | **Motor B (resolución)** como oráculo de contraste, **no confiable** | Ver §3 | Resolución prueba algo que el buscador refuta ⇒ alarma | Costo de implementar clausificación y unificación | Descartar el módulo; el núcleo no depende de él |
| P0-4 | Completar `OPEN_QUESTIONS` Q1–Q5 con el equipo | Decisiones registradas | — | Bloqueos en UI | — |

### P1 — adaptadores de entrada

| # | Tarea | Aceptación |
|---|---|---|
| P1-1 | Tabla de léxico revisada por humanos (sale de las conversaciones de clase) | Dos revisores; columnas: palabra, categoría, predicado, aridad, ambigüedad |
| P1-2 | Aho-Corasick para expresiones fijas con spans; integración con la gramática CYK | Los 51 casos borde siguen pasando; spans exactos |
| P1-3 | Adaptador español → `FormulaAST` con elección de lectura registrada | Frase ambigua ⇒ varias lecturas, nunca una elegida en silencio |
| P1-4 | Decisión de transporte núcleo ↔ UI (Q1) | Demo offline reproducible |

### P2 — experiencia

| # | Tarea |
|---|---|
| P2-1 | API local y proof debugger paso a paso (Fase 6), consumiendo `JSON_CONTRACTS` |
| P2-2 | `ExplanationBuilder` determinista y evento por paso verificado (Fase 7) |
| P2-3 | Visor de contramodelos y de trazas semánticas |

### P3 — presentación

| # | Tarea |
|---|---|
| P3-1 | Three.js, TTS del navegador, fallback 2D |
| P3-2 | Whisper opcional con confirmación |
| P3-3 | Ensayo de demo offline y plan de contingencia (Fase 8) |

## 3. Motor B: resolución como oráculo (diseño)

**Para qué sirve:** detectar errores del motor A comparando dos algoritmos **independientes**. No sustituye al checker: un resultado de resolución nunca se muestra como `proved`.

**Qué hace:** clausificación (forma normal negativa, estandarización, Skolemización), unificación con occurs-check, resolución binaria con factorización y límites de pasos y tiempo.

**Matriz de contraste** (sobre el corpus y los generadores):

| Motor A (deducción natural) | Motor B (resolución) | Conclusión |
|---|---|---|
| `proved` | encuentra refutación | **Consistente.** Dos caminos coinciden |
| `proved` | satura sin refutación | **Alarma de corrección**: uno de los dos tiene un bug |
| `proved` | agota límite | Sin información |
| `unknown` | encuentra refutación | **Hueco de completitud del motor A**: se registra, se arregla si es posible |
| `unknown` | agota límite | Sin información (legítimo en FOL) |
| contramodelo verificado | encuentra refutación | **Alarma de corrección** |

**Limitación honesta:** la resolución es refutacionalmente completa, pero la validez en FOL sigue siendo semidecidible: sin cota, no termina en los casos no válidos. Por eso es un oráculo de contraste y no un decisor.

## 4. Esfuerzo estimado (una persona, días laborales)

| Tarea | Estimación |
|---|---|
| P0-1 revisión cruzada | 1–2 por revisor |
| P0-2 contramodelos | 2–3 |
| P0-3 motor B | 4–6 |
| P1-1 léxico | 2–3 (etiquetado manual) |
| P1-2/P1-3 español integrado | 4–6 |
| P2 (UI, debugger, explicaciones) | 8–12 |
| P3 (3D, voz, ensayo) | 6–10 |

Son estimaciones gruesas para decidir qué recortar si falta tiempo. **Recorte recomendado, de lo primero a lo último:** Whisper → 3D elaborado → motor B → español más allá del subconjunto v1. Nunca se recorta: checker, contramodelos verificados, límites honestos.

## 5. Reglas de calidad (permanentes)

- Integración continua desde ya: la suite completa corre antes de cada integración.
- Cada regla del cálculo y cada condición lateral tiene prueba negativa.
- Los umbrales (profundidad, nodos, tiempo, tamaño de dominio) son **configuración**, no afirmaciones de verdad.
- Registro reproducible: versión, configuración, fixtures y resultados de cada ensayo de demo.

## 6. Estado del motor B (2026-11-12)

Implementado en `src/batz/resolution/` con el diseño de §3: clausificación (forma normal negativa, Skolem, distribución con cota), unificación con comprobación de ocurrencia, resolución binaria con factorización, selección por peso con turnos por antigüedad, y axiomas de igualdad cuando la fórmula usa `=`. Las variables libres del secuente se tratan como constantes arbitrarias, igual que en el motor A.

Evidencia (`tests/test_resolution.py`):

- Refuta los 88 secuentes válidos de `tests/proof_corpus.py` y ninguno de los 22 inválidos (20 saturan; 2 de igualdad agotan el límite de cláusulas, que es `unknown`).
- En lógica proposicional coincide con la tabla de verdad en 250 secuentes al azar: refuta si y solo si es válido.
- En primer orden, cada refutación de 160 secuentes al azar se contrastó con modelos pequeños: ninguno la falsifica.
- La matriz de contraste sobre el corpus completo no da ninguna alarma de corrección. Dio **un hueco de completitud del motor A**: `⊢ ∀x (A ∨ P(x)) ↔ (A ∨ ∀x P(x))`, que B refuta y A no prueba con sus límites por defecto.

Sigue sin ser un decisor: en primer orden puede no terminar, y por eso `unknown` existe. Nunca produce `proved`.
