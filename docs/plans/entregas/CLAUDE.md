# Entrega Claude: aplicación y pantallas

Base común: `ea78374`
Rama: `rediseno/claude-interfaz` (worktree `../proyecto1-claude`)
Estado: en curso

## Completado

- F1 (shell, navegación, Inicio): sidebar de 240 px colapsable (preferencia en `localStorage`
  `logos-sidebar`; se contrae sola entre 901 y 1100 px), menú móvil con botón, fondo, Escape y
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
`logos-recorrido` guarda `completado` u `omitido` (sin almacenamiento, se recuerda solo en la sesión). Se reabre con
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
