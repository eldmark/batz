# Entrega Codex: reproductor de explicaciones y escena 3D

Fecha: 2026-11-16.

- Base común: `ea78374` (documentación del rediseño).
- Rama: `rediseno/codex-reproductor`.
- Worktree usado: `/tmp/logos-codex-reproductor`.
- Commit de implementación: `40336ec`.
- Estado: listo para integrar. La integración con las pantallas pertenece a Claude.
- Fase cubierta: F3 en componente aislado, con los requisitos de F0 aplicables.
  F3 en la aplicación completa y F7 requieren la integración.

## Qué se implementó

`createExplanationPlayer` monta un componente independiente con texto, fórmula,
asignaciones, contexto, valor del paso, representación 2D y escena 3D diferida.
Consume los eventos existentes sin implementar lógica formal ni generar pasos.

Incluye reproducción, pausa, anterior/siguiente, repetición del paso actual,
reinicio, lista de pasos, velocidades 0.75/1/1.25/1.5, voz local española opcional,
sincronización labial, minimización, cierre, invalidación y pantalla completa nativa
o de respaldo. Coordina sus instancias para que solo una reproduzca a la vez.

El ID del resultado impide reiniciar al recargar el mismo objeto lógico. Un ID
nuevo comienza cerrado en índice cero. Minimizar/cerrar conserva el índice;
invalidar pausa y deshabilita el recorrido hasta recibir un ID nuevo. Los callbacks
de voz y cargas pendientes anteriores no pueden avanzar o reconstruir otro resultado.

La escena conserva avatar, GLB, Blender, animaciones y formas de boca. Se añadió
limpieza de texturas, geometrías y esqueletos, descarte de GLB recibido después
de destruir, manejo de pérdida de contexto y pausa del bucle. Las etiquetas del
dominio usan el color de texto existente para mejorar contraste sobre el fondo claro.

## Archivos y recursos de producción

| Ruta web que debe servir Python | Archivo | MIME |
|---|---|---|
| `/features/explanation-player/index.js` | `src/logos/web/features/explanation-player/index.js` | `text/javascript; charset=utf-8` |
| `/features/explanation-player/events.js` | `src/logos/web/features/explanation-player/events.js` | `text/javascript; charset=utf-8` |
| `/features/explanation-player/fullscreen.js` | `src/logos/web/features/explanation-player/fullscreen.js` | `text/javascript; charset=utf-8` |
| `/features/explanation-player/player.css` | `src/logos/web/features/explanation-player/player.css` | `text/css; charset=utf-8` |

Se modificó también `src/logos/web/story3d.js`, conservando su URL. Mantener las
rutas existentes de GLB, vendor y fuentes. No servir `tests/frontend/player/`
desde producción. El componente no necesita npm, CDN, framework ni compilación.

No se editaron `app.js`, `index.html`, `style.css`, `server.py`, tokens, motores
Python ni los archivos binarios del avatar.

## API y conexión para Claude

Implementa los métodos del contrato `docs/specs/EXPLANATION_PLAYER.md`:
`load`, `open`, `pause`, `minimize`, `close`, `invalidate`, `clear`, `getSnapshot`
y `destroy`, y los callbacks `onStepChange` y `onStateChange`.

Además se entrega un método aditivo `exitFullscreen()`. Permite que el shell
salga de pantalla completa (incluido el respaldo) al navegar, sin inspeccionar
clases del componente ni cerrar su presentación. No cambia las firmas del contrato.

```js
import {createExplanationPlayer} from '/features/explanation-player/index.js';

const player = createExplanationPlayer({
  host,
  onStepChange: ({resultId, event, index, total}) => {
    // Comprobar revisión/ID; resaltar solo dentro del resultado propietario.
    // event.line identifica Fitch; trace_path/span identifican la comprobación.
  },
  onStateChange: state => {
    // Actualizar acciones externas si corresponde. getSnapshot no emite callbacks.
  },
});

player.load({
  resultId: `evaluate:${revision}`,
  origin: 'evaluate',
  kind: 'evaluation',
  title: 'Evaluación semántica',
  story: response.story,
  model: response.model,
});
// Abrir solo a petición del usuario:
openExplanationButton.onclick = () => player.open();

// Al navegar:
player.pause();
player.exitFullscreen();

// Al cambiar entradas relevantes:
player.invalidate('El modelo cambió. Vuelve a evaluar.');
```

