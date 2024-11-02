# copyright (c) Zdenek Dolezal 2024-*

import bpy
import os
import re
import typing
import collections
import itertools
from . import prefs
from . import draw


CLASSES = []
# Mapping of node tree -> number of occurrences in last search
NODE_TREE_NODES = {}
# Mapping of found nodes to number of occurances of searched nodes
NODE_TREE_OCCURRENCES = {}

# Pattern related values, when using regexp variant of search
PATTERN = re.Pattern | None
PATTERN_COMPILE_ERROR: str | None = None


FilterType = typing.Callable[[bpy.types.Node, str, bool], bool]


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
        self.node_tree_finds: dict[bpy.types.NodeTree, bpy.types.Node] = {}
        self.node_tree_leaf_nodes_count: dict[bpy.types.NodeTree, int] = collections.defaultdict(
            int
        )
        self.all_found_nodes: set[bpy.types.Node] = set()

    def search(self) -> set[bpy.types.Node]:
        self._search_and_recurse(self.node_tree)
        self.node_tree_leaf_nodes_count[self.node_tree] = self._leaf_nodes_count(self.node_tree)
        return self.all_found_nodes

    def _search_and_recurse(
        self, node_tree: bpy.types.NodeTree, depth: int = 0
    ) -> set[bpy.types.Node]:
        if node_tree in self.node_tree_finds:
            return self.node_tree_finds[node_tree]
        else:
            self.node_tree_finds[node_tree] = set()

        for node in node_tree.nodes:
            # Frames are not considered in the search currently
            if isinstance(node, bpy.types.NodeFrame):
                continue

            if (
                hasattr(node, "node_tree")
                and node.node_tree is not None
                and self.search_in_node_groups
                and node.node_tree != self.node_tree
            ):
                self._search_and_recurse(node.node_tree, depth + 1)
                # If any nodes are found inside the node group, we add the node group to the result
                if len(self.node_tree_finds[node.node_tree]) > 0:
                    self.node_tree_finds[node_tree].add(node)

            # If any filter returns True for given node, we consider it in the result
            for filter_ in self.filters:
                if filter_(node):
                    self.all_found_nodes.add(node)
                    self.node_tree_finds[node_tree].add(node)
                    break

        return self.all_found_nodes

    def _leaf_nodes_count(self, node_tree: bpy.types.NodeTree) -> int:
        if node_tree in self.node_tree_leaf_nodes_count:
            return self.node_tree_leaf_nodes_count[node_tree]

        for node in node_tree.nodes:
            if node not in self.node_tree_finds[node_tree]:
                continue

            if hasattr(node, "node_tree") and node.node_tree is not None and node.node_tree != self.node_tree:
                self.node_tree_leaf_nodes_count[node_tree] = self._leaf_nodes_count(node.node_tree)
            else:
                self.node_tree_leaf_nodes_count[node_tree] += 1

        return self.node_tree_leaf_nodes_count[node_tree]


def get_context_found_nodes(context: bpy.types.Context) -> set[bpy.types.Node]:
    """Returns found nodes based on the current context."""
    if not hasattr(context.space_data, "edit_tree"):
        return set()

    return NODE_TREE_NODES.get(context.space_data.edit_tree, set())


def get_all_found_nodes(include_nodegroups: bool = False) -> set[bpy.types.Node]:
    ret = set()
    for node in itertools.chain(*NODE_TREE_NODES.values()):
        if not include_nodegroups and hasattr(node, "node_tree"):
            continue

        ret.add(node)

    return ret


def search_string(
    search: str, value: str, prefs: prefs.Preferences, enable_regex: bool = True
) -> str:
    if enable_regex and prefs.use_regex:
        return PATTERN.match(value) is not None

    if prefs.match_case:
        return search in value
    return search.lower() in value.lower()


def node_name_filter(node: bpy.types.Node, name: str, prefs: prefs.Preferences) -> bool:
    return search_string(name, node.name, prefs)


def node_blidname_filter(node: bpy.types.Node, value: str, prefs: prefs.Preferences) -> bool:
    return search_string(value, node.bl_idname, prefs)


def node_label_filter(node: bpy.types.Node, value: str, prefs: prefs.Preferences) -> bool:
    return search_string(value, node.label, prefs)


def node_group_name_filter(node: bpy.types.Node, value: str, prefs: prefs.Preferences) -> bool:
    if not hasattr(node, "node_tree") or node.node_tree is None:
        return False
    return search_string(value, node.node_tree.name, prefs)


