"""Assembly previews from the actual parametric solids; camera PCB/lens are proxies."""
from pathlib import Path
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import build_mount as b

P = Path(__file__).resolve().parent
FONT = FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
ANGLE, HEIGHT, FORWARD = 40, 90, 45
outer = b.FORK_GAP/2+b.FORK_T
pivot_y, pivot_z = b.PIVOT_Y-FORWARD, b.FOOT_T+HEIGHT
base = b.base_screw.rotate((0,0,-b.PLATE_T/b.BASE_PITCH*360)).translate((0,0,-b.PLATE_T-6))
mast = b.parts['02_mast_90mm_forward45_choose_one']
frame = b.camera_pose(b.frame,ANGLE,HEIGHT,FORWARD)
cover = b.camera_pose(b.retainer.translate((0,0,b.BACK_Z)),ANGLE,HEIGHT,FORWARD)
pcb = b.camera_pose(b.box(25,25,b.PCB_T,z=3),ANGLE,HEIGHT,FORWARD)
lens = b.camera_pose(b.cylinder(9,7,z=-4),ANGLE,HEIGHT,FORWARD)
bolt = b.pivot_screw.rotate((0,90,0)).translate((-outer-6,pivot_y,pivot_z))
nut = b.pivot_nut.rotate((0,0,2*outer/b.PIVOT_PITCH*360)).rotate((0,90,0)).translate((outer,pivot_y,pivot_z))
plate = b.box(78,65,b.PLATE_T,z=-b.PLATE_T)-b.cylinder(b.HOLE_D,b.PLATE_T+2,z=-b.PLATE_T-1)


def add(ax, solid, color, alpha=1):
    mesh = solid.simplify(.015).to_mesh64()
    vertices = np.asarray(mesh.vert_properties)[:,:3]
    faces = vertices[np.asarray(mesh.tri_verts)]
    ax.add_collection3d(Poly3DCollection(faces,facecolors=color,alpha=alpha,
                                       shade=True,lightsource=matplotlib.colors.LightSource(315,40)))


fig = plt.figure(figsize=(13,8),dpi=160)
fig.patch.set_facecolor('#f4f6f2')
for index, exploded in enumerate((False,True),1):
    ax = fig.add_subplot(1,2,index,projection='3d')
    ax.set_facecolor('#f4f6f2')
    add(ax,plate,'#b3c5c0',.28)
    add(ax,mast,'#287e72')
    add(ax,base.translate((0,0,-20 if exploded else 0)),'#a8b798')
    add(ax,frame,'#e3a346')
    add(ax,pcb,'#278b4e')
    add(ax,lens,'#21343b')
    offset = (0,12*math.cos(math.radians(ANGLE)),12*math.sin(math.radians(ANGLE))) if exploded else (0,0,0)
    add(ax,cover.translate(offset),'#eed0a3')
    add(ax,bolt.translate((-20 if exploded else 0,0,0)),'#9074aa')
    add(ax,nut.translate((20 if exploded else 0,0,0)),'#9074aa')
    if exploded:
        ax.plot([-38,36],[pivot_y,pivot_y],[pivot_z,pivot_z],ls=':',color='#829590',lw=1)
    ax.quiver(0,-62,0,0,-24,0,color='#166954',arrow_length_ratio=.18,lw=2)
    ax.text(0,-90,0,'车头',fontproperties=FONT,fontsize=10)
    view_y = pivot_y-20*math.cos(math.radians(ANGLE))-28*math.sin(math.radians(ANGLE))
    view_z = pivot_z-20*math.sin(math.radians(ANGLE))+28*math.cos(math.radians(ANGLE))
    ax.quiver(0,view_y,view_z,0,-25*math.cos(math.radians(ANGLE)),
              -25*math.sin(math.radians(ANGLE)),color='#226f54',arrow_length_ratio=.25,lw=2)
    ax.text(0,view_y-30,view_z-15,'镜头向前下',fontproperties=FONT,fontsize=9)
    ax.set(xlim=(-48,48),ylim=(-92,38),zlim=(-30,145))
    ax.set_box_aspect((96,130,175))
    ax.view_init(elev=23,azim=-42)
    ax.set_axis_off()
    ax.set_title('拆开看装配顺序' if exploded else '装好后：前伸立柱 + 可锁俯仰',fontproperties=FONT,fontsize=15,pad=8,color='#183a42')
fig.text(.05,.95,'全 3D 打印摄像头支架 · V7 试装版',fontproperties=FONT,fontsize=23,color='#183a42')
fig.text(.05,.90,'示例：90 mm 立柱 / 前伸 45 mm / 俯角 40°。绿色PCB与黑色镜头是示意，不包含在STL中。',fontproperties=FONT,fontsize=11,color='#5e7572')
fig.text(.06,.16,'① 底座塑料螺栓从亚克力下面穿入，拧进立柱底座。',fontproperties=FONT,fontsize=12,color='#183a42')
fig.text(.06,.12,'② 相机装入橙色托架；背面压框对准四个卡扣，先空架试扣。',fontproperties=FONT,fontsize=12,color='#183a42')
fig.text(.06,.08,'③ 托架放进叉耳，用紫色塑料螺栓与螺母锁定角度。',fontproperties=FONT,fontsize=12,color='#183a42')
fig.text(.06,.035,'只需选择一根立柱。先打00配合试件；图示不代表已适配实际PCB元件、排线及集尘盒。',fontproperties=FONT,fontsize=10,color='#5e7572')
fig.subplots_adjust(left=.03,right=.98,bottom=.20,top=.85,wspace=.03)
fig.savefig(P/'assembly_preview.png',facecolor=fig.get_facecolor())
fig.savefig(P/'assembly_preview.svg',facecolor=fig.get_facecolor())
print(P/'assembly_preview.png')
