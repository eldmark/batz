# Fase 1 — Lexer, parser y AST

## Objetivo
Aceptar expresiones formales de FOL y generar AST tipado, sin usar LLM.

## Tareas
1. Lexer con tokens, offsets y errores localizables.
2. Parser con precedencia y asociatividad documentadas.
3. AST inmutable: términos, átomos, conectivos, cuantificadores, igualdad.
4. Tabla de símbolos y validación de aridad.
5. Variables libres/ligadas, renombrado alfa y sustitución que evite captura.
6. Pretty-printer canónico y round-trip `parse(print(ast))` equivalente hasta alfa-equivalencia.
7. Tests unitarios, property-based y casos de error.

## Casos adversariales
`∀x P(x)`, `∀x(P(x)→Q(x))`, cuantificadores anidados, shadowing, sustitución que captura variable, predicado con aridad incorrecta, paréntesis sin cerrar, operador colgante, caracteres inesperados.

## Gate
No se acepta AST inválido; las pruebas de precedencia, sustitución y round-trip pasan. El parser no evalúa ni demuestra.
