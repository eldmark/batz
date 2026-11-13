"""Avatar realista de LOGOS: proporciones de adulto, cara desde la foto, mismo esqueleto y animaciones."""
import bpy, bmesh, math, json, os, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

D = os.path.dirname(os.path.abspath(__file__))
info = json.load(open(os.path.join(D, "face_info.json")))
exec(open(os.path.join(D, "avatar_helpers.py"), encoding="utf-8").read())   # ellipsoid, limb, torus, srgb, M…
rig = bpy.data.objects['AvatarRig']

# ── 0. fuera las mallas de caricatura ──
for name in ('Avatar', 'Avatar_src'):
    o = bpy.data.objects.get(name)
    if o: bpy.data.objects.remove(o, do_unlink=True)

# ── 1. esqueleto con proporciones de adulto (1,78 m), mismas direcciones de hueso ──
def along(head, direction, length):
    d = Vector(direction).normalized()
    return Vector(head) + d * length
BONES = {'hips': ((0, 0, .95), (0, 0, 1.07)), 'spine': ((0, 0, 1.07), (0, 0, 1.25)),
         'chest': ((0, 0, 1.25), (0, 0, 1.43)), 'neck': ((0, 0, 1.43), (0, 0, 1.53)),
         'head': ((0, 0, 1.53), (0, 0, 1.76))}
for s, sx in (('L', 1), ('R', -1)):
    sh = Vector((.18 * sx, 0, 1.40))
    el = along(sh, (.1 * sx, .005, -.225), .29)
    wr = along(el, (.07 * sx, -.02, -.22), .26)
    ht = along(wr, (.035 * sx, -.01, -.11), .17)
    hp = Vector((.10 * sx, 0, .95))
    kn = along(hp, (.01 * sx, -.005, -.36), .45)
    an = along(kn, (.005 * sx, .005, -.34), .42)
    to = along(an, (.005 * sx, -.15, -.08), .15)
    BONES.update({f'upper_arm.{s}': (sh, el), f'forearm.{s}': (el, wr), f'hand.{s}': (wr, ht),
                  f'thigh.{s}': (hp, kn), f'shin.{s}': (kn, an), f'foot.{s}': (an, to)})
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, (h, t) in BONES.items():
    eb = rig.data.edit_bones[name]
    roll = eb.roll
    eb.use_connect = False
    eb.head, eb.tail = Vector(h), Vector(t)
    eb.roll = roll
bpy.ops.object.mode_set(mode='OBJECT')
B = {n: (Vector(h), Vector(t)) for n, (h, t) in BONES.items()}

# ── 2. materiales ──
def color(mat, hexs, rough=.6):
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*srgb(hexs), 1)
    bsdf.inputs['Roughness'].default_value = rough
skin_hex = '#%02x%02x%02x' % tuple(round(c * 255 * .9) for c in info['skin_srgb'])  # la luz de la escena aclara la piel lisa
color(M['skin'], skin_hex, .55); color(M['shirt'], '#f1f1ec', .8); color(M['pants'], '#2a3347', .85)
color(M['shoe'], '#4a2e22', .45); color(M['belt'], '#3a281e', .5); color(M['hair'], '#2b1d16', .7)
cara = bpy.data.materials.get('Cara') or bpy.data.materials.new('Cara')
cara.use_nodes = True
nt = cara.node_tree; bsdf = nt.nodes.get('Principled BSDF')
img = bpy.data.images.load(os.path.join(D, 'cara.jpg'), check_existing=True); img.pack()
tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
bsdf.inputs['Roughness'].default_value = .55

parts = []
def keep(o): parts.append(o); return o

# ── 3. cuerpo ──
torso = [ellipsoid('pecho', (0, .008, 1.31), (.178, .105, .17), 'shirt', 'chest', seg=40, rings=24),
         ellipsoid('abdomen', (0, .014, 1.15), (.15, .09, .16), 'shirt', 'spine', seg=40, rings=24),
         torus('cuello_camisa', (0, .012, 1.482), .067, .019, 'shirt', 'chest', scale=(1, .95, 1.5))]
