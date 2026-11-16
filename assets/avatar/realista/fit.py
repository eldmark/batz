"""Deforma la cabeza de la base para que sus 468 puntos coincidan con los de la foto (alineados por similitud)."""
import bpy, bmesh, json, sys, math, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
D = sys.argv[sys.argv.index('--') + 1]
cam = json.load(open(D + 'base_cam.json')); bl = json.load(open(D + 'base_lm.json')); ul = json.load(open(D + 'foto_lm.json'))
body = bpy.data.objects['Body']; eyes = [bpy.data.objects['Eye.L'], bpy.data.objects['Eye.R']]
bm = bmesh.new(); bm.from_mesh(body.data)
for e in eyes: bm.from_mesh(e.data)
tree = BVHTree.FromBMesh(bm); bm.free()
N = 468
B = np.zeros((N, 3)); ok = np.zeros(N, bool)
for i, (u, v, _) in enumerate(bl['points'][:N]):
    x = (u / cam['res'] - .5) * cam['ortho']; z = cam['cz'] - (v / cam['res'] - .5) * cam['ortho']
    hit = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
    if hit[0] is not None: B[i] = hit[0]; ok[i] = hit[0].y < -.02
U = np.array([[p[0], p[2], -p[1]] for p in ul['points'][:N]])
INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
use = ok.copy(); use[INNER] = False
for i, o in zip(INNER, OUTER): B[i, 1] = B[o, 1] + .003     # los rayos de la ranura entran a la boca: profundidad del labio
def umeyama(src, dst):
    ms, md = src.mean(0), dst.mean(0); a, b = src - ms, dst - md
    Uu, S, Vt = np.linalg.svd(b.T @ a / len(src)); d = np.sign(np.linalg.det(Uu @ Vt))
    E = np.diag([1, 1, d]); R = Uu @ E @ Vt; s = np.trace(np.diag(S) @ E) / a.var(0).sum()
    return s, R, md - s * R @ ms
s, R, t = umeyama(U[use], B[use])
T = (s * (R @ U.T)).T + t
print('escala', s, 'error medio antes', np.linalg.norm(T[use] - B[use], axis=1).mean())
Dsp = T - B
Dsp[:, 1] *= .5                                   # la profundidad de MediaPipe es menos fiable
for i, o in zip(INNER, OUTER): Dsp[i] = Dsp[o]; ok[i] = True   # boca cerrada: los labios internos siguen a los externos
P = B[ok]; Dk = Dsp[ok]
# afín + gaussianas sobre el residuo
# escala por eje + traslación (sin cizalla, para no torcer el cráneo)
c0 = P.mean(0); aff = np.zeros((4, 3))
for k in range(3):
    A = np.c_[P[:, k] - c0[k], np.ones(len(P))]; (a, b), *_ = np.linalg.lstsq(A, Dk[:, k], rcond=None)
    aff[k, k] = a; aff[3, k] = b - a * c0[k]
A1 = np.c_[P, np.ones(len(P))]
res = Dk - A1 @ aff
bad = np.abs(res[:, 1]) > .008                     # puntos dentro de fosas o cuencas: fuera
print('descartados', bad.sum())
P, Dk, res = P[~bad], Dk[~bad], res[~bad]
sig = .03
def K(X, Y): d2 = ((X[:, None, :] - Y[None, :, :]) ** 2).sum(-1); return np.exp(-d2 / sig ** 2)
W = np.linalg.solve(K(P, P) + 4e-2 * np.eye(len(P)), res)
def disp(X): return np.c_[X, np.ones(len(X))] @ aff + K(X, P) @ W
# segunda pasada fina: lo que la primera no alcanzó (nariz, labios, párpados), sobre todo en x y z
def disp1(X): return np.c_[X, np.ones(len(X))] @ aff + K(X, P) @ W
r2 = (Dk - disp1(P)); r2[:, 1] *= .3
sig2 = .011
K2 = lambda X, Y: np.exp(-((X[:, None, :] - Y[None, :, :]) ** 2).sum(-1) / sig2 ** 2)
W2 = np.linalg.solve(K2(P, P) + 2e-2 * np.eye(len(P)), r2)
def disp(X): return disp1(X) + K2(X, P) @ W2
chin = B[152][2]
def fall(z): t = np.clip((z - (chin - .085)) / .075, 0, 1); return t * t * (3 - 2 * t)
V = np.array([v.co[:] for v in body.data.vertices])
m = V[:, 2] > chin - .1
dv = np.zeros_like(V); dv[m] = disp(V[m]) * fall(V[m, 2])[:, None]
body.data.vertices.foreach_set('co', (V + dv).ravel()); body.data.update()
for e in eyes:
    c = np.array(sum((v.co for v in e.data.vertices), Vector()) / len(e.data.vertices))[None]
    d = disp(c)[0]
    for v in e.data.vertices: v.co += Vector(d)
