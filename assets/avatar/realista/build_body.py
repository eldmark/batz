"""Cuerpo: esqueleto de LOGOS ajustado a la malla, pesos automáticos, ropa (polo, pantalón, zapatos), boca y GLB.
blender -b rig_src.blend --python build_body.py -- <dir>/ out.blend out.glb"""
import bpy, bmesh, json, sys, math, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index('--') + 1:]
BLINK_UP = 46
D, OUT_BLEND, OUT_GLB = argv[0], argv[1], argv[2]
hi = json.load(open(D + 'head_info.json'))
def smooth01(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

# ── 0. fuera las mallas viejas; entra el cuerpo nuevo ──
for o in list(bpy.data.objects):
    if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.materials):
    if m.users == 0: bpy.data.materials.remove(m)
with bpy.data.libraries.load(D + 'head.blend') as (src, dst): dst.objects = ['Body']
body = dst.objects[0]; bpy.context.scene.collection.objects.link(body)
rig = bpy.data.objects['AvatarRig']
me = body.data
V = np.array([v.co[:] for v in me.vertices])

# ── 1. articulaciones medidas en la malla ──
def center(z, xmin, xmax, side=1):
    s = V[(np.abs(V[:, 2] - z) < .012) & (side * V[:, 0] > xmin) & (side * V[:, 0] < xmax)]
    return np.array([side * (s[:, 0].min() + s[:, 0].max()) / 2 * side * side, (s[:, 1].min() + s[:, 1].max()) / 2, z]) if len(s) else None
J = {}
for s, sx in (('L', 1), ('R', -1)):
    def c(z, a, b):
        p = center(z, a, b, sx); p[0] = sx * abs(p[0]); return p
    sh = np.array([.178 * sx, -.005, 1.415])
    el = c(1.12, .24, .45); wr = c(.875, .3, .5)
    d = (wr - el) / np.linalg.norm(wr - el); ht = wr + d * .15 + np.array([0, -.01, 0])
    hip = np.array([.092 * sx, .0, .93]); kn = c(.49, .05, .25); an = c(.095, .1, .26)
    to = an + np.array([.01 * sx, -.14, -.07])
    J.update({f'upper_arm.{s}': (sh, el), f'forearm.{s}': (el, wr), f'hand.{s}': (wr, ht),
              f'thigh.{s}': (hip, kn), f'shin.{s}': (kn, an), f'foot.{s}': (an, to)})
chin = hi['chin']
J.update({'hips': ((0, .0, .93), (0, .0, 1.05)), 'spine': ((0, .0, 1.05), (0, .0, 1.22)),
          'chest': ((0, .0, 1.22), (0, .0, 1.43)), 'neck': ((0, .0, 1.43), (0, -.005, chin - .005)),
          'head': ((0, -.005, chin - .005), (0, -.005, hi['top'] + .01))})
for k, (a, b) in J.items(): print(k, np.round(a, 3).tolist(), np.round(b, 3).tolist())
bpy.context.view_layer.objects.active = rig; rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t) in J.items():
    eb = rig.data.edit_bones[name]; roll = eb.roll
    eb.use_connect = False; eb.head, eb.tail = Vector(h), Vector(t); eb.roll = roll
bpy.ops.object.mode_set(mode='OBJECT')

# ── 2. pesos automáticos (calor) ──
for g in list(body.vertex_groups):
    if g.name not in ('EYES', 'HAIR'): body.vertex_groups.remove(g)
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
bones = [b.name for b in rig.data.bones]
gidx = {g.index: g.name for g in body.vertex_groups}
Wt = {b: np.zeros(len(V)) for b in bones}
for v in me.vertices:
    for g in v.groups:
        n = gidx[g.group]
        if n in Wt: Wt[n][v.index] = g.weight
tot = sum(Wt.values())
print('sin peso', int((tot < 1e-3).sum()), 'de', len(V))
def gm(name):
    g = body.vertex_groups.get(name); return np.array([any(x.group == g.index and x.weight > .5 for x in v.groups) for v in me.vertices]) if g else np.zeros(len(V), bool)
