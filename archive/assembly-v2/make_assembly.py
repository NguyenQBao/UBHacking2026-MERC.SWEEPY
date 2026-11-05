from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
import fitz
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/'metalsweep-print-v2'
# Transform exported positive-coordinate STL back into v2 assembly coordinates.
items=[('01_base_x1',(-90,-75,0),'01 BASE', '#75b9c4'),('02_pi_deck_x1',(-75,-60,95),'02 PI DECK','#75b9c4')]
for x in (-65,65):
 for y in (-48,48):items.append(('03_column_45mm_x4',(x-6,y-6,25),'03 COLUMN','#e4a355'))
for x in (-29,29):
 for y in (-24.5,24.5):items.append(('04_pi_spacer_6mm_x4',(x-3.5,y-3.5,116),'04 PI SPACER','#dbb77a'))
items += [('06_detector_boom_x1',(15,-12,4),'06 BOOM','#69aa93'),('08_collection_tray_x1',(-37,25,4),'08 TRAY','#69aa93')]
# Deterministic assembly schematic using model dimensions; exploded Z exaggerated.
from matplotlib.patches import Polygon, Ellipse
fig,ax=plt.subplots(figsize=(11,7),layout='constrained')
def project(x,y,z):return np.array([x-.55*y,.30*x+.34*y+z])
def plate(x0,y0,w,d,z,h,color):
 top=[project(x,y,z+h) for x,y in [(x0,y0),(x0+w,y0),(x0+w,y0+d),(x0,y0+d)]]
 bottom=[project(x,y,z) for x,y in [(x0,y0),(x0+w,y0),(x0+w,y0+d),(x0,y0+d)]]
 for ids in ((0,1),(1,2)):
  i,j=ids;ax.add_patch(Polygon([bottom[i],bottom[j],top[j],top[i]],facecolor='#628897',edgecolor='#355667',linewidth=.8))
 ax.add_patch(Polygon(top,facecolor=color,edgecolor='#355667',linewidth=.8))
 return top
plate(15,-12,140,24,4,6,'#a7cdb9')
plate(-37,25,74,55.5,4,28,'#bad9c6')
plate(-90,-75,180,150,0,4,'#b1dce2')
for x in (-65,65):
 for y in (-48,48):
  p1=project(x,y,4);p2=project(x,y,95)
  ax.plot([p1[0],p2[0]],[p1[1],p2[1]],':',color='#82939d',linewidth=.7)
  plate(x-6,y-6,12,12,25,45,'#e6b36a')
plate(-75,-60,150,120,95,3,'#b1dce2')
for x in (-65,65):
 for y in (-48,48):ax.add_patch(Ellipse(project(x,y,98),5,2.6,facecolor='white',edgecolor='#355667',linewidth=.6))
for x in (-29,29):
 for y in (-24.5,24.5):
  plate(x-3.5,y-3.5,7,7,116,6,'#e6b36a')
for pos,t,off in [((-90,-75,0),'01 BASE',(0,-25)),((-75,-60,98),'02 DECK',(-50,20)),((65,-48,50),'03 x4',(30,0)),((29,-24.5,122),'04 x4',(45,25)),((145,-12,10),'06 BOOM',(30,5)),((-37,80,30),'08 TRAY',(-80,10))]:
 p=project(*pos);ax.annotate(t,p,xytext=p+off,arrowprops={'arrowstyle':'-','color':'#355667'},fontsize=11,color='#163446')
ax.set_aspect('equal');ax.autoscale_view();ax.margins(.18);ax.axis('off')
ax.set_title('V2 ASSEMBLY SCHEMATIC / exploded spacing / slots omitted',fontsize=13)
fig.savefig(ROOT/'exploded_view.png',dpi=180);plt.close(fig)

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
W,H=842,595
c=canvas.Canvas(str(ROOT/'METALSWEEP_v2_组装图纸.pdf'),pagesize=(W,H))
c.setTitle('METALSWEEP v2 Assembly / 组装图纸')
def txt(x,y,s,size=11,color='#163446'):
 c.setFillColor(HexColor(color));c.setFont('STSong-Light',size);c.drawString(x,y,s)
def line(x,y,a,b,col='#5b8497'):
 c.setStrokeColor(HexColor(col));c.setLineWidth(.8);c.line(x,y,a,b)
def page(n,title):
 c.setFillColor(HexColor('#f1f6f8'));c.rect(0,0,W,H,fill=1,stroke=0)
 txt(28,558,title,21);line(28,540,814,540)
 txt(28,18,'METALSWEEP v2 | 单位 mm | 装配原型，未实物验证 | 不按页面比例量尺寸',9)
 txt(770,18,f'{n} / 3',9)
def wrap(x,y,s,width=38,size=11,leading=17):
 for i in range(0,len(s),width):txt(x,y,s[i:i+width],size);y-=leading
 return y
