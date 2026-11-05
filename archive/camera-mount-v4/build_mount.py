from pathlib import Path
import numpy as np
import trimesh
from manifold3d import Manifold as M
import json
P=Path(__file__).resolve().parent

def box(x,y,h,at=(0,0,0)):
 return M.cube((x,y,h)).translate((at[0]-x/2,at[1]-y/2,at[2]))
def cz(d,h,at):return M.cylinder(h,d/2,circular_segments=48).translate(at)
def cx(d,h,at):return M.cylinder(h,d/2,circular_segments=48).rotate((0,90,0)).translate(at)
def slot(p,x,y,length,w):
 p-=box(w,length-w,10,(x,y,-1))
 for dy in (-(length-w)/2,(length-w)/2):p-=cz(w,10,(x,y+dy,-1))
 return p
base=box(60,45,4)
for x in (-23,23):base=slot(base,x,0,28,4)
# Matching clevis: 8.8 inside gap for 8-mm ear, 4-mm cheeks, 3.4 bore.
for x in (-6.4,6.4):base+=box(4,12,74,(x,0,4))
base-=cx(3.4,30,(-15,0,70))
carrier=box(36,34,3)-box(22,20,5,(0,0,-1))
carrier+=box(8,12,26,(0,-20,0))
carrier-=cx(3.4,12,(-6,-20,18))
for x in (-15.5,15.5):
 for y in (-6,6):carrier-=cz(2.4,6,(x,y,-1))
# Two small clevis fit coupons, same gap and hole as full set.
fit=box(30,20,3)
for x in (-6.4,6.4):fit+=box(4,12,14,(x,0,3))
fit-=cx(3.4,25,(-12.5,0,10))
ear=box(8,12,15)-cx(3.4,12,(-6,0,8))
parts={'01_base_and_clevis_x1':base,'02_pitch_carrier_x1':carrier,'00a_clevis_coupon_x1':fit,'00b_ear_coupon_x1':ear}
# Model-space assembled carrier pivot at (0,0,70), frame behind pivot.
installed=carrier.rotate((90,0,0)).translate((0,18,90))
angles=list(range(-20,51,5));collisions={}
for a in angles:
 posed=installed.translate((0,0,-70)).rotate((a,0,0)).translate((0,0,70))
 vol=(posed^base).volume()
 collisions[str(a)]=round(vol,6)
 assert vol<1e-5,(a,vol)
report={}
for name,solid in parts.items():
 assert len(solid.decompose())==1,name
 r=solid.to_mesh();m=trimesh.Trimesh(np.asarray(r.vert_properties)[:,:3],np.asarray(r.tri_verts),process=True)
 assert m.is_watertight and m.is_winding_consistent and m.volume>0,name
 m.apply_translation(-m.bounds[0]);m.export(P/(name+'.stl'))
 report[name]={'size_mm':m.extents.round(3).tolist(),'watertight':True,'volume_cm3':round(m.volume/1000,2)}
(P/'validation.json').write_text(json.dumps({'parts':report,'printed_part_collision_sample_angles_deg':collisions,'note':'Sampled printed solids only; excludes camera PCB, ribbon, bolt, ties and chassis.'},indent=2))
print('PASS: four solids; sampled printed-part collision checks -20 through +50 deg')
