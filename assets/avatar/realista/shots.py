"""Renders de control: shots(prefix, [(nombre, objetivo, distancia, yaw)]) con cámara y luces propias."""
import bpy, math
from mathutils import Vector
def setup(bg=(.2, .22, .24)):
    sc = bpy.context.scene
    cam = bpy.data.objects.get('ShotCam')
    if not cam:
        cam = bpy.data.objects.new('ShotCam', bpy.data.cameras.new('ShotCam')); sc.collection.objects.link(cam)
        for name, rot, e in (('ShotKey', (.95, 0, -.6), 3.0), ('ShotFill', (1.3, 0, .9), 1.0), ('ShotRim', (1.9, 0, 3.0), 1.5)):
            l = bpy.data.objects.new(name, bpy.data.lights.new(name, 'SUN')); sc.collection.objects.link(l); l.rotation_euler = rot; l.data.energy = e
    sc.camera = cam
    w = sc.world or bpy.data.worlds.new('W'); sc.world = w
    bgn = w.node_tree.nodes['Background']; bgn.inputs['Color'].default_value = (*bg, 1); bgn.inputs['Strength'].default_value = .7
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 640, 800
    sc.view_settings.view_transform = 'Standard'
    return cam
def shots(prefix, specs, lens=85):
    cam = setup(); cam.data.lens = lens; sc = bpy.context.scene
    for name, target, dist, yaw in specs:
        t = Vector(target); cam.location = t + Vector((math.sin(yaw), -math.cos(yaw), 0)) * dist
        cam.rotation_euler = (math.radians(90), 0, yaw)
        sc.render.filepath = prefix + name; bpy.ops.render.render(write_still=True)
