# copyright (c) Zdenek Dolezal 2024-*

import bpy
import typing


class Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    use_regex: bpy.props.BoolProperty(
        name="Use Regular Expressions",
        description="If toggled, then the search will be done using regular expressions",
    )

    match_case: bpy.props.BoolProperty(
        name="Match Case",
        description="If toggled, then the search will be case sensitive",
    )

    exact_match: bpy.props.BoolProperty(
        name="Exact Match",
        description="If toggled, then only exact matches of the input will be searched",
    )

    highlight_color: bpy.props.FloatVectorProperty(
        name="Highlight Color",
        description="Highlight color of the found nodes overlay",
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR',
        default=(1, 0.6, 0.1, 0.5),
    )

    border_attenuation: bpy.props.FloatProperty(
        name="Border Attenuation",
        description="Attenuation of the border color",
        min=0.0,
        max=1.0,
        default=0.6,
    )

    border_size: bpy.props.FloatProperty(
        name="Border Size (px)",
        description="How large is the attenuated border in pixels",
        min=0.0,
        default=10.0,
    )

    text_size: bpy.props.FloatProperty(
        name="Text Size (px)",
        description="Size of numbers reffering to occurances in a node group in pixels",
        min=0.0,
        default=25.0,
    )

    search_in_name: bpy.props.BoolProperty(
        name="Search in \"Name\"",
        description="If toggled, then what is in \"Search\" will be searched in node \"Name\"",
        default=True,
    )
    search_in_label: bpy.props.BoolProperty(
        name="Search in \"Label\"",
        description="If toggled, then what is in \"Search\" will be searched in node \"Label\"",
        default=True,
    )
    search_in_blidname: bpy.props.BoolProperty(
        name="Search in \"Node Type\"",
        description="If toggled, then what is in \"Search\" will be searched in node \"Node Type\" (.bl_idname)",
        default=False,
    )
    search_in_node_groups: bpy.props.BoolProperty(
        name="Search in Node Groups",
        description="If toggled, then we will search also the inside of node groups in current node tree",
        default=True,
    )

    # Search for errors
    search_unconnected: bpy.props.BoolProperty(
        name="Search Disconnected Nodes",
        description="If toggled, the search will include nodes that are not connected to anything",
        default=False,
    )
    search_missing_images: bpy.props.BoolProperty(
        name="Search Missing Image Nodes",
        description="If toggled, the search will include nodes that have missing images",
        default=False,
    )
    search_missing_node_groups: bpy.props.BoolProperty(
        name="Search Missing Node Groups",
        description="If toggled, the search will include nodes that have missing node groups",
        default=False,
    )

    search_in_attribute: bpy.props.BoolProperty(
        name="Search in Attributes",
        description="If toggled, \"Attribute Search\" will be used to filter nodes by usage of specified attribute name",
        default=False,
    )
    attribute_search: bpy.props.StringProperty(
        name="Attribute Search",
        description="Text to search inside attributes when \"Filter by Attribute\" is toggled",
    )


def get_preferences(context: typing.Optional[bpy.types.Context] = None) -> Preferences:
    if context is None:
        context = bpy.context

    return context.preferences.addons[__package__].preferences
