"""Perfil: la línea media de la cara (frente, nariz, labios, mentón) toma la silueta de las fotos de perfil,
y las orejas se mueven a donde están en las fotos. Guarda el mapeo (y, z) → píxel de cada perfil.
blender -b fit.blend --python profile_fit.py -- <dir>/"""
import bpy, json, sys, numpy as np
from mathutils import Vector
D = sys.argv[sys.argv.index('--') + 1]
pj = json.load(open(D + 'profile.json')); fl = json.load(open(D + 'fit_lm.json'))
B = np.array(fl['B'])
EARS = {'side_px': (434, 228), 'side_nx': (446, 221)}      # centro de la oreja en cada foto (la de −x espejada)
body = bpy.data.objects['Body']; eyes = [bpy.data.objects['Eye.L'], bpy.data.objects['Eye.R']]
V = np.array([v.co[:] for v in body.data.vertices])
def smooth01(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
chin, brow = B[152, 2], (B[105, 2] + B[334, 2]) / 2
cy = (B[234, 1] + B[454, 1]) / 2 + .01
# perfil de la malla: lo más adelantado por altura
zs = np.arange(chin - .04, brow + .09, .001)
head = (V[:, 2] > chin - .06) & (V[:, 1] < cy)
fm = np.array([V[head & (np.abs(V[:, 2] - z) < .0012), 1].min() for z in zs])
def mesh_keys():
    tip = zs[np.argmin(np.where((zs > chin + .03) & (zs < brow), fm, 9))]
    sel = zs[np.argmax(np.where((zs > tip + .012) & (zs < tip + .06), fm, -9))]
    # borde inferior del mentón: bajando desde la punta, donde el perfil ya retrocedió 1,2 cm detrás de lo más adelantado del mentón
    order = np.argsort(-zs); best = 9; men = None
    for i in order:
        z = zs[i]
        if z > tip - .05: continue
        best = min(best, fm[i])
        if fm[i] - best > .012: men = z; break
    return tip, sel, men
z_tip, z_sel, z_pog = mesh_keys()
print('malla: punta', round(z_tip, 4), 'entrecejo', round(z_sel, 4), 'borde del mentón', round(z_pog, 4))
targets, maps = [], {}
for name in ('side_px', 'side_nx'):
    p = pj[name]; f = np.array(p['front'], float); H = p['h']; f[f < 0] = np.nan
    rows = np.arange(H)
    def am(lo, hi, fn): r = np.arange(max(0, int(lo)), min(H, int(hi))); v = f[r]; return int(r[fn(np.where(np.isnan(v), np.inf if fn is np.argmin else -np.inf, v))])
    r_tip = am(H * .3, H * .65, np.argmin)
    r_sel = am(r_tip - 75, r_tip - 15, np.argmax)
    best = 1e9; r_pog = None
    for r in range(r_tip + 45, H):
        if np.isnan(f[r]): continue
        best = min(best, f[r])
        if f[r] - best > .012 / ((z_sel - z_pog) / max(1, (r - r_sel))) * 0 + 12 * 0 + 1e9: break
    # misma regla en píxeles: se busca la fila donde el perfil retrocede 1,2 cm; la escala aún no se conoce,
    # así que se itera: primero con 1 mm/px y luego con la escala resultante
    sc = .001
    for _ in range(3):
        best = 1e9
        for r in range(r_tip + 45, H):
            if np.isnan(f[r]): continue
            best = min(best, f[r])
            if (f[r] - best) * sc > .012: r_pog = r; break
        sc = (z_sel - z_pog) / (r_pog - r_sel)
    s = (z_sel - z_pog) / (r_pog - r_sel)                # metros por píxel
    zr = z_sel - (rows - r_sel) * s                      # altura de cada fila
    # y de cada columna: y = (c − c0)·s; c0 tal que el residuo medio entre entrecejo y mentón sea 0
    band = (zs > z_pog - .005) & (zs < z_sel + .005)
    fp = np.interp(zs, zr[::-1], f[::-1] * s)            # columnas → metros, sin desplazar
    off = np.nanmean(fm[band] - fp[band])
    yt = fp + off
    targets.append(yt)
    maps[name] = {'s': s, 'r_sel': r_sel, 'z_sel': z_sel, 'off': off}
    print(name, 'filas punta/entrecejo/borde del mentón', r_tip, r_sel, r_pog, 'escala mm/px', round(s * 1000, 3))
yt = np.nanmean(np.array(targets), 0)
dy = yt - fm
lo, hi = z_pog - .005, z_sel + .035
taper = smooth01((zs - lo) / .012) * smooth01((hi - zs) / .015)
dy = np.nan_to_num(dy) * taper
k = np.exp(-np.arange(-12, 13) ** 2 / 2 / 4.0 ** 2); k /= k.sum()
dy = np.convolve(np.pad(dy, 12, mode='edge'), k, 'valid')
dy = np.clip(dy, -.008, .008)
print('corrección (mm) cada 1 cm:', [(round(z, 3), round(d * 1000, 1)) for z, d in zip(zs[::10], dy[::10])])
# ancho lateral de la corrección según la zona
z_sub = z_tip - .016
def sigx(z): return np.where(z > z_sel, .05, np.where(z > z_sub, .019, np.where(z > z_pog + .012, .03, .036)))
dv = np.interp(V[:, 2], zs, dy, left=0, right=0)
fmv = np.interp(V[:, 2], zs, fm)
w = np.exp(-(V[:, 0] / sigx(V[:, 2])) ** 2) * smooth01((fmv + .04 - V[:, 1]) / .02) * head
V[:, 1] += dv * w
# orejas: no se mueven; se guarda dónde está cada una (malla) y dónde la ve la foto, para deformar la textura
for name, sx in (('side_px', 1), ('side_nx', -1)):
    m = maps[name]; c, r = EARS[name]
    ear = (sx * V[:, 0] > .068) & (np.abs(V[:, 2] - (brow - .02)) < .045) & (np.abs(V[:, 1] - cy) < .05)
    ce = V[ear].mean(0)
    m['ear_mesh'] = [float(ce[1]), float(ce[2])]
    m['ear_photo'] = [float(c * m['s'] + m['off']), float(m['z_sel'] - (r - m['r_sel']) * m['s'])]
    print(name, 'oreja malla', np.round(m['ear_mesh'], 3), 'foto', np.round(m['ear_photo'], 3))
# cuello un poco más grueso
zc0, zc1 = 1.43, chin - .015
wn = smooth01((V[:, 2] - zc0) / .025) * smooth01((zc1 - V[:, 2]) / .02) * smooth01((.1 - np.hypot(V[:, 0], V[:, 1] + .01)) / .025)
V[:, 0] *= 1 + .09 * wn; V[:, 1] = (V[:, 1] + .01) * (1 + .09 * wn) - .01
body.data.vertices.foreach_set('co', V.ravel()); body.data.update()
for e in eyes:
    c = sum((v.co for v in e.data.vertices), Vector()) / len(e.data.vertices)
    d = float(np.interp(c.z, zs, dy)) * float(np.exp(-(c.x / .05) ** 2))
    for v in e.data.vertices: v.co.y += d
json.dump(maps, open(D + 'side_maps.json', 'w'))
bpy.ops.wm.save_as_mainfile(filepath=D + 'fit.blend')
exec(open(D + 'shots.py').read())
z = brow - .02
shots(D + 'prof_', [('front.png', (0, 0, z), .9, 0), ('side.png', (0, 0, z), .9, 1.5708), ('34.png', (0, 0, z), .9, .6)])
