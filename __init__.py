bl_info = {
    "name": "Helldivers 2 Archives",
    "blender": (4, 0, 0),
    "category": "Import-Export",
    "author": "kboykboy2, AQ_Echoo",
    "warning": "此为修改版",
    "version": (2, 0, 0),
    "doc_url": "https://github.com/Estecsky/io_scene_helldivers2_AQ"
}

#region Imports

# System
import ctypes, os, tempfile, subprocess, time, webbrowser, re
import random as r
from copy import deepcopy
import copy
from math import ceil , sqrt # type: ignore
from pathlib import Path

# Blender
import bpy, bmesh, mathutils
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, PointerProperty
from bpy.types import Panel, Operator, PropertyGroup, Scene, Menu

from .stingray.animation import StingrayAnimation, AnimationException
from .stingray.material import LoadShaderVariables, LoadShaderVariables_CN, StingrayMaterial,Global_ShaderVariables,Global_ShaderVariables_CN
from .stingray.bones import LoadBoneHashes, StingrayBones
from .stingray.texture import StingrayTexture


# Local
# NOTE: Not bothering to do importlib reloading shit because these modules are unlikely to be modified frequently enough to warrant testing without Blender restarts
from .utils.math import MakeTenBitUnsigned, TenBitUnsigned
from .utils.memoryStream import MemoryStream
from .utils.logger import PrettyPrint
from .utils.slim import is_slim_version, load_package, get_package_toc, slim_init
from .AQ_Prefs_HD2 import AQ_PublicClass

import zipfile
import configparser
import struct
import concurrent.futures
from . import addon_updater_ops
from . import addonPreferences
from . import get_update_archivelistCN
#endregion

#region Global Variables

AddonPath = os.path.dirname(__file__)
BlenderAddonsPath = os.path.dirname(AddonPath)

Global_texconvpath         = f"{AddonPath}/deps/texconv.exe"
Global_palettepath         = f"{AddonPath}/deps/NormalPalette.dat"
Global_materialpath        = f"{AddonPath}/materials"
Global_typehashpath        = f"{AddonPath}/hashlists/typehash.txt"
Global_filehashpath        = f"{AddonPath}/hashlists/filehash.txt"
Global_friendlynamespath   = f"{AddonPath}/hashlists/friendlynames.txt"
Global_variablespath       = f"{AddonPath}/hashlists/shadervariables.txt"
Global_bonehashpath      = f"{AddonPath}/hashlists/bonehash.txt"

Global_variablesCNpath     = f"{AddonPath}/hashlists/shadervariables_combine_CN.txt"
Global_updatearchivelistCNpath = f"{AddonPath}/hashlists/update_archive_listCN.txt"

Global_configpath          = f"{BlenderAddonsPath}/io_scene_helldivers2_AQ.ini"
Global_defaultgamepath     = r"C:\Program Files (x86)\Steam\steamapps\common\Helldivers 2\data\ "
Global_defaultgamepath     = Global_defaultgamepath[:len(Global_defaultgamepath) - 1]
Global_gamepath            = ""
Global_gamepathIsValid = False

Global_BoneNames = {}

Global_SectionHeader = "---Helldivers 2 AQ魔改---"


Global_updatearchivelistCN_list = []
Global_PatchBasePath = ""
Global_Foldouts = []
#endregion
#region Common Hashes & Lookups

CompositeUnitID = 14191111524867688662
UnitID = 16187218042980615487
TexID  = 14790446551990181426
MaterialID  = 16915718763308572383
BoneID = 1792059921637536489
WwiseBankID = 6006249203084351385
WwiseDepID = 12624162998411505776
WwiseStreamID = 5785811756662211598
WwiseMetaDataID = 15351235653606224144
ParticleID = 12112766700566326628
AnimationID = 10600967118105529382
StateMachineID = 11855396184103720540
StringID = 979299457696010195
PhysicsID = 6877563742545042104

TextureTypeLookup = {
    "original": ("pbr: ", 
                 "",
                 "", 
                 "alpha mask: ",
                 "",
                 "normal: ",
                 "",
                 "sss color: ",
                 "", 
                 "color: ",
                 "", 
                 "", 
                 ""),
    "basic": ("pbr: ", "color: ", "normal: "),
    "basic+": (
        "PBR: ",
        "Base Color: ",
        "Normal: "
    ),
    "basic+Fixed": (
        "PBR: ",
        "Base Color: ",
        "Normal: "
    ),
    "bloom":  ("normal/ao/cavity: ",
                 "emission: ",
                 "color/metallic: "
    ),
    "glass": (
        "Glass stain: ",""
    ),
    "advanced_default": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_yellow": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_orange": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_red": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_pink": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_purple": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_dark-blue": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_blue": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_light-blue": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_blue-green": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "advanced_green": (
    "",
    "",
    "Normal/AO/Roughness: ",
    "Metallic: ",
    "",
    "Color/Emission Mask: ",
    "",
    "",
    "",
    "",
    ""
    ),
    "flowing": (
        "",
        "Normal_1: ",
        "Normal_2: ",
        "Mask: ",
        ""
    ),
    "alphaclip": (
        "Normal/AO/Roughness: ",
        "Alpha Mask: ",
        "Base Color/Metallic: "
    ),

    
    
}

