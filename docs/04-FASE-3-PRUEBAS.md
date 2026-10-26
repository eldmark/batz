# Fase 3 — Búsqueda de pruebas y checker independiente

## Objetivo
Encontrar derivaciones de consecuencias lógicas y verificar cada paso mediante un módulo pequeño, auditable e independiente del buscador.

## Diseño
Elegir **una** estrategia inicial: deducción natural con búsqueda restringida, o resolución de cláusulas con unificación. Si se usa resolución, especificar conversión a forma clausal, estandarización de variables, Skolemización y el vínculo formal entre refutación y consecuencia.

## Tareas
1. Definir reglas y side conditions del cálculo.
2. Implementar motor de búsqueda con presupuesto de tiempo/pasos.
3. Emitir certificado explícito: premisas, sustituciones, reglas, conclusiones y referencias.
4. Checker independiente: valida cada paso sin confiar en etiquetas del buscador.
5. Tests negativos: certificados falsificados, sustituciones ilegales, variables capturadas, premisas inexistentes.
6. Generar traza para depurador matemático.

## Precisión
El buscador puede devolver `unknown` por límites. `proved` solo tras aceptación del checker. La corrección del checker debe estar sustentada en las reglas formales, no solo en tests.

## Gate
Todos los certificados positivos son aceptados; los inválidos se rechazan. Las pruebas de regresión matemáticas pasan.
