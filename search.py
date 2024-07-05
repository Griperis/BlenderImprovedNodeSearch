# copyright (c) Zdenek Dolezal

import bpy
import typing
from . import prefs
from . import draw


CLASSES = []
FOUND_NODES = set()
NODE_TREE_OCCURRENCES = {}


FilterType = typing.Callable[[bpy.types.Node, str], bool]


class NodeSearch:
    def __init__(
        self,
        node_tree: bpy.types.NodeTree,
        filters: set[FilterType],
        search_in_node_groups: bool = True,
    ):
        self.node_tree = node_tree
        self.filters = filters
        self.search_in_node_groups = search_in_node_groups
        self.processed_node_trees = {}
        self.nested_node_tree_finds = {}

    def search(self) -> set[bpy.types.Node]:
        """Searched the node tree, while counting the nested node tree finds.

        Returns top level nodes that match the filters.
        """
        ret = set()
        all_found_nodes = self._search_and_recurse(self.node_tree)
        for node in self.node_tree.nodes:
            if node in all_found_nodes:
                ret.add(node)

        return ret

    def _search_and_recurse(
        self, node_tree: bpy.types.NodeTree, depth: int = 0
    ) -> set[bpy.types.Node]:
        ret = set()
        if node_tree in self.processed_node_trees:
            return self.processed_node_trees[node_tree]

        for node in node_tree.nodes:
            if hasattr(node, "node_tree"):
                if self.search_in_node_groups:
                    found_nodes = self._search_and_recurse(node.node_tree, depth + 1)
                    ret.update(found_nodes)
                    if len(found_nodes) > 0:
                        if depth == 0:
                            self.nested_node_tree_finds[node.node_tree] = len(found_nodes)
                            ret.add(node)
                    self.processed_node_trees[node_tree] = found_nodes

            # If any filter returns True for given node, we consider it in the result
            for filter_ in self.filters:
                if filter_(node):
                    ret.add(node)
                    break

        return ret


def node_name_filter(node: bpy.types.Node, name: str) -> bool:
    return name.lower() in node.name.lower()


def type_filter(node: bpy.types.Node, name: str) -> bool:
    return node.bl_idname == name


def attribute_filter(node: bpy.types.GeometryNode, name: str) -> bool:
    if (
        isinstance(
            node,
            (
                bpy.types.GeometryNodeInputNamedAttribute,
                bpy.types.GeometryNodeStoreNamedAttribute,
                bpy.types.GeometryNodeRemoveAttribute,
            ),
        )
        and name == ""
    ):
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


class ToggleSearchOverlay(bpy.types.Operator):
    bl_idname = "node_search.toggle_overlay"
    bl_label = "Overlay Search Results"

    handle = None
    # Node tree reference to draw only in the right context
    node_tree = None

    def add_draw_handler(self, context: bpy.types.Context):
        ToggleSearchOverlay.handle = bpy.types.SpaceNodeEditor.draw_handler_add(
            draw.highlight_nodes,
            (self, context, FOUND_NODES, NODE_TREE_OCCURRENCES),
            'WINDOW',
            'POST_PIXEL',
        )

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


class PerformNodeSearch(bpy.types.Operator):
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

        layout.prop(prefs_, "search_in_node_groups")

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
        if prefs_.search != "":
            filters_.add(lambda x: node_name_filter(x, prefs_.search))

        if prefs_.filter_by_attribute:
            filters_.add(lambda x: attribute_filter(x, prefs_.attribute_search))

        if prefs_.filter_by_type and (
            not prefs_.filter_by_attribute or context.area.ui_type != 'GeometryNodeTree'
        ):
            # Append the correct attribute filter with types from prefs_ based on the node tree type
            if context.area.ui_type == 'GeometryNodeTree':
                filters_.add(lambda x: type_filter(x, prefs_.geometry_node_types))
            elif context.area.ui_type == 'ShaderNodeTree':
                filters_.add(lambda x: type_filter(x, prefs_.shader_node_types))
            elif context.area.ui_type == 'CompositorNodeTree':
                filters_.add(lambda x: type_filter(x, prefs_.compositor_node_types))

        node_tree = context.space_data.edit_tree
        FOUND_NODES.clear()
        NODE_TREE_OCCURRENCES.clear()
        node_search = NodeSearch(node_tree, filters_, prefs_.search_in_node_groups)
        found_nodes = node_search.search()
        ToggleSearchOverlay.node_tree = node_tree
        FOUND_NODES.update(found_nodes)
        NODE_TREE_OCCURRENCES.update(node_search.nested_node_tree_finds)

        if len(found_nodes) > 0:
            self.report({'INFO'}, f"Found {len(found_nodes)} node(s)")
        else:
            self.report({'WARNING'}, "No nodes found")

        # Find the node tree to search in and filter in the nodes
        return {'FINISHED'}

    def invoke(self, context, event):
        # Toggle overlay by default
        if ToggleSearchOverlay.handle is None:
            bpy.ops.node_search.toggle_overlay('INVOKE_DEFAULT')

        return context.window_manager.invoke_props_dialog(self)


