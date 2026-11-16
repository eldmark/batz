"""Silueta de los perfiles: borde delantero, superior y trasero (ambos lados, el de -x espejado)."""
import json, cv2, numpy as np
out = {}
for name, flip in (('side_px', False), ('side_nx', True)):
    im = cv2.imread(name + '.png')
    if flip: im = im[:, ::-1].copy()
    H, W = im.shape[:2]
    bg = np.median(np.vstack([im[5:40, 5:40].reshape(-1, 3), im[5:40, -40:-5].reshape(-1, 3)]), 0)
    d = np.abs(im.astype(float) - bg).max(2)
    fg = (d > 28).astype(np.uint8) * 255
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg)
    k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); fg = np.where(lab == k, 255, 0).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    front = [int(np.nonzero(fg[r])[0].min()) if fg[r].any() else -1 for r in range(H)]
    back = [int(np.nonzero(fg[r])[0].max()) if fg[r].any() else -1 for r in range(H)]
    top = [int(np.nonzero(fg[:, c])[0].min()) if fg[:, c].any() else -1 for c in range(W)]
    cv2.imwrite(name + '_fg.png', fg)
    out[name] = {'w': W, 'h': H, 'front': front, 'back': back, 'top': top}
    # gráfico de control
    dbg = im.copy()
    for r, c in enumerate(front):
        if c >= 0: cv2.circle(dbg, (c, r), 1, (0, 0, 255), -1)
    for y in range(0, H, 25):
        cv2.line(dbg, (0, y), (W, y), (0, 200, 0) if y % 100 else (0, 120, 255), 1); cv2.putText(dbg, str(y), (2, y - 2), 0, .35, (0, 0, 0), 1)
    for x in range(0, W, 25):
        cv2.line(dbg, (x, 0), (x, H), (0, 200, 0) if x % 100 else (0, 120, 255), 1)
        if x % 100 == 0: cv2.putText(dbg, str(x), (x + 2, 12), 0, .35, (0, 0, 0), 1)
    cv2.imwrite(name + '_dbg.png', dbg)
json.dump(out, open('profile.json', 'w'))
