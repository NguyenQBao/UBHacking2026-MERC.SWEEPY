from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
import pymupdf
P=Path(__file__).resolve().parent
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
c=canvas.Canvas(str(P/'V3_刷子版布局与组装.pdf'),pagesize=(842,595))
def t(x,y,s,n=11):c.setFont('STSong-Light',n);c.setFillColor(HexColor('#193b4c'));c.drawString(x,y,s)
def box(x,y,w,h,col):c.setFillColor(HexColor(col));c.setStrokeColor(HexColor('#537382'));c.rect(x,y,w,h,fill=1)
def wrap(x,y,s,n=62):
 for i in range(0,len(s),n):t(x,y,s[i:i+n]);y-=18
 return y
for n in [1,2]:
 t(28,558,'METALSWEEP v3 / 刷子收集版'+('：布局示意' if n==1 else '：组装与试装顺序'),21)
 t(28,20,f'单位mm | 试装原型，非完整验证整机 | 不按图量尺寸 | {n}/2',9)
 if n==1:
  # Top schematic: +X is toward right. roller and camera are placeholders.
  box(55,185,360,300,'#d3e9ee')
  box(325,259,90,152,'#ffffff')
  box(145,255,140,160,'#a6cdb2')
  t(150,335,'08 收集盒',12);t(150,315,'前口朝右 +X',10)
  box(285,265,100,140,'#ead19d');t(290,345,'06 斜坡试件',10)
  box(405,265,40,140,'#c8cbd0');t(420,420,'滚刷占位',11)
  t(420,400,'尺寸待实测',10)
  c.setStrokeColor(HexColor('#648898'));c.setDash(4,3);c.rect(85,215,300,240);c.setDash()
  for x in (105,365):
   for y in (239,431):c.circle(x,y,4,fill=0)
  t(110,190,'01 底盘 180×150；前方 +X →',11)
  t(92,465,'02 上板虚线；摄像头位于前上方',10)
  y=495
  for title,body in [('前方：刷子','滚刷与导料坡先试装，尚未提供适配真实电机和轴承的正式支架。'),('中间：收集盒','后端安装耳对齐底盘(-30,±30)。前部缺口避开导料坡。电池位置需重新干摆。'),('上方：摄像头','OV5647载框、立柱和角支架为试件。先测近距清晰度，再固定高度和俯角。'),('图中位置的含义','底盘、上板、盒子按模型尺寸示意；滚刷为占位。坡道安装高度及固定座待实测。')]:
   t(520,y,title,13);y=wrap(520,y-23,body,22)-25
  wrap(45,130,'滚刷的工作方向：把前方碎屑扫向车身内，经导料坡送入盒子。先用纸板确认路径；不要直接按占位图购买或加工滚刷。',64)
 else:
  y=500
  for title,body in [('1 先验证孔与配合','先打孔径试片、Pi四孔框、电机座/长柱/小垫柱各1。真实零件合格后才补数量。'),('2 确定行走与地面高度','用现成轮和万向轮确定底盘离地高度，纸板摆放滚刷、收集盒和电池。滚刷不应将车身顶起。'),('3 打印上下板并干装','支柱孔中心(±65,±48)，4+45+3=52高度堆叠。M3×60是候选长度，先加垫片螺母实测。Pi使用M2.5及6高隔离柱。'),('4 安装摄像头试件','载框用绝缘软垫避开背部元件，轻绑板边；不压镜头或排线。角支架连接若不匹配，应改转接片，不能强拧。'),('5 试验滚刷和坡道','轴承/电机座、坡道固定座尚未定型。先用夹具地面验证送料，确定轴径、滚刷直径、位置、扭矩和坡口离地间隙后再建正式件。'),('6 最后装收集盒与传感器','盒底放底盘顶面，中心X10；耳孔对齐(-30,±30)。先装1个下视传感器测试遮挡，再补齐。布线远离刷轴及轮子。'),('7 打印及运行放行','MK4S用实验室实际喷嘴/PLA预设，0.20层高起步。先看切片首层和悬空路径。没有完成防跌落地面验证前不在桌沿自动运行。')]:
   t(35,y,title,13);y=wrap(55,y-21,body,64)-18
 c.showPage()
c.save()
doc=pymupdf.open(P/'V3_刷子版布局与组装.pdf')
for i,p in enumerate(doc):p.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(P/f'assembly_page_{i+1}.png')