Global_Materials = (
        ("bloom", "Bloom", "A bloom material with two color, normal map which does not render in the UI"),
        ("original", "Original", "The original template used for all mods uploaded to Nexus prior to the addon's public release, which is bloated with additional unnecessary textures. Sourced from a terminid."),
        ("advanced_default", "Advanced 默认无光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),   
        ("advanced_orange", "Advanced 橙光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_yellow", "Advanced 黄光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_red", "Advanced 红光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_pink", "Advanced 粉光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_purple", "Advanced 紫光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_dark-blue", "Advanced 深蓝光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_blue", "Advanced 蓝光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_light-blue", "Advanced 浅蓝光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_blue-green", "Advanced 蓝绿光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("advanced_green", "Advanced 绿光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),

        ("flowing","流光","光能电塔的流光材质，材质参数中切换uv空间改成负的就是从上往下，正的是从下往上"),
        ("glass", "透明玻璃", "透明玻璃，不知道能干嘛，自己猜()"),
        ("basic+Fixed", "Basic+", "A basic material with a color, normal, and PBR map which renders in the UI, Sourced from a SEAF NPC"),
        ("basic", "Basic", "A basic material with a color, normal, and PBR map. Sourced from a trash bag prop."),
        ("alphaclip", "Alpha Clip", "金属度在颜色贴图的alpha通道，A material that supports an alpha mask which does not render in the UI. Sourced from a skeleton pile")
    )

Global_MaterialParentIDs = {
    15235712479575174153 : "bloom",
    6101987038150196875 : "original",
    17265463703140804126 : "advanced_default",
    16342443352312747293 : "flowing",
    9576304397847579354 : "glass",
    8580182439406660688 : "basic+Fixed",
    15356477064658408677 : "basic",
    15586118709890920288 : "alphaclip",
    17720495965476876300 : "armorlut",
    # 9576304397847579354  : "translucent",
}

#endregion

#region Functions: Miscellaneous


def EntriesFromStrings(file_id_string, type_id_string):
    FileIDs = file_id_string.split(',')
    TypeIDs = type_id_string.split(',')
    Entries = []
    for n in range(len(FileIDs)):
        if FileIDs[n] != "":
            Entries.append(Global_TocManager.GetEntry(int(FileIDs[n]), int(TypeIDs[n])))
    return Entries

def EntriesFromString(file_id_string, TypeID):
    FileIDs = file_id_string.split(',')
    Entries = []
    for n in range(len(FileIDs)):
        if FileIDs[n] != "":
            Entries.append(Global_TocManager.GetEntry(int(FileIDs[n]), int(TypeID)))
    return Entries

def IDsFromString(file_id_string):
    FileIDs = file_id_string.split(',')
    Entries = []
    for n in range(len(FileIDs)):
        if FileIDs[n] != "":
            Entries.append(int(FileIDs[n]))
    return Entries

def GetDisplayData():
    # Set display archive TODO: Global_TocManager.LastSelected Draw Index could be wrong if we switch to patch only mode, that should be fixed
    DisplayTocEntries = []
    DisplayTocTypes   = []
    DisplayTocPatchPath = ""
    DisplayTocArchivePath = ""
    DisplayTocPatchPath_Add = ""
    DisplayArchive = Global_TocManager.ActiveArchive
    if bpy.context.scene.Hd2ToolPanelSettings.PatchOnly:
        if Global_TocManager.ActivePatch != None:
            DisplayTocEntries = [[Entry, True] for Entry in Global_TocManager.ActivePatch.TocEntries]
            DisplayTocTypes   = Global_TocManager.ActivePatch.TocTypes
            DisplayTocPatchPath = Global_TocManager.ActivePatch.Path
            DisplayTocPatchPath_Add = Global_TocManager.ActivePatch.Path
    elif Global_TocManager.ActiveArchive != None:
        DisplayTocEntries = [[Entry, False] for Entry in Global_TocManager.ActiveArchive.TocEntries]
        DisplayTocTypes   = [Type for Type in Global_TocManager.ActiveArchive.TocTypes]
        DisplayTocArchivePath = Global_TocManager.ActiveArchive.Path
        AddedTypes   = [Type.TypeID for Type in DisplayTocTypes]
        AddedEntries = [Entry[0].FileID for Entry in DisplayTocEntries]
        if Global_TocManager.ActivePatch != None:
            for Type in Global_TocManager.ActivePatch.TocTypes:
                if Type.TypeID not in AddedTypes:
                    AddedTypes.append(Type.TypeID)
                    DisplayTocTypes.append(Type)
            for Entry in Global_TocManager.ActivePatch.TocEntries:
                if Entry.FileID not in AddedEntries:
                    AddedEntries.append(Entry.FileID)
                    DisplayTocEntries.append([Entry, True])
        try:
            DisplayTocPatchPath_Add = Global_TocManager.ActivePatch.Path
            DisplayTocPatchPath = Global_TocManager.ActivePatch.Path
        except:
            DisplayTocPatchPath = ""
            DisplayTocPatchPath_Add = ""
    elif Global_TocManager.ActivePatch != None:
        # DisplayTocEntries_Add = [[Entry, True] for Entry in Global_TocManager.ActivePatch.TocEntries]
        # DisplayTocTypes_Add   = Global_TocManager.ActivePatch.TocTypes
        DisplayTocPatchPath_Add = Global_TocManager.ActivePatch.Path
        
    return [DisplayTocEntries, DisplayTocTypes, DisplayTocArchivePath, DisplayTocPatchPath,
            DisplayTocPatchPath_Add]

#endregion

#region Functions: Blender

# 检查材质名称是否以'.001'结尾
def CheckValidMaterial(obj, slot_index):
    material = obj.material_slots[slot_index].material
    if material.name.find(".0") != -1:
        original_material_name = material.name[:-4]
        
        target_material = bpy.data.materials.get(original_material_name)
        
        if target_material:
            obj.material_slots[slot_index].material = target_material
            
            material_users = material.users
            if material_users <= 0:
                bpy.data.materials.remove(material)
        else:
            PrettyPrint("尝试替换为正确的材质名: " + material.name + "该材质不存在，正在新建")
            AddMaterialToBlend_EMPTY(original_material_name)
            new_material = bpy.data.materials.get(original_material_name)
            obj.material_slots[slot_index].material = new_material
            
            material_users = material.users
            if material_users <= 0:
                bpy.data.materials.remove(material)
                
        PrettyPrint("材质清理完成")


def duplicate(obj, data=True, actions=True, collection=None):
    obj_copy = obj.copy()
    if data:
        obj_copy.data = obj_copy.data.copy()
    if actions and obj_copy.animation_data:
        if obj_copy.animation_data.action:
            obj_copy.animation_data.action = obj_copy.animation_data.action.copy()
    bpy.context.collection.objects.link(obj_copy)
    return obj_copy

def PrepareMesh(og_object):
    object = duplicate(og_object)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = object
    # split UV seams
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.seams_from_islands()
    except: PrettyPrint("Failed to create seams from UV islands. This is not fatal, but will likely cause undesirable results in-game", "warn")
    bpy.ops.object.mode_set(mode='OBJECT')

    bm = bmesh.new()
    bm.from_mesh(object.data)

    # get all sharp edges and uv seams
    sharp_edges = [e for e in bm.edges if not e.smooth]
    boundary_seams = [e for e in bm.edges if e.seam]
    # split edges
    bmesh.ops.split_edges(bm, edges=sharp_edges)
    bmesh.ops.split_edges(bm, edges=boundary_seams)
    # update mesh
    bm.to_mesh(object.data)
    bm.clear()
    # transfer normals
    modifier = object.modifiers.new("EXPORT_NORMAL_TRANSFER", 'DATA_TRANSFER')
    bpy.context.object.modifiers[modifier.name].data_types_loops = {'CUSTOM_NORMAL'}
    bpy.context.object.modifiers[modifier.name].object = og_object
    bpy.context.object.modifiers[modifier.name].use_loop_data = True
    bpy.context.object.modifiers[modifier.name].loop_mapping = 'TOPOLOGY'
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    # triangulate
    modifier = object.modifiers.new("EXPORT_TRIANGULATE", 'TRIANGULATE')
    bpy.context.object.modifiers[modifier.name].keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    # adjust weights
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    try:
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    except: pass

    return object

def GetMeshData(og_object, Global_TocManager, Global_BoneNames):
    global Global_palettepath
    object = PrepareMesh(og_object)
    bpy.context.view_layer.objects.active = object
    mesh = object.data

    vertices    = [ [vert.co[0], vert.co[1], vert.co[2]] for vert in mesh.vertices]
    normals     = [ [vert.normal[0], vert.normal[1], vert.normal[2]] for vert in mesh.vertices]
    tangents    = [ [vert.normal[0], vert.normal[1], vert.normal[2]] for vert in mesh.vertices]
    bitangents  = [ [vert.normal[0], vert.normal[1], vert.normal[2]] for vert in mesh.vertices]
    colors      = [[0,0,0,0] for n in range(len(vertices))]
    uvs         = []
    weights     = [[0,0,0,0] for n in range(len(vertices))]
    boneIndices = []
    faces       = []
    materials   = [ RawMaterialClass() for idx in range(len(object.material_slots))]
    mat_count = {}
    for idx in range(len(object.material_slots)):
        try:
            mat_id = int(object.material_slots[idx].name)
        except:
            raise Exception("Material name must be a number")
        if mat_id not in mat_count:
            mat_count[mat_id] = -1
        mat_count[mat_id] += 1
        materials[idx].IDFromName(og_object['Z_ObjectID'], str(mat_id), mat_count[mat_id])

    # get vertex color
    if mesh.vertex_colors:
        color_layer = mesh.vertex_colors.active
        for face in object.data.polygons:
            if color_layer == None: 
                PrettyPrint(f"{og_object.name} Color Layer does not exist", 'ERROR')
                break
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                col = color_layer.data[loop_idx].color
                colors[vert_idx] = [col[0], col[1], col[2], col[3]]

    # get normals, tangents, bitangents
    #mesh.calc_tangents()
    # 4.3 compatibility change
    if bpy.app.version[0] >= 4 and bpy.app.version[1] == 0:
        if not mesh.has_custom_normals:
            mesh.create_normals_split()
        mesh.calc_normals_split()
        
    for loop in mesh.loops:
        normals[loop.vertex_index]    = loop.normal.normalized()
        #tangents[loop.vertex_index]   = loop.tangent.normalized()
        #bitangents[loop.vertex_index] = loop.bitangent.normalized()
    # if fuckywuckynormalwormal do this bullshit
    #LoadNormalPalette()
    #normals = NormalsFromPalette(normals)
    # get uvs
    for uvlayer in object.data.uv_layers:
        if len(uvs) >= 3:
            break
        texCoord = [[0,0] for vert in mesh.vertices]
        for face in object.data.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                texCoord[vert_idx] = [uvlayer.data[loop_idx].uv[0], uvlayer.data[loop_idx].uv[1]*-1 + 1]
        uvs.append(texCoord)

    # get weights
    vert_idx = 0
    numInfluences = 4
    stingray_mesh_entry = Global_TocManager.GetEntry(int(og_object["Z_ObjectID"]), int(UnitID), IgnorePatch=False, SearchAll=True)
    if stingray_mesh_entry:
        if not stingray_mesh_entry.IsLoaded: stingray_mesh_entry.Load(True, False)
        stingray_mesh_entry = stingray_mesh_entry.LoadedData
    else:
        raise Exception(f"Unable to get mesh entry {og_object['Z_ObjectID']}")
    bone_info = stingray_mesh_entry.BoneInfoArray
    transform_info = stingray_mesh_entry.TransformInfo
    lod_index = og_object["BoneInfoIndex"]
    bone_names = []
    if not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
        if len(object.vertex_groups) > 0:
            for g in object.vertex_groups:
                bone_names.append(g.name)
            remap_info = [bone_names for _ in range(len(object.material_slots))]
            bone_info[lod_index].SetRemap(remap_info, transform_info)
        
        vertex_to_material_index = [5000 for _ in range(len(mesh.vertices))]
        for polygon in mesh.polygons:
            for vertex in polygon.vertices:
                vertex_to_material_index[vertex] = polygon.material_index
    
    if len(object.vertex_groups) > 0:
        for index, vertex in enumerate(mesh.vertices):
            group_idx = 0
            for group in vertex.groups:
                # limit influences
                if group_idx >= numInfluences:
                    break
                if group.weight > 0.001:
                    vertex_group        = object.vertex_groups[group.group]
                    vertex_group_name   = vertex_group.name
                    
                    #
                    # CHANGE THIS TO SUPPORT THE NEW BONE NAMES
                    # HOW TO ACCESS transform_info OF STINGRAY MESH??
                    if bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
                        parts               = vertex_group_name.split("_")
                        HDGroupIndex        = int(parts[0])
                        HDBoneIndex         = int(parts[1])
                    else:
                        material_idx = vertex_to_material_index[index]
                        try:
                            name_hash = int(vertex_group_name)
                        except ValueError:
                            name_hash = murmur32_hash(vertex_group_name.encode("utf-8"))
                        HDGroupIndex = 0
                        try:
                            real_index = transform_info.NameHashes.index(name_hash)
                        except ValueError:
                            existing_names = []
                            for i, h in enumerate(transform_info.NameHashes):
                                try:
                                    if i in bone_info[lod_index].RealIndices:
                                        existing_names.append(Global_BoneNames[h])
                                except KeyError:
                                    existing_names.append(str(h))
                                except IndexError:
                                    pass
                            if object:
                                PrettyPrint(f"Deleting object early and exiting weight painting mode...", 'error')
                                bpy.ops.object.mode_set(mode='OBJECT')
                                bpy.data.objects.remove(object, do_unlink=True)
                            raise Exception(f"\n\nVertex Group: {vertex_group_name} is not a valid vertex group for the model.\nIf you are using legacy weight names, make sure you enable the option in the settings.\n\nValid vertex group names: {existing_names}")
                        try:
                            HDBoneIndex = bone_info[lod_index].GetRemappedIndex(real_index, material_idx)
                        except (ValueError, IndexError): # bone index not in remap because the bone is not in the LOD bone data
                            continue
                            
                    # get real index from remapped index -> hashIndex = bone_info[mesh.LodIndex].GetRealIndex(bone_index); boneHash = transform_info.NameHashes[hashIndex]
                    # want to get remapped index from bone name
                    # hash = ...
                    # real_index = transform_info.NameHashes.index(hash)
                    # remap = bone_info[mesh.LodIndex].GetRemappedIndex(real_index)
                    if HDGroupIndex+1 > len(boneIndices):
                        dif = HDGroupIndex+1 - len(boneIndices)
                        boneIndices.extend([[[0,0,0,0] for n in range(len(vertices))]]*dif)
                    boneIndices[HDGroupIndex][vert_idx][group_idx] = HDBoneIndex
                    weights[vert_idx][group_idx] = group.weight
                    group_idx += 1
            vert_idx += 1
    else:
        boneIndices = []
        weights     = []
        
    #bpy.ops.object.mode_set(mode='POSE')
    # check option for saving bones
    # get armature object
    prev_obj = bpy.context.view_layer.objects.active
    prev_objs = bpy.context.selected_objects
    prev_mode = prev_obj.mode
    armature_obj = None
    for modifier in og_object.modifiers:
        if modifier.type == "ARMATURE":
            armature_obj = modifier.object
            break
    if armature_obj is not None:
        was_hidden = armature_obj.hide_get()
        armature_obj.hide_set(False)
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in armature_obj.data.edit_bones: # I'd like to use edit bones but it doesn't work for some reason
            PrettyPrint(bone.name)
            try:
                name_hash = int(bone.name)
            except ValueError:
                name_hash = murmur32_hash(bone.name.encode("utf-8"))
            try:
                transform_index = transform_info.NameHashes.index(name_hash)
            except ValueError:
                PrettyPrint(f"Failed to write data for bone: {bone.name}. This may be intended", 'warn')
                continue
                
            m = bone.matrix.transposed()
            transform_matrix = StingrayMatrix4x4()
            transform_matrix.v = [
                m[0][0], m[0][1], m[0][2], m[0][3],
                m[1][0], m[1][1], m[1][2], m[1][3],
                m[2][0], m[2][1], m[2][2], m[2][3],
                m[3][0], m[3][1], m[3][2], m[3][3]
            ]
            transform_info.TransformMatrices[transform_index] = transform_matrix
            if bone.parent:
                parent_matrix = bone.parent.matrix
                local_transform_matrix = parent_matrix.inverted() @ bone.matrix
                translation, rotation, scale = local_transform_matrix.decompose()
                rotation = rotation.to_matrix()
                transform_local = StingrayLocalTransform()
                transform_local.rot.x = [rotation[0][0], rotation[1][0], rotation[2][0]]
                transform_local.rot.y = [rotation[0][1], rotation[1][1], rotation[2][1]]
                transform_local.rot.z = [rotation[0][2], rotation[1][2], rotation[2][2]]
                transform_local.pos = translation
                transform_local.scale = scale
                transform_info.Transforms[transform_index] = transform_local
            else:
                transform_local = StingrayLocalTransform()
                transform_info.Transforms[transform_index] = transform_local
                
            # matrices in bone_info are the inverted joint matrices (for some reason)
            # and also relative to the mesh transform
            mesh_info_index = og_object["MeshInfoIndex"]
            mesh_info = stingray_mesh_entry.MeshInfoArray[mesh_info_index]
            origin_transform = transform_info.TransformMatrices[mesh_info.TransformIndex].ToLocalTransform()
            origin_transform_matrix = mathutils.Matrix.LocRotScale(origin_transform.pos, 
            mathutils.Matrix([origin_transform.rot.x, origin_transform.rot.y, origin_transform.rot.z]), 
            origin_transform.scale).inverted()
            
            for b in bone_info:
                if transform_index in b.RealIndices:
                    b_index = b.RealIndices.index(transform_index)
                    m = (origin_transform_matrix @ bone.matrix).inverted().transposed()
                    transform_matrix = StingrayMatrix4x4()
                    transform_matrix.v = [
                        m[0][0], m[0][1], m[0][2], m[0][3],
                        m[1][0], m[1][1], m[1][2], m[1][3],
                        m[2][0], m[2][1], m[2][2], m[2][3],
                        m[3][0], m[3][1], m[3][2], m[3][3]
                    ]
                    b.Bones[b_index] = transform_matrix

        armature_obj.hide_set(was_hidden)
        for obj in prev_objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = prev_obj
        bpy.ops.object.mode_set(mode=prev_mode)
    #bpy.ops.object.mode_set(mode='OBJECT')
    # get faces
    temp_faces = [[] for n in range(len(object.material_slots))]
    for f in mesh.polygons:
        temp_faces[f.material_index].append([f.vertices[0], f.vertices[1], f.vertices[2]])
        materials[f.material_index].NumIndices += 3
    for tmp in temp_faces: faces.extend(tmp)

    NewMesh = RawMeshClass()
    NewMesh.VertexPositions     = vertices
    NewMesh.VertexNormals       = normals
    #NewMesh.VertexTangents      = tangents
    #NewMesh.VertexBiTangents    = bitangents
    NewMesh.VertexColors        = colors
    NewMesh.VertexUVs           = uvs
    NewMesh.VertexWeights       = weights
    NewMesh.VertexBoneIndices   = boneIndices
    NewMesh.Indices             = faces
    NewMesh.Materials           = materials
    NewMesh.MeshInfoIndex       = og_object["MeshInfoIndex"]
    NewMesh.DEV_BoneInfoIndex   = og_object["BoneInfoIndex"]
    NewMesh.LodIndex            = og_object["BoneInfoIndex"]
    if len(vertices) > 0xffff: NewMesh.DEV_Use32BitIndices = True
    matNum = 0
    for material in NewMesh.Materials:
        try:
            material.DEV_BoneInfoOverride = int(og_object[f"matslot{matNum}"])
        except: pass
        matNum += 1

    if object is not None and object.name:
        PrettyPrint(f"Removing {object.name}")
        bpy.data.objects.remove(object, do_unlink=True)
    else:
        PrettyPrint(f"Current object: {object}")
    return NewMesh

def GetObjectsMeshData(Global_TocManager, Global_BoneNames):
    objects = bpy.context.selected_objects
    bpy.ops.object.select_all(action='DESELECT')
    data = {}
    for object in objects:
        if object.type != 'MESH':
            continue
        ID = object["Z_ObjectID"]
        MeshData = GetMeshData(object, Global_TocManager, Global_BoneNames)
        try:
            data[ID][MeshData.MeshInfoIndex] = MeshData
        except:
            data[ID] = {MeshData.MeshInfoIndex: MeshData}
    return data


def NameFromMesh(mesh, id, customization_info, bone_names, use_sufix=True):
    # generate name
    name = str(id)
    if customization_info.BodyType != "":
        BodyType    = customization_info.BodyType.replace("HelldiverCustomizationBodyType_", "")
        Slot        = customization_info.Slot.replace("HelldiverCustomizationSlot_", "")
        Weight      = customization_info.Weight.replace("HelldiverCustomizationWeight_", "")
        PieceType   = customization_info.PieceType.replace("HelldiverCustomizationPieceType_", "")
        name = Slot+"_"+PieceType+"_"+BodyType
    name_sufix = "_lod"+str(mesh.LodIndex)
    if mesh.LodIndex == -1:
        name_sufix = "_mesh"+str(mesh.MeshInfoIndex)
    if mesh.IsPhysicsBody():
        name_sufix = "_phys"+str(mesh.MeshInfoIndex)
    if use_sufix: name = name + name_sufix

    if use_sufix and bone_names != None:
        for bone_name in bone_names:
            if murmur32_hash(bone_name.encode()) == mesh.UnitID:
                name = bone_name

    return name

def CreateModel(stingray_unit, id, Global_BoneNames):
    addon_prefs = AQ_PublicClass.get_addon_prefs()
    model, customization_info, bone_names, transform_info, bone_info = stingray_unit.RawMeshes, stingray_unit.CustomizationInfo, stingray_unit.BoneNames, stingray_unit.TransformInfo, stingray_unit.BoneInfoArray

    if len(model) < 1: return
    # Make collection
    old_collection = bpy.context.collection
    if addon_prefs.MakeCollections:
        new_collection = bpy.data.collections.new(NameFromMesh(model[0], id, customization_info, bone_names, False))
        old_collection.children.link(new_collection)
    else:
        new_collection = old_collection
    # Make Meshes
    for mesh in model:
        # check lod
        if not bpy.context.scene.Hd2ToolPanelSettings.ImportLods and mesh.IsLod():
            continue
        # check physics
        if not bpy.context.scene.Hd2ToolPanelSettings.ImportPhysics and mesh.IsPhysicsBody():
            continue
        if not addon_prefs.ImportStatic and mesh.IsStaticMesh():
            continue
        # do safety check
        for face in mesh.Indices:
            for index in face:
                if index > len(mesh.VertexPositions):
                    raise Exception("Bad Mesh Parse: indices do not match vertices")
        # generate name
        name = NameFromMesh(mesh, id, customization_info, bone_names)

        # create mesh
        new_mesh = bpy.data.meshes.new(name)
        #new_mesh.from_pydata(mesh.VertexPositions, [], [])
        new_mesh.from_pydata(mesh.VertexPositions, [], mesh.Indices)
        new_mesh.update()
        # make object from mesh
        new_object = bpy.data.objects.new(name, new_mesh)
        # set transform
        local_transform = mesh.DEV_Transform.ToLocalTransform()
        new_object.scale = local_transform.scale
        new_object.location = local_transform.pos
        new_object.rotation_mode = 'QUATERNION'
        new_object.rotation_quaternion = mathutils.Matrix([local_transform.rot.x, local_transform.rot.y, local_transform.rot.z]).to_quaternion()


        # set object properties
        new_object["MeshInfoIndex"] = mesh.MeshInfoIndex
        new_object["BoneInfoIndex"] = mesh.LodIndex
        new_object["Z_ObjectID"]      = str(id)
        new_object["Z_SwapID_0"] = ""
        new_object["Z_SwapID_1"] = ""
        new_object["Z_SwapID_2"] = ""
        new_object["Z_SwapID_3"] = ""
        new_object["Z_SwapID_4"] = ""
        if customization_info.BodyType != "":
            new_object["Z_CustomizationBodyType"] = customization_info.BodyType
            new_object["Z_CustomizationSlot"]     = customization_info.Slot
            new_object["Z_CustomizationWeight"]   = customization_info.Weight
            new_object["Z_CustomizationPieceType"]= customization_info.PieceType
        if mesh.IsPhysicsBody():
            new_object.display_type = 'WIRE'

        # add object to scene collection
        new_collection.objects.link(new_object)
        # -- || ASSIGN NORMALS || -- #
        if len(mesh.VertexNormals) == len(mesh.VertexPositions):
            # 4.3 compatibility change
            if bpy.app.version[0] >= 4 and bpy.app.version[1] >= 1:
                new_mesh.shade_smooth()
            else:
                new_mesh.use_auto_smooth = True
            
            new_mesh.polygons.foreach_set('use_smooth',  [True] * len(new_mesh.polygons))
            if not isinstance(mesh.VertexNormals[0], int):
                new_mesh.normals_split_custom_set_from_vertices(mesh.VertexNormals)

        # -- || ASSIGN VERTEX COLORS || -- #
        if len(mesh.VertexColors) == len(mesh.VertexPositions):
            color_layer = new_mesh.vertex_colors.new()
            for face in new_mesh.polygons:
                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                    color_layer.data[loop_idx].color = (mesh.VertexColors[vert_idx][0], mesh.VertexColors[vert_idx][1], mesh.VertexColors[vert_idx][2], mesh.VertexColors[vert_idx][3])
        # -- || ASSIGN UVS || -- #
        for uvs in mesh.VertexUVs:
            uvlayer = new_mesh.uv_layers.new()
            new_mesh.uv_layers.active = uvlayer
            for face in new_mesh.polygons:
                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                    uvlayer.data[loop_idx].uv = (uvs[vert_idx][0], uvs[vert_idx][1]*-1 + 1)
        # -- || ASSIGN WEIGHTS || -- #
        created_groups = []
        available_bones = []
        for i, h in enumerate(transform_info.NameHashes):
            try:
                if i in bone_info[mesh.LodIndex].RealIndices:
                    available_bones.append(Global_BoneNames.get(h, str(h)))
            except IndexError:
                pass
        vertex_to_material_index = [5000]*len(mesh.VertexPositions)
        for mat_idx, mat in enumerate(mesh.Materials):
            for face in mesh.Indices[mat.StartIndex//3:(mat.StartIndex//3+mat.NumIndices//3)]:
                for vert_idx in face:
                    vertex_to_material_index[vert_idx] = mat_idx
        for vertex_idx in range(len(mesh.VertexWeights)):
            weights      = mesh.VertexWeights[vertex_idx]
            index_groups = [Indices[vertex_idx] for Indices in mesh.VertexBoneIndices]
            for group_index, indices in enumerate(index_groups):
                if bpy.context.scene.Hd2ToolPanelSettings.ImportGroup0 and group_index != 0:
                    continue
                if type(weights) != list:
                    weights = [weights]
                for weight_idx in range(len(weights)):
                    weight_value = weights[weight_idx]
                    bone_index   = indices[weight_idx]
                    if not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
                        try:
                            hashIndex = bone_info[mesh.LodIndex].GetRealIndex(bone_index, vertex_to_material_index[vertex_idx])
                        except:
                            continue
                        boneHash = transform_info.NameHashes[hashIndex]
                        group_name = Global_BoneNames.get(boneHash, str(boneHash))
                    else:
                        group_name = str(group_index) + "_" + str(bone_index)
                    if group_name not in created_groups:
                        created_groups.append(group_name)
                        try:
                            available_bones.remove(group_name)
                        except ValueError:
                            pass
                        new_vertex_group = new_object.vertex_groups.new(name=str(group_name))
                    vertex_group_data = [vertex_idx]
                    new_object.vertex_groups[str(group_name)].add(vertex_group_data, weight_value, 'ADD')
        if not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
            for bone in available_bones:
                new_vertex_group = new_object.vertex_groups.new(name=str(bone))
                
        # -- || ADD BONES || -- #
        if bpy.context.scene.Hd2ToolPanelSettings.ImportArmature and not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
            skeletonObj = None
            armature = None
            if len(bpy.context.selected_objects) > 0:
                skeletonObj = bpy.context.selected_objects[0]
            if skeletonObj and skeletonObj.type == 'ARMATURE':
                armature = skeletonObj.data
            if bpy.context.scene.Hd2ToolPanelSettings.MergeArmatures and armature != None:
                PrettyPrint(f"Merging to previous skeleton: {skeletonObj.name}")
            else:
                PrettyPrint(f"Creating New Skeleton")
                armature = bpy.data.armatures.new(f"{id}_skeleton{mesh.LodIndex}")
                armature.display_type = "OCTAHEDRAL"
                armature.show_names = False
                skeletonObj = bpy.data.objects.new(f"{id}_lod{mesh.LodIndex}_rig", armature)
                skeletonObj['BonesID'] = str(stingray_unit.BonesRef)
                skeletonObj.show_in_front = True
                
            if addon_prefs.MakeCollections:
                if 'skeletons' not in bpy.data.collections:
                    collection = bpy.data.collections.new("skeletons")
                    bpy.context.scene.collection.children.link(collection)
                else:
                    collection = bpy.data.collections['skeletons']
            else:
                collection = bpy.context.collection

            try:
                collection.objects.link(skeletonObj)
            except Exception as e:
                PrettyPrint(f"{e}", 'warn')

            #bpy.context.active_object = skeletonObj
            bpy.context.view_layer.objects.active = skeletonObj
            bpy.ops.object.mode_set(mode='EDIT')
            bones = None
            boneParents = None
            boneTransforms = {}
            boneMatrices = {}
            doPoseBone = {}
            if mesh.LodIndex in [-1, 0]:
                bones = [None] * transform_info.NumTransforms
                boneParents = [0] * transform_info.NumTransforms
                for i, transform in enumerate(transform_info.TransformEntries):
                    boneParent = transform.ParentBone
                    boneHash = transform_info.NameHashes[i]
                    if boneHash in Global_BoneNames: # name of bone
                        boneName = Global_BoneNames[boneHash]
                    else:
                        boneName = str(boneHash)
                    newBone = armature.edit_bones.get(boneName)
                    if newBone is None:
                        newBone = armature.edit_bones.new(boneName)
                        newBone.tail = 0, 0.05, 0
                        doPoseBone[newBone.name] = True
                    else:
                        doPoseBone[newBone.name] = False
                    bones[i] = newBone
                    boneParents[i] = boneParent
                    boneTransforms[newBone.name] = transform_info.Transforms[i]
                    boneMatrices[newBone.name] = transform_info.TransformMatrices[i]
            else:
                b_info = bone_info[mesh.LodIndex]
                bones = [None] * b_info.NumBones
                boneParents = [0] * b_info.NumBones
                for i, bone in enumerate(b_info.Bones): # this is not every bone in the transform_info
                    boneIndex = b_info.RealIndices[i] # index of bone in transform info
                    boneParent = transform_info.TransformEntries[boneIndex].ParentBone # index of parent bone in transform info
                    # index of parent bone in b_info.Bones?
                    if boneParent in b_info.RealIndices:
                        boneParentIndex = b_info.RealIndices.index(boneParent)
                    else:
                        boneParentIndex = -1
                    boneHash = transform_info.NameHashes[boneIndex]
                    if boneHash in Global_BoneNames: # name of bone
                        boneName = Global_BoneNames[boneHash]
                    else:
                        boneName = str(boneHash)
                    newBone = armature.edit_bones.get(boneName)
                    if newBone is None:
                        newBone = armature.edit_bones.new(boneName)
                        newBone.tail = 0, 0.05, 0
                        doPoseBone[newBone.name] = True
                    else:
                        doPoseBone[newBone.name] = False
                    bones[i] = newBone
                    boneTransforms[newBone.name] = transform_info.Transforms[boneIndex]
                    boneMatrices[newBone.name] = transform_info.TransformMatrices[boneIndex]
                    boneParents[i] = boneParentIndex
                    
            # parent all bones
            for i, bone in enumerate(bones):
                if boneParents[i] > -1:
                    bone.parent = bones[boneParents[i]]
            
            # pose all bones   
            bpy.context.view_layer.objects.active = skeletonObj
            
            for i, bone in enumerate(armature.edit_bones):
                try:
                    if not doPoseBone[bone.name]: continue
                    a = boneMatrices[bone.name]
                    mat = mathutils.Matrix.Identity(4)
                    mat[0] = a.v[0:4]
                    mat[1] = a.v[4:8]
                    mat[2] = a.v[8:12]
                    mat[3] = a.v[12:16]
                    mat.transpose()
                    bone.matrix = mat
                except Exception as e:
                    PrettyPrint(f"Failed setting bone matricies for: {e}. This may be intended", 'warn')
                
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # assign armature modifier to the mesh object
            modifier = new_object.modifiers.get("ARMATURE")
            if (modifier == None):
                modifier = new_object.modifiers.new("Armature", "ARMATURE")
                modifier.object = skeletonObj

            if bpy.context.scene.Hd2ToolPanelSettings.ParentArmature:
                new_object.parent = skeletonObj
            
            # select the armature at the end so we can chain import when merging
            for obj in bpy.context.selected_objects:
                obj.select_set(False)
            skeletonObj.select_set(True)
            
            # create empty animation data if it does not exist
            if not skeletonObj.animation_data:
              skeletonObj.animation_data_create()
                 
        # -- || ASSIGN MATERIALS || -- #
        # convert mesh to bmesh
        bm = bmesh.new()
        bm.from_mesh(new_object.data)
        # assign materials
        matNum = 0
        goreIndex = None
        for material in mesh.Materials:
            if str(material.MatID) == "12070197922454493211":
                goreIndex = matNum
                PrettyPrint(f"Found gore material at index: {matNum}")
            # append material to slot
            try: 
                new_object.data.materials.append(bpy.data.materials[material.MatID])
            except Exception: 
                # raise Exception(f"Tool was unable to find material that this mesh uses, ID: {material.MatID}")
                PrettyPrint(f"Tool was unable to find material that this mesh uses, ID: {material.MatID}")
                # 未找到材质直接新建
                AddMaterialToBlend_EMPTY(material.MatID)
                # 再次添加
                try:
                    new_object.data.materials.append(bpy.data.materials[material.MatID])
                except: 
                    raise Exception(f"Tool was unable to find material that this mesh uses, ID: {material.MatID}")
            # assign material to faces
            numTris    = int(material.NumIndices/3)
            StartIndex = int(material.StartIndex/3)
            for f in bm.faces[StartIndex:(numTris+(StartIndex))]:
                f.material_index = matNum
            matNum += 1
            
        # remove gore mesh
        if bpy.context.scene.Hd2ToolPanelSettings.RemoveGoreMeshes and goreIndex:
            PrettyPrint(f"Removing Gore Mesh")
            verticies = []
            for vert in bm.verts:
                if len(vert.link_faces) == 0:
                    continue
                if vert.link_faces[0].material_index == goreIndex:
                    verticies.append(vert)
            for vert in verticies:
                bm.verts.remove(vert)
                
        # convert bmesh to mesh
        bm.to_mesh(new_object.data)
        #平滑着色
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        if addon_prefs.ShadeSmooth:
            # 4.3 compatibility change
            if bpy.app.version[0] >= 4 and bpy.app.version[1] >= 1:
                new_mesh.shade_smooth()

            else:
                new_mesh.use_auto_smooth = False
                new_mesh.shade_smooth()
            
#endregion

#region Functions: Stingray Hashing

def GetTypeNameFromID(ID):
    for hash_info in Global_TypeHashes:
        if int(ID) == hash_info[0]:
            return hash_info[1]
    return "unknown"

def GetIDFromTypeName(Name):
    for hash_info in Global_TypeHashes:
        if hash_info[1] == Name:
            return int(hash_info[0])
    return None

def GetFriendlyNameFromID(ID):
    for hash_info in Global_NameHashes:
        if int(ID) == hash_info[0]:
            if hash_info[1] != "":
                return hash_info[1]
    return str(ID)

def GetArchiveNameFromID(EntryID):
    global Global_updatearchivelistCN_list
    for hash in Global_updatearchivelistCN_list:
        if hash["ArchiveID"].find(EntryID) != -1:
            ArchiveNameCN = str(hash["Classify"]).replace("'", "").replace("\n", "") + " - " + hash["Description"]
            return ArchiveNameCN
    return ""

def HasFriendlyName(ID):
    for hash_info in Global_NameHashes:
        if int(ID) == hash_info[0]:
            return True
    return False

def AddFriendlyName(ID, Name):
    Global_TocManager.SavedFriendlyNames = []
    Global_TocManager.SavedFriendlyNameIDs = []
    for hash_info in Global_NameHashes:
        if int(ID) == hash_info[0]:
            hash_info[1] = str(Name)
            return
    Global_NameHashes.append([int(ID), str(Name)])
    SaveFriendlyNames()

def SaveFriendlyNames():
    with open(Global_filehashpath, 'w') as f:
        for hash_info in Global_NameHashes:
            if hash_info[1] != "" and int(hash_info[0]) == murmur64_hash(hash_info[1].encode()):
                string = str(hash_info[0]) + " " + str(hash_info[1])
                f.writelines(string+"\n")
    with open(Global_friendlynamespath, 'w') as f:
        for hash_info in Global_NameHashes:
            if hash_info[1] != "":
                string = str(hash_info[0]) + " " + str(hash_info[1])
                f.writelines(string+"\n")


def bytes_to_long(bytes):
    assert len(bytes) == 8
    return sum((b << (k * 8) for k, b in enumerate(bytes)))

def murmur64_hash(data, seed: int = 0):

    m = 0xc6a4a7935bd1e995
    r = 47

    MASK = 2 ** 64 - 1

    data_as_bytes = bytearray(data)

    h = seed ^ ((m * len(data_as_bytes)) & MASK)

    off = int(len(data_as_bytes)/8)*8
    for ll in range(0, off, 8):
        k = bytes_to_long(data_as_bytes[ll:ll + 8])
        k = (k * m) & MASK
        k = k ^ ((k >> r) & MASK)
        k = (k * m) & MASK
        h = (h ^ k)
        h = (h * m) & MASK

    l = len(data_as_bytes) & 7

    if l >= 7:
        h = (h ^ (data_as_bytes[off+6] << 48))

    if l >= 6:
        h = (h ^ (data_as_bytes[off+5] << 40))

    if l >= 5:
        h = (h ^ (data_as_bytes[off+4] << 32))

    if l >= 4:
        h = (h ^ (data_as_bytes[off+3] << 24))

    if l >= 3:
        h = (h ^ (data_as_bytes[off+2] << 16))

    if l >= 2:
        h = (h ^ (data_as_bytes[off+1] << 8))

    if l >= 1:
        h = (h ^ data_as_bytes[off])
        h = (h * m) & MASK

    h = h ^ ((h >> r) & MASK)
    h = (h * m) & MASK
    h = h ^ ((h >> r) & MASK)

    return h
    
def murmur32_hash(data, seed: int = 0):
    return murmur64_hash(data, seed) >> 32

#endregion

#region Functions: Initialization


Global_TypeHashes = []
def LoadTypeHashes():
    with open(Global_typehashpath, 'r') as f:
        for line in f.readlines():
            parts = line.split(" ")
            Global_TypeHashes.append([int(parts[0], 16), parts[1].replace("\n", "")])

Global_NameHashes = []
def LoadNameHashes():
    Loaded = []
    with open(Global_filehashpath, 'r') as f:
        for line in f.readlines():
            parts = line.split(" ")
            Global_NameHashes.append([int(parts[0]), parts[1].replace("\n", "")])
            Loaded.append(int(parts[0]))
    with open(Global_friendlynamespath, 'r') as f:
        for line in f.readlines():
            parts = line.split(" ")
            if int(parts[0]) not in Loaded:
                Global_NameHashes.append([int(parts[0]), parts[1].replace("\n", "")])
                Loaded.append(int(parts[0]))


# 载入Archive收集表条目
def LoadUpdateArchiveList_CN():
    global Global_updatearchivelistCN_list
    Global_updatearchivelistCN_list = []
    with open(Global_updatearchivelistCNpath, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            if "本地更新时间" in line or line.find("None#None#None") != -1 or "以下是2025.3.18更新后" in line:
                continue
            Global_updatearchivelistCN_list.append({"ArchiveID": str(line.split("#")[0]),
                                                    "Classify": line.split("#")[1].split(","),
                                                    "Description": line.split("#")[2] })
            
def GetEntryParentMaterialID(entry):
    if entry.TypeID == MaterialID:
        f = MemoryStream(entry.TocData)
        for i in range(6):
            f.uint32(0)
        parentID = f.uint64(0)
        return parentID
    else:
        raise Exception(f"Entry: {entry.FileID} is not a material")
#endregion

#region Configuration

def InitializeConfig():
    global Global_gamepath, Global_configpath, Global_gamepathIsValid
    if os.path.exists(Global_configpath):
        config = configparser.ConfigParser()
        config.read(Global_configpath, encoding='utf-8')
        try:
            Global_gamepath = config['DEFAULT']['filepath']
        except:
            UpdateConfig()
            
        if os.path.exists(Global_gamepath):
            PrettyPrint(f"Loaded Data Folder: {Global_gamepath}")
            slim_init(Global_gamepath)
            Global_gamepathIsValid = True
        else:
            PrettyPrint(f"Game path: {Global_gamepath} is not a valid directory", 'ERROR')
            Global_gamepathIsValid = False

    else:
        UpdateConfig()

def get_helldivers2_path():
    import winreg

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
    except Exception:
        return None

    steam_path = os.path.normpath(steam_path)
    library_vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")

    if not os.path.exists(library_vdf):
        return None

    libraries = [os.path.join(steam_path, "steamapps")]
    with open(library_vdf, "r", encoding="utf-8") as f:
        content = f.read()

    for match in re.finditer(r'"\d+"\s+"([^"]+)"', content):
        lib_path = match.group(1).replace("\\\\", "\\")
        libraries.append(os.path.join(lib_path, "steamapps"))

    for lib in libraries:
        manifest = os.path.join(lib, "appmanifest_553850.acf")
        if os.path.exists(manifest):
            with open(manifest, "r", encoding="utf-8") as f:
                data = f.read()
            m = re.search(r'"installdir"\s+"([^"]+)"', data)
            if m:
                game_folder = m.group(1)
                return os.path.join(lib, "common", game_folder, "data")

    return None
    
def UpdateConfig():
    global Global_gamepath, Global_defaultgamepath, Global_gamepathIsValid
    if Global_gamepath == "":
        if get_helldivers2_path():
            Global_gamepath = get_helldivers2_path()
        else:
            Global_gamepath = Global_defaultgamepath
    if Global_gamepathIsValid: 
        slim_init(Global_gamepath)
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'filepath' : Global_gamepath}
    with open(Global_configpath, 'w') as configfile:
        config.write(configfile)
    
#endregion

#region Classes and Functions: Stingray Archives

class TocEntry:

    def __init__(self):
        self.FileID = self.TypeID = self.TocDataOffset = self.Unknown1 = self.GpuResourceOffset = self.Unknown2 = self.TocDataSize = self.GpuResourceSize = self.EntryIndex = self.StreamSize = self.StreamOffset = 0
        self.Unknown3 = 16
        self.Unknown4 = 64

        self.TocData =  self.TocData_OLD = b""
        self.GpuData =  self.GpuData_OLD = b""
        self.StreamData =  self.StreamData_OLD = b""

        # Custom Dev stuff
        self.LoadedData = None
        self.IsLoaded   = False
        self.IsModified = False
        self.IsCreated  = False # custom created, can be removed from archive
        self.IsSelected = False
        self.MaterialTemplate = None # for determining tuple to use for labeling textures in the material editor
        self.DEV_DrawIndex = -1

    # -- Serialize TocEntry -- #
    def Serialize(self, TocFile: MemoryStream, Index=0):
        self.FileID             = TocFile.uint64(self.FileID)
        self.TypeID             = TocFile.uint64(self.TypeID)
        self.TocDataOffset      = TocFile.uint64(self.TocDataOffset)
        self.StreamOffset       = TocFile.uint64(self.StreamOffset)
        self.GpuResourceOffset  = TocFile.uint64(self.GpuResourceOffset)
        self.Unknown1           = TocFile.uint64(self.Unknown1)
        self.Unknown2           = TocFile.uint64(self.Unknown2)
        self.TocDataSize        = TocFile.uint32(len(self.TocData))
        self.StreamSize         = TocFile.uint32(len(self.StreamData))
        self.GpuResourceSize    = TocFile.uint32(len(self.GpuData))
        self.Unknown3           = TocFile.uint32(self.Unknown3)
        self.Unknown4           = TocFile.uint32(self.Unknown4)
        self.EntryIndex         = TocFile.uint32(Index)
        return self

    # -- Write TocEntry Data -- #
    def SerializeData(self, TocFile: MemoryStream, GpuFile, StreamFile):
        if TocFile.IsReading():
            TocFile.seek(self.TocDataOffset)
            self.TocData = bytearray(self.TocDataSize)
        elif TocFile.IsWriting():
            self.TocDataOffset = TocFile.tell()
        self.TocData = TocFile.bytes(self.TocData)

        if GpuFile.IsWriting(): self.GpuResourceOffset = ceil(float(GpuFile.tell())/64)*64
        if self.GpuResourceSize > 0:
            GpuFile.seek(self.GpuResourceOffset)
            if GpuFile.IsReading(): self.GpuData = bytearray(self.GpuResourceSize)
            self.GpuData = GpuFile.bytes(self.GpuData)

        if StreamFile.IsWriting(): self.StreamOffset = ceil(float(StreamFile.tell())/64)*64
        if self.StreamSize > 0:
            StreamFile.seek(self.StreamOffset)
            if StreamFile.IsReading(): self.StreamData = bytearray(self.StreamSize)
            self.StreamData = StreamFile.bytes(self.StreamData)
        if GpuFile.IsReading():
            self.TocData_OLD    = bytearray(self.TocData)
            self.GpuData_OLD    = bytearray(self.GpuData)
            self.StreamData_OLD = bytearray(self.StreamData)

    # -- Get Data -- #
    def GetData(self):
        return [self.TocData, self.GpuData, self.StreamData]
    # -- Set Data -- #
    def SetData(self, TocData, GpuData, StreamData, IsModified=True):
        self.TocData = TocData
        self.GpuData = GpuData
        self.StreamData = StreamData
        self.TocDataSize     = len(self.TocData)
        self.GpuResourceSize = len(self.GpuData)
        self.StreamSize      = len(self.StreamData)
        self.IsModified = IsModified
    # -- Undo Modified Data -- #
    def UndoModifiedData(self):
        self.TocData = bytearray(self.TocData_OLD)
        self.GpuData = bytearray(self.GpuData_OLD)
        self.StreamData = bytearray(self.StreamData_OLD)
        self.TocDataSize     = len(self.TocData)
        self.GpuResourceSize = len(self.GpuData)
        self.StreamSize      = len(self.StreamData)
        self.IsModified = False
        if self.IsLoaded:
            self.Load(True, False)
    # -- Load Data -- #
    def Load(self, Reload=False, MakeBlendObject=True, LoadMaterialSlotNames=False):
        callback = None
        if self.TypeID == UnitID: callback = LoadStingrayUnit
        if self.TypeID == TexID: callback = LoadStingrayTexture
        if self.TypeID == MaterialID: callback = LoadStingrayMaterial
        # if self.TypeID == ParticleID: callback = LoadStingrayParticle
        if self.TypeID == CompositeUnitID: callback = LoadStingrayCompositeUnit
        if self.TypeID == BoneID: callback = LoadStingrayBones
        if self.TypeID == AnimationID: callback = LoadStingrayAnimation
        # if callback == None: callback = LoadStingrayDump

        if callback != None:
            if self.TypeID == UnitID:
                PrettyPrint(f"LoadMaterialSlotNames: {LoadMaterialSlotNames}")
                self.LoadedData = callback(self.FileID, self.TocData, self.GpuData, self.StreamData, Reload, MakeBlendObject, LoadMaterialSlotNames)
            else:
                self.LoadedData = callback(self.FileID, self.TocData, self.GpuData, self.StreamData, Reload, MakeBlendObject)
            if self.LoadedData == None: raise Exception("Archive Entry Load Failed")
            self.IsLoaded = True

    # -- Write Data -- #
    def Save(self, **kwargs):
        if not self.IsLoaded: self.Load(True, False)
        if self.TypeID == UnitID: callback = SaveStingrayMesh
        if self.TypeID == TexID: callback = SaveStingrayTexture
        if self.TypeID == MaterialID: callback = SaveStingrayMaterial
        # if self.TypeID == ParticleID: callback = SaveStingrayParticle
        if self.TypeID == AnimationID: callback = SaveStingrayAnimation
        # if callback == None: callback = SaveStingrayDump

        if self.IsLoaded:
            data = callback(self, self.FileID, self.TocData, self.GpuData, self.StreamData, self.LoadedData)
            self.SetData(data[0], data[1], data[2])
        return True

class TocFileType:
    def __init__(self, ID=0, NumFiles=0):
        self.unk1     = 0
        self.TypeID   = ID
        self.NumFiles = NumFiles
        self.unk2     = 16
        self.unk3     = 64
    def Serialize(self, TocFile):
        self.unk1     = TocFile.uint64(self.unk1)
        self.TypeID   = TocFile.uint64(self.TypeID)
        self.NumFiles = TocFile.uint64(self.NumFiles)
        self.unk2     = TocFile.uint32(self.unk2)
        self.unk3     = TocFile.uint32(self.unk3)
        return self

class SearchToc:
    def __init__(self):
        self.TocEntries = {}
        self.Path = ""
        self.Name = ""

    def HasEntry(self, file_id, type_id):
        try:
            return file_id in self.TocEntries[type_id]
        except KeyError:
            return False

    def FromFile(self, path):
        self.UpdatePath(path)
        bin_data = b""
        file = open(path, 'r+b')
        bin_data = file.read(12)
        magic, numTypes, numFiles = struct.unpack("<III", bin_data)
        if magic != 4026531857:
            file.close()
            return False

        offset = 60 + (numTypes << 5)
        bin_data = file.read(offset + 80 * numFiles)
        file.close()
        for _ in range(numFiles):
            file_id, type_id = struct.unpack_from("<QQ", bin_data, offset=offset)
            try:
                self.TocEntries[type_id].append(file_id)
            except KeyError:
                self.TocEntries[type_id] = [file_id]
            offset += 80
        return True

    def UpdatePath(self, path):
        self.Path = path
        self.Name = Path(path).name

class StreamToc:
    def __init__(self):
        self.magic      = self.numTypes = self.numFiles = self.unknown = 0
        self.unk4Data   = bytearray(56)
        self.TocTypes   = []
        self.TocEntries = []
        self.Path = ""
        self.Name = ""
        self.LocalName = ""

    def Serialize(self, SerializeData=True):
        # Create Toc Types Structs
        if self.TocFile.IsWriting():
            self.UpdateTypes()
        # Begin Serializing file
        self.magic      = self.TocFile.uint32(self.magic)
        if self.magic != 4026531857: return False

        self.numTypes   = self.TocFile.uint32(len(self.TocTypes))
        self.numFiles   = self.TocFile.uint32(len(self.TocEntries))
        self.unknown    = self.TocFile.uint32(self.unknown)
        self.unk4Data   = self.TocFile.bytes(self.unk4Data, 56)

        if self.TocFile.IsReading():
            self.TocTypes   = [TocFileType() for n in range(self.numTypes)]
            self.TocEntries = [TocEntry() for n in range(self.numFiles)]
        # serialize Entries in correct order
        self.TocTypes   = [Entry.Serialize(self.TocFile) for Entry in self.TocTypes]
        TocEntryStart   = self.TocFile.tell()
        if self.TocFile.IsReading(): self.TocEntries = [Entry.Serialize(self.TocFile) for Entry in self.TocEntries]
        else:
            Index = 1
            for Type in self.TocTypes:
                for Entry in self.TocEntries:
                    if Entry.TypeID == Type.TypeID:
                        Entry.Serialize(self.TocFile, Index)
                        Index += 1

        # Serialize Data
        if SerializeData:
            for FileEntry in self.TocEntries:
                FileEntry.SerializeData(self.TocFile, self.GpuFile, self.StreamFile)

        # re-write toc entry info with updated offsets
        if self.TocFile.IsWriting():
            self.TocFile.seek(TocEntryStart)
            Index = 1
            for Type in self.TocTypes:
                for Entry in self.TocEntries:
                    if Entry.TypeID == Type.TypeID:
                        Entry.Serialize(self.TocFile, Index)
                        Index += 1
        return True

    def UpdateTypes(self):
        self.TocTypes = []
        for Entry in self.TocEntries:
            exists = False
            for Type in self.TocTypes:
                if Type.TypeID == Entry.TypeID:
                    Type.NumFiles += 1; exists = True
                    break
            if not exists:
                self.TocTypes.append(TocFileType(Entry.TypeID, 1))

    def UpdatePath(self, path):
        self.Path = path
        self.Name = Path(path).name

    def FromFile(self, path, SerializeData=True):
        self.UpdatePath(path)
        with open(path, 'r+b') as f:
            self.TocFile = MemoryStream(f.read())

        self.GpuFile    = MemoryStream()
        self.StreamFile = MemoryStream()
        if SerializeData:
            if os.path.isfile(path+".gpu_resources"):
                with open(path+".gpu_resources", 'r+b') as f:
                    self.GpuFile = MemoryStream(f.read())
            if os.path.isfile(path+".stream"):
                with open(path+".stream", 'r+b') as f:
                    self.StreamFile = MemoryStream(f.read())
        return self.Serialize(SerializeData)

    def ToFile(self, path=None):
        global Global_PatchBasePath
        Global_PatchBasePath = ""
        self.TocFile = MemoryStream(IOMode = "write")
        self.GpuFile = MemoryStream(IOMode = "write")
        self.StreamFile = MemoryStream(IOMode = "write")
        self.Serialize()
        if path == None: path = self.Path
        
        Global_PatchBasePath = path
        
        with open(path, 'w+b') as f:
            f.write(bytes(self.TocFile.Data))
        with open(path+".gpu_resources", 'w+b') as f:
            f.write(bytes(self.GpuFile.Data))
        with open(path+".stream", 'w+b') as f:
            f.write(bytes(self.StreamFile.Data))

    def GetFileData(self, FileID, TypeID):
        for FileEntry in self.TocEntries:
            if FileEntry.FileID == FileID and FileEntry.TypeID == TypeID:
                return FileEntry.GetData()
        return None
    def GetEntry(self, FileID, TypeID):
        for Entry in self.TocEntries:
            if Entry.FileID == int(FileID) and Entry.TypeID == TypeID:
                return Entry
        return None
    def AddEntry(self, NewEntry):
        if self.GetEntry(NewEntry.FileID, NewEntry.TypeID) != None:
            raise Exception("Entry with same ID already exists")
        self.TocEntries.append(NewEntry)
        self.UpdateTypes()
    def RemoveEntry(self, FileID, TypeID):
        Entry = self.GetEntry(FileID, TypeID)
        if Entry != None:
            self.TocEntries.remove(Entry)
            self.UpdateTypes()

class TocManager():
    def __init__(self):
        self.SearchArchives  = []
        self.LoadedArchives  = []
        self.ActiveArchive   = None
        self.Patches         = []
        self.ActivePatch     = None

        self.CopyBuffer      = []
        self.SelectedEntries = []
        self.DrawChain       = []
        self.LastSelected = None # Last Entry Manually Selected
        self.SavedFriendlyNames   = []
        self.SavedFriendlyNameIDs = []
    #________________________________#
    # ---- Entry Selection Code ---- #
    def SelectEntries(self, Entries, Append=False):
        if not Append: self.DeselectAll()
        if len(Entries) == 1:
            Global_TocManager.LastSelected = Entries[0]

        for Entry in Entries:
            if Entry not in self.SelectedEntries:
                Entry.IsSelected = True
                self.SelectedEntries.append(Entry)
    def DeselectEntries(self, Entries):
        for Entry in Entries:
            Entry.IsSelected = False
            if Entry in self.SelectedEntries:
                self.SelectedEntries.remove(Entry)
    def DeselectAll(self):
        for Entry in self.SelectedEntries:
            Entry.IsSelected = False
        self.SelectedEntries = []
        self.LastSelected = None

    #________________________#
    # ---- Archive Code ---- #
    def LoadArchive(self, path, SetActive=True, IsPatch=False):
        # TODO: Add error if IsPatch is true but the path is not to a patch
        global Global_MaterialParentIDs
        
        for Archive in self.LoadedArchives:
            if Archive.Path == path:
                return Archive
        archiveID = path.replace(Global_gamepath, '')
        archiveName = GetArchiveNameFromID(archiveID)
        toc = StreamToc()
        toc.FromFile(path)
        if SetActive and not IsPatch:
            self.LoadedArchives.append(toc)
            self.ActiveArchive = toc
            # bpy.context.scene.Hd2ToolPanelSettings.LoadedArchives = archiveID 
        elif SetActive and IsPatch:
            self.Patches.append(toc)
            self.ActivePatch = toc
            
            # 预载材质模板
            for entry in self.ActivePatch.TocEntries:
                if entry.TypeID == MaterialID:
                    ID = GetEntryParentMaterialID(entry)
                    if ID in Global_MaterialParentIDs:
                        entry.MaterialTemplate = Global_MaterialParentIDs[ID]
                        # entry.Load()
                        PrettyPrint(f"Find Custom material, Template: {entry.MaterialTemplate}")
                    else:
                        PrettyPrint(f"Material: {entry.FileID} Parent ID: {ID} is not an custom material, skipping.")


        # Get search archives
        if len(self.SearchArchives) == 0:
            futures = []
            tocs = []
            executor = concurrent.futures.ThreadPoolExecutor()
            for root, dirs, files in os.walk(Path(path).parent):
                for name in files:
                    if Path(name).suffix == "":
                        search_toc = SearchToc()
                        tocs.append(search_toc)
                        futures.append(executor.submit(search_toc.FromFile, os.path.join(root, name)))
            for index, future in enumerate(futures):
                if future.result():
                    self.SearchArchives.append(tocs[index])
            executor.shutdown()


        return toc

    def GetEntryByLoadArchive(self, FileID: int, TypeID: int):
        return self.GetEntry(FileID, TypeID, SearchAll=False, IgnorePatch=True)
    # def GetEntryByPatch(self, FileID: int, TypeID: int):
    #     return self.GetEntry(FileID, TypeID)

    def UnloadArchives(self):
        # TODO: Make sure all data gets unloaded...
        # some how memory can still be too high after calling this
        self.LoadedArchives = []
        self.ActiveArchive  = None
        self.SearchArchives = []

    def UnloadPatches(self):
        self.Patches = []
        self.ActivePatch = None
        
    def SetActive(self, Archive):
        if Archive != self.ActiveArchive:
            self.ActiveArchive = Archive
            self.DeselectAll()

    def SetActiveByName(self, Name):
        for Archive in self.LoadedArchives:
            if Archive.Name == Name:
                self.SetActive(Archive)

    #______________________#
    # ---- Entry Code ---- #
    def GetEntry(self, FileID, TypeID, SearchAll=False, IgnorePatch=False):
        # Check Active Patch
        if not IgnorePatch and self.ActivePatch != None:
            Entry = self.ActivePatch.GetEntry(FileID, TypeID)
            if Entry != None:
                return Entry
        # Check Active Archive
        if self.ActiveArchive != None:
            Entry = self.ActiveArchive.GetEntry(FileID, TypeID)
            if Entry != None:
                return Entry
        # Check All Loaded Archives
        for Archive in self.LoadedArchives:
            Entry = Archive.GetEntry(FileID, TypeID)
            if Entry != None:
                return Entry
        # Check All Search Archives
        if SearchAll:
            for Archive in self.SearchArchives:
                if Archive.HasEntry(FileID, TypeID):
                    return self.LoadArchive(Archive.Path, False).GetEntry(FileID, TypeID)
        return None

    def Load(self, FileID, TypeID, Reload=False, SearchAll=False):
        Entry = self.GetEntry(FileID, TypeID, SearchAll)
        if Entry != None: Entry.Load(Reload)
        
    def Save(self, FileID, TypeID):
        Entry = self.GetEntry(FileID, TypeID)
        if not Global_TocManager.IsInPatch(Entry):
            Entry = self.AddEntryToPatch(FileID, TypeID)

        if Entry != None: Entry.Save()

    def CopyPaste(self, Entry, GenID = False, NewID = None):
        if self.ActivePatch == None:
            raise Exception("No patch exists, please create one first")
        if self.ActivePatch:
            dup = deepcopy(Entry)
            dup.IsCreated = True
            # if self.ActivePatch.GetEntry(dup.FileID, dup.TypeID) != None and NewID == None:
            #     GenID = True
            if GenID and NewID == None: dup.FileID = r.randint(1, 0xffffffffffffffff)
            if NewID != None:
                dup.FileID = NewID

            self.ActivePatch.AddEntry(dup)
    def Copy(self, Entries):
        self.CopyBuffer = []
        for Entry in Entries:
            if Entry != None: self.CopyBuffer.append(Entry)
    def Paste(self, GenID = False, NewID = None):
        if self.ActivePatch == None:
            raise Exception("No patch exists, please create one first")
        if self.ActivePatch:
            for ToCopy in self.CopyBuffer:
                self.CopyPaste(ToCopy, GenID, NewID)
            self.CopyBuffer = []

    def ClearClipboard(self):
        self.CopyBuffer = []

    #______________________#
    # ---- Patch Code ---- #
    def PatchActiveArchive(self,path=None):
        self.ActivePatch.ToFile(path= path)

    def CreatePatchFromActive(self,NewPatchIndex):
        if self.ActiveArchive == None:
            raise Exception("没有激活的Archive，无法创建Patch，请先载入一个Archive。")

        self.ActivePatch = deepcopy(self.ActiveArchive)
        self.ActivePatch.TocEntries  = []
        self.ActivePatch.TocTypes    = []
        # TODO: ask for which patch index
        path = self.ActiveArchive.Path
        if path.find(".patch_") != -1:
            path = path[:path.find(".patch_")] + ".patch_" + str(NewPatchIndex)
        else:
            path = path + ".patch_" + str(NewPatchIndex)
        self.ActivePatch.UpdatePath(path)
        self.Patches.append(self.ActivePatch)
        
    def RenameActivePatch(self, NewPath):
        if self.ActivePatch == None:
            raise Exception("没有激活的Patch，无法重命名，请先创建一个Patch。")
        path = self.ActivePatch.Path
        
        fileNamelist = path.split("\\")[:-1]
        fileNamelist.append(NewPath)
        Rename_path = "\\".join(fileNamelist)
        return Rename_path
        

    def SetActivePatch(self, Patch):
        self.ActivePatch = Patch

    def SetActivePatchByName(self, Name):
        for Patch in self.Patches:
            if Patch.Name == Name:
                self.SetActivePatch(Patch)
    def CheckActivePatch(self):
        if self.ActivePatch == None:
            return False
        else:
            return True

    def AddNewEntryToPatch(self, Entry):
        if self.ActivePatch == None:
            raise Exception("没有激活的Patch，无法添加Entry，请先创建一个Patch。")
        self.ActivePatch.AddEntry(Entry)

    def AddEntryToPatch(self, FileID, TypeID):
        if self.ActivePatch == None:
            raise Exception("没有激活的Patch，无法添加Entry，请先创建一个Patch。")

        Entry = self.GetEntry(FileID, TypeID)
        if Entry != None:
            PatchEntry = deepcopy(Entry)
            if PatchEntry.IsSelected:
                self.SelectEntries([PatchEntry], True)
            self.ActivePatch.AddEntry(PatchEntry)
            return PatchEntry
        return None

    def RemoveEntryFromPatch(self, FileID, TypeID):
        if self.ActivePatch != None:
            self.ActivePatch.RemoveEntry(FileID, TypeID)
        return None

    def GetPatchEntry(self, Entry):
        if self.ActivePatch != None:
            return self.ActivePatch.GetEntry(Entry.FileID, Entry.TypeID)
        return None
    def GetPatchEntry_B(self, FileID, TypeID):
        if self.ActivePatch != None:
            return self.ActivePatch.GetEntry(FileID, TypeID)
        return None

    def IsInPatch(self, Entry):
        if self.ActivePatch != None:
            PatchEntry = self.ActivePatch.GetEntry(Entry.FileID, Entry.TypeID)
            if PatchEntry != None: return True
            else: return False
        return False

    def DuplicateEntry(self, FileID, TypeID, NewID):
        Entry = self.GetEntry(FileID, TypeID)
        if Entry != None:
            self.CopyPaste(Entry, False, NewID)

#endregion

#region Classes and Functions: Stingray Animation
def LoadStingrayAnimation(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    toc = MemoryStream(TocData)
    PrettyPrint("Loading Animation")
    animation = StingrayAnimation()
    animation.Serialize(toc)
    PrettyPrint("Finished Loading Animation")
    if MakeBlendObject: # To-do: create action for armature
        context = bpy.context
        armature = context.active_object
        try:
            bones_id = int(armature['BonesID'])
        except ValueError:
            raise Exception(f"\n\nCould not obtain custom property: BonesID from armature: {armature.name}. Please make sure this is a valid value")
        bones_entry = Global_TocManager.GetEntryByLoadArchive(int(bones_id), BoneID)
        if not bones_entry.IsLoaded:
            bones_entry.Load()
        bones_data = bones_entry.TocData
        animation.to_action(context, armature, bones_data, ID)
    return animation
    
def SaveStingrayAnimation(self, ID, TocData, GpuData, StreamData, Animation):
    toc = MemoryStream(IOMode = "write")
    Animation.Serialize(toc)
    return [toc.Data, b"", b""]

#endregion

#region Classes and Functions: Stingray Materials


def LoadStingrayMaterial(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    exists = True
    force_reload = False
    try:
        mat = bpy.data.materials[str(ID)]
        if not mat.use_nodes: force_reload = True
    except: exists = False


    f = MemoryStream(TocData)
    Material = StingrayMaterial()
    Material.Serialize(f)
    if MakeBlendObject and not (exists and not Reload): AddMaterialToBlend(ID, Material)
    elif force_reload: AddMaterialToBlend(ID, Material, True)
    return Material

def SaveStingrayMaterial(self, ID, TocData, GpuData, StreamData, LoadedData):
    mat = LoadedData
    for TexIdx in range(len(mat.TexIDs)):
        oldTexID = mat.TexIDs[TexIdx]
        if mat.DEV_DDSPaths[TexIdx] != None:
            
            if CheckTextureExtension(mat.DEV_DDSPaths[TexIdx]):
                # get texture data
                StingrayTex = StingrayTexture()
                with open(mat.DEV_DDSPaths[TexIdx], 'r+b') as f:
                    StingrayTex.FromDDS(f.read())
            else: # 如果是tga,就使用texconv转换dds并保存到软件缓存路径
                tempdir = tempfile.gettempdir()
                if "[-_彩色_-]" in mat.DEV_DDSPaths[TexIdx]:
                    mat.DEV_DDSPaths[TexIdx] = mat.DEV_DDSPaths[TexIdx].replace("[-_彩色_-]", "")
                    DDS_Export_SRGB(tempdir=tempdir,input_path=mat.DEV_DDSPaths[TexIdx])
                    
                elif "[-_线性_-] " in mat.DEV_DDSPaths[TexIdx]:
                    mat.DEV_DDSPaths[TexIdx] = mat.DEV_DDSPaths[TexIdx].replace("[-_线性_-] ", "") 
                    DDS_Export_Linear(tempdir=tempdir,input_path=mat.DEV_DDSPaths[TexIdx])
                    
                else:
                    DDS_Export_SRGB(tempdir=tempdir,input_path=mat.DEV_DDSPaths[TexIdx])
                
                tga2dds_path = os.path.join(tempdir, CheckTextureName(mat.DEV_DDSPaths[TexIdx])+".dds")
                StingrayTex = StingrayTexture()
                with open(tga2dds_path, 'r+b') as f:
                    StingrayTex.FromDDS(f.read())
                
            Toc = MemoryStream(IOMode="write")
            Gpu = MemoryStream(IOMode="write")
            Stream = MemoryStream(IOMode="write")
            StingrayTex.Serialize(Toc, Gpu, Stream)
            # add texture entry to archive
            Entry = TocEntry()
            Entry.FileID = r.randint(1, 0xffffffffffffffff)
            Entry.TypeID = TexID
            Entry.IsCreated = True
            Entry.SetData(Toc.Data, Gpu.Data, Stream.Data, False)
            Global_TocManager.AddNewEntryToPatch(Entry)
            mat.TexIDs[TexIdx] = Entry.FileID
                
        else:
            Global_TocManager.Load(int(mat.TexIDs[TexIdx]), TexID, False, True)
            Entry = Global_TocManager.GetEntry(int(mat.TexIDs[TexIdx]), TexID, True)
            if Entry != None:
                Entry = deepcopy(Entry)
                Entry.FileID = r.randint(1, 0xffffffffffffffff)
                Entry.IsCreated = True
                Global_TocManager.AddNewEntryToPatch(Entry)
                mat.TexIDs[TexIdx] = Entry.FileID
                
        Global_TocManager.RemoveEntryFromPatch(oldTexID, TexID)
    f = MemoryStream(IOMode="write")
    LoadedData.Serialize(f)
    return [f.Data, b"", b""]

def AddMaterialToBlend(ID, StringrayMat, EmptyMatExists=False):
    if EmptyMatExists:
        mat = bpy.data.materials[str(ID)]
    else:
        mat = bpy.data.materials.new(str(ID)); mat.name = str(ID)

    mat.diffuse_color = (r.random(), r.random(), r.random(), 1)
    mat.use_nodes = True
    # bsdf = mat.node_tree.nodes["Principled BSDF"]
    idx = 0
    for TextureID in StringrayMat.TexIDs:
        # Create Node
        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.location = (-450, 850 - 300*idx)

        # Load Texture
        try:    bpy.data.images[str(TextureID)]
        except: Global_TocManager.Load(TextureID, TexID, False, True)
        # Apply Texture
        try: texImage.image = bpy.data.images[str(TextureID)]
        except:
            PrettyPrint(f"Failed to load texture {TextureID}. This is not fatal, but does mean that the materials in Blender will have empty image texture nodes", "warn")
            pass
        idx +=1

def AddMaterialToBlend_EMPTY(ID):
    try:
        bpy.data.materials[str(ID)]
    except:
        mat = bpy.data.materials.new(str(ID)); mat.name = str(ID)
        mat.diffuse_color = (r.random(), r.random(), r.random(), 1)

# 检查导入纹理的格式
def CheckTextureExtension(TexPath):
    file_name,file_extension = os.path.splitext(os.path.basename(TexPath))
    if file_extension.lower() == ".dds":
        return True
    else:
        return False
    
def CheckTextureName(TexPath):
    file_name,file_extension = os.path.splitext(os.path.basename(TexPath))
    return file_name


def DDS_Export_SRGB(tempdir,input_path):
    subprocess.run([Global_texconvpath, "-y", "-o", tempdir, "-ft", "dds", "-dx10", "-f", "BC7_UNORM_SRGB","-m","1","-srgb","-alpha",input_path ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    PrettyPrint("DDS_Export_SRGB", "info")
    
def DDS_Export_Linear(tempdir,input_path):
    subprocess.run([Global_texconvpath, "-y", "-o", tempdir, "-ft", "dds", "-dx10", "-f", "BC7_UNORM","-m","1","--ignore-srgb","-alpha",input_path ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    PrettyPrint("DDS_Export_Linear", "info")
#endregion

#region Classes and Functions: Stingray Textures



def LoadStingrayTexture(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    exists = True
    try: bpy.data.images[str(ID)]
    except: exists = False

    StingrayTex = StingrayTexture()
    StingrayTex.Serialize(MemoryStream(TocData), MemoryStream(GpuData), MemoryStream(StreamData))
    dds = StingrayTex.ToDDS()

    if MakeBlendObject and not (exists and not Reload):
        tempdir = tempfile.gettempdir()
        dds_path = f"{tempdir}\\{ID}.dds"
        tga_path = f"{tempdir}\\{ID}.tga"

        with open(dds_path, 'w+b') as f:
            f.write(dds)
        
        subprocess.run([Global_texconvpath, "-y", "-o", tempdir, "-ft", "tga", "-f", "R8G8B8A8_UNORM", dds_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        if os.path.isfile(tga_path):
            image = bpy.data.images.load(tga_path)
            image.name = str(ID)
            image.pack()
        else:
            raise Exception(f"Failed to convert texture {ID} to TGA, or DDS failed to export")
    
    return StingrayTex

def BlendImageToStingrayTexture(image, StingrayTex):
    tempdir  = tempfile.gettempdir()
    dds_path = f"{tempdir}\\blender_img.dds"
    tga_path = f"{tempdir}\\blender_img.tga"

    image.file_format = 'TARGA_RAW'
    image.filepath_raw = tga_path
    image.save()

    subprocess.run([Global_texconvpath, "-y", "-o", tempdir, "-ft", "dds", "-f", StingrayTex.Format, dds_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    
    if os.path.isfile(dds_path):
        with open(dds_path, 'r+b') as f:
            StingrayTex.FromDDS(f.read())
    else:
        raise Exception("Failed to convert TGA to DDS")

def SaveStingrayTexture(self,ID, TocData, GpuData, StreamData, LoadedData):
    exists = True
    try: bpy.data.images[str(ID)]
    except: exists = False

    Toc = MemoryStream(IOMode="write")
    Gpu = MemoryStream(IOMode="write")
    Stream = MemoryStream(IOMode="write")

    LoadedData.Serialize(Toc, Gpu, Stream)

    return [Toc.Data, Gpu.Data, Stream.Data]

#endregion

#region Classes and Functions: Stingray Bones

def LoadStingrayBones(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    StingrayBonesData = StingrayBones(Global_BoneNames)
    StingrayBonesData.Serialize(MemoryStream(TocData))
    return StingrayBonesData


#endregion

#region Classes and Functions: Stingray Composite Meshes

class CompositeMeshInfoItem:
    
    def __init__(self):
        self.MeshLayoutIdx = 0
        self.NumMaterials = 0
        self.MaterialsOffset = 0
        self.NumGroups = 0
        self.GroupsOffset = 0
        self.unk1 = bytearray()
        self.unk2 = 0
        self.Groups = []
        self.Materials = []
        
    def Serialize(self, f: MemoryStream):
        start_position = f.tell()
        self.MeshLayoutIdx = f.uint32(self.MeshLayoutIdx)
        self.unk1 = f.bytes(self.unk1, 20)
        self.NumMaterials = f.uint32(self.NumMaterials)
        self.MaterialsOffset = f.uint32(self.MaterialsOffset)
        self.unk2 = f.uint64(self.unk2)
        self.NumGroups = f.uint32(self.NumGroups)
        self.GroupsOffset = f.uint32(self.GroupsOffset)
        if f.IsReading(): self.Materials = [0] * self.NumMaterials
        f.seek(start_position + self.MaterialsOffset)
        self.Materials = [f.uint32(material) for material in self.Materials]
        f.seek(start_position + self.GroupsOffset)
        if f.IsReading(): self.Groups = [MeshSectionInfo(self.Materials) for _ in range(self.NumGroups)]
        self.Groups = [group.Serialize(f) for group in self.Groups]

class CompositeMeshInfo:
    
    def __init__(self):
        self.MeshCount = 0
        self.Meshes = []
        self.MeshInfoItemOffsets = []
        self.MeshInfoItems = []
        
    def Serialize(self, f: MemoryStream):
        start_position = f.tell()
        self.MeshCount = f.uint32(self.MeshCount)
        if f.IsReading(): self.Meshes = [0] * self.MeshCount
        self.Meshes = [f.uint32(mesh) for mesh in self.Meshes]
        if f.IsReading(): self.MeshInfoItemOffsets = [0] * self.MeshCount
        self.MeshInfoItemOffsets = [f.uint32(mesh) for mesh in self.MeshInfoItemOffsets]
        if f.IsReading(): self.MeshInfoItems = [CompositeMeshInfoItem() for _ in range(self.MeshCount)]
        for i, item in enumerate(self.MeshInfoItems):
            f.seek(start_position + self.MeshInfoItemOffsets[i])
            item.Serialize(f)
        

class StingrayCompositeUnit:
    def __init__(self):
        self.unk1 = self.NumUnits = self.StreamInfoOffset = 0
        self.Unreversed = bytearray()
        self.NumStreams = 0
        self.UnitHashes = []
        self.UnitTypeHashes = []
        self.MeshInfoOffsets = []
        self.StreamInfoArray = []
        self.StreamInfoOffsets = []
        self.MeshInfos = []
        self.StreamInfoUnk = []
        self.StreamInfoUnk2 = 0
        self.GpuData = None
    def Serialize(self, f: MemoryStream, gpu):
        self.unk1               = f.uint64(self.unk1)
        self.NumUnits           = f.uint32(self.NumUnits)
        self.StreamInfoOffset   = f.uint32(self.StreamInfoOffset)
        if f.IsReading():
            self.UnitHashes = [0] * self.NumUnits
            self.UnitTypeHashes = [0] * self.NumUnits
        for i in range(self.NumUnits):
            self.UnitTypeHashes[i] = f.uint64(self.UnitTypeHashes[i])
            self.UnitHashes[i] = f.uint64(self.UnitHashes[i])
        if f.IsReading():
            self.MeshInfoOffsets = [0] * self.NumUnits
        self.MeshInfoOffsets = [f.uint32(offset) for offset in self.MeshInfoOffsets]
        if f.IsReading(): self.MeshInfos = [CompositeMeshInfo() for _ in range(self.NumUnits)]
        for i, offset in enumerate(self.MeshInfoOffsets):
            f.seek(offset)
            self.MeshInfos[i].Serialize(f)
            
        if f.IsReading():
            self.Unreversed = bytearray(self.StreamInfoOffset-f.tell())
        self.Unreversed     = f.bytes(self.Unreversed)

        if f.IsReading(): f.seek(self.StreamInfoOffset)
        else:
            f.seek(ceil(float(f.tell())/16)*16); self.StreamInfoOffset = f.tell()
        self.NumStreams = f.uint32(len(self.StreamInfoArray))
        if f.IsWriting():
            self.StreamInfoOffsets = [0 for n in range(self.NumStreams)]
            self.StreamInfoUnk = [mesh_info.UnitID for mesh_info in self.MeshInfoArray[:self.NumStreams]]
        if f.IsReading():
            self.StreamInfoOffsets = [0 for n in range(self.NumStreams)]
            self.StreamInfoUnk     = [0 for n in range(self.NumStreams)]
            self.StreamInfoArray   = [StreamInfo() for n in range(self.NumStreams)]

        self.StreamInfoOffsets  = [f.uint32(Offset) for Offset in self.StreamInfoOffsets]
        self.StreamInfoUnk      = [f.uint32(Unk) for Unk in self.StreamInfoUnk]
        self.StreamInfoUnk2     = f.uint32(self.StreamInfoUnk2)
        for stream_idx in range(self.NumStreams):
            if f.IsReading(): f.seek(self.StreamInfoOffset + self.StreamInfoOffsets[stream_idx])
            else            : self.StreamInfoOffsets[stream_idx] = f.tell() - self.StreamInfoOffset
            self.StreamInfoArray[stream_idx] = self.StreamInfoArray[stream_idx].Serialize(f)

        self.GpuData = gpu
        return self

def LoadStingrayCompositeUnit(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    StingrayCompositeMeshData = StingrayCompositeUnit()
    StingrayCompositeMeshData.Serialize(MemoryStream(TocData), MemoryStream(GpuData))
    return StingrayCompositeMeshData

#endregion

#region Classes and Functions: Stingray Meshes
Global_MaterialSlotNames = {}


class StingrayMatrix4x4: # Matrix4x4: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_89
    def __init__(self):
        self.v = [float(0)]*16
    def Serialize(self, f: MemoryStream):
        self.v = [f.float32(value) for value in self.v]
        return self
    def ToLocalTransform(self):
        matrix = mathutils.Matrix([
            [self.v[0], self.v[1], self.v[2], self.v[12]],
            [self.v[4], self.v[5], self.v[6], self.v[13]],
            [self.v[8], self.v[9], self.v[10], self.v[14]],
            [self.v[3], self.v[7], self.v[11], self.v[15]]
        ])
        local_transform = StingrayLocalTransform()
        loc, rot, scale = matrix.decompose()
        rot = rot.to_matrix()
        local_transform.pos = loc
        local_transform.scale = scale
        local_transform.rot.x = rot[0]
        local_transform.rot.y = rot[1]
        local_transform.rot.z = rot[2]
        return local_transform

class StingrayMatrix3x3: # Matrix3x3: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_84
    def __init__(self):
        self.x = [1,0,0]
        self.y = [0,1,0]
        self.z = [0,0,1]
    def Serialize(self, f: MemoryStream):
        self.x = f.vec3_float(self.x)
        self.y = f.vec3_float(self.y)
        self.z = f.vec3_float(self.z)
        return self
    def ToQuaternion(self):
        T = self.x[0] + self.y[1] + self.z[2]
        M = max(T, self.x[0], self.y[1], self.z[2])
        qmax = 0.5 * sqrt(1-T + 2*M)
        if M == self.x[0]:
            qx = qmax
            qy = (self.x[1] + self.y[0]) / (4*qmax)
            qz = (self.x[2] + self.z[0]) / (4*qmax)
            qw = (self.z[1] - self.y[2]) / (4*qmax)
        elif M == self.y[1]:
            qx = (self.x[1] + self.y[0]) / (4*qmax)
            qy = qmax
            qz = (self.y[2] + self.z[1]) / (4*qmax)
            qw = (self.x[2] - self.z[0]) / (4*qmax)
        elif M == self.z[2]:
            qx = (self.x[2] + self.z[0]) / (4*qmax)
            qy = (self.y[2] + self.z[1]) / (4*qmax)
            qz = qmax
            qw = (self.x[2] - self.z[0]) / (4*qmax)
        else:
            qx = (self.z[1] - self.y[2]) / (4*qmax)
            qy = (self.x[2] - self.z[0]) / (4*qmax)
            qz = (self.y[0] + self.x[1]) / (4*qmax)
            qw = qmax
        return [qx, qy, qz, qw]

class StingrayLocalTransform: # Stingray Local Transform: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_100
    def __init__(self):
        self.rot   = StingrayMatrix3x3()
        self.pos   = [0,0,0]
        self.scale = [1,1,1]
        self.dummy = 0 # Force 16 byte alignment
        self.Incriment = self.ParentBone = 0

    def Serialize(self, f: MemoryStream):
        self.rot    = self.rot.Serialize(f)
        self.pos    = f.vec3_float(self.pos)
        self.scale  = f.vec3_float(self.scale)
        self.dummy  = f.float32(self.dummy)
        return self
    def SerializeV2(self, f: MemoryStream): # Quick and dirty solution, unknown exactly what this is for
        f.seek(f.tell()+48)
        self.pos    = f.vec3_float(self.pos)
        self.dummy  = f.float32(self.dummy)
        return self
    def SerializeTransformEntry(self, f: MemoryStream):
        self.Incriment = f.uint16(self.Incriment)
        self.ParentBone = f.uint16(self.ParentBone)
        return self

class TransformInfo: # READ ONLY
    def __init__(self):
        self.NumTransforms = 0
        self.Transforms = []
        self.TransformMatrices = []
        self.TransformEntries = []
        self.NameHashes = []
    def Serialize(self, f: MemoryStream):
        if f.IsReading():
            self.NumTransforms = f.uint32(self.NumTransforms)
            f.seek(f.tell()+12)
            self.Transforms = [StingrayLocalTransform().Serialize(f) for n in range(self.NumTransforms)]
            self.TransformMatrices = [StingrayMatrix4x4().Serialize(f) for n in range(self.NumTransforms)]
            self.TransformEntries = [StingrayLocalTransform().SerializeTransformEntry(f) for n in range(self.NumTransforms)]
            self.NameHashes = [f.uint32(n) for n in range(self.NumTransforms)]
            PrettyPrint(f"hashes: {self.NameHashes}")
        else:
            self.NumTransforms = f.uint32(self.NumTransforms)
            f.seek(f.tell()+12)
            self.Transforms = [t.Serialize(f) for t in self.Transforms]
            self.TransformMatrices = [t.Serialize(f) for t in self.TransformMatrices]
            self.TransformEntries = [t.SerializeTransformEntry(f) for t in self.TransformEntries]
            self.NameHashes = [f.uint32(h) for h in self.NameHashes]
        return self

class CustomizationInfo: # READ ONLY
    def __init__(self):
        self.BodyType  = ""
        self.Slot      = ""
        self.Weight    = ""
        self.PieceType = ""
    def Serialize(self, f: MemoryStream):
        if f.IsWriting():
            raise Exception("This struct is read only (write not implemented)")
        try: # TODO: fix this, this is basically completely wrong, this is generic user data, but for now this works
            f.seek(f.tell()+24)
            length = f.uint32(0)
            self.BodyType = bytes(f.bytes(b"", length)).replace(b"\x00", b"").decode()
            f.seek(f.tell()+12)
            length = f.uint32(0)
            self.Slot = bytes(f.bytes(b"", length)).replace(b"\x00", b"").decode()
            f.seek(f.tell()+12)
            length = f.uint32(0)
            self.Weight = bytes(f.bytes(b"", length)).replace(b"\x00", b"").decode()
            f.seek(f.tell()+12)
            length = f.uint32(0)
            self.PieceType = bytes(f.bytes(b"", length)).replace(b"\x00", b"").decode()
        except:
            self.BodyType  = ""
            self.Slot      = ""
            self.Weight    = ""
            self.PieceType = ""
            pass # tehee


class StreamComponentInfo:
    
    def __init__(self, type="position", format="float"):
        self.Type   = self.TypeFromName(type)
        self.Format = self.FormatFromName(format)
        self.Index   = 0
        self.Unknown = 0
    def Serialize(self, f: MemoryStream):
        self.Type      = f.uint32(self.Type)
        self.Format    = f.uint32(self.Format)
        self.Index     = f.uint32(self.Index)
        self.Unknown   = f.uint64(self.Unknown)
        return self
    def TypeName(self):
        if   self.Type == 0: return "position"
        elif self.Type == 1: return "normal"
        elif self.Type == 2: return "tangent" # not confirmed
        elif self.Type == 3: return "bitangent" # not confirmed
        elif self.Type == 4: return "uv"
        elif self.Type == 5: return "color"
        elif self.Type == 6: return "bone_index"
        elif self.Type == 7: return "bone_weight"
        return "unknown"
    def TypeFromName(self, name):
        if   name == "position": return 0
        elif name == "normal":   return 1
        elif name == "tangent":  return 2
        elif name == "bitangent":return 3
        elif name == "uv":       return 4
        elif name == "color":    return 5
        elif name == "bone_index":  return 6
        elif name == "bone_weight": return 7
        return -1
    def FormatName(self):
        # check archive 9102938b4b2aef9d
        if   self.Format == 0:  return "float"
        elif self.Format == 1:  return "vec2_float"
        elif self.Format == 2:  return "vec3_float"
        elif self.Format == 4:  return "rgba_r8g8b8a8"
        elif self.Format == 20: return "vec4_uint32" # vec4_uint32 ??
        elif self.Format == 24: return "vec4_uint8"
        elif self.Format == 25: return "vec4_1010102"
        elif self.Format == 26: return "unk_normal"
        elif self.Format == 29: return "vec2_half"
        elif self.Format == 31: return "vec4_half" # found in archive 738130362c354ceb->8166218779455159235.mesh
        return "unknown"
    def FormatFromName(self, name):
        if   name == "float":         return 0
        elif name == "vec3_float":    return 2
        elif name == "rgba_r8g8b8a8": return 4
        elif name == "vec4_uint32": return 20 # unconfirmed
        elif name == "vec4_uint8":  return 24
        elif name == "vec4_1010102":  return 25
        elif name == "unk_normal":  return 26
        elif name == "vec2_half":   return 29
        elif name == "vec4_half":   return 31
        return -1
    def GetSize(self):
        if   self.Format == 0:  return 4
        elif self.Format == 2:  return 12
        elif self.Format == 4:  return 4
        elif self.Format == 20: return 16
        elif self.Format == 24: return 4
        elif self.Format == 25: return 4
        elif self.Format == 26: return 4
        elif self.Format == 29: return 4
        elif self.Format == 31: return 8
        raise Exception("Cannot get size of unknown vertex format: "+str(self.Format))
    def SerializeComponent(self, f: MemoryStream, value):
        try:
            serialize_func = FUNCTION_LUTS.SERIALIZE_COMPONENT_LUT[self.Format]
            return serialize_func(f, value)
        except:
            raise Exception("Cannot serialize unknown vertex format: "+str(self.Format))

class BoneInfo:
    def __init__(self):
        self.NumBones = self.unk1 = self.RealIndicesOffset = self.FakeIndicesOffset = self.NumFakeIndices = self.FakeIndicesUnk = 0
        self.Bones = self.RealIndices = self.FakeIndices = []
        self.NumRemaps = self.MatrixOffset = 0
        self.Remaps = self.RemapOffsets = self.RemapCounts = []
    def Serialize(self, f: MemoryStream, end=None):
        self.Serialize_REAL(f)
        return self

    def Serialize_REAL(self, f: MemoryStream): # still need to figure out whats up with the unknown bit
        RelPosition = f.tell()
        
        self.NumBones       = f.uint32(self.NumBones)
        self.MatrixOffset           = f.uint32(self.MatrixOffset) # matrix pointer
        self.RealIndicesOffset = f.uint32(self.RealIndicesOffset) # unit indices
        self.FakeIndicesOffset = f.uint32(self.FakeIndicesOffset) # remap indices
        # get bone data
        if f.IsReading():
            self.Bones = [StingrayMatrix4x4() for n in range(self.NumBones)]
            self.RealIndices = [0 for n in range(self.NumBones)]
            self.FakeIndices = [0 for n in range(self.NumBones)]
        if f.IsReading(): f.seek(RelPosition+self.MatrixOffset)
        else            : self.MatrixOffset = f.tell()-RelPosition
        # save the right bone
        for i, bone in enumerate(self.Bones):
            if i == self.NumBones:
                break
            bone.Serialize(f)
        #self.Bones = [bone.Serialize(f) for bone in self.Bones]
        # get real indices
        if f.IsReading(): f.seek(RelPosition+self.RealIndicesOffset)
        else            : self.RealIndicesOffset = f.tell()-RelPosition
        self.RealIndices = [f.uint32(index) for index in self.RealIndices]

        # get remapped indices
        if f.IsReading(): f.seek(RelPosition+self.FakeIndicesOffset)
        else            : self.FakeIndicesOffset = f.tell()-RelPosition
        if f.IsReading():
            RemapStartPosition = f.tell()
            self.NumRemaps = f.uint32(self.NumRemaps)
            self.RemapOffsets = [0]*self.NumRemaps
            self.RemapCounts = [0]*self.NumRemaps
            for i in range(self.NumRemaps):
                self.RemapOffsets[i] = f.uint32(self.RemapOffsets[i])
                self.RemapCounts[i] = f.uint32(self.RemapCounts[i])
            for i in range(self.NumRemaps):
                f.seek(RemapStartPosition+self.RemapOffsets[i])
                self.Remaps.append([0]*self.RemapCounts[i])
                self.Remaps[i] = [f.uint32(index) for index in self.Remaps[i]]
        else:
            RemapStartPosition = f.tell()
            self.NumRemaps = f.uint32(self.NumRemaps)
            for i in range(self.NumRemaps):
                self.RemapOffsets[i] = f.uint32(self.RemapOffsets[i])
                self.RemapCounts[i] = f.uint32(self.RemapCounts[i])
            for i in range(self.NumRemaps):
                f.seek(RemapStartPosition+self.RemapOffsets[i])
                self.Remaps[i] = [f.uint32(index) for index in self.Remaps[i]]
        return self
    def GetRealIndex(self, bone_index, material_index=0):
        FakeIndex = self.Remaps[material_index][bone_index]
        return self.RealIndices[FakeIndex]
        
    def GetRemappedIndex(self, bone_index, material_index=0):
        return self.Remaps[material_index].index(self.RealIndices.index(bone_index))
        
    def SetRemap(self, remap_info: list[list[str]], transform_info):
        # remap_info is a list of bones indexed by material
        # so the list of bones for material slot 0 is covered by remap_info[0]
        #ideally this eventually allows for creating a remap for any arbitrary bone; requires editing the transform_info
        #return
        # I wonder if you can just take the transform component from the previous bone it was on
        # remap index should match the transform_info index!!!!!
        self.NumRemaps = len(remap_info)
        self.RemapCounts = [0] * self.NumRemaps
        #self.RemapCounts = [len(bone_names) for bone_names in remap_info]
        self.Remaps = []
        self.RemapOffsets = [8*self.NumRemaps+4]
        for i, bone_names in enumerate(remap_info):
            r = []
            for bone in bone_names:
                try:
                    h = int(bone)
                except ValueError:
                    h = murmur32_hash(bone.encode("utf-8"))
                try:
                    real_index = transform_info.NameHashes.index(h)
                except ValueError: # bone not in transform info for unit, unrecoverable
                    PrettyPrint(f"Bone '{bone}' does not exist in unit transform info, skipping...")
                    continue
                try:
                    r.append(self.RealIndices.index(real_index))
                    self.RemapCounts[i] += 1
                except ValueError:
                    PrettyPrint(f"Bone '{bone}' does not exist in LOD bone info, skipping...")
            self.Remaps.append(r)
            
        for i in range(1, self.NumRemaps):
            self.RemapOffsets.append(self.RemapOffsets[i-1]+4*self.RemapCounts[i])

class StreamInfo:
    def __init__(self):
        self.Components = []
        self.ComponentInfoID = self.NumComponents = self.VertexBufferID = self.VertexBuffer_unk1 = self.NumVertices = self.VertexStride = self.VertexBuffer_unk2 = self.VertexBuffer_unk3 = 0
        self.IndexBufferID = self.IndexBuffer_unk1 = self.NumIndices = self.IndexBuffer_unk2 = self.IndexBuffer_unk3 = self.IndexBuffer_Type = self.VertexBufferOffset = self.VertexBufferSize = self.IndexBufferOffset = self.IndexBufferSize = 0
        self.VertexBufferOffset = self.VertexBufferSize = self.IndexBufferOffset = self.IndexBufferSize = 0
        self.UnkEndingBytes = bytearray(16)
        self.DEV_StreamInfoOffset    = self.DEV_ComponentInfoOffset = 0 # helper vars, not in file

    def Serialize(self, f: MemoryStream):
        self.DEV_StreamInfoOffset = f.tell()
        self.ComponentInfoID = f.uint64(self.ComponentInfoID)
        self.DEV_ComponentInfoOffset = f.tell()
        f.seek(self.DEV_ComponentInfoOffset + 320)
        # vertex buffer info
        self.NumComponents      = f.uint64(len(self.Components))
        self.VertexBufferID     = f.uint64(self.VertexBufferID)
        self.VertexBuffer_unk1  = f.uint64(self.VertexBuffer_unk1)
        self.NumVertices        = f.uint32(self.NumVertices)
        self.VertexStride       = f.uint32(self.VertexStride)
        self.VertexBuffer_unk2  = f.uint64(self.VertexBuffer_unk2)
        self.VertexBuffer_unk3  = f.uint64(self.VertexBuffer_unk3)
        # index buffer info
        self.IndexBufferID      = f.uint64(self.IndexBufferID)
        self.IndexBuffer_unk1   = f.uint64(self.IndexBuffer_unk1)
        self.NumIndices         = f.uint32(self.NumIndices)
        self.IndexBuffer_Type   = f.uint32(self.IndexBuffer_Type)
        self.IndexBuffer_unk2   = f.uint64(self.IndexBuffer_unk2)
        self.IndexBuffer_unk3   = f.uint64(self.IndexBuffer_unk3)
        # offset info
        self.VertexBufferOffset = f.uint32(self.VertexBufferOffset)
        self.VertexBufferSize   = f.uint32(self.VertexBufferSize)
        self.IndexBufferOffset  = f.uint32(self.IndexBufferOffset)
        self.IndexBufferSize    = f.uint32(self.IndexBufferSize)
        # allign to 16
        self.UnkEndingBytes     = f.bytes(self.UnkEndingBytes, 16) # exact length is unknown
        EndOffset = ceil(float(f.tell())/16) * 16
        # component info
        f.seek(self.DEV_ComponentInfoOffset)
        if f.IsReading():
            self.Components = [StreamComponentInfo() for n in range(self.NumComponents)]
        self.Components = [Comp.Serialize(f) for Comp in self.Components]

        # return
        f.seek(EndOffset)
        return self

class MeshSectionInfo: # material info
    def __init__(self, material_slot_list=[]):
        self.MaterialIndex = self.VertexOffset=self.NumVertices=self.IndexOffset=self.NumIndices=self.unk2 = 0
        self.DEV_MeshInfoOffset=0 # helper var, not in file
        self.material_slot_list = material_slot_list
        self.ID = 0
        self.MaterialIndex = self.GroupIndex = 0
    def Serialize(self, f: MemoryStream):
        self.DEV_MeshInfoOffset = f.tell()
        self.MaterialIndex           = f.uint32(self.MaterialIndex)
        if f.IsReading():
            self.ID = self.material_slot_list[self.MaterialIndex]
        self.VertexOffset   = f.uint32(self.VertexOffset)
        self.NumVertices    = f.uint32(self.NumVertices)
        self.IndexOffset    = f.uint32(self.IndexOffset)
        self.NumIndices     = f.uint32(self.NumIndices)
        self.GroupIndex           = f.uint32(self.GroupIndex)
        return self

class MeshInfo:
    def __init__(self):
        self.unk1 = self.unk3 = self.unk4 = self.TransformIndex = self.LodIndex = self.StreamIndex = self.NumSections = self.unk7 = self.unk8 = self.unk9 = self.NumSections_unk = self.UnitID = 0
        self.unk2 = bytearray(32); self.unk6 = bytearray(40)
        self.MaterialIDs = self.Sections = []
        self.NumMaterials = 0
        self.MaterialOffset = 0
        self.SectionsOffset = 0
    def Serialize(self, f: MemoryStream):
        start_offset = f.tell()
        self.unk1 = f.uint64(self.unk1)
        self.unk2 = f.bytes(self.unk2, 32)
        self.UnitID= f.uint32(self.UnitID)
        self.unk3 = f.uint32(self.unk3)
        self.TransformIndex = f.uint32(self.TransformIndex)
        self.unk4 = f.uint32(self.unk4)
        self.LodIndex       = f.int32(self.LodIndex)
        self.StreamIndex    = f.uint32(self.StreamIndex)
        self.unk6           = f.bytes(self.unk6, 40)
        self.NumMaterials = f.uint32(self.NumMaterials)
        self.MaterialOffset = f.uint32(self.MaterialOffset)
        self.unk8           = f.uint64(self.unk8)
        self.NumSections    = f.uint32(self.NumSections)
        if f.IsWriting(): self.SectionsOffset = self.MaterialOffset + 4*self.NumMaterials
        self.SectionsOffset  = f.uint32(self.SectionsOffset)
        if f.IsReading(): self.MaterialIDs  = [0 for n in range(self.NumMaterials)]
        else:             self.MaterialIDs  = [section.ID for section in self.Sections]
        self.MaterialIDs  = [f.uint32(ID) for ID in self.MaterialIDs]
        if f.IsReading(): self.Sections    = [MeshSectionInfo(self.MaterialIDs) for n in range(self.NumSections)]
        self.Sections   = [Section.Serialize(f) for Section in self.Sections]
        return self
    def GetNumIndices(self):
        total = 0
        for section in self.Sections:
            total += section.NumIndices
        return total
    def GetNumVertices(self):
        return self.Sections[0].NumVertices

class RawMaterialClass:
    DefaultMaterialName    = "StingrayDefaultMaterial"
    DefaultMaterialShortID = 155175220
    def __init__(self):
        self.MatID      = self.DefaultMaterialName
        self.ShortID    = self.DefaultMaterialShortID
        self.StartIndex = 0
        self.NumIndices = 0
        self.DEV_BoneInfoOverride = None
    def IDFromName(self, unit_id, name, index):
        if name.find(self.DefaultMaterialName) != -1:
            self.MatID   = self.DefaultMaterialName
            self.ShortID = self.DefaultMaterialShortID
        else:
            try:
                self.MatID   = int(name)
                # self.ShortID = r.randint(1, 0xffffffff)
                
                try:
                    self.ShortID = Global_MaterialSlotNames[unit_id][self.MatID][index]
                except (KeyError, IndexError):
                    PrettyPrint(f"Unable to find material slot for material {name} with material count {index} for unit {unit_id}, using random material slot name")
                    self.ShortID = r.randint(1, 0xffffffff)
            except:
                raise Exception("Material name must be a number")

class RawMeshClass:
    def __init__(self):
        self.MeshInfoIndex = 0
        self.VertexPositions  = []
        self.VertexNormals    = []
        self.VertexTangents   = []
        self.VertexBiTangents = []
        self.VertexUVs        = []
        self.VertexColors     = []
        self.VertexBoneIndices= []
        self.VertexWeights    = []
        self.Indices          = []
        self.Materials        = []
        self.LodIndex         = -1
        self.UnitID           = 0
        self.DEV_Use32BitIndices = False
        self.DEV_BoneInfo      = None
        self.DEV_BoneInfoIndex = 0
        self.DEV_Transform     = None
    def IsPhysicsBody(self):
        IsPhysics = True
        for material in self.Materials:
            if material.MatID != material.DefaultMaterialName:
                IsPhysics = False
        return IsPhysics
    def IsLod(self):
        IsLod = True
        if self.LodIndex == 0 or self.LodIndex == -1:
            IsLod = False
        if self.IsPhysicsBody():
            IsLod = False
        return IsLod
    def IsStaticMesh(self):
        for vertex in self.VertexWeights:
            if vertex != [0, 0, 0, 0]:
                return False
        return True

    def InitBlank(self, numVertices, numIndices, numUVs, numBoneIndices):
        self.VertexPositions    = [[0,0,0] for n in range(numVertices)]
        self.VertexNormals      = [[0,0,0] for n in range(numVertices)]
        self.VertexTangents     = [[0,0,0] for n in range(numVertices)]
        self.VertexBiTangents   = [[0,0,0] for n in range(numVertices)]
        self.VertexColors       = [[0,0,0,0] for n in range(numVertices)]
        self.VertexWeights      = [[0,0,0,0] for n in range(numVertices)]
        self.Indices            = [[0,0,0] for n in range(int(numIndices/3))]
        for idx in range(numUVs):
            self.VertexUVs.append([[0,0] for n in range(numVertices)])
        for idx in range(numBoneIndices):
            self.VertexBoneIndices.append([[0,0,0,0] for n in range(numVertices)])
    
    def ReInitVerts(self, numVertices):
        self.VertexPositions    = [[0,0,0] for n in range(numVertices)]
        self.VertexNormals      = [[0,0,0] for n in range(numVertices)]
        self.VertexTangents     = [[0,0,0] for n in range(numVertices)]
        self.VertexBiTangents   = [[0,0,0] for n in range(numVertices)]
        self.VertexColors       = [[0,0,0,0] for n in range(numVertices)]
        self.VertexWeights      = [[0,0,0,0] for n in range(numVertices)]
        numVerts        = len(self.VertexUVs)
        numBoneIndices  = len(self.VertexBoneIndices)
        self.VertexUVs = []
        self.VertexBoneIndices = []
        for idx in range(numVerts):
            self.VertexUVs.append([[0,0] for n in range(numVertices)])
        for idx in range(numBoneIndices):
            self.VertexBoneIndices.append([[0,0,0,0] for n in range(numVertices)])

class BoneIndexException(Exception):
    pass

def sign(n):
    if n >= 0:
        return 1
    if n < 0:
        return -1

def octahedral_encode(x, y, z):
    l1_norm = abs(x) + abs(y) + abs(z)
    if l1_norm == 0: return 0, 0
    x /= l1_norm
    y /= l1_norm
    if z < 0:
        x, y = ((1-abs(y)) * sign(x)), ((1-abs(x)) * sign(y))
    return x, y

def octahedral_decode(x, y):
    z = 1 - abs(x) - abs(y)
    if z < 0:
        x, y = ((1-abs(y)) * sign(x)), ((1-abs(x)) * sign(y))
    return mathutils.Vector((x, y, z)).normalized().to_tuple()

def decode_packed_oct_norm(norm):
    r10 = norm & 0x3ff
    g10 = (norm >> 10) & 0x3ff
    return octahedral_decode(
        r10 * (2.0/1023.0) - 1,
        g10 * (2.0/1023.0) - 1
    )

def encode_packed_oct_norm(x, y, z):
    x, y = octahedral_encode(x, y, z)
    return int((x+1)*(1023.0/2.0)) | (int((y+1)*(1023.0/2.0)) << 10)

class SerializeFunctions:
    
    def SerializePositionComponent(gpu, mesh, component, vidx):
        mesh.VertexPositions[vidx] = component.SerializeComponent(gpu, mesh.VertexPositions[vidx])
    
    def SerializeNormalComponent(gpu, mesh, component, vidx):
        # norm = component.SerializeComponent(gpu, mesh.VertexNormals[vidx])
        if gpu.IsReading():
            norm = component.SerializeComponent(gpu, mesh.VertexNormals[vidx])
            if not isinstance(norm, int):
                norm = list(mathutils.Vector((norm[0],norm[1],norm[2])).normalized())
                mesh.VertexNormals[vidx] = norm[:3]
            else:
                # mesh.VertexNormals[vidx] = norm
                
                mesh.VertexNormals[vidx] = decode_packed_oct_norm(norm)
        else:
            norm = encode_packed_oct_norm(*mathutils.Vector(mesh.VertexNormals[vidx]).normalized().to_tuple())
            norm = component.SerializeComponent(gpu, norm)
    
    def SerializeTangentComponent(gpu, mesh, component, vidx):
        mesh.VertexTangents[vidx] = component.SerializeComponent(gpu, mesh.VertexTangents[vidx])
    
    def SerializeBiTangentComponent(gpu, mesh, component, vidx):
        mesh.VertexBiTangents[vidx] = component.SerializeComponent(gpu, mesh.VertexBiTangents[vidx])
    
    def SerializeUVComponent(gpu, mesh, component, vidx):
        mesh.VertexUVs[component.Index][vidx] = component.SerializeComponent(gpu, mesh.VertexUVs[component.Index][vidx])
    
    def SerializeColorComponent(gpu, mesh, component, vidx):
        mesh.VertexColors[vidx] = component.SerializeComponent(gpu, mesh.VertexColors[vidx])
    
    def SerializeBoneIndexComponent(gpu, mesh, component, vidx):
        try:
             mesh.VertexBoneIndices[component.Index][vidx] = component.SerializeComponent(gpu, mesh.VertexBoneIndices[component.Index][vidx])
        except:
            raise BoneIndexException(f"Vertex bone index out of range. Component index: {component.Index} vidx: {vidx}")
    
    def SerializeBoneWeightComponent(gpu, mesh, component, vidx):
        if component.Index > 0: # TODO: add support for this (check archive 9102938b4b2aef9d)
            PrettyPrint("Multiple weight indices are unsupported!", "warn")
            gpu.seek(gpu.tell()+component.GetSize())
        else:
            mesh.VertexWeights[vidx] = component.SerializeComponent(gpu, mesh.VertexWeights[vidx])


    def SerializeFloatComponent(f, value):
        return f.float32(value)
        
    def SerializeVec2FloatComponent(f, value):
        return f.vec2_float(value)
        
    def SerializeVec3FloatComponent(f, value):
        return f.vec3_float(value)
        
    def SerializeRGBA8888Component(f, value):
        if f.IsReading():
            r = min(255, int(value[0]*255))
            g = min(255, int(value[1]*255))
            b = min(255, int(value[2]*255))
            a = min(255, int(value[3]*255))
            value = f.vec4_uint8([r,g,b,a])
        else:
            value = f.vec4_uint8([r,g,b,a])
            value[0] = min(1, float(value[0]/255))
            value[1] = min(1, float(value[1]/255))
            value[2] = min(1, float(value[2]/255))
            value[3] = min(1, float(value[3]/255))
        return value
        
    def SerializeVec4Uint32Component(f, value):
        return f.vec4_uint32(value)
        
    def SerializeVec4Uint8Component(f, value):
        return f.vec4_uint8(value)
        
    def SerializeVec41010102Component(f, value):
        if f.IsReading():
            value = TenBitUnsigned(f.uint32(0))
            value[3] = 0 # seems to be needed for weights
        else:
            f.uint32(MakeTenBitUnsigned(value))
        return value
        
    def SerializeUnkNormalComponent(f, value):
        if isinstance(value, int):
            return f.uint32(value)
        else:
            return f.uint32(0)
            
    def SerializeVec2HalfComponent(f, value):
        return f.vec2_half(value)
        
    def SerializeVec4HalfComponent(f, value):
        if isinstance(value, float):
            return f.vec4_half([value,value,value,value])
        else:
            return f.vec4_half(value)
            
    def SerializeUnknownComponent(f, value):
        raise Exception("Cannot serialize unknown vertex format!")

class StreamComponentType:
    POSITION = 0
    NORMAL = 1
    TANGENT = 2 # not confirmed
    BITANGENT = 3 # not confirmed
    UV = 4
    COLOR = 5
    BONE_INDEX = 6
    BONE_WEIGHT = 7
    UNKNOWN_TYPE = -1
    
class StreamComponentFormat:
    FLOAT = 0
    VEC2_FLOAT = 1
    VEC3_FLOAT = 2
    RGBA_R8G8B8A8 = 4
    VEC4_UINT32 = 20 # unconfirmed
    VEC4_UINT8 = 24
    VEC4_1010102 = 25
    UNK_NORMAL = 26
    VEC2_HALF = 29
    VEC4_HALF = 31
    UNKNOWN_TYPE = -1

class FUNCTION_LUTS:

    SERIALIZE_MESH_LUT = {
        StreamComponentType.POSITION: SerializeFunctions.SerializePositionComponent,
        StreamComponentType.NORMAL: SerializeFunctions.SerializeNormalComponent,
        StreamComponentType.TANGENT: SerializeFunctions.SerializeTangentComponent,
        StreamComponentType.BITANGENT: SerializeFunctions.SerializeBiTangentComponent,
        StreamComponentType.UV: SerializeFunctions.SerializeUVComponent,
        StreamComponentType.COLOR: SerializeFunctions.SerializeColorComponent,
        StreamComponentType.BONE_INDEX: SerializeFunctions.SerializeBoneIndexComponent,
        StreamComponentType.BONE_WEIGHT: SerializeFunctions.SerializeBoneWeightComponent
    }

    SERIALIZE_COMPONENT_LUT = {
        StreamComponentFormat.FLOAT: SerializeFunctions.SerializeFloatComponent,
        StreamComponentFormat.VEC2_FLOAT: SerializeFunctions.SerializeVec2FloatComponent,
        StreamComponentFormat.VEC3_FLOAT: SerializeFunctions.SerializeVec3FloatComponent,
        StreamComponentFormat.RGBA_R8G8B8A8: SerializeFunctions.SerializeRGBA8888Component,
        StreamComponentFormat.VEC4_UINT32: SerializeFunctions.SerializeVec4Uint32Component,
        StreamComponentFormat.VEC4_UINT8: SerializeFunctions.SerializeVec4Uint8Component,
        StreamComponentFormat.VEC4_1010102: SerializeFunctions.SerializeVec41010102Component,
        StreamComponentFormat.UNK_NORMAL: SerializeFunctions.SerializeUnkNormalComponent,
        StreamComponentFormat.VEC2_HALF: SerializeFunctions.SerializeVec2HalfComponent,
        StreamComponentFormat.VEC4_HALF: SerializeFunctions.SerializeVec4HalfComponent
    }

class StingrayMeshFile:
    def __init__(self):
        self.HeaderData1        = bytearray(28);  self.HeaderData2        = bytearray(20); self.UnReversedData1  = bytearray(); self.UnReversedData2    = bytearray()
        self.StreamInfoOffset   = self.EndingOffset = self.MeshInfoOffset = self.NumStreams = self.NumMeshes = self.EndingBytes = self.StreamInfoUnk2 = self.HeaderUnk = self.MaterialsOffset = self.NumMaterials = self.NumBoneInfo = self.BoneInfoOffset = 0
        self.StreamInfoOffsets  = self.StreamInfoUnk = self.StreamInfoArray = self.MeshInfoOffsets = self.MeshInfoUnk = self.MeshInfoArray = []
        self.CustomizationInfoOffset = self.UnkHeaderOffset1 = self.UnkHeaderOffset2 = self.TransformInfoOffset = self.UnkRef1 = self.BonesRef = self.CompositeRef = 0
        self.BoneInfoOffsets = self.BoneInfoArray = []
        self.RawMeshes = []
        self.SectionsIDs = []
        self.MaterialIDs = []
        self.DEV_MeshInfoMap = [] # Allows removing of meshes while mapping them to the original meshes
        self.CustomizationInfo = CustomizationInfo()
        self.TransformInfo     = TransformInfo()
        self.BoneNames = None
        self.UnreversedData1_2 = bytearray()
        self.NameHash = 0
        self.LoadMaterialSlotNames = True

    # -- Serialize Mesh -- #
    def Serialize(self, f, gpu, Global_TocManager, redo_offsets = False):
        PrettyPrint("Serialize")
        if f.IsWriting() and not redo_offsets:
            # duplicate bone info sections if needed
            temp_boneinfos = [None for n in range(len(self.BoneInfoArray))]
            for Raw_Mesh in self.RawMeshes:
                idx         = Raw_Mesh.MeshInfoIndex
                Mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[idx]]
                if Mesh_info.LodIndex == -1:
                    continue
                RealBoneInfoIdx = Mesh_info.LodIndex
                BoneInfoIdx     = Raw_Mesh.DEV_BoneInfoIndex
                temp_boneinfos[RealBoneInfoIdx] = self.BoneInfoArray[BoneInfoIdx]
            self.BoneInfoArray = temp_boneinfos
            PrettyPrint("Building materials")
            self.SectionsIDs = []
            self.MaterialIDs = []
            Order = 0xffffffff
            for Raw_Mesh in self.RawMeshes:
                if len(Raw_Mesh.Materials) == 0:
                    raise Exception("Mesh has no materials, but at least one is required")
                idx         = Raw_Mesh.MeshInfoIndex
                Mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[idx]]
                Mesh_info.Sections = []
                Mesh_info.NumSections = 0
                Mesh_info.NumMaterials = 0
                for Material in Raw_Mesh.Materials:
                    Section = MeshSectionInfo()
                    Section.ID          = int(Material.ShortID)
                    Section.NumIndices  = Material.NumIndices
                    Section.VertexOffset  = Order # | Used for ordering function
                    Section.IndexOffset   = Order # /

                    # This doesnt do what it was intended to do
                    if Material.DEV_BoneInfoOverride != None:
                        PrettyPrint("Overriding unknown material values")
                        Section.MaterialIndex = Material.DEV_BoneInfoOverride
                        Section.GroupIndex = Material.DEV_BoneInfoOverride
                    else:
                        Section.MaterialIndex = len(Mesh_info.Sections) # | dont know what these actually are, but this is usually correct it seems
                        Section.GroupIndex = len(Mesh_info.Sections) # /

                    Mesh_info.Sections.append(Section)
                    Mesh_info.NumSections += 1
                    Mesh_info.NumMaterials += 1
                    Order -= 1
                    try: # if material ID uses the defualt material string it will throw an error, but thats fine as we dont want to include those ones anyway
                        #if int(Material.MatID) not in self.MaterialIDs:
                        self.MaterialIDs.append(int(Material.MatID))
                        self.SectionsIDs.append(int(Material.ShortID)) # MATERIAL SLOT NAME
                    except:
                        pass

        # serialize file
        self.UnkRef1            = f.uint64(self.UnkRef1)
        self.BonesRef           = f.uint64(self.BonesRef)
        if f.IsWriting():         f.uint64(0)
        else: self.CompositeRef = f.uint64(self.CompositeRef)
        self.HeaderData1        = f.bytes(self.HeaderData1, 28)
        self.TransformInfoOffset= f.uint32(self.TransformInfoOffset)
        self.HeaderData2        = f.bytes(self.HeaderData2, 20)
        self.CustomizationInfoOffset  = f.uint32(self.CustomizationInfoOffset)
        self.UnkHeaderOffset1   = f.uint32(self.UnkHeaderOffset1)
        self.UnkHeaderOffset2   = f.uint32(self.UnkHeaderOffset2)
        self.BoneInfoOffset     = f.uint32(self.BoneInfoOffset)
        self.StreamInfoOffset   = f.uint32(self.StreamInfoOffset)
        self.EndingOffset       = f.uint32(self.EndingOffset)
        self.MeshInfoOffset     = f.uint32(self.MeshInfoOffset)
        self.HeaderUnk          = f.uint64(self.HeaderUnk)
        self.MaterialsOffset    = f.uint32(self.MaterialsOffset)

        if f.IsReading() and self.MeshInfoOffset == 0:
            raise Exception("Unsupported Mesh Format (No geometry)")

        if f.IsReading() and (self.StreamInfoOffset == 0 and self.CompositeRef == 0):
            raise Exception("Unsupported Mesh Format (No buffer stream)")

        # Get composite file
        if f.IsReading() and self.CompositeRef != 0:
            pass
            #Entry = Global_TocManager.GetEntry(self.CompositeRef, CompositeUnitID)
            #if Entry != None:
            #    Global_TocManager.Load(Entry.FileID, Entry.TypeID)
            #    self.StreamInfoArray = Entry.LoadedData.StreamInfoArray
            #    gpu = Entry.LoadedData.GpuData
            #else:
            #    raise Exception(f"Composite mesh file {self.CompositeRef} could not be found")

        # Get bones file
        if f.IsReading() and self.BonesRef != 0:
            Entry = Global_TocManager.GetEntry(self.BonesRef, BoneID)
            if Entry != None:
                Global_TocManager.Load(Entry.FileID, Entry.TypeID)
                self.BoneNames = Entry.LoadedData.Names
                self.BoneHashes = Entry.LoadedData.BoneHashes

        # Get Customization data: READ ONLY
        if f.IsReading() and self.CustomizationInfoOffset > 0:
            loc = f.tell(); f.seek(self.CustomizationInfoOffset)
            self.CustomizationInfo.Serialize(f)
            f.seek(loc)
        # Get Transform data: READ ONLY
        #if f.IsReading() and self.TransformInfoOffset > 0:
        UnreversedData1_2Size = 0
        if self.TransformInfoOffset > 0: # need to update other offsets?
            loc = f.tell(); f.seek(self.TransformInfoOffset)
            self.TransformInfo.Serialize(f)
            if f.tell() % 16 != 0:
                f.seek(f.tell() + (16-f.tell()%16))
            UnreversedData1_2Start = f.tell()
            if self.CustomizationInfoOffset > 0:
                self.CustomizationInfoOffset = UnreversedData1_2Start
            if f.IsReading():
                if self.BoneInfoOffset > 0:
                    UnreversedData1_2Size = self.BoneInfoOffset-f.tell()
                elif self.StreamInfoOffset > 0:
                    UnreversedData1_2Size = self.StreamInfoOffset-f.tell()
                elif self.MeshInfoOffset > 0:
                    UnreversedData1_2Size = self.MeshInfoOffset-f.tell()
            else:
                UnreversedData1_2Size = len(self.UnreversedData1_2)
            f.seek(loc)

        # Unreversed data before transform info offset (may include customization info)
        # Unreversed data intersects other data we want to leave alone!
        if f.IsReading():
            if self.TransformInfoOffset > 0:
                UnreversedData1Size = self.TransformInfoOffset - f.tell()
            elif self.BoneInfoOffset > 0:
                UnreversedData1Size = self.BoneInfoOffset-f.tell()
            elif self.StreamInfoOffset > 0:
                UnreversedData1Size = self.StreamInfoOffset-f.tell()
            elif self.MeshInfoOffset > 0:
                UnreversedData1Size = self.MeshInfoOffset-f.tell()
        else: UnreversedData1Size = len(self.UnReversedData1)
        try:
            self.UnReversedData1    = f.bytes(self.UnReversedData1, UnreversedData1Size)
        except:
            PrettyPrint(f"Could not set UnReversedData1", "ERROR")
        
        if self.TransformInfoOffset > 0:
            f.seek(UnreversedData1_2Start)
            if UnreversedData1_2Size > 0:
                self.UnreversedData1_2 = f.bytes(self.UnreversedData1_2, UnreversedData1_2Size)
        

        # Bone Info
        if f.IsReading(): f.seek(self.BoneInfoOffset)
        else            : self.BoneInfoOffset = f.tell()
        self.NumBoneInfo = f.uint32(len(self.BoneInfoArray))
        if f.IsWriting() and not redo_offsets:
            self.BoneInfoOffsets = [0]*self.NumBoneInfo
        if f.IsReading():
            self.BoneInfoOffsets = [0]*self.NumBoneInfo
            self.BoneInfoArray   = [BoneInfo() for n in range(self.NumBoneInfo)]
        self.BoneInfoOffsets    = [f.uint32(Offset) for Offset in self.BoneInfoOffsets]
        for boneinfo_idx in range(self.NumBoneInfo):
            end_offset = None
            if f.IsReading():
                f.seek(self.BoneInfoOffset + self.BoneInfoOffsets[boneinfo_idx])
                if boneinfo_idx+1 != self.NumBoneInfo:
                    end_offset = self.BoneInfoOffset + self.BoneInfoOffsets[boneinfo_idx+1]
                else:
                    end_offset = self.StreamInfoOffset
                    if self.StreamInfoOffset == 0:
                        end_offset = self.MeshInfoOffset
            else:
                self.BoneInfoOffsets[boneinfo_idx] = f.tell() - self.BoneInfoOffset
            self.BoneInfoArray[boneinfo_idx] = self.BoneInfoArray[boneinfo_idx].Serialize(f, end_offset)
            # Bone Hash linking
            # if f.IsReading(): 
            #     PrettyPrint("Hashes")
            #     PrettyPrint(f"Length of bone names: {len(self.BoneNames)}")
            #     HashOffset = self.CustomizationInfoOffset - ((len(self.BoneNames) - 1) * 4) # this is a bad work around as we can't always get the bone names since some meshes don't have a bone file listed
            #     PrettyPrint(f"Hash Offset: {HashOffset}")
            #     f.seek(HashOffset)
            #     self.MeshBoneHashes = [0 for n in range(len(self.BoneNames))]
            #     self.MeshBoneHashes = [f.uint32(Hash) for Hash in self.MeshBoneHashes]
            #     PrettyPrint(self.MeshBoneHashes)
            #     for index in self.BoneInfoArray[boneinfo_idx].RealIndices:
            #         BoneInfoHash = self.MeshBoneHashes[index]
            #         for index in range(len(self.BoneHashes)):
            #             if self.BoneHashes[index] == BoneInfoHash:
            #                 BoneName = self.BoneNames[index]
            #                 PrettyPrint(f"Index: {index}")
            #                 PrettyPrint(f"Bone: {BoneName}")
            #                 continue


        # Stream Info
        if self.StreamInfoOffset != 0:
            if f.IsReading(): f.seek(self.StreamInfoOffset)
            else:
                f.seek(ceil(float(f.tell())/16)*16); self.StreamInfoOffset = f.tell()
            self.NumStreams = f.uint32(len(self.StreamInfoArray))
            if f.IsWriting():
                if not redo_offsets: self.StreamInfoOffsets = [0]*self.NumStreams
                self.StreamInfoUnk = [mesh_info.UnitID for mesh_info in self.MeshInfoArray[:self.NumStreams]]
            if f.IsReading():
                self.StreamInfoOffsets = [0]*self.NumStreams
                self.StreamInfoUnk     = [0]*self.NumStreams
                self.StreamInfoArray   = [StreamInfo() for n in range(self.NumStreams)]

            self.StreamInfoOffsets  = [f.uint32(Offset) for Offset in self.StreamInfoOffsets]
            self.StreamInfoUnk      = [f.uint32(Unk) for Unk in self.StreamInfoUnk]
            self.StreamInfoUnk2     = f.uint32(self.StreamInfoUnk2)
            for stream_idx in range(self.NumStreams):
                if f.IsReading(): f.seek(self.StreamInfoOffset + self.StreamInfoOffsets[stream_idx])
                else            : self.StreamInfoOffsets[stream_idx] = f.tell() - self.StreamInfoOffset
                self.StreamInfoArray[stream_idx] = self.StreamInfoArray[stream_idx].Serialize(f)

        # Mesh Info
        if f.IsReading(): f.seek(self.MeshInfoOffset)
        else            : self.MeshInfoOffset = f.tell()
        self.NumMeshes = f.uint32(len(self.MeshInfoArray))

        if f.IsWriting():
            if not redo_offsets: self.MeshInfoOffsets = [0]*self.NumMeshes
            self.MeshInfoUnk = [mesh_info.UnitID for mesh_info in self.MeshInfoArray]
        if f.IsReading():
            self.MeshInfoOffsets = [0]*self.NumMeshes
            self.MeshInfoUnk     = [0]*self.NumMeshes
            self.MeshInfoArray   = [MeshInfo() for n in range(self.NumMeshes)]
            self.DEV_MeshInfoMap = [n for n in range(len(self.MeshInfoArray))]

        self.MeshInfoOffsets  = [f.uint32(Offset) for Offset in self.MeshInfoOffsets]
        self.MeshInfoUnk      = [f.uint32(Unk) for Unk in self.MeshInfoUnk]
        for mesh_idx in range(self.NumMeshes):
            if f.IsReading(): f.seek(self.MeshInfoOffset+self.MeshInfoOffsets[mesh_idx])
            else            : self.MeshInfoOffsets[mesh_idx] = f.tell() - self.MeshInfoOffset
            self.MeshInfoArray[mesh_idx] = self.MeshInfoArray[mesh_idx].Serialize(f)

        # Get geometry group
        if f.IsReading() and self.CompositeRef != 0:
            Entry = Global_TocManager.GetEntry(self.CompositeRef, CompositeUnitID)
            if Entry != None:
                Global_TocManager.Load(Entry.FileID, Entry.TypeID)
                geometry_group = Entry.LoadedData
                unit_index = geometry_group.UnitHashes.index(int(self.NameHash))
                c_mesh_info = geometry_group.MeshInfos[unit_index]
                self.StreamInfoArray = Entry.LoadedData.StreamInfoArray
                self.NumStreams = len(self.StreamInfoArray)
                for i, mesh_info_item in enumerate(self.MeshInfoArray):
                    mesh_index = c_mesh_info.Meshes.index(mesh_info_item.UnitID)
                    c_mesh_info_item = c_mesh_info.MeshInfoItems[mesh_index]
                    mesh_info_item.StreamIndex      = c_mesh_info_item.MeshLayoutIdx
                    mesh_info_item.NumMaterials     = c_mesh_info_item.NumMaterials
                    mesh_info_item.MaterialOffset   = c_mesh_info_item.MaterialsOffset + 0x50
                    mesh_info_item.Sections         = c_mesh_info_item.Groups
                    mesh_info_item.MaterialIDs      = c_mesh_info_item.Materials
                    mesh_info_item.SectionsOffset   = c_mesh_info_item.GroupsOffset + 0x50
                    mesh_info_item.NumSections      = c_mesh_info_item.NumGroups
                self.StreamInfoOffset = 1
                gpu = Entry.LoadedData.GpuData
            else:
                raise Exception(f"Composite mesh file {self.CompositeRef} could not be found")


        # Materials
        if f.IsReading(): f.seek(self.MaterialsOffset)
        else            : self.MaterialsOffset = f.tell()
        self.NumMaterials = f.uint32(len(self.MaterialIDs))
        if f.IsReading():
            self.SectionsIDs = [0]*self.NumMaterials
            self.MaterialIDs = [0]*self.NumMaterials
        self.SectionsIDs = [f.uint32(ID) for ID in self.SectionsIDs]
        self.MaterialIDs = [f.uint64(ID) for ID in self.MaterialIDs]
        if f.IsReading() and self.LoadMaterialSlotNames:
            global Global_MaterialSlotNames
            id = str(self.NameHash)
            if id not in Global_MaterialSlotNames:
                Global_MaterialSlotNames[id] = {}
            for i in range(self.NumMaterials):
                if self.MaterialIDs[i] not in Global_MaterialSlotNames[id]: # probably going to have to save material slot names per LOD/mesh
                    Global_MaterialSlotNames[id][self.MaterialIDs[i]] = []
                PrettyPrint(f"Saving material slot name {self.SectionsIDs[i]} for material {self.MaterialIDs[i]}")
                if self.SectionsIDs[i] not in Global_MaterialSlotNames[id][self.MaterialIDs[i]]:
                    Global_MaterialSlotNames[id][self.MaterialIDs[i]].append(self.SectionsIDs[i])

        # Unreversed Data
        if f.IsReading(): UnreversedData2Size = self.EndingOffset-f.tell()
        else: UnreversedData2Size = len(self.UnReversedData2)
        self.UnReversedData2    = f.bytes(self.UnReversedData2, UnreversedData2Size)
        if f.IsWriting(): self.EndingOffset = f.tell()
        self.EndingBytes        = f.uint64(self.NumMeshes)
        if redo_offsets:
            return self

        # Serialize Data
        self.SerializeGpuData(gpu, Global_TocManager)

        # TODO: update offsets only instead of re-writing entire file
        if f.IsWriting() and not redo_offsets:
            f.seek(0)
            self.Serialize(f, gpu, Global_TocManager, True)
        return self

    def SerializeGpuData(self, gpu: MemoryStream, Global_TocManager):
        PrettyPrint("SerializeGpuData")
        # Init Raw Meshes If Reading
        if gpu.IsReading():
            self.InitRawMeshes()
        # re-order the meshes to match the vertex order (this is mainly for writing)
        OrderedMeshes = self.CreateOrderedMeshList()
        # Create Vertex Components If Writing
        if gpu.IsWriting():
            self.SetupRawMeshComponents(OrderedMeshes)

        # Serialize Gpu Data
        for stream_idx in range(len(OrderedMeshes)):
            Stream_Info = self.StreamInfoArray[stream_idx]
            if gpu.IsReading():
                self.SerializeIndexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes, Global_TocManager)
                self.SerializeVertexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
            else:
                self.SerializeVertexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
                self.SerializeIndexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes, Global_TocManager)

    def SerializeIndexBuffer(self, gpu: MemoryStream, Stream_Info, stream_idx, OrderedMeshes, Global_TocManager):
        # get indices
        IndexOffset  = 0
        CompiledIncorrectly = False
        if gpu.IsWriting():Stream_Info.IndexBufferOffset = gpu.tell()
        for mesh in OrderedMeshes[stream_idx][1]:
            Mesh_Info = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
            # Lod Info
            if gpu.IsReading():
                mesh.LodIndex = Mesh_Info.LodIndex
                mesh.DEV_BoneInfoIndex = Mesh_Info.LodIndex
            # handle index formats
            IndexStride = 2
            IndexInt = gpu.uint16
            if Stream_Info.IndexBuffer_Type == 1:
                IndexStride = 4
                IndexInt = gpu.uint32

            TotalIndex = 0
            mat_count = {}
            for Section in Mesh_Info.Sections:
                # Create mat info
                if gpu.IsReading():
                    mat = RawMaterialClass()
                    if Section.ID in self.SectionsIDs:
                        mat_idx = self.SectionsIDs.index(Section.ID)
                        mat.MatID = str(self.MaterialIDs[mat_idx])
                        if mat.MatID not in mat_count:
                            mat_count[mat.MatID] = -1
                        mat_count[mat.MatID] += 1
                        mat.IDFromName(str(self.NameHash), str(self.MaterialIDs[mat_idx]), mat_count[mat.MatID])
                        mat.MatID = str(self.MaterialIDs[mat_idx])
                        #mat.ShortID = self.SectionsIDs[mat_idx]
                        if bpy.context.scene.Hd2ToolPanelSettings.ImportMaterials:
                            Global_TocManager.Load(mat.MatID, MaterialID, False, True)
                        else:
                            AddMaterialToBlend_EMPTY(mat.MatID)
                    else:
                        try   : bpy.data.materials[mat.MatID]
                        except: bpy.data.materials.new(mat.MatID)
                    mat.StartIndex = TotalIndex*3
                    mat.NumIndices = Section.NumIndices
                    mesh.Materials.append(mat)

                if gpu.IsReading(): gpu.seek(Stream_Info.IndexBufferOffset + (Section.IndexOffset*IndexStride))
                else:
                    Section.IndexOffset = IndexOffset
                    PrettyPrint(f"Updated Section Offset: {Section.IndexOffset}")
                for fidx in range(int(Section.NumIndices/3)):
                    indices = mesh.Indices[TotalIndex]
                    for i in range(3):
                        value = indices[i]
                        if not (0 <= value <= 0xffff) and IndexStride == 2:
                            PrettyPrint(f"Index: {value} TotalIndex: {TotalIndex}indecies out of bounds", "ERROR")
                            CompiledIncorrectly = True
                            value = min(max(0, value), 0xffff)
                        elif not (0 <= value <= 0xffffffff) and IndexStride == 4:
                            PrettyPrint(f"Index: {value} TotalIndex: {TotalIndex} indecies out of bounds", "ERROR")
                            CompiledIncorrectly = True
                            value = min(max(0, value), 0xffffffff)
                        indices[i] = IndexInt(value)
                    mesh.Indices[TotalIndex] = indices
                    TotalIndex += 1
                IndexOffset  += Section.NumIndices
        # update stream info
        if gpu.IsWriting():
            Stream_Info.IndexBufferSize    = gpu.tell() - Stream_Info.IndexBufferOffset
            Stream_Info.NumIndices         = IndexOffset

        # calculate correct vertex num (sometimes its wrong, no clue why, see 9102938b4b2aef9d->7040046837345593857)
        if gpu.IsReading():
            for mesh in OrderedMeshes[stream_idx][0]:
                RealNumVerts = 0
                for face in mesh.Indices:
                    for index in face:
                        if index > RealNumVerts:
                            RealNumVerts = index
                RealNumVerts += 1
                Mesh_Info = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
                if Mesh_Info.Sections[0].NumVertices != RealNumVerts:
                    for Section in Mesh_Info.Sections:
                        Section.NumVertices = RealNumVerts
                    self.ReInitRawMeshVerts(mesh)

    def SerializeVertexBuffer(self, gpu: MemoryStream, Stream_Info, stream_idx, OrderedMeshes):
        # Vertex Buffer
        VertexOffset = 0
        if gpu.IsWriting(): Stream_Info.VertexBufferOffset = gpu.tell()
        for mesh in OrderedMeshes[stream_idx][0]:
            Mesh_Info = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
            if gpu.IsWriting():
                for Section in Mesh_Info.Sections:
                    Section.VertexOffset = VertexOffset
                    Section.NumVertices  = len(mesh.VertexPositions)
                    PrettyPrint(f"Updated VertexOffset Offset: {Section.VertexOffset}")
            MainSection = Mesh_Info.Sections[0]
            # get vertices
            if gpu.IsReading(): gpu.seek(Stream_Info.VertexBufferOffset + (MainSection.VertexOffset*Stream_Info.VertexStride))
            
            for vidx in range(len(mesh.VertexPositions)):
                if gpu.IsReading():
                    pass
                vstart = gpu.tell()

                for Component in Stream_Info.Components:
                    serialize_func = FUNCTION_LUTS.SERIALIZE_MESH_LUT[Component.Type]
                    serialize_func(gpu, mesh, Component, vidx)

                gpu.seek(vstart + Stream_Info.VertexStride)
            VertexOffset += len(mesh.VertexPositions)
        # update stream info
        if gpu.IsWriting():
            gpu.seek(ceil(float(gpu.tell())/16)*16)
            Stream_Info.VertexBufferSize    = gpu.tell() - Stream_Info.VertexBufferOffset
            Stream_Info.NumVertices         = VertexOffset
            
    def CreateOrderedMeshList(self):
        # re-order the meshes to match the vertex order (this is mainly for writing)
        meshes_ordered_by_vert = [
            sorted(
                [mesh for mesh in self.RawMeshes if self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]].StreamIndex == index],
                key=lambda mesh: self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]].Sections[0].VertexOffset
            ) for index in range(len(self.StreamInfoArray))
        ]
        meshes_ordered_by_index = [
            sorted(
                [mesh for mesh in self.RawMeshes if self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]].StreamIndex == index],
                key=lambda mesh: self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]].Sections[0].IndexOffset
            ) for index in range(len(self.StreamInfoArray))
        ]
        OrderedMeshes = [list(a) for a in zip(meshes_ordered_by_vert, meshes_ordered_by_index)]

        # set 32 bit face indices if needed
        for stream_idx in range(len(OrderedMeshes)):
            Stream_Info = self.StreamInfoArray[stream_idx]
            for mesh in OrderedMeshes[stream_idx][0]:
                if mesh.DEV_Use32BitIndices:
                    Stream_Info.IndexBuffer_Type = 1
        return OrderedMeshes

    def InitRawMeshes(self):
        for n in range(len(self.MeshInfoArray)):
            NewMesh     = RawMeshClass()
            Mesh_Info   = self.MeshInfoArray[n]

            indexerror = Mesh_Info.StreamIndex >= len(self.StreamInfoArray)
            messageerror = "ERROR" if indexerror else "INFO"
            message = "Stream index out of bounds" if indexerror else ""
            PrettyPrint(f"Num: {len(self.StreamInfoArray)} Index: {Mesh_Info.StreamIndex}    {message}", messageerror)
            if indexerror: continue

            Stream_Info = self.StreamInfoArray[Mesh_Info.StreamIndex]
            NewMesh.MeshInfoIndex = n
            NewMesh.UnitID = Mesh_Info.UnitID
            NewMesh.DEV_Transform = self.TransformInfo.TransformMatrices[Mesh_Info.TransformIndex]
            try:
                NewMesh.DEV_BoneInfo  = self.BoneInfoArray[Mesh_Info.LodIndex]
            except: pass
            numUVs          = 0
            numBoneIndices  = 0
            for component in Stream_Info.Components:
                if component.TypeName() == "uv":
                    numUVs += 1
                if component.TypeName() == "bone_index":
                    numBoneIndices += 1
            NewMesh.InitBlank(Mesh_Info.GetNumVertices(), Mesh_Info.GetNumIndices(), numUVs, numBoneIndices)
            self.RawMeshes.append(NewMesh)
    
    def ReInitRawMeshVerts(self, mesh):
        # for mesh in self.RawMeshes:
        Mesh_Info = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
        mesh.ReInitVerts(Mesh_Info.GetNumVertices())

    def SetupRawMeshComponents(self, OrderedMeshes):
        for stream_idx in range(len(OrderedMeshes)):
            Stream_Info = self.StreamInfoArray[stream_idx]

            HasPositions = False
            HasNormals   = False
            HasTangents  = False
            HasBiTangents= False
            IsSkinned    = False
            NumUVs       = 0
            NumBoneIndices = 0
            # get total number of components
            for mesh in OrderedMeshes[stream_idx][0]:
                if len(mesh.VertexPositions)  > 0: HasPositions  = True
                if len(mesh.VertexNormals)    > 0: HasNormals    = True
                if len(mesh.VertexTangents)   > 0: HasTangents   = True
                if len(mesh.VertexBiTangents) > 0: HasBiTangents = True
                if len(mesh.VertexBoneIndices)> 0: IsSkinned     = True
                if len(mesh.VertexUVs)   > NumUVs: NumUVs = len(mesh.VertexUVs)
                if len(mesh.VertexBoneIndices) > NumBoneIndices: NumBoneIndices = len(mesh.VertexBoneIndices)
            if bpy.context.scene.Hd2ToolPanelSettings.Force2UVs:
                NumUVs = max(3, NumUVs)
            if IsSkinned and NumBoneIndices > 1 and bpy.context.scene.Hd2ToolPanelSettings.Force1Group:
                NumBoneIndices = 1

            for mesh in OrderedMeshes[stream_idx][0]: # fill default values for meshes which are missing some components
                if not len(mesh.VertexPositions)  > 0:
                    raise Exception("bruh... your mesh doesn't have any vertices")
                if HasNormals and not len(mesh.VertexNormals)    > 0:
                    mesh.VertexNormals = [[0,0,0] for n in mesh.VertexPositions]
                if HasTangents and not len(mesh.VertexTangents)   > 0:
                    mesh.VertexTangents = [[0,0,0] for n in mesh.VertexPositions]
                if HasBiTangents and not len(mesh.VertexBiTangents) > 0:
                    mesh.VertexBiTangents = [[0,0,0] for n in mesh.VertexPositions]
                if IsSkinned and not len(mesh.VertexWeights) > 0:
                    mesh.VertexWeights      = [[0,0,0,0] for n in mesh.VertexPositions]
                    mesh.VertexBoneIndices  = [[[0,0,0,0] for n in mesh.VertexPositions]*NumBoneIndices]
                if IsSkinned and len(mesh.VertexBoneIndices) > NumBoneIndices:
                    mesh.VertexBoneIndices = mesh.VertexBoneIndices[::NumBoneIndices]
                if NumUVs > len(mesh.VertexUVs):
                    dif = NumUVs - len(mesh.VertexUVs)
                    for n in range(dif):
                        mesh.VertexUVs.append([[0,0] for n in mesh.VertexPositions])
            # make stream components
            Stream_Info.Components = []
            if HasPositions:  Stream_Info.Components.append(StreamComponentInfo("position", "vec3_float"))
            if HasNormals:    Stream_Info.Components.append(StreamComponentInfo("normal", "unk_normal"))
            for n in range(NumUVs):
                UVComponent = StreamComponentInfo("uv", "vec2_half")
                UVComponent.Index = n
                Stream_Info.Components.append(UVComponent)
            if IsSkinned:     Stream_Info.Components.append(StreamComponentInfo("bone_weight", "vec4_half"))
            for n in range(NumBoneIndices):
                BIComponent = StreamComponentInfo("bone_index", "vec4_uint8")
                BIComponent.Index = n
                Stream_Info.Components.append(BIComponent)
            # calculate Stride
            Stream_Info.VertexStride = 0
            for Component in Stream_Info.Components:
                Stream_Info.VertexStride += Component.GetSize()

def LoadStingrayUnit(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject , LoadMaterialSlotNames=False):
    toc  = MemoryStream(TocData)
    gpu  = MemoryStream(GpuData)
    bones_entry = Global_TocManager.GetEntryByLoadArchive(int(ID), int(BoneID))
    if bones_entry and not bones_entry.IsLoaded:
        bones_entry.Load(False, False)
    StingrayMesh = StingrayMeshFile()
    StingrayMesh.NameHash = int(ID)
    StingrayMesh.LoadMaterialSlotNames = LoadMaterialSlotNames
    StingrayMesh.Serialize(toc, gpu, Global_TocManager)
    if MakeBlendObject: CreateModel(StingrayMesh, str(ID), Global_BoneNames)
    return StingrayMesh

def SaveStingrayMesh(self,ID, TocData, GpuData, StreamData, StingrayMesh):
    # model = GetObjectsMeshData(Global_TocManager, Global_BoneNames)
    # # print(f"模型：{model}")
    # # raise Exception("停止")
    # FinalMeshes = [mesh for mesh in StingrayMesh.RawMeshes]
    # for mesh in model:
    #     for n in range(len(StingrayMesh.RawMeshes)):
    #         if StingrayMesh.RawMeshes[n].MeshInfoIndex == mesh.MeshInfoIndex:
    #             FinalMeshes[n] = mesh
    if bpy.context.scene.Hd2ToolPanelSettings.AutoLods:
        lod0 = None
        for mesh in StingrayMesh.RawMeshes:
            if mesh.LodIndex == 0:
                lod0 = mesh
                break
        # print(lod0)
        if lod0 != None:
            for n in range(len(StingrayMesh.RawMeshes)):
                if StingrayMesh.RawMeshes[n].IsLod():
                    newmesh = copy.copy(lod0)
                    newmesh.MeshInfoIndex = StingrayMesh.RawMeshes[n].MeshInfoIndex
                    StingrayMesh.RawMeshes[n] = newmesh
    # StingrayMesh.RawMeshes = FinalMeshes
    toc  = MemoryStream(IOMode = "write")
    gpu  = MemoryStream(IOMode = "write")
    StingrayMesh.Serialize(toc, gpu, Global_TocManager)
    return [toc.Data, gpu.Data, b""]

#endregion

#region Operators: Panel Settings
class ButtonOpenCacheDirectory(Operator):
    bl_idname ="helldiver2.open_cache_directory"
    bl_label = "Open Cache Directory"
    bl_description = "打开缓存目录"
    
    def execute(self, context):
        tempdir = tempfile.gettempdir()
        os.startfile(tempdir)
    
        return {"FINISHED"}
    
    
class ButtonOpenPatchOutDirectory(Operator):
    bl_idname ="helldiver2.open_patch_out_directory"
    bl_label = "Open Patch Out Directory"
    bl_description = "打开输出目录"
    
    @classmethod
    def poll(cls, context):
        return os.path.exists(Global_PatchBasePath)
    
    
    def execute(self, context):
        tempdir = tempfile.gettempdir()
        if os.path.dirname(Global_PatchBasePath) != tempdir:
            os.startfile(os.path.dirname(Global_PatchBasePath))

        
        return {"FINISHED"}

class ButtonAutoRenamePatch(Operator):
    bl_idname ="helldiver2.button_auto_rename_patch"
    bl_label = "auto_rename_patch"
    bl_description = "将patch重命名为基础资产的patch"
    
    NewRenamePatchIndex : IntProperty(name="序号", default=0)
    def draw(self, context):
        layout = self.layout; row = layout.row()
        row.label(text="Patch末尾序号:")
        row.prop(self, "NewRenamePatchIndex", icon='COPY_ID')
    
    def execute(self, context):
        bpy.context.scene.Hd2ToolPanelSettings.NewPatchName = "9ba626afa44a3aa3.patch_" + str(self.NewRenamePatchIndex)
        
            # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return {"FINISHED"}
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class ButtonUpdateArchivelistCN(Operator):
    bl_label = "更新已知资产列表"
    bl_idname = "helldiver2.update_archivelist_cn"
    bl_description = "从中文共享ID收集表更新已知资产列表"
    
    def execute(self, context):
        if get_update_archivelistCN.GetAndUpdateArchivelistCN():
            LoadUpdateArchiveList_CN()
            self.report({'INFO'}, "更新完成")
        else:
            with open(get_update_archivelistCN.Global_ErrorLog, 'r', encoding='utf-8') as f:
                self.report({'ERROR'}, f"更新失败，存在错误: {f.read()}. 错误日志见:{get_update_archivelistCN.Global_ErrorLog}")
        return {"FINISHED"}
#endregion

#region Operators: Archives & Patches
def ArchivesNotLoaded(self):
    if len(Global_TocManager.LoadedArchives) <= 0:
        self.report({'ERROR'}, "No Archives Currently Loaded")
        return True
    else: 
        return False
    
def PatchesNotLoaded(self):
    if len(Global_TocManager.Patches) <= 0:
        self.report({'ERROR'}, "No Patches Currently Loaded")
        return True
    else:
        return False

def hex_to_decimal(hex_string):
    try:
        decimal_value = int(hex_string, 16)
        return decimal_value
    except ValueError:
        PrettyPrint(f"Invalid hexadecimal string: {hex_string}")

class DefaultLoadArchiveOperator(Operator):
    bl_label = "Default Archive"
    bl_description = "载入默认基础资产"
    bl_idname = "helldiver2.archive_import_default"

    def execute(self, context):
        path = Global_gamepath + "9ba626afa44a3aa3"
        if not os.path.exists(path):
            self.report({'ERROR'}, "Current Filepath is Invalid. Change this in the Settings")
            context.scene.Hd2ToolPanelSettings.MenuExpanded = True
            return{'CANCELLED'}
        Global_TocManager.LoadArchive(path, True, False)

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}

class LoadArchiveOperator(Operator, ImportHelper):
    bl_label = "Load Archive"
    bl_idname = "helldiver2.archive_import"
    
    filter_glob: StringProperty(default='*', options={'HIDDEN'})

    is_patch: BoolProperty(name="is_patch", default=False, options={'HIDDEN'})
    
    filepath: StringProperty(name="File Path", subtype='FILE_PATH', default="")
    
    def execute(self, context):
        # Sanitize path by removing any provided extension, so the correct TOC file is loaded
        if not self.filepath:
            self.report({'ERROR'}, "文件路径不能为空。")
            return {'CANCELLED'}
            
        path = Path(self.filepath)
        if not path.suffix.startswith(".patch_"): path = path.with_suffix("")

        Global_TocManager.LoadArchive(str(path), True, self.is_patch)

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
            
        self.filepath = ""
        return{'FINISHED'}
        
    def invoke(self, context, event):
        wm = context.window_manager

        if self.filepath:
            return {'FINISHED'}
        else:
            self.filepath = bpy.path.abspath(Global_gamepath)
            wm.fileselect_add(self)
            return {'RUNNING_MODAL'} 

class UnloadArchivesOperator(Operator):
    bl_label = "Unload Archives"
    bl_idname = "helldiver2.archive_unloadall"

    def execute(self, context):
        Global_TocManager.UnloadArchives()
        return{'FINISHED'}

class UnloadPatchesOperator(Operator):
    bl_label = "Unload Patches"
    bl_idname = "helldiver2.patches_unloadall"
    bl_description = "Unloads All Current Loaded Patches"

    def execute(self, context):
        Global_TocManager.UnloadPatches()
        return{'FINISHED'}

class CreatePatchFromActiveOperator(Operator):
    bl_label = "Create Patch"
    bl_idname = "helldiver2.archive_createpatch"

    NewPatchIndex : IntProperty(name="新Patch序号", default=0)
    def draw(self, context):
        layout = self.layout; row = layout.row()
        row.prop(self, "NewPatchIndex", icon='COPY_ID')
        # print("NewPatchIndex:", self.NewPatchIndex)
    
    def execute(self, context):
        Global_TocManager.CreatePatchFromActive(NewPatchIndex = self.NewPatchIndex)

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        return{'FINISHED'}
        
    def invoke(self, context, event):
        wm = context.window_manager
        if self.NewPatchIndex == 0:
            return wm.invoke_props_dialog(self)
        else:
            return {'FINISHED'}
    
    def execute(self, context):
        Global_TocManager.CreatePatchFromActive(NewPatchIndex = self.NewPatchIndex)

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class PatchArchiveOperator(Operator):
    bl_label = "Patch Archive"
    bl_idname = "helldiver2.archive_export"

    def execute(self, context):
        global Global_TocManager
        global Global_PatchBasePath
        
        if bpy.context.scene.Hd2ToolPanelSettings.IsChangeOutPath and bpy.context.scene.Hd2ToolPanelSettings.NewPatchOutPath:
            if bpy.context.scene.Hd2ToolPanelSettings.IsRenamePatch and bpy.context.scene.Hd2ToolPanelSettings.NewPatchName:
                check_name = bpy.context.scene.Hd2ToolPanelSettings.NewPatchName
                if check_name.find(".patch_") == -1:
                    self.report({'ERROR'}, "文件名没有加上.patch_，自行检查")
                    return {'CANCELLED'}
                if check_name.find("9ba626afa44a3aa3.patch_") == -1:
                    self.report({'WARNING'}, "没有重命名为基础资产的patch")
                # New_path = Global_TocManager.RenameActivePatch(NewPath = bpy.context.scene.Hd2ToolPanelSettings.NewPatchName)
                New_path = os.path.join(bpy.context.scene.Hd2ToolPanelSettings.NewPatchOutPath, check_name)
                Global_TocManager.PatchActiveArchive(path= New_path)
            else:
                New_path = os.path.join(bpy.context.scene.Hd2ToolPanelSettings.NewPatchOutPath, Global_TocManager.ActivePatch.Name)
                Global_TocManager.PatchActiveArchive(path= New_path)
        else:
            if bpy.context.scene.Hd2ToolPanelSettings.IsRenamePatch and bpy.context.scene.Hd2ToolPanelSettings.NewPatchName:
                check_name = bpy.context.scene.Hd2ToolPanelSettings.NewPatchName
                if check_name.find(".patch_") == -1:
                    self.report({'ERROR'}, "文件名没有加上.patch_，自行检查")
                    return {'CANCELLED'}
                if check_name.find("9ba626afa44a3aa3.patch_") == -1:
                    self.report({'WARNING'}, "没有重命名为基础资产的patch")
                New_path = Global_TocManager.RenameActivePatch(NewPath = bpy.context.scene.Hd2ToolPanelSettings.NewPatchName)
                Global_TocManager.PatchActiveArchive(path= New_path)
            else:
                Global_TocManager.PatchActiveArchive()

        self.report({'INFO'}, f"写入patch完成,文件保存在{Global_PatchBasePath}")
        bpy.context.scene.Hd2ToolPanelSettings.IsZipPatch = False
        return{'FINISHED'}
    
class ZipPatchArchiveOperator(Operator,ExportHelper):
    bl_label = "Zip Patch Export"
    bl_idname = "helldiver2.archive_zippatch_export"
    bl_description = "将patch导出为zip文件"
    
    filename_ext = ".zip"
    
    filter_glob: StringProperty(
        default="*.zip",
        options={"HIDDEN"},

    )
    filepath: StringProperty(
        default="patch.zip",
        subtype="FILE_PATH",
    )
    
    
    @classmethod
    def poll(cls, context):
        return Global_TocManager.ActivePatch != None
    
    
    def execute(self, context):
        tempdir = tempfile.gettempdir()
        global Global_TocManager
        global Global_PatchBasePath
        

        if bpy.context.scene.Hd2ToolPanelSettings.IsRenamePatch and bpy.context.scene.Hd2ToolPanelSettings.NewPatchName:
            check_name = bpy.context.scene.Hd2ToolPanelSettings.NewPatchName
            if check_name.find(".patch_") == -1:
                self.report({'ERROR'}, "文件名没有加上.patch_，自行检查")
                return {'CANCELLED'}
            if check_name.find("9ba626afa44a3aa3.patch_") == -1:
                self.report({'WARNING'}, "没有重命名为基础资产的patch")
            # New_path = Global_TocManager.RenameActivePatch(NewPath = bpy.context.scene.Hd2ToolPanelSettings.NewPatchName)
            New_path = os.path.join(tempdir, check_name)
            Global_TocManager.PatchActiveArchive(path= New_path)
        else:
            New_path = os.path.join(tempdir, Global_TocManager.ActivePatch.Name)
            Global_TocManager.PatchActiveArchive(path= New_path)

        # 打包文件
        zipfileOutPath = self.filepath
        # if 
        with zipfile.ZipFile(zipfileOutPath, 'w',zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(New_path , arcname= os.path.basename(New_path))
            zipf.write(New_path + ".gpu_resources",arcname= os.path.basename(New_path) + ".gpu_resources")
            zipf.write(New_path + ".stream",arcname= os.path.basename(New_path) + ".stream")

        bpy.context.scene.Hd2ToolPanelSettings.IsZipPatch = True
        self.report({'INFO'}, f"patch打包完成,文件保存在{self.filepath}")
        return {'FINISHED'}
    def invoke(self, context, event):
        # self.filepath = ""
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

class ChangeFilepathOperator(Operator, ImportHelper):
    bl_label = "Change Filepath"
    bl_idname = "helldiver2.change_filepath"
    bl_description = "更改游戏data目录文件夹路径"
    #filename_ext = "."
    use_filter_folder = True

    filter_glob: StringProperty(options={'HIDDEN'}, default='')

    def __init__(self):
        global Global_gamepath
        self.filepath = bpy.path.abspath(Global_gamepath)
        
    def execute(self, context):
        global Global_gamepath
        filepath = self.filepath
        steamapps = "steamapps"
        if steamapps in filepath:
            filepath = f"{filepath.partition(steamapps)[0]}steamapps\common\Helldivers 2\data\ "[:-1]
        else:
            self.report({'ERROR'}, f"无法在此目录下找到steamapps文件夹: {filepath}")
            return{'CANCELLED'}
        Global_gamepath = filepath
        UpdateConfig()
        PrettyPrint(f"Changed Game File Path: {Global_gamepath}")
        return{'FINISHED'}
    
class AddSwapsID_property(Operator):
    bl_label =  "Add_Swaps_ID"
    bl_idname = "helldiver2.add_swaps_id_prop"
    bl_description = "一键添加转移自定义ID属性(可多选物体), 只有先前存在HD2自定义属性的物体才会被添加"
    
    
    SwapsID_amount : IntProperty(
        name="需要添加的转移ID数量",
        description="需要添加的转移ID数量，不推荐过多添加",
        default=1,
        min=1,
        max=200,
    )
    
    def draw(self, context):
        layout = self.layout; row = layout.row()
        row.prop(self, "SwapsID_amount", icon='COPY_ID')
    
    @classmethod
    def poll(cls, context):
        active_obj = context.active_object
        if active_obj:
            return active_obj.type == "MESH"
        return False

    def execute(self, context):
        active_obj = context.active_object
        if active_obj == None: 
            self.report({'ERROR'}, "请至少选择一个物体")
            return{'CANCELLED'}
        select_objs = context.selected_objects
        add_count = 0
        
        for obj in select_objs:
            has_swap_id = False
            ori_swap = ""
            if obj.type != "MESH":continue
            try:ObjectID = obj["Z_ObjectID"]
            except:continue
            
            SwapID_keys_id = [int(key.split("_")[-1]) for key in obj.keys() if key.startswith("Z_SwapID_")]
            
            
            
            try:
                obj["Z_SwapID"]
            except:
                pass
            else:
                if obj["Z_SwapID"] != "":
                    has_swap_id = True
                    ori_swap = obj["Z_SwapID"]
                    
                    del obj["Z_SwapID"]
                else:
                    del obj["Z_SwapID"]
                    obj["Z_SwapID_0"] = ""
            
            if ObjectID  !=  None:
                if len(SwapID_keys_id) != 0:
                    SwapID_keys_id.sort()
                    new_id = SwapID_keys_id[-1] + 1
                    for i in range(self.SwapsID_amount):
                        obj[f"Z_SwapID_{new_id + i}"] = ""
                else:
                    try:
                        obj["Z_SwapID_0"]
                    except:
                        for i in range(self.SwapsID_amount):
                            obj[f"Z_SwapID_{i}"] = ""
                    else:
                        for i in range(self.SwapsID_amount):
                            obj[f"Z_SwapID_{i + 1}"] = ""
                if has_swap_id:
                    obj["Z_SwapID_0"] = ori_swap
                
                add_count += 1
                
        self.report({'INFO'}, f"总共为选择的物体添加{add_count * self.SwapsID_amount}个空交换ID属性")        
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    
    
    

    
#endregion

#region Operators: Entries

class ArchiveEntryOperator(Operator):
    bl_label  = "Archive Entry"
    bl_idname = "helldiver2.archive_entry"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        return{'FINISHED'}

    def invoke(self, context, event):
        Entry = Global_TocManager.GetEntry(int(self.object_id), int(self.object_typeid))
        if event.ctrl:
            if Entry.IsSelected:
                Global_TocManager.DeselectEntries([Entry])
            else:
                Global_TocManager.SelectEntries([Entry], True)
            return {'FINISHED'}
        if event.shift:
            if Global_TocManager.LastSelected != None:
                LastSelected = Global_TocManager.LastSelected
                StartIndex   = LastSelected.DEV_DrawIndex
                EndIndex     = Entry.DEV_DrawIndex
                Global_TocManager.DeselectAll()
                Global_TocManager.LastSelected = LastSelected
                if StartIndex > EndIndex:
                    Global_TocManager.SelectEntries(Global_TocManager.DrawChain[EndIndex:StartIndex+1], True)
                else:
                    Global_TocManager.SelectEntries(Global_TocManager.DrawChain[StartIndex:EndIndex+1], True)
            else:
                Global_TocManager.SelectEntries([Entry], True)
            return {'FINISHED'}

        Global_TocManager.SelectEntries([Entry])
        return {'FINISHED'}
    
class MaterialShaderVariableEntryOperator(Operator):
    bl_label = "Shader Variable"
    bl_idname = "helldiver2.material_shader_variable"
    bl_description = "Material Shader Variable"

    object_id: StringProperty()
    variable_index: bpy.props.IntProperty()
    value_index: bpy.props.IntProperty()
    value: bpy.props.FloatProperty(
        name="Variable Value",
        description="Enter a floating point number"
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "value")

    def execute(self, context):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            Entry.LoadedData.ShaderVariables[self.variable_index].values[self.value_index] = self.value
            PrettyPrint(f"Set value to: {self.value} at variable: {self.variable_index} value: {self.value_index} for material ID: {self.object_id}")
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class MaterialShaderVariableColorEntryOperator(Operator):
    bl_label = "Color Picker"
    bl_idname = "helldiver2.material_shader_variable_color"
    bl_description = "Material Shader Variable Color"

    object_id: StringProperty()
    variable_index: bpy.props.IntProperty()
    color: bpy.props.FloatVectorProperty(
                name=f"Color",
                subtype="COLOR",
                size=3,
                min=0.0,
                max=1.0,
                default=(1.0, 1.0, 1.0)
            )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "color")

    def execute(self, context):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            for idx in range(3):
                Entry.LoadedData.ShaderVariables[self.variable_index].values[idx] = self.color[idx]
            PrettyPrint(f"Set color to: {self.color}for material ID: {self.object_id}")
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return {'FINISHED'}
    
    def invoke(self, context, event):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            for idx in range(3):
                self.color[idx] = Entry.LoadedData.ShaderVariables[self.variable_index].values[idx]
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)

class AddEntryToPatchOperator(Operator):
    bl_label = "Add Entry To Patch"
    bl_idname = "helldiver2.archive_addtopatch"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            Global_TocManager.AddEntryToPatch(Entry.FileID, Entry.TypeID)
        return{'FINISHED'}

class RemoveEntryFromPatchOperator(Operator):
    bl_label = "Remove Entry From Patch"
    bl_idname = "helldiver2.archive_removefrompatch"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            Global_TocManager.RemoveEntryFromPatch(Entry.FileID, Entry.TypeID)
        return{'FINISHED'}

class UndoArchiveEntryModOperator(Operator):
    bl_label = "Remove Modifications"
    bl_idname = "helldiver2.archive_undo_mod"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            if Entry != None:
                Entry.UndoModifiedData()
        return{'FINISHED'}

class DuplicateEntryOperator(Operator):
    bl_label = "Duplicate Entry"
    bl_idname = "helldiver2.archive_duplicate"

    NewFileID : StringProperty(name="NewFileID", default="")
    def draw(self, context):
        layout = self.layout; row = layout.row()
        row.prop(self, "NewFileID", icon='COPY_ID')

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Global_TocManager.DuplicateEntry(int(self.object_id), int(self.object_typeid), int(self.NewFileID))
        return{'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class RenamePatchEntryOperator(Operator):
    bl_label = "Rename Entry"
    bl_idname = "helldiver2.archive_entryrename"

    NewFileID : StringProperty(name="NewFileID", default="")
    def draw(self, context):
        layout = self.layout; row = layout.row()
        row.prop(self, "NewFileID", icon='COPY_ID')

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entry = Global_TocManager.GetPatchEntry_B(int(self.object_id), int(self.object_typeid))
        if Entry == None:
            raise Exception("Entry does not exist in patch (cannot rename non patch entries)")
        if Entry != None and self.NewFileID != "":
            Entry.FileID = int(self.NewFileID)
        return{'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class DumpArchiveObjectOperator(Operator):
    bl_label = "Dump Archive Object"
    bl_idname = "helldiver2.archive_object_dump_export"

    directory: StringProperty(name="Outdir Path",description="dump output dir")
    filter_folder: BoolProperty(default=True,options={"HIDDEN"})

    object_id: StringProperty(options={"HIDDEN"})
    object_typeid: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            if Entry != None:
                data = Entry.GetData()
                FileName = str(Entry.FileID)+"."+GetTypeNameFromID(Entry.TypeID)
                with open(self.directory + FileName, 'w+b') as f:
                    f.write(data[0])
                if data[1] != b"":
                    with open(self.directory + FileName+".gpu", 'w+b') as f:
                        f.write(data[1])
                if data[2] != b"":
                    with open(self.directory + FileName+".stream", 'w+b') as f:
                        f.write(data[2])
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ImportDumpOperator(Operator, ImportHelper):
    bl_label = "Import Dump"
    bl_idname = "helldiver2.archive_object_dump_import"

    object_id: StringProperty(options={"HIDDEN"})
    object_typeid: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        if Global_TocManager.ActivePatch == None:
            raise Exception("No patch exists, please create one first")

        FileID = int(self.object_id.split(',')[0])
        Entry = Global_TocManager.GetEntry(FileID, MaterialID)
        if Entry != None:
            if not Entry.IsLoaded: Entry.Load(False, False)
            path = self.filepath
            with open(path, 'r+b') as f:
                Entry.TocData = f.read()
            if os.path.isfile(f"{path}.gpu_resources"):
                with open(f"{path}.gpu_resources", 'r+b') as f:
                    Entry.GpuData = f.read()
            else:
                Entry.GpuData = b""
            if os.path.isfile(f"{path}.stream"):
                with open(f"{path}.stream", 'r+b') as f:
                    Entry.StreamData = f.read()
            else:
                Entry.StreamData = b""
            Entry.IsModified = True
            Global_TocManager.AddEntryToPatch(Entry.FileID, Entry.TypeID)
        return{'FINISHED'}

#endregion

#region Operators: Meshes

class ImportStingrayMeshOperator(Operator):
    bl_label = "Import Archive Mesh"
    bl_idname = "helldiver2.archive_mesh_import"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        Errors = []
        for EntryID in EntriesIDs:
            if len(EntriesIDs) == 1:
                Global_TocManager.Load(EntryID, UnitID)
            else:
                try:
                    Global_TocManager.Load(EntryID, UnitID)
                except Exception as error:
                    Errors.append([EntryID, error])

        if len(Errors) > 0:
            PrettyPrint("\nThese errors occurred while attempting to load meshes...", "error")
            idx = 0
            for error in Errors:
                PrettyPrint(f"  Error {idx}: for mesh {error[0]}", "error")
                PrettyPrint(f"    {error[1]}\n", "error")
                idx += 1
            raise Exception("One or more meshes failed to load")
        return{'FINISHED'}

class SaveStingrayMeshOperator(Operator):
    bl_label  = "Save Mesh"
    bl_idname = "helldiver2.archive_mesh_save"
    bl_options = {'REGISTER', 'UNDO'} 
    bl_description = "保存网格，必须选择一个网格物体"
    
    @classmethod
    def poll(cls, context):
        object = context.active_object
        return object is not None and object.type == "MESH"

    object_id: StringProperty()
    def execute(self, context):
        global Global_BoneNames
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        object = bpy.context.active_object
        # 检查Patch
        has_patch =  Global_TocManager.CheckActivePatch()
        if not has_patch:
            self.report({'ERROR'}, f"没有激活的Patch，无法保存，请先创建一个Patch。")
            return{'CANCELLED'}
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, f"不在物体模式下，当前模式: {context.mode}，保存取消")
            return {'CANCELLED'}
        if addon_prefs.SaveUseAutoSmooth:
            # 4.3 compatibility change
            if bpy.app.version[0] >= 4 and bpy.app.version[1] >= 1:
                bpy.ops.object.shade_auto_smooth(angle=3.14159)
                
            else:
                bpy.ops.object.use_auto_smooth = True
                bpy.context.object.data.auto_smooth_angle = 3.14159
        if object == None:
            self.report({"ERROR"}, "没有物体被选中，必须先选择一个物体再点击保存")
            return {'CANCELLED'}
        
        
        try:
            ID = object["Z_ObjectID"]
        except:
            self.report({'ERROR'}, f"{object.name} 没有HD2自定义属性")
            return{'CANCELLED'}
        # 材质名称检查与修正
        for idx in range(len(object.material_slots)):
            CheckValidMaterial(object,idx)
        
        # SwapID = ""
        SwapID_list = []
        try:
            object["Z_SwapID"]
        except:
            pass
        else:
            if object["Z_SwapID"] != "":
                object["Z_SwapID_0"] = object["Z_SwapID"]
                del object["Z_SwapID"]
        
        SwapID_keys = [key for key in object.keys() if key.startswith("Z_SwapID_")]
        
        if SwapID_keys:
            for key in SwapID_keys:
                if object[key] != "" :
                    if object[key].isnumeric():
                        SwapID_list.append(object[key])
                    else:
                        self.report({"ERROR"}, f"Object: {object.name} 的转换ID: {object[key]} 不是纯数字.")
                        return {'CANCELLED'}
                    
        model = GetObjectsMeshData(Global_TocManager, Global_BoneNames)
        Entry = Global_TocManager.GetEntryByLoadArchive(int(ID), UnitID)
        if Entry is None:
            self.report({'ERROR'},
                f"存档中需要保存的条目没有载入. 找不到物体ID: {ID}")
            return{'CANCELLED'}
        if not Entry.IsLoaded: Entry.Load(True, False)
        meshes = model[ID]
        for mesh_index, mesh in meshes.items():
            try:
                if Entry.LoadedData.RawMeshes[mesh_index].DEV_BoneInfoIndex == -1 and mesh.DEV_BoneInfoIndex > -1:
                    self.report({'ERROR'},
                                f"尝试用有权重网格覆盖静态网格。请检查网格是否正确。")
                    return{'CANCELLED'}
                Entry.LoadedData.RawMeshes[mesh_index] = mesh
            except IndexError:
                excpectedLength = len(Entry.LoadedData.RawMeshes) - 1
                self.report({'ERROR'}, f"MeshInfoIndex of {mesh_index} for {object.name} 超过了网格数量。预期最大 MeshInfoIndex 为: {excpectedLength}。请检查自定义属性是否匹配此值并重新保存网格。")
                return{'CANCELLED'}

            
        
        
        # 转换ID检查与修正
        if SwapID_list:
            if ID in SwapID_list:
                if SwapID_list.count(ID) > 1:
                    self.report({"ERROR"}, f"Object: {object.name} 的转换ID栏最多只能填一次自身ID.")
                    return {'CANCELLED'}

                SwapID_list.remove(ID)
                #将其放到末尾
                SwapID_list.append(ID)

            wasSaved = Entry.Save()
            
            if not wasSaved:
                self.report({"ERROR"}, f"保存失败 unit {bpy.context.selected_objects[0].name}.")
                return{'CANCELLED'}
            
            for SwapID in SwapID_list:

                if not Global_TocManager.IsInPatch(Entry):
                    Global_TocManager.AddEntryToPatch(int(ID), UnitID)
                        # bpy.ops.helldiver2.archive_addtopatch(object_id = str(ID),object_typeid = str(UnitID))

                Entry_In_patch = Global_TocManager.GetPatchEntry(Entry)
                if SwapID != ID:
                    self.report({'INFO'}, f"转移 Entry ID: {Entry.FileID} to: {SwapID}")
                    Global_TocManager.RemoveEntryFromPatch(int(SwapID), UnitID)
                    Entry_In_patch.FileID = int(SwapID)
                else:
                    self.report({'INFO'}, f"Entry ID: {Entry.FileID} 保持自身")

                
        
        else:
            # Global_TocManager.Save(int(self.object_id), UnitID)
            wasSaved = Entry.Save()
            if wasSaved:
                if not Global_TocManager.IsInPatch(Entry):
                    Entry = Global_TocManager.AddEntryToPatch(int(ID), UnitID)
            else:
                self.report({"ERROR"}, f"保存失败 unit {bpy.context.selected_objects[0].name}.")
                return{'CANCELLED'}
            self.report({'INFO'}, f"已保存 Unit Object ID: {self.object_id}")

        
        return{'FINISHED'}

class BatchSaveStingrayMeshOperator(Operator):
    bl_label  = "Save Meshes"
    bl_idname = "helldiver2.archive_mesh_batchsave"
    bl_description = "批量保存选中的网格"

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0


    def execute(self, context):
        start = time.time()
        errors = False
        objects = bpy.context.selected_objects
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        
        # 检查Patch
        has_patch =  Global_TocManager.CheckActivePatch()
        if not has_patch:
            self.report({'ERROR'}, f"没有激活的Patch，无法保存，请先创建一个Patch。")
            return{'CANCELLED'}
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, f"不在物体模式下，当前模式: {context.mode}，保存取消")
            return {'CANCELLED'}
        
        mesh_obj = []
        for i in objects:
            if i.type == "MESH":
                mesh_obj.append(i)
        num_initially_selected = len(mesh_obj)
        num_meshes = num_initially_selected
        
        if addon_prefs.SaveUseAutoSmooth:
            for i in objects:
                if i.type == "MESH":
                    # 4.3 compatibility change
                    if bpy.app.version[0] >= 4 and bpy.app.version[1] >= 1:
                        i.data.shade_auto_smooth(use_auto_smooth=True)
                    else:
                        i.data.use_auto_smooth = True
                        i.data.auto_smooth_angle = 3.14159
        # bpy.ops.object.select_all(action='DESELECT')
        
        IDs = []
        for object in objects:
            try:
                object["Z_SwapID"]
            except:
                pass
            else:
                if object["Z_SwapID"] != "":
                    object["Z_SwapID_0"] = object["Z_SwapID"]
            SwapID_list = []
            SwapID_keys = [key for key in object.keys() if key.startswith("Z_SwapID_")]
            try:
                ID = object["Z_ObjectID"]
                
                # 材质名称检查与修正
                for idx in range(len(object.material_slots)):
                    CheckValidMaterial(object,idx)
                
                if SwapID_keys:
                    for key in SwapID_keys:
                        if object[key] != "" :
                            if object[key].isnumeric():
                                SwapID_list.append(object[key])
                            else:
                                self.report({"ERROR"}, f"Object: {object.name} 的转换ID: {object[key]} 不是纯数字.")
                                return {'CANCELLED'}
                

                IDitem = [ID, SwapID_list]
                if IDitem not in IDs:
                    IDs.append(IDitem)
                    
            except:
                pass


        entries = []
        for IDitem in IDs:
            ID = IDitem[0]
            # SwapID_list = IDitem[1]
            Entry = Global_TocManager.GetEntryByLoadArchive(int(ID), UnitID)
            if Entry is None:
                self.report({'ERROR'}, f"保存的网格对应的档案未加载。无法找到 ID: {ID} 的自定义属性对象。")
                errors = True
                num_meshes -= len(MeshData[ID])
                entries.append(None)
                continue
            if not Entry.IsLoaded: Entry.Load(True, False, True)
            entries.append(Entry)

        MeshData = GetObjectsMeshData(Global_TocManager, Global_BoneNames)    
        for i, IDitem in enumerate(IDs):
            ID = IDitem[0]
            SwapID_list = IDitem[1]
            Entry = entries[i]
            if Entry is None:
                continue
            
            MeshList = MeshData[ID]
            
            if SwapID_list:
                # 预先检查是否有自身ID,有就放到末尾
                if ID in SwapID_list:
                    if SwapID_list.count(ID) > 1:
                        self.report({"ERROR"}, f"Object ID 为 {ID} 的转换ID栏最多只能填一次自身ID.")
                        return {'CANCELLED'}

                    SwapID_list.remove(ID)
                    #将其放到末尾
                    SwapID_list.append(ID)
                
                for mesh_index, mesh in MeshList.items():
                    try:
                        if Entry.LoadedData.RawMeshes[mesh_index].DEV_BoneInfoIndex == -1 and mesh.DEV_BoneInfoIndex > -1:
                            self.report({'ERROR'},
                                        f"尝试用有权重网格覆盖静态网格，请检查网格是否正确。")
                            return{'CANCELLED'}
                        Entry.LoadedData.RawMeshes[mesh_index] = mesh
                    except IndexError:
                        excpectedLength = len(Entry.LoadedData.RawMeshes) - 1
                        self.report({'ERROR'},f"MeshInfoIndex of {mesh_index} 超过了网格数量。预期最大 MeshInfoIndex 为: {excpectedLength}。请检查自定义属性是否匹配此值并重新保存网格。")
                        errors = True
                        num_meshes -= 1
    
                wasSaved = Entry.Save()
                if not wasSaved:
                    self.report({"ERROR"}, f"Object ID 为 {ID} 的物体保存失败 ")
                    num_meshes -= len(MeshData[ID])
                    # return{'CANCELLED'}
                
                for SwapID in SwapID_list:
                    
                    if not Global_TocManager.IsInPatch(Entry):
                        Global_TocManager.AddEntryToPatch(int(ID), UnitID)
                        print(f"Add Entry ID: {Entry.FileID} to Patch")

                    Entry_In_patch = Global_TocManager.GetPatchEntry_B(int(ID), UnitID)
                    
                    if SwapID != ID:
                        self.report({'INFO'}, f"转移 Entry ID: {Entry_In_patch.FileID} to: {SwapID}")
                        
                        Global_TocManager.RemoveEntryFromPatch(int(SwapID), UnitID)
                        Entry_In_patch.FileID = int(SwapID)
                        # print(f"is in patch: {Global_TocManager.IsInPatch(Entry)}")
                    else:
                        self.report({'INFO'}, f"Entry ID: {Entry.FileID} 保持自身")
                        
            
            else:
                for mesh_index, mesh in MeshList.items():
                    try:
                        if Entry.LoadedData.RawMeshes[mesh_index].DEV_BoneInfoIndex == -1 and mesh.DEV_BoneInfoIndex > -1:
                            self.report({'ERROR'},
                                        f"尝试用有权重网格覆盖静态网格，请检查网格是否正确。")
                            return{'CANCELLED'}
                        Entry.LoadedData.RawMeshes[mesh_index] = mesh
                    except IndexError:
                        excpectedLength = len(Entry.LoadedData.RawMeshes) - 1
                        self.report({'ERROR'},f"MeshInfoIndex of {mesh_index} 超过了网格数量。预期最大 MeshInfoIndex 为: {excpectedLength}。请检查自定义属性是否匹配此值并重新保存网格。")
                        errors = True
                        num_meshes -= 1
                        
                wasSaved = Entry.Save()
                if wasSaved:
                    if not Global_TocManager.IsInPatch(Entry):
                        Entry = Global_TocManager.AddEntryToPatch(int(ID), UnitID)
                else:
                    self.report({"ERROR"}, f"Object ID 为 {ID} 的物体保存失败 ")
                    num_meshes -= len(MeshData[ID])
                # for valid_obj in valid_object_list:
                #     valid_obj.select_set(True)
                    
                # Global_TocManager.Save(int(ID), UnitID)
        self.report({'INFO'}, f"成功保存 {num_meshes}/{num_initially_selected} 个网格。")
        if errors:
            self.report({'ERROR'}, f"保存网格时发生错误。请点击这里查看。")
        PrettyPrint(f"保存网格耗时: {time.time()-start}")
                
        return{'FINISHED'}

#endregion

#region Operators: Textures

# save texture from blender to archive button
# TODO: allow the user to choose an image, instead of looking for one of the same name
class SaveTextureFromBlendImageOperator(Operator):
    bl_label = "Save Texture"
    bl_idname = "helldiver2.texture_saveblendimage"

    object_id: StringProperty()
    def execute(self, context):
        Entries = EntriesFromString(self.object_id, TexID)
        for Entry in Entries:
            if Entry != None:
                if not Entry.IsLoaded: Entry.Load()
                try:
                    BlendImageToStingrayTexture(bpy.data.images[str(self.object_id)], Entry.LoadedData)
                except:
                    PrettyPrint("No blend texture was found for saving, using original", "warn"); pass
            Global_TocManager.Save(Entry.FileID, TexID)
        return{'FINISHED'}

# import texture from archive button
class ImportTextureOperator(Operator):
    bl_label = "Import Texture"
    bl_idname = "helldiver2.texture_import"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Load(int(EntryID), TexID)
        return{'FINISHED'}

# export texture to file
class ExportTextureOperator(Operator, ExportHelper):
    bl_label = "Export Texture"
    bl_idname = "helldiver2.texture_export"
    filename_ext = ".dds"

    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), TexID)
        if Entry != None:
            data = Entry.Load(False, False)
            with open(self.filepath, 'w+b') as f:
                f.write(Entry.LoadedData.ToDDS())
        return{'FINISHED'}
    
    def invoke(self, context, _event):
        if not self.filepath:
            blend_filepath = context.blend_data.filepath
            if not blend_filepath:
                blend_filepath = self.object_id
            else:
                blend_filepath = os.path.splitext(blend_filepath)[0]

            self.filepath = blend_filepath + self.filename_ext

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# batch export texture to file
class BatchExportTextureOperator(Operator):
    bl_label = "Export Textures"
    bl_idname = "helldiver2.texture_batchexport"
    filename_ext = ".dds"

    directory: StringProperty(name="Outdir Path",description="dds output dir")
    filter_folder: BoolProperty(default=True,options={"HIDDEN"})

    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Entry = Global_TocManager.GetEntry(EntryID, TexID)
            if Entry != None:
                data = Entry.Load(False, False)
                with open(self.directory + str(Entry.FileID)+".dds", 'w+b') as f:
                    f.write(Entry.LoadedData.ToDDS())
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# import texture from archive button
class SaveTextureFromDDSOperator(Operator, ImportHelper):
    bl_label = "Save Texture"
    bl_idname = "helldiver2.texture_savefromdds"

    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), TexID)
        if Entry != None:
            if len(self.filepath) > 1:
                # get texture data
                Entry.Load()
                StingrayTex = Entry.LoadedData
                with open(self.filepath, 'r+b') as f:
                    StingrayTex.FromDDS(f.read())
                Toc = MemoryStream(IOMode="write")
                Gpu = MemoryStream(IOMode="write")
                Stream = MemoryStream(IOMode="write")
                StingrayTex.Serialize(Toc, Gpu, Stream)
                # add texture to entry
                Entry.SetData(Toc.Data, Gpu.Data, Stream.Data, False)

                Global_TocManager.Save(int(self.object_id), TexID)
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return{'FINISHED'}

