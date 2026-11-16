"""Puntos de MediaPipe (478) de una imagen → JSON (píxeles + z en la escala de x)."""
import json, sys, cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path="face_landmarker.task"), num_faces=1,
                                    output_facial_transformation_matrixes=True)
det = vision.FaceLandmarker.create_from_options(opts)
bgr = cv2.imread(sys.argv[1]); h, w = bgr.shape[:2]
res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))))
if not res.face_landmarks: print("SIN CARA"); sys.exit(1)
pts = [[p.x * w, p.y * h, p.z * w] for p in res.face_landmarks[0]]
json.dump({"w": w, "h": h, "points": pts, "matrix": np.array(res.facial_transformation_matrixes[0]).tolist()}, open(sys.argv[2], "w"))
P = np.array(pts); print("ok", w, h, "bbox", P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max())
if len(sys.argv) > 3:
    for x, y, _ in pts: cv2.circle(bgr, (int(x), int(y)), 2, (0, 255, 0), -1)
    cv2.imwrite(sys.argv[3], bgr)
