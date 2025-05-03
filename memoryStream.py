import struct

class MemoryStream:
    def __init__(self, Data=b"", IOMode = "read"):
        self.Location = 0
        self.Data = bytearray(Data)
        if IOMode == "read":
            self.reading = True
        else:
            self.reading = False

    def open(self, Data, IOMode = "read"): # Open Stream
        self.Data = bytearray(Data)
        if IOMode == "read":
            self.reading = True
        else:
            self.reading = False

    def SetReadMode(self):
        self.reading = True

    def SetWriteMode(self):
        self.reading = False

    def IsReading(self):
        return self.reading

    def IsWriting(self):
        return not self.reading

    def seek(self, Location): # Go To Position In Stream
        self.Location = Location
        if self.Location > len(self.Data):
            missing_bytes = self.Location - len(self.Data)
            self.Data.extend(bytearray(missing_bytes))

    def tell(self): # Get Position In Stream
        return self.Location

    def read(self, length=-1): # Read Bytes From Stream
        if length == -1:
            length = len(self.Data) - self.Location
        if self.Location + length > len(self.Data):
            raise Exception("reading past end of stream")

        newData = self.Data[self.Location:self.Location+length]
        self.Location += length
        return bytes(newData)

    def write(self, bytes): # Write Bytes To Stream
        length = len(bytes)
        self.Data[self.Location:self.Location+length] = bytes
        self.Location += length

    def serialize(self, value, format, size):
        if self.reading:
            return struct.unpack(format, self.read(size))[0]
        else:
            self.write(struct.pack(format, value))
            return value

    def int8(self, value):
        return self.serialize(value, '<b', 1)

    def uint8(self, value):
        return self.serialize(value, '<B', 1)

    def int16(self, value):
        return self.serialize(value, '<h', 2)

    def uint16(self, value):
        return self.serialize(value, '<H', 2)

    def int32(self, value):
        return self.serialize(value, '<i', 4)

    def uint32(self, value):
        return self.serialize(value, '<I', 4)

    def int64(self, value):
        return self.serialize(value, '<q', 8)

    def uint64(self, value):
        return self.serialize(value, '<Q', 8)

    def float16(self, value):
        return self.serialize(value, '<e', 2)

    def float32(self, value):
        return self.serialize(value, '<f', 4)

    def float64(self, value):
        return self.serialize(value, '<d', 8)

    def __resize_vec(self, value, length):
        assert len(value) == length, "MISMATCHED LENGTH"
        value = list(value)
        if len(value) < length:
            dif = length - len(value)
            value.extend([0]*dif)
        if len(value) > length:
            value = value[:length]
        return value
    
    def vec2_float(self, value):
        return [self.float32(value[0]), self.float32(value[1])]

    def vec3_float(self, value):
        return [self.float32(value[0]), self.float32(value[1]), self.float32(value[2])]

    def vec2_half(self, value):
        return [self.float16(value[0]), self.float16(value[1])]

    def vec3_half(self, value):
        return [self.float16(value[0]), self.float16(value[1]), self.float16(value[2])]

    def vec4_half(self, value):
        return [self.float16(value[0]), self.float16(value[1]), self.float16(value[2]), self.float16(value[3])]

    def vec4_uint8(self, value):
        return [self.uint8(value[0]), self.uint8(value[1]), self.uint8(value[2]), self.uint8(value[3])]

    def vec4_uint16(self, value):
        return [self.uint16(value[0]), self.uint16(value[1]), self.uint16(value[2]), self.uint16(value[3])]

    def vec4_uint32(self, value):
        return [self.uint32(value[0]), self.uint32(value[1]), self.uint32(value[2]), self.uint32(value[3])]

    def array(self, type, value, size = -1):
        if size == -1:
            size = len(value)
        if len(value) != size:
            value = range(size)

        for n in range(size):
            value[n] = type()
        return value

    def bytes(self, value, size = -1):
        if size == -1:
            size = len(value)
        if len(value) != size:
            value = bytearray(size)

        if self.reading:
            return bytearray(self.read(size))
        else:
            self.write(value)
            return bytearray(value)
        return value