print('desplazamiento máx', np.abs(dv).max(), 'afín', np.round(aff[:3], 3).tolist())
# puntos finales (para la proyección de la foto)
Bf = B + disp(B) * fall(B[:, 2])[:, None]
# labios más finos: la profundidad alrededor de la boca se suaviza (Laplaciano solo en y)
V2 = V + dv
poly = Bf[OUTER][:, [0, 2]]
def inside(pt, pg):
    x, z = pt[:, 0][:, None], pt[:, 1][:, None]; x1, z1 = pg[:, 0][None], pg[:, 1][None]
    x2, z2 = np.roll(pg, -1, 0)[:, 0][None], np.roll(pg, -1, 0)[:, 1][None]
    cross = ((z1 > z) != (z2 > z)) & (x < (x2 - x1) * (z - z1) / (z2 - z1 + 1e-12) + x1)
    return cross.sum(1) % 2 == 1
cen = poly.mean(0); grow = cen + (poly - cen) * 1.6
front_m = V2[:, 1] < Bf[0, 1] + .02
inn = inside(V2[:, [0, 2]], poly) & front_m
reg = inside(V2[:, [0, 2]], grow) & front_m
w = np.where(inn, 1.0, 0.0)
nb = [[] for _ in range(len(V2))]
for e in body.data.edges:
    a, b = e.vertices; nb[a].append(b); nb[b].append(a)
# el interior de la boca (tapado desde el frente) no participa: si no, arrastra los labios
_bm = bmesh.new(); _bm.from_mesh(body.data); _tree = BVHTree.FromBMesh(_bm); _bm.free()
cand = np.nonzero(reg | (np.abs(V2[:, 0] - cen[0]) < .05) & (np.abs(V2[:, 2] - cen[1]) < .04))[0]
hidden = np.zeros(len(V2), bool)
for i in cand:
    hidden[i] = _tree.ray_cast(Vector(V2[i]) + Vector((0, -.0015, 0)), Vector((0, -1, 0)), .08)[0] is not None
reg &= ~hidden; inn &= ~hidden
idx = np.nonzero(reg)[0]
y = V2[:, 1].copy()
nbv = [[j for j in nb[i] if not hidden[j]] or [i] for i in idx]
deg = max(len(n) for n in nbv)
NB = np.array([n + [n[0]] * (deg - len(n)) for n in nbv]); CNT = np.array([len(n) for n in nbv])
MASKNB = np.arange(deg)[None] < CNT[:, None]
for it in range(600):
    y[idx] = (y[NB] * MASKNB).sum(1) / CNT
# peso: 0.8 dentro de los labios, decae hasta el borde de la región
dist = np.array([np.min(np.linalg.norm(poly - V2[i, [0, 2]], axis=1)) for i in idx])
wt = np.where(inn[idx], .95, .95 * np.clip(1 - dist / .014, 0, 1))
dy = (y[idx] - V2[idx, 1]) * wt
V2[idx, 1] += dy
# el interior de la boca retrocede igual que el labio más cercano (si no, asoma por delante)
hid = np.nonzero(hidden)[0]
if len(hid):
    dd = ((V2[hid][:, None, [0, 2]] - V2[idx][None, :, [0, 2]]) ** 2).sum(-1)
    V2[hid, 1] += np.clip(dy[dd.argmin(1)], 0, None) + .001
dv = V2 - V
body.data.vertices.foreach_set('co', V2.ravel()); body.data.update()
Bf[INNER + OUTER, 1] = Bf[INNER + OUTER, 1]  # (solo x, z se usan para la foto)
print('labios: vértices', len(idx))
# nariz más angosta: las aletas de la base son más anchas que las de la foto
V3 = np.array([v.co[:] for v in body.data.vertices])
tip = Bf[4]; sub = Bf[2]
cz_n = (tip[2] + sub[2]) / 2 - .002
r = np.sqrt((V3[:, 0] / .028) ** 2 + ((V3[:, 2] - cz_n) / .026) ** 2)
wn = np.clip(1 - r, 0, 1) ** .7 * (V3[:, 1] < tip[1] + .045)
V3[:, 0] *= 1 - .17 * wn
V3[:, 1] += .002 * wn * (np.abs(V3[:, 0]) > .008)          # aletas un poco hacia atrás
body.data.vertices.foreach_set('co', V3.ravel()); body.data.update()
Bf[:, 0] *= 1 - .17 * np.clip(1 - np.sqrt((Bf[:, 0] / .028) ** 2 + ((Bf[:, 2] - cz_n) / .026) ** 2), 0, 1) ** .7 * (Bf[:, 1] < tip[1] + .045)
json.dump({'B': Bf.tolist(), 'ok': ok.tolist()}, open(D + 'fit_lm.json', 'w'))
bpy.ops.wm.save_as_mainfile(filepath=D + 'fit.blend')
exec(open(D + 'shots.py').read())
z = cam['cz']
shots(D + 'fit_', [('front.png', (0, 0, z), .9, 0), ('34.png', (0, 0, z), .9, -.6), ('side.png', (0, 0, z), .9, -1.5708)])
