
import bpy, bmesh, math
from mathutils import Vector, Matrix
def srgb(hexs):
    h = hexs.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    return tuple(x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4 for x in c)
NAMES = {'skin':'Piel','hair':'Pelo','shirt':'Camisa','pants':'Pantalon','belt':'Cinturon','shoe':'Zapato','white':'OjoBlanco','pupil':'Pupila','mouth':'Boca','metal':'Hebilla','button':'Boton','teeth':'Dientes'}
M = {k: bpy.data.materials[v] for k, v in NAMES.items()}
def finish(obj, material, bone, smooth=True):
    obj.data.materials.append(M[material])
    vg = obj.vertex_groups.new(name=bone)
    vg.add(range(len(obj.data.vertices)), 1.0, 'REPLACE')
    if smooth:
        for p in obj.data.polygons: p.use_smooth = True
    return obj
def ellipsoid(name, loc, scale, material, bone, rot=(0, 0, 0), seg=24, rings=14):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale; o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return finish(o, material, bone)
def limb(name, a, b, r1, r2, material, bone, seg=20, caps=True):
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=seg, radius1=r1, radius2=r2, depth=d.length, location=(a+b)/2)
    o = bpy.context.object; o.name = name
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    finish(o, material, bone)
    if caps:
        ellipsoid(name+'_a', a, (r1,)*3, material, bone, seg=seg, rings=10)
        ellipsoid(name+'_b', b, (r2,)*3, material, bone, seg=seg, rings=10)
    return o
def torus(name, loc, major, minor, material, bone, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=28, minor_segments=10, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale; o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return finish(o, material, bone)
def box(name, loc, size, material, bone, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size; o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel:
        mod = o.modifiers.new('b', 'BEVEL'); mod.width = bevel; mod.segments = 3
        bpy.ops.object.modifier_apply(modifier='b')
    return finish(o, material, bone)
def bend(obj, axis, angle, deform_axis='Z'):
    """Curva una pieza con SimpleDeform y aplica."""
    mod = obj.modifiers.new('bend', 'SIMPLE_DEFORM'); mod.deform_method = 'BEND'
    mod.deform_axis = axis; mod.angle = angle
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier='bend')
    return obj
