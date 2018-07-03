Code Snippet
```python
from pxr import Usd, UsdGeom
stage = Usd.Stage.CreateNew('Sphere.usda')
xformPrim = UsdGeom.Xform.Define(stage, '/parent')
spherePrim = UsdGeom.Sphere.Define(stage, '/parent/sphere')
stage.GetRootLayer().Save()
```


xcrun usdz_converter Sphere.usda Sphere.usdz -v
-v : Verbose output
2018-07-03 14:31:29.013 usdz_converter[45393:2222590] 


Converting asset file 'Sphere.usda' ...
Mesh: sphere
		|
		+---->: 306 vertices.
		|
		+----> sub-mesh: ellipsoid-0
There are 306 vertices in this asset file 'Sphere.usda'.
