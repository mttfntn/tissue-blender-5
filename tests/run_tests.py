# SPDX-FileCopyrightText: 2026 Alessandro Zomparelli
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Smoke tests for Tissue, run inside Blender without a window:
#
#   blender --background --factory-startup --python tests/run_tests.py
#
# Every test builds a small scene, runs one Tissue tool and checks its result.
# The script exits with code 1 if any test fails, so CI marks the run as failed.

import math
import os
import shutil
import sys
import tempfile
import traceback

import addon_utils
import bmesh
import bpy
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TESTS = []


def test(func):
    TESTS.append(func)
    return func


def enable_tissue():
    # Copy the add-on into a folder called "tissue" so it imports under its own
    # name wherever the repository is checked out.
    root = tempfile.mkdtemp(prefix="tissue_tests_")
    shutil.copytree(REPO, os.path.join(root, "tissue"),
                    ignore=shutil.ignore_patterns(".git", "docs", "tests", "__pycache__"))
    sys.path.insert(0, root)
    addon_utils.enable("tissue", default_set=True, handle_error=None)
    if "tissue" not in bpy.context.preferences.addons:
        raise RuntimeError("Tissue could not be enabled")


def reset_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.curves,
                       bpy.data.materials, bpy.data.lattices, bpy.data.textures):
        bpy.data.batch_remove(list(collection))


def select_only(*objects, active=None):
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = active or objects[-1]


def add_grid(size=4):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=size + 1, y_subdivisions=size + 1, size=2)
    return bpy.context.object


def add_cube(size=0.5, location=(0, 0, 3)):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    return bpy.context.object


def add_icosphere(subdivisions=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions)
    return bpy.context.object


def add_weight(ob, name="Weight"):
    # A vertex group going from 0 to 1 along X.
    group = ob.vertex_groups.new(name=name)
    xs = [v.co.x for v in ob.data.vertices]
    lo, hi = min(xs), max(xs)
    for v in ob.data.vertices:
        group.add([v.index], (v.co.x - lo) / (hi - lo), 'REPLACE')
    ob.vertex_groups.active_index = group.index
    return group


def weights(ob, group):
    values = []
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == group.index:
                values.append(g.weight)
    return values


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def check_finished(result, name):
    check(result == {'FINISHED'}, f"{name} returned {result}")


def check_weights(ob, group):
    values = weights(ob, group)
    check(values, f"vertex group '{group.name}' is empty")
    check(all(0 <= w <= 1 for w in values), f"vertex group '{group.name}' has weights outside 0-1")


def new_group(ob, before):
    added = [g for g in ob.vertex_groups if g.name not in before]
    check(added, "no vertex group was created")
    return added[-1]


# --- Tissue Tools -------------------------------------------------------------


def tessellate(fill_mode, prepare=None):
    base = add_grid()
    if prepare:
        prepare(base)
    component = add_cube()
    select_only(component, base, active=base)
    result = bpy.ops.object.tissue_tessellate(
        generator=base.name, component=component.name, fill_mode=fill_mode)
    check_finished(result, f"Tessellate ({fill_mode})")
    out = bpy.context.object
    check(out not in (base, component), "no tessellated object was created")
    check(out.tissue.tissue_type == 'TESSELLATE', "result is not marked as a tessellation")
    check(len(out.data.polygons) > 0, "tessellation is empty")
    return base, component, out


@test
def tessellate_quad():
    base, component, out = tessellate('QUAD')
    expected = len(base.data.polygons) * len(component.data.polygons)
    check(len(out.data.polygons) == expected,
          f"expected {expected} faces, got {len(out.data.polygons)}")


@test
def tessellate_tri():
    tessellate('TRI')


@test
def tessellate_fan():
    tessellate('FAN')


@test
def tessellate_frame():
    tessellate('FRAME')


@test
def tessellate_patch():
    tessellate('PATCH', prepare=lambda base: base.modifiers.new("Subdivision", 'SUBSURF'))


