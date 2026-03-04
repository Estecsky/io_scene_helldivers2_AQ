import bpy, bpy_types
from math import ceil, sqrt, isnan, floor
import mathutils

from ..utils.logger import PrettyPrint
from ..utils.memoryStream import MemoryStream

class AnimationException(Exception):
    pass

class AnimationEntry:
    def __init__(self):
        self.type = 0
        self.subtype = 0
        self.bone = 0
        self.time = 0
        self.data = []
        self.data2 = []
        
    def Serialize(self, tocFile):
        if tocFile.IsReading():
            self.load(tocFile)
        else:
            self.save(tocFile)
            
    def load(self, tocFile):
        # load header
        data = [0, 0, 0, 0]
        bone = 0
        time = 0
        timeMs = 0
        temp = 0
        temp_arr = []
        subtype = 0
        data = tocFile.vec4_uint8(data)
        type = (data[1] & 0xC0) >> 6
        if type == 0:
            tocFile.seek(tocFile.tell()-4)
            subtype = tocFile.uint16(subtype)
            if subtype != 3:
                bone = tocFile.uint32(bone)
                time = tocFile.float32(time) * 1000
        else:
            bone = ((data[0] & 0xf0) >> 4) | ((data[1] & 0x3f) << 4)
            time = ((data[0] & 0xf) << 16) | (data[3] << 8) | data[2]
            
        if type == 3:
            data2 = AnimationBoneInitialState.decompress_rotation(tocFile.uint32(temp))
            # rotation data
        elif type == 2:
            # position data
            data2 = AnimationBoneInitialState.decompress_position([tocFile.uint16(temp) for _ in range(3)])
        elif type == 1:
            # scale data
            data2 = AnimationBoneInitialState.decompress_scale([tocFile.uint16(temp) for _ in range(3)])
        else:
            if subtype == 4:
                # position data (uncompressed)
                data2 = tocFile.vec3_float(temp_arr)
            elif subtype == 5:
                # rotation data (uncompressed)
                data2 = [tocFile.float32(temp) for _ in range(4)]
            elif subtype == 6:
                # scale data (uncompressed)
                data2 = tocFile.vec3_float(temp_arr)
            elif subtype == 2: # triggers sounds?
                data2 = bytearray()
            else:
                PrettyPrint(f"Unknown type/subtype! {type}/{subtype}")
                self.subtype = subtype
                self.type = type
                return
        self.data2 = data2
        self.data = data
        self.bone = bone
        self.subtype = subtype
        self.type = type
        self.time = time
        
    def save(self, tocFile):
        # load header
        data = [0, 0, 0, 0]
        bone = 0
        time = 0
        timeMs = 0
        temp = 0
        temp_arr = []
        subtype = 0
        #data = tocFile.vec4_uint8(self.data)
        new_data = [0, 0, 0, 0]
        new_data[1] |= (self.type << 6) & 0xC0
        #type = (data[1] & 0xC0) >> 6
        
        if self.type == 0:
            #tocFile.seek(tocFile.tell()-4)
            subtype = tocFile.uint16(self.subtype)
            if subtype != 3:
                bone = tocFile.uint32(self.bone)
                time = tocFile.float32(self.time/1000)
        else:
            new_data[0] |= (self.bone << 4) & 0xf0
            new_data[1] |= (self.bone >> 4) & 0x3f
            #bone = ((data[0] & 0xf0) >> 4) | ((data[1] & 0x3f) << 4)
            new_data[0] |= (self.time >> 16) & 0xf
            new_data[3] = (self.time >> 8) & 0xff
            new_data[2] = (self.time & 0xff)
            #time = ((data[0] & 0xf) << 16) | (data[3] << 8) | data[2]
            tocFile.vec4_uint8(new_data)
            
            
        if self.type == 3:
           # data2 = AnimationBoneInitialState.compress_rotation(tocFile.uint32(temp))
            tocFile.uint32(AnimationBoneInitialState.compress_rotation(self.data2))
            # rotation data
        elif self.type == 2:
            # position data
            #data2 = AnimationBoneInitialState.decompress_position([tocFile.uint16(temp) for _ in range(3)])
            data2 = AnimationBoneInitialState.compress_position(self.data2)
            for value in data2:
                tocFile.uint16(value)
        elif self.type == 1:
            # scale data
            #data2 = AnimationBoneInitialState.decompress_scale(tocFile.vec3_float(temp_arr))
            data2 = AnimationBoneInitialState.compress_scale(self.data2)
            for value in data2:
                tocFile.uint16(value)
        else:
            if subtype == 4:
                # position data (uncompressed)
                tocFile.vec3_float(self.data2)
                #data2 = tocFile.vec3_float(temp_arr)
            elif subtype == 5:
                # rotation data (uncompressed)
                for value in self.data2:
                    tocFile.float32(value)
                #data2 = [tocFile.float32(temp) for _ in range(4)]
            elif subtype == 6:
                # scale data (uncompressed)
                #data2 = tocFile.vec3_float(temp_arr)
                tocFile.vec3_float(self.data2)
            elif subtype == 2: # triggers sounds?
                pass
 
    
