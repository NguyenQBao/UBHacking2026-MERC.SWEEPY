from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
import pymupdf
P=Path(__file__).resolve().parent
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
c=canvas.Canvas(str(P/'摄像头支架_装配与算法.pdf'),pagesize=(842,595))
def t(x,y,s,n=11):c.setFillColor(HexColor('#17394b'));c.setFont('STSong-Light',n);c.drawString(x,y,s)
def rect(x,y,w,h,col):c.setFillColor(HexColor(col));c.setStrokeColor(HexColor('#507688'));c.rect(x,y,w,h,fill=1)
def wrap(x,y,s,n=62):
 for i in range(0,len(s),n):t(x,y,s[i:i+n]);y-=18
 return y
for page in (1,2):
 t(28,555,'摄像头支架 v4 / '+('配套连接与安装' if page==1 else '单摄像头：局部视觉闭环'),21)
 t(28,22,f'OV5647 + 现有亚克力底盘 | 原型，未实际试装 | {page}/2',9)
 if page==1:
  # Front schematic in mm, frame above fork; angle not claimed as a set point.
  s=2.4;ox=160;oy=195
  rect(ox-30*s,oy,60*s,4*s,'#9ac4d4')
  for x in (-8.4,4.4):rect(ox+x*s,oy+4*s,4*s,74*s,'#9ac4d4')
  rect(ox-4*s,oy+64*s,8*s,26*s,'#e7c28d')
  rect(ox-18*s,oy+73*s,36*s,34*s,'#e7c28d')
  rect(ox-11*s,oy+80*s,22*s,20*s,'#ffffff')
  c.setStrokeColor(HexColor('#e05e34'));c.setLineWidth(3);c.line(ox-16*s,oy+70*s,ox+16*s,oy+70*s)
  t(35,480,'正视装配示意（省略绑带孔与细节）',12)
  t(35,163,'底座60×45，轴中心高70',11)
  t(35,143,'红线：M3贯穿螺栓；橙色：俯仰载框',11)
  t(380,490,'连接件与安装顺序',14)
  y=462
  for text in ['1. 先打00a、00b试片，确认8.8夹缝能容纳8厚耳片。','2. 底座扎带穿过亚克力原有长槽，避开散热片和轮子。','3. 载框耳片插入双耳，3.4孔对齐，M3螺栓配垫片/锁母。','4. 相机板边用非导电软垫及细绑带固定，不能压背面元件。','5. 固定前先看画面：刷前区域可见，排线不拉紧。','6. 先测10/20/30/50cm清晰度，确认后再固定高度与角度。']:
   y=wrap(380,y,text,30)-16
  wrap(35,100,'本套替代旧v3摄像头试件。打印实体采样角度无碰撞，不代表真实PCB、镜头、排线、螺栓和车身都已避让；安装后逐一核对。',68)
 else:
  y=500
  for title,body in [('找目标','桌面ROI -> HSV分割（先用明显颜色目标）-> 面积/形状过滤 -> 连续3帧确认同一个目标。'),('转向对准','目标在左：右轮更快；目标在右：左轮更快。入口中心要按刷子在画面的位置标定，不能默认等于画面中心。'),('短步靠近','慢速短脉冲移动，停稳后拍新画面再判断。接近收集区域减速，目标丢失或图像过期就停车。'),('收集复查','进入已标记收集带后，刷子配合限定时间推进。目标消失不等于收集成功，需看进盒过程或额外核验。'),('后续毫米定位','镜头固定后做畸变标定，再用桌面至少4个不共线已知点求平面映射。用独立测量点验证误差，仅在标定区内使用。'),('边界与保护','单摄像头不自动实现整桌定位或防跌落。用独立下视传感器，控制器设置命令超时停车，先在地面测试。')]:
   t(35,y,title,13);y=wrap(60,y-22,body,64)-20
  t(35,75,'详见同包《安装与单摄像头算法.md》，含标定条件、控制符号和测试顺序。',11)
 c.showPage()
c.save()
doc=pymupdf.open(P/'摄像头支架_装配与算法.pdf')
for i,p in enumerate(doc):p.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(P/f'page_{i+1}.png')
