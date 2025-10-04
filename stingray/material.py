import os
from ..memoryStream import MemoryStream

Global_ShaderVariables = {}
Global_ShaderVariables_CN = {}


class StingrayMaterial:
    def __init__(self):
        self.undat1 = self.undat3 = self.undat4 = self.undat5 = self.undat6 = self.RemainingData = bytearray()
        # self.EndOffset = self.undat2 = self.UnkID = self.NumTextures = self.NumUnk = 0
        self.EndOffset = self.undat2 = self.ParentMaterialID = self.NumTextures = self.NumVariables = self.VariableDataSize = 0
        self.TexUnks = []
        self.TexIDs  = []
        self.ShaderVariables = []

        self.DEV_ShowEditor = False
        self.DEV_DDSPaths = []
    def Serialize(self, f):
        self.undat1      = f.bytes(self.undat1, 12)
        self.EndOffset   = f.uint32(self.EndOffset)
        self.undat2      = f.uint64(self.undat2)
        self.ParentMaterialID = f.uint64(self.ParentMaterialID)
        self.undat3      = f.bytes(self.undat3, 32)
        self.NumTextures = f.uint32(self.NumTextures)
        self.undat4      = f.bytes(self.undat4, 36)
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

 
def LoadShaderVariables(path):
    global Global_ShaderVariables
    with open(path, 'r') as f:
        for line in f.readlines():
            Global_ShaderVariables[int(line.split()[1], 16)] = line.split()[0]
# 载入翻译
def LoadShaderVariables_CN(path):
    global Global_ShaderVariables_CN
    with open(path, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            Global_ShaderVariables_CN[line.split()[1]] = line.split()[0]