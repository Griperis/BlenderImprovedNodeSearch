import bpy
import typing

# TODO: Support arbitrary Node Trees
def get_geometry_node_types_enum_items():
    for type_ in dir(bpy.types):
        if type_.startswith("GeometryNode"):
            yield (type_, type_, type_)


def get_compositor_node_types_enum_items():
    for type_ in dir(bpy.types):
        if type_.startswith("CompositorNode"):
            yield (type_, type_, type_)


def get_shader_node_types_enum_items():
    for type_ in dir(bpy.types):
        if type_.startswith("ShaderNode"):
            yield (type_, type_, type_)


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

    geometry_node_types: bpy.props.EnumProperty(
        items=lambda _, __: get_geometry_node_types_enum_items()
    )

    compositor_node_types: bpy.props.EnumProperty(
        items=lambda _, __: get_compositor_node_types_enum_items()
    )

    shader_node_types: bpy.props.EnumProperty(
        items=lambda _, __: get_shader_node_types_enum_items()
    )

    search: bpy.props.StringProperty()
    attribute_search: bpy.props.StringProperty()

    filter_by_type: bpy.props.BoolProperty()
    filter_by_attribute: bpy.props.BoolProperty()


def get_preferences(context: typing.Optional[bpy.types.Context] = None) -> Preferences:
    if context is None:
        context = bpy.context

    return context.preferences.addons[__package__].preferences