# copyright (c) Zdenek Dolezal 2024-*

import bpy
import typing
from . import prefs
from . import draw


CLASSES = []
# Set of found nodes for last search
FOUND_NODES = set()
# Mapping of node tree -> number of occurrences in last search
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


def node_blidname_filter(node: bpy.types.Node, value: str) -> bool:
    return value.lower() in node.bl_idname.lower()


def node_label_filter(node: bpy.types.Node, value: str) -> bool:
    return value.lower() in node.label.lower()


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

    # TODO: Finding if the node.inputs[x] is connected to other node or not
    # and use the value from there would be a improvement.
    searched_name = name.lower()
    if isinstance(node, bpy.types.GeometryNodeInputNamedAttribute):
        return node.inputs[0].default_value.lower() == searched_name
    elif isinstance(node, bpy.types.GeometryNodeStoreNamedAttribute):
        return node.inputs[2].default_value.lower() == searched_name
    elif isinstance(node, bpy.types.GeometryNodeRemoveAttribute):
        return node.inputs[1].default_value.lower() == searched_name
    return False


def ensure_search_result_valid():
    # TODO: Improve this, this crashes Blender, we need to be sure that we don't highlight and keep
    # references to nodes, that do not longer exist in the node tree.
    # Try except ReferenceError..., we have to do this at the right time
    if ToggleSearchOverlay.node_tree is None:
        return

    for node in list(FOUND_NODES):
        if node.name not in ToggleSearchOverlay.node_tree.nodes:
            FOUND_NODES.remove(node)
            print(f"Removing {node.name} from found nodes as it is no longer valid")
            if (
                hasattr(node, "node_tree")
                and node.node_tree is not None
                and node.node_tree in NODE_TREE_OCCURRENCES
            ):
                del NODE_TREE_OCCURRENCES[node.node_tree]
                print(
                    f"Removing {node.node_tree.name} from node tree occurrences as it is no longer valid"
                )


class ToggleSearchOverlay(bpy.types.Operator):
    bl_idname = "improved_node_search.toggle_overlay"
    bl_label = "Overlay Search Results"
    bl_description = "Toggle the visual display of the search results"

    handle = None
    # Node tree reference to draw only in the right context
    node_tree: bpy.types.NodeTree | None = None

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

        # TODO: This crashes Blender
        # ensure_search_result_valid()
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
    bl_idname = "improved_node_search.search"
    bl_label = "Search"
    bl_description = "Search for nodes in the current node tree based on several criteria"
    bl_property = "search"

    search: bpy.props.StringProperty(
        name="Search", description="Text to search for based on other options"
    )

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.area.type == 'NODE_EDITOR' and context.region.type == 'WINDOW'

    def draw(self, context: bpy.types.Context):
        prefs_ = prefs.get_preferences(context)
        layout = self.layout
        if not context.area.ui_type.endswith("NodeTree"):
            layout.label(text="Node search only works in node editors", icon='ERROR')
            return

        row = layout.row()
        row.scale_y = 1.2
        row.prop(
            self,
            "search",
            text="",
            placeholder=self._get_search_placeholder(prefs_),
            icon='VIEWZOOM',
        )
        layout.separator()

        col = layout.column(align=True)
        col.prop(prefs_, "search_in_name")
        col.prop(prefs_, "search_in_label")
        col.prop(prefs_, "search_in_blidname")

        layout.prop(prefs_, "search_in_node_groups")

        col = layout.column(align=True)
        if context.area.ui_type == 'GeometryNodeTree':
            col.prop(prefs_, "filter_by_attribute")
            if prefs_.filter_by_attribute:
                col.prop(prefs_, "attribute_search", text="", placeholder="Search in attributes")

    def execute(self, context: bpy.types.Context):
        prefs_ = prefs.get_preferences(context)
        filters_ = set()

        if (self.search == "" and not prefs_.filter_by_attribute) or (
            prefs_.attribute_search == "" and prefs_.filter_by_attribute
        ):
            self.report({'WARNING'}, "No search input provided")
            return {'CANCELLED'}

        if self.search != "":
            if prefs_.search_in_name:
                filters_.add(lambda x: node_name_filter(x, self.search))
            if prefs_.search_in_label:
                filters_.add(lambda x: node_label_filter(x, self.search))
            if prefs_.search_in_blidname:
                filters_.add(lambda x: node_blidname_filter(x, self.search))

        if prefs_.filter_by_attribute and prefs_.attribute_search != "":
            filters_.add(lambda x: attribute_filter(x, prefs_.attribute_search))

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

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        # Toggle overlay by default
        if ToggleSearchOverlay.handle is None:
            bpy.ops.improved_node_search.toggle_overlay('INVOKE_DEFAULT')

        return context.window_manager.invoke_props_dialog(self)

    def _get_search_placeholder(self, prefs_: prefs.Preferences) -> str:
        opts = []
        if prefs_.search_in_name:
            opts.append("Name")
        if prefs_.search_in_label:
            opts.append("Label")
        if prefs_.search_in_blidname:
            opts.append("Node Type")

        if len(opts) > 0:
            return f"Search in {', '.join(opts)}"
        else:
            return "Select something to search in"