for s, sx in (('L', 1), ('R', -1)):
    torso.append(ellipsoid(f'hombro.{s}', (.165 * sx, .005, 1.40), (.075, .07, .062), 'shirt', 'chest'))
bpy.ops.object.select_all(action='DESELECT')
for o in torso: o.select_set(True)
bpy.context.view_layer.objects.active = torso[0]
bpy.ops.object.join(); shirt = torso[0]
for name, kw in (('r', {'mode': 'VOXEL', 'voxel_size': .007}), ('s', {'factor': .7, 'iterations': 8})):
    mod = shirt.modifiers.new(name, 'REMESH' if name == 'r' else 'SMOOTH')
    for k, v in kw.items(): setattr(mod, k, v)
    bpy.ops.object.modifier_apply(modifier=name)
for p in shirt.data.polygons: p.use_smooth = True
shirt.vertex_groups.clear()
gc, gs = shirt.vertex_groups.new(name='chest'), shirt.vertex_groups.new(name='spine')
for v in shirt.data.vertices:
    z = (shirt.matrix_world @ v.co).z
    w = min(1, max(0, (z - 1.17) / .12)); w = w * w * (3 - 2 * w)
    gc.add([v.index], w, 'REPLACE'); gs.add([v.index], 1 - w, 'REPLACE')
keep(shirt)
for s, sx in (('L', 1), ('R', -1)):
    sh, el = B[f'upper_arm.{s}']; _, wr = B[f'forearm.{s}']; _, ht = B[f'hand.{s}']
    keep(limb(f'brazo.{s}', sh, el, .052, .044, 'shirt', f'upper_arm.{s}'))
    cuff = el + (wr - el) * .9
    keep(limb(f'antebrazo.{s}', el, cuff, .044, .036, 'shirt', f'forearm.{s}'))
    keep(limb(f'muneca.{s}', cuff, wr, .028, .026, 'skin', f'forearm.{s}'))
    keep(limb(f'mano.{s}', wr, wr + (ht - wr) * .75, .03, .026, 'skin', f'hand.{s}'))
    thumb = wr + (ht - wr) * .25 + Vector((-.012 * sx, -.022, 0))
    keep(limb(f'pulgar.{s}', wr + (ht - wr) * .1 + Vector((0, -.012, 0)), thumb, .011, .009, 'skin', f'hand.{s}'))
    hp, kn = B[f'thigh.{s}']; _, an = B[f'shin.{s}']; _, to = B[f'foot.{s}']
    keep(limb(f'muslo.{s}', hp + Vector((0, 0, .02)), kn, .085, .058, 'pants', f'thigh.{s}'))
    keep(limb(f'pierna.{s}', kn, an + Vector((0, 0, .03)), .058, .045, 'pants', f'shin.{s}'))
    keep(ellipsoid(f'zapato.{s}', (an.x, -.045, .045), (.052, .125, .048), 'shoe', f'foot.{s}'))
keep(ellipsoid('cadera', (0, .01, .99), (.175, .11, .11), 'pants', 'hips', seg=32, rings=16))
keep(torus('cinturon', (0, .008, 1.045), .163, .013, 'belt', 'hips', scale=(1, .67, 1)))
keep(limb('cuello', (0, .012, 1.43), (0, .016, 1.60), .06, .055, 'skin', 'neck'))

# ── 4. cabeza: cráneo, cara de la foto, orejas y pelo ──
NOSE = Vector((0, -.104, 1.645))
skull = keep(ellipsoid('craneo', (0, .004, 1.662), (.077, .098, .118), 'skin', 'head', seg=96, rings=64))

# cara: malla de MediaPipe con UV de la foto
verts, uvs, faces = [], [], []
for line in open(os.path.join(D, 'face.obj')):
    p = line.split()
    if not p: continue
    if p[0] == 'v': verts.append(Vector(map(float, p[1:4])))
    elif p[0] == 'vt': uvs.append((float(p[1]), float(p[2])))
    elif p[0] == 'f': faces.append([int(x.split('/')[0]) - 1 for x in p[1:]])
