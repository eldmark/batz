# Fase 8 — Validación formal, performance y demostración

## Objetivo
Preparar una presentación de competencia en la que la precisión matemática sea verificable y el efecto visual la haga comprensible.

## Plan de calidad
- Tests de lexer/parser/AST y propiedades de sustitución.
- Evaluación semántica de modelos finitos contra casos de referencia.
- Certificados inválidos deliberadamente inyectados para comprobar que el checker los rechaza.
- Contramodelos re-evaluados automáticamente.
- Límites de tiempo/memoria, fuzzing y regresión.
- Comparación con herramientas formales de referencia cuando el fragmento lo permita, registrando diferencias de semántica y alcance.
- Registro reproducible de versión, configuración, fixtures y resultados.

## Demostración en vivo
1. Introducir fórmula y premisas no preparadas dentro del fragmento soportado.
2. Mostrar tokens y AST.
3. Solicitar una conclusión demostrable: certificado y checker.
4. Solicitar una implicación inválida: contramodelo mínimo respecto al rango explorado.
5. Alterar interpretación del dominio: recalcular verdad.
6. Reproducir prueba narrada en 2D/3D.
7. Presentar un caso `unknown` y explicar por qué no es `false`.

## Gate
Ensayo completo sin depender de servicios externos para el núcleo; plan de contingencia offline y demostración de límites honestos.
