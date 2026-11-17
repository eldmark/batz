# LOGOS

Laboratorio de lógica de primer orden. Plan vigente del proyecto MM3032 (evaluador semántico): `docs/plans/PLAN_MM3032.md`. Fases originales en `docs/`.

## Fachada del proyecto MM3032 (M1)

```python
from logos import Signature, evaluar, libres

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

La interfaz queda en `http://127.0.0.1:8765/`, publicada solo en este equipo. Otro puerto: `LOGOS_PORT=9000 docker compose up --build`.

Abre `http://127.0.0.1:8765/` y pulsa «Ejemplo» (carga uno del modo en que estás), o «Cargar archivo» con uno de `ejemplos/*.logos`. La barra superior cambia entre cuatro modos: evaluar una fórmula en un modelo, demostrar una consecuencia, el diccionario y el cuaderno. La explicación se construye desde una traza verificada; cada nodo tiene un resumen, detalles desplegables y posición en la fórmula. Guía de defensa: `docs/DEFENSA.md`.

La sección «Buscar un modelo donde sea falsa» busca una interpretación estricta que falsifique una **sentencia**. Usa tamaños de dominio 1–3, hasta 5000 candidatos o 2 segundos; si no encuentra uno, devuelve `unknown` y no afirma validez universal. El hallazgo se muestra como tablas (la relación binaria, como matriz) y se puede cargar en las tablas del modelo. «Exportar JSON» guarda firma, interpretación y fórmula; «Cargar archivo» valida el modelo antes de cargarlo.

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

Un archivo `.logos` describe un modelo y sus fórmulas en texto plano; el formato está documentado en `src/logos/modelfile.py` y hay dos ejemplos en `ejemplos/`. La interfaz evalúa todas las fórmulas del archivo y compara cada una con su valor esperado, si lo trae.

## Diccionario

El tercer modo de la interfaz muestra el diccionario del español (`src/logos/lexicon.tsv`, unos 6200 entradas más 2700 deducidas por reglas con sus formas) y permite añadir palabras; las tuyas se guardan en `datos/lexico_usuario.tsv`. Con Docker esa carpeta es un volumen, así que no se pierden al reconstruir.

Para ampliarlo en lote: `PYTHONPATH=src python3 scripts/lexicon_queue.py mine texto.txt` (cola de candidatas), `next` (propuestas del modelo), `accept` (añade las revisadas). Ver `docs/plans/PLAN_MM3032.md` §10.

## Cuaderno: preguntas a tus propias fuentes

El cuarto modo reúne textos en español («fuentes») y contesta preguntas usando solo lo que ellos dicen. Abre la pestaña «Cuaderno» y pulsa «Ejemplo».

- **Fuentes.** Pega un texto o sube un `.txt`. Cada oración pasa por el español controlado: si tiene una sola lectura, es una premisa; si tiene varias, o si hubo que suponer la categoría de una palabra, espera a que elijas; si queda fuera de la gramática, se marca con el motivo y no se usa. Al abrir una fuente, el color de cada oración dice en cuál de los tres casos está, y al tocarla se ve su fórmula.
- **Preguntas.** Se escriben como una afirmación entre signos de pregunta («¿Juan aprueba?»). Hay cinco respuestas: **Sí** (hay prueba verificada), **No** (hay prueba verificada de lo contrario), **No lo deciden** (ni una ni otra: se muestran un modelo donde es falsa y otro donde es verdadera), **No se sigue** y **Sin respuesta** (se agotaron los límites).
- **Citas.** Cada premisa que usa la prueba lleva un número que abre la fuente en la oración de donde salió. La derivación solo lista las premisas que usa, aunque el cuaderno tenga muchas más.
- **Avisos.** Si las fuentes se contradicen entre sí, la respuesta lo dice; si la pregunta usa una palabra que ninguna premisa menciona, también.

«Se sigue de tus fuentes» quiere decir que hay una prueba desde lo que dicen, no que lo que dicen sea cierto. Ningún modelo de lenguaje interviene: una oración que la gramática no entiende no se interpreta «más o menos», se deja fuera.

Los cuadernos se guardan en `datos/cuadernos/` (otra carpeta: variable `LOGOS_NOTEBOOKS`), uno por archivo, y se exportan e importan como un solo `.json`. En disco solo van los textos y las lecturas elegidas; el análisis y las respuestas se recalculan cada vez, así que siguen al diccionario actual. Límites: 20 fuentes por cuaderno, 20 000 caracteres y 150 oraciones por fuente, 80 premisas por pregunta.

Para que haya contramodelos con muchas premisas, `modelfinder.py` busca modelos desplegando los cuantificadores sobre dominios pequeños en vez de enumerar interpretaciones completas; lo que encuentra se vuelve a evaluar con el evaluador antes de mostrarse. Código: `src/logos/notebook.py`, `src/logos/modelfinder.py`; pruebas: `tests/test_notebook.py`, `tests/test_modelfinder.py`.

## Español controlado