#endregion

#region Operators: Materials

class SaveMaterialOperator(Operator):
    bl_label = "Save Material"
    bl_idname = "helldiver2.material_save"
    bl_description = "保存材质"

    object_id: StringProperty()
    def execute(self, context):
        # 检查Patch
        has_patch =  Global_TocManager.CheckActivePatch()
        if not has_patch:
            self.report({'ERROR'}, f"没有激活的Patch，无法保存，请先创建一个Patch。")
            return{'CANCELLED'}
        
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Save(int(EntryID), MaterialID)
        return{'FINISHED'}

class ImportMaterialOperator(Operator):
    bl_label = "Import Material"
    bl_idname = "helldiver2.material_import"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Load(int(EntryID), MaterialID)
        return{'FINISHED'}

class AddMaterialOperator(Operator):
    bl_label = "Add Material"
    bl_idname = "helldiver2.material_add"
    bl_description = "添加材质,需要激活一个Patch"
    
    @classmethod
    def poll(cls, context):
        has_patch =  Global_TocManager.CheckActivePatch()
        return has_patch

    global Global_Materials
    selected_material: EnumProperty(items=Global_Materials, name="Template", default=1)

    def execute(self, context):
                # 检查Patch
        has_patch =  Global_TocManager.CheckActivePatch()
        if not has_patch:
            self.report({'ERROR'}, f"没有激活的Patch，无法创建，请先创建一个Patch。")
            return{'CANCELLED'}
        
        Entry = TocEntry()
        Entry.FileID = r.randint(1, 0xffffffffffffffff)
        Entry.TypeID = MaterialID
        Entry.MaterialTemplate = self.selected_material
        Entry.IsCreated = True
        with open(f"{Global_materialpath}\\{self.selected_material}.material", 'r+b') as f:
            data = f.read()
        Entry.TocData_OLD   = data
        Entry.TocData       = data

        Global_TocManager.AddNewEntryToPatch(Entry)

        # debug_print_id
        # mat_id = GetEntryParentMaterialID(Entry)
        # self.report({"INFO"}, f"Material {self.selected_material} Parent ID: {mat_id}")
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ShowMaterialEditorOperator(Operator):
    bl_label = "Show Material Editor"
    bl_idname = "helldiver2.material_showeditor"

    object_id: StringProperty()
    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), MaterialID)
        if Entry != None:
            if not Entry.IsLoaded: Entry.Load(False, False)
            mat = Entry.LoadedData
            if mat.DEV_ShowEditor:
                mat.DEV_ShowEditor = False
            else:
                mat.DEV_ShowEditor = True
        return{'FINISHED'}

