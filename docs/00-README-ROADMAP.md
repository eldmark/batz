# LOGOS — Laboratorio de lógica de primer orden

## Rediseño de interfaz (2026-11-16)

Para implementar la reorganización actual, leer el
[plan de interfaz](plans/REDISENO_INTERFAZ.md), el
[contrato del reproductor](specs/EXPLANATION_PLAYER.md) y el
[protocolo de trabajo paralelo Claude/Codex](plans/REDISENO_PARALELO.md).
Estos documentos especifican trabajo pendiente; las fases y estados históricos
que siguen no describen por sí solos la implementación actual.

## Visión
Construir para una competencia de lógica matemática un lexer, parser e intérprete propios para lógica de predicados de primer orden (FOL), ampliados con búsqueda de pruebas, verificador independiente, contraejemplos finitos y, solo después, traducción de español controlado, interfaz interactiva Three.js y narración sincronizada.

**Prioridad absoluta:** corrección matemática > pruebas y explicabilidad > interfaz > voz y animación.

## No prometer
- No prometer decidir toda FOL: la validez general es indecidible.
- No confundir ausencia de prueba con falsedad.
- No confundir validez en un dominio finito con validez universal.
- No atribuir conclusiones al modelo de voz o a un LLM.
- No afirmar originalidad absoluta: la contribución es integración rigurosa y experiencia demostrable.

## Fases
| Fase | Archivo | Gate |
|---|---|---|
| 0 | `01-FASE-0-CONTRATOS.md` | Semántica, alcance, interfaces y fixtures aprobados |
| 1 | `02-FASE-1-COMPILADOR.md` | Lexer/parser/AST y sustitución validados |
| 2 | `03-FASE-2-INTERPRETE.md` | Evaluación semántica en modelos finitos validada |
| 3 | `04-FASE-3-PRUEBAS.md` | Certificados y checker independiente |
| 4 | `05-FASE-4-CONTRAEJEMPLOS.md` | Contraejemplos verificados y límites explícitos |
| 5 | `06-FASE-5-ESPANOL.md` | Español controlado y ambigüedad explícita |
| 6 | `07-FASE-6-INTERFAZ.md` | Visualización reproducible de resultados verificados |
| 7 | `08-FASE-7-VOZ-3D.md` | Narración y 3D sincronizados con pruebas |
| 8 | `09-FASE-8-VALIDACION-DEMO.md` | Ensayo, benchmark y documentación de límites |

## Arquitectura
`texto formal -> lexer -> parser -> AST -> semántica / búsqueda -> checker -> certificado o contramodelo -> explicación estructurada -> UI / TTS / Three.js`.

El español controlado y Whisper son **adaptadores de entrada**: deben generar AST validado por el mismo núcleo.

## División sugerida para tres integrantes
- A: compilador, AST, gramática, sustitución, traductor controlado.
- B: intérprete, motor de pruebas, checker, contramodelos.
- C: frontend, renderer, voz, animaciones, UX.

**Todos** revisan fixtures matemáticos y contratos. Integración continua desde la primera fase.

## Política de trabajo con Claude
Antes de codificar, leer estos documentos, proponer ADRs/contratos y plan de tareas con pruebas. No alterar semántica por conveniencia del frontend. No avanzar de fase sin aprobar su gate. Cambios en alcance requieren aprobación humana.

## Documentos de Fase 0 (2026-10-21)
- `architecture/ARCHITECTURE.md`
- `specs/FORMAL_LANGUAGE.md`, `specs/SEMANTICS.md`, `specs/PROOF_CALCULUS.md`, `specs/JSON_CONTRACTS.md`
- `testing/ACCEPTANCE_FIXTURES.md`
- `plans/IMPLEMENTATION_PLAN.md`
- `decisions/OPEN_QUESTIONS.md` (auditoría, ADR y preguntas abiertas)