class AnimationBoneInitialState:
    def __init__(self):
        self.compressed_position = True
        self.compressed_rotation = True
        self.compressed_scale = True
        self.position = [0, 0, 0]
        self.rotation = [0, 0, 0, 0]
        self.scale = [1, 1, 1]
        
    def compress_position(position):
        return [int((pos * 3276.7) + 32767.0) for pos in position]
        
    def compress_rotation(rotation):
        if max(rotation) == rotation[0]:
            largest_idx = 0
        if max(rotation) == rotation[1]:
            largest_idx = 1
        if max(rotation) == rotation[2]:
            largest_idx = 2
        if max(rotation) == rotation[3]:
            largest_idx = 3
        cmp_rotation = 0
        first = rotation[(largest_idx+1)%4]
        first = int(((first / 0.75) * 512) + 512)
        cmp_rotation |= ((first & 0x3ff) << 2)
        second = rotation[(largest_idx+2)%4]
        second = int(((second / 0.75) * 512) + 512)
        cmp_rotation |= ((second & 0x3ff) << 12)
        third = rotation[(largest_idx+3)%4]
        third = int(((third / 0.75) * 512) + 512)
        cmp_rotation |= ((third & 0x3ff) << 22)
        cmp_rotation |= largest_idx
        return cmp_rotation
        
    def compress_scale(scale):
        return AnimationBoneInitialState.compress_position(scale)
        
    def decompress_position(position): # vector of 3 uint16 -> vector of 3 float32
        return [(pos - 32767.0) * (10.0/32767.0) for pos in position]
        
    def decompress_rotation(rotation): # uint32 -> vector of 4 float32
        first = (((rotation & 0xffc) >> 2) - 512.0) / 512.0 * 0.75
        second = (((rotation & 0x3ff000) >> 12) - 512.0) / 512.0 * 0.75
        third = (((rotation & 0xffc00000) >> 22) - 512.0) / 512.0 * 0.75
        largest_idx = rotation & 0x3
        largest_val = sqrt(1 - third**2 - second**2 - first**2)
        if largest_idx == 0:
            return [largest_val, first, second, third]
        elif largest_idx == 1:
            return [third, largest_val, first, second]
        elif largest_idx == 2:
            return [second, third, largest_val, first]
        elif largest_idx == 3:
            return [first, second, third, largest_val]
        
    def decompress_scale(scale):
        return AnimationBoneInitialState.decompress_position(scale)
        
    def __repr__(self):
        s = ""
        s += f"Position {self.position} Rotation {self.rotation} Scale {self.scale}"
        return s
        
class BitArray:
    def __init__(self, data=bytearray()):
        self.data = []
        for b in data:
            for x in reversed(range(8)):
                self.data.append((b >> x) & 1)
        
    def get(self, index):
        return self.data[index]
        
    def to_hex(self):
        hex_string = ""
        for x in range(int(len(self.data)/4)):
            slice = self.data[(x*4):(x*4)+4]
            val = 0
            for x in range(4):
                bit = slice[x]
                if bit:
                    val += 1
                if x != 3:
                    val = val << 1
            hex_string += hex(val)[2]
        return hex_string
            
