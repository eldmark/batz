# Fase 5 — Español controlado a lógica de primer orden

## Objetivo
Traducir un subconjunto explícito de español a AST formal sin introducir conclusiones no justificadas.

## Tareas
1. Definir gramática de español controlado: todos, algunos, ningún, y, o, no, si... entonces, relaciones binarias.
2. Separar análisis lingüístico, resolución de símbolos y AST formal.
3. Manejar concordancia/conjugaciones **solo** dentro de un vocabulario acotado; no intentar toda la lengua.
4. Identificar alcance de cuantificadores y ambigüedades; ofrecer varias lecturas cuando proceda.
5. Mostrar fórmula generada y exigir confirmación si hay ambigüedad.
6. Permitir edición manual de AST/fórmula.
7. Probar frases fuera de gramática: error o aclaración, nunca traducción inventada.

## Capas auxiliares (acordado 2026-10-21)
Arquitectura: `texto -> Aho-Corasick (expresiones fijas y léxico, con spans) -> gramática CYK (todas las lecturas) -> el usuario elige -> FormulaAST`.

1. **Aho-Corasick** detecta expresiones de varias palabras (`al menos`, `a lo sumo`, `si y solo si`, `o bien`, `no hay ningún`) **antes** de expandir contracciones, y localiza palabras del léxico conservando su span. Solo reconoce patrones; no interpreta.
2. **Tabla de léxico revisada por humanos**: se construye etiquetando conversaciones y ejemplos propios. Columnas mínimas: palabra, categoría, predicado, aridad, notas de ambigüedad (p. ej. `joven` N/Adj son predicados distintos). El resultado es una tabla, no un modelo entrenado.
3. **Sugeridor opcional** (`¿quisiste decir...?` para palabras desconocidas o sin tilde, y casos borde nuevos): puede **proponer**, nunca decide. Toda sugerencia pasa por la misma gramática y exige confirmación del usuario.

**Reglas:** ningún modelo ni umbral de confianza elige entre lecturas; las salidas de un LLM no son verdad de referencia para etiquetas; la validez la decide solo el checker. Se integra después de aprobar el gate de Fase 0 (`FormulaAST` y contratos).

## Ejemplo
`Todos los estudiantes leyeron un libro` puede tener lecturas `∀x∃y` y `∃y∀x`. No escoger silenciosamente.

## Gate
La tabla de léxico fue revisada por dos integrantes. Cada frase admitida produce AST bien formado y verificado; las ambiguas se señalan y las no soportadas se rechazan con diagnóstico.
