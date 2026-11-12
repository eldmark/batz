# Español controlado → FOL: tokenizador, gramática y casos borde

> Estado (2026-11-12): **gramática completa integrada** con CYK y Aho-Corasick (`spanish_cyk.py`, `spanish_semantics.py`); los 51 casos cumplen, ver `docs/validation/ESPANOL-51-CASOS.md`. El léxico sigue cerrado y sin revisión humana. Lo que sigue en este párrafo describe el estado anterior. Estado previo: especificación amplia en revisión. Desde 2026-11-02 existe un adaptador inicial independiente en `src/logos/spanish.py`, conectado a la API y a la interfaz. Reconoce solo nombres propios con verbos del léxico acotado, cuantificadores simples, identidad, «joven» y la ambigüedad de alcance de «Todos los estudiantes leyeron un libro». El prototipo de gramática de esta carpeta aún no está integrado; sus 51 casos siguen siendo la meta de la fase completa, no una cobertura del adaptador inicial.

## 1. Principio: no tirar información

Cada etapa conserva lo que recibió y le agrega algo. Si en algún punto se pierde algo, no hay forma de explicar el resultado, resaltar el error o narrar la prueba.

```
texto ─► tokens (span, superficie, normalizado, banderas)
       ─► segmentos (premisas / conclusión)
       ─► análisis léxico (todas las categorías posibles de cada token)
       ─► árboles sintácticos (TODOS, con rasgos y span por nodo)
       ─► lecturas semánticas (orden de cuantificadores)
       ─► FormulaAST (cada subfórmula apunta al span que la originó)
```

**Regla:** si hay más de una lectura distinta, se reporta y se pide confirmación. Nunca se elige ni se trunca en silencio. Después se muestra y se usa **solo la lectura que eligió el usuario**, y la elección queda registrada en la traza (§5.1).

## 2. Tokenizador

No se reutiliza `tokenize_sentence` de TDLC. Esa función pierde información que aquí necesitamos:

| `tokenize_sentence` (TDLC) | Problema para LOGOS |
|---|---|
| Pasa todo a minúsculas | Ya no se distingue el nombre propio "Rosa" del sustantivo "rosa" |
| Elimina `, ; : .` | La coma delimita el "si A, B" y las listas, y el punto separa premisas |
| No guarda offsets | Los errores no se pueden ubicar en el texto |
| No expande contracciones | Deja `al` y `del` como una sola palabra |

### Esquema de token

```json
{ "id": 7, "surface": "Al", "norm": "a", "span": [31, 33], "segment": 1,
  "kind": "word", "flags": ["from_contraction", "capitalized"] }
```

- `kind` puede ser `word`, `punct` o `marker` (un marcador de conclusión).
- `norm` es el texto en NFC, pasado por `casefold()` y sin `¿¡`. `surface` queda intacta.
- Una contracción genera dos tokens con el **mismo span**: `al` da `a` + `el`, y `del` da `de` + `el`.

### Casos borde del tokenizador

| Entrada | Decisión |
|---|---|
| Vacía, solo espacios o solo puntuación | `invalid_input: empty` |
| Tabs, saltos de línea, espacios repetidos | Son separadores. Un salto de línea también separa segmentos |
| `,` `;` `:` `.` pegados a una palabra (`Juan,María`) | Se separan como tokens propios |
| `...`, `!!`, `?!` | Se colapsan en un solo token y se avisa |
| `¿Se sigue que Juan lee?` | Es un marcador de conclusión (§3) y se marca como `question` |
| Sin tilde: `algun`, `ningun`, `Maria` | **Se pregunta**: "¿quisiste decir *algún*?". Nunca se corrige en silencio, aunque la corrección sea única |
| Pares donde la tilde cambia el significado: `si`/`sí`, `el`/`él`, `que`/`qué`, `mas`/`más`, `esta`/`está` | **No** se normalizan. Cada forma es su propia entrada (o se rechaza) |
| `sólo` | Se trata como alias de `solo`, según la norma RAE actual |
| Numerales: `dos`…`cinco` o `2`…`5` | Aceptados en v1 (§4.2). Otros números dan `unsupported: numeral_too_large` (el límite es configurable) |
| `al menos` | Es una expresión fija y se protege **antes** de expandir contracciones. Si no, `al` → `a el` rompe el determinante |
| Guiones, apóstrofos, emoji, letras de otros alfabetos | `invalid_input: unexpected_char` con su span |
| Palabra fuera del léxico | Error con span y sugerencias a distancia de edición ≤ 2 |
| Palabra desconocida con mayúscula a mitad de frase | Se sugiere "¿nombre propio no declarado?" |
| Mayúscula al inicio de la oración | No sirve como evidencia de nombre propio. Eso lo decide el léxico |
| Más de 40 tokens en un segmento | `invalid_input: too_long`. El límite va en la configuración |
| Fórmula mezclada con el texto (`P(a)`) | Se rechaza y se sugiere usar el editor formal |

