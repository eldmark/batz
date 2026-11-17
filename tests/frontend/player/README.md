# Demo y pruebas del reproductor

Este directorio es exclusivo del frente Codex. No modifica el servidor de la
aplicación ni necesita que el shell de Claude esté integrado.

## Ejecutar la demo

Desde la raíz de este worktree:

```bash
PYTHONPATH=src python3 tests/frontend/player/generate_fixtures.py
python3 tests/frontend/player/serve.py --port 8877
```

Abrir `http://127.0.0.1:8877`. El servidor escucha solo en loopback y sirve la
demo y los recursos web; no sirve archivos personales o de otras rutas.
Los fixtures ya están incluidos. El generador los reproduce con evaluación,
prueba y contramodelo de los motores reales. El fixture de origen Cuadernos
reutiliza el certificado de prueba; no simula una respuesta completa de su API.

## Pruebas de navegador

Necesitan Node.js, Playwright y Chromium. Playwright es una dependencia externa
de pruebas; no se añadió al runtime ni se creó un package.json de aplicación.
Si ya existe una instalación accesible a Node, usarla. Ejemplo de instalación
aislada y ejecución, con el servidor anterior activo:

```bash
npm install --prefix /tmp/logos-player-browser playwright --no-audit --no-fund
NODE_PATH=/tmp/logos-player-browser/node_modules node tests/frontend/player/check.cjs
```

Si Chromium no está instalado para esa versión de Playwright, instalarlo con
su CLI o señalar un ejecutable existente mediante `LOGOS_BROWSER`.

Variables opcionales:

| Variable | Uso |
|---|---|
| `LOGOS_PLAYER_URL` | URL de la demo; por defecto `http://127.0.0.1:8877`. |
| `LOGOS_BROWSER` | Ruta absoluta del ejecutable Chromium disponible. |
| `LOGOS_PLAYER_ARTIFACTS` | Directorio de capturas; por defecto `/tmp/logos-player-verification`. |
| `LOGOS_PLAYER_FILTER` | Ejecutar solo recorridos cuyo nombre contenga ese texto. |

La suite usa escenas y voces controladas para probar carreras y cancelaciones,
y escenas reales con el GLB para comprobar carga, formas de boca, movimiento
reducido y liberación de recursos. Simula ausencia de WebGL y fallo de GLB.
Verifica pantalla completa nativa y de respaldo, eventos/callbacks sincronizados,
elemento `0`, fin de guion, pausa por pestaña oculta y tamaños 360–1440 px.
Comprueba que no haya excepciones de página ni solicitudes a servidores externos.

La prueba de voces es simulada: no certifica calidad audible de una voz del
sistema ni reemplaza el ensayo en un teléfono real. Las capturas móviles usan
viewport de Chromium, sin hardware móvil.

## Integrar

Registrar en `Handler.do_GET`, con MIME apropiado, los cuatro archivos:

```text
/features/explanation-player/index.js
/features/explanation-player/events.js
/features/explanation-player/fullscreen.js
/features/explanation-player/player.css
```

Mantener `/story3d.js`, `/avatar/logos.glb`, vendor y fuentes. La aplicación
importa el primer módulo y carga la hoja CSS. El directorio de pruebas no se
registra en el servidor de producción.

La conexión a resultados reales y el retiro del reproductor legado corresponden
a Claude, según `docs/plans/REDISENO_PARALELO.md`.
