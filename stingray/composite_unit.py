from math import ceil
from ..utils.memoryStream import MemoryStream
from .unit import StreamInfo, MeshSectionInfo


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