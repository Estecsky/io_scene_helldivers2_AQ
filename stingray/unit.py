from math import ceil, sqrt # type: ignore

import mathutils
import bpy
import random
import bmesh

from ..utils.memoryStream import MemoryStream, MakeTenBitUnsigned, TenBitUnsigned
from ..utils.logger import PrettyPrint
from .hash import murmur32_hash