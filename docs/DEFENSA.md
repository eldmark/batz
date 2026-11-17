# Guía de defensa — Bat’z (MM3032)

## Cómo ejecutar la demostración

Desde la raíz del proyecto:

```bash
python3 evaluador.py
```

Abrir `http://127.0.0.1:8765/` en el navegador (también `docker compose up --build`). Pulsar «Cargar ejemplo» (en Evaluar hay además un menú de casos de ejemplo): el dominio es `{0,1}`, `a` vale `0`, `Pᴵ={(0)}` y `Qᴵ={(1)}`. La fórmula `∀x (P(x) → Q(x))` es falsa; `x=0` es el primer contraejemplo. Cambiarla a `∃x P(x)` muestra el testigo `0`. Las tablas y el editor aceptan teclado; los botones insertan símbolos en la posición del cursor.

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
| `countermodels.py` | Aporte creativo: busca modelos estrictos que falsifican una sentencia, y modelos donde las premisas valen y la conclusión no | Enumera por tamaño de dominio, respeta límites de tiempo/candidatos/tablas y revalida el hallazgo. Sin hallazgo: `unknown`, nunca «válida». Deja una bitácora (tamaños, candidatos, un ejemplo descartado) que el avatar narra. |
| `proof/fitch.py` | Dispone un certificado ya verificado en notación de Fitch | Cada hipótesis que una regla descarga abre una caja; ∀I y ∃E marcan su variable nueva. `check_layout` comprueba que cada línea cite líneas visibles y lo mismo que el paso del certificado. |
| `spanish_semantics.py` | Compone los árboles del español en fórmulas | El sujeto y el objeto de la oración principal pueden intercambiar su alcance; las relativas y el antecedente de «si» son islas; «ningún» no reparte su negación. |

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

### Preguntas sobre los aportes nuevos

11. **¿La vista Fitch es la misma prueba que aceptó el verificador?** Sí. El verificador revisa el certificado con contextos explícitos; la vista solo lo reordena y renumera. `check_layout` comprueba, línea por línea, que se citan las mismas fórmulas que el paso del certificado y que cada caja empieza con lo que su regla descarga. Se probó con las 88 pruebas del corpus y con certificados de Kalmár.
12. **¿Por qué hay pasos escritos antes de abrir una caja?** Porque no dependen de lo que la caja supone: así siguen visibles después de cerrarla. Lo que menciona la variable nueva de ∀I o ∃E se queda dentro de su caja.
13. **¿Por qué «Algún profesor admira a cada estudiante» tiene dos lecturas y «Todos leyeron todos los libros» una?** Con cuantificadores distintos (∃ y ∀) el orden cambia lo que se afirma: hay modelos donde una lectura es verdadera y la otra falsa. Con el mismo cuantificador simple, ∀x∀y ≡ ∀y∀x y ∃x∃y ≡ ∃y∃x, así que no hay nada que preguntar.
14. **¿Por qué `p → q` se lee como lógica proposicional?** En posición de fórmula, una minúscula sola no puede ser un término (los términos van dentro de un predicado o de `=`). Si todo el problema es proposicional, la validez es decidible: la tabla de verdad da el veredicto y Kalmár construye la prueba, que el verificador revisa.
15. **El contramodelo de Demostrar tiene una relación vacía, ¿no lo prohíbe el proyecto?** El perfil MM3032 la prohíbe para el modo Evaluar. Una consecuencia se juzga en todos los modelos de la semántica clásica, que sí admite relaciones vacías; por eso ese contramodelo no se puede abrir en Evaluar, y la interfaz lo dice.

## Ensayo con fórmulas no preparadas

Pedir a otra persona una fórmula que use los símbolos declarados. Antes de pulsar Evaluar, identificar libres y predecir el resultado a mano con la tabla de `D`. Comparar el resultado y desplegar cada paso. Probar también una entrada inválida (por ejemplo `P(a,a)`); debe aparecer el diagnóstico sin badge de verdad.

Para el aporte creativo, buscar un contramodelo de `∀x P(x)` con `P` unario: con el perfil de relaciones no vacías, el primer tamaño posible es 2. Cargarlo en las tablas y evaluar la misma fórmula. Repetir con tamaño máximo 1: el resultado debe ser `unknown`, sin afirmación de validez. Exportar el modelo, importarlo de nuevo y comprobar que conserva su interpretación.

## Revisión humana pendiente

La revisión cruzada del equipo de `FORMAL_LANGUAGE.md`, `SEMANTICS.md` y `ACCEPTANCE_FIXTURES.md` no se puede firmar automáticamente. Cada integrante debe revisar ejemplos, condiciones laterales y límites, y registrar nombre, fecha y observaciones en `docs/decisions/OPEN_QUESTIONS.md`. La lista completa de lo que necesita personas, para ir marcando, está en `docs/validation/REVISION-EQUIPO.md`.

## Demostración de los dos motores

En el modo «Demostrar», escribir `∀x (P(x) → Q(x))` y `P(a)` como premisas, `Q(a)` como conclusión y `a` como constante. Debe salir «Demostrada» con cuatro líneas en notación de Fitch y, debajo, «Los dos motores coinciden» con la refutación por resolución de cinco cláusulas. Borrar un paréntesis de una premisa: la revisión de sintaxis marca el punto exacto y el botón se desactiva.

