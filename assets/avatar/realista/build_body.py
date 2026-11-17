"""Cuerpo: esqueleto de Bat’z ajustado a la malla, pesos automáticos, ropa (polo, pantalón, zapatos), boca y GLB.
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
# hombro: el brazo solo arrastra lo que está más allá de la articulación en la dirección del brazo; lo que queda
# encima (el techo del hombro) lo mueve el pecho. Sin clavícula, si no, al levantar el brazo se dobla y hace joroba.
for s_ in 'LR':
    jh = np.array(J[f'upper_arm.{s_}'][0], float); jt = np.array(J[f'upper_arm.{s_}'][1], float)
    dA = (jt - jh) / np.linalg.norm(jt - jh)
    tA = (V - jh) @ dA
    near_s = (np.linalg.norm(V - jh, axis=1) < .17) & ~fix
    gA = smooth01((tA + .015) / .055)
    ua = Wt[f'upper_arm.{s_}']; new_ua = np.where(near_s, ua * gA, ua); take = ua - new_ua
    Wt[f'upper_arm.{s_}'] = new_ua; Wt['chest'] = Wt['chest'] + take
    idx_s = np.nonzero(take > 1e-5)[0]
    for b in (f'upper_arm.{s_}', 'chest'):
        g = body.vertex_groups[b]
        for i in idx_s:
            if Wt[b][i] > 1e-4: g.add([int(i)], float(Wt[b][i]), 'REPLACE')
            else: g.remove([int(i)])
    print('hombro', s_, ': vértices que pasan al pecho', len(idx_s))

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
M_SHIRT = mat('Camisa', '#1f2a46', .85); M_PANTS = mat('Pantalon', '#3d4047', .92); M_SHOE = mat('Zapato', '#2e211b', .5)   # pantalón gris carbón: el caqui se confundía con la piel
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
# pantalón holgado de corte recto: cada pierna es un tubo redondo que cae derecho (no marca muslo, rodilla,
# pantorrilla ni entrepierna); arriba de la entrepierna se funde con la forma de la cadera
def loosen_pants(verts):
    zc = float(J['thigh.L'][0][2]) - .12                         # altura de la entrepierna
    def r_prof(zz): return np.interp(zz, [.1, .45, .7, zc], [.064, .07, .08, .088])
    def gsmooth(a, sig):
        k = np.exp(-np.arange(-3 * sig, 3 * sig + 1) ** 2 / (2 * sig * sig)); k /= k.sum()
        pad = np.pad(a, ((3 * sig, 3 * sig),) + ((0, 0),) * (a.ndim - 1), mode='edge')
        return np.stack([np.convolve(pad[:, j], k, 'valid') for j in range(a.shape[1])], 1) if a.ndim > 1 else np.convolve(pad, k, 'valid')
    for sx in (1, -1):
        vs = [v for v in verts if sx * v.co.x > 0 and v.co.z < zc + .08]
        sl = {}
        for v in vs: sl.setdefault(int(v.co.z / .01), []).append(v)
        keys = sorted(sl)
        if len(keys) < 5: continue
        C, Rraw = [], []
        for k in keys:
            P = np.array([v.co[:2] for v in sl[k]]); c = (P.min(0) + P.max(0)) / 2
            C.append(c); Rraw.append(np.linalg.norm(P - c, axis=1).max())
        C, Rraw = np.array(C), np.array(Rraw); zk = np.array(keys) * .01 + .005
        Cs = gsmooth(C, 3)
        R = np.maximum(gsmooth(Rraw, 5), np.maximum(Rraw + .003, r_prof(zk)))
        R = np.maximum(gsmooth(R, 2), Rraw + .003)
        for k, c, r, zz in zip(keys, Cs, R, zk):
            w = float(smooth01((zc + .03 - zz) / .06))           # 1 en las piernas; en la cadera manda su propia forma
            for v in sl[k]:
                d = Vector((v.co.x - c[0], v.co.y - c[1], 0))
                if d.length < 1e-6: continue
                d.normalize()
                nx, ny = c[0] + d.x * r, c[1] + d.y * r
                if sx * nx < .006: nx = sx * .006                  # no cruzar a la otra pierna (entrepierna)
                v.co.x = v.co.x + (nx - v.co.x) * w; v.co.y = v.co.y + (ny - v.co.y) * w
    # frente de la entrepierna: no sobresale del frente de los muslos (la piel de abajo ya se borra, nada la atraviesa)
    zs_ = np.arange(zc - .04, zc + .09, .01)
    for z0 in zs_:
        band = [v for v in verts if abs(v.co.z - z0) < .006]
        thigh = [v.co.y for v in band if .07 < abs(v.co.x) < .13]
        if not thigh: continue
        y_cap = min(thigh) + .006
        for v in band:
            if abs(v.co.x) < .075 and v.co.y < y_cap and v.normal.y < 0:
                k = float(smooth01((.075 - abs(v.co.x)) / .03)) * float(smooth01((zc + .1 - v.co.z) / .03))
                v.co.y = v.co.y + (y_cap - v.co.y) * k
    vs_set = set(verts)                                           # alisar un poco las costuras de las rebanadas
    for _ in range(3):
        new = {v: v.co * .6 + sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges) * .4
               for v in verts if all(e.other_vert(v) in vs_set for e in v.link_edges)}
        for v, c in new.items(): v.co = c
    print('pantalón holgado: entrepierna a', round(zc, 3))
loosen_pants(pv)
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

# dientes: dos bandas curvas detrás de los labios (arriba fijos a la cabeza; abajo giran con la mandíbula)
def Sh(q): return Vector(piv) + (Vector(q) - Vector(piv)) * 1.05
mcT = Sh(hi['mouth']); hwT = (Sh(hi['mouth_r']).x - Sh(hi['mouth_l']).x) / 2
M_TEETH = mat('Dientes', '#e6e0d4', .35, False)
head_i = body.vertex_groups['head'].index
lips_front = V[(np.abs(V[:, 2] - mcT.z) < .004) & (np.abs(V[:, 0] - mcT.x) < hwT)]
def front_y(x):
    near_ = lips_front[np.abs(lips_front[:, 0] - x) < .004]
    return float(near_[:, 1].min()) if len(near_) else float(lips_front[:, 1].min())
cols_x = np.linspace(-hwT * .78, hwT * .78, 13) + mcT.x
teeth_faces = []
for z_top, z_bot in ((mcT.z + .0085, mcT.z + .0009), (mcT.z - .0008, mcT.z - .0095)):   # en reposo quedan fuera de la ranura entre los labios
    grid = []
    for x in cols_x:
        k = abs(x - mcT.x) / (hwT * .78)
        yb = front_y(x) + .0135 + .004 * k * k                       # justo donde empieza la cavidad (los labios miden ~1,2 cm); la arcada se va hacia atrás en los lados
        col = []
        for zz in np.linspace(z_top, z_bot, 3):
            tv = bm.verts.new((x, yb + .0006 * (1 - abs(zz - (z_top + z_bot) / 2) / (abs(z_top - z_bot) / 2)), zz))
            tv[dl].clear(); tv[dl][head_i] = 1.0; col.append(tv)
        grid.append(col)
    for c in range(len(grid) - 1):
        for r in range(2):
            f = bm.faces.new((grid[c][r], grid[c + 1][r], grid[c + 1][r + 1], grid[c][r + 1])); f.material_index = M_TEETH; f.smooth = True
            teeth_faces.append(f)
for f in teeth_faces:                                              # que miren hacia afuera (hacia −y)
    f.normal_update()
    if f.normal.y > 0: f.normal_flip()
print('dientes: caras', len(teeth_faces))

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
# la cabeza se agrandó un 5 % alrededor de «piv»: la boca medida antes hay que llevarla a esas coordenadas
def Sh(q): return Vector(piv) + (Vector(q) - Vector(piv)) * 1.05
mc = Sh(hi['mouth']); ml, mr = Sh(hi['mouth_l']), Sh(hi['mouth_r'])
chin_s = float(piv[2] + (chin - piv[2]) * 1.05)
half_w = (mr.x - ml.x) / 2
body.shape_key_add(name='Basis')
opn = body.shape_key_add(name='Boca_abierta'); rnd = body.shape_key_add(name='Boca_redonda')
from mathutils import Matrix
pivot = Vector((0, mc.y + .075, mc.z + .018))          # bisagra de la mandíbula, detrás de la boca
rot = Matrix.Rotation(math.radians(10), 3, 'X')
# labio inferior por conectividad: desde el mentón hacia arriba, dentro de la boca y sin llegar a las comisuras
# (los labios de la malla están separados por la ranura de la boca; así se abren justo ahí)
Vm = np.array([v.co[:] for v in me.vertices])
adjm = [[] for _ in range(len(Vm))]
for e in me.edges:
    a_, b_ = e.vertices; adjm[a_].append(b_); adjm[b_].append(a_)
boxm = (np.abs(Vm[:, 0] - mc.x) < half_w * .85) & (np.abs(Vm[:, 2] - mc.z) < .022) & (Vm[:, 1] < mc.y + .022)
lower = None
cand = np.nonzero(boxm & (Vm[:, 2] < mc.z - .012) & (np.abs(Vm[:, 0] - mc.x) < .006))[0]
cand_up = np.nonzero(boxm & (Vm[:, 2] > mc.z + .007) & (np.abs(Vm[:, 0] - mc.x) < .006))[0]
if len(cand) and len(cand_up):
    seed = cand[np.argmin(Vm[cand, 1])]; up_seed = cand_up[np.argmin(Vm[cand_up, 1])]
    reg = np.zeros(len(Vm), bool); reg[seed] = True; stack = [seed]
    while stack:
        i = stack.pop()
        for j in adjm[i]:
            if boxm[j] and not reg[j]: reg[j] = True; stack.append(j)
    if not reg[up_seed]: lower = reg
    print('boca: labio inferior', int(reg.sum()), 'vértices;', 'separado del superior' if lower is not None else 'se filtra al superior (regla de altura)')
mt_i = [m.name for m in me.materials].index('Dientes_v2')
lower_teeth = {vi for poly in me.polygons if poly.material_index == mt_i and poly.center.z < mc.z for vi in poly.vertices}   # todo lo que está bajo la costura gira con la mandíbula
all_teeth = {vi for poly in me.polygons if poly.material_index == mt_i for vi in poly.vertices}
for v in me.vertices:
    p = v.co; i = v.index
    if p.z < chin_s - .06 or p.z > mc.z + .02 or abs(p.x - mc.x) > .085 or p.y > mc.y + .085: continue
    dx = abs(p.x - mc.x)
    lat = smooth01((.072 - dx) / .03)
    neck = smooth01((p.z - (chin_s - .045)) / .03)
    deep = smooth01((mc.z - .012 - p.z) / .01)                       # más abajo: mentón entero con la mandíbula
    jaw = smooth01((mc.z - .004 - p.z) / .006) * deep
    if i in lower_teeth:
        below = 1.0
    elif lower is not None and boxm[i]:
        lip = (1 - min(1.0, dx / (half_w * .95)) ** 2) ** .6 if lower[i] else 0.0   # la abertura se afina hacia las comisuras
        below = max(lip, jaw)
    elif lower is None:
        below = smooth01((mc.z - p.z) / .0015)                        # respaldo: corte nítido en la línea de la boca
    else:
        below = jaw
    w = float(lat * below * neck)
    if w > 0:
        q = pivot + rot @ (p - pivot)
        opn.data[i].co = p + (q - p) * w
    elif p.z > mc.z - .001 and p.z < mc.z + .015 and dx < half_w and not (lower is not None and lower[i]) and i not in all_teeth:   # el labio superior sube apenas (los dientes no)
        k = (1 - max(0.0, p.z - mc.z) / .015) * (1 - dx / half_w)
        opn.data[i].co = p + Vector((0, 0, .0055 * k))
    d = math.hypot((p.x - mc.x) / (half_w * 1.35), (p.z - mc.z) / .03)
    if d < 1 and p.y < mc.y + .02 and i not in all_teeth:   # redonda: comisuras al centro, labios adelante
        ww = (1 - d) ** 1.1
        rnd.data[i].co = p + Vector((-(p.x - mc.x) * .28 * ww, -.004 * ww, 0))
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
