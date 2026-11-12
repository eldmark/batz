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

El avatar (`src/logos/web/avatar/logos.glb`, fuente editable en `assets/avatar/logos-avatar.blend`) es un modelo propio del proyecto, construido en Blender a partir de tres vistas de referencia: primitivas fundidas por material con remallado de vóxeles y suavizado. No contiene geometría ni texturas de terceros. Trae un esqueleto de 17 huesos con pesos difuminados en las articulaciones y siete animaciones: `Idle`, `Explica`, `Senala`, `Piensa`, `Verdadero`, `Falso` y `Saluda`.
