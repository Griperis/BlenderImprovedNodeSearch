# copyright (c) Zdenek Dolezal 2024-*

# Code for drawing of the node borders is inspired by the NodeWrangler addon bundled in Blender,
# created by Bartek Skorupa, Greg Zaal, Sebastian Koenig, Christian Brinkmann, Florian Meyer

import bpy
import blf
import mathutils
import gpu
import gpu_extras.presets
import math
import gpu_extras.batch
from . import prefs


def prefs_line_width():
    prefs = bpy.context.preferences.system
    return prefs.pixel_size


def abs_node_location(node):
    abs_location = node.location
    if node.parent is None:
        return abs_location
    return abs_location + abs_node_location(node.parent)


def dpi_fac():
    prefs = bpy.context.preferences.system
    return prefs.dpi / 72


def draw_circle_2d_filled(mx, my, radius, colour=(1.0, 1.0, 1.0, 0.7)):
    radius = radius * prefs_line_width()
    sides = 12
    vertices = [
        (
            radius * math.cos(i * 2 * math.pi / sides) + mx,
            radius * math.sin(i * 2 * math.pi / sides) + my,
        )
        for i in range(sides + 1)
    ]

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.uniform_float("color", colour)
    batch = gpu_extras.batch.batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    batch.draw(shader)


def get_node_location(node):
    nlocx, nlocy = abs_node_location(node)
    return (nlocx + 1) * dpi_fac(), (nlocy + 1) * dpi_fac()


def draw_rounded_node_border(node, radius=8, colour=(1.0, 1.0, 1.0, 0.7)):
    area_width = bpy.context.area.width
    sides = 16
    radius *= prefs_line_width()

    nlocx, nlocy = get_node_location(node)
    ndimx = node.dimensions.x
    ndimy = node.dimensions.y

    if node.hide:
        nlocx += -1
        nlocy += 5

    if node.type == 'REROUTE':
        # nlocx += 1
        nlocy -= 1
        ndimx = 0
        ndimy = 0
        radius += 6

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.uniform_float("color", colour)

    # Top left corner
    mx, my = bpy.context.region.view2d.view_to_region(nlocx, nlocy, clip=False)
    vertices = [(mx, my)]
    for i in range(sides + 1):
        if 4 <= i <= 8:
            if mx < area_width:
                cosine = radius * math.cos(i * 2 * math.pi / sides) + mx
                sine = radius * math.sin(i * 2 * math.pi / sides) + my
                vertices.append((cosine, sine))

    batch = gpu_extras.batch.batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    batch.draw(shader)

    # Top right corner
    mx, my = bpy.context.region.view2d.view_to_region(nlocx + ndimx, nlocy, clip=False)
    vertices = [(mx, my)]
    for i in range(sides + 1):
        if 0 <= i <= 4:
            if mx < area_width:
                cosine = radius * math.cos(i * 2 * math.pi / sides) + mx
                sine = radius * math.sin(i * 2 * math.pi / sides) + my
                vertices.append((cosine, sine))

    batch = gpu_extras.batch.batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    batch.draw(shader)

    # Bottom left corner
    mx, my = bpy.context.region.view2d.view_to_region(nlocx, nlocy - ndimy, clip=False)
    vertices = [(mx, my)]
    for i in range(sides + 1):
        if 8 <= i <= 12:
            if mx < area_width:
                cosine = radius * math.cos(i * 2 * math.pi / sides) + mx
                sine = radius * math.sin(i * 2 * math.pi / sides) + my
                vertices.append((cosine, sine))

    batch = gpu_extras.batch.batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    batch.draw(shader)

    # Bottom right corner
    mx, my = bpy.context.region.view2d.view_to_region(nlocx + ndimx, nlocy - ndimy, clip=False)
    vertices = [(mx, my)]
    for i in range(sides + 1):
        if 12 <= i <= 16:
            if mx < area_width:
                cosine = radius * math.cos(i * 2 * math.pi / sides) + mx
                sine = radius * math.sin(i * 2 * math.pi / sides) + my
                vertices.append((cosine, sine))

    batch = gpu_extras.batch.batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    batch.draw(shader)

    # prepare drawing all edges in one batch
    vertices = []
    indices = []
    id_last = 0

    # Left edge
    m1x, m1y = bpy.context.region.view2d.view_to_region(nlocx, nlocy, clip=False)
    m2x, m2y = bpy.context.region.view2d.view_to_region(nlocx, nlocy - ndimy, clip=False)
    if m1x < area_width and m2x < area_width:
        vertices.extend([(m2x - radius, m2y), (m2x, m2y), (m1x, m1y), (m1x - radius, m1y)])
        indices.extend(
            [(id_last, id_last + 1, id_last + 3), (id_last + 3, id_last + 1, id_last + 2)]
        )
        id_last += 4

    # Top edge
    m1x, m1y = bpy.context.region.view2d.view_to_region(nlocx, nlocy, clip=False)
    m2x, m2y = bpy.context.region.view2d.view_to_region(nlocx + ndimx, nlocy, clip=False)
    m1x = min(m1x, area_width)
    m2x = min(m2x, area_width)
    vertices.extend([(m1x, m1y), (m2x, m1y), (m2x, m1y + radius), (m1x, m1y + radius)])
    indices.extend([(id_last, id_last + 1, id_last + 3), (id_last + 3, id_last + 1, id_last + 2)])
    id_last += 4

    # Right edge
    m1x, m1y = bpy.context.region.view2d.view_to_region(nlocx + ndimx, nlocy, clip=False)
    m2x, m2y = bpy.context.region.view2d.view_to_region(nlocx + ndimx, nlocy - ndimy, clip=False)
    if m1x < area_width and m2x < area_width:
        vertices.extend([(m1x, m2y), (m1x + radius, m2y), (m1x + radius, m1y), (m1x, m1y)])
        indices.extend(
            [(id_last, id_last + 1, id_last + 3), (id_last + 3, id_last + 1, id_last + 2)]
        )
        id_last += 4

    # Bottom edge
    m1x, m1y = bpy.context.region.view2d.view_to_region(nlocx, nlocy - ndimy, clip=False)
    m2x, m2y = bpy.context.region.view2d.view_to_region(nlocx + ndimx, nlocy - ndimy, clip=False)
    m1x = min(m1x, area_width)
    m2x = min(m2x, area_width)
    vertices.extend([(m1x, m2y), (m2x, m2y), (m2x, m1y - radius), (m1x, m1y - radius)])
    indices.extend([(id_last, id_last + 1, id_last + 3), (id_last + 3, id_last + 1, id_last + 2)])

    # now draw all edges in one batch
    if len(vertices) != 0:
        batch = gpu_extras.batch.batch_for_shader(
            shader, 'TRIS', {"pos": vertices}, indices=indices
        )
        batch.draw(shader)


