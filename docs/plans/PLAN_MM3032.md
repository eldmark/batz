# Plan adaptado al proyecto MM3032 — Evaluador semántico

> Fecha: 2026-10-26. Fuente: `MM3032 - Proyecto.pdf`. Este plan **reemplaza en la práctica** las prioridades de `IMPLEMENTATION_PLAN.md` (que apuntaba a una competencia con 3D, voz y pruebas). El código de esas fases se conserva: es el núcleo y además sirve de aporte creativo.

## 1. Qué pide el PDF y cuánto vale

| Criterio | Pts | Qué lo cubre |
|---|---|---|
| Evaluación semántica y justificación | 30 | `semantics.py` + `explain.py` |
| Análisis sintáctico | 10 | lexer, parser, símbolos, errores con posición |
| Interfaz gráfica | 10 | Servidor local + HTML/JS (`logos.server`) |
| Defensa individual | 30 | docs + que cada integrante entienda cada módulo |
| Aportes creativos | 20 | pruebas, Kalmár, contramodelos, español (ver §5) |

Tickets: oro/plata solo suben el tope (90/100); el puntaje lo da el cumplimiento. Primero los 80 obligatorios, luego los creativos, y solo al final la presentación.

## 2. Cobertura del núcleo y de la interfaz (actualizada 2026-11-02)

| # | Requerimiento | Estado | Evidencia / hueco |
|---|---|---|---|
| 1 | Lenguaje configurable | **Implementado en código** | `Signature`, `check(strict=True)` y tabla editable de símbolos. La UI presenta constantes como funciones de aridad 0 |
| 2 | Interpretación | **Implementado en código** | `build_interpretation` exige dominio no vacío, funciones totales, relaciones no vacías y coincidencia exacta con la firma |
| 3 | Todos los conectivos | **Hecho** | `¬ ∧ ∨ → ↔ ∀ ∃`, además `⊥`, `=`, `≠`; ASCII y Unicode |
| 4 | Libres y entorno | **Implementado en código** | `libres` y la UI listan variables libres y solicitan su entorno; se valida antes de evaluar |
| 5 | Interfaz gráfica | **Implementado en código** | Botones `¬ ∧ ∨ → ∀ ∃ ( )` y teclado; falta revisión visual en navegador de entrega |
| 6 | Resultado y explicación | **Implementado en código** | `evaluate()` da la traza completa, `check_trace` la verifica y `explain()` genera testigo, contraejemplo o comprobación completa |
| 7 | Validación | **Implementado en código** | La fachada devuelve `invalid_input` sin valor; la matriz negativa está en `tests/test_project_integration.py` |

Fuera del PDF y ya hecho: buscador de pruebas, checker independiente, decisor proposicional (Kalmár), serialización JSON, gramática de español (prototipo).

## 3. Trabajo restante (obligatorio), en orden

### M1 — Cerrar el núcleo (pequeño, ~1 día)
**Estado (2026-11-02): implementado en código; pendiente revisión del equipo.** `build_interpretation`, `evaluar` y `libres` tienen pruebas de integración y negativas. La capa web sigue en M3.
1. **Modelo estricto del proyecto.** Nuevo `interpretation.py`: construye un `FiniteModel` desde `Signature` + datos en texto y rechaza: dominio vacío o con repetidos, relación vacía, función con tabla incompleta o valor fuera de `D`, tupla de longitud o elemento inválido, símbolo declarado sin interpretar, interpretación de símbolo no declarado. No se toca `FiniteModel` (las 137 pruebas dependen de que acepte relaciones vacías).
2. **Decisión a documentar:** predicados 0-arios. En `D⁰ = {()}`, «no vacía» obligaría a que fueran verdaderos. Propuesta: en el proyecto el predicado exige aridad ≥ 1 (se avisa en la UI). Anotar en `SEMANTICS.md`.
3. **Fachada única** `evaluar(firma, interpretación, texto, entorno) -> Resultado`. Devuelve `invalid_input` + lista de errores **o** valor + traza; nunca un valor con entrada inválida. Es el único punto que usa la UI.
4. `libres(texto)` para que la UI pida el entorno antes de evaluar.

### M2 — Explicador (30 pts de semántica; ~1–2 días)
**Estado (2026-11-02): implementado y probado en código.** Cada explicación verifica su traza antes de narrar.
`explain.py`, determinista, sobre la `Trace` ya verificada (`check_trace` antes de narrar):
- `∃` verdadero → **testigo**: primer hijo verdadero y por qué (instancia de la subfórmula).
- `∀` falso → **contraejemplo**: primer hijo falso.
- `∀` verdadero / `∃` falso → **comprobación completa**: «se revisaron los n elementos de D» con la tabla de valores.
- Conectivos: solo la razón decisiva (`∧` falso → el conyunto falso; `→` verdadero → antecedente falso o consecuente verdadero; `¬`, `↔`).
- Átomos: tupla evaluada y pertenencia a `P^I`; términos con valores intermedios (`f(a)=2`).
- Salida: árbol de explicación (resumen arriba, detalle desplegable) con spans de la fórmula para resaltar.
- Pruebas: cada plantilla, y propiedad: la explicación nunca contradice `holds`.

