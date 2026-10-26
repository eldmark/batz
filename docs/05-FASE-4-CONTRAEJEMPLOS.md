# Fase 4 — Contramodelos y exploración finita

## Objetivo
Refutar implicaciones inválidas encontrando un modelo donde todas las premisas sean verdaderas y la conclusión falsa.

## Tareas
1. Enumerar dominios finitos por tamaño creciente, con límite configurable.
2. Enumerar o buscar interpretaciones de símbolos (optimizar con solver si se justifica).
3. Verificar cada contramodelo con el evaluador independiente de búsqueda.
4. Reportar cardinalidad, interpretación y valores de cada premisa/conclusión.
5. Separar `no se encontró hasta tamaño N` de `válido en toda FOL`.
6. Añadir fixtures de implicaciones inválidas y fórmulas sin contramodelo finito dentro de límites.

## Caso estrella
`∀x(P(x)→Q(x))` **no implica** `∀x(Q(x)→P(x))`. Contramodelo con un elemento `a`: P(a)=falso, Q(a)=verdadero.

## Gate
Todos los contramodelos emitidos se verifican; timeout o límite produce `unknown`, jamás una afirmación universal injustificada.