Cargar `player.css` una vez. El host debe tener `min-width: 0` y puede moverse
a la fila de ancho completo sin recrear la instancia. El componente no desplaza
la página al cargar/abrir: el shell decide el desplazamiento al abrirlo.

Para pruebas, pasar `origin: 'prove'`, `kind: 'proof'`, el guion de prueba y
`model: null`. Para contramodelos, `kind: 'countermodel'` con su modelo y relato
completo. Cuadernos usa `origin: 'notebook'`; el módulo conserva el mapa entre
Fitch, premisas y fuentes. El reproductor no infiere citas a partir del texto.

Los IDs deben ser únicos entre resultados y revisiones. Usar un ID nuevo al
reejecutar con datos nuevos: `load` con el mismo ID conserva el estado y no cambia
el guion por debajo. No mutar los eventos recibidos en los callbacks.

Una historia vacía queda `empty`; `open()` no muestra una comprobación inventada.
Se rechaza explícitamente una `schema_version` declarada distinta de `"1"`.

Retirar la implementación antigua de narración, timers, DOM y fullscreen solo
al conectar estos puntos en todas las pantallas. Así se evita tener dos sistemas
de audio o botones apuntando al último resultado global.

## Demo y validación

Receta reproducible y variables de entorno en
[`tests/frontend/player/README.md`](../../../tests/frontend/player/README.md).
Desde la raíz del worktree:

```bash
PYTHONPATH=src python3 tests/frontend/player/generate_fixtures.py
python3 tests/frontend/player/serve.py --port 8877
```

Demo en `http://127.0.0.1:8877`. El servidor es solo para pruebas aisladas.
Los fixtures se generaron con los motores reales. El caso de origen Cuadernos
reutiliza un certificado de prueba, sin fingir una respuesta completa de su API.

Resultados obtenidos:

- `PYTHONPATH=src:tests python3 -m unittest discover -s tests`: 297 pruebas,
  correctas, dos omisiones de entorno (HTTP por sandbox y nombres cortos 8.3
  exclusivos de Windows).
- `PYTHONPATH=src:tests python3 -m unittest test_project_integration.LocalHTTP`:
  cuatro pruebas correctas al ejecutarse con acceso a puertos locales.
- Sintaxis de los cuatro módulos JavaScript, incluido `story3d.js`, correcta.
- `git diff --check`: correcto.
- 15 recorridos de navegador correctos con Playwright 1.65.1 y Chromium local:
  14 en una ejecución completa y el último añadido de fin de guion/visibilidad
  en una ejecución filtrada. Sin excepciones de página ni red externa.
- Avatar real cargado con WebGL por software, formas `Boca_abierta`,
  `Boca_redonda`, `Parpadeo`, apertura/cierre y movimiento reducido comprobados.
- Probados 1440, 1024, 768, 390 y 360 px, además de 844×390; sin desborde de
  página, manteniendo el paso al mover/redimensionar el host.
- Probados fallos de WebGL y GLB, import y GLB pendientes al destruir, voz
  inexistente, audio obsoleto, dos instancias, revisión invalidada, fin de guion,
  visibilidad, foco/scroll y fullscreen nativo y de respaldo.

Comando del navegador en este equipo (con el servidor de demo activo):

```bash
NODE_PATH=/tmp/logos-player-browser/node_modules LOGOS_BROWSER=/home/dmark123/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome node tests/frontend/player/check.cjs
```

Capturas revisadas en `/tmp/logos-player-verification/escritorio-3d.png` y
`/tmp/logos-player-verification/movil-3d.png`. Son artefactos locales, no requisitos
para ejecutar ni archivos que deba servir la aplicación.

## Límites y trabajo pendiente

- Las pruebas de síntesis usan una voz simulada; no hay ensayo audible con una
  voz española del sistema. No se verificó calidad de pronunciación real.
- Los tamaños móviles están emulados en Chromium; no se ensayó un teléfono real.
- La selección desde la escena y desde 2D consume casos del guion; el resaltado
  externo real de Fitch/árbol y la apertura de citas son responsabilidad de Claude.
- Pendientes de Claude: registrar recursos, montar hosts y CSS, adaptar resultados,
  pausar/salir de fullscreen al navegar, invalidar por edición, retirar el legado
  y validar todos los módulos juntos. No se ha fusionado esta rama a `main`.
