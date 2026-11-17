# Guía de uso y referencia de Bat’z

Esta guía reúne el uso detallado de cada sección de Bat’z (antes LOGOS): la API de Python, cada pantalla, los formatos de archivo y la voz opcional. La entrada del proyecto, con el recorrido corto para revisarlo, está en el [README](../README.md); la forma de ejecutarlo o publicarlo, en [PUBLICAR.md](PUBLICAR.md); el recorrido por el código, en [ARQUITECTURA.md](ARQUITECTURA.md).

## Fachada del proyecto MM3032 (M1)

```python
from batz import Signature, evaluar, libres

firma = Signature(constants={"a"}, predicates={"P": 1})
datos = {"domain": [0, 1], "constants": {"a": 0},
         "predicates": {"P": {"arity": 1, "tuples": [[0]]}}}
libres("P(x)", firma)               # ('x',)
resultado = evaluar(firma, datos, "P(x)", {"x": 0})
resultado.status, resultado.value   # ('ok', True)
```

`interpretacion` acepta un objeto o texto JSON con el formato de `FiniteModel`; la fachada exige exactamente los símbolos de la firma, relaciones no vacías y predicados de aridad positiva. Un error devuelve `status='invalid_input'`, diagnósticos en `errors` y ningún valor ni traza.

## Interfaz local (M2–M4)

```bash
python3 evaluador.py
```

Con Docker (no hace falta tener Python instalado):

```bash
docker compose up --build      # detener: docker compose down
```

La interfaz queda en `http://127.0.0.1:8765/`, publicada solo en este equipo. Otro puerto: `BATZ_PORT=9000 docker compose up --build`.

Abre `http://127.0.0.1:8765/`. La barra lateral tiene siete secciones: Inicio, Evaluar modelo, Demostrar, Practicar, Cuadernos, Diccionario y Aprender (más las páginas de Gödel, Turing y Church, a las que se llega desde Inicio). En Evaluar hay un menú de «casos de ejemplo» y el botón «Importar modelo» acepta uno de `ejemplos/*.logos` o un JSON exportado; en Demostrar, Diccionario y Cuadernos, el botón de la barra superior carga un ejemplo del modo en que estás. La explicación se construye desde una traza verificada; cada nodo tiene un resumen, detalles desplegables y posición en la fórmula. Guía de defensa: `docs/DEFENSA.md`.

### Practicar: 50 demostraciones interactivas

Abre `http://127.0.0.1:8765/#/practicar` o pulsa **Practicar** en la barra lateral. Son 50 ejercicios fijos, sin temática ni tiempo límite, divididos en tres categorías con sus propios contadores de progreso:

| Categoría | Niveles | Recorrido |
|---|---|---|
| Introducción | 01–10 | Pruebas de uno o dos pasos: conectores, hipótesis, particularización, testigos e igualdad. |
| Desafío | 11–40 | Contraposición, casos anidados, De Morgan, testigos nuevos, unicidad, funciones y primera inducción. |
| Modo Leyenda | 41–50 | Peirce, principio del bebedor, alcance de cuantificadores, funciones inyectivas/sobreyectivas y lemas por inducción. |

Las tres categorías están siempre disponibles. La dificultad aumenta por la combinación de estrategias y el control de dependencias, además de la extensión de las pruebas. La última demostración construye la conmutatividad de la suma en 49 pasos propios y tres inducciones; sus dos lemas también deben demostrarse.

En el inicio de Practicar hay un panel **Cómo se juega** (las reglas del juego en cinco ideas), el botón **Reglas y chuleta** (diálogo con las reglas completas y las 22 reglas de inferencia con un ejemplo verificado de cada una; también está como botón **Reglas** dentro de cada ejercicio) y **Ver el tutorial**: «Tu primera prueba en 2 minutos», una guía paso a paso sobre el ejercicio 01 real. La primera vez aparece además un banner «¿Primera vez? Haz el tutorial». El tutorial no se abre solo, se puede omitir con Esc y, si ya tenías el ejercicio 01 completo, tu prueba se restaura al terminar.