offset = NOSE - verts[1]
me = bpy.data.meshes.new('Cara'); face = bpy.data.objects.new('Cara', me)
bpy.context.collection.objects.link(face)
me.from_pydata([v + offset for v in verts], [], faces)
uv = me.uv_layers.new(name='UVMap')
for poly in me.polygons:
    for li in poly.loop_indices:
        uv.data[li].uv = uvs[me.loops[li].vertex_index]
me.materials.append(cara)
for p in me.polygons: p.use_smooth = True
# orientación de las normales hacia afuera (hacia -Y)
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
if sum(f.normal.y for f in bm.faces) > 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
bm.to_mesh(me); bm.free()
INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
lip_y = sum(me.vertices[i].co.y for i in OUTER) / len(OUTER)
for i in INNER: me.vertices[i].co.y = lip_y + .003
vg = face.vertex_groups.new(name='head'); vg.add(range(len(me.vertices)), 1.0, 'REPLACE')
keep(face)

def bvh(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.transform(obj.matrix_world)
    tree = BVHTree.FromBMesh(bm); bm.free(); return tree
# el borde de la cara se apoya en el cráneo; el cráneo se esconde detrás de la cara
skull_tree = bvh(skull)
for i in info['ring']:                          # el faldón se apoya sobre el cráneo
    v = me.vertices[i]
    hit = skull_tree.ray_cast(Vector((v.co.x, -0.3, v.co.z)), Vector((0, 1, 0)))
    if v.co.z < NOSE.z - .05:                     # bajo la mandíbula: el faldón va hacia el cuello
        v.co.y = -.032 + abs(v.co.x) * .35; v.co.z = max(v.co.z - .006, 1.55); v.co.x *= .9
    elif hit[0] is not None:
        v.co.y = hit[0].y - .0008
    else:
        v.co.x *= .92; v.co.y = .0
face_tree = bvh(face)
mw = skull.matrix_world
cz = NOSE.z + (info['chin_z'] + info['forehead_z']) / 2
def under_face(w, k):
    probe = Vector((w.x * k, -0.3, cz + (w.z - cz) * k))
    return face_tree.ray_cast(probe, Vector((0, 1, 0)))[0] is not None
for part in (skull,):
    mw, mi = part.matrix_world, part.matrix_world.inverted()
    bm = bmesh.new(); bm.from_mesh(part.data); gone = []
    for v in bm.verts:
        w = mw @ v.co
        if w.y > .01: continue
        if under_face(w, 1.06): gone.append(v); continue
        hit = face_tree.ray_cast(Vector((w.x, -0.3, w.z)), Vector((0, 1, 0)))[0]
        if hit is not None and w.y < hit.y + .005:
            w.y = hit.y + .003; v.co = mi @ w
    bmesh.ops.delete(bm, geom=gone, context='VERTS'); bm.to_mesh(part.data); bm.free()
for s, sx in (('L', 1), ('R', -1)):
    keep(ellipsoid(f'oreja.{s}', (.079 * sx, .012, 1.648), (.012, .024, .033), 'skin', 'head', rot=(0, .25 * sx, 0)))
# pelo corto, raya de lado, entradas en las sienes
hair = ellipsoid('pelo', (0, .006, 1.674), (.083, .103, .124), 'hair', 'head', seg=64, rings=40)
front_z = NOSE.z + info['forehead_z'] - .006
bm = bmesh.new(); bm.from_mesh(hair.data)
gone, sunk = [], set()
for v in bm.verts:
    x, y, z = hair.matrix_world @ v.co
    if y < -.02:                                   # frente: línea del pelo con entradas
        limit = front_z + .028 * (abs(x) / .06) ** 2
    elif y < .05:                                  # lados: por encima de la oreja
        limit = 1.675 + .03 * (1 - (y + .02) / .07)
    else:                                          # nuca
        limit = 1.585
    t = min(1, max(0, (limit - z) / .012)); t = t * t * (3 - 2 * t)
    if t > 0: sunk.add(v.index)
    c = Vector((0, .006, 1.674))
    w = hair.matrix_world @ v.co
    v.co = hair.matrix_world.inverted() @ (c + (w - c) * (1 - .22 * t))
mi = hair.matrix_world.inverted()
for v in bm.verts:                                 # volumen arriba y adelante, peinado hacia atrás
    w = hair.matrix_world @ v.co
    lift = max(0, (w.z - 1.73) / .06) * max(0, 1 - (w.y + .1) / .2)
    w.z += .012 * lift; w.y -= .004 * lift
    v.co = mi @ w
gone = []
for v in bm.verts:
    w = hair.matrix_world @ v.co
    hit = face_tree.ray_cast(Vector((w.x, -0.3, w.z)), Vector((0, 1, 0)))[0]
    if v.index in sunk and hit is not None and w.y < hit.y + .006:
        c = Vector((0, .006, 1.674))
        v.co = hair.matrix_world.inverted() @ (c + (w - c) * .72)
bm.to_mesh(hair.data); bm.free()
hair_parts = [hair]
bpy.ops.object.select_all(action='DESELECT')
for o in hair_parts: o.select_set(True)
bpy.context.view_layer.objects.active = hair
bpy.ops.object.join()
sm = hair.modifiers.new('suave', 'SMOOTH'); sm.factor = .5; sm.iterations = 3
bpy.ops.object.modifier_apply(modifier='suave')
for p in hair.data.polygons: p.use_smooth = True
hair.vertex_groups.clear(); g = hair.vertex_groups.new(name='head'); g.add(range(len(hair.data.vertices)), 1.0, 'REPLACE')
keep(hair)

# ── 5. boca: formas para hablar, sobre los vértices de la cara ──
face.shape_key_add(name='Basis')
mouth = (me.vertices[13].co + me.vertices[14].co) / 2
opn = face.shape_key_add(name='Boca_abierta'); rnd = face.shape_key_add(name='Boca_redonda')
for v in me.vertices:
    rel = v.co - mouth
    dist = math.hypot(rel.x / 1.3, rel.z)
    if rel.z < .002:          # labio inferior y mentón bajan
        w = max(0., 1 - dist / .055) ** 1.2
        opn.data[v.index].co = v.co + Vector((0, .004 * w, -.013 * w))
    elif dist < .02:          # el labio superior sube un poco
        w = 1 - dist / .02
        opn.data[v.index].co = v.co + Vector((0, 0, .0025 * w))
    if dist < .045:           # redonda: comisuras hacia el centro y labios hacia adelante
        w = (1 - dist / .045) ** 1.1
        rnd.data[v.index].co = v.co + Vector((-rel.x * .32 * w, -.005 * w, -.004 * w * (rel.z < 0)))

# ── 6. una sola malla con el esqueleto ──
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:          # todas las piezas, también las tapas que crea limb()
    if o.type == 'MESH': o.select_set(True)
bpy.context.view_layer.objects.active = face
bpy.ops.object.join()
avatar = face; avatar.name = 'Avatar'; avatar.data.name = 'AvatarMesh'
avatar.parent = rig
arm = avatar.modifiers.new('Armature', 'ARMATURE'); arm.object = rig
for m in list(avatar.data.materials):
    pass
print('VERTS', len(avatar.data.vertices), 'SHAPEKEYS', [k.name for k in avatar.data.shape_keys.key_blocks])

# ── 7. cámara de revisión, guardar y exportar ──
out_blend, out_glb = sys.argv[sys.argv.index('--') + 1:sys.argv.index('--') + 3]
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
bpy.ops.object.select_all(action='DESELECT')
avatar.select_set(True); rig.select_set(True)
bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB', use_selection=True, export_yup=True,
                          export_animations=True, export_animation_mode='ACTIONS', export_skins=True,
                          export_morph=True, export_morph_normal=True, export_cameras=False,
                          export_lights=False, export_image_format='JPEG')
print('OK', out_glb, os.path.getsize(out_glb))
