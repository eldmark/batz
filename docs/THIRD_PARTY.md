# Bibliotecas incluidas

La vista 3D usa Three.js 0.187.0. Los archivos `three.module.js` y `three.core.js` están en `src/logos/web/vendor/`, junto con la licencia MIT original. Se descargaron del paquete `three@0.187.0` publicado en npm: https://www.npmjs.com/package/three/v/0.187.0. Así la demo puede cargar el 3D desde el servidor local, sin CDN.

Huella SHA-256 del paquete descargado: `ff540832ded0cfe919764d24a3d88f3e2a05f23303f876423e4f893841e90728`.

Para reconstruir esos archivos:

```bash
npm pack three@0.187.0 --pack-destination /tmp
```

Dentro del archivo `.tgz` están `package/build/three.module.js`, `package/build/three.core.js` y `package/LICENSE`. No se usa npm al ejecutar LOGOS.

## Tipografías

La interfaz sirve sus fuentes desde `src/logos/web/fonts/`, sin CDN, para que la demo se vea igual sin internet.

| Archivo | Familia | Uso | Licencia | Origen |
|---|---|---|---|---|
| `literata.woff2` | Literata (variable, subconjunto latino) | titulares y veredicto | SIL OFL 1.1 | npm `@fontsource-variable/literata@5.3.0` |
| `plex-sans.woff2` | IBM Plex Sans (variable, subconjunto latino) | texto de la interfaz | SIL OFL 1.1 | npm `@fontsource-variable/ibm-plex-sans@5.3.0` |
| `jbmono-400.woff2`, `jbmono-600.woff2` | JetBrains Mono NL (sin ligaduras) | fórmulas y tuplas | SIL OFL 1.1 (fuente); MIT (empaquetado) | npm `jetbrains-mono@1.0.6` |

JetBrains Mono NL se eligió para las fórmulas porque el archivo completo contiene `∀ ∃ ∧ ∨ ¬ → ↔ ⊥ ≠ ∈`; los subconjuntos latinos de las otras dos no los traen. Las licencias están junto a los archivos (`LICENSE-*.txt`).

## Cargador de modelos y avatar

`vendor/GLTFLoader.js`, `vendor/BufferGeometryUtils.js` y `vendor/SkeletonUtils.js` vienen del mismo paquete `three@0.187.0` (carpeta `examples/jsm`, licencia MIT). El único cambio es la ruta de sus `import`, que ahora apunta a `./three.module.js` para no depender de un mapa de importación.

El avatar está en `src/logos/web/avatar/logos.glb`, con su fuente editable en `assets/avatar/logos-avatar.blend`.

- **Malla:** el cuerpo y los ojos parten de [Human Base Meshes](https://download.blender.org/demo/asset-bundles/human-base-meshes/) de Blender Studio (v1.4.1, CC0, dominio público), deformados en Blender para que la cabeza tome la forma de una cara real.
- **Textura de la cara:** es una foto proyectada de un integrante del equipo, usada con su permiso.
- **Pelo, ropa y ojos:** son del proyecto.
- **Puntos de la cara:** se detectaron con el modelo Face Landmarker de MediaPipe (Apache 2.0), que se usa solo al construir el avatar y no se distribuye.
- **Esqueleto y animaciones:** son propios: 17 huesos y siete animaciones (`Idle`, `Explica`, `Senala`, `Piensa`, `Verdadero`, `Falso` y `Saluda`).
- **Boca:** tiene dos formas (morph targets): `Boca_abierta`, una mandíbula que gira, y `Boca_redonda`. La narración las mueve con cada palabra.

El proceso completo está en `assets/avatar/realista/README.md`.

## Voz local (opcional, no incluida en el repositorio)

`scripts/instalar_voz.ps1` y `scripts/instalar_voz.sh` descargan, en la carpeta del usuario y nunca en el repositorio:

| Componente | Licencia | Origen |
|---|---|---|
| whisper.cpp 1.9.5 (`whisper-cli` y sus DLL) | MIT | https://github.com/ggml-org/whisper.cpp/releases (SHA-256 fijado en el script) |
| Modelo `ggml-base.bin` (pesos de Whisper convertidos) | MIT | https://huggingface.co/ggerganov/whisper.cpp (tamaño y SHA-256 fijados en el script) |
| ffmpeg (paquete `Gyan.FFmpeg` de winget en Windows) | GPL v3 en esa compilación | lo instala winget por usuario; LOGOS solo lo llama para convertir la grabación |

LOGOS no redistribuye ninguno de los tres: solo los ejecuta si el usuario los instaló.

## Microinteracciones de la interfaz

La píldora que se desliza entre pestañas, los botones con estado de carga y borde de luz, el veredicto letra por letra, los avisos flotantes, los contadores y las casillas con palomita se inspiraron en componentes de la galería comunitaria de 21st.dev (Slide Tabs, Eclipse Button, Shine Border, Text Effect, Blur Fade, Number Ticker, Toast). Esos componentes son de React y varios no declaran licencia, así que no se copió código: cada efecto está escrito desde cero en `web/style.css` y `web/app.js`, sin dependencias.
