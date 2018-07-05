from enum import Enum
import json
import os

class AccessorType(Enum):
    SCALAR = 'SCALAR'
    VEC2 = 'VEC2'
    VEC3 = 'VEC3'
    VEC4 = 'VEC4'
    MAT2 = 'MAT2'
    MAT3 = 'MAT3'
    MAT4 = 'MAT4'

class AccessorComponentType(Enum):
    BYTE = 5120
    UNSIGNED_BYTE = 5121
    SHORT = 5122
    UNSIGNED_SHORT = 5123
    UNSIGNED_INT = 5125
    FLOAT = 5126

class Accessor:
    def __init__(self, accessor_type, accessor_component_type, count, bufferview, byteoffset = 0):
        self.accessor_type = accessor_type
        self.accessor_component_type = accessor_component_type
        self.count = count
        self.bufferview = bufferview
        self.byteoffset = byteoffset

class BufferView:
    def __init__(self, buffer, bytelength, byteoffset=0, bytestride=None):
        self.buffer = buffer
        self.byteoffset = byteoffset
        self.bytelength = bytelength
        self.bytestride = bytestride


class GLTF2Loader:
    def __init__(self, gltf_file):
        if os.path.isfile(gltf_file) and gltf_file.endswith('.gltf'):
            with open(gltf_file) as f:
                self.json_data = json.load(f)

    def _get_accessor(self, accessor_json):
        accessor_type = AccessorType(accessor_json['type']).name
        accessor_component_type = AccessorComponentType(accessor_json['componentType']).name
        count = accessor_json['count']
        bufferview = self.json_data['bufferViews'][accessor_json['bufferView']]
        byteoffset = accessor_json['byteOffset'] if ('byteOffset' in accessor_json) else 0
        return Accessor(accessor_type = accessor_type, accessor_component_type = accessor_component_type, count = count, bufferview = bufferview, byteoffset = byteoffset)
        
    def _get_bufferview(self, bufferview_json):
        buffer = bufferview_json['buffer']
        bytelength = bufferview_json['byteLength']
        byteoffset = bufferview_json['byteOffset'] if ('byteOffset' in bufferview_json) else 0
        byteStride = bufferview_json['byteStride'] if ('byteStride' in bufferview_json) else None
        return BufferView(buffer=buffer, bytelength=bytelength, byteoffset=byteoffset=, bytestride=byteStride)

    def get_buffer_data(self, accessor, bufferview):
        '''Get the buffer referenced by the bufferview'''
        '''Get the bytelength data from the buffer (check if stride is necessary)'''
        '''use the accessor to interpret the bufferview data'''
        pass