is_eye, is_hair = gm('EYES'), gm('HAIR')
rigid_head = is_eye | is_hair | (V[:, 2] > chin + .03) & (np.abs(V[:, 0]) < .12)
fix = rigid_head | (tot < 1e-3) & (V[:, 2] > 1.4)
for b in bones:
    g = body.vertex_groups[b]; idx = np.nonzero(fix)[0].tolist()
    if b == 'head': g.add(idx, 1.0, 'REPLACE')
    else: g.remove(idx)
for b in bones: Wt[b][fix] = 1.0 if b == 'head' else 0.0
# la cabeza entera (mandíbula, boca por dentro) va rígida con el hueso «head»; transición suave hacia el cuello
tb = smooth01((V[:, 2] - (chin - .06)) / .045) * (np.abs(V[:, 0]) < .13) * (V[:, 1] < .09)
blend = np.nonzero((tb > 0) & ~fix)[0]
for b in bones:
    Wt[b][blend] = Wt[b][blend] * (1 - tb[blend]) + (tb[blend] if b == 'head' else 0)
for b in bones:
    g = body.vertex_groups[b]
    for i in blend:
        if Wt[b][i] > 1e-4: g.add([int(i)], float(Wt[b][i]), 'REPLACE')
        else: g.remove([int(i)])
# hombros: cerca del cuello la parte de arriba del hombro la mueve el pecho, no el brazo
# (sin clavícula, al levantar los brazos el escote se estiraba hacia arriba y asomaba piel)
fneck = smooth01((.16 - np.abs(V[:, 0])) / .05) * smooth01((V[:, 2] - 1.36) / .04) * (1 - fix)
for s_ in 'LR':
    take = Wt[f'upper_arm.{s_}'] * fneck; Wt[f'upper_arm.{s_}'] -= take; Wt['chest'] += take
idx_m = np.nonzero(fneck > 0)[0]
for b in bones:
    g = body.vertex_groups[b]
    for i in idx_m:
        if Wt[b][i] > 1e-4: g.add([int(i)], float(Wt[b][i]), 'REPLACE')
        else: g.remove([int(i)])
print('hombros: vértices con peso movido al pecho', len(idx_m))

# cabeza 5 % más grande respecto al cuerpo (escala por el peso del hueso «head», alrededor de la base del cráneo)
piv = np.array(J['head'][0], float)
wh = Wt['head']
Vs = piv + (V - piv) * (1 + .05 * wh)[:, None]
me.vertices.foreach_set('co', Vs.ravel()); me.update()
V = Vs
# ── 3. ropa: copias desplazadas de la piel (heredan los pesos) ──
def along(bone, P):
    h, t = map(np.array, J[bone]); d = t - h; return ((P - h) @ d) / (d @ d)
z = V[:, 2]; y = V[:, 1]; x = V[:, 0]
front = smooth01((-.01 - y) / .05)
collar_z = 1.478 - .028 * front - .028 * front * np.exp(-(x / .022) ** 2)
torso_w = Wt['hips'] + Wt['spine'] + Wt['chest'] + Wt['neck']
arm_up = Wt['upper_arm.L'] + Wt['upper_arm.R']
arm_lo = Wt['forearm.L'] + Wt['forearm.R'] + Wt['hand.L'] + Wt['hand.R']
legs = sum(Wt[f'{b}.{s}'] for b in ('thigh', 'shin') for s in 'LR')
feet = Wt['foot.L'] + Wt['foot.R']
t_arm = np.maximum(along('upper_arm.L', V) * (x > 0), along('upper_arm.R', V) * (x < 0))
rad = np.hypot(x / 1.0, (y + .012) / 1.12)
neck_hole = (rad < .068) & (z > 1.458 + .02 * smooth01((y + .01) / .06))   # cuello redondo de hombre
SHIRT = (z > .86) & ~neck_hole & (z < 1.56) & (arm_lo < .35) & ~rigid_head & (Wt['head'] < .4) & ((arm_up < .5) | (t_arm < .66))
PANTS = (z < .975) & (z > .1) & (arm_lo < .3) & (arm_up < .3) & (torso_w + legs > .5)
SHOES = (z < .115) & (legs + feet > .5)
PANTS &= ~SHOES
print('camisa', SHIRT.sum(), 'pantalón', PANTS.sum(), 'zapatos', SHOES.sum())

