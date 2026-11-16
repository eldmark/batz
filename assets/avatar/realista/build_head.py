"""Cabeza: foto proyectada, pelo con volumen, ojos procedurales; una textura compuesta en numpy.
blender -b fit.blend --python build_head.py -- <dir>/"""
import bpy, bmesh, json, sys, math, heapq, numpy as np
from mathutils import Vector
D = sys.argv[sys.argv.index('--') + 1]
fl = json.load(open(D + 'fit_lm.json')); ul = json.load(open(D + 'foto_lm.json')); fi = json.load(open(D + 'foto_info.json'))
B = np.array(fl['B']); ok = np.array(fl['ok'])
W, H = ul['w'], ul['h']; PH = np.array(ul['points'])[:478, :2]
body = bpy.data.objects['Body']; eyes = [bpy.data.objects['Eye.L'], bpy.data.objects['Eye.R']]
INNER_UP = [191, 80, 81, 82, 13, 312, 311, 310, 415]; INNER_LO = [95, 88, 178, 87, 14, 317, 402, 318, 324]
def smooth01(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

# ── 1. ojos dentro del cuerpo ──
for e in eyes:
    g = e.vertex_groups.new(name='EYES'); g.add(range(len(e.data.vertices)), 1, 'REPLACE')
bpy.ops.object.select_all(action='DESELECT')
for o in [body] + eyes: o.select_set(True)
bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
me = body.data

def verts(): return np.array([v.co[:] for v in me.vertices])
def group_mask(name):
    gi = body.vertex_groups[name].index
    return np.array([any(g.group == gi and g.weight > .5 for g in v.groups) for v in me.vertices])
V = verts(); nV = len(V); is_eye = group_mask('EYES')
NRM = np.array([v.normal[:] for v in me.vertices])
chin, brow, nose = B[152, 2], (B[105, 2] + B[334, 2]) / 2, B[4, 2]
ZCUT = chin - .075; TOP = V[:, 2].max()
cy = (B[234, 1] + B[454, 1]) / 2 + .01
print('chin', chin, 'brow', brow, 'top', TOP)

# ── 2. TPS (x, z) → píxel de la foto ──
src = B[:468, [0, 2]].copy(); dst = PH[:468].copy()
src[INNER_UP, 1] += .0008; src[INNER_LO, 1] -= .0008
def tps_fit(S, T, lam=1e-7):
    n = len(S); r = np.sqrt(((S[:, None] - S[None]) ** 2).sum(-1)); K = r ** 2 * np.log(r + 1e-12)
    P = np.c_[np.ones(n), S]; A = np.zeros((n + 3, n + 3)); A[:n, :n] = K + lam * np.eye(n); A[:n, n:] = P; A[n:, :n] = P.T
    return S, np.linalg.solve(A, np.r_[T, np.zeros((3, 2))])
def tps_eval(model, X):
    S, sol = model; out = np.zeros((len(X), 2))
    for i in range(0, len(X), 4000):
        x = X[i:i + 4000]; r = np.sqrt(((x[:, None] - S[None]) ** 2).sum(-1)); K = r ** 2 * np.log(r + 1e-12)
        out[i:i + 4000] = K @ sol[:len(S)] + np.c_[np.ones(len(x)), x] @ sol[len(S):]
    return out
model = tps_fit(src[ok[:468]], dst[ok[:468]])
def photo_px(X): return tps_eval(model, X[:, [0, 2]])
head = V[:, 2] > ZCUT - .02
pix = np.zeros((nV, 2)); pix[head] = photo_px(V[head])

# ── 3. campo del cuero cabelludo, suavizado sobre la malla ──
hl = np.array(fi['hairline'])
def hair_y_at(px): return np.interp(px, hl[:, 0], hl[:, 1], left=np.nan, right=np.nan)
th = np.degrees(np.arctan2(np.abs(V[:, 0]), -(V[:, 1] - cy)))
side_z = brow + .014; nape_z = nose - .025
geo_line = np.interp(th, [70, 105, 180], [side_z, side_z - .006, nape_z])
hy = hair_y_at(pix[:, 0])
f_front = np.where(np.isnan(hy), 0, smooth01((hy + 6 - pix[:, 1]) / 14))
f_geo = smooth01((V[:, 2] - geo_line) / .006)
wgeo = smooth01((th - 62) / 18)
field = np.where(np.isnan(hy), f_geo, f_front * (1 - wgeo) + f_geo * wgeo)
field = np.maximum(field, smooth01((V[:, 2] - (brow + .06)) / .01))
field[~head | is_eye] = 0
nb = [[] for _ in range(nV)]
for e in me.edges:
    a, b = e.vertices; nb[a].append(b); nb[b].append(a)
idx = np.nonzero(head & ~is_eye)[0]
deg = max(len(nb[i]) for i in idx)
NB = np.array([nb[i] + [nb[i][0]] * (deg - len(nb[i])) for i in idx]); CNT = np.array([len(nb[i]) for i in idx])
MK = np.arange(deg)[None] < CNT[:, None]
for _ in range(6): field[idx] = (field[NB] * MK).sum(1) / CNT * .5 + field[idx] * .5
scalp = field > .5

# ── 4. pelo: cáscara desde el cuero cabelludo ──
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
hf = [f for f in bm.faces if any(field[v.index] > .3 for v in f.verts) and all(head[v.index] and not is_eye[v.index] for v in f.verts)]
ret = bmesh.ops.duplicate(bm, geom=hf)
new_faces = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMFace)]
new_verts = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMVert)]
vmap = {v: i for i, v in enumerate(new_verts)}
# vértice original de cada vértice nuevo (mismo orden de creación que en hf)
newset = set(new_verts)
orig = {}
for a, b in ret['vert_map'].items():
    if b in newset and a not in newset: orig[b] = a.index
    elif a in newset and b not in newset: orig[a] = b.index
