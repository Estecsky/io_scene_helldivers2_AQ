bl_info = {
    "name": "Helldivers 2 Archives",
    "blender": (4, 0, 0),
    "category": "Import-Export",
    "author": "kboykboy2, AQ_Echoo",
    "warning": "此为修改版",
    "version": (1, 7, 7),
    "doc_url": "https://github.com/Estecsky/io_scene_helldivers2_AQ"
}

#region Imports

# System
import ctypes, os, tempfile, subprocess, time, webbrowser
import random as r
from copy import deepcopy
import copy
from math import ceil # type: ignore
from pathlib import Path

# Blender
import bpy, bmesh, mathutils
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, PointerProperty
from bpy.types import Panel, Operator, PropertyGroup, Scene, Menu

# Local
# NOTE: Not bothering to do importlib reloading shit because these modules are unlikely to be modified frequently enough to warrant testing without Blender restarts
from .math import MakeTenBitUnsigned, TenBitUnsigned
from .memoryStream import MemoryStream
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

Global_dllpath             = f"{AddonPath}\\deps\\HDTool_Helper.dll"
Global_texconvpath         = f"{AddonPath}\\deps\\texconv.exe"
Global_palettepath         = f"{AddonPath}\\deps\\NormalPalette.dat"
Global_materialpath        = f"{AddonPath}\\materials"
Global_typehashpath        = f"{AddonPath}\\hashlists\\typehash.txt"
Global_filehashpath        = f"{AddonPath}\\hashlists\\filehash.txt"
Global_friendlynamespath   = f"{AddonPath}\\hashlists\\friendlynames.txt"
Global_variablespath       = f"{AddonPath}\\hashlists\\shadervariables.txt"

Global_variablesCNpath     = f"{AddonPath}\\hashlists\\shadervariables_combine_CN.txt"
Global_updatearchivelistCNpath = f"{AddonPath}\\hashlists\\update_archive_listCN.txt"

Global_configpath          = f"{BlenderAddonsPath}\\io_scene_helldivers2_AQ.ini"
Global_defaultgamepath     = "C:\Program Files (x86)\Steam\steamapps\common\Helldivers 2\data\ "
Global_defaultgamepath     = Global_defaultgamepath[:len(Global_defaultgamepath) - 1]
Global_gamepath            = ""




Global_CPPHelper = ctypes.cdll.LoadLibrary(Global_dllpath) if os.path.isfile(Global_dllpath) else None

Global_ShaderVariables = {}
Global_ShaderVariables_CN = {}
Global_updatearchivelistCN_list = []
Global_PatchBasePath = ""
Global_Foldouts = []
#endregion
#region Common Hashes & Lookups

CompositeMeshID = 14191111524867688662
MeshID = 16187218042980615487
TexID  = 14790446551990181426
MaterialID  = 16915718763308572383

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
    "bloom": (
        "Normal: ",
        "Bloom Color: ",
        "Bloom Color: "
    ),
    "glass": (
        "Glass stain: ",""
    ),
    "emissive": ("normal/ao/cavity: ", "emission: ", "color/metallic: "),
    "advanced_no_emi": (
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
        "Normal: ",
        "",
        "Mask: ",
        ""
    ),
    "alphaclip": (
        "Normal/AO/Roughness: ",
        "Alpha Mask: ",
        "Base Color/Metallic: "
    ),

    
    
}

#endregion

#region Functions: Miscellaneous

def PrettyPrint(msg, type="info"): # Inspired by FortnitePorting
    reset = u"\u001b[0m"
    color = reset
    match type:
        case "info":
            color = u"\u001b[36m"
        case "warn":
            color = u"\u001b[31m"
        case "error":
            color = u"\u001b[33m"
        case _:
            pass
    print(f"{color}[HD2TOOL]{reset} {msg}")

def DXGI_FORMAT(format):
    Dict = {0: "UNKNOWN", 1: "R32G32B32A32_TYPELESS", 2: "R32G32B32A32_FLOAT", 3: "R32G32B32A32_UINT", 4: "R32G32B32A32_SINT", 5: "R32G32B32_TYPELESS", 6: "R32G32B32_FLOAT", 7: "R32G32B32_UINT", 8: "R32G32B32_SINT", 9: "R16G16B16A16_TYPELESS", 10: "R16G16B16A16_FLOAT", 11: "R16G16B16A16_UNORM", 12: "R16G16B16A16_UINT", 13: "R16G16B16A16_SNORM", 14: "R16G16B16A16_SINT", 15: "R32G32_TYPELESS", 16: "R32G32_FLOAT", 17: "R32G32_UINT", 18: "R32G32_SINT", 19: "R32G8X24_TYPELESS", 20: "D32_FLOAT_S8X24_UINT", 21: "R32_FLOAT_X8X24_TYPELESS", 22: "X32_TYPELESS_G8X24_UINT", 23: "R10G10B10A2_TYPELESS", 24: "R10G10B10A2_UNORM", 25: "R10G10B10A2_UINT", 26: "R11G11B10_FLOAT", 27: "R8G8B8A8_TYPELESS", 28: "R8G8B8A8_UNORM", 29: "R8G8B8A8_UNORM_SRGB", 30: "R8G8B8A8_UINT", 31: "R8G8B8A8_SNORM", 32: "R8G8B8A8_SINT", 33: "R16G16_TYPELESS", 34: "R16G16_FLOAT", 35: "R16G16_UNORM", 36: "R16G16_UINT", 37: "R16G16_SNORM", 38: "R16G16_SINT", 39: "R32_TYPELESS", 40: "D32_FLOAT", 41: "R32_FLOAT", 42: "R32_UINT", 43: "R32_SINT", 44: "R24G8_TYPELESS", 45: "D24_UNORM_S8_UINT", 46: "R24_UNORM_X8_TYPELESS", 47: "X24_TYPELESS_G8_UINT", 48: "R8G8_TYPELESS", 49: "R8G8_UNORM", 50: "R8G8_UINT", 51: "R8G8_SNORM", 52: "R8G8_SINT", 53: "R16_TYPELESS", 54: "R16_FLOAT", 55: "D16_UNORM", 56: "R16_UNORM", 57: "R16_UINT", 58: "R16_SNORM", 59: "R16_SINT", 60: "R8_TYPELESS", 61: "R8_UNORM", 62: "R8_UINT", 63: "R8_SNORM", 64: "R8_SINT", 65: "A8_UNORM", 66: "R1_UNORM", 67: "R9G9B9E5_SHAREDEXP", 68: "R8G8_B8G8_UNORM", 69: "G8R8_G8B8_UNORM", 70: "BC1_TYPELESS", 71: "BC1_UNORM", 72: "BC1_UNORM_SRGB", 73: "BC2_TYPELESS", 74: "BC2_UNORM", 75: "BC2_UNORM_SRGB", 76: "BC3_TYPELESS", 77: "BC3_UNORM", 78: "BC3_UNORM_SRGB", 79: "BC4_TYPELESS", 80: "BC4_UNORM", 81: "BC4_SNORM", 82: "BC5_TYPELESS", 83: "BC5_UNORM", 84: "BC5_SNORM", 85: "B5G6R5_UNORM", 86: "B5G5R5A1_UNORM", 87: "B8G8R8A8_UNORM", 88: "B8G8R8X8_UNORM", 89: "R10G10B10_XR_BIAS_A2_UNORM", 90: "B8G8R8A8_TYPELESS", 91: "B8G8R8A8_UNORM_SRGB", 92: "B8G8R8X8_TYPELESS", 93: "B8G8R8X8_UNORM_SRGB", 94: "BC6H_TYPELESS", 95: "BC6H_UF16", 96: "BC6H_SF16", 97: "BC7_TYPELESS", 98: "BC7_UNORM", 99: "BC7_UNORM_SRGB", 100: "AYUV", 101: "Y410", 102: "Y416", 103: "NV12", 104: "P010", 105: "P016", 106: "420_OPAQUE", 107: "YUY2", 108: "Y210", 109: "Y216", 110: "NV11", 111: "AI44", 112: "IA44", 113: "P8", 114: "A8P8", 115: "B4G4R4A4_UNORM", 130: "P208", 131: "V208", 132: "V408"}
    return Dict[format]