## 3. Segmentación: premisas y conclusión

- Los segmentos se separan con `.`, `;` y saltos de línea.
- **Marcadores de conclusión** (al inicio de un segmento): `por lo tanto`, `por consiguiente`, `en consecuencia`, `así que`, `luego`, `∴`, `¿se sigue que …?`, `¿es cierto que …?`.
- **`entonces` es ambiguo**:
  - Si en el mismo segmento hay un `si` antes, forma parte del condicional.
  - Si abre el segmento y no hay ningún `si` antes, es un marcador de conclusión.
  - Si las dos interpretaciones son posibles, se pide aclaración.
- `luego` solo funciona como marcador de conclusión. En v0 no tiene lectura temporal y así queda documentado.
- Dos o más conclusiones dan `invalid_input`. Si no hay conclusión, el sistema pasa al modo "evaluar / revisar consistencia".

## 4. Diseño de la gramática

### 4.1 Decisiones

1. **La concordancia vive en los no terminales.** Los rasgos `g ∈ {M,F}` y `n ∈ {S,P}` se expanden desde plantillas (`generar_gramatica.py`, unas 45 plantillas que dan 130 reglas). Así el parser rechaza solo "María es alto" o "Todos los estudiantes lee", sin un filtro aparte.
2. **El léxico es una tabla aparte.** Guarda lema, categoría, rasgos y símbolo de predicado. La gramática se genera a partir de ella.
3. **No hay ε.** Además, el símbolo inicial `S` nunca aparece en el lado derecho (`S -> O`). Si apareciera, el `to_cnf` de TDLC crea un inicio `X1`, que `collapsed()` trata como auxiliar.
4. **No se eliminan las producciones unitarias. Este es el hallazgo principal.** Con el pipeline completo de TDLC, "Juan es joven" da **1** árbol: `Pred_MS → Adj_MS → joven` y `Pred_MS → N_MS → joven` se funden en `Pred_MS → joven`. Eso borra la ambigüedad léxica y, de paso, las categorías `NProp`, `VI` y `SVpos`.
   **La solución:** reutilizar solo la binarización y el aislamiento de terminales (`to_cnf`) y ejecutar **CYK con cierre unario**. Con eso salen **2** árboles completos (verificado).
5. **Se enumeran todos los árboles, con un límite.** El `cyk.py` de TDLC reconstruye uno solo (`_build_tree` usa `[0]`), aunque la tabla guarda todos los backpointers. Primero se cuenta los árboles con programación dinámica y, si pasan el límite, se pide reformular; nunca se trunca.

### 4.2 Cobertura v0

| Construcción | Ejemplo | FOL |
|---|---|---|
| Universal | Todo estudiante aprueba / Todos los estudiantes aprueban / Cada… | `∀x(E(x)→A(x))` |
| Existencial | Algún / un / algunos estudiante(s) lee(n) | `∃x(E(x)∧L(x))` (algunos significa ≥ 1) |
| Negativo de sujeto | Ningún estudiante lee | `¬∃x(E(x)∧L(x))` |
| Concordancia negativa | Juan no lee ningún libro | `¬∃y(Li(y)∧Lee(j,y))`: **una** sola negación |
| Adjetivo intersectivo | Todo estudiante inteligente aprueba | `∀x(E(x)∧I(x)→A(x))` |
| Relativa de sujeto | Todo estudiante que estudia aprueba | `∀x(E(x)∧Es(x)→A(x))` |
| Relativa con subjuntivo | No hay ningún estudiante que lea | Subjuntivo permitido **solo** dentro de una relativa |
| Transitivo con "a" personal | Juan ama a María / ve a todos los estudiantes | `Ama(j,m)` |
| Reflexivo | Juan se ama | `Ama(j,j)` |
| Cópula + adjetivo/sustantivo | Juan es alto (y inteligente) / es estudiante | `Alto(j)` |
| Cópula + indefinido | Juan es **un** estudiante | `E(j)`: predicativo, **no** `∃` |
| Identidad | Juan es Pedro | `j = p` |
| Existencial "hay" | Hay un estudiante que lee / No hay… / existe | `∃x(…)` / `¬∃x(…)` |
| "Solo" | Solo los estudiantes leen | `∀x(L(x)→E(x))`: la dirección se invierte |
| "Solo" + nombre | Solo Juan lee | `∀x(L(x)→x=j)` |
| Coordinación de nombres | Juan, Pedro y Ana leen | `L(j)∧L(p)∧L(a)` (distributiva) |
| Sujeto disyuntivo (v1) | Juan o María lee / leen; Juan, Pedro o Ana estudian | `L(j)∨L(m)`. El verbo acepta singular o plural |
| Al menos n (v1) | Al menos dos estudiantes leen | `∃x₁∃x₂(x₁≠x₂ ∧ E(x₁)∧L(x₁) ∧ E(x₂)∧L(x₂))` |
| A lo sumo n (v1) | A lo sumo tres profesores aprueban | `¬`(al menos n+1) |
| Exactamente n (v1) | Exactamente una persona lee | (al menos n) `∧` (a lo sumo n) |
| Numeral a secas (v1) | Dos estudiantes leen | **Ambiguo** entre al menos y exactamente, así que se pregunta (§5) |
| Conectivos | y, o (inclusiva), no es cierto que | `∧ ∨ ¬` |
| O exclusiva | O bien A o bien B | `(A∨B)∧¬(A∧B)` |
| Condicionales | Si A(,) (entonces) B / B si A / A solo si B / A si y solo si B | `A→B`, `A→B`, `A→B`, `A↔B` |

