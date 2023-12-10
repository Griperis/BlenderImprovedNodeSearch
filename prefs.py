import bpy
import typing

class Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    highlight_color: bpy.props.FloatVectorProperty(
        name="Highlight Color",
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR',
        default=(1, 0.6, 0.1, 0.5)
    )

    border_attenuation: bpy.props.FloatProperty(
        name="Border Attenuation",
        min=0.0,
        max=1.0,
        default=0.6
    )

    border_size: bpy.props.FloatProperty(
        name="Border Size (px)",
        min=0.0,
        default=10.0
    )


def get_preferences(context: typing.Optional[bpy.types.Context] = None) -> Preferences:
    if context is None:
        context = bpy.context

    return context.preferences.addons[__package__].preferences