page(1,'01 / 结构爆炸示意与零件编号')
c.drawImage(str(ROOT/'exploded_view.png'),20,105,width=555,height=410,preserveAspectRatio=True,anchor='c',mask='auto')
y=510
for title,body in [ ('01 底盘 ×1','180×150×4。前方为 +X；装配基准为底盘中心。'),('03 支柱 ×4','45高，配上下板四角孔；爆炸图拉大了层间距。'),('02 上板 ×1','150×120×3。装配时底面 Z=49，顶面 Z=52。'),('04 Pi垫柱 ×4','6高。实际安装在上板顶面，Pi底面约 Z=58。'),('06 探测臂 ×1','图中按实际位置置于底盘顶面；线圈未建模。'),('08 收集盒 ×1','图中侧置，耳孔匹配底盘；不是自动收集通道。')]:
 txt(586,y,title,12);y=wrap(586,y-20,body,19,10,15)-16
wrap(35,84,'图为按模型尺寸绘制的装配示意，省略长孔和细节。树莓派、电机、轮子、电池、传感器、磁吸机构及紧固件未作为实体建模。',70,11)
c.showPage()
page(2,'02 / 孔位平面图与装配高度')
# 2D assembly plan with coordinates, no invented mechanical interfaces.
ox,oy,sc=255,285,1.7
def xy(x,y):return ox+x*sc,oy+y*sc
c.setFillColor(HexColor('#d9eef1'));c.setStrokeColor(HexColor('#426b7e'))
c.rect(*xy(-90,-75),180*sc,150*sc,fill=1,stroke=1)
c.setDash(4,3);c.rect(*xy(-75,-60),150*sc,120*sc,fill=0,stroke=1);c.setDash()
for x in (-65,65):
 for y in (-48,48):
  c.setFillColor(HexColor('#dc9d45'));c.circle(*xy(x,y),4,fill=1,stroke=0)
  txt(*xy(x-13,y+7),f'{x},{y}',8)
# boom / tray outlines at their exact bounding placements
c.setFillColor(HexColor('#a8d2bf'));c.rect(*xy(15,-12),140*sc,24*sc,fill=1,stroke=1)
c.rect(*xy(-35,35.5),70*sc,45*sc,fill=1,stroke=1)
for x,y in [(30,0),(60,0),(-30,30),(30,30)]:
 c.setFillColor(HexColor('#c45d38'));c.circle(*xy(x,y),3.5,fill=1,stroke=0)
 txt(*xy(x-10,y+6),f'{x},{y}',8)
line(*xy(0,-85),*xy(0,90));line(*xy(-100,0),*xy(165,0))
txt(*xy(165,6),'+X 前',10);txt(*xy(3,91),'+Y',10)
txt(*xy(-87,-71),'BASE 180 x 150',10);txt(*xy(62,-54),'DECK',8)
txt(600,504,'侧面高度堆叠（轮子未计入）',13)
y=475
for s in ['Z=58：Pi 底面（含6高隔离柱）','Z=52：上板顶面','Z=49：上板底面','Z=4 至49：45高支柱','Z=0 至4：底盘','Z=4：探测臂 / 收集盒底面']:
 txt(600,y,s,10);y-=25
wrap(600,302,'四角使用 M3 贯通紧固。4+45+3=52 mm，M3×60可作为试装候选；加垫片螺母后实测余量。',20,11)
wrap(600,215,'Pi四孔中心距58×49。M2.5螺丝配6高垫柱；长度需计入真实PCB、上板和螺母。',20,11)
wrap(45,92,'图例：橙色=上下板连接孔；红色=附件指定连接点；虚线=上板轮廓。坐标以底盘中心为(0,0)，不是STL文件的最小角。',71,11)
c.showPage()
page(3,'03 / 按顺序组装与检查')
steps=[('1. 先干装试片','用00孔径试片和00b四孔框检查M3/M2.5及真实Pi。孔不合适先改孔补偿，不整体缩放模型。'),('2. 底盘、电机和支撑轮','05电机座先试一个，放底盘下方两侧并用绑带试固定。轮轴、轮径、万向轮位置待实物确定；先保证两驱动轮和支撑轮稳定落地。'),('3. 安装探测臂与侧盒','06臂中心置于X=85,Y=0，近端槽对准底盘(30,0)、(60,0)，M3螺丝和宽垫片夹紧。08盒中心Y=58，耳孔对齐(±30,30)。螺丝长度按堆叠实测。'),('4. 电池与电机驱动','放在下层，用绝缘绑带固定。留出支柱和螺母空间，电池封装不能被锐边或螺丝挤压。先检查上板45 mm净空。'),('5. 支柱、上板与Pi','03四支柱放四角，装02上板，先松装四根贯通螺丝，全部自然对孔后交替轻拧。04垫柱隔开Pi，PCB不承受弯曲。'),('6. 线圈与传感器','07垫板用扎带固定实际线圈壳体；09先试一个传感器，确定下视方向、离地高度和轮子遮挡后再装余件。具体模块孔位未适配。'),('7. 上电前后检查','先手转轮、检查线缆及螺丝不碰电路。地面低速验证驱动与桌沿检测，测探测线圈受电机和磁体的干扰；未验证前不在桌沿自动运行。')]
y=505
for title,body in steps:
 txt(35,y,title,12);y=wrap(58,y-19,body,65,10,15)-13
c.showPage();c.save()
doc=fitz.open(ROOT/'METALSWEEP_v2_组装图纸.pdf')
for i,p in enumerate(doc):p.get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(ROOT/f'page_{i+1}.png')
print('Created 3-page PDF and rendered pages')