print('mapa de vértices', len(orig), len(new_verts))
# normales de la cáscara (= las del cráneo) y distancia al borde por Dijkstra
bmesh.ops.recalc_face_normals(bm, faces=new_faces)
bm.normal_update()
boundary = [v for v in new_verts if any(e.is_boundary for e in v.link_edges)]
dist = {v: 0.0 for v in boundary}; pq = [(0.0, id(v), v) for v in boundary]; heapq.heapify(pq)
while pq:
    d, _, v = heapq.heappop(pq)
    if d > dist.get(v, 1e9): continue
    for e in v.link_edges:
        w = e.other_vert(v)
        if w not in vmap: continue
        nd = d + e.calc_length()
        if nd < dist.get(w, 1e9): dist[w] = nd; heapq.heappush(pq, (nd, id(w), w))
part_x = -.028                               # raya del lado izquierdo de la imagen (−x)
for v in new_verts:
    p = v.co; hz = np.clip((p.z - (brow + .015)) / (TOP - brow - .015), 0, 1)
    T = .0035 + .015 * hz ** .9
    front_top = (p.y < cy - .035) * hz
    T += .007 * front_top                                     # tupé: el pelo se levanta adelante
    T *= .55 + .45 * smooth01((p.x - part_x) / .02 + .5)      # del lado de la raya, más pegado
    R = .006 + .006 * (1 - front_top)
    r = smooth01(dist.get(v, 1) / R) * smooth01((field[orig[v]] - .5) / .35)
    v.co = p + v.normal * (-.0007 + (.0019 + T) * r)     # en el borde queda bajo la piel: la línea la pone la textura
# suavizar la cáscara sin mover el borde
inner = [v for v in new_verts if v not in set(boundary)]
for _ in range(4):
    new = {v: sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges) for v in inner}
    for v, c in new.items(): v.co = v.co * .5 + c * .5
bm.to_mesh(me); bm.free(); me.update()
V = verts(); nV = len(V)
is_hair = np.zeros(nV, bool); is_hair[-len(new_verts):] = True
gh = body.vertex_groups.new(name='HAIR'); gh.add(np.nonzero(is_hair)[0].tolist(), 1, 'REPLACE')
is_eye = np.r_[is_eye, np.zeros(len(new_verts), bool)]
head = np.r_[head, np.ones(len(new_verts), bool)]
NRM = np.array([v.normal[:] for v in me.vertices])
pix = np.zeros((nV, 2)); pix[head] = photo_px(V[head])
field = np.r_[field, np.array([field[orig[v]] for v in new_verts])]