class SetMaterialTexture(Operator, ImportHelper):
    bl_label = "Set Material Texture"
    bl_idname = "helldiver2.material_settex"


    filename_ext = ".dds"

    filter_glob: StringProperty(default="*.dds;*.tga", options={'HIDDEN'})



    object_id: StringProperty(options={"HIDDEN"})
    tex_idx: IntProperty(options={"HIDDEN"})
    
    def ColorSpaceEnum():
        return [("sRGB", "sRGB", ""), ("Linear", "Linear", "")]

    SaveColorSpace: EnumProperty(name="色彩空间", items=[("Linear", "Linear", ""),("sRGB", "sRGB", "")])
   
    
    
    def draw(self, context):
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        is_tga_on = addon_prefs.tga_Tex_Import_Switch
        is_png_on = addon_prefs.png_Tex_Import_Switch
        if is_tga_on or is_png_on:
            layout = self.layout
            layout.label(text="颜色贴图使用sRGB,法向金属糙度等使用线性",icon="INFO")
            layout.label(text="导入的纹理在保存时将会转换为下列的色彩空间",icon="INFO")
            layout.label(text="纹理色彩空间为：")
            layout.prop(self, "SaveColorSpace")
            
    
    def addprefix(self, path, prefix):
        Ori_filename = os.path.basename(path)
        
        add_prefix_in_path = os.path.join(os.path.dirname(path), f"{prefix}"+ Ori_filename)
        return add_prefix_in_path
    
    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), MaterialID)
        if Entry != None:
            if Entry.IsLoaded:
                if self.SaveColorSpace == "sRGB" and ".tga" in os.path.basename(self.filepath):
                    
                    Entry.LoadedData.DEV_DDSPaths[self.tex_idx] = self.addprefix(path=self.filepath,prefix="[-_彩色_-]")
                if self.SaveColorSpace == "Linear" and ".tga" in os.path.basename(self.filepath):
                    
                    Entry.LoadedData.DEV_DDSPaths[self.tex_idx] = self.addprefix(path=self.filepath,prefix="[-_线性_-] ")
                else:
                    
                    Entry.LoadedData.DEV_DDSPaths[self.tex_idx] = self.filepath
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}
    def invoke(self, context, event):

        addon_prefs = AQ_PublicClass.get_addon_prefs()
        is_tga_on = addon_prefs.tga_Tex_Import_Switch
        is_png_on = addon_prefs.png_Tex_Import_Switch

        if not is_tga_on and not is_png_on:
            self.filter_glob = "*.dds"
        elif is_tga_on and is_png_on:
            self.filter_glob = "*.tga;*.png"
        elif is_tga_on and not is_png_on:
            self.filter_glob = "*.tga"
        elif is_png_on and not is_tga_on:
            self.filter_glob = "*.png"
            
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
            
        
        

