# Plan adaptado al proyecto MM3032 — Evaluador semántico

> Fecha: 2026-10-26. Fuente: `MM3032 - Proyecto.pdf`. Este plan **reemplaza en la práctica** las prioridades de `IMPLEMENTATION_PLAN.md` (que apuntaba a una competencia con 3D, voz y pruebas). El código de esas fases se conserva: es el núcleo y además sirve de aporte creativo.

## 1. Qué pide el PDF y cuánto vale

| Criterio | Pts | Qué lo cubre |
|---|---|---|
| Evaluación semántica y justificación | 30 | `semantics.py` + **explicador (falta)** |
| Análisis sintáctico | 10 | lexer, parser, símbolos, errores con posición |
| Interfaz gráfica | 10 | **no existe** |
| Defensa individual | 30 | docs + que cada integrante entienda cada módulo |
| Aportes creativos | 20 | pruebas, Kalmár, contramodelos, español (ver §5) |

Tickets: oro/plata solo suben el tope (90/100); el puntaje lo da el cumplimiento. Primero los 80 obligatorios, luego los creativos, y solo al final la presentación.

## 2. Cobertura actual (137 pruebas, todas pasan)

| # | Requerimiento | Estado | Evidencia / hueco |
|---|---|---|---|
| 1 | Lenguaje configurable | **Parcial** | `Signature` (constantes, funciones, predicados con aridad) y `check(strict=True)`. Falta capa de entrada desde la UI y constantes como funciones 0-arias en el texto del usuario |
| 2 | Interpretación | **Parcial** | `FiniteModel`: dominio no vacío, sin repetidos, funciones **totales**, tuplas en `D^n`. **Hueco: admite relaciones vacías** (el PDF las prohíbe) y no exige que el modelo coincida con la firma |
| 3 | Todos los conectivos | **Hecho** | `¬ ∧ ∨ → ↔ ∀ ∃`, además `⊥`, `=`, `≠`; ASCII y Unicode |
| 4 | Libres y entorno | **Parcial** | `free_vars`, `unassigned_variable`, `invalid_assignment`. Falta que el sistema **liste** las libres y pida el entorno (UI) |
| 5 | Interfaz gráfica | **Falta** | Nada. Botones `¬ ∧ ∨ → ∀ ∃ ( )` y teclado |
| 6 | Resultado y explicación | **Parcial** | `evaluate()` da la traza completa (sin cortocircuito), `check_trace` la verifica. **Falta traducirla a texto**: testigo, contraejemplo, comprobación completa |
| 7 | Validación | **Parcial** | Léxico, sintaxis, aridad, símbolos sin declarar, asignación y modelo ya dan `LogosError` con span. Falta: relaciones vacías, modelo vs. firma, y que nada llegue a evaluar si hay un error (`status: invalid_input`, sin valor) |

Fuera del PDF y ya hecho: buscador de pruebas, checker independiente, decisor proposicional (Kalmár), serialización JSON, gramática de español (prototipo).

## 3. Trabajo restante (obligatorio), en orden

### M1 — Cerrar el núcleo (pequeño, ~1 día)
1. **Modelo estricto del proyecto.** Nuevo `interpretation.py`: construye un `FiniteModel` desde `Signature` + datos en texto y rechaza: dominio vacío o con repetidos, relación vacía, función con tabla incompleta o valor fuera de `D`, tupla de longitud o elemento inválido, símbolo declarado sin interpretar, interpretación de símbolo no declarado. No se toca `FiniteModel` (las 137 pruebas dependen de que acepte relaciones vacías).
2. **Decisión a documentar:** predicados 0-arios. En `D⁰ = {()}`, «no vacía» obligaría a que fueran verdaderos. Propuesta: en el proyecto el predicado exige aridad ≥ 1 (se avisa en la UI). Anotar en `SEMANTICS.md`.
3. **Fachada única** `evaluar(firma, interpretación, texto, entorno) -> Resultado`. Devuelve `invalid_input` + lista de errores **o** valor + traza; nunca un valor con entrada inválida. Es el único punto que usa la UI.
4. `libres(texto)` para que la UI pida el entorno antes de evaluar.

### M2 — Explicador (30 pts de semántica; ~1–2 días)
`explain.py`, determinista, sobre la `Trace` ya verificada (`check_trace` antes de narrar):
- `∃` verdadero → **testigo**: primer hijo verdadero y por qué (instancia de la subfórmula).
- `∀` falso → **contraejemplo**: primer hijo falso.
- `∀` verdadero / `∃` falso → **comprobación completa**: «se revisaron los n elementos de D» con la tabla de valores.
- Conectivos: solo la razón decisiva (`∧` falso → el conyunto falso; `→` verdadero → antecedente falso o consecuente verdadero; `¬`, `↔`).
- Átomos: tupla evaluada y pertenencia a `P^I`; términos con valores intermedios (`f(a)=2`).
- Salida: árbol de explicación (resumen arriba, detalle desplegable) con spans de la fórmula para resaltar.
- Pruebas: cada plantilla, y propiedad: la explicación nunca contradice `holds`.