### M3 — Interfaz gráfica (10 pts; ~3–4 días)
**Estado (2026-11-02): implementada en código; pendiente revisión visual en el navegador de entrega.**
**Decisión recomendada:** servidor local `http.server` + HTML/JS puro, sin dependencias (consistente con ADR-001 y la opción (a) de Q1). Razón concreta: en esta máquina `tkinter` no importa (`libtk8.6.so` ausente) y no hay Qt; la web se abre en cualquier navegador y no se instala nada. Alternativa si el docente exige ventana nativa: Tkinter en la máquina de entrega (la fachada de M1 no cambia).

Pantallas (una sola vista con 4 pasos):
1. **Lenguaje:** tabla editable de símbolos (nombre, tipo constante/función/predicado, aridad).
2. **Interpretación:** dominio como lista; por cada símbolo, una tabla (funciones: celda por cada `D^n`; predicados: casillas marcables para cada tupla). Se bloquea «Evaluar» si hay relación vacía o celda sin llenar.
3. **Fórmula:** campo de texto + botones `¬ ∧ ∨ → ∀ ∃ ( )` (+ `↔`, `=`, `⊥`) que insertan en el cursor; el teclado funciona igual (alias ASCII ya soportados). Errores subrayados con el span del `LogosError`.
4. **Entorno y resultado:** lista de variables libres con selector de `D`; badge Verdadero/Falso y árbol de explicación de M2.

Criterios: ninguna entrada inválida muestra Verdadero/Falso; mensajes en español; flujo completo con teclado.

### M4 — Validación y documentación (~1–2 días)
**Estado (2026-11-02): matriz negativa, pruebas de integración y guía de defensa implementadas. La revisión cruzada humana sigue pendiente.**
- Matriz de pruebas negativas, una por código de error del requerimiento 7 (sintaxis, símbolo, aridad, dominio, tupla, asignación faltante, asignación fuera de `D`).
- Pruebas de integración de la fachada con fixtures de `ACCEPTANCE_FIXTURES.md`.
- **Guía de defensa** (`docs/DEFENSA.md`): cada módulo en media página, la regla de Tarski que implementa, y 10 preguntas probables con respuesta (¿por qué `∀` en dominio vacío no se permite?, ¿por qué no hay cortocircuito en la traza?, ¿qué pasa con `x` libre y cuantificada a la vez?).
- Revisión cruzada de `FORMAL_LANGUAGE`, `SEMANTICS` y fixtures (P0-1): cada integrante debe poder defender todo, no solo su parte.

## 4. Lo que se recorta o se pospone
| Antes | Ahora |
|---|---|
| Fase 7 (voz, Three.js, Whisper) | Fuera de la rúbrica MM3032; reabierta como extra por pedido del usuario. Three.js y controles probados en Brave; síntesis local implementada, pendiente ensayo audible en un equipo con voz española; Whisper opcional pendiente |
| Motor B (resolución) | **Hecho (2026-11-12)** como segunda opinión en el modo Demostrar; ver `IMPLEMENTATION_PLAN.md` §6 |
| Español controlado integrado (Fase 5) | **Hecho**: gramática completa con CYK; los 51 casos cumplen (`docs/validation/ESPANOL-51-CASOS.md`). Pendiente: léxico abierto con etiquetador entrenado y revisión humana |
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

**Estado (2026-11-02):** los tres recomendados están implementados en código. El visualizador usa `explain.py`; `countermodels.py` busca con cotas y revalida cada hallazgo; la interfaz importa y exporta JSON. Falta revisión visual y ensayo de defensa con otras personas.

**Extra en curso:** el adaptador inicial de español controlado devuelve todas las lecturas de su fragmento y no escoge una ambigüedad por el usuario. La gramática completa de `SPANISH_CONTROLLED.md`, Aho-Corasick, CYK y la revisión humana del léxico siguen pendientes; no se presenta el adaptador inicial como cobertura de los 51 casos.

## 6. Orden y puertas
`M1 → M2 → M3 → M4 → creativos → ensayo de defensa`. No se empieza M3 sin la fachada de M1; no se declara terminado M2 sin que `check_trace` pase sobre cada explicación. Toda demo se ensaya con fórmulas **no preparadas**.