#endregion

#region Operators : Animation
class ImportStingrayAnimationOperator(Operator):
    bl_label = "Import Animation"
    bl_idname = "helldiver2.archive_animation_import"
    bl_description = "导入动画到场景中，必须选择一个骨架"
    
    @classmethod
    def poll(cls, context):
        object = context.active_object
        return object is not None and object.type == "ARMATURE"
    
    
    object_id: StringProperty()
    def execute(self, context):
        # check if armature selected
        armature = context.active_object
        if armature.type != "ARMATURE":
            self.report({'ERROR'}, "Please select an armature to import the animation to")
            return {'CANCELLED'}
        animation_id = self.object_id
        try:
            Global_TocManager.Load(int(animation_id), AnimationID)
        except AnimationException as e:
            self.report({'ERROR'}, f"{e}")
            return {'CANCELLED'}
        except Exception as error:
            PrettyPrint(f"Encountered unknown animation error: {error}", 'error')
            self.report({'ERROR'}, f"Encountered an error whilst importing animation. See Console for more info.")
            return {'CANCELLED'}
        return{'FINISHED'}
        
class SaveStingrayAnimationOperator(Operator):
    bl_label  = "Save Animation"
    bl_idname = "helldiver2.archive_animation_save"
    bl_description = "保存动画，必须选择一个骨架"
    
    @classmethod
    def poll(cls, context):
        object = context.active_object
        return object is not None and object.type == "ARMATURE"
    
    
    def execute(self, context):
        if PatchesNotLoaded(self):
            return{'CANCELLED'}
        object = bpy.context.active_object
        if object.animation_data is None or object.animation_data.action is None:
            self.report({'ERROR'}, "Armature has no active action!")
            return {'CANCELLED'}
        if object == None or object.type != "ARMATURE":
            self.report({'ERROR'}, "Please select an armature")
            return {'CANCELLED'}
        action_name = object.animation_data.action.name
        if len(object.animation_data.action.fcurves) == 0:
            self.report({'ERROR'}, f"Action: {action_name} has no keyframe data! Make sure your animation has at least an initial keyframe with a recorded pose.")
            return {'CANCELLED'}
        entry_id = action_name.split(" ")[0].split("_")[0].split(".")[0]
        if entry_id.startswith("0x"):
            entry_id = hex_to_decimal(entry_id)
        try:
            bones_id = object['BonesID']
        except Exception as e:
            PrettyPrint(f"Encountered animation error: {e}", 'error')
            self.report({'ERROR'}, f"Armature: {object.name} is missing HD2 custom property: BonesID")
            return{'CANCELLED'}
        PrettyPrint(f"Getting Animation Entry: {entry_id}")
        animation_entry = Global_TocManager.GetEntryByLoadArchive(int(entry_id), AnimationID)
        if not animation_entry:
            self.report({'ERROR'}, f"Could not find animation entry for Action: {action_name} as EntryID: {entry_id}. Assure your action name starts with a valid ID for the animation entry.")
            return{'CANCELLED'}
        if not animation_entry.IsLoaded: animation_entry.Load(True, False)
        bones_entry = Global_TocManager.GetEntryByLoadArchive(int(bones_id), BoneID)
        bones_data = bones_entry.TocData
        try:
            animation_entry.LoadedData.load_from_armature(context, object, bones_data)
        except AnimationException as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        wasSaved = animation_entry.Save()
        if wasSaved:
            if not Global_TocManager.IsInPatch(animation_entry):
                animation_entry = Global_TocManager.AddEntryToPatch(int(entry_id), AnimationID)
            else:
                Global_TocManager.RemoveEntryFromPatch(int(entry_id), AnimationID)
                animation_entry = Global_TocManager.AddEntryToPatch(int(entry_id), AnimationID)
        else:
            self.report({"ERROR"}, f"Failed to save animation for armature {bpy.context.selected_objects[0].name}.")
            return{'CANCELLED'}
        self.report({'INFO'}, f"Saved Animation")
        return {'FINISHED'}


