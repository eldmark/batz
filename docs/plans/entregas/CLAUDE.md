# Entrega Claude: aplicación y pantallas

Base común: `ea78374`
Rama: `rediseno/claude-interfaz` (worktree `../proyecto1-claude`)
Estado: en curso

## Completado

- F1 (shell, navegación, Inicio): sidebar de 240 px colapsable (preferencia en `localStorage`
  `batz-sidebar`; se contrae sola entre 901 y 1100 px), menú móvil con botón, fondo, Escape y
  foco; encabezado con título, Importar modelo (solo Evaluar), ejemplo rotulado por módulo y Ayuda
  contextual; rutas `#/inicio|evaluar|demostrar|cuadernos|diccionario`, hash desconocido → Inicio;
  Atrás/Adelante/recarga; un único `main`; borradores conservados al navegar (las secciones solo se ocultan).
- Inicio: pregunta central, 4 tarjetas y 3 ejercicios que abren el módulo y cargan datos; si
  reemplazan datos de Evaluar/Demostrar se avisa con acción «Deshacer».

- F2/F4 (parcial): pasos rotulados en Evaluar; Demostrar explica «todos los modelos» frente a una interpretación;
  el contraste de motores es un `<details>` tras el veredicto (abierto solo si hay discrepancia real);
  las respuestas de Evaluar/Demostrar se descartan si las entradas cambiaron mientras llegaban (`evalInputs`, `proofInputs`).

