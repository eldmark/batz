# Fase 6 — Frontend y depurador lógico

## Objetivo
Visualizar el funcionamiento real del motor matemático sin introducir lógica en el frontend.

## Pantallas
- Editor formal con resaltado de tokens y errores.
- AST interactivo.
- Panel de premisas, objetivo y modelo.
- Proof debugger paso a paso con regla, sustitución y referencias.
- Visor de contramodelos: dominio, predicados y evaluación.
- Distinción visual de `proved`, `counterexample`, `unknown` y diagnóstico de inconsistencia.

## Contratos
Consumir resultados JSON versionados. La UI solo representa certificados aceptados o contramodelos verificados; jamás inventa pasos. Incluir modo accesible 2D y exportación de pruebas.

## Gate
Pruebas de integración con fixtures, accesibilidad básica, errores claros y reproducción determinista de un certificado.
