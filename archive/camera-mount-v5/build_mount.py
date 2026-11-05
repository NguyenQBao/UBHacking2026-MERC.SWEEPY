"""20-mm-hole camera mount. Units mm. pip install manifold3d numpy trimesh."""
from pathlib import Path
import json
import numpy as np
import trimesh
from manifold3d import Manifold as M
P=Path(__file__).resolve().parent
HOLE_DIAMETER=20.0
PLATE_THICKNESS=3.0 # Accepted provisional value, not measured.
PLUG_DIAMETER=19.4
PLUG_LENGTH=PLATE_THICKNESS-0.5
FLANGE_DIAMETER=40.0
FLANGE_THICKNESS=4.0
PIVOT_HEIGHT_ABOVE_FLANGE=60.0
CAMERA_SIZE=25.0
assert PLUG_LENGTH>0

def box(x,y,z,at=(0,0,0)):
 return M.cube((x,y,z)).translate((at[0]-x/2,at[1]-y/2,at[2]))
def cz(d,h,x=0,y=0,z=0):return M.cylinder(h,d/2,circular_segments=96).translate((x,y,z))
def cx(d,h,x=0,y=0,z=0):return M.cylinder(h,d/2,circular_segments=64).rotate((0,90,0)).translate((x,y,z))
z_top=PLUG_LENGTH+FLANGE_THICKNESS
pivot_y=13.0
pivot_z=z_top+PIVOT_HEIGHT_ABOVE_FLANGE
base=cz(PLUG_DIAMETER,PLUG_LENGTH)+cz(FLANGE_DIAMETER,FLANGE_THICKNESS,z=PLUG_LENGTH)
for x in (-6.4,6.4):base+=box(4,8,PIVOT_HEIGHT_ABOVE_FLANGE+8,(x,pivot_y,z_top-0.2))
base-=cz(4.5,150,z=-1)
base-=cx(3.4,30,x=-15,y=pivot_y,z=pivot_z)
washer=cz(36,3)-cz(4.5,5,z=-1)
carrier=box(37,37,3)-box(22,22,5,(0,0,-1))
carrier+=box(8,12,26,(0,-20,0))
carrier-=cx(3.4,12,x=-6,y=-20,z=18)
for x in (-16,16):
 for y in (-7,7):carrier-=cz(2.4,6,x,y,-1)
# Cheap locating-post coupon, printed flange-down, flipped for testing.
fit=cz(32,3)+cz(PLUG_DIAMETER,PLUG_LENGTH,z=3)
fit-=cz(4.5,12,z=-1)
clevis=box(28,16,3)
for x in (-6.4,6.4):clevis+=box(4,8,14,(x,0,3))
clevis-=cx(3.4,24,x=-12,z=10)
ear=box(8,12,15)-cx(3.4,12,x=-6,z=8)
parts={'01_hole20_base_with_mast_x1':base,'02_camera25_pitch_carrier_x1':carrier,
       '03_under_plate_washer_x1':washer,'00a_post19p4_fit_coupon_x1':fit,
       '00b_pitch_fork_coupon_x1':clevis,'00c_pitch_ear_coupon_x1':ear}
# Printed part fit, acrylic clearance and tool access checks in assembly coordinates.
installed=carrier.rotate((90,0,0)).translate((0,pivot_y+18,pivot_z+20))
collisions={}
for a in range(-20,51,5):
 posed=installed.translate((0,-pivot_y,-pivot_z)).rotate((a,0,0)).translate((0,pivot_y,pivot_z))
 v=(posed^base).volume();assert v<1e-5,(a,v);collisions[str(a)]=round(v,6)
plate_bottom=PLUG_LENGTH-PLATE_THICKNESS
plate=box(120,120,PLATE_THICKNESS,(0,0,plate_bottom))-cz(HOLE_DIAMETER,20,z=-10)
assert (base^plate).volume()<1e-6
assert PLUG_DIAMETER<HOLE_DIAMETER
# Plug must not bottom on lower washer before acrylic is clamped.
assert PLATE_THICKNESS-PLUG_LENGTH>=.49
# M4 head/washer/screwdriver envelope; excludes separate carrier and actual camera.
assert (base^cz(10,100,z=z_top+.1)).volume()<1e-6
report={}
for name,solid in parts.items():
 assert len(solid.decompose())==1,name
 r=solid.to_mesh();m=trimesh.Trimesh(np.asarray(r.vert_properties)[:,:3],np.asarray(r.tri_verts),process=True)
 assert m.is_watertight and m.is_winding_consistent and m.volume>0,name
 m.apply_translation(-m.bounds[0]);m.export(P/(name+'.stl'))
 report[name]={'bounds_mm':m.extents.round(3).tolist(),'solid_cm3':round(m.volume/1000,2),'watertight':True,'one_solid':True}
(P/'validation.json').write_text(json.dumps({'parameters':{'hole_diameter':HOLE_DIAMETER,'assumed_acrylic_thickness':PLATE_THICKNESS,'plug_diameter':PLUG_DIAMETER,'plug_length':PLUG_LENGTH,'plug_to_lower_washer_clearance':PLATE_THICKNESS-PLUG_LENGTH,'pivot_height_above_plate':FLANGE_THICKNESS+PIVOT_HEIGHT_ABOVE_FLANGE},'parts':report,'sampled_printed_part_collision_volume_mm3':collisions,'acrylic_intersection_volume_mm3':0,'note':'No actual PCB, ribbon, screw, chassis edge or hardware test.'},indent=2))
print('PASS: six printable solids; sampled pitch clearance, nominal acrylic clearance and central M4 access checked')