def attribute_filter(node: bpy.types.GeometryNode, name: str, prefs: prefs.Preferences) -> bool:
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
    searched_input = None
    if isinstance(node, bpy.types.GeometryNodeInputNamedAttribute):
        searched_input = node.inputs[0].default_value
    elif isinstance(node, bpy.types.GeometryNodeStoreNamedAttribute):
        searched_input = node.inputs[2].default_value
    elif isinstance(node, bpy.types.GeometryNodeRemoveAttribute):
        searched_input = node.inputs[1].default_value
    return search_string(name, searched_input, prefs, enable_regex=False)


def unconnected_node_filter(node: bpy.types.Node) -> bool:
    return len(node.outputs) > 0 and sum(output.is_linked for output in node.outputs) == 0


def missing_image_filter(node: bpy.types.Node) -> bool:
    if not hasattr(node, "image"):
        return False

    if node.image is None:
        return True

    image = typing.cast(bpy.types.Image, node.image)
    path = os.path.abspath(bpy.path.abspath(image.filepath))
    return not os.path.isfile(path)


def missing_node_group_filter(node: bpy.types.Node) -> bool:
    if not hasattr(node, "node_tree"):
        return False

    return node.node_tree is None


class ToggleSearchOverlay(bpy.types.Operator):
    bl_idname = "improved_node_search.toggle_overlay"
    bl_label = "Overlay Search Results"
    bl_description = "Toggle the visual display of the search results"

    handle = None

    def add_draw_handler(self, context: bpy.types.Context):
        ToggleSearchOverlay.handle = bpy.types.SpaceNodeEditor.draw_handler_add(
            draw.highlight_nodes,
            (context, NODE_TREE_NODES, NODE_TREE_OCCURRENCES),
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


def _search_updated(op: bpy.types.OperatorProperties, context: bpy.types.Context) -> None:
    global PATTERN
    global PATTERN_COMPILE_ERROR

    PATTERN = None
    PATTERN_COMPILE_ERROR = None
    # We treat the search always as a pattern, only show the error and use the pattern if
    # the user wants to use regex.
    try:
        PATTERN = re.compile(op.search)
    except re.error as e:
        print(f"Error compiling pattern: {e}")
        PATTERN_COMPILE_ERROR = str(e)


class PerformNodeSearch(bpy.types.Operator):
    bl_idname = "improved_node_search.search"
    bl_label = "Search"
    bl_description = "Search for nodes in the current node tree based on several criteria"
    bl_property = "search"

    search: bpy.props.StringProperty(
        name="Search",
        description="Text to search for based on other options",
        update=_search_updated,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return context.area.type == 'NODE_EDITOR' and context.region.type == 'WINDOW'

    def draw(self, context: bpy.types.Context):
        prefs_ = prefs.get_preferences(context)
        layout = self.layout
        if not context.area.ui_type.endswith(("NodeTree", "NodesTree")):
            layout.label(text="Node search only works in node editors", icon='ERROR')
            return

        is_regex_error = prefs_.use_regex and PATTERN_COMPILE_ERROR is not None
        row = layout.row(align=True)
        row.scale_y = 1.2
        row.alert = is_regex_error
        row.prop(
            self,
            "search",
            text="",
            placeholder=self._get_search_placeholder(prefs_),
            icon='VIEWZOOM',
        )
        # Create another row for the aligned icon, just so we can toggle the alert=False
        row = row.row(align=True)
        row.alert = False
        row.prop(prefs_, "use_regex", icon='SORTBYEXT', text="")
        row.prop(prefs_, "match_case", icon='SORTALPHA', text="")

        if prefs_.use_regex and is_regex_error:
            row = layout.row()
            row.alert = True
            row.label(text=f"Error: {PATTERN_COMPILE_ERROR}", icon='ERROR')

        col = layout.column(align=True)
        col.prop(prefs_, "search_in_name")
        col.prop(prefs_, "search_in_label")
        col.prop(prefs_, "search_in_blidname")

        layout.prop(prefs_, "search_in_node_groups")

        col = layout.column(align=True)
        col.prop(prefs_, "search_unconnected")
        col.prop(prefs_, "search_missing_images")
        col.prop(prefs_, "search_missing_node_groups")

        col = layout.column(align=True)
        if context.area.ui_type == 'GeometryNodeTree':
            col.prop(prefs_, "filter_by_attribute")
            if prefs_.filter_by_attribute:
                col.prop(prefs_, "attribute_search", text="", placeholder="Search in attributes")

        if len(NODE_TREE_NODES) > 0:
            layout.operator(ClearSearch.bl_idname, icon='PANEL_CLOSE', text="Clear Previous Search")

    def execute(self, context: bpy.types.Context):
        prefs_ = prefs.get_preferences(context)
        filters_ = set()

        if self._is_search_required(prefs_) and self.search == "":
            self.report({'WARNING'}, "No search input provided, provide search input")
            return {'CANCELLED'}

        if prefs_.use_regex and PATTERN is None and PATTERN_COMPILE_ERROR is not None:
            self.report({'ERROR'}, f"Provided regular expression is not valid")
            return {'CANCELLED'}

        if self.search != "":
            if prefs_.search_in_name:
                filters_.add(lambda x: node_name_filter(x, self.search, prefs_))
            if prefs_.search_in_label:
                filters_.add(lambda x: node_label_filter(x, self.search, prefs_))
            if prefs_.search_in_blidname:
                filters_.add(lambda x: node_blidname_filter(x, self.search, prefs_))
            if prefs_.search_in_node_groups:
                filters_.add(lambda x: node_group_name_filter(x, self.search, prefs_))

        if prefs_.filter_by_attribute and prefs_.attribute_search != "":
            filters_.add(lambda x: attribute_filter(x, prefs_.attribute_search, prefs_))

        if prefs_.search_unconnected:
            filters_.add(lambda x: unconnected_node_filter(x))
        if prefs_.search_missing_images:
            filters_.add(lambda x: missing_image_filter(x))
        if prefs_.search_missing_node_groups:
            filters_.add(lambda x: missing_node_group_filter(x))

        node_tree = context.space_data.edit_tree
        NODE_TREE_NODES.clear()
        NODE_TREE_OCCURRENCES.clear()
        node_search = NodeSearch(node_tree, filters_, prefs_.search_in_node_groups)
        found_nodes = node_search.search()
        # Set the overlay's node tree to the current one
        NODE_TREE_NODES.update(node_search.node_tree_finds)
        NODE_TREE_OCCURRENCES.update(node_search.node_tree_leaf_nodes_count)

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

    def _is_search_required(self, prefs_: prefs.Preferences) -> bool:
        return any(
            (
                prefs_.search_in_name,
                prefs_.search_in_label,
                prefs_.search_in_blidname,
            )
        )


CLASSES.append(PerformNodeSearch)


class ClearSearch(bpy.types.Operator):
    bl_idname = "improved_node_search.clear"
    bl_label = "Clear Search"
    bl_description = "Clear the search results"

    def execute(self, context: bpy.types.Context):
        NODE_TREE_NODES.clear()
        NODE_TREE_OCCURRENCES.clear()
        return {'FINISHED'}


CLASSES.append(ClearSearch)


class SelectFoundNodes(bpy.types.Operator):
    bl_idname = "improved_node_search.select_found"
    bl_label = "Select Found Nodes"
    bl_description = "Select all found nodes"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return hasattr(context.space_data, "node_tree")

    def execute(self, context: bpy.types.Context):
        bpy.ops.node.select_all(action='DESELECT')
        for node in get_context_found_nodes(context):
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
        return len(get_context_found_nodes(context)) > 0

    def execute(self, context: bpy.types.Context):
        new_index = CycleFoundNodes.index + self.direction
        found_nodes = get_context_found_nodes(context)
        # clamp next_index to boundaries of FOUND_NODES
        if new_index > len(found_nodes) - 1:
            new_index = 0
        elif new_index < 0:
            new_index = len(found_nodes) - 1

        # We sort the found nodes by name, as set is unordered
        node = sorted(list(found_nodes), key=lambda x: x.name)[new_index]

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

        found_nodes = get_all_found_nodes(include_nodegroups=True)
        if len(found_nodes) > 0:
            row = layout.row()
            row.label(text=f"Found {len(found_nodes)} node(s)")
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
            for node_tree, nodes in NODE_TREE_NODES.items():
                col = layout.column(align=True)
                col.label(text=node_tree.name)
                for node in nodes:
                    col.label(text=f"  {node.name}")


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


@bpy.app.handlers.persistent
def _depsgraph_update_pre(scene: bpy.types.Scene):
    for node_tree in list(NODE_TREE_NODES):
        nodes = list(NODE_TREE_NODES[node_tree])
        try:
            data_node_group = bpy.data.node_groups.get(node_tree.name)
        except ReferenceError:
            NODE_TREE_NODES.pop(node_tree)
            NODE_TREE_OCCURRENCES.pop(node_tree)
            continue

        if data_node_group is None:
            NODE_TREE_NODES.pop(node_tree)
            NODE_TREE_OCCURRENCES.pop(node_tree)
            continue

        for node in nodes:
            try:
                if node.name not in data_node_group.nodes:
                    NODE_TREE_NODES[node_tree].remove(node)
                    NODE_TREE_OCCURRENCES[node_tree] -= 1
            except UnicodeDecodeError:
                NODE_TREE_NODES[node_tree].remove(node)
                NODE_TREE_OCCURRENCES[node_tree] -= 1


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.app.handlers.depsgraph_update_pre.append(_depsgraph_update_pre)


def unregister():
    bpy.app.handlers.depsgraph_update_pre.remove(_depsgraph_update_pre)

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