@test
def tessellate_refresh():
    base, component, out = tessellate('QUAD')
    faces = len(out.data.polygons)
    component.scale = (1, 1, 2)
    select_only(out)
    check_finished(bpy.ops.object.tissue_update_tessellate(), "Refresh")
    check(len(out.data.polygons) == faces, "refresh changed the number of faces")


@test
def dual_mesh():
    ob = add_icosphere()
    vertices = len(ob.data.vertices)
    select_only(ob)
    check_finished(bpy.ops.object.dual_mesh(), "Dual Mesh")
    # The dual of a closed triangle mesh has one face per original vertex.
    check(len(ob.data.polygons) == vertices,
          f"expected {vertices} faces, got {len(ob.data.polygons)}")


@test
def polyhedra_wireframe():
    ob = add_cube(size=2, location=(0, 0, 0))
    select_only(ob)
    check_finished(bpy.ops.object.polyhedral_wireframe(), "Polyhedra Wireframe")
    check(len(bpy.context.object.data.polygons) > 0, "result is empty")


@test
def convert_to_curve():
    ob = add_grid()
    select_only(ob)
    check_finished(bpy.ops.object.tissue_convert_to_curve(), "Convert to Curve")
    check(bpy.context.object.type == 'CURVE', "result is not a curve")


@test
def lattice_along_surface():
    surface = add_grid()
    ob = add_cube(size=0.5, location=(0, 0, 1))
    select_only(ob, surface, active=surface)
    # Hiding the lattice needs a 3D Viewport, which background mode does not have.
    check_finished(bpy.ops.object.lattice_along_surface(hide_lattice=False), "Lattice along Surface")
    check(any(o.type == 'LATTICE' for o in bpy.data.objects), "no lattice was created")


@test
def uv_to_mesh():
    ob = add_cube(size=2, location=(0, 0, 0))
    select_only(ob)
    check_finished(bpy.ops.object.uv_to_mesh(), "UV to Mesh")
    check(bpy.context.object != ob, "no mesh was created")


@test
def random_materials():
    ob = add_grid()
    for i in range(3):
        ob.data.materials.append(bpy.data.materials.new(f"Material{i}"))
    select_only(ob)
    check_finished(bpy.ops.object.random_materials(), "Random Materials")
    used = {p.material_index for p in ob.data.polygons}
    check(len(used) > 1, "all faces kept the same material")


@test
def weight_to_materials():
    ob = add_grid()
    add_weight(ob)
    for i in range(3):
        ob.data.materials.append(bpy.data.materials.new(f"Material{i}"))
    select_only(ob)
    check_finished(bpy.ops.object.weight_to_materials(), "Weight to Materials")


@test
def rotate_faces():
    base, component, out = tessellate('QUAD')
    select_only(base)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    check_finished(bpy.ops.mesh.tissue_rotate_face_right(), "Rotate Faces")
    bpy.ops.object.mode_set(mode='OBJECT')


# --- Tissue Weight Tools ------------------------------------------------------


def weight_tool(operator, name, prepare=None, **kwargs):
    ob = add_icosphere(subdivisions=3)
    if prepare:
        prepare(ob)
    select_only(ob)
    before = {g.name for g in ob.vertex_groups}
    check_finished(operator(**kwargs), name)
    check_weights(ob, new_group(ob, before))
    return ob


@test
def weight_area():
    weight_tool(bpy.ops.object.face_area_to_vertex_groups, "Area")


@test
def weight_curvature():
    weight_tool(bpy.ops.object.curvature_to_vertex_groups, "Curvature")


@test
def weight_formula():
    weight_tool(bpy.ops.object.weight_formula, "Weight Formula", formula="rz")