skin_bm = bmesh.new(); skin_bm.from_mesh(me); tree = BVHTree.FromBMesh(skin_bm); skin_bm.free()
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
mat_names = [m.name for m in me.materials]
def mat(name, hexs, rough, double=True):
    m = bpy.data.materials.get(name + '_v2') or bpy.data.materials.new(name + '_v2'); m.use_nodes = True
    h = hexs.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c]
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = rough
    m.use_backface_culling = not double
    if m.name not in [x.name for x in me.materials]: me.materials.append(m)
    return [x.name for x in me.materials].index(m.name)
M_SHIRT = mat('Camisa', '#1f2a46', .85); M_PANTS = mat('Pantalon', '#9c8763', .9); M_SHOE = mat('Zapato', '#2e211b', .5)
M_BTN = mat('Boton', '#151b2c', .4, False)

COVERED = np.zeros(len(V), bool)
def garment(sel, mat_i, offset_fn, smooth_iter, name):
    bm.verts.index_update(); bm.faces.ensure_lookup_table()
    faces = {f for f in bm.faces if all(v.index < len(sel) and sel[v.index] for v in f.verts)}
    for _ in range(6):                      # fuera las caras que sobresalen del borde (puntas)
        drop = {f for f in faces if sum(1 for e in f.edges if not any(g in faces for g in e.link_faces if g is not f)) >= 2}
        if not drop: break
        faces -= drop
    faces = list(faces)
    for f in faces:
        for v in f.verts: COVERED[v.index] = True
    ret = bmesh.ops.duplicate(bm, geom=faces)
    nf = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMFace)]
    nv = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMVert)]
    for f in nf: f.material_index = mat_i; f.smooth = True
    bnd = {v for v in nv if any(e.is_boundary for e in v.link_edges)}
    # suavizar (quita músculos), luego empujar afuera de la piel
    def relax(iters):
        for _ in range(iters):
            new = {}
            for v in nv:
                if v in bnd:
                    nbs = [e.other_vert(v).co for e in v.link_edges if e.is_boundary]
                    if len(nbs) == 2: new[v] = v.co * .5 + (nbs[0] + nbs[1]) * .25
                else:
                    nbs = [e.other_vert(v).co for e in v.link_edges]
                    new[v] = v.co * .4 + sum(nbs, Vector()) / len(nbs) * .6
            for v, c in new.items(): v.co = c
    def push(scale):
        for v in nv:
            loc, n, _, _ = tree.find_nearest(v.co)
            off = offset_fn(v.co) * scale
            s = (v.co - loc).dot(n)
            if s < off: v.co = v.co + n * (off - s)
    relax(smooth_iter); push(1.6); push(1.6)
    relax(smooth_iter // 2); push(1.0); push(1.0)
    def loop_step(lam):
        new = {}
        for v in bnd:
            nbs = [e.other_vert(v).co for e in v.link_edges if e.is_boundary]
            if len(nbs) == 2: new[v] = v.co + ((nbs[0] + nbs[1]) * .5 - v.co) * lam
        for v, c in new.items(): v.co = c
    for _ in range(30):                      # bordes sin dientes de sierra; Taubin: no encoge el aro (el escote no se aplana)
        loop_step(.5); loop_step(-.53)
    push(.8)
    print(name, len(nv), 'vértices')
    return nv, nf, bnd

def shirt_off(p):
    hem = smooth01((1.06 - p.z) / .15); loose = .008 + .005 * hem          # ruedo recto, sin forma de A
    sl = 0.0
    for s, sx in (('L', 1), ('R', -1)):
        if p.x * sx > .15: t = along(f'upper_arm.{s}', np.array(p[:])); sl = max(sl, smooth01((t + .1) / .3))
    return loose + .006 * sl                                            # manga recta, sin abombar el hombro
sv, sf, sb = garment(SHIRT, M_SHIRT, shirt_off, 30, 'camisa')
# la tela cuelga: bajo el pecho no se mete hacia el cuerpo y la cintura no se angosta (torso de hombre, no reloj de arena)
def drape(verts, axis, sign, bins_axis, sel, slope):
    cols = {}
    for v in verts:
        if sel(v): cols.setdefault(round(v.co[bins_axis] / .012), []).append(v)
    for vs in cols.values():
        vs.sort(key=lambda v: -v.co.z)
        env, zprev = None, None
        for v in vs:
            val = sign * v.co[axis]
            if env is not None:
                lim = env - slope * (zprev - v.co.z)
                if val < lim: v.co[axis] = sign * lim; val = lim
            env = val if env is None else max(val, env - slope * (zprev - v.co.z)); zprev = v.co.z
torso = [v for v in sv if v.co.z < 1.36 and v.co.z > .86 and abs(v.co.x) < .2]
drape(torso, 1, -1, 0, lambda v: v.normal.y < -.35, .22)                  # frente: cae desde el pecho
for sx in (1, -1):
    drape(torso, 0, sx, 1, lambda v, sx=sx: sx * v.normal.x > .45 and sx * v.co.x > .08, .12)   # costados: casi rectos
for _ in range(6):
    new = {v: v.co * .5 + sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges) * .5 for v in torso if v not in sb}
    for v, c in new.items(): v.co = c
