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

## Archivos

Nuevos: `web/app/navigation.js`, `web/features/home/home.js`, `web/styles/shell.css`,
`tests/frontend/app/navigation.test.mjs`. Modificados: `index.html`, `app.js` (ahora `type="module"`),
`style.css` (retirada la barra superior y las pestañas de modo), `server.py` (3 rutas estáticas nuevas),
`tests/test_project_integration.py` (el título cambió).

## Verificación

- `PYTHONPATH=src:tests python3 -m unittest discover -s tests`, `node --test tests/frontend/app/`.
- Playwright (Chromium) a 1440 y 390 px: navegación, Atrás/Adelante, borrador conservado, hash
  desconocido, recarga, ejercicio 1 con aviso y Deshacer, sin errores de consola ni desborde horizontal.

## Pendiente (propietario Claude)

F2 Evaluar (resultado bajo la fórmula, herramientas secundarias plegadas), F4 Demostrar, F5 Cuadernos
(tres paneles), F6 Diccionario, ayuda/recorrido de primer acceso, 1024/768/360 px y teclado,
integración del reproductor de Codex (sección 7 del protocolo). El reproductor legado sigue operativo.
