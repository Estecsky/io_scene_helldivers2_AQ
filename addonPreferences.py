import bpy
from .AQ_Prefs_HD2 import AQ_PublicClass
from . import addon_updater_ops
from bpy.props import BoolProperty, IntProperty


@addon_updater_ops.make_annotations
class HD2_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = AQ_PublicClass.AQ_ADDON_NAME
    
   # addon updater preferences
    auto_check_update: bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )  # type: ignore

    updater_interval_months: bpy.props.IntProperty(
        name="Months",
        description="Number of months between checking for updates",
        default=0,
        min=0,
    )  # type: ignore
    updater_interval_days: bpy.props.IntProperty(
        name="Days",
        description="Number of days between checking for updates",
        default=7,
        min=0,
    )  # type: ignore
    updater_interval_hours: bpy.props.IntProperty(
        name="Hours",
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23,
    )  # type: ignore
    updater_interval_minutes: bpy.props.IntProperty(
        name="Minutes",
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59,
    )  # type: ignore
    
    tga_Tex_Import_Switch : BoolProperty(name="TGA_Tex_Import_Switch",default = False,description = "开启TGA纹理导入开关，tga会自动转换为dds,文件输出目录为软件缓存目录")
    def draw(self, context):

        # layout = self.layout
        layout = self.layout
        layout.prop(self, "tga_Tex_Import_Switch",text="TGA纹理导入开关")
        addon_updater_ops.update_settings_ui(self, context)

def register():
    bpy.utils.register_class(HD2_AddonPreferences)


def unregister():
    bpy.utils.unregister_class(HD2_AddonPreferences)