El panel «Escribir la fórmula en español» reconoce un fragmento pequeño y muestra todas sus lecturas. El sujeto y el objeto directo de la oración principal pueden intercambiar su alcance: «Todos los estudiantes leyeron un libro» y «Algún profesor admira a cada estudiante» dan dos lecturas cada una; «Todos los estudiantes leyeron todos los libros» da una, porque las dos órdenes dicen lo mismo. Lo que está dentro de una relativa o del «si» no cambia de alcance, y «ningún» tampoco. Hay que elegir una lectura antes de preparar el modelo. Las frases fuera del fragmento se rechazan. La especificación amplia y los casos todavía no cubiertos están en `docs/specs/SPANISH_CONTROLLED.md`.

## Narración y vista 3D opcionales

Al evaluar una fórmula, hallar un contramodelo o demostrar, «Ver paso a paso» recorre los pasos verificados con pausa, avance, retroceso y repetición. En un contramodelo, el avatar cuenta primero la búsqueda (qué tamaños probó, cuántas interpretaciones descartó y un ejemplo que no sirve) y luego por qué la fórmula falla. En una prueba, narra las líneas de la vista Fitch con su mismo número. La vista 3D usa Three.js incluido localmente; la vista 2D queda disponible si WebGL falla.

El botón de la esquina de la escena pone el paso a paso en pantalla completa: la escena crece y el texto del paso y los controles quedan al lado (debajo en el teléfono). Las flechas ← → cambian de paso y Esc sale. En Android, si el teléfono está vertical, intenta girar a horizontal. En el iPhone, que no ofrece pantalla completa para estos elementos, la sección cubre la ventana.

La voz solo se activa si el usuario la marca y el sistema tiene una voz local en español; si no la hay, la casilla se desactiva y explica cómo instalarla (en Windows: Configuración → Hora e idioma → Voz → Agregar voces → Español). Mientras habla, la boca del avatar sigue a la voz sílaba por sílaba:

- **Ritmo:** cuando la voz empieza una palabra, la palabra se parte en sílabas al ritmo medido de la voz, que se ajusta solo con el tiempo entre palabras. Así nunca se atrasa.
- **Letras, cifras y símbolos:** se cuentan por su nombre: «x» es «equis», «0» es «cero», «=» es «igual a».
- **Forma de la boca:** abre en las vocales abiertas, se redondea en «o» y «u» y junta los labios en m, b, p y v (morph targets `Boca_abierta` y `Boca_redonda` del GLB).
- **Voces que no avisan cada palabra:** la boca sigue un ritmo estimado a partir del texto.

### Entrada por voz (opcional)

«Grabar frase» transcribe en este equipo con whisper.cpp; nada sale a internet. Para instalarlo, por usuario y sin administrador:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_voz.ps1      # Windows: ffmpeg (winget), whisper.cpp y el modelo base
```

```bash
bash scripts/instalar_voz.sh                                           # Linux o macOS (sin probar en esta entrega)
```

whisper.cpp y el modelo quedan en `%LOCALAPPDATA%\LOGOS\voz` (o `~/.local/share/logos/voz`), donde el servidor los encuentra sin variables de entorno; cada descarga se comprueba con su SHA-256. `-Modelo small` es más preciso y más lento. Para quitarlo: borrar esa carpeta y `winget uninstall --id Gyan.FFmpeg -e`. La imagen de Docker no incluye la voz. El texto transcrito siempre se muestra para revisarlo antes de traducirlo.

La procedencia y la licencia de Three.js, whisper.cpp y lo demás están en `docs/THIRD_PARTY.md`.

## Fases 1 a 3: compilador, semántica finita y pruebas (`src/logos/`)

```
PYTHONPATH=src:tests python3 -m unittest discover -s tests
```

Solo librería estándar de Python (≥ 3.10). Sintaxis y símbolos: `docs/specs/FORMAL_LANGUAGE.md`. Semántica: `docs/specs/SEMANTICS.md`. Cálculo de pruebas: `docs/specs/PROOF_CALCULUS.md`. Contratos JSON: `docs/specs/JSON_CONTRACTS.md`. Arquitectura, plan y decisiones: `docs/architecture/`, `docs/plans/`, `docs/decisions/`.

```python
from logos import parse, to_string, substitute, Var
f = parse("∀x (P(x) → Q(x))")
to_string(f, ascii=True)   # 'forall x (P(x) -> Q(x))'
from logos import FiniteModel, is_true, evaluate
m = FiniteModel(["a"], predicates={"P": (1, []), "Q": (1, [("a",)])})
is_true(m, parse("∀x (Q(x) → P(x))"))   # False: contramodelo de la conversa
```

```python
from logos.proof import prove_text, format_certificate
r = prove_text(["∀x (P(x) → Q(x))", "P(a)"], "Q(a)", constants=["a"])
r.status                          # 'proved' (solo si el checker aceptó el certificado)
print(format_certificate(r.certificate))
```

El buscador (`proof/search.py`) es incompleto: devuelve `unknown` (nunca "falso") al agotar profundidad, nodos o tiempo. El checker (`proof/checker.py`) no depende del buscador.

Lógica proposicional (siempre hay veredicto: prueba o contramodelo verificado):

```python
from logos import decide, parse
v = decide([parse("p → q", propositional=True)], parse("¬q → ¬p", propositional=True))
v.status, v.method                # ('proved', 'search'); el respaldo completo es 'kalmar'
```