**Ensayo técnico (2026-11-02):** el recorrido reproducible de API y rendimiento pasó; ver `docs/validation/ENSAYO-MM3032.md` y el JSON con la semilla, resultados y huella del código. También pasó la interacción visual automatizada en Brave. Siguen pendientes el recorrido en la computadora de entrega, el ensayo audible con una voz local española y la revisión firmada por el equipo.

**Auditoría contra el PDF (2026-11-11):** se probaron por la fachada 30 fórmulas y 23 interpretaciones inválidas, y el flujo completo en Chromium (botones, teclado, entorno, relación vacía, dominio vacío). Los siete requerimientos se cumplen. Correcciones de esa pasada: el dominio vacío ahora da su propio mensaje; el entorno rechaza nombres que no son variables (constantes, funciones, predicados); cada nodo de la explicación muestra su fórmula y el entorno de la instancia (`con x = 0`); las tuplas se escriben `(0)` y no `(0,)`; «la función 'g' no está declarada». 175 pruebas pasan.

## 7. Preguntas abiertas para el equipo
1. **Fecha de entrega y de defensa** (Q2): sin ella no se recortan los aportes creativos.
2. **¿Cuántos integrantes y quién defiende qué?** La defensa es individual (30 pts) y «se podrá preguntar sobre cualquier parte».
3. **¿Ventana nativa obligatoria?** Si no, se sigue con la UI web local.
4. **¿Las constantes se declaran como funciones 0-arias** (como dice el PDF: «símbolo funcional n-ario») o aparte? Hoy hay `constants` separado; la UI puede presentar ambos como «función de aridad 0».

## 8. Estado al 2026-11-12

**Interfaz.** Dos modos en la barra superior. *Evaluar en un modelo*: lenguaje e interpretación a la izquierda, fórmula, entorno y veredicto a la derecha; contramodelos y español quedan plegados. *Demostrar*: premisas y conclusión con revisión de sintaxis mientras se escribe, prueba verificada y contraste con el motor B. El paso a paso ya no se abre solo: se pide desde el resultado. Paleta en cuadrado desde el verde `#3f7660`, tipografías Literata, IBM Plex Sans y JetBrains Mono servidas en local.

**Archivos preparados.** «Cargar archivo» (o soltar el archivo sobre la página) acepta el JSON exportado y el formato de texto `.logos`: dominio, constantes, funciones, predicados y una lista de fórmulas con entorno y valor esperado opcionales. Cada fórmula se evalúa y se compara con lo esperado; ejemplos en `ejemplos/`.

**Ejecución.** `python3 evaluador.py` o `docker compose up --build`.

**Pruebas.** 195 automáticas. Reportes regenerables: `scripts/report_spanish.py` (51 casos) y `scripts/validate_demo.py` (recorrido de la demo).

**Pendiente.**
- Etiquetador entrenado: **hecho (2026-11-12)**. Regresión logística por descenso de gradiente sobre frases generadas; 94.4 % de exactitud en palabras nunca vistas y 19 de 20 frases de clase (`docs/validation/ETIQUETADOR-ESPANOL.md`). Las conversaciones del cerebro solo sirvieron de prueba: casi no traen frases para formalizar. Pendiente: revisión humana de las listas de lemas.
- Avatar: **hecho (2026-11-12)**. Modelado y animado en Blender, exportado a GLB y conectado al paso a paso: señala el elemento que se está probando, piensa en los conectivos y reacciona al valor final. Un clic en un elemento del dominio salta al caso que el cuantificador prueba con él. Voz sincronizada y guía de la búsqueda de contramodelos: **hechas (2026-11-13)**, ver §10.
- Vista Fitch de las pruebas: **hecha (2026-11-13)**, ver §10.
- Revisión cruzada firmada y ensayo de defensa: siguen pendientes; necesitan personas (`docs/validation/REVISION-EQUIPO.md`).

## 9. Diccionario del español (2026-11-12)

