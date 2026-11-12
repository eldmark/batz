# Guía de defensa — LOGOS MM3032

## Cómo ejecutar la demostración

Desde la raíz del proyecto:

```bash
python3 evaluador.py
```

Abrir `http://127.0.0.1:8765/` en el navegador (también `docker compose up --build`). Pulsar «Ejemplo»: el dominio es `{0,1}`, `a` vale `0`, `Pᴵ={(0)}` y `Qᴵ={(1)}`. La fórmula `∀x (P(x) → Q(x))` es falsa; `x=0` es el primer contraejemplo. Cambiarla a `∃x P(x)` muestra el testigo `0`. Las tablas y el editor aceptan teclado; los botones insertan símbolos en la posición del cursor.

## Mapa de módulos y argumento matemático

| Módulo | Función | Regla defendible |
|---|---|---|
| `lexer.py`, `parser.py`, `ast.py` | Texto → tokens → árbol bien formado con posiciones | La precedencia y el alcance de cuantificadores son sintácticos. `∀x P(x) → Q(x)` se lee `(∀x P(x)) → Q(x)` en este lenguaje. |
| `symbols.py` | Comprueba declaraciones y aridades contra `Signature` | Un símbolo no declarado o usado con otra aridad es entrada inválida, no una fórmula falsa. |
| `model.py`, `interpretation.py` | Representa `D`, constantes, funciones totales y relaciones; aplica las restricciones MM3032 | `D ≠ ∅`; `fᴵ : Dⁿ → D` debe tener una salida para cada entrada. En MM3032, cada relación declarada debe ser no vacía. |
| `transform.py` | Calcula variables libres y sustitución sin captura | Una variable libre requiere una asignación; una ligada toma su valor del cuantificador. |
| `semantics.py` | Evalúa términos y fórmulas; genera una traza completa y la comprueba | Tarski: `𝓜,s ⊨ ∀x φ` si para cada `d∈D`, `𝓜,s[x↦d] ⊨ φ`; `∃` requiere alguno. Los conectivos usan sus tablas clásicas. |
| `project.py` | Fachada `libres` / `evaluar` | Se valida firma, modelo, fórmula y entorno antes de devolver un valor. `invalid_input` nunca lleva valor ni traza. |
| `explain.py` | Deriva texto y árbol de explicación de una traza ya verificada | Un `∃` verdadero muestra el primer testigo; un `∀` falso, el primer contraejemplo; los otros dos casos muestran toda la tabla de `D`. |
| `server.py`, `web/` | Interfaz local, sin dependencias externas | El navegador recoge datos y muestra la explicación; Python decide el valor. El servidor escucha solo en `127.0.0.1`. |
| `proof/`, `propositional.py` | Aportes creativos existentes: prueba, verificador y decisión proposicional | Un certificado aceptado respalda `proved`; agotar búsqueda en FOL significa `unknown`. No forma parte del cálculo del valor en un modelo. |
| `resolution/` | Aporte creativo: segundo demostrador, por resolución, independiente del primero | Refuta premisas ∪ {¬conclusión}. Si deriva la cláusula vacía, la consecuencia vale; si satura sin ella, no vale; si agota límites, no dice nada. Solo contrasta: `proved` exige certificado de deducción natural. |
| `modelfile.py` | Lee archivos `.logos` con modelo y fórmulas | Solo lee la forma; la validación matemática la hace `build_interpretation`. |
| `countermodels.py` | Aporte creativo: busca modelos estrictos que falsifican una sentencia | Enumera por tamaño de dominio, respeta límites de tiempo/candidatos/tablas y revalida el hallazgo. Sin hallazgo: `unknown`, nunca «válida». |

## Diez preguntas probables

1. **¿Por qué no aceptan un dominio vacío?** El enunciado y el perfil del proyecto exigen `D ≠ ∅`. Esto también evita que `∀x P(x)` sea verdadero por vacuidad mientras `∃x P(x)` sea falso en un dominio vacío.
2. **¿Qué significa `P(a)` verdadero?** Evaluamos `a` en `D` y comprobamos si la tupla de un elemento `(aᴵ,)` pertenece a la extensión `Pᴵ`.
3. **¿Qué significa que una función sea total?** Para cada tupla de `Dⁿ` hay exactamente un valor en `D`; una celda sin valor invalida la interpretación.
4. **¿Por qué la traza no hace cortocircuito?** Registra todas las instancias de cuantificadores y ambos lados de conectivos. Eso permite explicar y auditar el resultado completo; `check_trace` verifica cada nodo.
5. **¿Qué pasa si `x` aparece libre y cuantificada?** Solo se pide entorno para las ocurrencias libres. Dentro de `∀x` o `∃x`, la asignación temporal `s[x↦d]` sombrea el valor exterior.
6. **¿Por qué un símbolo sin declarar no vale falso?** La verdad solo está definida para fórmulas interpretadas sobre la firma. Falta de declaración es un error de entrada, anterior a Tarski.
7. **¿Por qué rechazan relaciones vacías si la lógica suele permitirlas?** Es una restricción del perfil MM3032. El núcleo `FiniteModel` sí permite `∅` para conservar la semántica clásica general.
8. **¿Por qué el proyecto prohíbe predicados de aridad cero?** En `D⁰={()}`, exigir relación no vacía forzaría que todos fueran verdaderos. Para poder expresar falso en proposicional se usa el núcleo general, fuera del perfil estricto.
9. **Si la fórmula salió verdadera, ¿es válida universalmente?** No. Solo es verdadera en la interpretación y, si es abierta, el entorno elegidos. Validez universal requiere todos los modelos; la búsqueda acotada no la decide.
10. **¿Cómo saben que la explicación no inventa el resultado?** `explain` llama primero a `check_trace`; cada resumen usa los valores de los hijos verificados. Una traza manipulada produce `invalid_trace`.