# ── 5. de frente / máscaras por vértice ──
from mathutils.bvhtree import BVHTree
_bm = bmesh.new(); _bm.from_mesh(me); _tree = BVHTree.FromBMesh(_bm); _bm.free()
mc = (B[13] + B[14]) / 2
box = (np.abs(V[:, 0] - mc[0]) < .036) & (np.abs(V[:, 2] - mc[2]) < .022) & ~is_hair & ~is_eye
is_mouth = np.zeros(nV, bool)
for i in np.nonzero(box)[0]:
    hit = _tree.ray_cast(Vector((V[i, 0], -1.0, V[i, 2])), Vector((0, 1, 0)))     # superficie visible de frente
    is_mouth[i] = hit[0] is not None and V[i, 1] - hit[0].y > .004
print('interior de la boca', is_mouth.sum())
ycut = (B[234, 1] + B[454, 1]) / 2
front = smooth01((-NRM[:, 1] + .3) / .35) * smooth01((ycut - V[:, 1]) / .015)

ey = np.zeros(nV)
for sgn in (-1, 1):
    m = is_eye & (np.sign(V[:, 0]) == sgn); ey[m] = (V[m, 1] < np.median(V[m, 1]))
front[is_eye] = ey[is_eye]
front[is_mouth] = 0

# ── 6. UV: atlas de la cabeza + pelo ──
for u in list(me.uv_layers): me.uv_layers.remove(u)
puv = me.uv_layers.new(name='PhotoUV')
lv = np.zeros(len(me.loops), int); me.loops.foreach_get('vertex_index', lv)
puv.data.foreach_set('uv', np.c_[pix[lv, 0] / W, 1 - pix[lv, 1] / H].ravel().astype(np.float32))
atlas = me.uv_layers.new(name='UVMap'); me.uv_layers.active = atlas
headfaces = np.array([all(head[i] for i in p.vertices) for p in me.polygons])
bpy.ops.object.mode_set(mode='EDIT'); bm = bmesh.from_edit_mesh(me)
for f in bm.faces: f.select = bool(headfaces[f.index])
bmesh.update_edit_mesh(me)
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.003, scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
def attr(name, vals3):
    a = me.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    a.data.foreach_set('color', np.c_[vals3, np.ones(nV)].ravel().astype(np.float32))
attr('m1', np.c_[is_mouth.astype(float), np.zeros(nV), front])
attr('m2', np.c_[field, is_eye.astype(float), is_hair.astype(float)])

# ── 7. horneado de pasadas (flotantes) ──
me.materials.clear()
bk = bpy.data.materials.new('Bake'); bk.use_nodes = True; me.materials.append(bk)
N, L = bk.node_tree.nodes, bk.node_tree.links
for n in list(N):
    if n.type != 'OUTPUT_MATERIAL': N.remove(n)
outn = N['Material Output']; em = N.new('ShaderNodeEmission'); L.new(em.outputs[0], outn.inputs['Surface'])
uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'PhotoUV'
geo = N.new('ShaderNodeNewGeometry')
a1 = N.new('ShaderNodeVertexColor'); a1.layer_name = 'm1'
a2 = N.new('ShaderNodeVertexColor'); a2.layer_name = 'm2'
sep = N.new('ShaderNodeSeparateColor'); L.new(a1.outputs['Color'], sep.inputs[0])
cmb = N.new('ShaderNodeCombineXYZ'); spu = N.new('ShaderNodeSeparateXYZ')
L.new(uvn.outputs[0], spu.inputs[0]); L.new(spu.outputs[0], cmb.inputs[0]); L.new(spu.outputs[1], cmb.inputs[1]); L.new(sep.outputs[2], cmb.inputs[2])
target = N.new('ShaderNodeTexImage'); N.active = target
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.cycles.device = 'CPU'
sc.render.bake.margin = 6
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active = body
RES = 2048
# solo se hornean las caras de la cabeza: el resto se oculta temporalmente moviéndolo a otro material sin imagen activa
nb_mat = bpy.data.materials.new('NoBake'); nb_mat.use_nodes = True; me.materials.append(nb_mat)
nbt = nb_mat.node_tree.nodes.new('ShaderNodeTexImage'); nbt.image = bpy.data.images.new('nb', 4, 4); nb_mat.node_tree.nodes.active = nbt
me.polygons.foreach_set('material_index', np.where(headfaces, 0, 1).astype(np.int32))
def bake(socket):
    for l in list(em.inputs[0].links): L.remove(l)
    L.new(socket, em.inputs[0])
    img = bpy.data.images.new('pass', RES, RES, float_buffer=True); img.colorspace_settings.name = 'Non-Color'
    target.image = img
    bpy.ops.object.bake(type='EMIT', use_clear=True)
    a = np.empty(RES * RES * 4, np.float32); img.pixels.foreach_get(a); return a.reshape(RES, RES, 4)
