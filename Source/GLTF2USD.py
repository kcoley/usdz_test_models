import argparse
import json
import ntpath
import numpy
import os
from pprint import pprint

from pxr import Usd, UsdGeom
# stage = Usd.Stage.CreateNew('Sphere.usda')
# xformPrim = UsdGeom.Xform.Define(stage, '/parent')
# spherePrim = UsdGeom.Sphere.Define(stage, '/parent/sphere')
# stage.GetRootLayer().Save()

class GLTF2USD:
    def __init__(self, gltf_file):
        if os.path.isfile(gltf_file) and gltf_file.endswith('.gltf'):   
            self.gltf_document = self._convert_to_gltf_document(gltf_file)
            file_base_name = ntpath.basename(gltf_file)
            usd_name = '{base_name}.usda'.format(base_name =os.path.splitext(file_base_name)[0])
            print usd_name
            self.stage = Usd.Stage.CreateNew(usd_name)
        else:
            raise Exception('Currently, only .gltf files are supported!')

    def _convert_to_gltf_document(self, gltf_file):
        with open(gltf_file) as f:
            self.json_data = json.load(f)
            
    def print_gltf_data(self):
        pprint(self.json_data)
    
    def convert_nodes_to_xform(self):
        if 'nodes' in self.json_data:
            for i, node in enumerate(self.json_data['nodes']):
                xform_name = 'node{}'.format(i)
                self._convert_node_to_xform(node, xform_name)
            #self.stage.GetRootLayer().Save()
                

    def _convert_node_to_xform(self, node, xform_name):
        print(node)
        xform_path = '/{}'.format(xform_name)
        xformPrim = UsdGeom.Xform.Define(self.stage, xform_path)
        if 'mesh' in node:
            self._convert_mesh_to_xform(self.json_data['meshes'][node['mesh']], xform_path)

    def _convert_mesh_to_xform(self, mesh, parent_path):
        #for each mesh primitive, create a USD mesh
        if 'primitives' in mesh:
            for i, mesh_primitive in enumerate(mesh['primitives']):
                print('mesh_primitive{}'.format(i))

    def _convert_primitive_to_mesh(self, primitive, parent_path):
        print('mesh primitive')

    def _get_accessor_data(self, index):
        accessor = self.json_data['accessors'][index]
        print(accessor)


def convert_to_usd(gltf_file):
    gltf_converter = GLTF2USD(gltf_file)
    gltf_converter.convert_nodes_to_xform()
    #gltf_converter.print_gltf_data()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert glTF to USD')
    parser.add_argument('--gltf', action='store', dest='gltf_file', help='glTF file (in .gltf format)', required=True)
    args = parser.parse_args()

    if args.gltf_file:
        convert_to_usd(args.gltf_file)