pv, pf, pb = garment(PANTS, M_PANTS, lambda p: .008 + .005 * smooth01((.6 - p.z) / .4), 40, 'pantalón')
fv, ff, fb = garment(SHOES, M_SHOE, lambda p: .007, 8, 'zapatos')

# cuello redondo con ribete: banda que sube del borde del escote y abraza el cuello
dl = bm.verts.layers.deform.verify()
sv_set = set(sv)
bedges = [e for e in bm.edges if e.is_boundary and e.verts[0] in sv_set and e.verts[1] in sv_set]
adj = {}
for e in bedges:
    a_, b_ = e.verts; adj.setdefault(a_, []).append(b_); adj.setdefault(b_, []).append(a_)
loops, seen = [], set()
for st in adj:
    if st in seen: continue
    lp = [st]; seen.add(st); prev, cur = None, st
    while True:
        nx = [w for w in adj[cur] if w is not prev and w not in seen]
        if not nx: break
        prev, cur = cur, nx[0]; lp.append(cur); seen.add(cur)
    loops.append(lp)
neck_loop = max(loops, key=lambda lp: np.mean([v.co.z for v in lp]))
print('escote: lazos', len(loops), 'vértices', len(neck_loop), 'z media', round(float(np.mean([v.co.z for v in neck_loop])), 3),
      'z min/max', round(min(v.co.z for v in neck_loop), 3), round(max(v.co.z for v in neck_loop), 3))
ringv = V[(np.abs(V[:, 2] - 1.49) < .006) & (np.hypot(V[:, 0], V[:, 1] + .01) < .1)]
ncx, ncy = float(ringv[:, 0].mean()), float(ringv[:, 1].mean())
M_RIB = mat('Cuello', '#19223b', .9)
bone_names = list(Wt.keys())
gi_of = {bn: body.vertex_groups[bn].index for bn in bone_names}
def skin_weights(pt):
    loc, nrm, fi, dist = tree.find_nearest(pt)
    vs = me.polygons[fi].vertices
    return {bn: float(np.mean([Wt[bn][i] for i in vs])) for bn in bone_names}
def set_w(v, wd):
    v[dl].clear(); tot_ = sum(wd.values()) or 1.0
    for bn, w in wd.items():
        if w > 1e-3: v[dl][gi_of[bn]] = w / tot_
# cada vértice de ropa toma los pesos de la piel que tiene justo debajo (tras alisar y colgar la tela,
# el vértice de origen puede quedar a 1–2 cm y se movería distinto: asomaba piel al levantar los brazos)
def transfer_weights(verts):
    for v in verts:
        loc, nrm, fi, dist = tree.find_nearest(v.co)
        vs = list(me.polygons[fi].vertices)
        dd = np.linalg.norm(V[vs] - np.array(loc[:]), axis=1); wv = 1 / (dd + 1e-5); wv /= wv.sum()
        set_w(v, {bn: float(sum(Wt[bn][i] * w for i, w in zip(vs, wv))) for bn in bone_names})
