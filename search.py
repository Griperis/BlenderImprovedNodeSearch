import bpy
import typing
from . import prefs
from . import draw_nw


CLASSES = []
FOUND_NODES = set()


def search_nodes(node_tree, filter_) -> typing.Iterable[bpy.types.Node]:
    ret = set()
    for node in node_tree.nodes:
        if hasattr(node, "node_tree"):
            ret.update(search_nodes(node.node_tree, filter_))
        
        if filter_(node):
            continue
        
        ret.add(node)
    
    return ret
    

def attribute_filter(node) -> bool:
    if not isinstance(node, (bpy.types.GeometryNodeInputNamedAttribute, bpy.types.GeometryNodeStoreNamedAttribute)):
        return True
    
    return False


# unique_attribute_names = set()
# for node_tree in bpy.data.node_groups:
#     print(f"Node Tree: {node_tree.name}")
#     nodes = search_nodes(node_tree, attribute_filter)
#     for node in nodes:
#         if isinstance(node, bpy.types.GeometryNodeInputNamedAttribute):
#             unique_attribute_names.add(node.inputs[0].default_value)
#         elif isinstance(node, bpy.types.GeometryNodeStoreNamedAttribute):
#             unique_attribute_names.add(node.inputs[1].default_value)
            

# print(unique_attribute_names)


class ToggleSearchOverlay(bpy.types.Operator):
    bl_idname = "node_search.toggle_overlay"
    bl_label = "Overlay Search Results"

    handle = None


    def add_draw_handler(self, context: bpy.types.Context):
        ToggleSearchOverlay.handle = bpy.types.SpaceNodeEditor.draw_handler_add(
            draw_nw.main_draw, (self, context, FOUND_NODES), 'WINDOW', 'POST_PIXEL')

    @staticmethod
    def remove_draw_handler():
        bpy.types.SpaceNodeEditor.draw_handler_remove(ToggleSearchOverlay.handle, 'WINDOW')
        ToggleSearchOverlay.handle = None

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if ToggleSearchOverlay.handle is None:
            self.add_draw_handler(context)
        else:
            self.remove_draw_handler()

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

CLASSES.append(ToggleSearchOverlay)


# The operator performing the search and changing the state
class AdvancedNodeSearch(bpy.types.Operator):
    bl_idname = "node_search.search"
    bl_label = "Search"

    def draw(self, context):
        layout = self.layout

    def execute(self, context):
        FOUND_NODES.clear()
        FOUND_NODES.update(set(context.selected_nodes))
        return {'FINISHED'}

    def invoke(self, context, event):
        # Toggle overlay by default
        if ToggleSearchOverlay.handle is None:
            bpy.ops.node_search.toggle_overlay('INVOKE_DEFAULT')

        return context.window_manager.invoke_props_dialog(self)


CLASSES.append(AdvancedNodeSearch)


class AdvancedNodeSearchPanel(bpy.types.Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_label = "Advanced Search"
    bl_idname = "NODE_EDITOR_PT_Advanced_Search"

    def draw(self, context):
        prefs_ = prefs.get_preferences(context)
        layout = self.layout
        layout.operator(AdvancedNodeSearch.bl_idname, text="Search", icon='VIEWZOOM')
        layout.operator(
            ToggleSearchOverlay.bl_idname,
            depress=ToggleSearchOverlay.handle is not None,
            text="Overlay",
            icon='OUTLINER_DATA_LIGHT')
        layout.prop(prefs_, "highlight_color")
        layout.prop(prefs_, "border_attenuation", slider=True)
        layout.prop(prefs_, "border_size")


CLASSES.append(AdvancedNodeSearchPanel)