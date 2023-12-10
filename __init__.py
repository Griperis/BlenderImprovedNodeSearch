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
from . import search
from . import prefs


CLASSES = [
    prefs.Preferences,
] + search.CLASSES


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

    if search.ToggleSearchOverlay.handle is not None:
        search.ToggleSearchOverlay.remove_draw_handler()