## Ensayo con fórmulas no preparadas

Pedir a otra persona una fórmula que use los símbolos declarados. Antes de pulsar Evaluar, identificar libres y predecir el resultado a mano con la tabla de `D`. Comparar el resultado y desplegar cada paso. Probar también una entrada inválida (por ejemplo `P(a,a)`); debe aparecer el diagnóstico sin badge de verdad.

Para el aporte creativo, buscar un contramodelo de `∀x P(x)` con `P` unario: con el perfil de relaciones no vacías, el primer tamaño posible es 2. Cargarlo en las tablas y evaluar la misma fórmula. Repetir con tamaño máximo 1: el resultado debe ser `unknown`, sin afirmación de validez. Exportar el modelo, importarlo de nuevo y comprobar que conserva su interpretación.

## Revisión humana pendiente

La revisión cruzada del equipo de `FORMAL_LANGUAGE.md`, `SEMANTICS.md` y `ACCEPTANCE_FIXTURES.md` no se puede firmar automáticamente. Cada integrante debe revisar ejemplos, condiciones laterales y límites, y registrar nombre, fecha y observaciones en `docs/decisions/OPEN_QUESTIONS.md`.

## Demostración de los dos motores

En el modo «Demostrar», escribir `∀x (P(x) → Q(x))` y `P(a)` como premisas, `Q(a)` como conclusión y `a` como constante. Debe salir «Demostrada» con cuatro pasos y, debajo, «Los dos motores coinciden» con la refutación por resolución de cinco cláusulas. Cambiar a premisa `P → Q` y conclusión `Q → P`: sale «No se sigue», porque la resolución satura sin contradicción; el motor de deducción natural por sí solo solo habría dicho «sin prueba». Borrar un paréntesis de una premisa: la revisión de sintaxis marca el punto exacto y el botón se desactiva.

Para el evaluador, cargar `ejemplos/grafo.logos`: ocho fórmulas se evalúan de una vez, siete coinciden con el valor que el archivo esperaba y una (`Q(a)`) se rechaza por símbolo no declarado, sin valor de verdad.

## Demostración del español y del avatar

En «Escribir la fórmula en español», probar «Todos los perros ladran». Ninguna de las dos palabras está en el léxico: aparece un aviso con lo que se supuso (`perros`, sustantivo masculino plural; `ladran`, verbo sin objeto, plural), con su probabilidad, y la fórmula `∀x (Perro(x) → Ladrar(x))`. Probar después «Perros los todos ladran»: se rechaza, porque la categoría propuesta no basta si la gramática no encuentra análisis. Pregunta probable: *¿el modelo decide la fórmula?* No: solo propone la categoría de una palabra; la estructura sale de la gramática y la persona ve el supuesto antes de usarla.

Tras evaluar una fórmula con cuantificadores, pulsar «Ver paso a paso». El avatar señala el elemento que se está probando, y un clic en cualquier elemento del dominio salta al caso que el cuantificador prueba con él. Al terminar el recorrido reacciona al valor de la fórmula.

## Demostración del diccionario

En «Escribir la fórmula en español» probar «Si una persona es humana, entonces es mortal»: da `∀x (Persona(x) ∧ Humano(x) → Mortal(x))` sin ningún supuesto, porque las tres palabras están en el diccionario. Con «humano» en vez de «humana» se rechaza y propone la corrección. En el modo «Diccionario», buscar `durmieron` muestra el verbo `dormir` con todas sus formas y el símbolo `Dormir`. Consultar `galopan`, que no está: el modelo propone verbo sin objeto y lema `galopar`; al guardar, la frase «Todos los unicornios galopan» ya solo supone `unicornios`.

Preguntas probables: *¿de dónde sale el género de un sustantivo?* Del diccionario, no de la terminación. *¿Cómo sabe que «duermen» es «dormir»?* Porque el diccionario genera las formas a partir del infinitivo y del cambio de raíz declarado; no lo adivina. *¿Un modelo de lenguaje decide algo al evaluar?* No: se usó para redactar el léxico, que es un archivo revisable; al correr solo hay tablas, una gramática y un clasificador pequeño que propone y pide confirmación.
