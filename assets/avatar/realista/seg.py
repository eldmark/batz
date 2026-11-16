"""Silueta de la persona (GrabCut, local) + colores de pelo e iris de la foto."""
import json, cv2, numpy as np
d = json.load(open('foto_lm.json')); P = np.array(d['points'])
img = cv2.imread('foto.png'); H, W = img.shape[:2]
fi = json.load(open('foto_info.json'))
face_h = P[152, 1] - P[10, 1]
x0, x1 = P[:468, 0].min(), P[:468, 0].max(); pad = (x1 - x0) * .22
rect_top = max(0, int(P[10, 1] - face_h * .75))
mask = np.full((H, W), cv2.GC_BGD, np.uint8)
mask[rect_top:int(P[152, 1] + face_h * .1), int(x0 - pad):int(x1 + pad)] = cv2.GC_PR_FGD
oval = P[fi['oval'], :2].astype(np.int32)
cv2.fillPoly(mask, [oval], cv2.GC_FGD)
# pelo seguro: justo arriba del nacimiento del pelo, al centro
hl = np.array(fi['hairline'])
for x, y in hl[::3].astype(int):
    cv2.circle(mask, (x, max(0, y - 25)), 10, cv2.GC_FGD, -1)
bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
cv2.grabCut(img, mask, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
person = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
# quedarse con la componente que contiene la cara y rellenar huecos
n, lab = cv2.connectedComponents(person)
person = np.where(lab == lab[int(P[1, 1]), int(P[1, 0])], 255, 0).astype(np.uint8)
person = cv2.morphologyEx(person, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
person = cv2.erode(person, np.ones((5, 5), np.uint8))
cv2.imwrite('foto_person.png', cv2.GaussianBlur(person, (0, 0), 3))
# pelo: píxeles oscuros de la persona por encima del nacimiento
lum = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
above = np.zeros((H, W), bool)
for x, y in hl.astype(int): above[:max(0, y - 8), x] = True
hp = img[(person > 0) & above & (lum < 90)]
hair = np.median(hp, 0)[::-1] / 255 if len(hp) > 50 else np.array([.17, .115, .085])
# iris: centro y radio en píxeles, color
irises = []
for c, ring in ((468, (469, 470, 471, 472)), (473, (474, 475, 476, 477))):
    cx, cy = P[c, :2]; r = np.mean([np.hypot(*(P[i, :2] - P[c, :2])) for i in ring])
    yy, xx = np.mgrid[:H, :W]; m = (xx - cx) ** 2 + (yy - cy) ** 2 < (r * .8) ** 2
    irises.append({'c': [cx, cy], 'r': r, 'color': (np.median(img[m], 0)[::-1] / 255).tolist()})
fi.update({'hair_srgb': hair.tolist(), 'iris': irises})
json.dump(fi, open('foto_info.json', 'w'))
dbg = img.copy(); dbg[person < 128] //= 4
cv2.imwrite('person_dbg.jpg', cv2.resize(dbg, (W // 2, H // 2)))
print('pelo', hair, 'iris', [(round(i['r'], 1), [round(c, 2) for c in i['color']]) for i in irises])