1. Elige un ejercicio. El objetivo y cada línea tienen su lectura española encima de la fórmula.
2. Selecciona una regla; la ayuda explica cuántas referencias requiere y en qué orden.
3. Escribe las referencias o toca los números de las líneas. Escribe la nueva fórmula con el teclado o los botones de símbolos. Completa el término, la variable o la plantilla si la regla los pide.
4. Pulsa **Comprobar paso** (también Ctrl/⌘ + Enter). Un error conserva tu entrada. **Deshacer** elimina el último paso.
5. El objetivo solo se completa si su prueba no depende de hipótesis ajenas a las premisas. Las hipótesis pendientes se pueden desplegar en cada línea. No son cajas Fitch: son las dependencias formales de cada derivación.

Hay tres pistas por ejercicio y una solución de referencia desplegable. Leerla no completa el ejercicio. Se aceptan otras pruebas correctas y están disponibles todas las reglas, con las recomendadas primero. Los pasos, el borrador y las pistas se guardan en este navegador; al recargar se vuelven a verificar las pruebas guardadas. Si no hay almacenamiento local, se puede jugar durante la sesión.

Los ejercicios aritméticos usan la notación funcional que admite el núcleo: `cero` representa 0, `s(t)` el sucesor, `suma(t,u)` la suma y `producto(t,u)` la multiplicación. Los axiomas y las instancias del esquema de inducción son premisas explícitas; no se evalúa la aritmética de Peano como si tuviera un modelo finito.

Al actualizar desde la versión de diez ejercicios se conservan y revalidan las pruebas compatibles. Los antiguos 05, 06 y 10 se sustituyeron por ejercicios introductorios; sus borradores se archivan en el registro `previous` del progreso local. Los temas más avanzados reaparecen en Desafío. Una revisión matemática por ejercicio permite detectar futuros cambios de enunciado sin atribuir una solución antigua al nuevo problema.

El banco y las pistas están en `src/batz/practice_bank.py`; el tutor y la API están en `src/batz/practice.py`. El servidor recalcula todos los contextos y comprueba los prefijos con el checker independiente; nunca confía en contextos o marcas de éxito del cliente. Al terminar verifica el certificado contra las premisas reales del ejercicio. Las pruebas se ejecutan con:

```powershell
$env:PYTHONPATH = "src;tests"
python -m unittest discover -s tests -p test_practice.py -v
```

La validación opcional de navegador está en `scripts/validate_practice_browser.cjs`; requiere una instalación externa de Playwright y un servidor Bat’z activo. No se necesitan dependencias nuevas para ejecutar el juego. Para exportar sus fixtures desde la raíz del repositorio:

```powershell
$env:PYTHONPATH = "src"
python -c "import json; from pathlib import Path; from batz.practice import EXERCISES; Path('practice-fixtures.json').write_text(json.dumps(EXERCISES), encoding='utf-8')"
$env:BATZ_PRACTICE_FIXTURES = "$PWD\practice-fixtures.json"
# Opcional: PLAYWRIGHT_MODULE apunta al paquete playwright o playwright-core existente.
# Opcional: PLAYWRIGHT_CHROMIUM_EXECUTABLE apunta a un Chromium ya instalado.
# Opcional: BATZ_BASE_URL cambia http://127.0.0.1:8765.
node scripts/validate_practice_browser.cjs
```

La sección «Buscar un modelo donde sea falsa» busca una interpretación estricta que falsifique una **sentencia**. Usa tamaños de dominio 1–3, hasta 5000 candidatos o 2 segundos; si no encuentra uno, devuelve `unknown` y no afirma validez universal. El hallazgo se muestra como tablas (la relación binaria, como matriz) y se puede cargar en las tablas del modelo. «Exportar JSON» guarda firma, interpretación y fórmula; «Importar modelo» valida el modelo antes de cargarlo.

### Modo Demostrar