for grp in (sv, pv, fv): transfer_weights(grp)
up = Vector((0, 0, 1)); rows = []
for bv in neck_loop:
    rh = Vector((bv.co.x - ncx, bv.co.y - ncy, 0)); rh = rh.normalized() if rh.length > 1e-6 else Vector((0, -1, 0))
    zt = bv.co.z + .015
    hit = tree.ray_cast(Vector((ncx, ncy, zt)), rh, .2)
    top = (hit[0] + rh * .0035) if hit[0] is not None else (bv.co + up * .012 - rh * .008)
    wb = {bn: bv[dl].get(gi_of[bn], 0.0) for bn in bone_names}
    wt_ = skin_weights(top)
    row = [bv]
    for p_, t_ in ((bv.co + (top - bv.co) * .5 + rh * .0025, .5), (top, 1.), (top + up * .003 - rh * .003, 1.)):
        nv_ = bm.verts.new(p_); set_w(nv_, {bn: wb[bn] * (1 - t_) + wt_[bn] * t_ for bn in bone_names}); row.append(nv_)
    rows.append(row)
closed = any(e.other_vert(neck_loop[0]) is neck_loop[-1] for e in neck_loop[0].link_edges)
band = []
for i in range(len(rows) if closed else len(rows) - 1):
    ra_, rb_ = rows[i], rows[(i + 1) % len(rows)]
    for k in range(3):
        f = bm.faces.new((ra_[k], rb_[k], rb_[k + 1], ra_[k + 1])); f.material_index = M_RIB; f.smooth = True; band.append(f)
bmesh.ops.recalc_face_normals(bm, faces=band)
print('ribete: caras', len(band), 'cerrado', closed)

# piel tapada por la ropa: fuera (se deja un anillo bajo los bordes)
cov = COVERED.copy()
core = cov.copy()
for _ in range(7):
    grow = core.copy()
    for e in me.edges:
        a, b = e.vertices
        if not cov[a] or not cov[b]: grow[a] = grow[b] = False
    core = grow
nskin = len(V)
bm.verts.index_update(); bm.verts.ensure_lookup_table(); bm.normal_update()
# la piel que queda bajo los bordes de la ropa se mete 4 mm: al levantar los brazos ya no atraviesa la tela
for i in np.nonzero(cov & ~core)[0]:
    bv_ = bm.verts[int(i)]; bv_.co -= bv_.normal * .004
dead = [f for f in bm.faces if all(v.index < nskin and core[v.index] for v in f.verts)]
bmesh.ops.delete(bm, geom=dead, context='FACES')
bm.to_mesh(me); bm.free(); me.update()
print('vértices finales', len(me.vertices))

for m in me.materials:
    if m and m.name.startswith('Pelo'): m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .82
# ── 4. boca: formas para hablar ──
mc = Vector(hi['mouth']); ml, mr = Vector(hi['mouth_l']), Vector(hi['mouth_r'])
half_w = (mr.x - ml.x) / 2
body.shape_key_add(name='Basis')
opn = body.shape_key_add(name='Boca_abierta'); rnd = body.shape_key_add(name='Boca_redonda')
from mathutils import Matrix
pivot = Vector((0, mc.y + .075, mc.z + .018))          # bisagra de la mandíbula, detrás de la boca
rot = Matrix.Rotation(math.radians(9), 3, 'X')
for v in me.vertices:
    p = v.co
    if p.z < chin - .06 or p.z > mc.z + .02 or abs(p.x - mc.x) > .085 or p.y > mc.y + .085: continue
    lat = smooth01((.072 - abs(p.x - mc.x)) / .03)
    below = smooth01((mc.z + .0006 - p.z) / .0035)
    neck = smooth01((p.z - (chin - .045)) / .03)
    w = float(lat * below * neck)
    if w > 0:
        q = pivot + rot @ (p - pivot)
        opn.data[v.index].co = p + (q - p) * w
    elif p.z > mc.z and p.z < mc.z + .015 and abs(p.x - mc.x) < half_w:   # el labio superior sube apenas
        k = (1 - (p.z - mc.z) / .015) * (1 - abs(p.x - mc.x) / half_w)
        opn.data[v.index].co = p + Vector((0, 0, .0018 * k))
    d = math.hypot((p.x - mc.x) / (half_w * 1.35), (p.z - mc.z) / .03)
    if d < 1 and p.y < mc.y + .02:                 # redonda: comisuras al centro, labios adelante
        ww = (1 - d) ** 1.1
        rnd.data[v.index].co = p + Vector((-(p.x - mc.x) * .28 * ww, -.004 * ww, 0))