### 4.3 Lo que se rechaza con diagnóstico (nunca se inventa una traducción)

| Entrada | Por qué | Sugerencia |
|---|---|---|
| El estudiante lee | Un definido singular necesitaría unicidad (ι / Russell) | "Todo estudiante…" o un nombre propio |
| Los estudiantes leen | Definido plural: puede ser genérico o específico | "Todos los estudiantes…" |
| Ningún estudiante no lee | No es gramatical en español estándar | Quitar el "no" |
| Juan lee ningún libro | Falta el "no" de la concordancia negativa | "Juan no lee ningún libro" |
| Juan lea | Subjuntivo fuera de una relativa | — |
| Pronombres: él, lo, la, le | Anáfora (oraciones "burro") fuera del alcance | Repetir el nombre |
| Lee un libro (sin sujeto) | Sujeto omitido (pro-drop) | Escribir el sujeto |
| Los estudiantes, que estudian, aprueban | Relativa explicativa: cambia el significado | Quitar las comas |
| Exactamente dos estudiante lee / Al menos un estudiantes leen | Falla la concordancia de número | — |
| Juan o María es alta | Falla la concordancia de género (con un sujeto masculino gana el masculino) | — |
| estar, cuando, porque, a menos que, comparativos, modales | Fuera del fragmento | — |

## 5. Las tres fuentes de ambigüedad

| Fuente | Etapa que la detecta | Ejemplo | Lecturas |
|---|---|---|---|
| **Léxica** | Léxico + CYK | Juan es joven (N/Adj) | 2 árboles con predicados distintos (`Joven_sust` / `Joven_adj`). **Se pregunta** |
| **Sintáctica** | CYK, todos los árboles | Si Juan lee, entonces María estudia y Pedro estudia | `(A→B)∧C` contra `A→(B∧C)` |
| | | Juan lee y María estudia o Pedro estudia | `(A∧B)∨C` contra `A∧(B∨C)` |
| **De alcance** | Composición semántica (no la ve el parser) | Todos los estudiantes leyeron un libro | `∀x∃y` contra `∃y∀x` |
| | | Todos los estudiantes no leen | `∀x(E→¬L)` contra `¬∀x(E→L)` |
| **Cuantitativa** (v1) | Composición semántica | Dos estudiantes leen | Al menos 2 contra exactamente 2 |

Para que las ambigüedades no se multipliquen sin necesidad, hay **dos únicos casos** que no se preguntan, porque las variantes dan exactamente la misma fórmula y no hay nada que interpretar:

- **Árboles que solo difieren en el género.** "Dos estudiantes" sale como `SN_MP` y como `SN_FP`, porque *dos* no marca género y *estudiante* sirve para los dos. El género es concordancia, no significado: los árboles se comparan sin ese rasgo (verificado).

- **Cadenas de un mismo operador asociativo** (`∧`, `∨`). Se aplanan y se pasan a forma α-canónica antes de comparar lecturas. Por ejemplo, "A y B y C y D y E" da **14 árboles** (el número de Catalan C₄, verificado) que son una sola fórmula.

La gramática además evita lecturas falsas con estas reglas:

- **Islas de alcance**: un cuantificador que está dentro de una relativa o del antecedente de un "si" no sale de ahí. Por eso "Si algún estudiante lee, Juan aprueba" da `(∃x(E∧L))→A(j)` y nada más.
- La concordancia negativa ("no… ningún") cuenta como **una** negación y no genera lecturas extra.
- También hay límites de lecturas por alcance (n! permutaciones) y de árboles, ambos configurables. Si se superan, se pide reformular.

### 5.1 Protocolo de pregunta

1. Se muestran **todas** las lecturas distintas: la fórmula, una paráfrasis determinista ("para cada estudiante hay un libro…" / "hay un libro que todos…") y el span de la frase que causa la ambigüedad.
2. El usuario elige una. Si ninguna le sirve, puede reformular o editar la fórmula a mano.
3. A partir de ahí se muestra y se usa **solo la lectura elegida**. En la traza queda `{reading_id, alternativas, elegida_por: "usuario"}`, y la narración puede decir "interpretamos X porque así lo indicaste".
4. Hay preguntas encadenadas (por ejemplo, una tilde dudosa y además una ambigüedad de alcance). Se hacen en orden, primero la del tokenizador, y cada respuesta acota la siguiente.

## 6. Nombres de símbolos

- El predicado se nombra por lema: `leyó`, `lee`, `leen` y `lea` dan todos `Leer`. **El tiempo verbal se ignora** (decisión del equipo). Solo queda como información en la traza, sin aviso ni pregunta.
- Cuando una misma palabra tiene dos categorías, cada una da un predicado distinto (`Joven_sust`, `Joven_adj`) y la ambigüedad se pregunta. **No se fusionan por lema.**
- Para los numerales hace falta igualdad: "al menos n" genera n variables y n(n−1)/2 desigualdades. Por eso n ≤ 5 (configurable). El buscador de contramodelos tiene que empezar en dominios de tamaño ≥ n.
- Cuando un mismo verbo tiene dos aridades ("Juan lee" frente a "Juan lee un libro"), se generan símbolos distintos: `Leer/1` y `Leer/2`. Nunca se rellena con `∃y` en silencio.
- Las constantes salen del nombre propio en minúsculas (`juan`). Las variables son frescas (`x1, x2…`) y no chocan con ninguna constante.

## 7. Qué se reutiliza de TDLC y qué cambia

| Pieza | Uso |
|---|---|
| `parser.parse_grammar_text`, `Grammar` | Tal cual |
| `to_cnf` (binarización + `T_x`) | Tal cual, **sin** `eliminate_epsilon` / `eliminate_unit` / `remove_useless` (la gramática ya no tiene ε ni símbolos inútiles; agregar un test que lo verifique) |
| `cyk.cyk` | Se extiende con **cierre unario** y **enumeración de todos los árboles** (ya hay un prototipo en `validar_gramatica.py`) |
| `ParseNode.collapsed()` | Tal cual. Deshace la binarización correctamente (verificado) |
| `tokenize_sentence` | **Se reemplaza** (ver §2) |
| Convención de nombres | Ningún no terminal propio puede empezar con `T_` ni ser `X` + dígitos |

## 8. Archivos de esta carpeta

- `espanol/generar_gramatica.py`: plantillas y léxico v0, de donde sale `gramatica_v0.txt`.
- `espanol/gramatica_v0.txt`: gramática expandida (130 reglas, incluye lo de v1).
- `espanol/casos_borde.txt`: el formato es `<árboles distintos esperados>| frase` (0 significa rechazo).
- `espanol/validar_gramatica.py`: **prototipo de validación, no es código de producción**. Importa TDLC desde una ruta absoluta.

```
python3 docs/specs/espanol/validar_gramatica.py docs/specs/espanol/gramatica_v0.txt docs/specs/espanol/casos_borde.txt
```

## 9. Decisiones del equipo (2026-10-16)

| # | Pregunta | Decisión |
|---|---|---|
| 1 | ¿Se ignora el tiempo verbal? | **Sí.** `leyó` = `lee` = `Leer` |
| 2 | ¿"Joven" (N) y "joven" (Adj) son el mismo predicado? | **No.** Son predicados distintos y se pregunta cuál se quiso decir |
| 3 | ¿Se aceptan palabras sin tilde? | **Se pregunta** cuál era la palabra. Nunca se corrige en silencio |
| 4 | ¿El sujeto disyuntivo y los numerales entran en v1? | **Sí.** Ya están en la gramática y en los casos borde |
| 5 | ¿Qué se muestra cuando hay ambigüedad? | Se pregunta siempre, y después se muestra **la lectura que el usuario eligió** (§5.1) |
