"""METALSWEEP v3, units mm. pip install manifold3d numpy trimesh matplotlib"""
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

# Open-ended strap cradle, 26 mm clear width; not an exact TT screw mount.
p=box(74,34,3)
p+=box(74,4,10,(0,-15,2))
p+=box(74,4,10,(0,15,2))
for x in (-25,25):
    p=slot(p,x,0,12)
    for y in (-9,9):p=slot(p,x,y,9,4)
parts['05_motor_strap_cradle_x2']=p

# Brush version: front chassis notch avoids blocking the low collection ramp.
parts['01_base_x1'] -= box(46,76,8,(68,0,-1))
# Additional camera mast mount on upper deck; outside Pi nominal mounting area.
for y in (-15,15):parts['02_pi_deck_x1']=hole(parts['02_pi_deck_x1'],65,y)
# Collection tray: rear at X=-25, front mouth at X45 after X=10 translation.
p=box(70,80,28)-box(65,75,29,(0,0,2.5))
p-=box(8,70,28,(34,0,2.5))
for y in (-30,30):
    p+=box(14,12,4,(-40,y,0));p=hole(p,-40,y)
# When translated X10, ears match base X=-30,Y=+-30.
parts['08_brush_collection_tray_x1']=p
# Ramp wedge, high end at local X0, low end X50; printable flat underside.
# The assembly height remains adjustable until real wheel/brush measurements.
from manifold3d import Mesh
v=np.array([[0,-35,0],[50,-35,0],[50,35,0],[0,35,0],
            [0,-35,14],[50,-35,2],[50,35,2],[0,35,14]],dtype=np.float32)
f=np.array([[0,2,1],[0,3,2],[0,1,5],[0,5,4],[1,2,6],[1,6,5],
            [2,3,7],[2,7,6],[3,0,4],[3,4,7],[4,5,6],[4,6,7]],dtype=np.uint32)
p=M(Mesh(v,f))
# Side ears take adjustable clamps; final bracket depends on wheel ground height.
for y in (-40,40):
    p+=box(18,12,4,(8,y,0));p=hole(p,8,y)
parts['06_brush_ramp_trial_x1']=p
# Brush shaft support TEST plates, print flat; separate from motor torque mount.
# 3.4 mm slot is only a trial fit for a nominal 3 mm axle; not a bearing seat.
p=box(45,40,4)
p=slot(p,0,10,26,3.4)
for x in (-14,14):p=hole(p,x,-12)
parts['07_brush_support_trial_x2']=p
# Camera mast: flat vertical plate, 2 mounting holes; secured through angle feet.
p=box(24,70,4)
for y in (-25,25):p=hole(p,0,y)
parts['10_camera_mast_x1']=p
# Two universal L feet. Print with base on bed; horizontal holes may need cleaning.
p=box(24,20,4)+box(24,4,20,(0,8,0))
p=hole(p,0,-3)
p-=cyl(3.4,30).rotate((90,0,0)).translate((0,20,12))
parts['11_camera_angle_foot_x2']=p
# Wide open camera carrier, using loose insulated ties, not exact PCB hole claims.
p=box(36,34,3)-box(26,24,5,(0,0,-1))
for x in (-15.5,15.5):
    for y in (-6,6):p=hole(p,x,y,2.4)
# Side pivot tab; carrier pivots about an M3 bolt, angle set during focus test.
p+=box(12,12,3,(0,-21,0));p=hole(p,0,-21)
parts['12_camera_carrier_trial_x1']=p

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

# Cheap four-hole Pi pattern check before committing to a full upper deck.
p=box(70,61,2)-box(50,41,4,(0,0,-1))
for x in (-29,29):
    for y in (-24.5,24.5):p=hole(p,x,y,2.9)
parts['00b_pi_pattern_coupon_x1']=p

# Verify corner stack, front-notch clearance, tray and camera mounting bores.
for name in ('01_base_x1','02_pi_deck_x1'):
    for x,y in SUPPORTS:
        assert (parts[name] ^ cyl(3,10,x,y,-1)).volume()<1e-6,(name,x,y)
        if name=='01_base_x1':
            assert (parts[name] ^ cyl(10,4,x,y,0)).volume()>200
tray=parts['08_brush_collection_tray_x1'].translate((10,0,0))
for y in (-30,30):
    for q in (tray,parts['01_base_x1']):assert (q ^ cyl(3,10,-30,y,-1)).volume()<1e-6
for y in (-15,15):assert (parts['02_pi_deck_x1'] ^ cyl(3,10,65,y,-1)).volume()<1e-6

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
fig=plt.figure(figsize=(16,14),layout='constrained')
for i,(name,mesh) in enumerate(meshes.items(),1):
    ax=fig.add_subplot(4,4,i,projection='3d')
    light=np.array([.3,-.4,.85]);light/=np.linalg.norm(light)
    shade=.55+.45*np.maximum(0,mesh.face_normals@light)
    colors=np.column_stack((shade*.34,shade*.72,shade*.79,np.ones(len(shade))))
    ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolors=colors,edgecolor='none',linewidth=0))
    a,b=mesh.bounds;mid=(a+b)/2;r=max(mesh.extents)/2*1.15
    ax.set(xlim=(mid[0]-r,mid[0]+r),ylim=(mid[1]-r,mid[1]+r),zlim=(mid[2]-r,mid[2]+r))
    ax.set_box_aspect((1,1,1));ax.view_init(32,-55);ax.set_axis_off()
    ax.set_title(name+'\n'+' x '.join(f'{v:g}' for v in mesh.extents)+' mm',fontsize=9)
fig.suptitle('METALSWEEP v3 | Actual STL parts | Prototype / verify fit before full print',fontsize=17)
fig.savefig(OUT/'parts_preview.png',dpi=160)
print(json.dumps(report,indent=2))
