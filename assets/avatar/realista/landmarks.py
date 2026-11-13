import json, sys
import cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarksConnections as C

img_path = sys.argv[1]
opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path="face_landmarker.task"),
                                    output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=1)
det = vision.FaceLandmarker.create_from_options(opts)
bgr = cv2.imread(img_path)
h, w = bgr.shape[:2]
res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
lm = res.face_landmarks[0]
pts = [[p.x, p.y, p.z] for p in lm]
tess = [(c.start, c.end) for c in C.FACE_LANDMARKS_TESSELATION]
# triángulos: tríos de aristas consecutivas que cierran un ciclo
tris = []
for i in range(0, len(tess) - 2, 3):
    a, b, c = tess[i:i+3]
    vs = {a[0], a[1], b[0], b[1], c[0], c[1]}
    if len(vs) == 3: tris.append(sorted(vs))
oval = [c.start for c in C.FACE_LANDMARKS_FACE_OVAL]
print("puntos", len(pts), "aristas", len(tess), "triángulos", len(tris), "imagen", w, h)
json.dump({"w": w, "h": h, "points": pts, "tris": tris, "oval": oval,
           "matrix": np.array(res.facial_transformation_matrixes[0]).tolist(),
           "blend": {b.category_name: b.score for b in res.face_blendshapes[0]}}, open(sys.argv[2], "w"))
