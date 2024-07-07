# copyright (c) Zdenek Dolezal 2024-*
# Improved Node Search - Powerful tool to find nodes in node trees.
# Author: Zdenek Dolezal
# Licence: GPL 3.0

# Thanks to 'user3597862' for the code snipped used to implement 'mouse_to_region_coords' method
# https://blender.stackexchange.com/questions/218096/translate-area-mouse-coordinates-to-the-the-node-editors-blackboard-coordinates

bl_info = {
    "name": "Improved Node Search",
    "author": "Zdenek Dolezal",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
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


KEYMAPS = []


def register():
    KEYMAPS.clear()

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager
    if wm.keyconfigs.addon is None:
        return

    km = wm.keyconfigs.addon.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new(search.PerformNodeSearch.bl_idname, 'F', 'PRESS', ctrl=True)
    KEYMAPS.append((km, kmi))


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

    if search.ToggleSearchOverlay.handle is not None:
        search.ToggleSearchOverlay.remove_draw_handler()

    for km, kmi in KEYMAPS:
        km.keymap_items.remove(kmi)

    KEYMAPS.clear()