p_m1 = bake(a1.outputs['Color']); p_uv = bake(cmb.outputs[0]); p_pos = bake(geo.outputs['Position']); p_m2 = bake(a2.outputs['Color'])
cov = p_pos[..., 2] > 1.0
print('cobertura', cov.mean())

# ── 8. composición en numpy ──
def load(path):
    im = bpy.data.images.load(path); w, h = im.size; a = np.empty(w * h * im.channels, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, im.channels)[::-1]; return a
photo = load(D + 'foto_rgba.png'); person = load(D + 'foto_person.png')[..., 0]
def sample(img, px, py):
    h, w = img.shape[:2]; x = np.clip(px, 0, w - 1.001); y = np.clip(py, 0, h - 1.001)
    x0, y0 = x.astype(int), y.astype(int); fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    I = img if img.ndim == 3 else img[..., None]
    v = (I[y0, x0] * (1 - fx) * (1 - fy) + I[y0, x0 + 1] * fx * (1 - fy) + I[y0 + 1, x0] * (1 - fx) * fy + I[y0 + 1, x0 + 1] * fx * fy)
    inside = ((px >= 0) & (px < w - 1) & (py >= 0) & (py < h - 1))[..., None]
    return v * inside
u, v, fr = p_uv[..., 0], p_uv[..., 1], p_uv[..., 2]
px, py = u * W, (1 - v) * H
ph = sample(photo, px, py); per = sample(person, px, py)[..., 0]
GAIN = 1.33
phc = np.clip(ph[..., :3] * GAIN, 0, 1); a_face = ph[..., 3]
skin = np.array(fi['skin_srgb']) * 1.1; hairc = np.array(fi['hair_srgb']) * .95
field_t, eye_t, hair_t = p_m2[..., 0], p_m2[..., 1] > .5, p_m2[..., 2] > .5
P3 = p_pos[..., :3]
# pelo plano con mechones peinados hacia atrás (ruido según la posición)
streak = (np.sin(P3[..., 0] * 1400 + np.sin(P3[..., 1] * 90) * 2.5 + P3[..., 2] * 260) * .5 +
          np.sin(P3[..., 0] * 610 - P3[..., 2] * 120 + np.sin(P3[..., 1] * 40) * 4) * .5)
hair_flat = hairc[None, None] * (1 + .10 * streak[..., None])
# piel del cuerpo = la de la cara ya aclarada (mejillas y frente de frente), para que brazos y cara coincidan
sel_s = (a_face > .95) & (fr > .9) & (p_m2[..., 1] < .5) & (p_m1[..., 0] < .5)
lum_s = phc[sel_s].mean(-1)
pick = phc[sel_s][(lum_s > np.percentile(lum_s, 35)) & (lum_s < np.percentile(lum_s, 80))]
skin = np.median(pick, 0) * .97
print('piel desde la cara', np.round(skin, 3))
base = skin[None, None] * np.ones_like(phc)
s = smooth01((field_t - .35) / .3)[..., None]
col = base * (1 - s) + hair_flat * s
# cara de la foto
af = (a_face * fr)[..., None]
col = col * (1 - af) + phc * af
# pelo de la foto, de frente y dentro de la silueta, por encima del nacimiento
hyt = hair_y_at(px.ravel()).reshape(px.shape)
above = np.nan_to_num(smooth01((hyt + 2 - py) / 10) * smooth01((py - (hyt - 120)) / 40), nan=0)
lum = phc.mean(-1)
ah = (fr * per * above * smooth01((.42 - lum) / .12))[..., None]
col = col * (1 - ah) + phc * ah
# ojos procedurales
EC = {}
Vn = V
for sgn in (-1, 1):
    m = is_eye & (np.sign(Vn[:, 0]) == sgn); C = Vn[m].mean(0); rad = np.linalg.norm(Vn[m] - C, axis=1).max()
    # punto del ojo cuya proyección cae en el iris de la foto (de los que miran al frente)
    iris = min(fi['iris'], key=lambda ir: abs((ir['c'][0] - W / 2) - sgn * 1e9) if False else np.linalg.norm(photo_px(C[None])[0] - ir['c']))
    cand = np.nonzero(m & (front > .5))[0]
    k = cand[np.argmin(np.linalg.norm(pix[cand] - iris['c'], axis=1))]
    S = C + (Vn[k] - C) / np.linalg.norm(Vn[k] - C) * rad
    EC[sgn] = (C, rad, S)