def DXGI_FORMAT_SIZE(format):
    if format.find("BC1") != -1 or format.find("BC4") != -1:
        return 8
    elif format.find("BC") != -1:
        return 16
    else:
        raise Exception("Provided DDS' format is currently unsupported")

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

def duplicate(obj, data=True, actions=True, collection=None):
    obj_copy = obj.copy()
    if data:
        obj_copy.data = obj_copy.data.copy()
    if actions and obj_copy.animation_data:
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

def GetMeshData(og_object):
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
    for idx in range(len(object.material_slots)): materials[idx].IDFromName(object.material_slots[idx].name)

    # get vertex color
    if mesh.vertex_colors:
        color_layer = mesh.vertex_colors.active
        for face in object.data.polygons:
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
    LoadNormalPalette(Global_palettepath)
    normals = NormalsFromPalette(normals)
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
    if len(object.vertex_groups) > 0:
        for vertex in mesh.vertices:
            group_idx = 0
            for group in vertex.groups:
                # limit influences
                if group_idx >= numInfluences:
                    break
                if group.weight > 0.001:
                    vertex_group        = object.vertex_groups[group.group]
                    vertex_group_name   = vertex_group.name
                    parts               = vertex_group_name.split("_")
                    HDGroupIndex        = int(parts[0])
                    HDBoneIndex         = int(parts[1])
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

    bpy.data.objects.remove(object, do_unlink=True)
    return NewMesh

def GetObjectsMeshData():
    objects = bpy.context.selected_objects
    bpy.ops.object.select_all(action='DESELECT')
    data = []
    for object in objects:
        data.append(GetMeshData(object))
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
            if Hash32(bone_name) == mesh.MeshID:
                name = bone_name

    return name

def CreateModel(model, id, customization_info, bone_names):
    addon_prefs = AQ_PublicClass.get_addon_prefs()
    if len(model) < 1: return
    # Make collection
    old_collection = bpy.context.collection
    if bpy.context.scene.Hd2ToolPanelSettings.MakeCollections:
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
        PrettyPrint(f"scale: {mesh.DEV_Transform.scale}")
        PrettyPrint(f"location: {mesh.DEV_Transform.pos}")
        new_object.scale = (mesh.DEV_Transform.scale[0],mesh.DEV_Transform.scale[1],mesh.DEV_Transform.scale[2])
        new_object.location = (mesh.DEV_Transform.pos[0],mesh.DEV_Transform.pos[1],mesh.DEV_Transform.pos[2])

        # TODO: fix incorrect rotation
        rot = mesh.DEV_Transform.rot
        rotation_matrix = mathutils.Matrix([rot.x, rot.y, rot.z])
        new_object.rotation_mode = 'QUATERNION'
        new_object.rotation_quaternion = rotation_matrix.to_quaternion()

        # set object properties
        new_object["MeshInfoIndex"] = mesh.MeshInfoIndex
        new_object["BoneInfoIndex"] = mesh.LodIndex
        new_object["Z_ObjectID"]      = str(id)
        new_object["Z_SwapID"] = ""
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
        for vertex_idx in range(len(mesh.VertexWeights)):
            weights      = mesh.VertexWeights[vertex_idx]
            index_groups = [Indices[vertex_idx] for Indices in mesh.VertexBoneIndices]
            group_index  = 0
            for indices in index_groups:
                if bpy.context.scene.Hd2ToolPanelSettings.ImportGroup0 and group_index != 0:
                    continue
                if type(weights) != list:
                    weights = [weights]
                for weight_idx in range(len(weights)):
                    weight_value = weights[weight_idx]
                    bone_index   = indices[weight_idx]
                    #bone_index   = mesh.DEV_BoneInfo.GetRealIndex(bone_index)
                    group_name   = str(group_index) + "_" + str(bone_index)
                    if group_name not in created_groups:
                        created_groups.append(group_name)
                        new_vertex_group = new_object.vertex_groups.new(name=str(group_name))
                    vertex_group_data = [vertex_idx]
                    new_object.vertex_groups[str(group_name)].add(vertex_group_data, weight_value, 'ADD')
                group_index += 1
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
            try: new_object.data.materials.append(bpy.data.materials[material.MatID])
            except: raise Exception(f"Tool was unable to find material that this mesh uses, ID: {material.MatID}")
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
            


        # Create skeleton
        if False:
            if mesh.DEV_BoneInfo != None:
                for Bone in mesh.DEV_BoneInfo.Bones:
                    current_pos = [Bone.v[12], Bone.v[13], Bone.v[14]]
                    bpy.ops.object.empty_add(type='SPHERE', radius=0.08, align='WORLD', location=(current_pos[0], current_pos[1], current_pos[2]), scale=(1, 1, 1))

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
            if hash_info[1] != "" and int(hash_info[0]) == Hash64(hash_info[1]):
                string = str(hash_info[0]) + " " + str(hash_info[1])
                f.writelines(string+"\n")
    with open(Global_friendlynamespath, 'w') as f:
        for hash_info in Global_NameHashes:
            if hash_info[1] != "":
                string = str(hash_info[0]) + " " + str(hash_info[1])
                f.writelines(string+"\n")

def Hash32(string):
    output    = bytearray(4)
    c_output  = (ctypes.c_char * len(output)).from_buffer(output)
    Global_CPPHelper.dll_Hash32(c_output, string.encode())
    F = MemoryStream(output, IOMode = "read")
    return F.uint32(0)

def Hash64(string):
    output    = bytearray(8)
    c_output  = (ctypes.c_char * len(output)).from_buffer(output)
    Global_CPPHelper.dll_Hash64(c_output, string.encode())
    F = MemoryStream(output, IOMode = "read")
    return F.uint64(0)

#endregion

#region Functions: Initialization

def LoadNormalPalette(path):
    Global_CPPHelper.dll_LoadPalette(path.encode())

def NormalsFromPalette(normals):
    f = MemoryStream(IOMode = "write")
    normals = [f.vec3_float(normal) for normal in normals]
    output    = bytearray(len(normals)*4)
    c_normals = ctypes.c_char_p(bytes(f.Data))
    c_output  = (ctypes.c_char * len(output)).from_buffer(output)
    Global_CPPHelper.dll_NormalsFromPalette(c_output, c_normals, ctypes.c_uint32(len(normals)))
    F = MemoryStream(output, IOMode = "read")
    return [F.uint32(0) for normal in normals]

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

def LoadShaderVariables():
    global Global_ShaderVariables
    with open(Global_variablespath, 'r') as f:
        for line in f.readlines():
            Global_ShaderVariables[int(line.split()[1], 16)] = line.split()[0]