def get_region_borders(context: bpy.types.Context):
    view2d = context.region.view2d
    x, y = (0, 0)
    w, h = (context.region.width, context.region.height)

    return (*view2d.region_to_view(x, y), *view2d.region_to_view(x + w, y + h))


def is_node_partially_in_view(node: bpy.types.Node, context: bpy.types.Context) -> bool:
    nx, ny = get_node_location(node)
    bx, by, b_xw, b_yh = get_region_borders(context)
    return nx < b_xw and ny - node.dimensions.y < b_yh and nx + node.dimensions.x > bx and ny > by


def get_node_clamped_position(node: bpy.types.Node, context: bpy.types.Context):
    nx, ny = get_node_location(node)
    bx, by, b_xw, b_yh = get_region_borders(context)
    hx_dim, hy_dim = node.dimensions.x / 2.0, node.dimensions.y / 2.0

    rx, ry = nx + hx_dim, ny - hy_dim
    if nx + node.dimensions.x < bx:
        rx = bx + 10.0
    if nx > b_xw:
        rx = b_xw - 10.0

    if ny < by:
        ry = by + 10.0
    if ny - node.dimensions.y > b_yh:
        ry = b_yh - 10.0

    return rx, ry


def draw_text(x: float, y: float, text: str, size: float, colour: set[float, float, float, float]):
    prev_state = gpu.state.blend_get()
    blf.size(0, size)
    w, h = blf.dimensions(0, text)
    blf.position(0, x - w / 2.0, y - h / 2.0, 0)
    blf.color(0, *colour)
    blf.draw(0, text)

    gpu.state.blend_set(prev_state)


def highlight_nodes(
    context: bpy.types.Context,
    node_tree_nodes: dict[bpy.types.NodeTree, list[bpy.types.Node]],
    node_tree_occurances: dict[bpy.types.NodeTree, int],
) -> None:
    prefs_ = prefs.get_preferences(context)
    if not (context.area.type == 'NODE_EDITOR' and context.region.type == 'WINDOW'):
        return

    nodes = node_tree_nodes.get(context.space_data.edit_tree, None)
    if nodes is None:
        return

    prev_state = gpu.state.blend_get()
    gpu.state.blend_set('ALPHA')
    inner = prefs_.highlight_color
    outer = mathutils.Vector(prefs_.highlight_color) * prefs_.border_attenuation

    for node in nodes:
        # This count is going to be > 0 only for node groups that should be highlighted with
        # the number text.
        inside_node_count = 0
        if hasattr(node, "node_tree"):
            inside_node_count = node_tree_occurances.get(node.node_tree, 0)

        if is_node_partially_in_view(node, context):
            x, y = get_node_location(node)
            cx, cy = context.region.view2d.view_to_region(
                x + (node.dimensions.x / 2.0), y - (node.dimensions.y / 2.0)
            )
            draw_rounded_node_border(node, radius=5, colour=inner)
            draw_rounded_node_border(node, radius=5 + prefs_.border_size, colour=outer)

            if inside_node_count > 0:
                tx, ty = context.region.view2d.view_to_region(
                    x + (node.dimensions.x / 2.0), y - node.dimensions.y - prefs_.text_size
                )
                draw_text(tx, ty, str(inside_node_count), prefs_.text_size, inner)
        else:
            cx, cy = context.region.view2d.view_to_region(*get_node_clamped_position(node, context))
            draw_circle_2d_filled(cx, cy, 10.0, inner)
            draw_circle_2d_filled(cx, cy, 10.0 + prefs_.border_size, outer)
            if inside_node_count > 0:
                draw_text(cx, cy, str(inside_node_count), prefs_.text_size, (1.0, 1.0, 1.0, 1.0))

    gpu.state.blend_set(prev_state)
