# Bibliotecas incluidas

La vista 3D usa Three.js 0.187.0. Los archivos `three.module.js` y `three.core.js` están en `src/logos/web/vendor/`, junto con la licencia MIT original. Se descargaron del paquete `three@0.187.0` publicado en npm: https://www.npmjs.com/package/three/v/0.187.0. Así la demo puede cargar el 3D desde el servidor local, sin CDN.

Huella SHA-256 del paquete descargado: `ff540832ded0cfe919764d24a3d88f3e2a05f23303f876423e4f893841e90728`.

Para reconstruir esos archivos:

```bash
npm pack three@0.187.0 --pack-destination /tmp
```

Dentro del archivo `.tgz` están `package/build/three.module.js`, `package/build/three.core.js` y `package/LICENSE`. No se usa npm al ejecutar LOGOS.
