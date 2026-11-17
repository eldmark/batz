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

## F6 Diccionario

Rama `rediseno/diccionario` (worktree `../proyecto1-dict`). Sin framework; estilos en `web/styles/dictionary.css`, lógica en la sección «diccionario» de `app.js`.

- Búsqueda y filtros arriba (categoría y origen: léxico base / tuyas / automáticas, vía el parámetro `source` ya existente de `/api/lexicon/search`); resultados como lista de botones; detalles de la entrada (categoría, símbolo, formas, significado, origen) en un panel contextual.
- ≥1024 px: resultados y panel lado a lado. <1024 px: el panel reemplaza a los resultados (`data-view`); «Volver a los resultados» (o Escape) restaura la búsqueda, la posición de scroll y el foco en la fila abierta.
- «Añadir palabra» abre el formulario en el mismo panel; propuesta, lema, categoría, irregularidades, sinónimo/sentido y vista previa se conservan al cerrarlo, reabrirlo o cambiar de sección. «Descartar lo escrito» lo vacía.
- Desde una palabra desconocida de Evaluar o Cuadernos (`openDictionaryWith`) se precarga la palabra y aparece un aviso con «Volver a <origen>»; el origen conserva su estado porque las secciones solo se ocultan. Si había un borrador distinto, se avisa y se puede «Deshacer».
- Solo las entradas `usuario` tienen «Quitar» (con confirmación); base y automáticas se rotulan con texto, no solo con color. API `/api/lexicon/*` sin cambios.
- Cambios mínimos fuera de la sección: se retiró `mode-dictionary` del bucle de sub-pestañas, `setMode` ya no reinicia la lista al volver al diccionario, y `server.py` sirve `/styles/dictionary.css`.
- Verificación: `unittest` (315 pruebas OK), `node --check`, Playwright a 1440/1024/768/390/360 px (buscar, filtrar, detalle, añadir, quitar, llegada desde Evaluar y Cuadernos y regreso, sin desborde ni errores de consola).