# 载入翻译
def LoadShaderVariables_CN():
    global Global_ShaderVariables_CN
    with open(Global_variablesCNpath, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            Global_ShaderVariables_CN[line.split()[1]] = line.split()[0]
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
#endregion

#region Configuration

def InitializeConfig():
    global Global_gamepath, Global_configpath
    if os.path.exists(Global_configpath):
        config = configparser.ConfigParser()
        config.read(Global_configpath, encoding='utf-8')
        try:
            Global_gamepath = config['DEFAULT']['filepath']
        except:
            UpdateConfig()
        PrettyPrint(f"Loaded Data Folder: {Global_gamepath}")

    else:
        UpdateConfig()

def UpdateConfig():
    global Global_gamepath, Global_defaultgamepath
    if Global_gamepath == "":
        Global_gamepath = Global_defaultgamepath
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
    def Serialize(self, TocFile, Index=0):
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
    def SerializeData(self, TocFile, GpuFile, StreamFile):
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
    def Load(self, Reload=False, MakeBlendObject=True):
        callback = None
        if self.TypeID == MeshID: callback = LoadStingrayMesh
        if self.TypeID == TexID: callback = LoadStingrayTexture
        if self.TypeID == MaterialID: callback = LoadStingrayMaterial
        if self.TypeID == CompositeMeshID: callback = LoadStingrayCompositeMesh
        if self.TypeID == Hash64("bones"): callback = LoadStingrayBones
        if callback != None:
            self.LoadedData = callback(self.FileID, self.TocData, self.GpuData, self.StreamData, Reload, MakeBlendObject)
            if self.LoadedData == None: raise Exception("Archive Entry Load Failed")
            self.IsLoaded   = True
            # if self.TypeID == MeshID and not self.IsModified:
            #     for object in bpy.data.objects:
            #         try:
            #             objectID = object["Z_ObjectID"]
            #             infoIndex = object["MeshInfoIndex"]
            #             if objectID == str(self.FileID):
            #                 PrettyPrint(f"Writing Vertex Groups for {object.name}")
            #                 vertexNames = []
            #                 for group in object.vertex_groups:
            #                     vertexNames.append(group.name)
            #                 newGroups = [objectID, infoIndex, vertexNames]
            #                 if newGroups not in self.VertexGroups:
            #                     self.VertexGroups.append(newGroups)
            #                 PrettyPrint(self.VertexGroups)
            #                 PrettyPrint(f"Writing Transforms for {object.name}")
            #                 transforms = []
            #                 transforms.append(object.location)
            #                 transforms.append(object.rotation_euler)
            #                 transforms.append(object.scale)
            #                 objectTransforms = [objectID, infoIndex, transforms]
            #                 if objectTransforms not in self.Transforms:
            #                     self.Transforms.append(objectTransforms)
            #                 PrettyPrint(self.Transforms)
            #         except:
            #             PrettyPrint(f"Object: {object.name} has No HD2 Properties")
    # -- Write Data -- #
    def Save(self):
        if not self.IsLoaded: self.Load(True, False)
        if self.TypeID == MeshID: callback = SaveStingrayMesh
        if self.TypeID == TexID: callback = SaveStingrayTexture
        if self.TypeID == MaterialID: callback = SaveStingrayMaterial
        if callback == None: raise Exception("Save Callback could not be found")

        if self.IsLoaded:
            data = callback(self.FileID, self.TocData, self.GpuData, self.StreamData, self.LoadedData)
            self.SetData(data[0], data[1], data[2])

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

        # Get search archives
        if len(self.SearchArchives) == 0:
            # for root, dirs, files in os.walk(Path(path).parent):
            #     for name in files:
            #         if Path(name).suffix == "":
            #             search_toc = StreamToc()
            #             success = search_toc.FromFile(os.path.join(root, name), False)
            #             if success:
            #                 self.SearchArchives.append(search_toc)
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
            raise Exception("No Archive exists to create patch from, please open one first")

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
            raise Exception("No patch exists, please create one first")
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

    def AddNewEntryToPatch(self, Entry):
        if self.ActivePatch == None:
            raise Exception("No patch exists, please create one first")
        self.ActivePatch.AddEntry(Entry)

    def AddEntryToPatch(self, FileID, TypeID):
        if self.ActivePatch == None:
            raise Exception("No patch exists, please create one first")

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

#region Classes and Functions: Stingray Materials
class ShaderVariable:
    klasses = {
        0: "Scalar",
        1: "Vector2",
        2: "Vector3",
        3: "Vector4",
        12: "Other"
    }

    def __init__(self):
        self.klass = self.klassName = self.elements = self.ID = self.offset = self.elementStride = 0
        self.values = []
        self.name = ""

class StingrayMaterial:
    def __init__(self):
        self.undat1 = self.undat3 = self.undat4 = self.undat5 = self.undat6 = self.RemainingData = bytearray()
        # self.EndOffset = self.undat2 = self.UnkID = self.NumTextures = self.NumUnk = 0
        self.EndOffset = self.undat2 = self.UnkID = self.NumTextures = self.NumVariables = self.VariableDataSize = 0
        self.TexUnks = []
        self.TexIDs  = []
        self.ShaderVariables = []

        self.DEV_ShowEditor = False
        self.DEV_DDSPaths = []
    def Serialize(self, f):
        self.undat1      = f.bytes(self.undat1, 12)
        self.EndOffset   = f.uint32(self.EndOffset)
        self.undat2      = f.uint64(self.undat2)
        self.UnkID       = f.uint64(self.UnkID) # could be shader id?
        self.undat3      = f.bytes(self.undat3, 32)
        self.NumTextures = f.uint32(self.NumTextures)
        self.undat4      = f.bytes(self.undat4, 36)
        # self.NumUnk      = f.uint32(self.NumUnk)
        # self.undat5      = f.bytes(self.undat5, 28)
        self.NumVariables= f.uint32(self.NumVariables)
        self.undat5      = f.bytes(self.undat5, 12)
        self.VariableDataSize = f.uint32(self.VariableDataSize)
        self.undat6      = f.bytes(self.undat6, 12)
        if f.IsReading():
            self.TexUnks = [0 for n in range(self.NumTextures)]
            self.TexIDs = [0 for n in range(self.NumTextures)]
            self.ShaderVariables = [ShaderVariable() for n in range(self.NumVariables)]
        self.TexUnks = [f.uint32(TexUnk) for TexUnk in self.TexUnks]
        self.TexIDs  = [f.uint64(TexID) for TexID in self.TexIDs]
    # ShaderVariables added
        for variable in self.ShaderVariables:
            variable.klass = f.uint32(variable.klass)
            variable.klassName = ShaderVariable.klasses[variable.klass]
            variable.elements = f.uint32(variable.elements)
            variable.ID = f.uint32(variable.ID)
            if variable.ID in Global_ShaderVariables:
                variable.name = Global_ShaderVariables[variable.ID]
            variable.offset = f.uint32(variable.offset)
            variable.elementStride = f.uint32(variable.elementStride)
            if f.IsReading():
                variable.values = [0 for n in range(variable.klass + 1)]  # Create an array with the length of the data which is one greater than the klass value

        variableValueLocation = f.Location # Record and add all of the extra data that is skipped around during the variable offsets

        if f.IsReading():self.RemainingData = f.bytes(self.RemainingData, len(f.Data) - f.tell())
        if f.IsWriting():self.RemainingData = f.bytes(self.RemainingData)
        
        f.Location = variableValueLocation

        for variable in self.ShaderVariables:
            oldLocation = f.Location
            f.Location = f.Location + variable.offset
            for idx in range(len(variable.values)):
                variable.values[idx] = f.float32(variable.values[idx])
            f.Location = oldLocation
            
        self.EditorUpdate()

    def EditorUpdate(self):
        self.DEV_DDSPaths = [None for n in range(len(self.TexIDs))]

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

def SaveStingrayMaterial(ID, TocData, GpuData, StreamData, LoadedData):
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

class StingrayMipmapInfo:
    def __init__(self):
        self.Start     = self.BytesLeft = self.Height = self.Width  = 0
    def Serialize(self, Toc):
        self.Start      = Toc.uint32(self.Start)
        self.BytesLeft  = Toc.uint32(self.BytesLeft)
        self.Height     = Toc.uint16(self.Height)
        self.Width      = Toc.uint16(self.Width)
        return self

class StingrayTexture:
    def __init__(self):
        self.UnkID = self.Unk1  = self.Unk2  = 0
        self.MipMapInfo = []

        self.ddsHeader = bytearray(148)
        self.rawTex    = b""

        self.Format     = ""
        self.Width      = 0
        self.Height     = 0
        self.NumMipMaps = 0
    def Serialize(self, Toc, Gpu, Stream):
        # clear header, so we dont have to deal with the .stream file
        if Toc.IsWriting():
            self.Unk1 = 0; self.Unk2  = 0xFFFFFFFF
            self.MipMapInfo = [StingrayMipmapInfo() for n in range(15)]

        self.UnkID = Toc.uint32(self.UnkID)
        self.Unk1  = Toc.uint32(self.Unk1)
        self.Unk2  = Toc.uint32(self.Unk2)
        if Toc.IsReading(): self.MipMapInfo = [StingrayMipmapInfo() for n in range(15)]
        self.MipMapInfo = [mipmapInfo.Serialize(Toc) for mipmapInfo in self.MipMapInfo]
        self.ddsHeader  = Toc.bytes(self.ddsHeader, 148)
        self.ParseDDSHeader()

        if Toc.IsWriting():
            Gpu.bytes(self.rawTex)
        else:# IsReading
            if len(Stream.Data) > 0:
                self.rawTex = Stream.Data
            else:
                self.rawTex = Gpu.Data

    def ToDDS(self):
        return self.ddsHeader + self.rawTex
    
    def FromDDS(self, dds):
        self.ddsHeader = dds[:148]
        self.rawTex    = dds[148::]
    
    def ParseDDSHeader(self):
        dds = MemoryStream(self.ddsHeader, IOMode="read")
        dds.seek(12)
        self.Height = dds.uint32(0)
        self.Width  = dds.uint32(0)
        dds.seek(28)
        self.NumMipMaps = dds.uint32(0)
        dds.seek(128)
        self.Format = DXGI_FORMAT(dds.uint32(0))
    
    def CalculateGpuMipmaps(self):
        Stride = DXGI_FORMAT_SIZE(self.Format) / 16
        start_mip = max(1, self.NumMipMaps-6)

        CurrentWidth = self.Width
        CurrentSize = int((self.Width*self.Width)*Stride)
        for mip in range(self.NumMipMaps-1):
            if mip+1 == start_mip:
                return CurrentSize

            if CurrentWidth > 4: CurrentWidth /= 2
            CurrentSize += int((CurrentWidth*CurrentWidth)*Stride)

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

def SaveStingrayTexture(ID, TocData, GpuData, StreamData, LoadedData):
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

class StingrayBones:
    def __init__(self):
        self.NumNames = self.NumUnk = 0
        self.UnkArray1 = []; UnkArray2 = []; UnkArray3 = []; self.Names = []
    def Serialize(self, f):
        self.NumNames = f.uint32(self.NumNames)
        self.NumUnk   = f.uint32(self.NumUnk)
        if f.IsReading():
            self.UnkArray1 = [0 for n in range(self.NumUnk)]
            self.UnkArray2 = [0 for n in range(self.NumNames)]
            self.UnkArray3 = [0 for n in range(self.NumUnk)]
        self.UnkArray1 = [f.uint32(value) for value in self.UnkArray1]
        self.UnkArray2 = [f.uint32(value) for value in self.UnkArray2]
        self.UnkArray3 = [f.uint32(value) for value in self.UnkArray3]
        if f.IsReading():
            Data = f.read().split(b"\x00")
            self.Names = [dat.decode() for dat in Data]
        else:
            Data = b""
            for string in self.Names:
                Data += string.encode() + b"\x00"
            f.write(Data)
        return self

def LoadStingrayBones(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    StingrayBonesData = StingrayBones()
    StingrayBonesData.Serialize(MemoryStream(TocData))
    return StingrayBonesData

#endregion

#region Classes and Functions: Stingray Composite Meshes

class StingrayCompositeMesh:
    def __init__(self):
        self.unk1 = self.NumExternalMeshes = self.StreamInfoOffset = 0
        self.Unreversed = bytearray()
        self.NumStreams = 0
        self.StreamInfoArray = []
        self.StreamInfoOffsets = []
        self.StreamInfoUnk = []
        self.StreamInfoUnk2 = 0
        self.GpuData = None
    def Serialize(self, f, gpu):
        self.unk1               = f.uint64(self.unk1)
        self.NumExternalMeshes  = f.uint32(self.NumExternalMeshes)
        self.StreamInfoOffset   = f.uint32(self.StreamInfoOffset)
        if f.IsReading():
            self.Unreversed = bytearray(self.StreamInfoOffset-f.tell())
        self.Unreversed     = f.bytes(self.Unreversed)

        if f.IsReading(): f.seek(self.StreamInfoOffset)
        else:
            f.seek(ceil(float(f.tell())/16)*16); self.StreamInfoOffset = f.tell()
        self.NumStreams = f.uint32(len(self.StreamInfoArray))
        if f.IsWriting():
            if not redo_offsets: self.StreamInfoOffsets = [0 for n in range(self.NumStreams)] #type: ignore
            else: self.StreamInfoOffsets = [f.tell() for n in range(self.NumStreams)]
            self.StreamInfoUnk = [mesh_info.MeshID for mesh_info in self.MeshInfoArray[:self.NumStreams]]
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

def LoadStingrayCompositeMesh(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    StingrayCompositeMeshData = StingrayCompositeMesh()
    StingrayCompositeMeshData.Serialize(MemoryStream(TocData), MemoryStream(GpuData))
    return StingrayCompositeMeshData

#endregion

#region Classes and Functions: Stingray Meshes

class StingrayMatrix4x4: # Matrix4x4: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_89
    def __init__(self):
        self.v = [float(0)]*16
    def Serialize(self, f):
        self.v = [f.float32(value) for value in self.v]
        return self

class StingrayMatrix3x3: # Matrix3x3: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_84
    def __init__(self):
        self.x = [0,0,0]
        self.y = [0,0,0]
        self.z = [0,0,0]
    def Serialize(self, f):
        self.x = f.vec3_float(self.x)
        self.y = f.vec3_float(self.x)
        self.z = f.vec3_float(self.x)
        return self

class StingrayLocalTransform: # Stingray Local Transform: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_100
    def __init__(self):
        self.rot   = StingrayMatrix3x3()
        self.pos   = [0,0,0]
        self.scale = [1,1,1]
        self.dummy = 0 # Force 16 byte alignment
    def Serialize(self, f):
        self.rot    = self.rot.Serialize(f)
        self.pos    = f.vec3_float(self.pos)
        self.scale  = f.vec3_float(self.scale)
        self.dummy  = f.float32(self.dummy)
        return self
    def SerializeV2(self, f): # Quick and dirty solution, unknown exactly what this is for
        f.seek(f.tell()+48)
        self.pos    = f.vec3_float(self.pos)
        self.dummy  = f.float32(self.dummy)
        return self

class TransformInfo: # READ ONLY
    def __init__(self):
        self.NumTransforms = 0
        self.Transforms = []
        self.PositionTransforms = []
    def Serialize(self, f):
        if f.IsWriting():
            raise Exception("This struct is read only (write not implemented)")
        self.NumTransforms = f.uint32(self.NumTransforms)
        f.seek(f.tell()+12)
        self.Transforms = [StingrayLocalTransform().Serialize(f) for n in range(self.NumTransforms)]
        self.PositionTransforms = [StingrayLocalTransform().SerializeV2(f) for n in range(self.NumTransforms)]
        for n in range(self.NumTransforms):
            self.Transforms[n].pos = self.PositionTransforms[n].pos

class CustomizationInfo: # READ ONLY
    def __init__(self):
        self.BodyType  = ""
        self.Slot      = ""
        self.Weight    = ""
        self.PieceType = ""
    def Serialize(self, f):
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

class StreamComponentInfo:
    def __init__(self, type="position", format="float"):
        self.Type   = self.TypeFromName(type)
        self.Format = self.FormatFromName(format)
        self.Index   = 0
        self.Unknown = 0
    def Serialize(self, f):
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
    def SerializeComponent(self, f, value):
        try:
            serialize_func = FUNCTION_LUTS.SERIALIZE_COMPONENT_LUT[self.Format]
            return serialize_func(f, value)
        except:
            raise Exception("Cannot serialize unknown vertex format: "+str(self.Format))

class BoneInfo:
    def __init__(self):
        self.NumBones = self.unk1 = self.RealIndicesOffset = self.FakeIndicesOffset = self.NumFakeIndices = self.FakeIndicesUnk = 0
        self.Bones = self.RealIndices = self.FakeIndices = []
        self.DEV_RawData = bytearray()
    def Serialize(self, f, end=None):
        if f.IsReading():
            self.DEV_RawData = bytearray(end-f.tell())
            start = f.tell()
            self.Serialize_REAL(f)
            f.seek(start)
        self.DEV_RawData = f.bytes(self.DEV_RawData)
        return self

    def Serialize_REAL(self, f): # still need to figure out whats up with the unknown bit
        RelPosition = f.tell()

        self.NumBones       = f.uint32(self.NumBones)
        self.unk1           = f.uint32(self.unk1)
        self.RealIndicesOffset = f.uint32(self.RealIndicesOffset)
        self.FakeIndicesOffset = f.uint32(self.FakeIndicesOffset)
        # get bone data
        if f.IsReading():
            self.Bones = [StingrayMatrix4x4() for n in range(self.NumBones)]
            self.RealIndices = [0 for n in range(self.NumBones)]
            self.FakeIndices = [0 for n in range(self.NumBones)]
        self.Bones = [bone.Serialize(f) for bone in self.Bones]
        # get real indices
        if f.IsReading(): f.seek(RelPosition+self.RealIndicesOffset)
        else            : self.RealIndicesOffset = f.tell()-RelPosition
        self.RealIndices = [f.uint32(index) for index in self.RealIndices]
        # get unknown
        return self

        # get fake indices
        if f.IsReading(): f.seek(RelPosition+self.FakeIndicesOffset)
        else            : self.FakeIndicesOffset = f.tell()-RelPosition
        self.NumFakeIndices = f.uint32(self.NumFakeIndices)
        self.FakeIndicesUnk = f.uint64(self.FakeIndices[0])
        self.FakeIndices = [f.uint32(index) for index in self.FakeIndices]
        return self
    def GetRealIndex(self, bone_index):
        FakeIndex = self.FakeIndices.index(bone_index)
        return self.RealIndices[FakeIndex]

class StreamInfo:
    def __init__(self):
        self.Components = []
        self.ComponentInfoID = self.NumComponents = self.VertexBufferID = self.VertexBuffer_unk1 = self.NumVertices = self.VertexStride = self.VertexBuffer_unk2 = self.VertexBuffer_unk3 = 0
        self.IndexBufferID = self.IndexBuffer_unk1 = self.NumIndices = self.IndexBuffer_unk2 = self.IndexBuffer_unk3 = self.IndexBuffer_Type = self.VertexBufferOffset = self.VertexBufferSize = self.IndexBufferOffset = self.IndexBufferSize = 0
        self.VertexBufferOffset = self.VertexBufferSize = self.IndexBufferOffset = self.IndexBufferSize = 0
        self.UnkEndingBytes = bytearray(16)
        self.DEV_StreamInfoOffset    = self.DEV_ComponentInfoOffset = 0 # helper vars, not in file

    def Serialize(self, f):
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

class MeshSectionInfo:
    def __init__(self, ID=0):
        self.unk1 = self.VertexOffset=self.NumVertices=self.IndexOffset=self.NumIndices=self.unk2 = 0
        self.DEV_MeshInfoOffset=0 # helper var, not in file
        self.ID = ID
    def Serialize(self, f):
        self.DEV_MeshInfoOffset = f.tell()
        self.unk1           = f.uint32(self.unk1)
        self.VertexOffset   = f.uint32(self.VertexOffset)
        self.NumVertices    = f.uint32(self.NumVertices)
        self.IndexOffset    = f.uint32(self.IndexOffset)
        self.NumIndices     = f.uint32(self.NumIndices)
        self.unk2           = f.uint32(self.unk1)
        return self

class MeshInfo:
    def __init__(self):
        self.unk1 = self.unk3 = self.unk4 = self.TransformIndex = self.LodIndex = self.StreamIndex = self.NumSections = self.unk7 = self.unk8 = self.unk9 = self.NumSections_unk = self.MeshID = 0
        self.unk2 = bytearray(32); self.unk6 = bytearray(40)
        self.SectionIDs = self.Sections = []
    def Serialize(self, f):
        self.unk1 = f.uint64(self.unk1)
        self.unk2 = f.bytes(self.unk2, 32)
        self.MeshID= f.uint32(self.MeshID)
        self.unk3 = f.uint32(self.unk3)
        self.TransformIndex = f.uint32(self.TransformIndex)
        self.unk4 = f.uint32(self.unk4)
        self.LodIndex       = f.int32(self.LodIndex)
        self.StreamIndex    = f.uint32(self.StreamIndex)
        self.unk6           = f.bytes(self.unk6, 40)
        self.NumSections_unk= f.uint32(len(self.Sections))
        self.unk7           = f.uint32(0x80)
        self.unk8           = f.uint64(self.unk8)
        self.NumSections    = f.uint32(len(self.Sections))
        self.unk9           = f.uint32(0x80+(len(self.Sections)*4))
        if f.IsReading(): self.SectionIDs  = [0 for n in range(self.NumSections)]
        else:             self.SectionIDs  = [section.ID for section in self.Sections]
        self.SectionIDs  = [f.uint32(ID) for ID in self.SectionIDs]
        if f.IsReading(): self.Sections    = [MeshSectionInfo(self.SectionIDs[n]) for n in range(self.NumSections)]
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
    def IDFromName(self, name):
        if name.find(self.DefaultMaterialName) != -1:
            self.MatID   = self.DefaultMaterialName
            self.ShortID = self.DefaultMaterialShortID
        else:
            try:
                self.MatID   = int(name)
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
        self.MeshID           = 0
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

class SerializeFunctions:

    def SerializePositionComponent(gpu, mesh, component, vidx):
        mesh.VertexPositions[vidx] = component.SerializeComponent(gpu, mesh.VertexPositions[vidx])

    def SerializeNormalComponent(gpu, mesh, component, vidx):
        norm = component.SerializeComponent(gpu, mesh.VertexNormals[vidx])
        if gpu.IsReading():
            if not isinstance(norm, int):
                norm = list(mathutils.Vector((norm[0],norm[1],norm[2])).normalized())
                mesh.VertexNormals[vidx] = norm[:3]
            else:
                mesh.VertexNormals[vidx] = norm

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
            raise Exception(f"Vertex bone index out of range. Component index: {component.Index} vidx: {vidx}")

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
    # -- Serialize Mesh -- #
    def Serialize(self, f, gpu, redo_offsets = False):
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
                for Material in Raw_Mesh.Materials:
                    Section = MeshSectionInfo()
                    Section.ID          = int(Material.ShortID)
                    Section.NumIndices  = Material.NumIndices
                    Section.VertexOffset  = Order # | Used for ordering function
                    Section.IndexOffset   = Order # /

                    # This doesnt do what it was intended to do
                    if Material.DEV_BoneInfoOverride != None:
                        PrettyPrint("Overriding unknown material values")
                        Section.unk1 = Material.DEV_BoneInfoOverride
                        Section.unk2 = Material.DEV_BoneInfoOverride
                    else:
                        Section.unk1 = len(Mesh_info.Sections) # | dont know what these actually are, but this is usually correct it seems
                        Section.unk2 = len(Mesh_info.Sections) # /

                    Mesh_info.Sections.append(Section)
                    Order -= 1
                    try: # if material ID uses the defualt material string it will throw an error, but thats fine as we dont want to include those ones anyway
                        #if int(Material.MatID) not in self.MaterialIDs:
                        self.MaterialIDs.append(int(Material.MatID))
                        self.SectionsIDs.append(int(Material.ShortID))
                    except:
                        pass

        # serialize file
        self.UnkRef1            = f.uint64(self.UnkRef1)
        self.BonesRef           = f.uint64(self.BonesRef)
        self.CompositeRef       = f.uint64(self.CompositeRef)
        self.HeaderData1        = f.bytes(self.HeaderData1, 28)
        self.TransformInfoOffset= f.uint32(self.TransformInfoOffset)
        self.HeaderData2        = f.bytes(self.HeaderData2, 20)
        self.CustomizationInfoOffset  = f.uint32(self.CustomizationInfoOffset)
        self.UnkHeaderOffset1   = f.uint32(self.UnkHeaderOffset1)
        self.UnkHeaderOffset2   = f.uint32(self.UnkHeaderOffset1)
        self.BoneInfoOffset     = f.uint32(self.BoneInfoOffset)
        self.StreamInfoOffset   = f.uint32(self.StreamInfoOffset)
        self.EndingOffset       = f.uint32(self.EndingOffset)
        self.MeshInfoOffset     = f.uint32(self.MeshInfoOffset)
        self.HeaderUnk          = f.uint64(self.HeaderUnk)
        self.MaterialsOffset    = f.uint32(self.MaterialsOffset)

        if f.IsReading() and self.MeshInfoOffset == 0:
            raise Exception("Unsuported Mesh Format (No geometry)")

        if f.IsReading() and (self.StreamInfoOffset == 0 and self.CompositeRef == 0):
            raise Exception("Unsuported Mesh Format (No buffer stream)")

        # Get composite file
        if f.IsReading() and self.CompositeRef != 0:
            Entry = Global_TocManager.GetEntry(self.CompositeRef, CompositeMeshID)
            if Entry != None:
                Global_TocManager.Load(Entry.FileID, Entry.TypeID)
                self.StreamInfoArray = Entry.LoadedData.StreamInfoArray
                gpu = Entry.LoadedData.GpuData
            else:
                raise Exception(f"Composite mesh file {self.CompositeRef} could not be found")

        # Get bones file
        if f.IsReading() and self.BonesRef != 0:
            Entry = Global_TocManager.GetEntry(self.BonesRef, Hash64("bones"))
            if Entry != None:
                Global_TocManager.Load(Entry.FileID, Entry.TypeID)
                self.BoneNames = Entry.LoadedData.Names

        # Get Customization data: READ ONLY
        if f.IsReading() and self.CustomizationInfoOffset > 0:
            loc = f.tell(); f.seek(self.CustomizationInfoOffset)
            self.CustomizationInfo.Serialize(f)
            f.seek(loc)
        # Get Transform data: READ ONLY
        if f.IsReading() and self.TransformInfoOffset > 0:
            loc = f.tell(); f.seek(self.TransformInfoOffset)
            self.TransformInfo.Serialize(f)
            f.seek(loc)

        # Unreversed data
        if f.IsReading():
            if self.BoneInfoOffset > 0:
                UnreversedData1Size = self.BoneInfoOffset-f.tell()
            elif self.StreamInfoOffset > 0:
                UnreversedData1Size = self.StreamInfoOffset-f.tell()
        else: UnreversedData1Size = len(self.UnReversedData1)
        self.UnReversedData1    = f.bytes(self.UnReversedData1, UnreversedData1Size)

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

        # Stream Info
        if self.StreamInfoOffset != 0:
            if f.IsReading(): f.seek(self.StreamInfoOffset)
            else:
                f.seek(ceil(float(f.tell())/16)*16); self.StreamInfoOffset = f.tell()
            self.NumStreams = f.uint32(len(self.StreamInfoArray))
            if f.IsWriting():
                if not redo_offsets: self.StreamInfoOffsets = [0]*self.NumStreams
                self.StreamInfoUnk = [mesh_info.MeshID for mesh_info in self.MeshInfoArray[:self.NumStreams]]
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
            self.MeshInfoUnk = [mesh_info.MeshID for mesh_info in self.MeshInfoArray]
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

        # Materials
        if f.IsReading(): f.seek(self.MaterialsOffset)
        else            : self.MaterialsOffset = f.tell()
        self.NumMaterials = f.uint32(len(self.MaterialIDs))
        if f.IsReading():
            self.SectionsIDs = [0]*self.NumMaterials
            self.MaterialIDs = [0]*self.NumMaterials
        self.SectionsIDs = [f.uint32(ID) for ID in self.SectionsIDs]
        self.MaterialIDs = [f.uint64(ID) for ID in self.MaterialIDs]

        # Unreversed Data
        if f.IsReading(): UnreversedData2Size = self.EndingOffset-f.tell()
        else: UnreversedData2Size = len(self.UnReversedData2)
        self.UnReversedData2    = f.bytes(self.UnReversedData2, UnreversedData2Size)
        if f.IsWriting(): self.EndingOffset = f.tell()
        self.EndingBytes        = f.uint64(self.NumMeshes)
        if redo_offsets:
            return self

        # Serialize Data
        self.SerializeGpuData(gpu);

        # TODO: update offsets only instead of re-writing entire file
        if f.IsWriting() and not redo_offsets:
            f.seek(0)
            self.Serialize(f, gpu, True)
        return self

    def SerializeGpuData(self, gpu):
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
                self.SerializeIndexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
                self.SerializeVertexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
            else:
                self.SerializeVertexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
                self.SerializeIndexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)

    def SerializeIndexBuffer(self, gpu, Stream_Info, stream_idx, OrderedMeshes):
        # get indices
        IndexOffset  = 0
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
            for Section in Mesh_Info.Sections:
                # Create mat info
                if gpu.IsReading():
                    mat = RawMaterialClass()
                    if Section.ID in self.SectionsIDs:
                        mat_idx = self.SectionsIDs.index(Section.ID)
                        mat.IDFromName(str(self.MaterialIDs[mat_idx]))
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
                    # v1 = IndexInt(mesh.Indices[TotalIndex][0])
                    # v2 = IndexInt(mesh.Indices[TotalIndex][1])
                    # v3 = IndexInt(mesh.Indices[TotalIndex][2])
                    # mesh.Indices[TotalIndex] = [v1, v2, v3]
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

    def SerializeVertexBuffer(self, gpu, Stream_Info, stream_idx, OrderedMeshes):
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
        # man this code is ass, there has to be a better way to do this, but i am stupid af frfr no cap
        OrderedMeshes = [ [[], []] for n in range(len(self.StreamInfoArray))]
        VertOrderedMeshes_flat = []
        IndexOrderedMeshes_flat = []
        while len(VertOrderedMeshes_flat) != len(self.RawMeshes):
            smallest_vert_mesh = None
            smallest_index_mesh = None
            for mesh in self.RawMeshes:
                mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
                if mesh not in VertOrderedMeshes_flat:
                    if smallest_vert_mesh == None:
                        smallest_vert_mesh = mesh
                    else:
                        smallest_mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[smallest_vert_mesh.MeshInfoIndex]]
                        if mesh_info.Sections[0].VertexOffset < smallest_mesh_info.Sections[0].VertexOffset:
                            smallest_vert_mesh = mesh

                if mesh not in IndexOrderedMeshes_flat:
                    if smallest_index_mesh == None:
                        smallest_index_mesh = mesh
                    else:
                        smallest_mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[smallest_index_mesh.MeshInfoIndex]]
                        if mesh_info.Sections[0].IndexOffset < smallest_mesh_info.Sections[0].IndexOffset:
                            smallest_index_mesh = mesh
            mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[smallest_vert_mesh.MeshInfoIndex]]
            OrderedMeshes[mesh_info.StreamIndex][0].append(smallest_vert_mesh)
            mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[smallest_index_mesh.MeshInfoIndex]]
            OrderedMeshes[mesh_info.StreamIndex][1].append(smallest_index_mesh)
            VertOrderedMeshes_flat.append(smallest_vert_mesh)
            IndexOrderedMeshes_flat.append(smallest_index_mesh)

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
            # print("Num: ", len(self.StreamInfoArray), " Index: ", Mesh_Info.StreamIndex)
            indexerror = Mesh_Info.StreamIndex >= len(self.StreamInfoArray)
            messageerror = "ERROR" if indexerror else "INFO"
            message = "Stream index out of bounds" if indexerror else ""
            PrettyPrint(f"Num: {len(self.StreamInfoArray)} Index: {Mesh_Info.StreamIndex}    {message}", messageerror)
            if indexerror: continue
            
            Stream_Info = self.StreamInfoArray[Mesh_Info.StreamIndex]
            NewMesh.MeshInfoIndex = n
            NewMesh.MeshID = Mesh_Info.MeshID
            NewMesh.DEV_Transform = self.TransformInfo.Transforms[Mesh_Info.TransformIndex]
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
            if NumUVs < 2 and bpy.context.scene.Hd2ToolPanelSettings.Force2UVs:
                NumUVs = 2
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

