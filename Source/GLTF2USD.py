import argparse
import json
import ntpath
import numpy
import os
from pprint import pprint
from gltf2loader import GLTF2Loader, PrimitiveMode

from pxr import Usd, UsdGeom, Sdf, UsdShade
# stage = Usd.Stage.CreateNew('Sphere.usda')
# xformPrim = UsdGeom.Xform.Define(stage, '/parent')
# spherePrim = UsdGeom.Sphere.Define(stage, '/parent/sphere')
# stage.GetRootLayer().Save()

class GLTF2USD:
    def __init__(self, gltf_file):
        self.gltf_loader = GLTF2Loader(gltf_file)
        file_base_name = ntpath.basename(gltf_file)
        usd_name = '{base_name}.usda'.format(base_name =os.path.splitext(file_base_name)[0])
        print usd_name
        self.stage = Usd.Stage.CreateNew(usd_name)

    def _convert_to_gltf_document(self, gltf_file):
        with open(gltf_file) as f:
            self.json_data = json.load(f)
            
    def print_gltf_data(self):
        pprint(self.json_data)
    
    def convert_nodes_to_xform(self):
        if 'nodes' in self.gltf_loader.json_data:
            for i, node in enumerate(self.gltf_loader.json_data['nodes']):
                xform_name = 'node{}'.format(i)
                self._convert_node_to_xform(node, xform_name)
            self.stage.GetRootLayer().Save()
                
    def _convert_node_to_xform(self, node, xform_name):
        print(node)
        xform_path = '/{}'.format(xform_name)
        xformPrim = UsdGeom.Xform.Define(self.stage, xform_path)
        if 'mesh' in node:
            self._convert_mesh_to_xform(self.gltf_loader.json_data['meshes'][node['mesh']], xform_path)

    def _convert_mesh_to_xform(self, mesh, parent_path):
        #for each mesh primitive, create a USD mesh
        if 'primitives' in mesh:
            for i, mesh_primitive in enumerate(mesh['primitives']):
                mesh_primitive_name = 'mesh_primitive{}'.format(i)
                self._convert_primitive_to_mesh(name=mesh_primitive_name, primitive=mesh_primitive, parent_path=parent_path)

    def _convert_primitive_to_mesh(self, name, primitive, parent_path):
        mesh = UsdGeom.Mesh.Define(self.stage, parent_path + '/{}'.format(name))
        print('mesh primitive')
        buffer = self.gltf_loader.json_data['buffers'][0]
        if 'material' in primitive:
            print('material present')
            usd_material = self.usd_materials[primitive['material']]
            UsdShade.MaterialBindingAPI(mesh).Bind(usd_material)
        if 'attributes' in primitive:
            for attribute in primitive['attributes']:
                print(attribute)
                if attribute == 'POSITION':
                    accessor_index = primitive['attributes'][attribute]
                    accessor = self.gltf_loader.json_data['accessors'][accessor_index]
                    data = self.gltf_loader.get_data(buffer=buffer, accessor=accessor)
                    mesh.CreatePointsAttr(data)
                    print(data)
                    
                    print 'position attribute'
                if attribute == 'NORMAL':
                    accessor_index = primitive['attributes'][attribute]
                    accessor = self.gltf_loader.json_data['accessors'][accessor_index]
                    data = self.gltf_loader.get_data(buffer=buffer, accessor=accessor)
                    mesh.CreateNormalsAttr(data)
                    print(data)
                    print 'normal attribute'
                if attribute == 'COLOR':
                    accessor_index = primitive['attributes'][attribute]
                    accessor = self.gltf_loader.json_data['accessors'][accessor_index]
                    data = self.gltf_loader.get_data(buffer=buffer, accessor=accessor)
                    mesh.CreateColorsAttr(data)
                    print(data)
                    print 'color attribute'
                if attribute == 'TEXCOORD_0':
                    accessor_index = primitive['attributes'][attribute]
                    accessor = self.gltf_loader.json_data['accessors'][accessor_index]
                    data = self.gltf_loader.get_data(buffer=buffer, accessor=accessor)
                    print(data)
                    print 'texcoord 0'
                    prim_var = UsdGeom.PrimvarsAPI(mesh)
                    uv = prim_var.CreatePrimvar('primvars:st0', Sdf.ValueTypeNames.TexCoord2fArray, 'vertex')
                    uv.Set(data)


        if 'indices' in primitive:
            print('indices present')
            indices = self.gltf_loader.get_data(buffer=buffer, accessor=self.gltf_loader.json_data['accessors'][primitive['indices']])
            print(indices)
            #TODO: Compute faces properly
            
            num_faces = len(indices)/3
            face_count = [3] * num_faces
            mesh.CreateFaceVertexCountsAttr(face_count)
            mesh.CreateFaceVertexIndicesAttr(indices)

        if 'material' in primitive:
            material = self.gltf_loader.json_data['materials'][primitive['material']]
            print('material present')

    def _create_preview_surface_material(self, material, parent_path):
        pass

    def _convert_materials_to_preview_surface(self):
        if 'materials' in self.gltf_loader.json_data:
            self.usd_materials = []
            print('materials present')
            material_path_root = '/Materials'
            scope = UsdGeom.Scope.Define(self.stage, material_path_root)

            for i, material in enumerate(self.gltf_loader.json_data['materials']):
                name = 'pbrmaterial{}'.format(i)
                material_path = Sdf.Path('{0}/{1}'.format(material_path_root, name))
                usd_material = UsdShade.Material.Define(self.stage, material_path)
                self.usd_materials.append(usd_material)
                specular_workflow = usd_material.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Bool)
                specular_workflow.Set(False)
                usd_material_surface_output = usd_material.CreateOutput("surface", Sdf.ValueTypeNames.Token)
                usd_material_displacement_output = usd_material.CreateOutput("displacement", Sdf.ValueTypeNames.Token)
                pbr_mat = UsdShade.Shader.Define(self.stage, material_path.AppendChild('pbrMat1'))
                pbr_mat.CreateIdAttr("UsdPreviewSurface")
                pbr_mat_surface_output = pbr_mat.CreateOutput("surface", Sdf.ValueTypeNames.Token)
                pbr_mat_displacement_output = pbr_mat.CreateOutput("displacement", Sdf.ValueTypeNames.Token)
                usd_material_surface_output.ConnectToSource(pbr_mat_surface_output)
                usd_material_displacement_output.ConnectToSource(pbr_mat_displacement_output)
                
                if 'pbrMetallicRoughness' in material:
                    pbr_metallic_roughness = material['pbrMetallicRoughness']
                    print('pbr present')
                    if 'baseColorFactor' in pbr_metallic_roughness:
                        diffuse_color = pbr_mat.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
                        base_color_factor = pbr_metallic_roughness['baseColorFactor']
                        diffuse_color.Set((base_color_factor[0],base_color_factor[1],base_color_factor[2]))
                        opacity = pbr_mat.CreateInput("opacity", Sdf.ValueTypeNames.Float)
                        opacity.Set(base_color_factor[3])







        
             

    def _get_accessor_data(self, index):
        accessor = self.gltf_loader.json_data['accessors'][index]
        print(accessor)


def convert_to_usd(gltf_file):
    gltf_converter = GLTF2USD(gltf_file)
    gltf_converter._convert_materials_to_preview_surface()
    gltf_converter.convert_nodes_to_xform()
    #gltf_converter.print_gltf_data()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert glTF to USD')
    parser.add_argument('--gltf', action='store', dest='gltf_file', help='glTF file (in .gltf format)', required=True)
    args = parser.parse_args()

    if args.gltf_file:
        convert_to_usd(args.gltf_file)
