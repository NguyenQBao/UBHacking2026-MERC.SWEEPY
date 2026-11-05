"""METALSWEEP v1, units mm. pip install manifold3d numpy trimesh matplotlib"""
from pathlib import Path
import json
import numpy as np
import trimesh
from manifold3d import Manifold as M

OUT = Path(__file__).resolve().parent
BASE = (180, 150, 4)
UPPER = (150, 120, 3)
SUPPORTS = [(x, y) for x in (-65, 65) for y in (-48, 48)]

def box(x, y, z, at=(0, 0, 0)):
    return M.cube((x, y, z)).translate((at[0]-x/2, at[1]-y/2, at[2]))

def cyl(d, h, x=0, y=0, z=0):
    return M.cylinder(h, d/2, circular_segments=48).translate((x,y,z))

def hole(part, x, y, d=3.4, h=100):
    return part - cyl(d, h, x, y, -1)

def slot(part, x, y, length, width=3.4, h=100):
    tool = box(length-width, width, h, (x,y,-1))
    for dx in (-(length-width)/2, (length-width)/2):
        tool += cyl(width,h,x+dx,y,-1)
    return part-tool

parts = {}
p = box(*BASE)
for x,y in SUPPORTS: p=hole(p,x,y)
# Grid of independent slots; front is +X. No exact motor footprint assumed.
for x in (-60,-30,0,30,60):
    for y in (-60,-30,0,30,60): p=slot(p,x,y,18)
# Narrow strap apertures for battery and temporary motor attachment.
for x in (-42,42):
    for y in (-18,18): p=slot(p,x,y,24,5)
parts['01_base_x1']=p

p=box(*UPPER)
for x,y in SUPPORTS:p=hole(p,x,y)
# Pi 3B nominal 58 x 49 mounting pattern; dry-fit official board before use.
for x in (-29,29):
    for y in (-24.5,24.5):p=hole(p,x,y,2.9)
for x in range(-50,51,10):
    for y in (-40,40):p=slot(p,x,y,7,4)
parts['02_pi_deck_x1']=p
parts['03_column_45mm_x4']=hole(box(12,12,45),0,0)
parts['04_pi_spacer_6mm_x4']=hole(cyl(7,6),0,0,2.9)

# Open universal strap cradle, internal 66 x 26, not an exact TT screw mount.
p=box(74,34,3)
p+=box(74,4,10,(0,-15,2))
p+=box(74,4,10,(0,15,2))
for x in (-25,25):
    p=slot(p,x,0,12)
    for y in (-9,9):p=slot(p,x,y,9,4)
parts['05_motor_strap_cradle_x2']=p

# Front boom bolts to base slots at X60 and X90; distal joint supports a strap.
p=box(140,24,6)
for x in (-55,-25,25,55):p=slot(p,x,0,18)
for x in (-48,48):
    for y in (-8,8):p=slot(p,x,y,10,3)
parts['06_detector_boom_x1']=p

# Two strap saddles support an existing detector housing; NOT a working coil.
p=box(50,24,4)
for x in (-17,17):p=slot(p,x,0,10,4)
p=hole(p,0,0)
parts['07_detector_strap_saddle_x2']=p

# Open-top tray with two solid rear ears; manually removable via screws.
p=box(70,45,28)-box(65,40,28,(0,0,2.5))
for x in (-25,25):
    p+=box(14,12,3,(x,-27,0))
    p=hole(p,x,-28)
parts['08_collection_tray_x1']=p

# Generic sensor shelf; zip tie sensor, adjust final downward view in assembly.
p=box(30,20,3)
p=slot(p,0,0,18)
for y in (-6,6):p=slot(p,0,y,20,3)
parts['09_sensor_shelf_x4']=p

# Prioritize this small tolerance coupon before printing large pieces.
p=box(60,20,3)
for x,d in zip((-24,-12,0,12,24),(2.7,2.9,3.2,3.4,3.6)):
    p=hole(p,x,0,d)
parts['00_hole_coupon_x1']=p

meshes={}
report={}
for name,solid in parts.items():
    raw=solid.to_mesh()
    mesh=trimesh.Trimesh(vertices=np.asarray(raw.vert_properties)[:,:3],faces=np.asarray(raw.tri_verts),process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,name
    assert len(solid.decompose())==1,name
    mesh.apply_translation(-mesh.bounds[0])
    mesh.export(OUT/(name+'.stl'))
    meshes[name]=mesh
    report[name]={'bounds_mm':mesh.extents.round(3).tolist(),'volume_cm3':round(mesh.volume/1000,2),'watertight':True,'connected_solids':1}
(OUT/'mesh_validation.json').write_text(json.dumps(report,indent=2))

# Honest preview of the actual meshes, not an AI illustration.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
fig=plt.figure(figsize=(16,10),layout='constrained')
for i,(name,mesh) in enumerate(meshes.items(),1):
    ax=fig.add_subplot(3,4,i,projection='3d')
    light=np.array([.3,-.4,.85]);light/=np.linalg.norm(light)
    shade=.55+.45*np.maximum(0,mesh.face_normals@light)
    colors=np.column_stack((shade*.34,shade*.72,shade*.79,np.ones(len(shade))))
    ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolors=colors,edgecolor='none',linewidth=0))
    a,b=mesh.bounds;mid=(a+b)/2;r=max(mesh.extents)/2*1.15
    ax.set(xlim=(mid[0]-r,mid[0]+r),ylim=(mid[1]-r,mid[1]+r),zlim=(mid[2]-r,mid[2]+r))
    ax.set_box_aspect((1,1,1));ax.view_init(32,-55);ax.set_axis_off()
    ax.set_title(name+'\n'+' x '.join(f'{v:g}' for v in mesh.extents)+' mm',fontsize=9)
fig.suptitle('METALSWEEP v1 | Actual STL parts | Prototype / verify fit before full print',fontsize=17)
fig.savefig(OUT/'parts_preview.png',dpi=160)
print(json.dumps(report,indent=2))
