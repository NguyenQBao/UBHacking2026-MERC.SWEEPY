"""Parametric roll-paper box, mm. Prototype: verify actual roll and adhesive."""
from pathlib import Path
import json
import numpy as np
import trimesh
from manifold3d import Manifold as M
P=Path(__file__).resolve().parent
# Intended maximum roll: 115 mm axial length, 120 mm full diameter.
INNER_X,INNER_Y=120.0,126.0
WALL=3.0
HEIGHT=135.0
OUTER_X,OUTER_Y=INNER_X+2*WALL,INNER_Y+2*WALL
LID_GAP=.4  # each side; test with small coupon first

def cube(x,y,h,z=0,at=(0,0)):
 return M.cube((x,y,h)).translate((at[0]-x/2,at[1]-y/2,z))
def rounded(x,y,h,r,z=0):
 p=cube(x-2*r,y,h,z)+cube(x,y-2*r,h,z)
 for a in (-x/2+r,x/2-r):
  for b in (-y/2+r,y/2-r):
   p+=M.cylinder(h,r,circular_segments=48).translate((a,b,z))
 return p
body=rounded(OUTER_X,OUTER_Y,HEIGHT,6)-rounded(INNER_X,INNER_Y,HEIGHT,3,3)
# Open-to-top outlet avoids a long unsupported printed bridge.
body-=cube(116,10,16,HEIGHT-12,(0,OUTER_Y/2-2))
lid=rounded(OUTER_X,OUTER_Y,3,6)
skirt=rounded(INNER_X-2*LID_GAP,INNER_Y-2*LID_GAP,6,2.6,3)
skirt-=rounded(INNER_X-2*LID_GAP-4,INNER_Y-2*LID_GAP-4,8,1,3)
# Remove front skirt across outlet: do not obstruct the paper path.
skirt-=cube(116,10,10,2,(0,INNER_Y/2-2))
lid+=skirt
# Test the same local wall/skirt gap using a small straight section.
coupon_base=cube(36,28,10)-cube(30,22,12,2)
coupon_insert=cube(36,28,2)+cube(30-2*LID_GAP,22-2*LID_GAP,6,2)
coupon_insert-=cube(26-2*LID_GAP,18-2*LID_GAP,8,2)
parts={'01_box_body_x1':body,'02_removable_lid_x1':lid,
       '00a_fit_wall_coupon_x1':coupon_base,'00b_fit_lid_coupon_x1':coupon_insert}
report={}
for name,solid in parts.items():
 assert len(solid.decompose())==1,name
 raw=solid.to_mesh();mesh=trimesh.Trimesh(np.asarray(raw.vert_properties)[:,:3],np.asarray(raw.tri_verts),process=True)
 assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,name
 mesh.apply_translation(-mesh.bounds[0]);mesh.export(P/(name+'.stl'))
 report[name]={'size_mm':mesh.extents.round(3).tolist(),'solid_volume_cm3':round(mesh.volume/1000,2),'watertight':True,'one_solid':True}
# Verify nominal installed front paper passage remains clear of the lid skirt.
# lid inverted for installation: printed Z3..9 becomes assembled Z135..129.
installed_lid=lid.rotate((0,180,0)).translate((0,0,HEIGHT+3))
passage=cube(100,10,10,HEIGHT-11,(0,OUTER_Y/2-2))
assert (body^passage).volume()<1e-6
assert (installed_lid^passage).volume()<1e-6
(P/'validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
