"""Run inside Blender (blender --background --python blender_open.py -- <obj> <out.blend> [renders_dir]):
imports an M13 vehicle OBJ (+MTL with the game textures), tidies the materials and saves a .blend; optional preview
renders. An OBJ that carries vertex normals (the M3 Lee export) keeps them (smooth castings, flat plates); one without
(the SU-122 export) is shaded flat like the game."""
import bpy, sys, os, math, mathutils
argv = sys.argv[sys.argv.index('--') + 1:]
obj, out = argv[0], argv[1]; rdir = argv[2] if len(argv) > 2 else None
has_normals = any(line.startswith('vn ') for line in open(obj, errors='ignore'))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=obj, forward_axis='NEGATIVE_Z', up_axis='Y')
for o in bpy.context.scene.objects:
    o.select_set(True)
    for slot in o.material_slots:
        m = slot.material
        if m and m.use_nodes:
            bsdf = m.node_tree.nodes.get('Principled BSDF')
            if bsdf: bsdf.inputs['Roughness'].default_value = 0.85
if not has_normals: bpy.ops.object.shade_flat()
scn = bpy.context.scene
world = bpy.data.worlds.new('w'); scn.world = world; world.color = (0.55, 0.57, 0.6)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scn.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(35)); sun.data.energy = 4
bpy.ops.wm.save_as_mainfile(filepath=out)
print('saved', out)
if rdir:
    os.makedirs(rdir, exist_ok=True); stem = os.path.splitext(os.path.basename(obj))[0]
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 8.0
    scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.light = 'STUDIO'; scn.display.shading.color_type = 'TEXTURE'
    scn.render.resolution_x = 1600; scn.render.resolution_y = 1000
    for name, (az, el) in {'side': (90, 0), 'front34': (35, 25), 'rear34': (-145, 25), 'top': (0, 89)}.items():
        a, e = math.radians(az), math.radians(el); r = 20
        cam.location = (r * math.sin(a) * math.cos(e), -r * math.cos(a) * math.cos(e), r * math.sin(e) + 0.3)
        cam.rotation_euler = mathutils.Vector(-cam.location).to_track_quat('-Z', 'Y').to_euler()
        scn.render.filepath = os.path.join(rdir, '%s_%s.png' % (stem, name)); bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