#region Operators: Clipboard Functionality

class CopyArchiveEntryOperator(Operator):
    bl_label = "Copy Entry"
    bl_idname = "helldiver2.archive_copy"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        Global_TocManager.Copy(Entries)
        return{'FINISHED'}

class PasteArchiveEntryOperator(Operator):
    bl_label = "Paste Entry"
    bl_idname = "helldiver2.archive_paste"

    def execute(self, context):
        Global_TocManager.Paste()
        return{'FINISHED'}

class ClearClipboardOperator(Operator):
    bl_label = "Clear Clipboard"
    bl_idname = "helldiver2.archive_clearclipboard"

    def execute(self, context):
        Global_TocManager.ClearClipboard()
        return{'FINISHED'}

class CopyTextOperator(Operator):
    bl_label  = "Copy ID"
    bl_idname = "helldiver2.copytest"

    text: StringProperty()
    def execute(self, context):
        cmd='echo '+str(self.text).strip()+'|clip'
        subprocess.check_call(cmd, shell=True)
        return{'FINISHED'}

#endregion

#region Operators: UI/UX

class LoadArchivesOperator(Operator):
    bl_label = "Load Archives"
    bl_idname = "helldiver2.archives_import"

    paths_str: StringProperty(name="paths_str")
    def execute(self, context):
        global Global_TocManager
        paths = self.paths_str.split(',')
        for path in paths:
            if path != "" and os.path.exists(path):
                Global_TocManager.LoadArchive(path)
                id = self.paths_str.replace(Global_gamepath, "")
                name = f"{GetArchiveNameFromID(id)} {id}"
                self.report({'INFO'}, f"载入 {name}")
        self.paths = []
        return{'FINISHED'}

