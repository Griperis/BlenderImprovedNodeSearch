# Blender Node Search - Powerful tool to find nodes in node trees.
# Author: Zdenek Dolezal
# Licence: GPL 3.0

# Thanks to 'user3597862' for the code snipped used to implement 'mouse_to_region_coords' method
# https://blender.stackexchange.com/questions/218096/translate-area-mouse-coordinates-to-the-the-node-editors-blackboard-coordinates

bl_info = {
    "name": "Node Search", # TODO: Node Finder?
    "author": "Zdenek Dolezal",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "",
    "description": "",
    "category": "Node",
}

import bpy
import typing

from . import draw

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


CLASSES = [
    draw.DrawHighlight
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)