@test
def weight_random():
    # Random fills the active vertex group instead of creating a new one.
    ob = add_icosphere(subdivisions=3)
    group = add_weight(ob)
    select_only(ob)
    check_finished(bpy.ops.object.random_weight(), "Random")
    check_weights(ob, group)


@test
def weight_harmonic():
    weight_tool(bpy.ops.object.harmonic_weight, "Harmonic", prepare=add_weight)


@test
def weight_laplacian():
    weight_tool(bpy.ops.object.weight_laplacian, "Weight Laplacian", prepare=add_weight)


@test
def weight_distance():
    def select_one_vertex(ob):
        for v in ob.data.vertices:
            v.select = v.index == 0
    weight_tool(bpy.ops.object.tissue_weight_distance, "Weight Distance", prepare=select_one_vertex)


@test
def edges_deformation():
    def deform(ob):
        ob.modifiers.new("Cast", 'CAST').factor = 1.0
    weight_tool(bpy.ops.object.edges_deformation, "Edges Deformation", prepare=deform)


@test
def edges_bending():
    def deform(ob):
        ob.modifiers.new("Cast", 'CAST').factor = 1.0
    weight_tool(bpy.ops.object.edges_bending, "Edges Bending", prepare=deform)


@test
def contour_curves():
    ob = add_icosphere(subdivisions=3)
    add_weight(ob)
    select_only(ob)
    check_finished(bpy.ops.object.tissue_weight_contour_curves_pattern(object=ob.name), "Contour Curves")
    check(bpy.context.object != ob, "no contour object was created")


@test
def contour_displace():
    ob = add_icosphere(subdivisions=3)
    add_weight(ob)
    select_only(ob)
    check_finished(bpy.ops.object.weight_contour_displace(), "Contour Displace")


@test
def contour_mask():
    ob = add_icosphere(subdivisions=3)
    add_weight(ob)
    select_only(ob)
    check_finished(bpy.ops.object.weight_contour_mask(), "Contour Mask")


@test
def reaction_diffusion():
    ob = add_icosphere(subdivisions=3)
    select_only(ob)
    check_finished(bpy.ops.object.reaction_diffusion_free_data(), "Reaction Diffusion reset")
    check_finished(bpy.ops.object.start_reaction_diffusion(), "Reaction Diffusion")
    check({"A", "B"} <= {g.name for g in ob.vertex_groups}, "groups A and B were not created")


# --- Conversions --------------------------------------------------------------


@test
def weight_to_colors_and_back():
    ob = add_icosphere(subdivisions=3)
    add_weight(ob)
    select_only(ob)
    check_finished(bpy.ops.object.vertex_group_to_vertex_colors(), "Convert to Colors")
    check(len(ob.data.color_attributes) > 0, "no color attribute was created")
    before = {g.name for g in ob.vertex_groups}
    check_finished(bpy.ops.object.vertex_colors_to_vertex_groups(), "Convert to Weight")
    check_weights(ob, new_group(ob, before))


@test
def weight_to_uv():
    ob = add_icosphere(subdivisions=3)
    add_weight(ob)
    select_only(ob)
    uv_maps = len(ob.data.uv_layers)
    check_finished(bpy.ops.object.vertex_group_to_uv(), "Convert to UV")
    check(len(ob.data.uv_layers) > uv_maps, "no UV map was created")


# --- Options and behaviour ----------------------------------------------------


def update_tessellation(out):
    select_only(out)
    check_finished(bpy.ops.object.tissue_update_tessellate(), "Refresh")


def check_reports_error(func, text):
    # A problem with the user's settings has to be a readable message, not a traceback.
    try:
        func()
    except RuntimeError as e:
        check("Traceback" not in str(e), f"got a traceback instead of a message: {e}")
        check(text in str(e), f"unexpected message: {e}")
    else:
        raise AssertionError(f"expected the error '{text}'")


