# Fase 2 — Semántica e intérprete de FOL

## Objetivo
Evaluar fórmulas en una estructura finita explícita, conforme a la semántica clásica de primer orden.

## Tareas
1. Modelo finito: dominio no vacío, interpretaciones de constantes, funciones y relaciones.
2. Asignación de variables y evaluación recursiva de términos y fórmulas.
3. `∀` recorre todos los elementos; `∃` comprueba al menos uno.
4. Igualdad como identidad del dominio.
5. Evaluación de fórmulas abiertas requiere asignación explícita; evitar afirmar verdad sin contexto.
6. Explicar resultados con trazas semánticas verificables.
7. Tests contra tablas de verdad, modelos enumerados manualmente y casos de cuantificadores alternados.

## Ejemplo
`∀x(P(x)→Q(x))` es verdadero en un modelo cuando cada elemento que satisface P también satisface Q; no autoriza la conversa `∀x(Q(x)→P(x))`.

## Gate
Resultados reproducibles para dominios pequeños y tests de propiedades semánticas. No interpretar `no demostrable` como `falso`.