class SearchArchivesOperator(Operator):
    bl_label = "搜索已知Archive"
    bl_idname = "helldiver2.search_archives"
    bl_description = "搜索已知Archive "

    SearchField : StringProperty(name="SearchField", default="")
    #======不应该显示的分类资产=========
    hide_classify = [
        "大概环境物体",
        "未知",
        "无网格",
        "已无法搜索",
        "导入失败",
        "None",
        "没有导入确认",
        "音频",
        "视频",
    ]
    
    
    def draw(self, context):
        global Global_updatearchivelistCN_list
        layout = self.layout
        row = layout.row()
        row.scale_y = 1.2
        row.prop(self, "SearchField", icon='VIEWZOOM',text="搜索Archive")
        # Update displayed archives
        if self.PrevSearch != self.SearchField:
            self.PrevSearch = self.SearchField

            self.ArchivesToDisplay = []
            for Entry in Global_updatearchivelistCN_list:
                if Entry["Description"].lower().find(self.SearchField.lower()) != -1 or self.SearchField.lower() in Entry["Classify"]:
                    if not set(Entry["Classify"]).issubset(set(self.hide_classify)) and self.hide_classify[3] not in Entry["Classify"] and Entry["Classify"] and Entry["Description"].find("None") == -1:

                        self.ArchivesToDisplay.append([Entry["Classify"], Entry["Description"], Entry["ArchiveID"]])
    
        if self.SearchField != "" and len(self.ArchivesToDisplay) == 0:
            row = layout.row(); row.label(text="没有找到匹配的Archive")
            row = layout.row(); row.label(text="收集表中有的条目却不在这里？")
            row = layout.row(); row.label(text="尝试手动更新本地Archive列表")
            row = layout.row(); row.label(text="或打开Archive中文收集表链接：")
            row = layout.row(); row.operator("helldiver2.archive_spreadsheet", icon= 'URL')

        else:
            for Archive in self.ArchivesToDisplay:
                box = layout.box()
                row = box.row()
                row.label(text=str(Archive[0]).strip("[").strip("]")+": "+ Archive[1], icon='GROUP')
                row.scale_x = 1.5
                row.operator("helldiver2.archives_import", icon= 'FILE_NEW', text="").paths_str = Global_gamepath + str(Archive[2])

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        self.PrevSearch = "NONE"
        self.ArchivesToDisplay = []

        wm = context.window_manager
        return wm.invoke_props_dialog(self,width=400)

class SelectAllOfTypeOperator(Operator):
    bl_label  = "Select All Of Type"
    bl_idname = "helldiver2.select_type"

    object_typeid: StringProperty()
    def execute(self, context):
        Entries = GetDisplayData()[0]
        for EntryInfo in Entries:
            Entry = EntryInfo[0]
            if Entry.TypeID == int(self.object_typeid):
                DisplayEntry = Global_TocManager.GetEntry(Entry.FileID, Entry.TypeID)
                if DisplayEntry.IsSelected:
                    #Global_TocManager.DeselectEntries([Entry])
                    pass
                else:
                    Global_TocManager.SelectEntries([Entry], True)
        return{'FINISHED'}

class SetEntryFriendlyNameOperator(Operator):
    bl_label = "Set Friendly Name"
    bl_idname = "helldiver2.archive_setfriendlyname"

    NewFriendlyName : StringProperty(name="NewFriendlyName", default="")
    def draw(self, context):
        layout = self.layout; row = layout.row()
        row.prop(self, "NewFriendlyName", icon='COPY_ID')
        row = layout.row()
        if murmur64_hash(str(self.NewFriendlyName).encode()) == int(self.object_id):
            row.label(text="Hash is correct")
        else:
            row.label(text="Hash is incorrect")
        row.label(text=str(murmur64_hash(str(self.NewFriendlyName).encode())))

    object_id: StringProperty()
    def execute(self, context):
        AddFriendlyName(int(self.object_id), str(self.NewFriendlyName))
        return{'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

#endregion

#region Operators: Help

class HelpOperator(Operator):
    bl_label  = "Help"
    bl_idname = "helldiver2.help"

    def execute(self, context):
        url = "https://docs.google.com/document/d/1SF7iEekmxoDdf0EsJu1ww9u2Cr8vzHyn2ycZS7JlWl0"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}
    
class ButtonAQGitHub(bpy.types.Operator):
    bl_idname = "helldiver2.aq_githubweb"
    bl_label = "GitHub"
    bl_description = "打开AQ魔改版插件的 GitHub页面"

    def execute(self, context):
        webbrowser.open("https://github.com/Estecsky/io_scene_helldivers2_AQ")
        return {"FINISHED"}

class ArchiveSpreadsheetOperator(Operator):
    bl_label  = "Archive CN Spreadsheet"
    bl_idname = "helldiver2.archive_spreadsheet"
    bl_description = "打开绝地潜兵2中文Archive 收集表"

    def execute(self, context):
        url = "https://www.kdocs.cn/l/csRnAs7QlZvQ"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}

#endregion

#region Operators: Context Menu

def CopyToClipboard(txt):
    cmd='echo '+txt.strip()+'|clip'
    return subprocess.check_call(cmd, shell=True)

class CopyArchiveIDOperator(Operator):
    bl_label = "Copy Archive ID"
    bl_idname = "helldiver2.copy_archive_id"
    bl_description = "将活跃的 Archive ID 复制到剪贴板"

    def execute(self, context):
        if ArchivesNotLoaded(self):
            return {'CANCELLED'}
        archiveID = str(Global_TocManager.ActiveArchive.Name)
        CopyToClipboard(archiveID)
        self.report({'INFO'}, f"复制 Archive ID: {archiveID}")

        return {'FINISHED'}

class EntrySectionOperator(Operator):
    bl_label = "Collapse Section"
    bl_idname = "helldiver2.collapse_section"
    bl_description = "折叠该区域"

    type: StringProperty(default = "")

    def execute(self, context):
        global Global_Foldouts
        for i in range(len(Global_Foldouts)):
            if Global_Foldouts[i][0] == str(self.type):
                Global_Foldouts[i][1] = not Global_Foldouts[i][1]
                # PrettyPrint(f"Folding foldout: {Global_Foldouts[i]}")
        return {'FINISHED'}

stored_custom_properties = {}
class CopyCustomPropertyOperator(Operator):
    bl_label = "Copy HD2 Properties"
    bl_idname = "helldiver2.copy_custom_properties"
    bl_description = "复制绝地潜兵2网格的自定义属性"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global stored_custom_properties
        
        selectedObjects = context.selected_objects
        if len(selectedObjects) == 0:
            self.report({'WARNING'}, "没有选中的网格")
            return {'CANCELLED'}
        PrettyPrint(selectedObjects)

        obj = context.active_object
        stored_custom_properties.clear()
        for key, value in obj.items():
            if key not in obj.bl_rna.properties:  # Skip built-in properties
                stored_custom_properties[key] = value

        self.report({'INFO'}, f"复制了 {len(stored_custom_properties)} 个自定义属性")
        return {'FINISHED'}

class PasteCustomPropertyOperator(Operator):
    bl_label = "Paste HD2 Properties"
    bl_idname = "helldiver2.paste_custom_properties"
    bl_description = "粘贴绝地潜兵2网格的自定义属性"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global stored_custom_properties

        selectedObjects = context.selected_objects
        if len(selectedObjects) == 0:
            self.report({'WARNING'}, "没有选中的网格")
            return {'CANCELLED'}

        obj = context.active_object
        if not stored_custom_properties:
            self.report({'WARNING'}, "没有可粘贴的自定义属性")
            return {'CANCELLED'}

        for key, value in stored_custom_properties.items():
            obj[key] = value

        for area in bpy.context.screen.areas:
            area.tag_redraw()

        self.report({'INFO'}, f"粘贴了 {len(stored_custom_properties)} 个自定义属性")
        return {'FINISHED'}
    
class CopyDecimalIDOperator(Operator):
    bl_label = "Copy ID"
    bl_idname = "helldiver2.copy_decimal_id"
    bl_description = "复制所选网格的物体ID"

    def execute(self, context):
        object = context.active_object
        if not object:
            self.report({"ERROR"}, "没有选中的网格")
        try:
            ID = str(object["Z_ObjectID"])
        except:
            self.report({'ERROR'}, f"网格: {object.name} 没有 Helldivers 属性 ID")
            return {'CANCELLED'}
        
        CopyToClipboard(ID)
        self.report({'INFO'}, f"复制了 {object.name} 的物体 {ID}")
        return {'FINISHED'}
    
    
    
def CustomPropertyContext(self, context):
    layout = self.layout
    layout.separator()
    layout.label(text=Global_SectionHeader)
    layout.separator()
    # layout.operator("helldiver2.copy_hex_id", icon='COPY_ID')
    layout.operator("helldiver2.copy_decimal_id", icon='COPY_ID')
    layout.separator()
    layout.operator("helldiver2.copy_custom_properties", icon= 'COPYDOWN')
    layout.operator("helldiver2.paste_custom_properties", icon= 'PASTEDOWN')
    layout.separator()
    layout.operator("helldiver2.archive_animation_save", icon='ARMATURE_DATA')
    layout.operator("helldiver2.archive_mesh_batchsave", icon= 'FILE_BLEND')
        
#endregion


#region Menus and Panels

def LoadedArchives_callback(scene, context):
    items = [(Archive.Name,Archive.Name , "") for Archive in Global_TocManager.LoadedArchives]
    return items

def Patches_callback(scene, context):
    return [(Archive.Name, Archive.Name, Archive.Name ) for Archive in Global_TocManager.Patches]

class Hd2ToolPanelSettings(PropertyGroup):
    # Patches
    Patches   : EnumProperty(name="Patches", items=Patches_callback)
    PatchOnly : BoolProperty(name="Show Patch Entries Only", description = "仅显示当前补丁中存在的条目", default = False)
    # Archive
    ContentsExpanded : BoolProperty(default = True)
    LoadedArchives   : EnumProperty(name="LoadedArchives", items=LoadedArchives_callback)
    # Settings
    MenuExpanded     : BoolProperty(default = False)
    ShowMeshes       : BoolProperty(name="Meshes", description = "Show Meshes", default = True)
    ShowTextures     : BoolProperty(name="Textures", description = "Show Textures", default = True)
    ShowMaterials    : BoolProperty(name="Materials", description = "Show Materials", default = True)
    # ShowAnimations   : BoolProperty(name="Animations", description = "Show Animations", default = False)
    ShowOthers       : BoolProperty(name="Other", description = "Show All Else", default = False)
    ImportMaterials  : BoolProperty(name="Import Materials", description = "完全导入材质,通过附加利用的纹理,否则创建占位符", default = True)
    ImportLods       : BoolProperty(name="Import LODs", description = "导入LODs", default = False)
    ImportGroup0     : BoolProperty(name="Import Group 0 Only", description = "仅导入第一个顶点组,忽略其他组", default = True)
    ImportPhysics    : BoolProperty(name="Import Physics", description = "导入物理体", default = False)
    # ImportStatic     : BoolProperty(name="Import Static Meshes", description = "导入静态网格", default = False)
    # MakeCollections  : BoolProperty(name="Make Collections", description = "Make new collection when importing meshes", default = True)
    Force2UVs        : BoolProperty(name="Force 2 UV Sets", description = "强制至少2个UV集,某些材质需要此设置", default = True)
    Force1Group      : BoolProperty(name="Force 1 Group", description = "强制网格仅包含1个顶点组", default = True)
    AutoLods         : BoolProperty(name="Auto LODs", description = "根据LOD0自动生成LOD条目,不会实际减少网格质量", default = True)
    SaveBonePositions: BoolProperty(name="Save Animation Bone Positions", description = "保存动画中的骨骼位置 (可能会与添加动画冲突)", default = True)
    ImportArmature   : BoolProperty(name="Import Armatures", description = "导入网格的Armature", default = True)
    MergeArmatures   : BoolProperty(name="Merge Armatures", description = "将导入的Armature合并到选中的Armature", default = True)
    ParentArmature   : BoolProperty(name="Parent Armatures", description = "将导入的Armature设置为导入的网格的父对象", default = True)
    RemoveGoreMeshes : BoolProperty(name="Remove Gore Meshes", description = "自动删除所有使用断肢材质的顶点", default = True)
    shadervariablesUI : BoolProperty(name="Shader Variables UI", description = "显示着色器变量参数UI", default = True)
    LegacyWeightNames     : BoolProperty(name="Legacy Weight Names", description="使用旧版顶点组权重名称", default = False)

    # ShadeSmooth      : BoolProperty(name="Shade Smooth", description = "导入模型时平滑着色,开启此项将关闭自动平滑", default = True)
    # Search
    SearchField : StringProperty(default = "")
    
    # add
    IsRenamePatch : BoolProperty(name="RenamePatch",default = False,description = "重命名patch")
    IsChangeOutPath : BoolProperty(name="ChangeOutPath",default = False,description = "修改输出路径")
    NewPatchName : StringProperty(name="NewPatchName",default = "")
    NewPatchOutPath : StringProperty(name="NewOutPath",default = "",subtype='DIR_PATH')
    IsZipPatch : BoolProperty(name="ZipPatch",default = False,description = "压缩patch")