CLASSES.append(PerformNodeSearch)


class ClearSearch(bpy.types.Operator):
    bl_idname = "node_search.clear"
    bl_label = "Clear Search"

    def execute(self, context: bpy.types.Context):
        FOUND_NODES.clear()
        return {'FINISHED'}


CLASSES.append(ClearSearch)


class SelectFoundNodes(bpy.types.Operator):
    bl_idname = "node_search.select_found"
    bl_label = "Select Found Nodes"

    def execute(self, context: bpy.types.Context):
        bpy.ops.node.select_all(action='DESELECT')
        for node in FOUND_NODES:
            node.select = True
        return {'FINISHED'}


CLASSES.append(SelectFoundNodes)


class CycleFoundNodes(bpy.types.Operator):
    bl_idname = "node_search.cycle_found"
    bl_label = "Cycle Found Nodes"

    direction: bpy.props.IntProperty(default=1, min=-1, max=1)

    index = 0

    def execute(self, context: bpy.types.Context):
        if len(FOUND_NODES) == 0:
            return {'FINISHED'}

        new_index = CycleFoundNodes.index + self.direction
        # clamp next_index to boundaries of FOUND_NODES
        if new_index > len(FOUND_NODES) - 1:
            new_index = 0
        elif new_index < 0:
            new_index = len(FOUND_NODES) - 1

        # We sort the found nodes by name, as set is unordered
        node = sorted(list(FOUND_NODES), key=lambda x: x.name)[new_index]
        print(f"Trying to select {node.name}")

        # Context override doesn't work for some reason here
        # TODO: Store and restore selection here
        bpy.ops.node.select_all(action='DESELECT')
        node.select = True
        bpy.ops.node.view_selected()
        node.select = False

        CycleFoundNodes.index = new_index
        return {'FINISHED'}


CLASSES.append(CycleFoundNodes)


class ImprovedNodeSearchPanel(bpy.types.Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_label = "Improved Search"
    bl_idname = "NODE_EDITOR_PT_Improved_Search"

    def draw_header(self, context: bpy.types.Context) -> None:
        self.layout.label(text="", icon='VIEWZOOM')

    def draw(self, context):
        prefs_ = prefs.get_preferences(context)
        layout = self.layout
        layout.operator(PerformNodeSearch.bl_idname, text="Search", icon='VIEWZOOM')
        layout.operator(
            ToggleSearchOverlay.bl_idname,
            depress=ToggleSearchOverlay.handle is not None,
            text="Overlay",
            icon='OUTLINER_DATA_LIGHT',
        )

        if len(FOUND_NODES) > 0:
            row = layout.row()
            row.label(text=f"Found {len(FOUND_NODES)} node(s)")
            row.operator(ClearSearch.bl_idname, icon='PANEL_CLOSE', text="")
            layout.separator()
            row = layout.row()
            row.operator(SelectFoundNodes.bl_idname, text="Select")
            row.operator(CycleFoundNodes.bl_idname, text="Prev").direction = -1
            row.operator(CycleFoundNodes.bl_idname, text="Next").direction = 1

        layout.prop(prefs_, "highlight_color")
        layout.prop(prefs_, "border_attenuation", slider=True)
        layout.prop(prefs_, "border_size")
        layout.prop(prefs_, "text_size")

        col = layout.column(align=True)
        for node in FOUND_NODES:
            col.label(text=node.name)
            col.label(text=node.bl_idname)
            col.separator()

        col = layout.column(align=True)
        for node_tree, value in NODE_TREE_OCCURRENCES.items():
            col.label(text=node_tree.name)
            col.label(text=str(value))


CLASSES.append(ImprovedNodeSearchPanel)