- **Léxico base** `src/logos/lexicon.tsv`: unos 1500 lemas (sustantivos con género, adjetivos, verbos con su uso y nombres propios). De cada lema se generan sus formas: plural, femenino y seis formas verbales (presente, subjuntivo y pasado, singular y plural). Lo generó un modelo de lenguaje fuera de la aplicación y está **pendiente de revisión humana**; se corrige editando el archivo.
- **Verbos irregulares**: tres mecanismos, del más barato al más explícito. Reglas ortográficas (`buscar → busque`, `proteger → proteja`, `crecer → crezca`, `construir → construye`), cambio de raíz declarado (`cambio=ue|ie|i`: `dormir → duerme, durmió`) y, para los del todo irregulares, las seis formas escritas (`formas=tiene,tienen,tenga,tengan,tuvo,tuvieron`). El símbolo lógico es siempre el infinitivo: `duermen → Dormir`.
- **Sustantivos**: el género no se deduce de la terminación (`problema` es masculino, `mano` femenino); se guarda en el diccionario, con `C` para los que valen para los dos (`artista`). Para una palabra que no está, el modelo propone género usando el determinante de la frase y la gramática descarta lo que no concuerda.
- **Página «Diccionario»** (tercer modo): buscar por lema o por cualquier forma, ver formas y símbolo, y añadir palabras. Al consultar una palabra que no está, el etiquetador propone categoría, género o uso y lema; la persona corrige y guarda. Las altas van a `datos/lexico_usuario.tsv` (volumen en Docker) y sirven de inmediato.
- **Gramática**: nueva regla para el condicional con sujeto tácito («Si una persona es humana, entonces es mortal» → `∀x (Persona(x) ∧ Humano(x) → Mortal(x))`) y predicado nominal de otro género («Ninguna ballena es un pez»). Cuando lo único que falla es la concordancia de un adjetivo, el error propone la forma correcta. Los 51 casos de la especificación siguen cumpliendo; «Los estudiantes leen» sigue rechazada, como pide la especificación, ahora con una explicación.
- **Etiquetador**: reentrenado con el diccionario como fuente; 97.1 % en palabras nunca vistas. Solo actúa sobre palabras que no están en el diccionario.

## 10. Estado al 2026-11-13 (rama `mejoras/plan-movil-animaciones`)

**Correcciones.**
- *Alcance en español*: la segunda lectura ya no depende de un único patrón (∀ sujeto, ∃ objeto). Cualquier par de cuantificadores del sujeto y del objeto directo de la oración principal la tiene, salvo ∀∀ y ∃∃ (equivalentes) y «ningún». Las relativas y el antecedente de «si» siguen siendo islas. «Algún profesor admira a cada estudiante» da ∃∀ y ∀∃. Los 51 casos siguen cumpliendo.
- *Reglas en notación de libro*: la derivación y la narración dicen «Hipótesis», «∀E», «→E», no `assume`, `all_e`, `imp_e`.
- *«No se sigue» con contramodelo*: si no hay prueba, se busca un modelo de 1 a 3 elementos con las premisas verdaderas y la conclusión falsa (semántica estándar, con relaciones vacías), verificado con el evaluador, y se puede abrir en el modo Evaluar.
- *Contramodelo legible*: tablas y matriz en vez de JSON. *Detalles*: plurales («1 elemento», «el único elemento de D»), favicon, pie de página abajo, `THREE.Timer` en vez de `THREE.Clock`, avisos que se van solos en vez de una franja fija.

**Pendientes del plan resueltos.**
- *Vista Fitch* (`proof/fitch.py`): cajas por cada hipótesis descargada y por la variable nueva de ∀I/∃E; `check_layout` comprueba la fidelidad con el certificado (corpus completo y Kalmár). La narración sigue su numeración.
- *Avatar*: boca con dos formas (`Boca_abierta`, `Boca_redonda`) que siguen las vocales de cada palabra de la voz; cuenta la búsqueda de contramodelos (tamaños, descartes, un ejemplo) antes de explicar por qué falla la fórmula.
- *Q4, letras proposicionales*: en Demostrar, `p → q` se decide como lógica proposicional (tabla de verdad y Kalmár). En Evaluar sigue el perfil MM3032 (aridad ≥ 1).
- *Whisper*: `scripts/instalar_voz.ps1` (probado en Windows) y `.sh` (sin probar en Linux real) instalan whisper.cpp 1.9.5, el modelo base y ffmpeg por usuario; la transcripción local funciona de punta a punta.
- *Léxico*: auditoría automática con `scripts/auditar_lexico.py` y las 55 dudas decididas y aplicadas (género común, verbos con y sin objeto, nombres propios que chocaban con palabras comunes, «escribe/estudia/aprueba» con objeto en la gramática). Etiquetador reentrenado: 96,3 % en palabras nunca vistas. Falta que una persona confirme el resumen de `docs/validation/LEXICO-AUDITORIA.md`.

**Teléfono y movimiento.** Ver README («En el teléfono»). Verificado en Chrome con 360 y 390 px y pantalla táctil emulada: sin desborde horizontal, objetivos de toque de 40 px o más y campos de 16 px.

**Siguen necesitando personas** (`docs/validation/REVISION-EQUIPO.md`): revisión cruzada firmada, ensayo de defensa, recorrido en la computadora de entrega, ensayo audible con una voz española instalada, confirmación de las decisiones del léxico, prueba en un teléfono real y la fecha de entrega (Q2).
