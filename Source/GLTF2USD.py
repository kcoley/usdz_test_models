import argparse
import json
import ntpath
import numpy
import os
import shutil

from gltf2loader import GLTF2Loader, PrimitiveMode, TextureWrap, MinFilter, MagFilter

from PIL import Image

from pxr import Usd, UsdGeom, Sdf, UsdShade, Gf

'''
Class for converting glTF 2.0 models to Pixar's USD format.  Currently openly supports .gltf files
with non-embedded data and exports to .usda .
'''
class GLTF2USD:
    texture_sampler_wrap = {
        TextureWrap.CLAMP_TO_EDGE : 'clamp',
        TextureWrap.MIRRORED_REPEAT : 'mirror',
        TextureWrap.REPEAT: 'repeat',
    }

    def __init__(self, gltf_file, verbose):
        self.gltf_loader = GLTF2Loader(gltf_file)
        self.verbose = verbose
        file_base_name = ntpath.basename(gltf_file)
        usd_name = '{base_name}.usda'.format(base_name =os.path.splitext(file_base_name)[0])
        self.stage = Usd.Stage.CreateNew(usd_name)

    '''
    Returns all the children nodes
    '''
    def _get_child_nodes(self):
        child_nodes = set()
        for node in self.gltf_loader.json_data['nodes']:
            if 'children' in node:
                child_nodes.update(node['children'])

        return child_nodes
    
    '''
    Converts the glTF nodes to USD Xforms.  The models get a parent Xform that scales the geometry by 100 to convert from meters (glTF) to centimeters (USD).
    '''
    def convert_nodes_to_xform(self):
        parent_root = '/root'
        parent_transform = UsdGeom.Xform.Define(self.stage, parent_root)
        parent_transform.AddScaleOp().Set((100, 100, 100))
        
        child_nodes = self._get_child_nodes()
        if 'nodes' in self.gltf_loader.json_data:
            child_nodes = self._get_child_nodes()
            for i, node in enumerate(self.gltf_loader.json_data['nodes']):
                if i not in child_nodes:
                    xform_name = '{parent_root}/node{index}'.format(parent_root=parent_root, index=i)
                    self._convert_node_to_xform(node, xform_name)
            self.stage.GetRootLayer().Save()
        if self.verbose:
            print('Conversion complete!')

    '''
    Converts a glTF node to a USD transform.
    '''        
    def _convert_node_to_xform(self, node, xform_name):
        xform_path = '{}'.format(xform_name)
        xformPrim = UsdGeom.Xform.Define(self.stage, xform_path)
        
        if 'matrix' in node:
            matrix = node['matrix']
            xformPrim.AddTransformOp().Set(
                Gf.Matrix4d(
                    matrix[0], matrix[1], matrix[2], matrix[3],
                    matrix[4], matrix[5], matrix[6], matrix[7],
                    matrix[8], matrix[9], matrix[10], matrix[11],
                    matrix[12], matrix[13], matrix[14], matrix[15]
                    )
            )
        else:
            xform_matrix = Gf.Matrix4d()
            if 'scale' in node:
                scale = node['scale']
                #xformPrim.AddScaleOp().Set((scale[0], scale[1], scale[2]))
                xform_matrix.SetScale((scale[0], scale[1], scale[2]))

            if 'rotation' in node:
                rotation = node['rotation']
                #xformPrim.AddOrientOp().Set(Gf.Quatf(rotation[3], rotation[0], rotation[1], rotation[2]))
                xform_matrix.SetRotateOnly(Gf.Quatf(rotation[3], rotation[0], rotation[1], rotation[2]))

            if 'translation' in node:
                translation = node['translation']
                #xformPrim.AddTranslateOp().Set((translation[0], translation[1], translation[2]))
                xform_matrix.SetTranslateOnly((translation[0], translation[1], translation[2]))

            xformPrim.AddTransformOp().Set(xform_matrix)
        
        
        if 'mesh' in node:
            self._convert_mesh_to_xform(self.gltf_loader.json_data['meshes'][node['mesh']], xform_path)
        if 'children' in node:
            for child in node['children']:
                self._convert_node_to_xform(self.gltf_loader.json_data['nodes'][child], xform_path + '/node{}'.format(child))

    '''
    Converts a glTF mesh to a USD Xform.  Each primitive becomes a submesh of the Xform.
    '''
    def _convert_mesh_to_xform(self, mesh, parent_path):
        #for each mesh primitive, create a USD mesh
        if 'primitives' in mesh:
            for i, mesh_primitive in enumerate(mesh['primitives']):
                mesh_primitive_name = 'mesh_primitive{}'.format(i)
                self._convert_primitive_to_mesh(name=mesh_primitive_name, primitive=mesh_primitive, parent_path=parent_path)

    '''
    Converts a primitive to a USD mesh
    '''
    def _convert_primitive_to_mesh(self, name, primitive, parent_path):
        mesh = UsdGeom.Mesh.Define(self.stage, parent_path + '/{}'.format(name))
        buffer = self.gltf_loader.json_data['buffers'][0]
        if 'material' in primitive:
            usd_material = self.usd_materials[primitive['material']]
            UsdShade.MaterialBindingAPI(mesh).Bind(usd_material)
        if 'attributes' in primitive:
            for attribute in primitive['attributes']:
                if attribute == 'POSITION':
                    accessor_index = primitive['attributes'][attribute]
                    accessor = self.gltf_loader.json_data['accessors'][accessor_index]
                    data = self.gltf_loader.get_data(buffer=buffer, accessor=accessor)
                    mesh.CreatePointsAttr(data)
                if attribute == 'NORMAL':
                    accessor_index = primitive['attributes'][attribute]
                    accessor = self.gltf_loader.json_data['accessors'][accessor_index]
                    data = self.gltf_loader.get_data(buffer=buffer, accessor=accessor)                  
                    mesh.CreateNormalsAttr(data)

                if attribute == 'COLOR':
                    accessor_index = primitive['attributes'][attribute]
                    accessor = self.gltf_loader.json_data['accessors'][accessor_index]
                    data = self.gltf_loader.get_data(buffer=buffer, accessor=accessor)
                    mesh.CreateColorsAttr(data)
                if attribute == 'TEXCOORD_0':
                    accessor_index = primitive['attributes'][attribute]
                    accessor = self.gltf_loader.json_data['accessors'][accessor_index]
                    data = self.gltf_loader.get_data(buffer=buffer, accessor=accessor)
                    invert_uvs = []
                    for uv in data:
                        new_uv = (uv[0], 1 - uv[1])
                        invert_uvs.append(new_uv)
                    prim_var = UsdGeom.PrimvarsAPI(mesh)
                    uv = prim_var.CreatePrimvar('primvars:st0', Sdf.ValueTypeNames.TexCoord2fArray, 'vertex')
                    uv.Set(invert_uvs)


        if 'indices' in primitive:
            #TODO: Need to support glTF primitive modes.  Currently only Triangle mode is supported
            indices = self.gltf_loader.get_data(buffer=buffer, accessor=self.gltf_loader.json_data['accessors'][primitive['indices']])
            
            num_faces = len(indices)/3
            face_count = [3] * num_faces
            mesh.CreateFaceVertexCountsAttr(face_count)
            mesh.CreateFaceVertexIndicesAttr(indices)
        else:
            position_accessor =  self.gltf_loader.json_data['accessors'][primitive['attributes']['POSITION']]
            count = position_accessor['count']
            num_faces = count/3
            indices = range(0, count)
            face_count = [3] * num_faces
            mesh.CreateFaceVertexCountsAttr(face_count)
            mesh.CreateFaceVertexIndicesAttr(indices)

        if 'material' in primitive:
            material = self.gltf_loader.json_data['materials'][primitive['material']]

    def _get_texture__wrap_modes(self, texture):
        texture_data = {'wrapS': 'repeat', 'wrapT': 'repeat'}
        if 'sampler' in texture:
            sampler = self.gltf_loader.json_data['samplers'][texture['sampler']]
            
            if 'wrapS' in sampler:
                print(TextureWrap(sampler['wrapS']))
                texture_data['wrapS'] = GLTF2USD.texture_sampler_wrap[TextureWrap(sampler['wrapS'])]

            if 'wrapT' in sampler:
                print(TextureWrap(sampler['wrapT']))
                texture_data['wrapT'] = GLTF2USD.texture_sampler_wrap[TextureWrap(sampler['wrapT'])]

        return texture_data

    def _convert_images_to_usd(self):
        if 'images' in self.gltf_loader.json_data:
            self.images = []
            for i, image in enumerate(self.gltf_loader.json_data['images']):
                image_path = os.path.join(self.gltf_loader.root_dir, image['uri'])
                image_name = os.path.join(os.getcwd(), ntpath.basename(image_path))
                shutil.copyfile(image_path, image_name)
                self.images.append(ntpath.basename(image_name))

    def _convert_materials_to_preview_surface(self):
        if 'materials' in self.gltf_loader.json_data:
            self.usd_materials = []
            material_path_root = '/Materials'
            scope = UsdGeom.Scope.Define(self.stage, material_path_root)

            for i, material in enumerate(self.gltf_loader.json_data['materials']):
                name = 'pbrmaterial{}'.format(i)
                material_path = Sdf.Path('{0}/{1}'.format(material_path_root, name))
                usd_material = UsdShade.Material.Define(self.stage, material_path)
                self.usd_materials.append(usd_material)
                
                usd_material_surface_output = usd_material.CreateOutput("surface", Sdf.ValueTypeNames.Token)
                usd_material_displacement_output = usd_material.CreateOutput("displacement", Sdf.ValueTypeNames.Token)
                pbr_mat = UsdShade.Shader.Define(self.stage, material_path.AppendChild('pbrMat1'))
                pbr_mat.CreateIdAttr("UsdPreviewSurface")
                specular_workflow = pbr_mat.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Bool)
                specular_workflow.Set(False)
                pbr_mat_surface_output = pbr_mat.CreateOutput("surface", Sdf.ValueTypeNames.Token)
                pbr_mat_displacement_output = pbr_mat.CreateOutput("displacement", Sdf.ValueTypeNames.Token)
                usd_material_surface_output.ConnectToSource(pbr_mat_surface_output)
                usd_material_displacement_output.ConnectToSource(pbr_mat_displacement_output)

                #define uv primvar0
                primvar_st0 = UsdShade.Shader.Define(self.stage, material_path.AppendChild('primvar_st0'))
                primvar_st0.CreateIdAttr('UsdPrimvarReader_float2')
                fallback_st0 = primvar_st0.CreateInput('fallback', Sdf.ValueTypeNames.Float2)
                fallback_st0.Set((0,0))
                primvar_st0_varname = primvar_st0.CreateInput('varname', Sdf.ValueTypeNames.Token)
                primvar_st0_varname.Set('st0')
                primvar_st0_output = primvar_st0.CreateOutput('result', Sdf.ValueTypeNames.Float2)

                #define uv primvar1
                primvar_st1 = UsdShade.Shader.Define(self.stage, material_path.AppendChild('primvar_st1'))
                primvar_st1.CreateIdAttr('UsdPrimvarReader_float2')
                fallback_st1 = primvar_st1.CreateInput('fallback', Sdf.ValueTypeNames.Float2)
                fallback_st1.Set((0,0))
                primvar_st1_varname = primvar_st1.CreateInput('varname', Sdf.ValueTypeNames.Token)
                primvar_st1_varname.Set('st1')
                primvar_st1_output = primvar_st1.CreateOutput('result', Sdf.ValueTypeNames.Float2)
                
                if 'pbrMetallicRoughness' in material:
                    pbr_metallic_roughness = material['pbrMetallicRoughness']
                    if 'baseColorFactor' in pbr_metallic_roughness:
                        diffuse_color = pbr_mat.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
                        base_color_factor = pbr_metallic_roughness['baseColorFactor']
                        diffuse_color.Set((base_color_factor[0],base_color_factor[1],base_color_factor[2]))
                        opacity = pbr_mat.CreateInput("opacity", Sdf.ValueTypeNames.Float)
                        opacity.Set(base_color_factor[3])
                    if 'metallicFactor' in pbr_metallic_roughness:
                        metallic_factor = pbr_metallic_roughness['metallicFactor']
                        metallic = pbr_mat.CreateInput('metallic', Sdf.ValueTypeNames.Float)
                        metallic.Set(pbr_metallic_roughness['metallicFactor'])
                
                if 'occlusionTexture' in material:
                    base_color_texture = material['occlusionTexture']
                    image_name = self.images[base_color_texture['index']]
                    base_color_texture_shader = UsdShade.Shader.Define(self.stage, material_path.AppendChild('occlusionTexture'))
                    base_color_texture_shader.CreateIdAttr("UsdUVTexture")
                    
                    file_asset = base_color_texture_shader.CreateInput('file', Sdf.ValueTypeNames.Asset)
                    file_asset.Set(image_name)
                    base_color_texture_shader_rgb_output = base_color_texture_shader.CreateOutput('r', Sdf.ValueTypeNames.Float)
                    pbr_mat_base_color_texture = pbr_mat.CreateInput('occlusion', Sdf.ValueTypeNames.Float)
                    pbr_mat_base_color_texture.ConnectToSource(base_color_texture_shader_rgb_output)
                    base_color_texture_shader_input = base_color_texture_shader.CreateInput('st', Sdf.ValueTypeNames.Float2)
                    base_color_texture_shader_fallback = base_color_texture_shader.CreateInput('fallback', Sdf.ValueTypeNames.Float)
                    base_color_texture_shader_fallback.Set(0)
                    if 'texCoord' in base_color_texture and base_color_texture['texCoord'] == 1:
                        base_color_texture_shader_input.ConnectToSource(primvar_st1_output)
                    else:
                        base_color_texture_shader_input.ConnectToSource(primvar_st0_output)
                    if 'strength' in base_color_texture:
                        scale_vector = base_color_texture_shader.CreateInput('scale', Sdf.ValueTypeNames.Float4)
                        scale_factor = base_color_texture['strength']
                        scale_vector.Set((scale_factor, scale_factor, scale_factor, scale_factor))

                
                if 'normalTexture' in material:
                    scale_factor = material['normalTexture']['scale'] if 'scale' in material['normalTexture'] else [0,0,1]
                    fallback_normal_color = tuple(scale_factor[0:3])
                    scale_factor = (scale_factor[0], scale_factor[1], scale_factor[2], 1)
                    normal_components = {
                        'rgb': 
                        {'sdf_type' : Sdf.ValueTypeNames.Normal3f, 'name': 'normal'}
                    }

                    self._convert_texture_to_usd(
                        pbr_mat=pbr_mat, 
                        gltf_texture=material['normalTexture'], 
                        gltf_texture_name='normalTexture', 
                        color_components=normal_components, 
                        scale_factor=scale_factor, 
                        fallback_factor=fallback_normal_color, 
                        material_path=material_path,
                        fallback_type=Sdf.ValueTypeNames.Normal3f,
                        primvar_st0_output=primvar_st0_output,
                        primvar_st1_output=primvar_st1_output
                    )
                
                if 'emissiveTexture' in material:
                    emissive_factor = material['emissiveFactor'] if 'emissiveFactor' in material else [0,0,0]
                    fallback_emissive_color = tuple(emissive_factor[0:3])
                    scale_emissive_factor = (emissive_factor[0], emissive_factor[1], emissive_factor[2], 1)
                    emissive_components = {
                        'rgb': 
                        {'sdf_type' : Sdf.ValueTypeNames.Color3f, 'name': 'emissiveColor'}
                    }

                    self._convert_texture_to_usd(
                        pbr_mat=pbr_mat, 
                        gltf_texture=material['emissiveTexture'], 
                        gltf_texture_name='emissiveTexture', 
                        color_components=emissive_components, 
                        scale_factor=scale_emissive_factor, 
                        fallback_factor=fallback_emissive_color, 
                        material_path=material_path,
                        fallback_type=Sdf.ValueTypeNames.Color3f,
                        primvar_st0_output=primvar_st0_output,
                        primvar_st1_output=primvar_st1_output
                    )

                if 'baseColorTexture' in pbr_metallic_roughness:
                    base_color_factor = pbr_metallic_roughness['baseColorFactor'] if 'baseColorFactor' in pbr_metallic_roughness else [1,1,1,1]
                    fallback_base_color = (base_color_factor[0], base_color_factor[1], base_color_factor[2])
                    scale_base_color_factor = base_color_factor
                    base_color_components = {
                        'rgb': 
                        {'sdf_type' : Sdf.ValueTypeNames.Color3f, 'name': 'diffuseColor'}
                    }

                    self._convert_texture_to_usd(
                        pbr_mat=pbr_mat, 
                        gltf_texture=pbr_metallic_roughness['baseColorTexture'], 
                        gltf_texture_name='baseColorTexture', 
                        color_components=base_color_components, 
                        scale_factor=scale_base_color_factor, 
                        fallback_factor=fallback_base_color, 
                        material_path=material_path,
                        fallback_type=Sdf.ValueTypeNames.Color3f,
                        primvar_st0_output=primvar_st0_output,
                        primvar_st1_output=primvar_st1_output
                    )

                if 'metallicRoughnessTexture' in pbr_metallic_roughness:
                    metallic_roughness_texture_file = os.path.join(self.gltf_loader.root_dir, self.gltf_loader.json_data['images'][pbr_metallic_roughness['metallicRoughnessTexture']['index']]['uri'])
                    result = self.create_metallic_roughness_to_grayscale_images(metallic_roughness_texture_file)
                    metallic_factor = pbr_metallic_roughness['metallicFactor'] if 'metallicFactor' in pbr_metallic_roughness else 1.0
                    fallback_metallic = metallic_factor
                    scale_metallic = [metallic_factor] * 4
                    metallic_color_components = {
                        'b': 
                        {'sdf_type' : Sdf.ValueTypeNames.Float, 'name': 'metallic'}
                    }

                    roughness_factor = pbr_metallic_roughness['roughnessFactor'] if 'roughnessFactor' in pbr_metallic_roughness else 1.0
                    fallback_roughness = roughness_factor
                    scale_roughness = [roughness_factor] * 4
                    roughness_color_components = {
                        'g': 
                        {'sdf_type': Sdf.ValueTypeNames.Float, 'name': 'roughness'},
                    }
                    

                    self._convert_texture_to_usd(
                        pbr_mat=pbr_mat, 
                        gltf_texture=pbr_metallic_roughness['metallicRoughnessTexture'], 
                        gltf_texture_name='metallicTexture', 
                        color_components=metallic_color_components, 
                        scale_factor=scale_metallic, 
                        fallback_factor=fallback_metallic, 
                        material_path=material_path,
                        fallback_type=Sdf.ValueTypeNames.Float,
                        primvar_st0_output=primvar_st0_output,
                        primvar_st1_output=primvar_st1_output
                    )

                    self._convert_texture_to_usd(
                        pbr_mat=pbr_mat, 
                        gltf_texture=pbr_metallic_roughness['metallicRoughnessTexture'], 
                        gltf_texture_name='roughnessTexture', 
                        color_components=roughness_color_components, 
                        scale_factor=scale_roughness, 
                        fallback_factor=fallback_roughness, 
                        material_path=material_path,
                        fallback_type=Sdf.ValueTypeNames.Float,
                        primvar_st0_output=primvar_st0_output,
                        primvar_st1_output=primvar_st1_output
                    )

    def unpack_textures_to_grayscale_images(self, image, color_components):
        image_base_name = ntpath.basename(image)
        texture_name = image_base_name
        for color_component, sdf_type in color_components.iteritems():
            if color_component == 'rgb':
                pass
            else:
                img = Image.open(image)
                if img.mode == 'P':
                    img = img.convert('RGB')
                occlusion, roughness, metallic = img.split()
                if color_component == 'r':
                    texture_name = 'Occlusion_{}'.format(image_base_name)
                    occlusion.save(texture_name)
                elif color_component == 'g':
                    texture_name = 'Roughness_{}'.format(image_base_name)
                    roughness.save(texture_name)
                elif color_component == 'b':
                    texture_name = 'Metallic_{}'.format(image_base_name)
                    metallic.save(texture_name)
                else:
                    raise Exception('Unsupported image type!')


        return texture_name
    

    def create_metallic_roughness_to_grayscale_images(self, image):
        image_base_name = ntpath.basename(image)
        roughness_texture_name = 'Roughness_{}'.format(image_base_name)
        metallic_texture_name = 'Metallic_{}'.format(image_base_name)

        img = Image.open(image)

        if img.mode == 'P':
            #convert paletted image to RGB
            img = img.convert('RGB')
        channels = img.split()
        #get roughness
        channels[1].save(roughness_texture_name)
        #get metalness
        channels[2].save(metallic_texture_name)

        return {'metallic': metallic_texture_name, 'roughness': roughness_texture_name}

    '''
    Converts a glTF texture to USD
    '''
    def _convert_texture_to_usd(self, primvar_st0_output, primvar_st1_output, pbr_mat, gltf_texture, gltf_texture_name, color_components, scale_factor, fallback_factor, material_path, fallback_type):
        image_name = gltf_texture if (isinstance(gltf_texture, basestring)) else self.images[gltf_texture['index']]
        texture_index = int(gltf_texture['index'])
        texture = self.gltf_loader.json_data['textures'][texture_index]
        wrap_modes = self._get_texture__wrap_modes(texture)
        texture_shader = UsdShade.Shader.Define(self.stage, material_path.AppendChild(gltf_texture_name))
        texture_shader.CreateIdAttr("UsdUVTexture")

        wrap_s = texture_shader.CreateInput('wrapS', Sdf.ValueTypeNames.Token).Set(wrap_modes['wrapS'])
        wrap_t = texture_shader.CreateInput('wrapT', Sdf.ValueTypeNames.Token).Set(wrap_modes['wrapT'])
        
        texture_name = self.unpack_textures_to_grayscale_images(image_name, color_components)
        file_asset = texture_shader.CreateInput('file', Sdf.ValueTypeNames.Asset)
        file_asset.Set(texture_name)

        for color_params, usd_color_params in color_components.iteritems():
            sdf_type = usd_color_params['sdf_type']
            texture_shader_output = texture_shader.CreateOutput(color_params, sdf_type)
            pbr_mat_texture = pbr_mat.CreateInput(usd_color_params['name'], sdf_type)
            pbr_mat_texture.ConnectToSource(texture_shader_output)

        texture_shader_input = texture_shader.CreateInput('st', Sdf.ValueTypeNames.Float2)
        texture_shader_fallback = texture_shader.CreateInput('fallback', fallback_type)
        texture_shader_fallback.Set(fallback_factor)
        if 'texCoord' in gltf_texture and gltf_texture['texCoord'] == 1:
            texture_shader_input.ConnectToSource(primvar_st1_output)
        else:
            texture_shader_input.ConnectToSource(primvar_st0_output)
            
        scale_vector = texture_shader.CreateInput('scale', Sdf.ValueTypeNames.Float4)
        scale_vector.Set((scale_factor[0], scale_factor[1], scale_factor[2], scale_factor[3]))


'''
Converts a glTF file to USD
'''
def convert_to_usd(gltf_file, verbose=False):
    gltf_converter = GLTF2USD(gltf_file, verbose)
    gltf_converter._convert_images_to_usd()
    gltf_converter._convert_materials_to_preview_surface()
    gltf_converter.convert_nodes_to_xform()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert glTF to USD')
    parser.add_argument('--gltf', action='store', dest='gltf_file', help='glTF file (in .gltf format)', required=True)
    parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help='Enable verbose mode')
    args = parser.parse_args()

    if args.gltf_file:
        convert_to_usd(args.gltf_file, args.verbose)
