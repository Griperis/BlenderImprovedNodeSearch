import bpy
import mathutils
import gpu
import gpu_extras.presets
import typing

from . import draw_nw


HIGHLIGHT_COLOR = (0, 1, 1, 0.5)


def mouse_to_region_coords(
    context: bpy.types.Context,
    event: bpy.types.Event
) -> typing.Tuple[float, float]:

    region = context.region.view2d
    ui_scale = context.preferences.system.ui_scale
    x, y = region.region_to_view(event.mouse_x, event.mouse_y)
    return (x / ui_scale, y / ui_scale)


class DrawHighlight(bpy.types.Operator):
    bl_idname = "node_search.draw_highlight"
    bl_label = "Highlight Found Nodes"
    
    handle = None
    target_locations: typing.List[mathutils.Vector] = []

    def draw_callback(self, context: bpy.types.Context):
        original_blend = gpu.state.blend_get()
        gpu.state.blend_set('ALPHA')
        for position in DrawHighlight.target_locations:
            gpu_extras.presets.draw_circle_2d(position, HIGHLIGHT_COLOR, 50)

        gpu.state.blend_set(original_blend)

    def add_draw_handler(self, context: bpy.types.Context):
        DrawHighlight.handle = bpy.types.SpaceNodeEditor.draw_handler_add(
            draw_nw.main_draw, (self, context), 'WINDOW', 'POST_PIXEL')

    def remove_draw_handler(self):
        bpy.types.SpaceNodeEditor.draw_handler_remove(DrawHighlight.handle, 'WINDOW')
        DrawHighlight.handle = None

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            self.remove_draw_handler()
            return {'FINISHED'}

        if event.type == 'LEFTMOUSE':
            self.mouse_path.append((event.mouse_region_x, event.mouse_region_y))
        
        DrawHighlight.target_locations = [
            bpy.context.region.view2d.view_to_region(
                node.location.x, node.location.y, clip=True) for node in context.selected_nodes]

        context.area.tag_redraw()
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.mouse_path = []
        DrawHighlight.handle = None
        self.add_draw_handler(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}