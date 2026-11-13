"""Malla de la cara desde los puntos de MediaPipe + textura con el borde fundido en tono de piel."""
import json, cv2, numpy as np
d = json.load(open("face1.json"))
W, H = d["w"], d["h"]
P = np.array(d["points"][:468])            # sin los puntos del iris
xy = P[:, :2] * [W, H]
oval = np.array([xy[i] for i in dict.fromkeys(d["oval"])], np.float32)
# Delaunay sobre la proyección frontal, solo dentro del óvalo (cubre ojos y boca: la foto los muestra)
sub = cv2.Subdiv2D((0, 0, W, H))
for p in xy: sub.insert((float(min(max(p[0], 0), W - 1)), float(min(max(p[1], 0), H - 1))))
index = {(round(float(p[0]), 3), round(float(p[1]), 3)): i for i, p in enumerate(np.clip(xy, 0, [W - 1, H - 1]))}
tris = []
for t in sub.getTriangleList():
    pts = t.reshape(3, 2)
    ids = [int(np.argmin(((xy - [a, b]) ** 2).sum(1))) for a, b in pts]
    if len(set(ids)) < 3 or any(((xy[i] - p) ** 2).sum() > 1.0 for i, p in zip(ids, pts)): continue
    c = pts.mean(0)
    if cv2.pointPolygonTest(oval, (float(c[0]), float(c[1])), False) >= 0: tris.append(ids)
# metros: ancho de cara (óvalo) ≈ 0.145 m
width_px = oval[:, 0].max() - oval[:, 0].min()
S = 0.145 / width_px
center = xy[[1]].mean(0)                      # punta de la nariz como origen horizontal
V = np.c_[(xy[:, 0] - center[0]) * S, -(P[:, 2] * W) * S, -(xy[:, 1] - center[1]) * S]  # x derecha, y hacia la cámara(+), z arriba
V[:, 1] *= -1                                 # Blender: -Y mira a la cámara
x0, y0 = oval.min(0) - 0.10 * (oval.max(0) - oval.min(0))
x1, y1 = oval.max(0) + 0.10 * (oval.max(0) - oval.min(0))
side = max(x1 - x0, y1 - y0); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
x0, y0 = cx - side / 2, cy - side / 2
UV = np.c_[(xy[:, 0] - x0) / side, 1 - (xy[:, 1] - y0) / side]
# faldón: un anillo fuera del óvalo (18 % más grande) que en Blender se apoya sobre el cráneo
order = list(dict.fromkeys(d["oval"]))
c2 = xy[order].mean(0)
skirt = []
for i in order:
    up = (c2[1] - xy[i][1]) / (oval[:, 1].max() - oval[:, 1].min()) * 2   # 1 arriba, -1 abajo
    k = 1.03 if up > .35 else 1.08
    q = c2 + (xy[i] - c2) * k
    skirt.append(len(V))
    V = np.vstack([V, [(q[0] - center[0]) * S, V[i][1], -(q[1] - center[1]) * S]])
    UV = np.vstack([UV, [(q[0] - x0) / side, 1 - (q[1] - y0) / side]])
for k in range(len(order)):
    a, b = order[k], order[(k + 1) % len(order)]
    ra, rb = skirt[k], skirt[(k + 1) % len(order)]
    tris += [[a, b, rb], [a, rb, ra]]
with open("face.obj", "w") as f:
    f.write("mtllib face.mtl\no Cara\n")
    for v in V: f.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
    for u in UV: f.write(f"vt {u[0]:.5f} {u[1]:.5f}\n")
    f.write("usemtl Cara\n")
    for a, b, c in tris: f.write(f"f {a+1}/{a+1} {b+1}/{b+1} {c+1}/{c+1}\n")
# textura: fuera del óvalo, tono de piel (inpaint) para que el borde no sangre fondo blanco
img = cv2.imread(r"C:/Users/LZARO~1/AppData/Local/Temp/claude/87014b816d34d15c/0310c928-dc5b-4b2a-8b90-1d688d04c369/images/1.jpg")
mask = np.full((H, W), 255, np.uint8); cv2.fillPoly(mask, [oval.astype(np.int32)], 0)
mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
filled = cv2.inpaint(img, mask, 9, cv2.INPAINT_TELEA)
# tono de piel: mejillas (puntos 50 y 280) y frente (151)
patches = []
for i in (50, 280, 205, 425, 108, 337, 151):     # mejillas y frente
    x, y = int(xy[i][0]), int(xy[i][1])
    patches.append(img[y - 5:y + 6, x - 5:x + 6].reshape(-1, 3))
inside = np.zeros((H, W), np.uint8); cv2.fillPoly(inside, [oval.astype(np.int32)], 255)
inside = cv2.erode(inside, np.ones((15, 15), np.uint8))
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
keep = (inside > 0) & (hsv[..., 2] > 150) & (hsv[..., 1] < 110)   # sin cejas, ojos ni labios
skin = np.median(img[keep], 0)
# el anillo exterior del óvalo se funde hacia ese tono
dist = cv2.distanceTransform(255 - mask, cv2.DIST_L2, 5)
ring = np.clip(dist / 7.0, 0, 1)[..., None]
blend = (filled * ring + skin * (1 - ring)).astype(np.uint8)
M = np.float32([[1024 / side, 0, -x0 * 1024 / side], [0, 1024 / side, -y0 * 1024 / side]])
big = cv2.warpAffine(blend, M, (1024, 1024), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
big = cv2.addWeighted(big, 1.35, cv2.GaussianBlur(big, (0, 0), 3), -0.35, 0)   # algo de nitidez
cv2.imwrite("cara.jpg", big, [cv2.IMWRITE_JPEG_QUALITY, 90])
rgb = skin[::-1] / 255
json.dump({"ring": skirt, "skin_srgb": rgb.tolist(), "scale": float(S), "verts": len(V), "tris": len(tris),
           "chin_z": float(V[152, 2]), "forehead_z": float(V[10, 2]), "nose_y": float(V[1, 1]),
           "left_x": float(V[234, 0]), "right_x": float(V[454, 0]), "ear_y": float(V[234, 1])}, open("face_info.json", "w"), default=lambda o: o.tolist())
print(open("face_info.json").read())
