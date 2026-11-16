# Avatar realista: cómo se construye

El avatar de la vista 3D (`src/logos/web/avatar/logos.glb`) se arma en Blender 5.2 sin interfaz y sin servicios externos. Todo corre en la máquina local. La foto de referencia no está en el repositorio; solo su proyección aparece, ya horneada, dentro del GLB.

## Entradas

| Archivo | De dónde sale |
|---|---|
| `human_base_meshes_bundle.blend` | [Human Base Meshes](https://download.blender.org/demo/asset-bundles/human-base-meshes/) de Blender Studio, v1.4.1, CC0. Se usa el cuerpo masculino realista con sus ojos. |
| `face_landmarker.task` | Modelo Face Landmarker de MediaPipe (Apache 2.0). |
| `foto.png` | Foto de frente de la persona, con buena luz y sin gorra. |
| `rig_src.blend` | `assets/avatar/logos-avatar.blend` del commit 283b739: esqueleto de 17 huesos y siete animaciones. |

## Pasos

Se ejecutan en este orden, todos con el mismo directorio de trabajo `D/`:

```sh
blender -b human_base_meshes_bundle.blend --python prep_base.py -- D/   # base a 1,78 m + render frontal
python lm.py D/base_front.png D/base_lm.json                             # 478 puntos sobre la base
python lm.py D/foto.png D/foto_lm.json                                   # 478 puntos sobre la foto
python mask.py && python seg.py                                          # máscara de la cara, silueta, colores
blender -b D/base.blend --python fit.py -- D/                            # la cabeza toma la forma de la cara
blender -b D/fit.blend --python build_head.py -- D/                      # textura, pelo y ojos
blender -b rig_src.blend --python build_body.py -- D/ out.blend out.glb  # esqueleto, ropa, boca, GLB
```

`lm.py`, `mask.py` y `seg.py` usan Python con `mediapipe` y `opencv-python`. `mask.py` y `seg.py` leen y escriben en el directorio actual.

## Qué hace cada script

- **`prep_base.py`**: deja solo el cuerpo realista y los ojos, aplica un nivel de multirresolución y escala a 1,78 m. Después renderiza la cabeza de frente en ortográfica para detectar los puntos sobre la propia malla.
- **`fit.py`**:
  - Alinea los puntos de la foto con los de la base (similitud de Umeyama).
  - Deforma la cabeza en dos pasadas: escala por eje más gaussianas de 3 cm, y luego gaussianas de 1,1 cm.
  - Descarta los puntos cuyos rayos caen en fosas o cuencas.
  - Aplana los labios sin tocar el interior de la boca.
  - Angosta las aletas de la nariz.
- **`build_head.py`**:
  - Proyecta la foto con una interpolación de placas delgadas que cierra la boca.
  - Arma el pelo como una cáscara sobre el cuero cabelludo. Su borde queda bajo la piel, así que la línea del pelo la dibuja la textura.
  - Hornea pasadas flotantes con Cycles y compone la textura en numpy: foto aclarada, piel tomada de la propia cara, pelo de la foto cerca de la frente, ojos procedurales con el iris donde está en la foto e interior de la boca oscuro.
- **`build_body.py`**:
  - Mueve los huesos del esqueleto a las articulaciones medidas en la malla y pesa con calor. La cabeza queda rígida sobre el hueso `head`.
  - Arma la ropa como copias suavizadas de la piel, que heredan los pesos: camiseta azul marino de manga corta con dos botones, pantalón caqui y zapatos. Borra la piel tapada.
  - Crea las formas `Boca_abierta` (mandíbula que gira) y `Boca_redonda`, y exporta.

`shots.py` tiene la cámara y las luces de los renders de control.
