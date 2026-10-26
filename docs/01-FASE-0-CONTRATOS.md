# Fase 0 — Contratos y definición formal

## Objetivo
Congelar qué fragmento de FOL soportará la primera versión y cómo se intercambian datos entre módulos.

## Alcance mínimo
- Fórmulas: predicados, igualdad, `¬`, `∧`, `∨`, `→`, `↔`, `∀`, `∃`, paréntesis.
- Términos: variables y constantes; funciones n-arias como extensión explícita, con tests.
- Dominios finitos no vacíos para evaluación; interpretación explícita de constantes, funciones y predicados.
- Variables libres y ligadas, aridades y precedencia definidas.
- Un cálculo de pruebas **especificado** (por ejemplo deducción natural o resolución); no mezclar reglas de sistemas distintos sin justificación.

## Contratos de resultado
- `proved`: certificado aceptado por checker independiente.
- `counterexample`: estructura que satisface premisas y falsifica conclusión, comprobada por evaluador.
- `unknown`: timeout, límite o búsqueda inconclusa.
- `inconsistent`: diagnóstico adicional respaldado por certificado o por análisis finito claramente acotado. En lógica clásica, premisas inconsistentes implican cualquier fórmula.
- `invalid_input`: error léxico, sintáctico o semántico con ubicación.

## Contrato de datos
Definir schemas versionados para `FormulaAST`, `FiniteModel`, `ProofCertificate`, `ProofStep`, `Countermodel`, `ExplanationEvent`, `Diagnostic`. Incluir `schema_version`, IDs estables, fórmulas serializadas canónicamente y trazabilidad de pasos.

## Tareas
1. Escribir especificación EBNF y semántica denotacional del fragmento.
2. Definir reglas de tipado/aridad y tratamiento de símbolos no declarados.
3. Elegir cálculo formal y describir condiciones laterales de cada regla.
4. Crear fixtures positivos, negativos y ambiguos.
5. Fijar límites de búsqueda y timeouts como configuración, no como afirmaciones de verdad.
6. Acordar JSON de intercambio entre backend y UI.

## Gate
Dos revisores verifican la especificación y las fórmulas de referencia. Claude entrega contratos y plan, **no implementación silenciosa**.
