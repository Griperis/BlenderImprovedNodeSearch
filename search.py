import bpy
import typing
from . import prefs
from . import draw_nw


CLASSES = []
FOUND_NODES = set()


def search_nodes(node_tree, filters) -> typing.Set[bpy.types.Node]:
    ret = set()
    for node in node_tree.nodes:
        if hasattr(node, "node_tree"):
            ret.update(search_nodes(node.node_tree, filters))
        
        # If any filter returns True for given node, we consider it in the result
        for filter_ in filters:
            if filter_(node):
                ret.add(node)
                break
    
    return ret
    

def node_name_filter(node: bpy.types.Node, name: str) -> bool:
    return name.lower() in node.name.lower()


def type_filter(node: bpy.types.Node, name: str) -> bool:
    return node.bl_idname == name


def attribute_filter(node: bpy.types.GeometryNode, name: str) -> bool:
    if isinstance(
        node, (
            bpy.types.GeometryNodeInputNamedAttribute,
            bpy.types.GeometryNodeStoreNamedAttribute,
            bpy.types.GeometryNodeRemoveAttribute
    )) and name == "":   
        return True
    
    # TODO: Find if the node.inputs[x] is connected to other node or not
    # and use the value from there.
    searched_name = name.lower()
    if isinstance(node, bpy.types.GeometryNodeInputNamedAttribute):
        return node.inputs[0].default_value.lower() == searched_name
    elif isinstance(node, bpy.types.GeometryNodeStoreNamedAttribute):
        return node.inputs[2].default_value.lower() == searched_name
    elif isinstance(node, bpy.types.GeometryNodeRemoveAttribute):
        return node.inputs[1].default_value.lower() == searched_name
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


class AdvancedNodeSearch(bpy.types.Operator):
    bl_idname = "node_search.search"
    bl_label = "Search"

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.area.type == 'NODE_EDITOR' and context.region.type == 'WINDOW'

    def draw(self, context):
        prefs_ = prefs.get_preferences(context)
        layout = self.layout
        if context.area.ui_type not in {'GeometryNodeTree', 'ShaderNodeTree', 'CompositorNodeTree'}:
            layout.label(text="Node search only works in node editors")
            return
        
        # TODO: use regexes option
        layout.prop(prefs_, "search")
        layout.separator()

        # We don't show filtering by type if filtering by attribute is shown
        if not prefs_.filter_by_attribute or context.area.ui_type != 'GeometryNodeTree':
            layout.prop(prefs_, "filter_by_type")
            if prefs_.filter_by_type:
                if context.area.ui_type == 'GeometryNodeTree':
                    layout.prop(prefs_, "geometry_node_types")
                elif context.area.ui_type == 'ShaderNodeTree':
                    layout.prop(prefs_, "shader_node_types")
                elif context.area.ui_type == 'CompositorNodeTree':
                    layout.prop(prefs_, "compositor_node_types")

        if context.area.ui_type == 'GeometryNodeTree':
            layout.prop(prefs_, "filter_by_attribute")
            if prefs_.filter_by_attribute:
                layout.prop(prefs_, "attribute_search")

    def execute(self, context):
        prefs_ = prefs.get_preferences(context)
        filters_ = set()
        filters_.add(lambda x: node_name_filter(x, prefs_.search))

        if prefs_.filter_by_attribute:
            filters_.add(lambda x: attribute_filter(x, prefs_.attribute_search))
        
        if prefs_.filter_by_type and (not prefs_.filter_by_attribute or context.area.ui_type != 'GeometryNodeTree'):
            # Append the correct attribute filter with types from prefs_ based on the node tree type
            if context.area.ui_type == 'GeometryNodeTree':
                filters_.add(lambda x: type_filter(x, prefs_.geometry_node_types))
            elif context.area.ui_type == 'ShaderNodeTree':
                filters_.add(lambda x: type_filter(x, prefs_.shader_node_types))
            elif context.area.ui_type == 'CompositorNodeTree':
                filters_.add(lambda x: type_filter(x, prefs_.compositor_node_types))
        
        node_tree = context.space_data.edit_tree
        FOUND_NODES.clear()
        found_nodes = search_nodes(node_tree, filters_)
        FOUND_NODES.update(found_nodes)

        if len(found_nodes) > 0:
            self.report({'INFO'}, f"Found {len(found_nodes)} nodes")
        else:
            self.report({'WARNING'}, "No nodes found")

        # Find the node tree to search in and filter in the nodes
        return {'FINISHED'}

    def invoke(self, context, event):
        # Toggle overlay by default
        if ToggleSearchOverlay.handle is None:
            bpy.ops.node_search.toggle_overlay('INVOKE_DEFAULT')

        return context.window_manager.invoke_props_dialog(self)


CLASSES.append(AdvancedNodeSearch)


class ClearSearch(bpy.types.Operator):
    bl_idname = "node_search.clear"
    bl_label = "Clear Search"

    def execute(self, context: bpy.types.Context):
        FOUND_NODES.clear()
        return {'FINISHED'}
    

CLASSES.append(ClearSearch)


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
        
        if len(FOUND_NODES) > 0:
            row = layout.row()
            row.label(text=f"Found {len(FOUND_NODES)} node(s)")
            row.operator(ClearSearch.bl_idname, icon='PANEL_CLOSE', text="")
            layout.separator()
        
        layout.prop(prefs_, "highlight_color")
        layout.prop(prefs_, "border_attenuation", slider=True)
        layout.prop(prefs_, "border_size")


CLASSES.append(AdvancedNodeSearchPanel)