class HellDivers2ToolsPanel(Panel):
    bl_label = f"Helldivers 2 AQ Modified{bl_info['version']}"
    bl_idname = "SF_PT_Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Modding"
    bl_order = 0

    def draw_material_editor(self, Entry, layout, row):
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        scene = bpy.context.scene
        filepath = ""
        if Entry.IsLoaded:
            mat = Entry.LoadedData
            if mat.DEV_ShowEditor:
                for i, t in enumerate(mat.TexIDs):
                    row = layout.row(); row.separator(factor=2.0)
                    ddsPath = mat.DEV_DDSPaths[i]
                    if ddsPath != None: filepath = ddsPath
                    prefix = TextureTypeLookup[Entry.MaterialTemplate][i] if Entry.MaterialTemplate != None else ""
                    label = os.path.basename(filepath) if ddsPath != None else str(t)
                    row.label(text=prefix+label, icon='FILE_IMAGE')
                    props = row.operator("helldiver2.material_settex", icon='FILEBROWSER', text="")
                    props.object_id = str(Entry.FileID)
                    props.tex_idx = i
                #======
                row = layout.row(); row.separator(factor=2.0)
                # row.label(text="材质参数栏",icon='OPTIONS')
                row.prop(scene.Hd2ToolPanelSettings, "shadervariablesUI",
                icon="DOWNARROW_HLT" if scene.Hd2ToolPanelSettings.shadervariablesUI else "RIGHTARROW",
                icon_only=True, emboss=False, text=f"着色器变量参数栏 | 材质模板：{Entry.MaterialTemplate if Entry.MaterialTemplate != None else '无'}")
                if scene.Hd2ToolPanelSettings.shadervariablesUI:
                    row.prop(addon_prefs, "ShowshaderVariables_CN",text="")
                #=====
                if scene.Hd2ToolPanelSettings.shadervariablesUI:
                    for i, variable in enumerate(mat.ShaderVariables):
                        row = layout.row(); row.separator(factor=2.0)
                        split = row.split(factor=0.5)
                        row = split.column()
                        row.alignment = 'RIGHT'
                        name = variable.ID
                        if variable.name != "":
                            global Global_ShaderVariables_CN
                            name = variable.name
                            if addon_prefs.ShowshaderVariables_CN:
                                if Global_ShaderVariables_CN[name]:
                                    name = Global_ShaderVariables_CN[name]
                        row.label(text=f"{variable.klassName}: {name}", icon='OPTIONS')
                        row = split.column()
                        row.alignment = 'LEFT'
                        sections = len(variable.values)
                        if sections == 3: sections = 4 # add an extra for the color picker
                        row = row.split(factor=1/sections)
                        for j, value in enumerate(variable.values):
                            ShaderVariable = row.operator("helldiver2.material_shader_variable", text=str(round(value, 2)))
                            ShaderVariable.value = value
                            ShaderVariable.object_id = str(Entry.FileID)
                            ShaderVariable.variable_index = i
                            ShaderVariable.value_index = j
                        if len(variable.values) == 3:
                            ColorPicker = row.operator("helldiver2.material_shader_variable_color", text="", icon='EYEDROPPER')
                            ColorPicker.object_id = str(Entry.FileID)
                            ColorPicker.variable_index = i

    def draw_entry_buttons(self, box, row, Entry, PatchOnly):
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        if Entry.TypeID == UnitID:
            row.operator("helldiver2.archive_mesh_save", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.archive_mesh_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
            if Global_TocManager.IsInPatch(Entry) and addon_prefs.DisplayRenameButton:
                props = row.operator("helldiver2.archive_entryrename", icon='TEXT', text="")
                props.object_id     = str(Entry.FileID)
                props.object_typeid = str(Entry.TypeID)
        elif Entry.TypeID == TexID:
            row.operator("helldiver2.texture_saveblendimage", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.texture_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
        elif Entry.TypeID == MaterialID:
            row.operator("helldiver2.material_save", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.material_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.material_showeditor", icon='MOD_LINEART', text="").object_id = str(Entry.FileID)
            self.draw_material_editor(Entry, box, row)
        elif Entry.TypeID == AnimationID:
            row.operator("helldiver2.archive_animation_save",icon='FILE_BLEND', text="")
            row.operator("helldiver2.archive_animation_import", icon="IMPORT", text="").object_id = str(Entry.FileID)
            
        if Global_TocManager.IsInPatch(Entry):
            props = row.operator("helldiver2.archive_removefrompatch", icon='FAKE_USER_ON', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        else:
            props = row.operator("helldiver2.archive_addtopatch", icon='FAKE_USER_OFF', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        if Entry.IsModified:
            props = row.operator("helldiver2.archive_undo_mod", icon='TRASH', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        if PatchOnly:
            props = row.operator("helldiver2.archive_removefrompatch", icon='X', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)

    def draw(self, context):
        layout = self.layout
        scene = bpy.context.scene
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        # Draw Settings, Documentation and Spreadsheet
        row = layout.row()
        row.prop(scene.Hd2ToolPanelSettings, "MenuExpanded",
            icon="DOWNARROW_HLT" if scene.Hd2ToolPanelSettings.MenuExpanded else "RIGHTARROW",
            icon_only=True, emboss=False, text="Settings")
        if scene.Hd2ToolPanelSettings.MenuExpanded:
            row.operator("helldiver2.aq_githubweb", icon='URL', text="")
        row.operator("helldiver2.archive_spreadsheet", icon='INFO', text="")
        if scene.Hd2ToolPanelSettings.MenuExpanded:
            row = layout.row(); row.separator(); row.label(text="显示设置"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "ShowMeshes",text="显示网格")
            row.prop(scene.Hd2ToolPanelSettings, "ShowTextures",text="显示纹理")
            row.prop(scene.Hd2ToolPanelSettings, "ShowMaterials",text="显示材质")
            row.prop(addon_prefs, "ShowAnimations",text="显示动画")
            row.prop(scene.Hd2ToolPanelSettings, "ShowOthers",text="显示其他")
            row.prop(addon_prefs, "ShowArchivePatchPath",text="实时显示Archive和Patch路径")
            row.prop(addon_prefs,"Layout_search_New",text="显示搜索已知Archive为主的布局")
            row.prop(addon_prefs, "ShowQuickSwitch",text="显示快捷设置按钮")
            row = layout.row(); row.separator(); row.label(text="导入设置"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "ImportMaterials",text="导入材质")
            row.prop(scene.Hd2ToolPanelSettings, "ImportLods",text="导入Lods")
            row.prop(scene.Hd2ToolPanelSettings, "ImportGroup0",text="只导入Group 0")
            row.prop(addon_prefs, "MakeCollections",text="为每个物体创建集合")
            row.prop(scene.Hd2ToolPanelSettings, "ImportPhysics",text="导入物理")
            row.prop(addon_prefs, "ImportStatic",text="导入静态网格（无权重）")
            row.prop(scene.Hd2ToolPanelSettings, "RemoveGoreMeshes",text="删除断肢网格")
            row.prop(addon_prefs, "ShadeSmooth",text="导入模型时平滑着色")
            row.prop(addon_prefs, "tga_Tex_Import_Switch",text="开启TGA纹理导入")
            row.prop(addon_prefs, "png_Tex_Import_Switch",text="开启PNG纹理导入")
            row.prop(scene.Hd2ToolPanelSettings, "ParentArmature",text="父级Armature")
            row.prop(scene.Hd2ToolPanelSettings, "ImportArmature",text="导入Armature")
            row = layout.row(); row.separator(); row.label(text="导出设置"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "Force2UVs",text="强制使用2个UV通道")
            row.prop(scene.Hd2ToolPanelSettings, "Force1Group",text="强制使用1个权重组")
            row.prop(scene.Hd2ToolPanelSettings, "AutoLods",text="自动Lods")
            row.prop(scene.Hd2ToolPanelSettings, "SaveBonePositions",text="保存动画骨骼位置")
            row.prop(addon_prefs,"SaveUseAutoSmooth",text="保存网格时开启自动平滑")
            row.prop(addon_prefs,"ShowZipPatchButton",text="显示打包Patch为Zip功能")
            row.prop(addon_prefs,"DisplayRenameButton",text="显示重命名按钮")
            row = layout.row(); row.separator(); row.label(text="其他设置"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "LegacyWeightNames",text="旧权重名称")
            row.prop(scene.Hd2ToolPanelSettings, "MergeArmatures",text="合并Armature")
            
            row = layout.row()
            row.separator()
            row.label(text=Global_gamepath)
            row = row.grid_flow(columns=1)
            row.operator("helldiver2.change_filepath", icon='FILEBROWSER',text="更改游戏data目录")
            row = layout.row()
            row.separator()
            row.label(text="缓存目录")
            row = row.grid_flow(columns=1)
            row.operator("helldiver2.open_cache_directory",text="打开缓存目录",icon='FILE_FOLDER')
            row = layout.row(); row.separator(); row.label(text="手动更新本地Archive列表"); box = row.box(); row = box.grid_flow(columns=1)
            row.operator("helldiver2.update_archivelist_cn", text="更新已知资产列表", icon='FILE_REFRESH')
            row = layout.row(); row.separator(); row.label(text="一键添加转移ID属性"); row = row.grid_flow(columns=1)
            row.operator("helldiver2.add_swaps_id_prop", text="添加转移自定义ID属性", icon='ADD')
        # Draw Archive Import/Export Buttons
        if addon_prefs.ShowQuickSwitch:
            row = layout.row(); row = layout.row()
            row.alignment = 'CENTER'
            row.label(text="快捷设置")
            row = layout.row()
            row.prop(scene.Hd2ToolPanelSettings, "ImportLods",text="导入Lods")
            row.prop(addon_prefs, "ImportStatic",text="导入静态网格（无权重）")
            row.prop(scene.Hd2ToolPanelSettings, "AutoLods",text="自动Lods")
            
        row = layout.row(); row = layout.row()
        row.operator("helldiver2.archive_import_default", icon= 'SOLO_ON', text="")
        if addon_prefs.Layout_search_New:
            row.operator("helldiver2.search_archives", icon= 'VIEWZOOM', text="搜索已知Archive")
        else:
            row.operator("helldiver2.archive_import", icon= 'IMPORT',text="载入Archive").is_patch = False
            
        row.operator("helldiver2.archive_unloadall", icon= 'FILE_REFRESH', text="")
        row = layout.row()
        row.prop(scene.Hd2ToolPanelSettings, "LoadedArchives", text="Archives")
        
        if addon_prefs.Layout_search_New:
            row.operator("helldiver2.archive_import", icon= 'FILE_FOLDER',text="").is_patch = False
        else:
            row.operator("helldiver2.search_archives", icon= 'VIEWZOOM', text="")
            
        if len(Global_TocManager.LoadedArchives) > 0:
            Global_TocManager.SetActiveByName(scene.Hd2ToolPanelSettings.LoadedArchives)

        # Draw Patch Stuff
        row = layout.row(); row = layout.row()
        row.operator("helldiver2.archive_createpatch", icon= 'COLLECTION_NEW', text="新建Patch")
        row.operator("helldiver2.archive_export", icon= 'DISC', text="写入Patch")
        if addon_prefs.ShowZipPatchButton:
            row.operator("helldiver2.archive_zippatch_export",icon="EXPORT",text="导出为Zip")
        row.operator("helldiver2.patches_unloadall", icon= 'FILE_REFRESH', text="")
        
        row = layout.row()
        row.prop(scene.Hd2ToolPanelSettings, "Patches", text="Patches")
        if len(Global_TocManager.Patches) > 0:
            Global_TocManager.SetActivePatchByName(scene.Hd2ToolPanelSettings.Patches)
        row.prop(scene.Hd2ToolPanelSettings,"IsRenamePatch",icon = "GREASEPENCIL",text="")
        row.prop(scene.Hd2ToolPanelSettings,"IsChangeOutPath",icon = "FOLDER_REDIRECT",text="")
        row.operator("helldiver2.archive_import", icon= 'IMPORT', text="").is_patch = True
        #-------------add------------
        
        # Get Display Data
        DisplayData = GetDisplayData()
        DisplayTocEntries = DisplayData[0]
        DisplayTocTypes   = DisplayData[1]
        DisplayTocArchivePath = DisplayData[2]
        DisplayTocPatchPath = DisplayData[3]
        
        DisplayTocPatchPath_add = DisplayData[4]
        
        if scene.Hd2ToolPanelSettings.IsRenamePatch:
            row = layout.row()
            row.label(text="重命名已经打开",icon="ERROR")
            row = layout.row()
            row.operator("helldiver2.button_auto_rename_patch",text="自动重命名为基础资产的patch",icon="OUTLINER_DATA_GP_LAYER")
            row = layout.row()
            row.prop(scene.Hd2ToolPanelSettings, "NewPatchName", text="修改为 ")
        if scene.Hd2ToolPanelSettings.IsChangeOutPath:
            # PathSign = "\\" 
            row = layout.row()
            row.label(text="修改Patch写入路径已经打开",icon="ERROR")
            row = layout.row()
            row.prop(scene.Hd2ToolPanelSettings, "NewPatchOutPath", text="修改路径 ")
            
        if DisplayTocPatchPath_add != "": #首先判断是否载入patch
            box = layout.box()
            row = box.row()
            if scene.Hd2ToolPanelSettings.IsChangeOutPath: #判断是否打开自定义输出
                if scene.Hd2ToolPanelSettings.NewPatchOutPath != "": #判断是否有自定义路径输入，如果有
                    if scene.Hd2ToolPanelSettings.NewPatchName != "" and scene.Hd2ToolPanelSettings.IsRenamePatch: #判断是否打开重命名，如果打开
                        row.label(text=f"写入路径预览: {scene.Hd2ToolPanelSettings.NewPatchOutPath + scene.Hd2ToolPanelSettings.NewPatchName}",icon="INFO")
                    else: #没打开或者为空就使用原名称
                        row.label(text=f"写入路径预览: {scene.Hd2ToolPanelSettings.NewPatchOutPath + Global_TocManager.ActivePatch.Name}",icon="INFO")
                elif scene.Hd2ToolPanelSettings.NewPatchOutPath == "": #如果没有
                    if scene.Hd2ToolPanelSettings.NewPatchName != "" and scene.Hd2ToolPanelSettings.IsRenamePatch: #判断是否打开重命名，如果打开
                        row.label(text=f"写入路径预览: {os.path.join(os.path.dirname(DisplayTocPatchPath_add),scene.Hd2ToolPanelSettings.NewPatchName)}",icon="INFO")
                    else: #没自定义路径输入和没有重命名就使用原路径加原名称
                        row.label(text=f"写入路径预览: {DisplayTocPatchPath_add}",icon="INFO")
            else: #没打开自定义输出再判断是否使用重命名
                if scene.Hd2ToolPanelSettings.NewPatchName != "" and scene.Hd2ToolPanelSettings.IsRenamePatch:
                    row.label(text=f"写入路径预览: {os.path.join(os.path.dirname(DisplayTocPatchPath_add),scene.Hd2ToolPanelSettings.NewPatchName)}",icon="INFO")
                else:
                    row.label(text=f"写入路径预览: {DisplayTocPatchPath_add}",icon="INFO")
            if os.path.exists(Global_PatchBasePath) and not scene.Hd2ToolPanelSettings.IsZipPatch:
                box = layout.box()
                box.operator("helldiver2.open_patch_out_directory",text="打开Patch保存文件夹")
        else:
            pass
            # row = layout.row()
            # row.label(text="无Patch载入，无法预览写入路径",icon="ERROR")
        #---------------------------        
        # Draw Archive Contents
        row = layout.row(); row = layout.row()
        title = "无Archive载入"
        if Global_TocManager.ActiveArchive != None:
            ArchiveID = Global_TocManager.ActiveArchive.Name
            name = GetArchiveNameFromID(ArchiveID)
            title = f"{name}    ID: {ArchiveID}"
        if Global_TocManager.ActivePatch != None and scene.Hd2ToolPanelSettings.PatchOnly:
            name = Global_TocManager.ActivePatch.Name
            title = f"Patch: {name}"
        row.prop(scene.Hd2ToolPanelSettings, "ContentsExpanded",
            icon="DOWNARROW_HLT" if scene.Hd2ToolPanelSettings.ContentsExpanded else "RIGHTARROW",
            icon_only=True, emboss=False, text= title)
        row.operator("helldiver2.copy_archive_id", icon='COPY_ID', text="")
        row.prop(scene.Hd2ToolPanelSettings, "PatchOnly", text="")


        # Draw Contents
        NewFriendlyNames = []
        NewFriendlyIDs = []
        if scene.Hd2ToolPanelSettings.ContentsExpanded:
            if len(DisplayTocEntries) == 0: return

            # Draw Toc Archive or Patch Path
            if addon_prefs.ShowArchivePatchPath:
                if scene.Hd2ToolPanelSettings.PatchOnly:
                    row = layout.row()
                    row.label(text=f"Patch路径：{DisplayTocPatchPath}",icon="INFO")
                else:
                    col = layout.column()
                    col.label(text=f"Archive路径：{DisplayTocArchivePath}")
                    if DisplayTocPatchPath != "":
                        col.label(text=f"Patch路径：{DisplayTocPatchPath}",icon="INFO")
                    else:
                        col.label(text="No Patch",icon="INFO")
            # Draw Search Bar
            row = layout.row(); row = layout.row()
            row.prop(scene.Hd2ToolPanelSettings, "SearchField", icon='VIEWZOOM', text="")

            DrawChain = []
            for Type in DisplayTocTypes:
                # check if there is any entry of this type that matches search field
                # TODO: should probably make a better way to do this
                bFound = False
                for EntryInfo in DisplayTocEntries:
                    Entry = EntryInfo[0]
                    if Entry.TypeID == Type.TypeID:
                        if str(Entry.FileID).find(scene.Hd2ToolPanelSettings.SearchField) != -1:
                            bFound = True
                if not bFound: continue

                # Get Type Icon
                type_icon = 'FILE'
                show = None
                global Global_Foldouts
                if Type.TypeID == UnitID:
                    type_icon = 'FILE_3D'
                    if not scene.Hd2ToolPanelSettings.ShowMeshes: continue
                elif Type.TypeID == TexID:
                    type_icon = 'FILE_IMAGE'
                    if not scene.Hd2ToolPanelSettings.ShowTextures: continue
                elif Type.TypeID == MaterialID:
                    type_icon = 'MATERIAL'
                    if not scene.Hd2ToolPanelSettings.ShowMaterials: continue
                elif Type.TypeID == AnimationID:  # 添加显示动画条目
                    type_icon = 'ARMATURE_DATA'
                    if not addon_prefs.ShowAnimations: continue
                elif scene.Hd2ToolPanelSettings.ShowOthers: 
                    if Type.TypeID == BoneID: type_icon = 'BONE_DATA'
                    elif Type.TypeID == ParticleID:type_icon = 'PARTICLES'
                    elif Type.TypeID == WwiseBankID:  type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseDepID: type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseStreamID:  type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseMetaDataID: type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == StateMachineID: type_icon = 'DRIVER'
                    elif Type.TypeID == StringID: type_icon = 'WORDWRAP_ON'
                    elif Type.TypeID == PhysicsID: type_icon = 'PHYSICS'
                else:
                    continue

                for section in Global_Foldouts:
                    if section[0] == str(Type.TypeID):
                        show = section[1]
                        break
                if show == None:
                    fold = False
                    if Type.TypeID == MaterialID or Type.TypeID == TexID or Type.TypeID == UnitID: fold = True
                    foldout = [str(Type.TypeID), fold]
                    Global_Foldouts.append(foldout)
                    PrettyPrint(f"Adding Foldout ID: {foldout}")
                    
                fold_icon = "DOWNARROW_HLT" if show else "RIGHTARROW"
                # Draw Type Header
                box = layout.box(); row = box.row()
                typeName = GetTypeNameFromID(Type.TypeID)
                split = row.split()
                
                sub = split.row(align=True)
                sub.operator("helldiver2.collapse_section", text=f"{typeName}: {str(Type.TypeID)}", icon=fold_icon, emboss=False).type = str(Type.TypeID)
                # Skip drawling entries if section hidden
                if not show: continue
                
                row.operator("helldiver2.select_type", icon='RESTRICT_SELECT_OFF', text="").object_typeid = str(Type.TypeID)
                # Draw Add Material Button
                if typeName == "material": row.operator("helldiver2.material_add", icon='FILE_NEW', text="")

                # Draw Archive Entries
                col = box.column()
                for EntryInfo in DisplayTocEntries:
                    Entry = EntryInfo[0]
                    PatchOnly = EntryInfo[1]
                    # Exclude entries that should not be drawn
                    if Entry.TypeID != Type.TypeID: continue
                    if str(Entry.FileID).find(scene.Hd2ToolPanelSettings.SearchField) == -1: continue
                    # Deal with friendly names
                    if len(Global_TocManager.SavedFriendlyNameIDs) > len(DrawChain) and Global_TocManager.SavedFriendlyNameIDs[len(DrawChain)] == Entry.FileID:
                        FriendlyName = Global_TocManager.SavedFriendlyNames[len(DrawChain)]
                    else:
                        try:
                            FriendlyName = Global_TocManager.SavedFriendlyNames[Global_TocManager.SavedFriendlyNameIDs.index(Entry.FileID)]
                            NewFriendlyNames.append(FriendlyName)
                            NewFriendlyIDs.append(Entry.FileID)
                        except:
                            FriendlyName = GetFriendlyNameFromID(Entry.FileID)
                            NewFriendlyNames.append(FriendlyName)
                            NewFriendlyIDs.append(Entry.FileID)


                    # Draw Entry
                    PatchEntry = Global_TocManager.GetEntry(int(Entry.FileID), int(Entry.TypeID))
                    PatchEntry.DEV_DrawIndex = len(DrawChain)

                    row = col.row(align=True); row.separator()
                    props = row.operator("helldiver2.archive_entry", icon=type_icon, text=FriendlyName, emboss=PatchEntry.IsSelected, depress=PatchEntry.IsSelected)
                    props.object_id     = str(Entry.FileID)
                    props.object_typeid = str(Entry.TypeID)
                    # Draw Entry Buttons
                    self.draw_entry_buttons(col, row, PatchEntry, PatchOnly)
                    # Update Draw Chain
                    DrawChain.append(PatchEntry)
            Global_TocManager.DrawChain = DrawChain
        Global_TocManager.SavedFriendlyNames = NewFriendlyNames
        Global_TocManager.SavedFriendlyNameIDs = NewFriendlyIDs

class WM_MT_button_context(Menu):
    bl_label = "Entry Context Menu"

    def draw_entry_buttons(self, row, Entry):
        if not Entry.IsSelected:
            Global_TocManager.SelectEntries([Entry])

        # Combine entry strings to be passed to operators
        FileIDStr = ""
        TypeIDStr = ""
        for SelectedEntry in Global_TocManager.SelectedEntries:
            FileIDStr += str(SelectedEntry.FileID)+","
            TypeIDStr += str(SelectedEntry.TypeID)+","
        # Get common class
        AreAllMeshes    = True
        AreAllTextures  = True
        AreAllMaterials = True
        SingleEntry = True
        NumSelected = len(Global_TocManager.SelectedEntries)
        if len(Global_TocManager.SelectedEntries) > 1:
            SingleEntry = False
        for SelectedEntry in Global_TocManager.SelectedEntries:
            if SelectedEntry.TypeID == UnitID:
                AreAllTextures = False
                AreAllMaterials = False
            elif SelectedEntry.TypeID == TexID:
                AreAllMeshes = False
                AreAllMaterials = False
            elif SelectedEntry.TypeID == MaterialID:
                AreAllTextures = False
                AreAllMeshes = False
        
        RemoveFromPatchName = "Remove From Patch" if SingleEntry else f"Remove {NumSelected} From Patch"
        AddToPatchName = "Add To Patch" if SingleEntry else f"Add {NumSelected} To Patch"
        ImportMeshName = "Import Mesh" if SingleEntry else f"Import {NumSelected} Meshes"
        ImportTextureName = "Import Texture" if SingleEntry else f"Import {NumSelected} Textures"
        ImportMaterialName = "Import Material" if SingleEntry else f"Import {NumSelected} Materials"
        DumpObjectName = "Dump Object" if SingleEntry else f"Dump {NumSelected} Objects"
        SaveTextureName = "Save Blender Texture" if SingleEntry else f"Save Blender {NumSelected} Textures"
        SaveMaterialName = "Save Material" if SingleEntry else f"Save {NumSelected} Materials"
        UndoName = "Undo Modifications" if SingleEntry else f"Undo {NumSelected} Modifications"
        CopyName = "Copy Entry" if SingleEntry else f"Copy {NumSelected} Entries"
        
        # Draw seperator
        row.separator()
        row.label(text="---------- HellDivers2 ----------")

        # Draw copy button
        row.separator()
        props = row.operator("helldiver2.archive_copy", icon='COPYDOWN', text=CopyName)
        props.object_id     = FileIDStr
        props.object_typeid = TypeIDStr
        if len(Global_TocManager.CopyBuffer) != 0:
            row.operator("helldiver2.archive_paste", icon='PASTEDOWN', text="Paste "+str(len(Global_TocManager.CopyBuffer))+" Entries")
            row.operator("helldiver2.archive_clearclipboard", icon='TRASH', text="Clear Clipboard")
        if SingleEntry:
            props = row.operator("helldiver2.archive_duplicate", icon='DUPLICATE', text="Duplicate Entry")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        
        if Global_TocManager.IsInPatch(Entry):
            props = row.operator("helldiver2.archive_removefrompatch", icon='X', text=RemoveFromPatchName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr
        else:
            props = row.operator("helldiver2.archive_addtopatch", icon='PLUS', text=AddToPatchName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr

        # Draw import buttons
        # TODO: Add generic import buttons
        row.separator()
        if AreAllMeshes:
            row.operator("helldiver2.archive_mesh_import", icon='IMPORT', text=ImportMeshName).object_id = FileIDStr
        if AreAllTextures:
            row.operator("helldiver2.texture_import", icon='IMPORT', text=ImportTextureName).object_id = FileIDStr
            if SingleEntry:
                row.operator("helldiver2.texture_export", icon='EXPORT', text="Export Texture").object_id = str(Entry.FileID)
            else:
                row.operator("helldiver2.texture_batchexport", icon='EXPORT', text=f"Export {NumSelected} Textures").object_id = FileIDStr
        elif AreAllMaterials:
            row.operator("helldiver2.material_import", icon='IMPORT', text=ImportMaterialName).object_id = FileIDStr
        # Draw export buttons
        row.separator()
        props = row.operator("helldiver2.archive_object_dump_export", icon='PACKAGE', text=DumpObjectName)
        props.object_id     = FileIDStr
        props.object_typeid = TypeIDStr
        # Draw dump import button
        if AreAllMaterials and SingleEntry: row.operator("helldiver2.archive_object_dump_import", icon="IMPORT", text="Import Raw Dump").object_id = FileIDStr
        # Draw save buttons
        row.separator()
        if AreAllMeshes:
            if SingleEntry:
                row.operator("helldiver2.archive_mesh_save", icon='FILE_BLEND', text="Save Mesh").object_id = str(Entry.FileID)
            else:
              row.operator("helldiver2.archive_mesh_batchsave", icon='FILE_BLEND', text=f"Save {NumSelected} Meshes")
        elif AreAllTextures:
            row.operator("helldiver2.texture_saveblendimage", icon='FILE_BLEND', text=SaveTextureName).object_id = FileIDStr
            if SingleEntry:
                row.operator("helldiver2.texture_savefromdds", icon='IMAGE_REFERENCE', text="Save Texture From DDS").object_id = str(Entry.FileID)
        elif AreAllMaterials:
            row.operator("helldiver2.material_save", icon='FILE_BLEND', text=SaveMaterialName).object_id = FileIDStr
        # Draw copy ID buttons
        if SingleEntry:
            row.separator()
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry ID").text = str(Entry.FileID)
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Type ID").text  = str(Entry.TypeID)
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Friendly Name").text  = GetFriendlyNameFromID(Entry.FileID)
            if Global_TocManager.IsInPatch(Entry):
                props = row.operator("helldiver2.archive_entryrename", icon='TEXT', text="Rename")
                props.object_id     = str(Entry.FileID)
                props.object_typeid = str(Entry.TypeID)
        if Entry.IsModified:
            row.separator()
            props = row.operator("helldiver2.archive_undo_mod", icon='TRASH', text=UndoName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr

        if SingleEntry:
            row.operator("helldiver2.archive_setfriendlyname", icon='WORDWRAP_ON', text="Set Friendly Name").object_id = str(Entry.FileID)
    
    def draw(self, context):
        value = getattr(context, "button_operator", None)
        if type(value).__name__ == "HELLDIVER2_OT_archive_entry":
            layout = self.layout
            FileID = getattr(value, "object_id")
            TypeID = getattr(value, "object_typeid")
            self.draw_entry_buttons(layout, Global_TocManager.GetEntry(int(FileID), int(TypeID)))

#endregion

classes = (
    LoadArchiveOperator,
    PatchArchiveOperator,
    ImportStingrayMeshOperator,
    SaveStingrayMeshOperator,
    ImportStingrayAnimationOperator,
    SaveStingrayAnimationOperator,
    ImportMaterialOperator,
    ImportTextureOperator,
    ExportTextureOperator,
    DumpArchiveObjectOperator,
    ImportDumpOperator,
    Hd2ToolPanelSettings,
    HellDivers2ToolsPanel,
    UndoArchiveEntryModOperator,
    AddMaterialOperator,
    SaveMaterialOperator,
    SaveTextureFromBlendImageOperator,
    ShowMaterialEditorOperator,
    SetMaterialTexture,
    SearchArchivesOperator,
    LoadArchivesOperator,
    CopyArchiveEntryOperator,
    PasteArchiveEntryOperator,
    ClearClipboardOperator,
    SaveTextureFromDDSOperator,
    HelpOperator,
    ArchiveSpreadsheetOperator,
    UnloadArchivesOperator,
    ArchiveEntryOperator,
    CreatePatchFromActiveOperator,
    AddEntryToPatchOperator,
    RemoveEntryFromPatchOperator,
    CopyTextOperator,
    BatchExportTextureOperator,
    BatchSaveStingrayMeshOperator,
    SelectAllOfTypeOperator,
    RenamePatchEntryOperator,
    DuplicateEntryOperator,
    SetEntryFriendlyNameOperator,
    MaterialShaderVariableEntryOperator,
    MaterialShaderVariableColorEntryOperator,
    ButtonOpenCacheDirectory,
    ButtonAutoRenamePatch,
    ButtonOpenPatchOutDirectory,
    ZipPatchArchiveOperator,
    DefaultLoadArchiveOperator,
    ChangeFilepathOperator,
    ButtonUpdateArchivelistCN,
    CopyArchiveIDOperator,
    EntrySectionOperator,
    ButtonAQGitHub,
    UnloadPatchesOperator,
    AddSwapsID_property,
    CopyCustomPropertyOperator,
    PasteCustomPropertyOperator,
    CopyDecimalIDOperator,
)

Global_TocManager = TocManager()

def register():
    LoadTypeHashes()
    LoadNameHashes()
    LoadShaderVariables(Global_variablespath)
    LoadShaderVariables_CN(Global_variablesCNpath)
    LoadUpdateArchiveList_CN()
    InitializeConfig()
    LoadBoneHashes(Global_bonehashpath, Global_BoneNames)
    for cls in classes:
        bpy.utils.register_class(cls)
    Scene.Hd2ToolPanelSettings = PointerProperty(type=Hd2ToolPanelSettings)
    bpy.utils.register_class(WM_MT_button_context)
    addonPreferences.register()
    addon_updater_ops.register(bl_info)
    bpy.types.VIEW3D_MT_object_context_menu.append(CustomPropertyContext)

def unregister():
    bpy.utils.unregister_class(WM_MT_button_context)
    del Scene.Hd2ToolPanelSettings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    addonPreferences.unregister()
    addon_updater_ops.unregister()
    bpy.types.VIEW3D_MT_object_context_menu.remove(CustomPropertyContext)

if __name__=="__main__":
    register()