print('ojos', {k: (np.round(v[0], 3).tolist(), round(v[1], 4)) for k, v in EC.items()})
iris_c = np.array([.25, .16, .11])
for sgn, (C, rad, S) in EC.items():
    m = eye_t & ((np.sign(P3[..., 0]) == sgn))
    d = np.linalg.norm(P3[m] - S, axis=1)
    ang = np.arctan2(P3[m][:, 2] - S[2], P3[m][:, 0] - S[0])
    sclera = np.array([.76, .72, .69]) * (1 - .3 * smooth01((d - .008) / .008))[:, None]
    sclera *= (1 - .35 * smooth01((P3[m][:, 2] - S[2] - .002) / .004))[:, None]     # sombra del párpado
    fib = (1 + .18 * np.sin(ang * 23) * np.sin(ang * 7 + 1))[:, None]
    ir = iris_c * fib * (.7 + .5 * smooth01(d / .0056))[:, None] * (1 - .6 * smooth01((d - .0045) / .0011))[:, None]
    pupil = np.array([.03, .025, .025])
    c = np.where((d < .0022)[:, None], pupil, np.where((d < .0056)[:, None], ir, sclera))
    col[m] = c
mo = (p_m1[..., 0] > .5)
col[mo] = np.array([.16, .07, .07])
col[~cov] = skin
img = bpy.data.images.new('CaraTex', RES, RES)
img.pixels.foreach_set(np.dstack([np.clip(col, 0, 1), np.ones((RES, RES))]).ravel().astype(np.float32))
img.filepath_raw = D + 'cara_tex.png'; img.file_format = 'PNG'; img.save()

# ── 9. materiales finales ──
def srgb2lin(c): return [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c]
me.materials.clear()
def textured(name, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
    b = nt.nodes['Principled BSDF']; nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough; return m
piel = bpy.data.materials.new('Piel'); piel.use_nodes = True
pb = piel.node_tree.nodes['Principled BSDF']; pb.inputs['Base Color'].default_value = (*srgb2lin(skin), 1); pb.inputs['Roughness'].default_value = .55
for m in (piel, textured('Cara', .55), textured('Pelo', .5), textured('Ojos', .12)): me.materials.append(m)
fi_eye = np.array([all(is_eye[i] for i in p.vertices) for p in me.polygons])
fi_hair = np.array([all(is_hair[i] for i in p.vertices) for p in me.polygons])
mi = np.where(fi_eye, 3, np.where(fi_hair, 2, np.where(headfaces, 1, 0)))
me.polygons.foreach_set('material_index', mi.astype(np.int32))
me.uv_layers.remove(me.uv_layers['PhotoUV'])
for a in list(me.color_attributes): me.color_attributes.remove(a)
img.pack()
json.dump({'chin': chin, 'brow': brow, 'nose': nose, 'zcut': ZCUT, 'cy': cy, 'top': TOP,
           'mouth': ((B[13] + B[14]) / 2).tolist(), 'mouth_l': B[61].tolist(), 'mouth_r': B[291].tolist()},
          open(D + 'head_info.json', 'w'))
sc.render.engine = 'BLENDER_EEVEE'
bpy.ops.wm.save_as_mainfile(filepath=D + 'head.blend')
print('OK cabeza', nV)