CLASSES.append(PerformNodeSearch)


class ClearSearch(bpy.types.Operator):
    bl_idname = "improved_node_search.clear"
    bl_label = "Clear Search"
    bl_description = "Clear the search results"

    def execute(self, context: bpy.types.Context):
        FOUND_NODES.clear()
        return {'FINISHED'}


CLASSES.append(ClearSearch)


class SelectFoundNodes(bpy.types.Operator):
    bl_idname = "improved_node_search.select_found"
    bl_label = "Select Found Nodes"
    bl_description = "Select all found nodes"

    def execute(self, context: bpy.types.Context):
        bpy.ops.node.select_all(action='DESELECT')
        for node in FOUND_NODES:
            node.select = True
        return {'FINISHED'}


CLASSES.append(SelectFoundNodes)


class CycleFoundNodes(bpy.types.Operator):
    bl_idname = "improved_node_search.cycle_found"
    bl_label = "Cycle Found Nodes"
    bl_description = "Go to the next or previous found node"

    direction: bpy.props.IntProperty(default=1, min=-1, max=1)

    index = 0

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return len(FOUND_NODES) > 0

    def execute(self, context: bpy.types.Context):
        # asserted by poll
        assert len(FOUND_NODES) > 0

        new_index = CycleFoundNodes.index + self.direction
        # clamp next_index to boundaries of FOUND_NODES
        if new_index > len(FOUND_NODES) - 1:
            new_index = 0
        elif new_index < 0:
            new_index = len(FOUND_NODES) - 1

        # We sort the found nodes by name, as set is unordered
        node = sorted(list(FOUND_NODES), key=lambda x: x.name)[new_index]
        print(f"Trying to select {node.name}")

        bpy.ops.node.select_all(action='DESELECT')
        node.select = True
        bpy.ops.node.view_selected()
        node.select = False

        CycleFoundNodes.index = new_index
        return {'FINISHED'}


CLASSES.append(CycleFoundNodes)


class ImprovedNodeSearchMixin:
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Tool"


class ImprovedNodeSearchPanel(bpy.types.Panel, ImprovedNodeSearchMixin):
    bl_label = "Improved Search"
    bl_idname = "NODE_EDITOR_PT_Improved_Search"

    def draw_header(self, context: bpy.types.Context) -> None:
        self.layout.label(text="", icon='VIEWZOOM')

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator(PerformNodeSearch.bl_idname, text="Search", icon='VIEWZOOM')
        row.operator(
            ToggleSearchOverlay.bl_idname,
            depress=ToggleSearchOverlay.handle is not None,
            text="",
            icon='OUTLINER_DATA_LIGHT',
        )

        if len(FOUND_NODES) > 0:
            row = layout.row()
            row.label(text=f"Found {len(FOUND_NODES)} node(s)")
            row.operator(ClearSearch.bl_idname, icon='PANEL_CLOSE', text="")
            layout.separator()
            layout.operator(
                SelectFoundNodes.bl_idname, text="Select Found", icon='RESTRICT_SELECT_OFF'
            )
            row = layout.row(align=True)
            row.operator(CycleFoundNodes.bl_idname, text="Previous", icon='TRIA_LEFT').direction = (
                -1
            )
            row.operator(CycleFoundNodes.bl_idname, text="Next", icon='TRIA_RIGHT').direction = 1

        # Useful for debugging
        if False:
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


class ImprovedNodeSearchCustomizeDisplayPanel(bpy.types.Panel, ImprovedNodeSearchMixin):
    bl_label = "Display"
    bl_idname = "NODE_EDITOR_PT_Improved_Search_Customize_Display"
    bl_parent_id = ImprovedNodeSearchPanel.bl_idname

    def draw(self, context: bpy.types.Context) -> None:
        prefs_ = prefs.get_preferences(context)
        layout = self.layout
        layout.prop(prefs_, "highlight_color", text="")
        layout.prop(prefs_, "text_size")

        col = layout.column(align=True)
        col.prop(prefs_, "border_attenuation", slider=True)
        col.prop(prefs_, "border_size")


CLASSES.append(ImprovedNodeSearchCustomizeDisplayPanel)
