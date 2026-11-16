# Avatar realista: cómo se construye

El avatar de la vista 3D (`src/logos/web/avatar/logos.glb`) se arma en Blender 5.2 sin interfaz y sin servicios externos. Todo corre en la máquina local. La foto de referencia no está en el repositorio; solo su proyección aparece, ya horneada, dentro del GLB.

## Entradas

| Archivo | De dónde sale |
|---|---|
| `human_base_meshes_bundle.blend` | [Human Base Meshes](https://download.blender.org/demo/asset-bundles/human-base-meshes/) de Blender Studio, v1.4.1, CC0. Se usa el cuerpo masculino realista con sus ojos. |
| `face_landmarker.task` | Modelo Face Landmarker de MediaPipe (Apache 2.0). |
| `foto.png` | Foto de frente de la persona, con la boca cerrada, luz pareja y fondo liso. |
| `side_px.png`, `side_nx.png` | Perfiles: la cámara del lado +x (la cara mira a la izquierda de la imagen) y del lado −x (la cara mira a la derecha), con el mismo fondo y la misma luz. |
| `rig_src.blend` | `assets/avatar/logos-avatar.blend` del commit 283b739: esqueleto de 17 huesos y siete animaciones. |

## Pasos

Se ejecutan en este orden, todos con el mismo directorio de trabajo `D/`:

```sh
blender -b human_base_meshes_bundle.blend --python prep_base.py -- D/   # base a 1,78 m + render frontal
python lm.py D/base_front.png D/base_lm.json                             # 478 puntos sobre la base
python lm.py D/foto.png D/foto_lm.json                                   # 478 puntos sobre la foto
python mask.py && python seg.py && python profile.py                     # máscara, silueta, colores, perfiles
blender -b D/base.blend --python fit.py -- D/                            # la cabeza toma la forma de la cara
blender -b D/fit.blend --python profile_fit.py -- D/                     # la línea media toma la del perfil
blender -b D/fit.blend --python build_head.py -- D/                      # textura (frente + perfiles), pelo, ojos
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
- **`profile.py`**: saca la silueta de cada perfil (el fondo liso se separa por diferencia de color). Espeja el perfil de −x.
- **`profile_fit.py`**:
  - Escala cada perfil con la distancia entre el entrecejo y el borde inferior del mentón.
  - Corrige la profundidad de la línea media: frente, nariz, labios y mentón, con un tope de 8 mm.
  - Guarda el mapeo (y, z) → píxel de cada perfil.
  - El centro de la oreja en cada foto se anota a mano en `EARS`. La oreja de la malla no se mueve; la textura se deforma alrededor de ella para que calce.
- **`build_head.py`**:
  - Proyecta la foto con una interpolación de placas delgadas que cierra la boca.
  - Arma el pelo como una cáscara sobre el cuero cabelludo. Su borde queda bajo la piel, así que la línea del pelo la dibuja la textura.
  - Proyecta la malla a la foto de frente con la pose real de la cabeza (la rotación que estima `fit.py`). La interpolación solo corrige el residuo fino.
  - El grosor del pelo sale de las siluetas:
    - **Arriba:** la curva del perfil, suavizada.
    - **Lados:** al menos 7 mm.
    - **Atrás:** el perfil, con tope de 12 mm.
    - **Tope general:** 22 mm.
  - La línea del pelo sale de la foto de frente. En costados y nuca sale de los perfiles: es pelo lo que está dentro de la silueta y no es piel ni camisa.
  - Hornea pasadas flotantes con Cycles (incluida una de normales) y compone la textura en numpy:
    - **Cara:** la foto de frente.
    - **Costados:** los perfiles, con el color igualado al de la mejilla de frente; se usan en orejas, patillas, pelo y cuello.
    - **Piel lisa:** el tono se toma de la propia cara.
    - **Ojos:** los de la foto de frente; el iris procedural solo cubre lo que la foto no ve.
    - **Boca:** el interior va oscuro.
    - **Tono:** al final se baja un 22 % la saturación de la piel (más blanca, sin el rojo saturado).
- **`build_body.py`**:
  - Mueve los huesos del esqueleto a las articulaciones medidas en la malla y pesa con calor. La cabeza queda rígida sobre el hueso `head` y es un 5 % más grande respecto al cuerpo.
  - Cerca del cuello, la parte de arriba del hombro la mueve el pecho y no el brazo. El esqueleto no tiene clavícula, y sin esto el escote se rompe al levantar los brazos.
  - Arma la ropa como copias suavizadas de la piel: camiseta azul marino de manga recta hasta medio brazo, pantalón caqui y zapatos. Cada vértice de ropa toma los pesos de la piel que tiene justo debajo.
  - Borra la piel tapada; la que queda bajo los bordes se mete 4 mm.
  - La camiseta cuelga como tela: bajo el pecho cae recta y la cintura casi no se angosta, así no marca busto ni cintura de reloj de arena.
  - Los bordes de la ropa se alisan con Taubin (no encoge el aro, así el escote no se aplana en cuello de bote).
  - El cuello redondo lleva un ribete: una banda más oscura que sube del borde del escote y abraza el cuello.
  - Crea las formas `Boca_abierta` (mandíbula que gira), `Boca_redonda` y `Parpadeo`, y exporta. En `Parpadeo` los párpados giran alrededor del centro del ojo, con el ángulo medido en los bordes de los párpados de la foto.

`shots.py` tiene la cámara y las luces de los renders de control.