- Integración de `origin/main` (PR #3, juego «Practicar»): ruta `#/practicar` (el enlace anterior `#practicar` sigue valiendo),
  entrada en la barra lateral bajo Razonamiento; `practice.js` arranca también al abrir la ruta directamente.

- F5 (Cuadernos): paneles Fuentes / Preguntas y respuestas / Evidencia (3 columnas ≥1280 px; en 901–1279 px la evidencia
  va bajo las preguntas; en móvil, tres vistas con «Ver evidencia»). La respuesta resumida queda en Preguntas; premisas
  con cita, derivación Fitch, contramodelos y «Ver paso a paso» van a Evidencia. Una cita abre la fuente y la oración
  exacta, con «Volver a la evidencia». Una pregunta nueva o un cambio de fuentes limpia la evidencia anterior y descarta
  respuestas en vuelo (`nbAskRev`). La barra lateral se contrae sola en 901–1100 px si no hay preferencia guardada.

- Evaluar como asistente de 3 pasos (a petición del usuario): 1 Construye el modelo (enfocado, con selector de casos),
  2 Escribe la fórmula (modelo y lenguaje resumidos en una línea, teclado lógico, escritura en español visible con
  frases de ejemplo y selector de casos), 3 Resultado (solo veredicto y fórmula; «Ver por qué» plegado; botones
  «Buscar dónde sea falsa» y «Explicación guiada»). 18 casos de ejemplo en `features/evaluator/examples.js`, todos
  comprobados contra el motor real. Una lectura en español solo añade al lenguaje los símbolos que falten (con «Deshacer»).

## Archivos

Nuevos: `web/app/navigation.js`, `web/features/home/home.js`, `web/styles/shell.css`,
`tests/frontend/app/navigation.test.mjs`. Modificados: `index.html`, `app.js` (ahora `type="module"`),
`style.css` (retirada la barra superior y las pestañas de modo), `server.py` (3 rutas estáticas nuevas),
`tests/test_project_integration.py` (el título cambió).

## Verificación

- `PYTHONPATH=src:tests python3 -m unittest discover -s tests`, `node --test tests/frontend/app/navigation.test.mjs`.
- Playwright (Chromium) a 1440 y 390 px: navegación, Atrás/Adelante, borrador conservado, hash
  desconocido, recarga, ejercicio 1 con aviso y Deshacer, sin errores de consola ni desborde horizontal.

## Pendiente (propietario Claude)

F2/F4: errores con acción hacia la entrada, aviso de reemplazo en más cargas, vista móvil Modelo / Fórmula y resultado, hosts del reproductor bajo el resultado; F5 Cuadernos
(tres paneles), F6 Diccionario, ayuda/recorrido de primer acceso, 1024/768/360 px y teclado,
integración del reproductor de Codex (sección 7 del protocolo). El reproductor legado sigue operativo.

## Recorrido de primer acceso

Rama `rediseno/recorrido`. Diálogo de 3 pasos (barra lateral, Razonamiento/Conocimiento, ejecutar un ejemplo desde Inicio),
opcional y sin velo: es una tarjeta flotante (`role="dialog"`, `aria-modal="false"`) que resalta el elemento con un contorno
y deja usable la aplicación con el ratón. Mientras está abierto atrapa el foco (Tab / Shift+Tab); Escape u «Omitir» lo
cierra y devuelve el foco a quien lo abrió. Se ofrece solo en la primera visita y solo en Inicio. La clave `localStorage`
`batz-recorrido` guarda `completado` u `omitido` (sin almacenamiento, se recuerda solo en la sesión). Se reabre con
«Ver el recorrido» en el panel de Ayuda (lleva a Inicio; reabrirlo no degrada un `completado`). En ≤900 px el paso 1 abre el
menú lateral y lo cierra al salir; navegar a otra sección cierra el recorrido.

Archivos: `web/features/tour/tour.js`, `web/styles/tour.css`, `tests/frontend/app/tour.test.mjs`; conexión mínima en
`app.js` (import, instancia, botón y `maybeOffer()` tras el `setMode` inicial), `index.html` (css y botón en la ayuda)
y `server.py` (2 rutas estáticas). Verificación: unittest, `node --test`, `--check` de `app.js` y Playwright a 1440/768/390 px.

## F7 accesibilidad

Rama `rediseno/a11y`. Auditoría con axe-core 4.x (copia local, sin red) en 1440 y 390 px sobre Inicio, Evaluar, Demostrar,
Practicar y Cuadernos (estados vacíos y con resultado), más sondas propias con Playwright: IDs duplicados, un solo `main` y un
solo `h1`, foco tras cambiar de ruta (siempre al `h1`), recorrido con Tab por cada ruta (sin elementos invisibles ni sin
indicador de foco), menú móvil, subpestañas, árboles y objetivos táctiles. Contrastes medidos con la fórmula WCAG (script propio).

Corregido:
- Practicar: `--pr-muted` y otros grises fijos pasan a `var(--text-muted)` (4.36, 3.94 y 3.28:1 pasan a 5.5-6.5:1); las tarjetas
  de ejercicio ya no usan un `aria-label` que contradecía el texto visible; la barra de progreso tiene `role="img"`; la flecha es decorativa.
- Menú móvil: con el menú abierto, Tab y Mayús+Tab recorren solo los enlaces (antes el foco escapaba al contenido de detrás).
- Subpestañas (Cuadernos, Diccionario, Evaluar; función genérica del shell): se añaden Inicio y Fin a las flechas.
- Móvil: enlaces del menú y «Saltar al contenido» de 44 px.
- Avisos en vivo: `#proof-check` ya no anuncia en cada pulsación (se enlaza con `aria-describedby` desde sus campos);
  `#nb-evidence` ya no duplica el anuncio de `#nb-answer`.
- Campos: el borde usa `--neutral-500` (3.05:1) en lugar de `--emph-1-border` (1.71:1, incumplía 1.4.11). tokens.css no cambia.

Comprobado sin hallazgos: IDs únicos, landmark único, foco al `h1` en las 6 rutas, árboles (Enter/Espacio, `aria-expanded`,
nombre con verdadero/falso), V/F con letra además de color, `prefers-reduced-motion` (sin animaciones en curso en Demostrar).

No corregido: ver el informe de la entrega (Evaluar queda a cargo del asistente de 3 pasos; reproductor, Diccionario y recorrido no se editaron).
No se revisó con lector de pantalla real ni en teléfono real; solo emulación de Chromium.

## F6 Diccionario

Rama `rediseno/diccionario` (worktree `../proyecto1-dict`). Sin framework; estilos en `web/styles/dictionary.css`, lógica en la sección «diccionario» de `app.js`.

- Búsqueda y filtros arriba (categoría y origen: léxico base / tuyas / automáticas, vía el parámetro `source` ya existente de `/api/lexicon/search`); resultados como lista de botones; detalles de la entrada (categoría, símbolo, formas, significado, origen) en un panel contextual.
- ≥1024 px: resultados y panel lado a lado. <1024 px: el panel reemplaza a los resultados (`data-view`); «Volver a los resultados» (o Escape) restaura la búsqueda, la posición de scroll y el foco en la fila abierta.
- «Añadir palabra» abre el formulario en el mismo panel; propuesta, lema, categoría, irregularidades, sinónimo/sentido y vista previa se conservan al cerrarlo, reabrirlo o cambiar de sección. «Descartar lo escrito» lo vacía.
- Desde una palabra desconocida de Evaluar o Cuadernos (`openDictionaryWith`) se precarga la palabra y aparece un aviso con «Volver a <origen>»; el origen conserva su estado porque las secciones solo se ocultan. Si había un borrador distinto, se avisa y se puede «Deshacer».
- Solo las entradas `usuario` tienen «Quitar» (con confirmación); base y automáticas se rotulan con texto, no solo con color. API `/api/lexicon/*` sin cambios.
- Cambios mínimos fuera de la sección: se retiró `mode-dictionary` del bucle de sub-pestañas, `setMode` ya no reinicia la lista al volver al diccionario, y `server.py` sirve `/styles/dictionary.css`.
- Verificación: `unittest` (315 pruebas OK), `node --check`, Playwright a 1440/1024/768/390/360 px (buscar, filtrar, detalle, añadir, quitar, llegada desde Evaluar y Cuadernos y regreso, sin desborde ni errores de consola).


## Encuadre de la escena 3D

`story3d.js` (archivo de Codex, editado en la integración): la cámara encuadraba solo por el ancho del dominio y cortaba el avatar y su brazo en contenedores casi cuadrados. Ahora centra y encuadra desde el borde izquierdo del avatar (con margen para el gesto) hasta el borde derecho del dominio. Comprobado con capturas a 1440, 1920 y 390 px (paso 10 de un contramodelo de 2 elementos).

## F7 responsive y fallos

Rama `rediseno/responsive` (worktree `../proyecto1-resp`). Por indicación de coordinación, Evaluar (estructura, vista móvil
Modelo / Fórmula, «Ir a la entrada» en Evaluar) queda fuera: lo rehace otro frente.

Corregido: Demostrar rotula el resultado como «Prueba verificada», «Contramodelo verificado» o «Búsqueda inconclusa»
(esta última añade que inconcluso no significa falso); los errores de sintaxis de premisas/conclusión llevan «Ir a la
entrada», que enfoca la premisa o la conclusión y selecciona el tramo señalado. CSS nuevo en `web/styles/responsive.css`
(registrado en `server.py` y enlazado en `index.html`).

Comprobado con Playwright (Chromium headless, emulación; sin teléfono real) en 1440, 1024, 768, 390, 360 y 844x390: sin
desborde horizontal de la página ni elementos fuera del viewport en Inicio, Practicar, Evaluar (resultado verdadero/falso,
árbol, lote), Demostrar (prueba, contramodelo, inconclusa), Cuadernos (fuentes, preguntas, evidencia), y con el
reproductor abierto y en pantalla completa. Fallos simulados (WebGL nulo, GLB abortado, sin voces / sin `speechSynthesis`,
movimiento reducido): el texto, los pasos y los controles siguen operativos; WebGL y GLB fallidos muestran el aviso y la
vista 2D. Cero solicitudes a hosts externos. No probado: voz española real, teléfono físico, Evaluar en el modelo grande
en móvil (fuera de alcance).

## Marca Batz («hilo») y motivos de cuerda

Nombre visible cambiado de LOGOS a Batz (títulos, barra lateral, ayudas, taller de Practicar); el paquete Python, las rutas de la API y las claves `localStorage` conservan `logos` para no romper datos. `styles/thread.css`: marca provisional (hilo con nudo, sustituible por el logotipo que envíe el usuario), cuerda trenzada como filo del encabezado y de los separadores, hilo vertical con nudo en la barra lateral, pasos de Evaluar enhebrados y título con hilo corto. Añadidos: guía de símbolos y «Modo presentación» (letra grande, sin barra lateral) en el panel de Ayuda; el texto de Cuadernos explica que son apuntes interrogables.

## Banner de Inicio

Rama `rediseno/banner`. Banner ancho en Inicio (`features/home/home.js`, `renderBanner`; estilos en `styles/home.css`, registrado en `server.py` y enlazado con una línea en `index.html`) con Kurt Gödel (completitud 1929, incompletitud 1931), Alan Turing (máquina de Turing y problema de la parada, 1936; indecidibilidad de la validez en primer orden junto con Church) y el objetivo de practicar, con enlace `<a href="#/practicar">`. Cada bloque conecta con la página: Evaluar = semántica, Demostrar = sintaxis, completitud como puente; «inconclusa» no es «falso».

Retratos locales en `web/img/` (`godel.jpg`, `turing.jpg`, ambos de dominio público en Commons), servidos desde la lista explícita de `do_GET`. Autor, licencia y origen en `web/img/CREDITOS.md` y como pie de foto enlazado. Duotono solo con CSS (`mix-blend-mode`), un hilo SVG une los retratos; con `prefers-reduced-motion` el hilo no se anima. Si una imagen falta o falla, queda una tarjeta con iniciales. Para cambiar un retrato, sustituir el archivo y su fila en CREDITOS.md.

## Conexión Gödel–Turing, exportar resultados

Inicio: «Practica lo que probaron Gödel y Turing» (3 tarjetas que cargan en Demostrar un caso demostrable, uno con contramodelo y uno inconcluso; comprobados contra el motor: Prueba verificada / Contramodelo verificado / Búsqueda inconclusa). Exportar: `features/export/export.js` genera una página HTML autónoma (sin recursos externos, con estilos incrustados) de un resultado de Evaluar (fórmula, entorno, veredicto, modelo, razones) o de Demostrar (premisas, conclusión, prueba Fitch, contramodelo o búsqueda inconclusa); botones «Descargar resultado» (HTML) e «Imprimir o guardar PDF» (marco oculto + diálogo de impresión del navegador). Un resultado obsoleto no se exporta. No incluye Cuadernos todavía. La impresión solo se comprobó hasta crear el marco; el diálogo del navegador no se automatizó.

## Aprender

Rama `rediseno/aprender`. Sección nueva `#/aprender` (id de modo `learn`, enlace `tab-learn` en «Conocimiento», bajo Cuadernos y Diccionario). Registrada en `app/navigation.js` (con prueba), `MODES` y `SECTION_HELP` de `app.js`, `<section id="mode-learn">` en `index.html` y la lista controlada de `do_GET` (`/styles/learn.css`, `/features/learn/{learn,data,deck}.js`). Ediciones en `app.js`: solo el import, `MODES`, la ayuda, ocultar «Ejemplo» en esta sección y `initLearn(...)` al arrancar.

- `features/learn/data.js`: solo datos. 18 hitos históricos (año, personas, aporte, «dónde lo ves en Batz» con enlace interno) y 33 tarjetas en 5 temas (lenguaje, semántica, sintaxis y pruebas, metateoría, errores comunes).
- `features/learn/deck.js`: lógica pura (barajar, filtrar, cola de estudio, progreso, almacenamiento tolerante a fallos). Probada en `tests/frontend/app/learn.test.mjs`.
- `features/learn/learn.js` y `styles/learn.css`: interfaz. La historia es una `<ol>` con `<details>` por hito sobre un hilo vertical con nudos; filtros por tema y «Abrir/Cerrar todos». Las tarjetas se voltean con clic, Enter o Espacio (botón con `aria-pressed`), flechas izquierda/derecha para pasar, filtros por tema, modo Estudiar (baraja, «La sabía» / «Repasar», ronda con cierre, opción de omitir las sabidas), progreso en `localStorage['batz-tarjetas']` y reinicio con confirmación. Con `prefers-reduced-motion` no hay giro 3D: la cara cambia al instante. Hay una alternativa en texto (`<details>` con todas las tarjetas).
- Criterio de rigor: solo fechas y atribuciones comprobables. Se omitió, por no poder verificarlas aquí, la autoría de los símbolos ∀ y ∃, la fecha exacta de «Löwenheim–Skolem» fuera de 1915/1920 y cualquier cita textual de Leibniz o Hilbert.

## Logotipo Bat’z

El usuario envió el logotipo (una V de hilo crema tejida con tres hilos y un gancho a la derecha, y el nombre con apóstrofo): el nombre visible pasa a **Bat’z** y la marca se redibujó en vectores con los colores de Batz (verde de marca `#006f50`/`#003726`, V en `#e8fcf3`, hilos en ámbar `signal-300`). Archivos: `favicon.svg` (icono de aplicación), `img/batz-icono.svg`, `img/batz-marca-claro.svg` y `img/batz-marca-oscuro.svg`; en la barra lateral la marca es un SVG en línea (`.brand-mark`, hilos que se dibujan al cargar salvo con movimiento reducido). Es una reconstrucción a partir de las capturas enviadas, no el archivo original: si hay un SVG de origen, conviene sustituirla.

## Micro-interacciones globales

`styles/motion.css` (todo bajo `prefers-reduced-motion: no-preference`; solo transform/opacity): entrada de sección, pasos de Evaluar que entran de lado con el hilo entre pasos que se llena, nudo de la barra lateral que «aterriza», hilo del veredicto que se dibuja, presión y brillo en botones, borde de campos teñido de hilo al enfocar, resultados con ascenso. Comprobado: con reducedMotion emulado no hay animaciones propias en curso; el flujo de Evaluar y las exportaciones siguen funcionando.

## Landing minimalista

Rama `rediseno/landing`. Inicio (`#/inicio`) rehecho con menos cajas: titular grande en Literata («El *hilo* que une la matemática en comprobaciones», «hilo» con subrayado que se dibuja), una frase de propuesta, un botón principal «Empezar» (abre Evaluar con el primer ejercicio) y uno secundario («Ver las herramientas», desplaza y enfoca la sección). Después, en una columna acompañada por un hilo trenzado de tres hebras (verde, ciruela, azul; nudos ámbar en cada sección): Cuatro herramientas (lista con filetes y el ejemplo en mono), tres ejercicios como pasos numerados, banner editorial de Gödel y Turing (retratos grandes, duotono que pasa a color suave al pasar el puntero o enfocar, sin editar las fotos) y las tres tarjetas «Practica lo que probaron Gödel y Turing» como lista. El contenido factual y los `runExercise` no cambian.

Archivos: `features/home/home.js` (estructura), `features/home/motion.js` (nuevo: aparición escalonada con IntersectionObserver una sola vez, hilo que se dibuja con el scroll mediante `clip-path`, contadores, foco de luz del puntero; todo se libera en `teardown`), `styles/home.css` y retirada de las reglas `.home*` de `shell.css`. `motion.js` está en la lista de `do_GET`. El titular vive en `index.html`; `renderHome` reescribe su contenido sin tocar el HTML.

Cifras de «33 tarjetas · 18 hitos · 50 ejercicios»: las dos primeras salen de `features/learn/data.js` (`CARDS`, `HISTORY`) y no pueden desfasarse; los 50 ejercicios son la constante `PRACTICE_COUNT` de `home.js`, igual a `len(practice_bank.EXERCISES)`: actualizarla si cambia el banco. Los contadores suben una vez; el texto ya trae la cifra final.

Movimiento: solo `transform`, `opacity` y `clip-path`. Con `prefers-reduced-motion: reduce` no se añade ningún estado oculto, no hay observadores ni animaciones ni transformaciones, y los cambios de hover y foco son instantáneos. El foco de luz solo existe con puntero fino; con teclado la tarjeta se resalta con borde y foco visible.

## Retratos

Rama `rediseno/imagenes`. Retratos locales de 19 de las 22 personas de la historia de la lógica en `src/batz/web/img/people/<slug>.jpg` (escala de grises, hasta 480 px, menos de 150 kB), con licencia verificada en Commons (dominio público, CC BY-SA 2.0 DE/3.0/4.0). Sin imagen verificable libre, y por tanto con iniciales: Church, Jaśkowski y Fitch. `godel.jpg` y `turing.jpg` siguen también en `img/` porque el banner actual las usa.

Fuente única de datos: `features/people/people.js` (`PEOPLE`, `PEOPLE_ORDER`, `person(slug)`, más `initials` y `lifespan`). Cada entrada trae nombre, años, `image` (ruta o `null`), `credit`, `creditUrl` y `license`. Quien use un retrato con licencia CC BY-SA (Löwenheim, Tarski, Gentzen, Robinson) debe mostrar el `credit` de forma visible; el resto, de dominio público, lo muestra igualmente como cortesía. Tabla completa con autor, licencia, URL y fecha en `img/CREDITOS.md`.

`do_GET` registra cada imagen existente y `people.js` en su lista controlada; no hay servicio de archivos por ruta (`/img/people/../../server.py` devuelve 404). Si se añade un retrato: archivo + fila en `CREDITOS.md` + entrada en `people.js` + línea en `do_GET`. Prueba: `node --test tests/frontend/app/people.test.mjs`.

## Línea del tiempo de Aprender

Rama `rediseno/linea-tiempo`. La historia de la lógica deja de ser una lista de 18 `<details>` y pasa a una línea del tiempo:
pista horizontal con hilo y un nudo por hito (etiqueta de año corta), el hito elegido en una tarjeta grande y, a los lados,
el hito de antes y el de después como tarjetas pequeñas (en ≤767 px, pestañas laterales de 44 px con la fecha en vertical).

- Elegir: clic en un nudo, arrastre del ratón sobre el hilo, flechas, Inicio/Fin y RePág/AvPág (nudos con `tabindex` móvil y
  `aria-current="step"`), botones Anterior/Siguiente (deshabilitados en los extremos), tocar las tarjetas vecinas y deslizar con
  el dedo sobre la tarjeta. Los filtros por tema se conservan y limitan los hitos que se recorren (se mantiene el actual si sigue visible).
- Anuncio `role="status"` educado («Hito N de M: año, título»). El deslizamiento usa solo `transform`/`opacity`; con
  `prefers-reduced-motion` no hay animación propia.
- Tarjeta: año, tema, título, personas (de `features/people/people.js` vía `slugs` en `data.js`) con retrato redondeado,
  nombre y años de vida; sin foto (Church, Jaśkowski, Fitch) hay monograma; los créditos CC BY / CC BY-SA (Löwenheim, Tarski,
  Gentzen, Robinson) se ven como enlace a la fuente junto al retrato; el resto lleva el crédito en el `title`. Aportación y
  «Dónde lo ves en Bat’z» no cambian.
- Cierre: en el último hito aparece «Has recorrido la historia — ahora repásala»; el botón pone las tarjetas en «Estudiar»
  (tema «Todas», barajadas), hace scroll al bloque y enfoca «Voltear tarjeta». Las tarjetas de teoría no se tocaron salvo la función `startStudy`.
- Corrección de datos: el orden de la lista ahora es cronológico por año de inicio (Tarski 1933 y Gentzen 1934 iban después de Church y Turing 1936).
- Archivos: `features/learn/timeline.js` (lógica pura, nuevo), `learn.js`, `data.js` (`slugs`), `styles/learn.css`,
  `server.py` (ruta de `timeline.js`), `tests/frontend/app/learn.test.mjs`.

## Carrusel y páginas de personas

Rama `rediseno/personas`. El banner de Inicio es ahora un carrusel de tres diapositivas (Gödel, Turing, Church) en
`features/home/carousel.js`: `role="region"` con `aria-roledescription="carrusel"`, diapositivas `role="group"`
«1 de 3», botones anterior/siguiente, puntos con `aria-current`, flechas/Inicio/Fin, deslizar táctil (solo toque y lápiz)
y anuncio `aria-live="polite"` únicamente al navegar. Sin autoavance. Las inactivas llevan `inert`; el movimiento es
solo `opacity`/`transform` y se apaga con `prefers-reduced-motion`. La lógica pura (`stepIndex`, `swipeDelta`, `keyIndex`) está probada.
Church no tiene retrato libre: tarjeta tipográfica con monograma «AC» y la nota «Retrato no disponible con licencia libre».
Rutas `#/godel`, `#/turing`, `#/church` (`nav: false` en `navigation.js`, fuera de la barra lateral; `personFor`).
Datos en `features/people/bios.js`, vista en `person.js` (reutiliza el `runExercise` y `CONNECTIONS` de Inicio), estilos en `styles/people.css`.
En `app.js` solo la conexión: sección `#mode-person`, título, foco al h1 y ayuda. Todo dato incierto se omitió (p. ej. lugar de la muerte de Church).

## Voces en Linux y selector de voz; foto de Church

Causa de que no se oyera: el reproductor usa `speechSynthesis` del navegador y solo acepta voces españolas **locales**. En Windows/macOS el navegador las trae del sistema; en Linux solo las ve si hay `speech-dispatcher` con un sintetizador, y suele no haber ninguna. Solución: (1) `src/batz/voice_output.py` genera el audio en el propio equipo con `espeak-ng` si está instalado (WAV por `POST /api/voice/speak`; voces por `POST /api/voice/voices`; texto ≤600 caracteres, id de voz validado contra la lista instalada, sin shell, caché de 64 entradas, el texto no sale de la máquina); (2) el reproductor tiene un selector «Voz» (Automática, voces del navegador, voces del equipo), un botón «Probar voz» y guarda la elección en `localStorage['batz-voz']`; con voz del equipo la boca del avatar se reparte en la duración real del audio; (3) sin ninguna voz, el reproductor explica cómo instalar `espeak-ng` y sigue funcionando sin audio. Probado con un `espeak-ng` simulado (9 pruebas Python y 4 de Node) y en Chromium con y sin voces; **no probado con un espeak-ng real ni oyendo el audio**, porque la máquina de desarrollo no lo tiene instalado.
Foto de Alonzo Church: aportada por el usuario; procedencia y licencia **sin verificar** (ver `img/CREDITOS.md`); el pie de foto lo dice.

## Corrección: llave sin cerrar en `thread.css`

Al reordenar el hilo de los pasos de Evaluar (commit «el hilo solo cruza los huecos»), una sustitución con expresión regular borró el cierre de un `@media (max-width: 720px)`. Todo lo que seguía en `thread.css` (marca `Bat’z`, modo presentación, guía de símbolos) quedó dentro de ese `@media` y solo se aplicaba en móvil: en escritorio el nombre se partía en tres líneas y el modo presentación no ocultaba la barra lateral ni fijaba su botón. Corregido, con `tests/frontend/app/css.test.mjs` (llaves balanceadas en todas las hojas). Además: las letras del veredicto se agrupan por palabra (una palabra nunca se parte; antes «verific/ada»), el modo presentación se cierra con Escape, y el servidor envía `Cache-Control: no-cache` en los archivos estáticos para que el navegador no conserve hojas viejas.

## Diagnóstico de voces

Con `espeak-ng` real (1.52.0) la ruta completa funciona en Chromium: `/api/voice/voices` lista 4 voces, «Probar voz» reproduce 2 s de audio y la narración pide el audio al servidor. Cuando a un usuario «no le detecta la voz», las causas son del entorno: servidor en ejecución anterior a la función (404 en `/api/voice/voices`), servidor lanzado donde `espeak-ng` no está en el `PATH`, o instalación posterior a la carga de la página. El panel de voz ahora dice cuál es la causa real (servidor antiguo, sin servidor, sin motor) y tiene «Volver a buscar voces» sin recargar la página.

## Voz dentro de Docker

El `Dockerfile` instala `espeak-ng` (paquete de Debian, sin recomendados) antes de crear el usuario sin privilegios; la imagen pasa de «solo librería estándar» a «librería estándar + espeak-ng». Probado construyendo la imagen real (250 MB) y arrancándola: dentro del contenedor, como usuario `logos`, `/api/voice/voices` responde `available: true` y `/api/voice/speak` devuelve un WAV de 22,05 kHz. Debian lista varias filas por idioma, así que `parse_voices` deduplica por id (con prueba). Se sigue sin transcripción por voz (whisper) en la imagen.