def LoadStingrayMesh(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    toc  = MemoryStream(TocData)
    gpu  = MemoryStream(GpuData)
    StingrayMesh = StingrayMeshFile().Serialize(toc, gpu)
    if MakeBlendObject: CreateModel(StingrayMesh.RawMeshes, str(ID), StingrayMesh.CustomizationInfo, StingrayMesh.BoneNames)
    return StingrayMesh

def SaveStingrayMesh(ID, TocData, GpuData, StreamData, StingrayMesh):
    model = GetObjectsMeshData()
    FinalMeshes = [mesh for mesh in StingrayMesh.RawMeshes]
    for mesh in model:
        for n in range(len(StingrayMesh.RawMeshes)):
            if StingrayMesh.RawMeshes[n].MeshInfoIndex == mesh.MeshInfoIndex:
                FinalMeshes[n] = mesh
    if bpy.context.scene.Hd2ToolPanelSettings.AutoLods:
        lod0 = None
        for mesh in FinalMeshes:
            if mesh.LodIndex == 0:
                lod0 = mesh
        # print(lod0)
        if lod0 != None:
            for n in range(len(FinalMeshes)):
                if FinalMeshes[n].IsLod():
                    newmesh = copy.copy(lod0)
                    newmesh.MeshInfoIndex = FinalMeshes[n].MeshInfoIndex
                    FinalMeshes[n] = newmesh
    StingrayMesh.RawMeshes = FinalMeshes
    toc  = MemoryStream(IOMode = "write")
    gpu  = MemoryStream(IOMode = "write")
    StingrayMesh.Serialize(toc, gpu)
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

#region Operators: Context Menu
class CopyArchiveIDOperator(Operator):
    bl_label = "Copy Archive ID"
    bl_idname = "helldiver2.copy_archive_id"
    bl_description = "将活跃的 Archive ID 复制到剪贴板"

    def execute(self, context):
        if ArchivesNotLoaded(self):
            return {'CANCELLED'}
        archiveID = str(Global_TocManager.ActiveArchive.Name)
        bpy.context.window_manager.clipboard = archiveID
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

#endregion

#region Operators: Archives & Patches
def ArchivesNotLoaded(self):
    if len(Global_TocManager.LoadedArchives) <= 0:
        self.report({'ERROR'}, "No Archives Currently Loaded")
        return True
    else: 
        return False


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
            if obj.type != "MESH":
                
                continue
            try:
                ObjectID = obj["Z_ObjectID"]
            except:
                continue
            try:
                obj["Z_SwapID"]
            except:
                pass
            else:
                continue
            
            if ObjectID  !=  None:
                obj["Z_SwapID"] = ""
                add_count += 1
                
        self.report({'INFO'}, f"总共为选择的物体添加{add_count}个空交换ID属性")        
        
        return {'FINISHED'}
    
    
    
    
    

    
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
                Global_TocManager.Load(EntryID, MeshID)
            else:
                try:
                    Global_TocManager.Load(EntryID, MeshID)
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

    object_id: StringProperty()
    def execute(self, context):
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        object = bpy.context.active_object
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
        
        SwapID = ""
        try:
            SwapID = object["Z_SwapID"]
            if SwapID != "" and not SwapID.isnumeric():
                self.report({"ERROR"}, f"Object: {object.name} 的转换ID: {SwapID} 不是纯数字.")
                return {'CANCELLED'}
        except:
            pass
            # self.report({'INFO'}, f"{obj.name} has no HD2 Swap ID. Skipping Swap.")
        Global_TocManager.Save(int(self.object_id), MeshID)
        
        if SwapID != "" and SwapID.isnumeric():
            Entry = Global_TocManager.GetPatchEntry_B(int(ID), MeshID)
            self.report({'INFO'}, f"转移 Entry ID: {Entry.FileID} to: {SwapID}")
            Global_TocManager.RemoveEntryFromPatch(int(SwapID), MeshID)
            Entry.FileID = int(SwapID)
        
        return{'FINISHED'}

class BatchSaveStingrayMeshOperator(Operator):
    bl_label  = "Save Meshes"
    bl_idname = "helldiver2.archive_mesh_batchsave"

    def execute(self, context):
        objects = bpy.context.selected_objects
        addon_prefs = AQ_PublicClass.get_addon_prefs()
        if addon_prefs.SaveUseAutoSmooth:
            for i in objects:
                if i.type == "MESH":
                    # 4.3 compatibility change
                    if bpy.app.version[0] >= 4 and bpy.app.version[1] >= 1:
                        i.data.shade_auto_smooth(use_auto_smooth=True)
                    else:
                        i.data.use_auto_smooth = True
                        i.data.auto_smooth_angle = 3.14159
        bpy.ops.object.select_all(action='DESELECT')
        
        IDs = []
        for object in objects:
            SwapID = ""
            try:
                ID = object["Z_ObjectID"]
                try:
                    SwapID = object["Z_SwapID"]
                    PrettyPrint(f"Found Swap of ID: {ID} Swap: {SwapID}")
                    if SwapID != "" and not SwapID.isnumeric():
                        self.report({"ERROR"}, f"Object: {object.name} 的转换ID: {SwapID} 不是纯数字.")
                        return {'CANCELLED'}
                    
                except:
                    pass
                IDitem = [ID, SwapID]
                if IDitem not in IDs:
                    IDs.append(IDitem)
                    
            except:
                pass
        for IDitem in IDs:
            ID = IDitem[0]
            SwapID = IDitem[1]
            for object in objects:
                try:
                    if object["Z_ObjectID"] == ID:
                       object.select_set(True)
                except: pass

            Global_TocManager.Save(int(ID), MeshID)
            
            if SwapID != "" :
                Entry = Global_TocManager.GetPatchEntry_B(int(ID), MeshID)
                self.report({'INFO'}, f"转移 Entry ID: {Entry.FileID} to: {SwapID}")
                Global_TocManager.RemoveEntryFromPatch(int(SwapID), MeshID)
                Entry.FileID = int(SwapID)
                
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

    object_id: StringProperty()
    def execute(self, context):
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

    materials = (
        ("bloom", "Bloom", "A bloom material with two color, normal map which does not render in the UI"),
        ("original", "Original", "The original template used for all mods uploaded to Nexus prior to the addon's public release, which is bloated with additional unnecessary textures. Sourced from a terminid."),
        ("advanced_no_emi", "Advanced 无光", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),   
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

        ("flowing","流光","光能电塔的流光材质"),
        ("glass", "透明玻璃", "透明玻璃，不知道能干嘛，自己猜()"),
        ("basic+Fixed", "Basic+", "A basic material with a color, normal, and PBR map which renders in the UI, Sourced from a SEAF NPC"),
        ("basic", "Basic", "A basic material with a color, normal, and PBR map. Sourced from a trash bag prop."),
        ("emissive", "Emissive", "A basic material with a color, normal, and emission map. Sourced from a vending machine."),
        ("alphaclip", "Alpha Clip", "金属度在颜色贴图的alpha通道，A material that supports an alpha mask which does not render in the UI. Sourced from a skeleton pile")
    )

    selected_material: EnumProperty(items=materials, name="Template", default=1)

    def execute(self, context):
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
        if Hash64(str(self.NewFriendlyName)) == int(self.object_id):
            row.label(text="Hash is correct")
        else:
            row.label(text="Hash is incorrect")
        row.label(text=str(Hash64(str(self.NewFriendlyName))))

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

#region Menus and Panels

def LoadedArchives_callback(scene, context):
    items = [(Archive.Name,Archive.Name , "") for Archive in Global_TocManager.LoadedArchives]
    return items

def Patches_callback(scene, context):
    return [(Archive.Name, Archive.Name, Archive.Name ) for Archive in Global_TocManager.Patches]

class Hd2ToolPanelSettings(PropertyGroup):
    # Patches
    Patches   : EnumProperty(name="Patches", items=Patches_callback)
    PatchOnly : BoolProperty(name="Show Patch Entries Only", description = "Filter list to entries present in current patch", default = False)
    # Archive
    ContentsExpanded : BoolProperty(default = True)
    LoadedArchives   : EnumProperty(name="LoadedArchives", items=LoadedArchives_callback)
    # Settings
    MenuExpanded     : BoolProperty(default = False)
    ShowMeshes       : BoolProperty(name="Meshes", description = "Show Meshes", default = True)
    ShowTextures     : BoolProperty(name="Textures", description = "Show Textures", default = True)
    ShowMaterials    : BoolProperty(name="Materials", description = "Show Materials", default = True)
    ShowOthers       : BoolProperty(name="Other", description = "Show All Else", default = False)
    ImportMaterials  : BoolProperty(name="Import Materials", description = "Fully import materials by appending the textures utilized, otherwise create placeholders", default = True)
    ImportLods       : BoolProperty(name="Import LODs", description = "Import LODs", default = False)
    ImportGroup0     : BoolProperty(name="Import Group 0 Only", description = "Only import the first vertex group, ignore others", default = True)
    ImportPhysics    : BoolProperty(name="Import Physics", description = "Import Physics Bodies", default = False)
    # ImportStatic     : BoolProperty(name="Import Static Meshes", description = "Import Static Meshes", default = False)
    MakeCollections  : BoolProperty(name="Make Collections", description = "Make new collection when importing meshes", default = True)
    Force2UVs        : BoolProperty(name="Force 2 UV Sets", description = "Force at least 2 UV sets, some materials require this", default = True)
    Force1Group      : BoolProperty(name="Force 1 Group", description = "Force mesh to only have 1 vertex group", default = True)
    AutoLods         : BoolProperty(name="Auto LODs", description = "Automatically generate LOD entries based on LOD0, does not actually reduce the quality of the mesh", default = True)
    RemoveGoreMeshes : BoolProperty(name="Remove Gore Meshes", description = "Automatically delete all of the verticies with the gore material when loading a model", default = True)
    shadervariablesUI : BoolProperty(name="Shader Variables UI", description = "显示着色器变量参数UI", default = True)
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
                icon_only=True, emboss=False, text="着色器变量参数栏")
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
        if Entry.TypeID == MeshID:
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
            row.prop(scene.Hd2ToolPanelSettings, "ShowMeshes")
            row.prop(scene.Hd2ToolPanelSettings, "ShowTextures")
            row.prop(scene.Hd2ToolPanelSettings, "ShowMaterials")
            row.prop(scene.Hd2ToolPanelSettings, "ShowOthers")
            row.prop(addon_prefs, "ShowArchivePatchPath",text="实时显示Archive和Patch路径")
            row.prop(addon_prefs,"Layout_search_New",text="显示搜索已知Archive为主的布局")
            row = layout.row(); row.separator(); row.label(text="导入设置"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "ImportMaterials",text="导入材质")
            row.prop(scene.Hd2ToolPanelSettings, "ImportLods",text="导入Lods")
            row.prop(scene.Hd2ToolPanelSettings, "ImportGroup0",text="只导入Group 0")
            row.prop(scene.Hd2ToolPanelSettings, "MakeCollections",text="为每个物体创建集合")
            row.prop(scene.Hd2ToolPanelSettings, "ImportPhysics",text="导入物理")
            row.prop(addon_prefs, "ImportStatic",text="导入静态网格（无权重）")
            row.prop(scene.Hd2ToolPanelSettings, "RemoveGoreMeshes",text="删除断肢网格")
            row.prop(addon_prefs, "ShadeSmooth",text="导入模型时平滑着色")
            row.prop(addon_prefs, "tga_Tex_Import_Switch",text="开启TGA纹理导入")
            row.prop(addon_prefs, "png_Tex_Import_Switch",text="开启PNG纹理导入")
            row = layout.row(); row.separator(); row.label(text="Export Options"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "Force2UVs")
            row.prop(scene.Hd2ToolPanelSettings, "Force1Group")
            row.prop(scene.Hd2ToolPanelSettings, "AutoLods")
            row.prop(addon_prefs,"SaveUseAutoSmooth",text="保存网格时开启自动平滑")
            row.prop(addon_prefs,"ShowZipPatchButton",text="显示打包Patch为Zip功能")
            row.prop(addon_prefs,"DisplayRenameButton",text="显示重命名按钮")
            
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
                if Type.TypeID == MeshID:
                    type_icon = 'FILE_3D'
                    if not scene.Hd2ToolPanelSettings.ShowMeshes: continue
                elif Type.TypeID == TexID:
                    type_icon = 'FILE_IMAGE'
                    if not scene.Hd2ToolPanelSettings.ShowTextures: continue
                elif Type.TypeID == MaterialID:
                    type_icon = 'MATERIAL'
                    if not scene.Hd2ToolPanelSettings.ShowMaterials: continue
                elif not scene.Hd2ToolPanelSettings.ShowOthers: continue

                for section in Global_Foldouts:
                    if section[0] == str(Type.TypeID):
                        show = section[1]
                        break
                if show == None:
                    fold = False
                    if Type.TypeID == MaterialID or Type.TypeID == TexID or Type.TypeID == MeshID: fold = True
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
            if SelectedEntry.TypeID == MeshID:
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
    
)

Global_TocManager = TocManager()

def register():
    if Global_CPPHelper == None: raise Exception("HDTool_Helper is required by the addon but failed to load!")
    LoadNormalPalette(Global_palettepath)
    LoadTypeHashes()
    LoadNameHashes()
    LoadShaderVariables()
    LoadShaderVariables_CN()
    LoadUpdateArchiveList_CN()
    InitializeConfig()
    for cls in classes:
        bpy.utils.register_class(cls)
    Scene.Hd2ToolPanelSettings = PointerProperty(type=Hd2ToolPanelSettings)
    bpy.utils.register_class(WM_MT_button_context)
    addonPreferences.register()
    addon_updater_ops.register(bl_info)

def unregister():
    bpy.utils.unregister_class(WM_MT_button_context)
    del Scene.Hd2ToolPanelSettings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    addonPreferences.unregister()
    addon_updater_ops.unregister()

if __name__=="__main__":
    register()