class StingrayAnimation:
    
    def __init__(self):
        self.initial_bone_states = []
        self.entries = []
        self.hashes = []
        self.hashes2 = []
        self.hashes_floats = []
        self.hashes_count = 0
        self.hashes2_count = 0
        self.unk = 0
        self.unk2 = 0
        self.bone_count = 0
        self.animation_length = 0
        self.file_size = 0
        self.is_additive_animation = False
        
    def Serialize(self, tocFile):
        if tocFile.IsReading():
            self.load(tocFile)
        else:
            self.save(tocFile)
        
    def load(self, tocFile):
        temp = 0
        temp_arr = []
        self.unk = tocFile.uint32(temp)
        self.bone_count = tocFile.uint32(temp)
        self.animation_length = tocFile.float32(temp)
        self.file_size = tocFile.uint32(temp)
        self.hashes_count = tocFile.uint32(temp)
        self.hashes2_count = tocFile.uint32(temp)
        self.hashes = []
        for _ in range(self.hashes_count):
            self.hashes.append(tocFile.uint64(temp))
        self.hashes2 = []
        for _ in range(self.hashes2_count):
            self.hashes2.append(tocFile.uint64(temp))
        self.unk2 = tocFile.uint16(temp)
        num_bytes = ceil(3 * self.bone_count / 8)
        if num_bytes % 2 == 1:
            num_bytes += 1
        byte_data = tocFile.bytes(temp_arr, size=num_bytes)
        self.byte_data = bytearray(byte_data)
        for x in range(len(byte_data)):
            byte_value = byte_data[x]
            reversed_byte = 0
            for i in range(8):
                if (byte_value >> i) & 1:
                    reversed_byte |= (1 << (7 - i))
            byte_data[x] = reversed_byte
        bit_array = BitArray(byte_data)
        for x in range(self.bone_count):
            bone_state = AnimationBoneInitialState()
            bone_state.compress_position = bit_array.get(x*3)
            bone_state.compress_rotation = bit_array.get(x*3+1)
            bone_state.compress_scale = bit_array.get(x*3+2)
            if bone_state.compress_position:
                bone_state.position = AnimationBoneInitialState.decompress_position([tocFile.uint16(temp) for _ in range(3)])
            else:
                bone_state.position = tocFile.vec3_float(temp_arr)
            if bone_state.compress_rotation:
                bone_state.rotation = AnimationBoneInitialState.decompress_rotation(tocFile.uint32(temp))
            else:
                bone_state.rotation = [tocFile.float32(temp) for _ in range(4)]
            if bone_state.compress_scale:
                bone_state.scale = AnimationBoneInitialState.decompress_scale([tocFile.uint16(temp) for _ in range(3)])
            else:
                bone_state.scale = tocFile.vec3_float(temp_arr)
            self.initial_bone_states.append(bone_state)
        for _ in range(self.hashes_count):
            self.hashes_floats.append(tocFile.float32(temp))
        count = 1
        while tocFile.uint16(temp) != 3:
            count += 1
            tocFile.seek(tocFile.tell()-2)
            entry = AnimationEntry()
            entry.Serialize(tocFile)
            if not (entry.type == 0 and entry.subtype not in [2, 4, 5, 6]):
                self.entries.append(entry)
        for initial_state in self.initial_bone_states:
            if initial_state.scale[0] == 0:
                self.is_additive_animation = True
                break
        
        
    def save(self, tocFile):
        temp = 0
        temp_arr = []
        tocFile.uint32(self.unk)
        tocFile.uint32(self.bone_count)
        tocFile.float32(self.animation_length)
        tocFile.uint32(self.file_size)
        tocFile.uint32(self.hashes_count)
        tocFile.uint32(self.hashes2_count)
        for value in self.hashes:
            tocFile.uint64(value)
        for value in self.hashes2:
            tocFile.uint64(value)
        tocFile.uint16(self.unk2)
        bit_arr = []
        for bone_state in self.initial_bone_states:
            bit_arr.append(bone_state.compress_position)
            bit_arr.append(bone_state.compress_rotation)
            bit_arr.append(bone_state.compress_scale)
        while len(bit_arr) % 8 != 0:
            bit_arr.append(0)
        bit_array = BitArray()
        bit_array.data = bit_arr
        hex_val = bit_array.to_hex()
        byte_data = bytearray.fromhex(hex_val)
        for x in range(len(byte_data)):
            byte_value = byte_data[x]
            reversed_byte = 0
            for i in range(8):
                if (byte_value >> i) & 1:
                    reversed_byte |= (1 << (7 - i))
            byte_data[x] = reversed_byte
        #bit_array = BitArray(byte_data)
        tocFile.bytes(byte_data)
        if tocFile.tell() % 2 == 1:
            tocFile.seek(tocFile.tell()+1)
        for bone_state in self.initial_bone_states:
            if bone_state.compress_position:
                for pos in AnimationBoneInitialState.compress_position(bone_state.position):
                    tocFile.uint16(pos)
            else:
                tocFile.vec3_float(bone_state.position)
            if bone_state.compress_rotation:
                tocFile.uint32(AnimationBoneInitialState.compress_rotation(bone_state.rotation))
            else:
                for value in bone_state.rotation:
                    tocFile.float32(value)
            if bone_state.compress_scale:
                for s in AnimationBoneInitialState.compress_scale(bone_state.scale):
                    tocFile.uint16(s)
            else:
                tocFile.vec3_float(bone_state.scale)
        for value in self.hashes_floats:
            tocFile.float32(value)
        count = 1
        for entry in self.entries:
            count += 1
            entry.Serialize(tocFile)
        tocFile.uint16(0x03)
        size = tocFile.uint32(tocFile.tell())
        
        # repeat for some reason
        tocFile.uint32(self.unk)
        tocFile.uint32(self.bone_count)
        tocFile.float32(self.animation_length)
        #tocFile.uint32(self.file_size)
        tocFile.seek(tocFile.tell()+4)
        tocFile.uint32(self.hashes_count)
        tocFile.uint32(self.hashes2_count)
        for value in self.hashes:
            tocFile.uint64(value)
        for value in self.hashes2:
            tocFile.uint64(value)
        tocFile.uint16(self.unk2)
        tocFile.bytes(byte_data)
        if tocFile.tell() % 2 == 1:
            tocFile.seek(tocFile.tell()+1)
        for bone_state in self.initial_bone_states:
            if bone_state.compress_position:
                for pos in AnimationBoneInitialState.compress_position(bone_state.position):
                    tocFile.uint16(pos)
            else:
                tocFile.vec3_float(bone_state.position)
            if bone_state.compress_rotation:
                tocFile.uint32(AnimationBoneInitialState.compress_rotation(bone_state.rotation))
            else:
                for value in bone_state.rotation:
                    tocFile.float32(value)
            if bone_state.compress_scale:
                for s in AnimationBoneInitialState.compress_scale(bone_state.scale):
                    tocFile.uint16(s)
            else:
                tocFile.vec3_float(bone_state.scale)
        for value in self.hashes_floats:
            tocFile.float32(value)
        count = 1
        for entry in self.entries:
            count += 1
            entry.Serialize(tocFile)
        tocFile.uint16(0x03)
        tocFile.uint32(size)
        
    def remove_bone(self, bone_index):
        self.initial_bone_states.pop(bone_index)
        self.bone_count -= 1
        self.entries = [entry for entry in self.entries if entry.bone != bone_index]
        for entry in self.entries:
            if entry.bone > bone_index:
                entry.bone -= 1
        output_stream = MemoryStream(IOMode="write")
        self.Serialize(output_stream)
        self.file_size = len(output_stream.Data)
        
    def add_bone(self, bone):
        initial_state = AnimationBoneInitialState()
        initial_state.compress_position = 0
        initial_state.compress_rotation = 0
        initial_state.compress_scale = 0
        if bone.parent:
            translation, rotation, scale = (bone.parent.matrix.inverted() @ bone.matrix).decompose()
        else:
            translation, rotation, scale = bone.matrix.decompose()
        initial_state.position = translation.to_tuple()
        initial_state.rotation = [0, 0, 0, 1]
        initial_state.scale = [1, 1, 1] if not self.is_additive_animation else [0, 0, 0]
        self.initial_bone_states.append(initial_state)
        self.bone_count += 1
        output_stream = MemoryStream(IOMode="write")
        self.Serialize(output_stream)
        self.file_size = len(output_stream.Data)

    def load_from_armature(self, context, armature, bones_data):
        #if self.is_additive_animation:
        #    raise AnimationException("Saving additive animations is not yet supported")
        #self.entries.clear()
        self.entries = [entry for entry in self.entries if (entry.type == 0 and entry.subtype == 2)]
        print(len(self.entries))
        self.initial_bone_states.clear()
        action = armature.animation_data.action
        idx = bones_data.index(b"StingrayEntityRoot")
        temp = bones_data[idx:]
        splits = temp.split(b"\x00")
        bone_names = []
        for item in splits:
            if item != b'':
                bone_names.append(item.decode('utf-8'))
        bone_to_index = {bone: bone_names.index(bone) for bone in bone_names}
        index_to_bone = bone_names
        initial_bone_data = {}
        bpy.ops.object.mode_set(mode="POSE")
        start, end = action.frame_range
        
        context.scene.frame_set(0)
        # initial bone data = anim frame 0
        
        for bone in armature.pose.bones:
            if self.is_additive_animation:
                mat = bone.matrix_basis
            else:
                if bone.parent is not None:
                    mat = (bone.parent.matrix.inverted() @ bone.matrix)
                else:
                    mat = bone.matrix
            position, rotation, scale = mat.decompose()
            rotation = (rotation[1], rotation[2], rotation[3], rotation[0])
            position = list(position)
            scale = list(scale)
            initial_bone_data[bone.name] = {'position': position, 'rotation': rotation, 'scale': scale}
            
        for bone_name in bone_names:
            try:
                bone = initial_bone_data[bone_name]
                initial_state = AnimationBoneInitialState()
                initial_state.compress_position = 0
                initial_state.compress_rotation = 0
                initial_state.compress_scale = 0
                initial_state.position = bone['position']
                initial_state.rotation = bone['rotation']
                initial_state.scale = [1, 1, 1] if not self.is_additive_animation else [0, 0, 0]
                self.initial_bone_states.append(initial_state)
            except KeyError:
                initial_state = AnimationBoneInitialState()
                initial_state.compress_position = 0
                initial_state.compress_rotation = 0
                initial_state.compress_scale = 0
                initial_state.position = [0, 0, 0]
                initial_state.rotation = [0, 0, 0, 1]
                initial_state.scale = [1, 1, 1] if not self.is_additive_animation else [0, 0, 0]
                self.initial_bone_states.append(initial_state)

        for frame in range(1, ceil(end)+1):
            context.scene.frame_set(frame)
            for bone in armature.pose.bones:
                if bone.name not in bone_names:
                    continue
                if self.is_additive_animation:
                    local_transform = bone.matrix_basis
                else:
                    if bone.parent:
                        local_transform = bone.parent.matrix.inverted() @ bone.matrix
                    else:
                        local_transform = bone.matrix
                translation, rotation, scale = local_transform.decompose()
                
                # save translation
                if context.scene.Hd2ToolPanelSettings.SaveBonePositions:
                    new_entry = AnimationEntry()
                    new_entry.bone = bone_to_index[bone.name]
                    new_entry.type = 0
                    new_entry.subtype = 4
                    new_entry.data2 = list(translation)
                    new_entry.time =  int(1000 * frame / 30)
                    self.entries.append(new_entry)
                    
                # save rotation
                new_entry = AnimationEntry()
                new_entry.bone = bone_to_index[bone.name]
                new_entry.type = 0
                new_entry.subtype = 5
                new_entry.data2 = [rotation.x, rotation.y, rotation.z, rotation.w]
                new_entry.time =  int(1000 * frame / 30)
                self.entries.append(new_entry)

        length_frames = end - start
        self.entries = sorted(self.entries, key=lambda e: e.time)            
        self.animation_length = length_frames / 30
        self.bone_count = len(self.initial_bone_states)
        bpy.ops.object.mode_set(mode="OBJECT")
        context.scene.frame_end = ceil(length_frames)
        
        output_stream = MemoryStream(IOMode="write")
        self.Serialize(output_stream)
        self.file_size = len(output_stream.Data)

    def to_action(self, context, armature, bones_data, state_machine_data, animation_id):
        
        idx = bones_data.index(b"StingrayEntityRoot")
        temp = bones_data[idx:]
        splits = temp.split(b"\x00")
        bone_names = []
        for item in splits:
            if item != b'':
                bone_names.append(item.decode('utf-8'))
        if int(animation_id) not in state_machine_data.animation_ids:
            raise AnimationException("This animation is not for this armature")
        blend_mask_index = -1
        layer_num = -1
        for i, layer in enumerate(state_machine_data.layers):
            for state in layer.states:
                if int(animation_id) in state.animation_ids:
                    blend_mask_index = state.blend_mask_index
                    layer_num = i
        #if len(self.initial_bone_states) != int.from_bytes(bones_data[0:4], "little"):
        #    raise AnimationException("This animation is not for this armature")
        action_name = f"{animation_id} (blend mask {blend_mask_index}) (layer {layer_num})"
        if blend_mask_index == 0xFFFFFFFF:
            action_name = f"{animation_id} (no blend mask) (layer {layer_num})"
        
        PrettyPrint(f"Creaing action with ID: {animation_id}")
        actions = bpy.data.actions
        action = actions.new(action_name)
        action.use_fake_user = True
        armature.animation_data.action = action
        bone_to_index = {bone: bone_names.index(bone) for bone in bone_names}
        index_to_bone = bone_names
        initial_bone_data = {}
        bpy.ops.object.mode_set(mode="EDIT")
        
        inverted_rest_poses = {
            bone.name: (bone.parent.matrix.inverted() @ bone.matrix).inverted() if bone.parent != None else bone.matrix.inverted() for bone in armature.data.edit_bones 
        }
        
        bpy.ops.object.mode_set(mode="POSE")
        additive_animation = self.is_additive_animation

        # initial state
        for bone_index, initial_state in enumerate(self.initial_bone_states):
            bone_name = index_to_bone[bone_index]
            try:
                bone = armature.pose.bones[bone_name]
            except KeyError:
                PrettyPrint(f"Failed to find bone: {bone_name} in rig for animation. This may be intended", 'warn')
                continue
            translation = mathutils.Vector(initial_state.position)
            rotation = mathutils.Quaternion([initial_state.rotation[3], initial_state.rotation[0], initial_state.rotation[1], initial_state.rotation[2]])
            scale = None
            matrix = mathutils.Matrix.LocRotScale(translation, rotation, scale)
            if additive_animation:
                bone.matrix_basis = matrix
            else:
                bone.matrix_basis = inverted_rest_poses[bone.name] @ matrix
            bone.keyframe_insert(data_path=f"location", frame=0, group=bone.name)
            bone.keyframe_insert(data_path=f"rotation_quaternion", frame=0, group=bone.name)
            
        # entries
        length_frames = 0
        for entry in self.entries:
            if entry.type not in [2, 3] and entry.subtype not in [4, 5]: # skip scale entries
                continue
            bone_name = index_to_bone[entry.bone]
            if bone_name not in armature.pose.bones:
                PrettyPrint(f"Failed to find bone: {bone_name} in rig for animation. This may be intended", 'warn')
                continue
            bone = armature.pose.bones[bone_name]
            frame = 30 * entry.time / 1000
            length_frames = max(length_frames, frame)
            data_path = ""
            translation = rotation = scale = None
            if entry.type == 2 or entry.subtype == 4: # position
                translation = mathutils.Vector(entry.data2)
                data_path = "location"
            elif entry.type == 3 or entry.subtype == 5: # rotation
                rotation = mathutils.Quaternion([entry.data2[3], entry.data2[0], entry.data2[1], entry.data2[2]])
                data_path = "rotation_quaternion"
            matrix = mathutils.Matrix.LocRotScale(translation, rotation, scale)
            if additive_animation:
                bone.matrix_basis = matrix
            else:
                bone.matrix_basis = inverted_rest_poses[bone.name] @ matrix
            bone.keyframe_insert(data_path=data_path, frame=frame, group=bone.name)
        
        bpy.ops.screen.animation_cancel(restore_frame=False)        
        bpy.ops.screen.animation_play()
        context.scene.frame_end = ceil(length_frames)
        context.scene.frame_start = 0
        context.scene.render.fps = 30
        bpy.ops.object.mode_set(mode="POSE")

