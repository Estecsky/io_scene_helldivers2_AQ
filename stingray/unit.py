from math import ceil, sqrt # type: ignore

import mathutils
import bpy
import random
import bmesh

from ..memoryStream import MemoryStream, MakeTenBitUnsigned, TenBitUnsigned
from ..logger import PrettyPrint
from .hash import murmur32_hash