- **Prueba en notación de Fitch.** El certificado de deducción natural que acepta el verificador se dispone en líneas con cajas: cada hipótesis que se descarga (→I, ¬I, RAA, ∨E, ∃E) abre una, y la variable nueva de ∀I y ∃E queda marcada. Solo cambia la presentación; `proof/fitch.py` comprueba que cada línea cite lo mismo que el certificado.
- **«No se sigue» con su contramodelo.** Si no hay prueba, se busca un modelo de 1 a 3 elementos donde las premisas son verdaderas y la conclusión falsa (semántica estándar: admite relaciones vacías). Se verifica con el evaluador y se puede abrir en el modo Evaluar con la conclusión.
- **Letras proposicionales.** Una minúscula sola en posición de fórmula (`p → q`) es una letra: si todo el problema es proposicional, se decide completo con la tabla de verdad y el lema de Kalmár (prueba o valuación que lo refuta). Las letras se muestran como se escribieron.
- **Resolución** sigue como segunda opinión independiente.

### En el teléfono

Bajo 720 px de ancho, la cabecera se compacta, Evaluar y Diccionario se recorren en dos sub-pestañas («1 · Modelo / 2 · Fórmula», «Buscar / Añadir»), los símbolos se editan en tarjetas y, mientras se escribe una fórmula, el teclado lógico queda pegado encima del teclado del sistema. Todo lo que se toca mide al menos 44 px y los campos usan 16 px para que iPhone no haga zoom. En el paso a paso se cambia de paso deslizando sobre la escena.

Las microinteracciones (píldora que se desliza entre pestañas, botones con estado de carga y ✓/✕, veredicto letra por letra, avisos que entran y se van solos, contadores, casillas que dibujan su palomita) se inspiraron en componentes de 21st.dev y están reescritas a mano en CSS y JavaScript, sin dependencias. Con «reducir movimiento» activado en el sistema, se apagan.

## Ensayo final reproducible

```bash
PYTHONPATH=src python3 scripts/validate_demo.py --seed 20261102
```

El reporte y el recorrido para la entrega están en `docs/validation/ENSAYO-MM3032.md`. El ensayo usa solo HTTP local y deja claro cuáles comprobaciones necesitan una persona frente al navegador.

## Archivos preparados

Un archivo `.logos` (la extensión conserva el nombre anterior del proyecto) describe un modelo y sus fórmulas en texto plano; el formato está documentado en `src/batz/modelfile.py` y hay dos ejemplos en `ejemplos/`. La interfaz evalúa todas las fórmulas del archivo y compara cada una con su valor esperado, si lo trae.

## Diccionario

La sección «Diccionario» muestra el diccionario del español (`src/batz/lexicon.tsv`, unos 6200 entradas más 2700 deducidas por reglas con sus formas) y permite añadir palabras; las tuyas se guardan en `datos/lexico_usuario.tsv`. Con Docker esa carpeta es un volumen, así que no se pierden al reconstruir.

Para ampliarlo en lote: `PYTHONPATH=src python3 scripts/lexicon_queue.py mine texto.txt` (cola de candidatas), `next` (propuestas del modelo), `accept` (añade las revisadas). Ver `docs/plans/PLAN_MM3032.md` §10.

## Cuaderno: preguntas a tus propias fuentes

La sección «Cuadernos» reúne textos en español («fuentes») y contesta preguntas usando solo lo que ellos dicen. Abre «Cuadernos» y pulsa «Crear el cuaderno de ejemplo».

- **Fuentes.** Pega un texto o sube un `.txt`. Cada oración pasa por el español controlado: si tiene una sola lectura, es una premisa; si tiene varias, o si hubo que suponer la categoría de una palabra, espera a que elijas; si queda fuera de la gramática, se marca con el motivo y no se usa. Al abrir una fuente, el color de cada oración dice en cuál de los tres casos está, y al tocarla se ve su fórmula.
- **Preguntas.** Se escriben como una afirmación entre signos de pregunta («¿Juan aprueba?»). Hay cinco respuestas: **Sí** (hay prueba verificada), **No** (hay prueba verificada de lo contrario), **No lo deciden** (ni una ni otra: se muestran un modelo donde es falsa y otro donde es verdadera), **No se sigue** y **Sin respuesta** (se agotaron los límites).
- **Citas.** Cada premisa que usa la prueba lleva un número que abre la fuente en la oración de donde salió. La derivación solo lista las premisas que usa, aunque el cuaderno tenga muchas más.
- **Avisos.** Si las fuentes se contradicen entre sí, la respuesta lo dice; si la pregunta usa una palabra que ninguna premisa menciona, también.