@test
def tessellate_patch_uv_rotation():
    # The evaluated generator has more faces than patches: this used to raise an IndexError.
    base, component, out = tessellate('PATCH', prepare=lambda base: base.modifiers.new("Subdivision", 'SUBSURF'))
    faces = len(out.data.polygons)
    out.tissue_tessellate.rotation_mode = 'UV'
    update_tessellation(out)
    check(len(out.data.polygons) == faces, "UV rotation changed the number of faces")


@test
def tessellate_frame_iterations():
    # The first iteration has coincident vertices: this used to raise a ValueError.
    base, component, out = tessellate('FRAME')
    out.tissue_tessellate.iterations = 2
    update_tessellation(out)
    check(len(out.data.polygons) > 0, "tessellation is empty")


@test
def tessellate_missing_collection():
    base, component, out = tessellate('QUAD')
    out.tissue_tessellate.component_mode = 'COLLECTION'
    select_only(out)
    check_reports_error(bpy.ops.object.tissue_update_tessellate, "Collection")


@test
def tessellate_collection():
    base, component, out = tessellate('QUAD')
    collection = bpy.data.collections.new("Components")
    bpy.context.scene.collection.children.link(collection)
    collection.objects.link(component)
    out.tissue_tessellate.component_mode = 'COLLECTION'
    out.tissue_tessellate.component_coll = collection
    update_tessellation(out)
    check(len(out.data.polygons) > 0, "tessellation is empty")
    bpy.data.collections.remove(collection)


@test
def tessellate_open_edges_crease():
    # The value used to be written to 'crease_edge.001', which Blender ignores.
    base = add_grid()
    component = add_grid(size=1)
    select_only(component, base, active=base)
    result = bpy.ops.object.tissue_tessellate(generator=base.name, component=component.name, fill_mode='QUAD')
    check_finished(result, "Tessellate")
    out = bpy.context.object
    props = out.tissue_tessellate
    props.merge = True
    props.close_mesh = 'CAP'
    props.open_edges_crease = 0.5
    update_tessellation(out)
    names = [a.name for a in out.data.attributes]
    check('crease_edge.001' not in names, "creases were written to a second layer")
    check('crease_edge' in names, "no creases were created")
    creases = [0.0] * len(out.data.attributes['crease_edge'].data)
    out.data.attributes['crease_edge'].data.foreach_get('value', creases)
    check(max(creases) > 0.4, f"creases were not set, highest value is {max(creases)}")


@test
def tessellate_animated():
    base, component, out = tessellate('QUAD')
    z = max(v.co.z for v in out.data.vertices)
    out.tissue.bool_run = True
    for v in base.data.vertices:
        v.co.z += 1
    bpy.context.scene.frame_set(bpy.context.scene.frame_current + 1)
    out.tissue.bool_run = False
    check(max(v.co.z for v in out.data.vertices) > z + 0.5, "the tessellation did not follow the generator")


