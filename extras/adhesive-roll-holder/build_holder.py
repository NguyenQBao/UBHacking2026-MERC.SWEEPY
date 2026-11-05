from pathlib import Path
import numpy as np
import trimesh
from manifold3d import Manifold as M
import json
P=Path(__file__).resolve().parent
# Adhesive pads face down; shaft lies along X; two separately placed supports.
PAD=(40,40,4)
ROD=8.0
SLOT=9.0
report={}
for height in (25,60):
 p=M.cube(PAD).translate((-20,-20,0))
 # 12 mm wide bearing tower; slot opens upward for easy manual removal.
 p+=M.cube((12,24,height+8-4)).translate((-6,-12,4))
 bore=M.cylinder(16,SLOT/2,circular_segments=64).rotate((0,90,0)).translate((-8,0,height))
 entry=M.cube((16,SLOT,20)).translate((-8,-SLOT/2,height))
 p-=bore+entry
 assert len(p.decompose())==1
 raw=p.to_mesh();mesh=trimesh.Trimesh(np.asarray(raw.vert_properties)[:,:3],np.asarray(raw.tri_verts),process=True)
 assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
 mesh.apply_translation(-mesh.bounds[0])
 name=f'adhesive_support_axis_{height}mm_PRINT_TWO'
 mesh.export(P/(name+'.stl'))
 report[name]={'dimensions_mm':mesh.extents.tolist(),'shaft_center_height_mm':height,'rod_nominal_mm':8,'slot_mm':9,'watertight':True,'volume_cm3':round(mesh.volume/1000,2)}
# Wall mount: adhesive back at Z=0; gravity is -Y; rod axis X.
p=M.cube((40,80,4)).translate((-20,-40,0))
p+=M.cube((12,20,69)).translate((-6,-12,4))
bore=M.cylinder(16,4.5,circular_segments=64).rotate((0,90,0)).translate((-8,0,65))
entry=M.cube((16,20,9)).translate((-8,0,60.5))
p-=bore+entry
assert len(p.decompose())==1
r=p.to_mesh();mesh=trimesh.Trimesh(np.asarray(r.vert_properties)[:,:3],np.asarray(r.tri_verts),process=True)
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
mesh.apply_translation(-mesh.bounds[0]);mesh.export(P/'WALL_adhesive_support_PRINT_TWO.stl')
report['WALL_adhesive_support_PRINT_TWO']={'dimensions_mm':mesh.extents.tolist(),'shaft_offset_from_wall_mm':65,'adhesive_pad_mm':[40,80],'watertight':True}
(P/'validation.json').write_text(json.dumps(report,indent=2))
# Schematic: not claiming a fit to an unmeasured roll.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
a,b=axs
for x in (0,160):
 a.add_patch(Rectangle((x,0),40,4,color='#5da8b8'))
 a.add_patch(Rectangle((x+14,4),12,56,color='#8ec6cd'))
a.plot([8,192],[60,60],color='#545f69',lw=6)
a.add_patch(Rectangle((42,29),116,62,facecolor='#e2ccab',edgecolor='#927347'))
a.text(100,105,'Roll: length/diameter TBD',ha='center',fontsize=12)
a.text(100,-13,'Two separate adhesive pads; spacing adjustable',ha='center',fontsize=10)
a.set(xlim=(-8,208),ylim=(-22,120));a.set_title('FRONT VIEW / schematic');a.set_aspect('equal');a.axis('off')
b.add_patch(Rectangle((-20,0),40,4,color='#5da8b8'))
b.add_patch(Rectangle((-12,4),24,64,color='#8ec6cd'))
b.add_patch(Circle((0,60),4.5,facecolor='white',edgecolor='#326472'))
b.add_patch(Rectangle((-4.5,60),9,10,color='white'))
b.annotate('9 mm open slot / 8 mm rod',xy=(0,60),xytext=(22,82),arrowprops={'arrowstyle':'-'},fontsize=10)
b.annotate('40 x 40 mm adhesive pad',xy=(12,2),xytext=(24,20),arrowprops={'arrowstyle':'-'},fontsize=10)
b.set(xlim=(-28,125),ylim=(-5,110));b.set_aspect('equal');b.axis('off');b.set_title('END VIEW / tall version')
fig.suptitle('Adhesive roll support: trial parts, not a powered brush bearing',fontsize=13)
fig.savefig(P/'holder_preview.png',dpi=170)
print(json.dumps(report,indent=2))