«Se sigue de tus fuentes» quiere decir que hay una prueba desde lo que dicen, no que lo que dicen sea cierto. Ningún modelo de lenguaje interviene: una oración que la gramática no entiende no se interpreta «más o menos», se deja fuera.

Los cuadernos se guardan en `datos/cuadernos/` (otra carpeta: variable `BATZ_NOTEBOOKS`), uno por archivo, y se exportan e importan como un solo `.json`. En disco solo van los textos y las lecturas elegidas; el análisis y las respuestas se recalculan cada vez, así que siguen al diccionario actual. Límites: 20 fuentes por cuaderno, 20 000 caracteres y 150 oraciones por fuente, 80 premisas por pregunta.

Para que haya contramodelos con muchas premisas, `modelfinder.py` busca modelos desplegando los cuantificadores sobre dominios pequeños en vez de enumerar interpretaciones completas; lo que encuentra se vuelve a evaluar con el evaluador antes de mostrarse. Código: `src/batz/notebook.py`, `src/batz/modelfinder.py`; pruebas: `tests/test_notebook.py`, `tests/test_modelfinder.py`.

## Español controlado

El panel «O escríbela en español» (paso 2 de Evaluar) reconoce un fragmento pequeño y muestra todas sus lecturas. El sujeto y el objeto directo de la oración principal pueden intercambiar su alcance: «Todos los estudiantes leyeron un libro» y «Algún profesor admira a cada estudiante» dan dos lecturas cada una; «Todos los estudiantes leyeron todos los libros» da una, porque las dos órdenes dicen lo mismo. Lo que está dentro de una relativa o del «si» no cambia de alcance, y «ningún» tampoco. Hay que elegir una lectura antes de preparar el modelo. Las frases fuera del fragmento se rechazan. La especificación amplia y los casos todavía no cubiertos están en `docs/specs/SPANISH_CONTROLLED.md`.

## Narración y vista 3D opcionales

Al evaluar una fórmula, hallar un contramodelo o demostrar, «Explicación guiada» recorre los pasos verificados con pausa, avance, retroceso y repetición. En un contramodelo, el avatar cuenta primero la búsqueda (qué tamaños probó, cuántas interpretaciones descartó y un ejemplo que no sirve) y luego por qué la fórmula falla. En una prueba, narra las líneas de la vista Fitch con su mismo número. La vista 3D usa Three.js incluido localmente; la vista 2D queda disponible si WebGL falla.

El botón de la esquina de la escena pone el paso a paso en pantalla completa: la escena crece y el texto del paso y los controles quedan al lado (debajo en el teléfono). Las flechas ← → cambian de paso y Esc sale. En Android, si el teléfono está vertical, intenta girar a horizontal. En el iPhone, que no ofrece pantalla completa para estos elementos, la sección cubre la ventana.

La voz solo se activa si el usuario la marca. Hay dos fuentes de voz en español, ambas locales: las del navegador (en Windows: Configuración → Hora e idioma → Voz → Agregar voces → Español) y, si el navegador no ofrece ninguna (lo normal en Linux), las de `espeak-ng`, que genera el servidor en este equipo (el texto no sale de la máquina; ver «Voz de la explicación» más abajo). El selector «Voz» del reproductor lista ambas; «Automática» prefiere la del navegador. Si no hay ninguna, la casilla se desactiva, explica la causa y ofrece «Volver a buscar voces». Mientras habla, la boca del avatar sigue a la voz sílaba por sílaba:

- **Ritmo:** cuando la voz empieza una palabra, la palabra se parte en sílabas al ritmo medido de la voz, que se ajusta solo con el tiempo entre palabras. Así nunca se atrasa.
- **Letras, cifras y símbolos:** se cuentan por su nombre: «x» es «equis», «0» es «cero», «=» es «igual a».
- **Forma de la boca:** abre en las vocales abiertas, se redondea en «o» y «u» y junta los labios en m, b, p y v (morph targets `Boca_abierta` y `Boca_redonda` del GLB).
- **Voces que no avisan cada palabra:** la boca sigue un ritmo estimado a partir del texto.

### Voz de la explicación con espeak-ng (opcional)

El servidor genera el audio con `espeak-ng` (`src/batz/voice_output.py`, rutas `/api/voice/voices` y `/api/voice/speak`; contratos en `docs/specs/JSON_CONTRACTS.md` §8.7). Es una voz sintética, inteligible pero robótica; hay una masculina y una femenina por variante del español. Instalación: Arch/CachyOS `sudo pacman -S espeak-ng`, Debian/Ubuntu `sudo apt install espeak-ng`, Fedora `sudo dnf install espeak-ng`. La imagen de Docker ya lo incluye. Tras instalarlo no hace falta recargar la página: «Volver a buscar voces».

### Entrada por voz (opcional)

«Grabar frase» transcribe en este equipo con whisper.cpp; nada sale a internet. Para instalarlo, por usuario y sin administrador:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_voz.ps1      # Windows: ffmpeg (winget), whisper.cpp y el modelo base
```

```bash
bash scripts/instalar_voz.sh                                           # Linux o macOS (sin probar en esta entrega)
```

whisper.cpp y el modelo quedan en `%LOCALAPPDATA%\Batz\voz` (o `~/.local/share/batz/voz`), donde el servidor los encuentra sin variables de entorno; cada descarga se comprueba con su SHA-256. `-Modelo small` es más preciso y más lento. Para quitarlo: borrar esa carpeta y `winget uninstall --id Gyan.FFmpeg -e`. La imagen de Docker no incluye la transcripción por voz (whisper), pero sí `espeak-ng` para la voz de la explicación guiada. El texto transcrito siempre se muestra para revisarlo antes de traducirlo.

La procedencia y la licencia de Three.js, whisper.cpp y lo demás están en `docs/THIRD_PARTY.md`.

## Fases 1 a 3: compilador, semántica finita y pruebas (`src/batz/`)

```
PYTHONPATH=src:tests python3 -m unittest discover -s tests
```

Solo librería estándar de Python (3.10 o posterior). Sintaxis y símbolos: `docs/specs/FORMAL_LANGUAGE.md`. Semántica: `docs/specs/SEMANTICS.md`. Cálculo de pruebas: `docs/specs/PROOF_CALCULUS.md`. Contratos JSON: `docs/specs/JSON_CONTRACTS.md`. Arquitectura, plan y decisiones: `docs/architecture/`, `docs/plans/`, `docs/decisions/`.

```python
from batz import parse, to_string, substitute, Var
f = parse("∀x (P(x) → Q(x))")
to_string(f, ascii=True)   # 'forall x (P(x) -> Q(x))'
from batz import FiniteModel, is_true, evaluate
m = FiniteModel(["a"], predicates={"P": (1, []), "Q": (1, [("a",)])})
is_true(m, parse("∀x (Q(x) → P(x))"))   # False: contramodelo de la conversa
```

```python
from batz.proof import prove_text, format_certificate
r = prove_text(["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", constants=["a"])
r.status                          # 'proved' (solo si el checker aceptó el certificado)
print(format_certificate(r.certificate))
```

El buscador (`proof/search.py`) es incompleto: devuelve `unknown` (nunca "falso") al agotar profundidad, nodos o tiempo. El checker (`proof/checker.py`) no depende del buscador.

Lógica proposicional (siempre hay veredicto: prueba o contramodelo verificado):

```python
from batz import decide, parse
v = decide([parse("p → q", propositional=True)], parse("¬q → ¬p", propositional=True))
v.status, v.method                # ('proved', 'search'); el respaldo completo es 'kalmar'
```