@test
def tessellate_shape_keys():
    # Component's Shape Keys are only used without the component's modifiers.
    failures = []
    enum_items = lambda name: [i.identifier for i in bpy.types.Object.bl_rna.properties[
        'tissue_tessellate'].fixed_type.properties[name].enum_items]
    for fill_mode in ('QUAD', 'TRI', 'FAN', 'FRAME', 'PATCH'):
        for normals_mode in enum_items('normals_mode'):
            for scale_mode in enum_items('scale_mode'):
                reset_scene()
                base = add_grid()
                if fill_mode == 'PATCH':
                    base.modifiers.new("Subdivision", 'SUBSURF')
                base.shape_key_add(name="Basis")
                base_key = base.shape_key_add(name="Key")
                base_key.value = 0.5
                # With Shape Keys as normals, the normals are the distance between the keys
                for point in base_key.data:
                    point.co.z += 0.2
                add_weight(base)
                component = add_cube()
                component.shape_key_add(name="Basis")
                key = component.shape_key_add(name="Key")
                key.value = 1
                for point in key.data:
                    point.co.z += 0.1
                select_only(component, base, active=base)
                case = f"{fill_mode}/{normals_mode}/{scale_mode}"
                try:
                    bpy.ops.object.tissue_tessellate(generator=base.name, component=component.name, fill_mode=fill_mode)
                    out = bpy.context.object
                    props = out.tissue_tessellate
                    props.com_modifiers = False
                    props.bool_shapekeys = True
                    props.normals_mode = normals_mode
                    props.scale_mode = scale_mode
                    update_tessellation(out)
                    props.vertex_group_thickness = "Weight"
                    update_tessellation(out)
                    if not out.data.shape_keys or len(out.data.shape_keys.key_blocks) != 2:
                        failures.append(f"{case}: the shape keys were not transferred")
                    else:
                        basis, moved = out.data.shape_keys.key_blocks
                        if all((a.co - b.co).length < 1e-5 for a, b in zip(basis.data, moved.data)):
                            failures.append(f"{case}: the shape key doesn't move the geometry")
                except Exception as e:
                    failures.append(f"{case}: {str(e).strip().splitlines()[-1]}")
    check(not failures, "\n".join(failures))


def add_hexagon(with_quad=False):
    # One flat hexagon, optionally with a quad attached to one of its edges.
    verts = [(math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0) for i in range(6)]
    faces = [list(range(6))]
    if with_quad:
        verts += [(2, 0, 0), (1.5, 0.866, 0)]
        faces.append([0, 6, 7, 1])
    mesh = bpy.data.meshes.new("Hexagon")
    mesh.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new("Hexagon", mesh)
    bpy.context.collection.objects.link(ob)
    ob.modifiers.new("Subdivision", 'SUBSURF')
    bpy.context.view_layer.update()
    return ob


def check_no_temporary_objects():
    left = [o.name for o in bpy.data.objects if "_tissue_tmp" in o.name or o.name.endswith("_before_subs")]
    check(not left, f"temporary objects were left in the file: {left}")


@test
def patch_without_quads():
    # This used to raise an IndexError.
    base = add_hexagon()
    base.hide_render = True
    component = add_cube()
    select_only(component, base, active=base)
    check_reports_error(lambda: bpy.ops.object.tissue_tessellate(
        generator=base.name, component=component.name, fill_mode='PATCH'), "4-sided")
    check_no_temporary_objects()
    check(base.hide_render, "the visibility of the Base was not restored")
    check(bpy.context.view_layer.objects.active == base, "the Base is not active anymore")


@test
def patch_without_quads_on_update():
    # A tessellation that already exists has to stay as it is.
    base = add_hexagon()
    component = add_cube()
    select_only(component, base, active=base)
    check_finished(bpy.ops.object.tissue_tessellate(
        generator=base.name, component=component.name, fill_mode='FAN'), "Tessellate")
    out = bpy.context.object
    faces = len(out.data.polygons)
    props = out.tissue_tessellate
    props.bool_hold = True
    props.fill_mode = 'PATCH'
    props.bool_hold = False
    select_only(out)
    check_reports_error(bpy.ops.object.tissue_update_tessellate, "4-sided")
    check("4-sided" in props.error_message, "the panel doesn't show the error")
    check(len(out.data.polygons) == faces, "the failed update changed the tessellation")
    check_no_temporary_objects()


@test
def patch_with_some_quads():
    # Faces without 4 sides are skipped.
    base = add_hexagon(with_quad=True)
    component = add_cube()
    select_only(component, base, active=base)
    check_finished(bpy.ops.object.tissue_tessellate(
        generator=base.name, component=component.name, fill_mode='PATCH'), "Tessellate")
    check(len(bpy.context.object.data.polygons) == 6, f"got {len(bpy.context.object.data.polygons)} faces")