### M3 — Interfaz gráfica (10 pts; ~3–4 días)
**Decisión recomendada:** servidor local `http.server` + HTML/JS puro, sin dependencias (consistente con ADR-001 y la opción (a) de Q1). Razón concreta: en esta máquina `tkinter` no importa (`libtk8.6.so` ausente) y no hay Qt; la web se abre en cualquier navegador y no se instala nada. Alternativa si el docente exige ventana nativa: Tkinter en la máquina de entrega (la fachada de M1 no cambia).

Pantallas (una sola vista con 4 pasos):
1. **Lenguaje:** tabla editable de símbolos (nombre, tipo constante/función/predicado, aridad).
2. **Interpretación:** dominio como lista; por cada símbolo, una tabla (funciones: celda por cada `D^n`; predicados: casillas marcables para cada tupla). Se bloquea «Evaluar» si hay relación vacía o celda sin llenar.
3. **Fórmula:** campo de texto + botones `¬ ∧ ∨ → ∀ ∃ ( )` (+ `↔`, `=`, `⊥`) que insertan en el cursor; el teclado funciona igual (alias ASCII ya soportados). Errores subrayados con el span del `LogosError`.
4. **Entorno y resultado:** lista de variables libres con selector de `D`; badge Verdadero/Falso y árbol de explicación de M2.

Criterios: ninguna entrada inválida muestra Verdadero/Falso; mensajes en español; flujo completo con teclado.

### M4 — Validación y documentación (~1–2 días)
- Matriz de pruebas negativas, una por código de error del requerimiento 7 (sintaxis, símbolo, aridad, dominio, tupla, asignación faltante, asignación fuera de `D`).
- Pruebas de integración de la fachada con fixtures de `ACCEPTANCE_FIXTURES.md`.
- **Guía de defensa** (`docs/DEFENSA.md`): cada módulo en media página, la regla de Tarski que implementa, y 10 preguntas probables con respuesta (¿por qué `∀` en dominio vacío no se permite?, ¿por qué no hay cortocircuito en la traza?, ¿qué pasa con `x` libre y cuantificada a la vez?).
- Revisión cruzada de `FORMAL_LANGUAGE`, `SEMANTICS` y fixtures (P0-1): cada integrante debe poder defender todo, no solo su parte.

## 4. Lo que se recorta o se pospone
| Antes | Ahora |
|---|---|
| Fase 7 (voz, Three.js, Whisper) | **Fuera.** No suma a la rúbrica |
| Motor B (resolución) | **Fuera** salvo que sobre tiempo después de M4 |
| Español controlado integrado (Fase 5) | Candidato a creativo, ver §5 |
| Q1, Q2, Q3, Q5, Q6, Q7 | Q1 resuelta arriba; Q2 = fecha de entrega del PDF (**falta que la fijes**); Q6/Q7 no aplican |
| Q4 (letras proposicionales en minúscula) | Pendiente; solo importa si el proyecto acepta fórmulas proposicionales de clase |

## 5. Aportes creativos (20 pts: originalidad 5, valor 6, implementación 6, defensa 3)
Deben estar implementados, probados y justificados; elegir **dos o tres**, no todos.

| Candidato | Costo | Por qué puntúa |
|---|---|---|
| **Buscador de contramodelos / modelos** («dame un modelo donde la fórmula sea falsa») sobre la firma del usuario | 2–3 d | Reutiliza `FiniteModel`; verificación con `is_countermodel`; límites honestos |
| **Tabla de verdad / validez en el dominio** y equivalencia de dos fórmulas en el modelo | 1 d | Muy defendible |
| **Visualizador del árbol de evaluación** (colapsable, colores verdadero/falso, resaltado de la subfórmula en el texto) | 1–2 d | Alto valor didáctico, se apoya en M2 |
| **Verificador de pruebas / `decide` proposicional** ya existente, expuesto en la UI | 1 d | Ya implementado y con 100+ pruebas; solo falta exponerlo |
| Entrada en español controlado (gramática v0) | 4–6 d | Original pero riesgoso para el tiempo |
| Importar/exportar interpretaciones en JSON | 0.5 d | Barato, útil para la demo |

**Recomendación:** visualizador del árbol + buscador de contramodelos + exportación JSON. Si falta tiempo, exponer `decide` en vez del buscador.

## 6. Orden y puertas
`M1 → M2 → M3 → M4 → creativos → ensayo de defensa`. No se empieza M3 sin la fachada de M1; no se declara terminado M2 sin que `check_trace` pase sobre cada explicación. Toda demo se ensaya con fórmulas **no preparadas**.

## 7. Preguntas abiertas para el equipo
1. **Fecha de entrega y de defensa** (Q2): sin ella no se recortan los aportes creativos.
2. **¿Cuántos integrantes y quién defiende qué?** La defensa es individual (30 pts) y «se podrá preguntar sobre cualquier parte».
3. **¿Ventana nativa obligatoria?** Si no, se sigue con la UI web local.
4. **¿Las constantes se declaran como funciones 0-arias** (como dice el PDF: «símbolo funcional n-ario») o aparte? Hoy hay `constants` separado; la UI puede presentar ambos como «función de aridad 0».
