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