@test
def patch_on_selected_faces():
    # Selected faces without 4 sides used to get through the filter.
    for select_quad in (True, False):
        reset_scene()
        base = add_hexagon(with_quad=True)
        base.data.polygons[0].select = True
        base.data.polygons[1].select = select_quad
        component = add_cube()
        select_only(component, base, active=base)
        run = lambda: bpy.ops.object.tissue_tessellate(generator=base.name, component=component.name,
                                                       fill_mode='PATCH', bool_selection=True)
        if select_quad:
            check_finished(run(), "Tessellate")
            check(len(bpy.context.object.data.polygons) == 6, f"got {len(bpy.context.object.data.polygons)} faces")
        else:
            check_reports_error(run, "4-sided")
            check_no_temporary_objects()


@test
def patch_with_modifier_after_subdivision():
    # This message was never shown: the error code was read as a list of objects.
    base = add_grid()
    base.modifiers.new("Subdivision", 'SUBSURF')
    base.modifiers.new("Bevel", 'BEVEL')
    component = add_cube()
    select_only(component, base, active=base)
    check_reports_error(lambda: bpy.ops.object.tissue_tessellate(
        generator=base.name, component=component.name, fill_mode='PATCH'), "Modifiers")
    check_no_temporary_objects()


@test
def tessellate_after_reload():
    base, component, out = tessellate('QUAD')
    faces = len(out.data.polygons)
    name = out.name
    path = os.path.join(tempfile.mkdtemp(prefix="tissue_reload_"), "reload.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    out = bpy.data.objects[name]
    check(out.tissue_tessellate.generator is not None, "the generator was lost")
    update_tessellation(out)
    check(len(out.data.polygons) == faces, "the reloaded tessellation changed")
    bpy.ops.wm.read_homefile(use_factory_startup=True, use_empty=False)


def particles(settings_type):
    ob = add_grid()
    modifier = ob.modifiers.new("Particles", 'PARTICLE_SYSTEM')
    settings = modifier.particle_system.settings
    settings.type = settings_type
    settings.count = 5
    settings.frame_start = settings.frame_end = 1
    select_only(ob)
    return ob


@test
def convert_particles_to_curve():
    for settings_type in ('HAIR', 'EMITTER'):
        reset_scene()
        ob = particles(settings_type)
        check_finished(bpy.ops.object.tissue_convert_to_curve(mode='PARTICLES'), "Convert to Curve")
        check(bpy.context.object.type == 'CURVE', "result is not a curve")


@test
def convert_without_particles():
    ob = add_grid()
    select_only(ob)
    check_reports_error(lambda: bpy.ops.object.tissue_convert_to_curve(mode='PARTICLES'), "Particle")


@test
def streamlines_from_script():
    # Without the dialog the object name was empty: this used to raise a KeyError.
    ob = add_icosphere(subdivisions=3)
    add_weight(ob)
    select_only(ob)
    check_finished(bpy.ops.object.tissue_weight_streamlines(), "Streamlines")
    check(bpy.context.object.type == 'CURVE', "result is not a curve")


@test
def weight_tools_in_edit_mode():
    # VertexGroup.add() is not allowed in Edit Mode: these used to raise a RuntimeError.
    for name in ('face_area_to_vertex_groups', 'random_weight', 'harmonic_weight', 'weight_laplacian',
                 'curvature_to_vertex_groups', 'vertex_group_to_vertex_colors'):
        reset_scene()
        ob = add_icosphere(subdivisions=2)
        add_weight(ob)
        select_only(ob)
        bpy.ops.object.mode_set(mode='EDIT')
        check_finished(getattr(bpy.ops.object, name)(), name)


def contour_with(**settings):
    ob = add_icosphere(subdivisions=3)
    add_weight(ob)
    values = [v.co.z for v in ob.data.vertices]
    ob.data.attributes.new("height", 'FLOAT', 'POINT').data.foreach_set('value', values)
    for v in ob.data.vertices:
        v.select = v.index == 0
    select_only(ob)
    settings = {k: (v(ob) if callable(v) else v) for k, v in settings.items()}
    result = bpy.ops.object.tissue_weight_contour_curves_pattern(object=ob.name, **settings)
    check_finished(result, "Contour Curves")
    check(bpy.context.object != ob, "no contour object was created")


@test
def contour_modes():
    contour_with(contour_mode='WEIGHT', vertex_group_contour=lambda ob: ob.vertex_groups[0].name)
    reset_scene()
    contour_with(contour_mode='ATTRIBUTE', contour_attribute="height")
    reset_scene()
    contour_with(contour_mode='GEODESIC', seeds_mode='WEIGHT', vertex_group_seed=lambda ob: ob.vertex_groups[0].name)
    reset_scene()
    contour_with(contour_mode='TOPOLOGY', seeds_mode='WEIGHT', vertex_group_seed=lambda ob: ob.vertex_groups[0].name)


def reaction_diffusion_object():
    ob = add_icosphere(subdivisions=3)
    select_only(ob)
    check_finished(bpy.ops.object.start_reaction_diffusion(), "Reaction Diffusion")
    for v in ob.data.vertices:
        if v.co.z > 0.5:
            ob.vertex_groups['B'].add([v.index], 1, 'REPLACE')
    return ob


@test
def reaction_diffusion_simulates():
    ob = reaction_diffusion_object()
    group = ob.vertex_groups['B']
    before = weights(ob, group)
    scene = bpy.context.scene
    for frame in range(2, 5):
        scene.frame_set(frame)
    ob.reaction_diffusion_settings.run = False
    check(weights(ob, group) != before, "the simulation did not change the weights")
    check_weights(ob, group)


@test
def reaction_diffusion_bake():
    ob = reaction_diffusion_object()
    props = ob.reaction_diffusion_settings
    props.cache_frame_start = 1
    props.cache_frame_end = 3
    props.cache_dir = tempfile.mkdtemp(prefix="tissue_rd_")
    check_finished(bpy.ops.object.bake_reaction_diffusion(), "Bake")
    # The last frame used to be skipped.
    for frame in (1, 2, 3):
        for name in ('a', 'b'):
            check(os.path.exists(os.path.join(props.cache_dir, f"{name}_{frame:04d}")), f"frame {frame} was not baked")
    check_finished(bpy.ops.object.reaction_diffusion_free_data(), "Free Data")
    check(os.listdir(props.cache_dir) == [], "Free Data left some files")
    props.run = False


@test
def texture_reaction_diffusion():
    ob = add_grid()
    select_only(ob)
    check_finished(bpy.ops.object.start_tex_reaction_diffusion(), "Texture Reaction Diffusion")
    props = ob.tex_reaction_diffusion_settings
    image = bpy.data.images[props.img_b] if isinstance(props.img_b, str) else props.img_b
    width, height = image.size
    pixels = [0.0, 0.0, 0.0, 1.0] * (width * height)
    for y in range(height // 2 - 4, height // 2 + 4):
        for x in range(width // 2 - 4, width // 2 + 4):
            pixels[(y * width + x) * 4] = 1.0
    image.pixels.foreach_set(pixels)
    before = [0.0] * len(pixels)
    image.pixels.foreach_get(before)
    # The frame handler is added by the panel, which isn't drawn in background mode.
    sys.modules["tissue.texture_reaction_diffusion"].tex_reaction_diffusion_def(ob)
    after = [0.0] * len(pixels)
    image.pixels.foreach_get(after)
    check(after != before, "the simulation did not change the image")
    check_finished(bpy.ops.object.reset_tex_reaction_diffusion(), "Texture Reaction Diffusion reset")


@test
def texture_reaction_diffusion_numpy_matches_numba():
    module = sys.modules["tissue.texture_reaction_diffusion"]
    if 'run_tex_rd_ani' not in vars(module):
        print("      (Numba is not available: nothing to compare)")
        return
    rng = np.random.default_rng(1)
    shape = (40, 30)
    start_a, start_b = rng.random(shape), rng.random(shape) * 0.2
    vf1, vf2 = rng.random((4, *shape)), rng.random((4, *shape))
    settings = (rng.random(shape), rng.random(shape) * 0.5, np.full(shape, 0.03), np.full(shape, 0.06), 1.0, 5)
    results = []
    for run in (module.run_tex_rd_ani, module.np_run_tex_rd_ani):
        a, b = start_a.copy(), start_b.copy()
        run(a, b, np.zeros(shape), np.zeros(shape), *settings, vf1, vf2, np.zeros(shape))
        results.append((a, b))
    check(np.allclose(results[0][0], results[1][0]) and np.allclose(results[0][1], results[1][1]),
          "the NumPy simulation gives a different result")


# --- Add-on lifecycle (last: it disables and enables Tissue) ---------------------


OBJECT_PROPERTIES = (
    "tissue", "tissue_tessellate", "tissue_polyhedra", "tissue_to_curve",
    "tissue_contour_curves", "formula_settings", "reaction_diffusion_settings",
    "tex_reaction_diffusion_settings",
)


def tissue_handlers():
    handlers = list(bpy.app.handlers.frame_change_post) + list(bpy.app.handlers.render_init)
    return [h.__name__ for h in handlers if getattr(h, "__module__", "").split(".")[0] == "tissue"]


@test
def disable_and_enable():
    # Ported from upstream's b5-dev branch. Animated Tessellate and Reaction-Diffusion
    # add frame handlers while they are used: disabling has to remove them too.
    base, component, out = tessellate('QUAD')
    out.tissue.bool_run = True
    reaction_diffusion_object()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current + 1)
    check(tissue_handlers(), "the test didn't add any handler to remove")
    addon_utils.disable("tissue", default_set=True, handle_error=None)
    left = [p for p in OBJECT_PROPERTIES if hasattr(bpy.types.Object, p)]
    check(not left, f"disabling left these object properties: {left}")
    check(not tissue_handlers(), f"disabling left these handlers: {tissue_handlers()}")
    bpy.context.scene.frame_set(bpy.context.scene.frame_current + 1)
    addon_utils.enable("tissue", default_set=True, handle_error=None)
    check(not tissue_handlers(), f"enabling added handlers: {tissue_handlers()}")
    # The tools still work after re-enabling.
    reset_scene()
    tessellate('QUAD')


# --- Runner -------------------------------------------------------------------


def main():
    print(f"\nBlender {bpy.app.version_string}, Python {sys.version.split()[0]}")
    # Tissue also finds a Numba installed by its own button. Set TISSUE_TEST_NO_NUMBA
    # to test the NumPy code paths, or TISSUE_TEST_SITE to a folder with Numba.
    if os.environ.get("TISSUE_TEST_NO_NUMBA"):
        class BlockNumba:
            def find_spec(self, name, path=None, target=None):
                if name.split('.')[0] in ('numba', 'llvmlite'):
                    raise ImportError(f"{name} is blocked for this test run")
        sys.meta_path.insert(0, BlockNumba())
        print("Numba blocked")
    elif os.environ.get("TISSUE_TEST_SITE"):
        sys.path.insert(0, os.environ["TISSUE_TEST_SITE"])
        import numba
        print(f"Numba {numba.__version__}")
    enable_tissue()
    failures = []
    for func in TESTS:
        reset_scene()
        try:
            func()
        except Exception:
            failures.append((func.__name__, traceback.format_exc()))
            print(f"FAIL  {func.__name__}")
        else:
            print(f"ok    {func.__name__}")

    for name, trace in failures:
        print(f"\n--- {name} ---\n{trace}")
    print(f"\n{len(TESTS) - len(failures)} passed, {len(failures)} failed")
    sys.exit(1 if failures else 0)


main()
