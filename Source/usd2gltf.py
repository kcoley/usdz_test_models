import argparse

from gltf2loader import GLTF2Loader, PrimitiveMode, TextureWrap, MinFilter, MagFilter

from pxr import Usd, UsdGeom, Sdf, UsdShade, Gf

class USD2GLTF:
    def __init__(self, usd_file, verbose):
        self.verbose = verbose
        self.usd_stage = Usd.Stage.Open(usd_file)
    
    def _convert_to_gltf(self):
        [x for x in self.usd_stage.Traverse()]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert glTF to USD')
    parser.add_argument('--usd', action='store', dest='usd_file', help='usd file (in .usd, .usda, or .usdc format)', required=True)
    parser.add_argument('--verbose', '-v', action='store_true', dest='verbose', help='Enable verbose mode')
    args = parser.parse_args()