# parpadeo: los párpados giran alrededor del centro del ojo (no atraviesan el globo). El ángulo sale de los
# bordes de los párpados medidos en la foto (MediaPipe 159/145 y 386/374), llevados a la cabeza ya escalada.
blk = body.shape_key_add(name='Parpadeo', from_mix=False)
Vc = np.array([v.co[:] for v in me.vertices]); is_eye = gm('EYES'); is_hair = gm('HAIR'); nsk = len(Vc)
LM = np.array(json.load(open(D + 'fit_lm.json'))['B'])
LMh = piv + (LM - piv) * 1.05
for sx in (1, -1):
    em_ = np.nonzero(is_eye & (np.sign(Vc[:, 0]) == sx))[0]
    C = Vc[em_].mean(0); R = float(np.linalg.norm(Vc[em_] - C, axis=1).max())
    up_i, lo_i = min(((159, 145), (386, 374)), key=lambda pr: abs(LMh[pr[0], 0] - C[0]))
    ang_of = lambda q: math.atan2(q[2] - C[2], -(q[1] - C[1]))            # 0 = de frente, + = hacia arriba
    total = ang_of(LMh[up_i]) - ang_of(LMh[lo_i]) + math.radians(11)       # cerrar del todo, con traslape
    a_up, a_lo = .88 * total, .12 * total
    near = np.nonzero((np.linalg.norm(Vc - C, axis=1) < R + .016) & ~is_eye & ~is_hair)[0]
    zc_margin = C[2]
    for i in near:
        p = Vc[i] - C; d = float(np.linalg.norm(p))
        if p[1] > R * .45: continue                                        # solo la parte delantera
        lat = float(smooth01((R * 1.2 - abs(p[0])) / (R * .55)))           # en las comisuras casi no se mueve
        on_lid = float(smooth01((R + .0115 - d) / .007))                   # sobre el globo = párpado; el pliegue se queda
        if p[2] >= 0:
            ang = a_up * on_lid * lat * float(smooth01((p[2] + .001) / .002))
        else:
            ang = -a_lo * float(smooth01((R + .007 - d) / .005)) * lat
        if abs(ang) < 1e-5: continue
        ca, sa = math.cos(ang), math.sin(ang)
        blk.data[i].co = Vector((C[0] + p[0], C[1] + p[1] * ca - p[2] * sa, C[2] + p[1] * sa + p[2] * ca))
    print('parpadeo ojo', sx, 'radio', round(R, 4), 'cierre (grados)', round(math.degrees(total), 1), 'vértices', len(near))
for k in me.shape_keys.key_blocks: k.value = 0.0
body.active_shape_key_index = 0

# ── 5. guardar y exportar ──
body.name = 'Avatar'; me.name = 'AvatarMesh'
for g in ('EYES', 'HAIR'):
    if body.vertex_groups.get(g): body.vertex_groups.remove(body.vertex_groups[g])
rig.data.pose_position = 'POSE'
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); rig.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, export_yup=True,
                          export_animations=True, export_animation_mode='ACTIONS', export_skins=True,
                          export_morph=True, export_morph_normal=True, export_cameras=False,
                          export_lights=False, export_image_format='JPEG', export_jpeg_quality=88)
import os; print('OK', OUT_GLB, os.path.getsize(OUT_GLB))
