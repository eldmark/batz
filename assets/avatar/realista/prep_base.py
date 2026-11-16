"""Base: cuerpo masculino realista (CC0, Blender Studio) a 1,78 m, centrado, con ojos; render frontal ortográfico de la cabeza."""
import bpy, sys, json, math, os
from mathutils import Vector
out = sys.argv[sys.argv.index('--') + 1]
keep = {'GEO-body_male_realistic', 'GEO-body_male_realistic.eye.L', 'GEO-body_male_realistic.eye.R'}
for o in list(bpy.data.objects):
    if o.name not in keep: bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections): bpy.data.collections.remove(c)
body = bpy.data.objects['GEO-body_male_realistic']
eyes = [bpy.data.objects['GEO-body_male_realistic.eye.L'], bpy.data.objects['GEO-body_male_realistic.eye.R']]
sc = bpy.context.scene
for o in [body] + eyes:
    if o.name not in sc.collection.objects: sc.collection.objects.link(o)
    print(o.name, 'parent', o.parent and o.parent.name, o.matrix_world.translation[:])
bpy.context.view_layer.objects.active = body
for m in list(body.modifiers):
    if m.type == 'MULTIRES': m.levels = 1
    bpy.ops.object.modifier_apply(modifier=m.name)
# todo en coordenadas de mundo, sin padres
for o in [body] + eyes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    o.data.transform(mw); o.matrix_world.identity()
zs = [v.co.z for v in body.data.vertices]
k = 1.78 / (max(zs) - min(zs)); x0 = body.location.x
cx = sum(v.co.x for v in body.data.vertices) / len(body.data.vertices)
for o in [body] + eyes:
    for v in o.data.vertices:
        v.co = Vector(((v.co.x - cx) * k, v.co.y * k, (v.co.z - min(zs)) * k))
body.name = 'Body'; eyes[0].name = 'Eye.L'; eyes[1].name = 'Eye.R'
print('verts', len(body.data.vertices), 'faces', len(body.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=out + 'base.blend')
# render frontal ortográfico de la cabeza
head = [v.co for v in body.data.vertices if v.co.z > 1.5]
top = max(v.z for v in head); cz = top - .13
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = .34
cam.location = (0, -1.5, cz); cam.rotation_euler = (math.radians(90), 0, 0)
for name, rot, e in (('K', (1.0, 0, -.5), 2.5), ('F', (1.2, 0, .6), 1.2)):
    l = bpy.data.objects.new(name, bpy.data.lights.new(name, 'SUN')); sc.collection.objects.link(l); l.rotation_euler = rot; l.data.energy = e
mat = bpy.data.materials.new('gris'); mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.62, .45, .36, 1)
body.data.materials.append(mat)
emat = bpy.data.materials.new('ojo'); emat.use_nodes = True
emat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.85, .85, .85, 1)
for e in eyes: e.data.materials.append(emat)
w = sc.world or bpy.data.worlds.new('W'); sc.world = w
w.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = sc.render.resolution_y = 1024
sc.render.filepath = out + 'base_front.png'; bpy.ops.render.render(write_still=True)
json.dump({'cz': cz, 'ortho': .34, 'res': 1024}, open(out + 'base_cam.json', 'w'))
