import bpy
import os
from os.path import dirname, realpath, basename
from bpy.props import BoolProperty, IntProperty


class AQ_Prefs:

    @staticmethod
    def pref_():
        return bpy.context.preferences.addons[AQ_PublicClass.AQ_ADDON_NAME].preferences

    @property
    def pref(self):
        return self.pref_()

    @staticmethod
    def get_addon_prefs(addon_name=None):
        addon = AQ_PublicClass.AQ_ADDON_NAME if addon_name is None else addon_name
        return bpy.context.preferences.addons[addon].preferences


class AQ_PublicClass(AQ_Prefs):

    AQ_ADDON_NAME = basename(dirname(realpath(__file__)))
