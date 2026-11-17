"""Máscara de la cara en la foto (canal alfa): óvalo + frente hasta el nacimiento del pelo, borde suave."""
import json, cv2, numpy as np
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarksConnections as C
d = json.load(open('foto_lm.json')); P = np.array(d['points'])[:, :2]
img = cv2.imread('foto.png'); H, W = img.shape[:2]
oval_idx = list(dict.fromkeys(c.start for c in C.FACE_LANDMARKS_FACE_OVAL))
# ordenar el óvalo por ángulo alrededor de su centro
c = P[oval_idx].mean(0); oval_idx.sort(key=lambda i: np.arctan2(P[i, 1] - c[1], P[i, 0] - c[0]))
oval = P[oval_idx].astype(np.int32)
mask = np.zeros((H, W), np.uint8); cv2.fillPoly(mask, [oval], 255)
lum = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(float)
lum = cv2.GaussianBlur(lum, (0, 0), 3)
top = {}
ys, xs = np.nonzero(mask)
x_lo, x_hi = int(P[oval_idx, 0].min()), int(P[oval_idx, 0].max())
skin_l = np.median(lum[int(P[10, 1]):int(P[10, 1]) + 20, int(P[10, 0]) - 20:int(P[10, 0]) + 20])
hair = []
for x in range(x_lo, x_hi + 1):
    col = np.nonzero(mask[:, x])[0]
    if not len(col): continue
    y = col.min()
    lim = P[10, 1] - .42 * (P[152, 1] - P[10, 1]) * (1 - ((x - c[0]) / (x_hi - c[0] + 1)) ** 2 * .5)
    while y > lim and lum[y - 1, x] > skin_l * .78: y -= 1      # subir mientras sea piel
    hair.append((x, y)); mask[y:col.min() + 1, x] = 255
hair = np.array(hair)
# el nacimiento del pelo, suavizado
hs = hair.copy().astype(float); hs[:, 1] = np.convolve(np.pad(hair[:, 1], 6, mode='edge'), np.ones(13) / 13, 'valid')
mask[:] = 0; poly = np.vstack([oval[np.argsort([np.arctan2(p[1] - c[1], p[0] - c[0]) for p in oval])]])
cv2.fillPoly(mask, [oval], 255)
for x, y in hs.astype(int): mask[y:int(c[1]), x] = np.maximum(mask[y:int(c[1]), x], 255)
mask = cv2.erode(mask, np.ones((7, 7), np.uint8))
alpha = cv2.GaussianBlur(mask, (0, 0), 7)
# boca cerrada: el hueco con los dientes se pinta del color del borde del labio, más oscuro
INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
mouth = np.zeros((H, W), np.uint8); cv2.fillPoly(mouth, [P[INNER].astype(np.int32)], 255)
gap = np.linalg.norm(P[13] - P[14]) / np.linalg.norm(P[61] - P[291])
if gap < .06: mouth[:] = 0          # boca cerrada: nada que rellenar
ring = cv2.dilate(mouth, np.ones((9, 9), np.uint8)) & ~cv2.dilate(mouth, np.ones((3, 3), np.uint8))
lip = np.median(img[ring > 0], 0) * .78 if mouth.any() else np.zeros(3)
m = cv2.GaussianBlur(cv2.dilate(mouth, np.ones((5, 5), np.uint8)), (0, 0), 2.5)[..., None] / 255.
if mouth.any(): img = (img * (1 - m) + lip * m).astype(np.uint8)
# bigote: se aclara hacia el tono de las mejillas (se nota menos la sombra bajo la nariz)
lip_top = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]
poly_m = np.vstack([P[[98, 2, 327]], P[lip_top[::-1]]]).astype(np.int32)
mm = np.zeros((H, W), np.uint8); cv2.fillPoly(mm, [cv2.convexHull(poly_m)], 255)
mm = cv2.GaussianBlur(cv2.dilate(mm, np.ones((3, 3), np.uint8)), (0, 0), 3)[..., None] / 255. * .45
def _patch(i, r=8): x, y = P[i].astype(int); return img[y - r:y + r, x - r:x + r].reshape(-1, 3)
cheek_c = np.median(np.vstack([_patch(i) for i in (205, 425, 50, 280)]), 0)
# mantener la textura: se suma la diferencia de brillo, no se pinta encima
img = np.clip(img + (cheek_c - cv2.GaussianBlur(img, (0, 0), 4)) * mm, 0, 255).astype(np.uint8)
rgba = np.dstack([img, alpha]); cv2.imwrite('foto_rgba.png', rgba)
# piel: mediana de mejillas y frente
def patch(i, r=14): x, y = P[i].astype(int); return img[y - r:y + r, x - r:x + r].reshape(-1, 3)
inner = cv2.erode(mask, np.ones((61, 61), np.uint8)) > 0
l2 = lum[inner]; px = img[inner][(l2 > np.percentile(l2, 55)) & (l2 < np.percentile(l2, 85))]
skin = np.median(px, 0)[::-1] / 255
json.dump({'skin_srgb': skin.tolist(), 'hairline': hs.tolist(), 'oval': oval_idx}, open('foto_info.json', 'w'))
dbg = img.copy(); dbg[alpha < 128] //= 3
for x, y in hs.astype(int): cv2.circle(dbg, (x, y), 2, (0, 0, 255), -1)
cv2.imwrite('mask_dbg.jpg', cv2.resize(dbg, (W // 2, H // 2)))
print('piel', skin, 'pelo y rango', hs[:, 1].min(), hs[:, 1].max())