Con el botón de ejemplo de Demostrar («Cargar ejemplo» en la barra superior, que va rotando) se recorren tres casos; las tarjetas de Inicio «Practica lo que probaron Gödel y Turing» cargan además tres casos ligados a resultados de Gödel y Turing. El segundo, `∀x ∃y Ama(x, y)` contra `∃y ∀x Ama(x, y)`, sale «No se sigue» con un contramodelo verificado de dos elementos (`Ama` como matriz: cada uno ama al otro). «Abrir en Evaluar» lo carga con la conclusión, y al evaluarla sale «Falso». «Ver paso a paso» muestra al avatar contando la búsqueda antes de explicar por qué falla. El tercero es la ley de Peirce, `((p → q) → p) → p`: con letras minúsculas se decide como lógica proposicional, y la prueba tiene cajas anidadas con RAA. Cambiar a premisa `p → q` y conclusión `q → p`: sale «No se sigue» con la valuación p = F, q = V.

Para el evaluador, cargar `ejemplos/grafo.logos`: ocho fórmulas se evalúan de una vez, siete coinciden con el valor que el archivo esperaba y una (`Q(a)`) se rechaza por símbolo no declarado, sin valor de verdad.

## Demostración del español y del avatar

En «Escribir la fórmula en español», probar «Todos los perros ladran». Ninguna de las dos palabras está en el léxico: aparece un aviso con lo que se supuso (`perros`, sustantivo masculino plural; `ladran`, verbo sin objeto, plural), con su probabilidad, y la fórmula `∀x (Perro(x) → Ladrar(x))`. Probar después «Perros los todos ladran»: se rechaza, porque la categoría propuesta no basta si la gramática no encuentra análisis. Pregunta probable: *¿el modelo decide la fórmula?* No: solo propone la categoría de una palabra; la estructura sale de la gramática y la persona ve el supuesto antes de usarla.

Tras evaluar una fórmula con cuantificadores, pulsar «Ver paso a paso». El avatar señala el elemento que se está probando, y un clic en cualquier elemento del dominio salta al caso que el cuantificador prueba con él. Al terminar el recorrido reacciona al valor de la fórmula. Con «Leer en voz alta» (requiere una voz en español instalada en el sistema), su boca se abre y se redondea con las vocales de cada palabra que dice.

En el panel de español, «Algún profesor admira a cada estudiante» da dos lecturas (∃∀ y ∀∃). Pregunta probable: *¿y «Todos los estudiantes leyeron todos los libros»?* Una sola: las dos órdenes son equivalentes.

## Demostración del diccionario

En «Escribir la fórmula en español» probar «Si una persona es humana, entonces es mortal»: da `∀x (Persona(x) ∧ Humano(x) → Mortal(x))` sin ningún supuesto, porque las tres palabras están en el diccionario. Con «humano» en vez de «humana» se rechaza y propone la corrección. En el modo «Diccionario», buscar `durmieron` muestra el verbo `dormir` con todas sus formas y el símbolo `Dormir`. Consultar `galopan`, que no está: el modelo propone verbo sin objeto y lema `galopar`; al guardar, la frase «Todos los unicornios galopan» ya solo supone `unicornios`.

Preguntas probables: *¿de dónde sale el género de un sustantivo?* Del diccionario, no de la terminación. *¿Cómo sabe que «duermen» es «dormir»?* Porque el diccionario genera las formas a partir del infinitivo y del cambio de raíz declarado; no lo adivina. *¿Un modelo de lenguaje decide algo al evaluar?* No: se usó para redactar el léxico, que es un archivo revisable; al correr solo hay tablas, una gramática y un clasificador pequeño que propone y pide confirmación.

## Sinónimos y sentidos

«Todo can ladra» da exactamente la misma fórmula que «Todo perro ladra»: los sinónimos comparten símbolo, así que para la lógica son la misma frase. «Juan compra un banco» da dos lecturas, `Banco_asiento` y `Banco_entidad`, con una nota que dice qué sentido es cada una: igual que la ambigüedad de alcance, no se elige en silencio. Pregunta probable: *¿por qué dos símbolos distintos para «banco»?* Porque en lógica un predicado fija un significado; si fueran el mismo, se podría «demostrar» algo mezclando los dos sentidos.

## Árbol de cada fórmula

Evaluar `∀x (P(x) → ∃y R(x, y))` y pulsar «Árbol»: cada nodo trae su valor y bajo cada cuantificador hay una rama por elemento del dominio (`x = 0`, `x = 1`…); las hojas dicen si la tupla pertenece a la relación (`(0, 1) ∈ Rᴵ`). Es la definición de Tarski dibujada: se ve por qué un `∀` es falso (una rama falsa) o un `∃` verdadero (una rama verdadera). Con «Estructura» se ve el árbol sintáctico. Pregunta probable: *¿el árbol se calcula aparte?* No: se lee de la traza que el verificador ya aceptó, así que no puede contradecir el resultado.
