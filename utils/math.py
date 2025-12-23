def InsureBitLength(bits, length):
    # cut off if to big
    if len(bits) > length:
        bits = bits[:length]
    # add to start if to small
    newbits = str().ljust(length-len(bits),"0")
    return newbits + bits

def TenBitSigned(U32):
    X = (U32 & 1023)
    Y = ((U32 >> 10) & 1023)
    Z = ((U32 >> 20) & 1023)
    W = (U32 >> 30)
    v = [((X - 511) / 512), ((Y - 511) / 512), ((Z - 511) / 512), W / 3]
    return v

def TenBitUnsigned(U32):
    X = (U32 & 1023)
    Y = ((U32 >> 10) & 1023)
    Z = ((U32 >> 20) & 1023)
    W = (U32 >> 30)
    v = [(X / 1023), (Y  / 1023), (Z  / 1023), W / 3]
    return v

def MakeTenBitUnsigned(vec):
    x = vec[0];y = vec[1];z = vec[2]
    x *= 1024; y *= 1024; z *= 1024
    xbin = bin(int(x))[2:]; ybin = bin(int(y))[2:]; zbin = bin(int(z))[2:]
    xbin = InsureBitLength(xbin, 10); ybin = InsureBitLength(ybin, 10); zbin = InsureBitLength(zbin, 10);
    binary = InsureBitLength(zbin+ybin+xbin, 32)
    return int(binary, 2)

def MakeTenBitSigned(vec):
    x = vec[0];y = vec[1];z = vec[2]
    x = (abs(x)*512); y =(abs(y)*512); z =(abs(z)*512)
    # add bias
    if vec[0] < 0:
        x = abs(x-511)
    else:
        x += 511
    if vec[1] < 0:
        y = abs(y-511)
    else:
        y += 511
    if vec[2] < 0:
        z = abs(z-511)
    else:
        z += 511
    xbin = bin(int(x))[2:]; ybin = bin(int(y))[2:]; zbin = bin(int(z))[2:]
    xbin = InsureBitLength(xbin, 10); ybin = InsureBitLength(ybin, 10); zbin = InsureBitLength(zbin, 10);
    binary = InsureBitLength(zbin+ybin+xbin, 32)
    return int(binary, 2)