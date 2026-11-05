from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
import pymupdf
P=Path(__file__).resolve().parent
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
c=canvas.Canvas(str(P/'圆孔20_摄像头25_组装图.pdf'),pagesize=(1000,750))
def t(x,y,s,n=12,col='#193a4b'):
 c.setFont('STSong-Light',n);c.setFillColor(HexColor(col));c.drawString(x,y,s)
def rect(x,y,w,h,col,stroke=True):
 c.setFillColor(HexColor(col));c.setStrokeColor(HexColor('#537284'));c.setLineWidth(.8);c.rect(x,y,w,h,fill=1,stroke=stroke)
def line(a,b,col='#537284',width=1):
 c.setStrokeColor(HexColor(col));c.setLineWidth(width);c.line(*a,*b)
def leader(a,b,s):

 if b[0]<100:
  line(a,(b[0]+200,b[1]));line((b[0]+200,b[1]),b);t(b[0],b[1]+8,s,11)
 else:
  line(a,b);t(b[0]+4,b[1]-3,s,11)
def wrap(x,y,s,n=56):
 for i in range(0,len(s),n):t(x,y,s[i:i+n],11);y-=17
 return y
for page in (1,2):
 t(28,710,'圆孔安装摄像头支架 v5 / '+('装配剖面示意' if page==1 else '打印清单与试装顺序'),23)
 t(28,682,'圆孔直径20；摄像头25×25；亚克力板厚暂按3。单位mm，不按页面比例量尺寸。',13)
 t(28,21,f'试装原型 | 未做实物装配、切片及承载验证 | 第{page}/2页',10)
 if page==1:
  ox,oy,s=230,245,3
  def at(y,z):return ox+y*s,oy+z*s
  # Acrylic slab shown cut at central 20-mm opening.
  rect(45,oy-.5*s,ox-30-45,3*s,'#dfedf2')
  rect(ox+30,oy-.5*s,470-(ox+30),3*s,'#dfedf2')
  # Placing plug tip at Z0, acrylic top Z2.5.
  rect(*at(-9.7,0),19.4*s,2.5*s,'#77b4c5')
  rect(*at(-20,2.5),40*s,4*s,'#77b4c5')
  # Under washer rests against actual underside at Z=-.5.
  rect(*at(-18,-3.5),36*s,3*s,'#e5bd7e')
  rect(*at(-2.25,-3.5),4.5*s,3*s,'#ffffff')
  # M4 head, metal washers, shaft, lower nut (schematic).
  rect(*at(-5,6.5),10*s,1*s,'#a8afb3')
  rect(*at(-3.5,7.5),7*s,3*s,'#7f8990')
  rect(*at(-2,-12.5),4*s,20*s,'#7f8990')
  rect(*at(-5,-4.5),10*s,1*s,'#a8afb3')
  rect(*at(-3.5,-7.7),7*s,3.2*s,'#7f8990')
  # Side view of one clevis cheek; carrier shown at zero pitch.
  rect(*at(9,6.3),8*s,68*s,'#77b4c5')
  rect(*at(5,60.5),26*s,12*s,'#e5bd7e')
  rect(*at(28,68),3*s,37*s,'#e5bd7e')
  # Indicative actual PCB outline, not a fabricated mounting-hole pattern.
  rect(*at(26.5,74),1.5*s,25*s,'#70a17b')
  c.setStrokeColor(HexColor('#b84d2f'));c.setFillColor(HexColor('#ffffff'));c.circle(*at(13,66.5),1.7*s,fill=1)
  line(at(24,86),at(-5,86),'#b84d2f',1.7)
  line(at(-5,86),at(-1,88),'#b84d2f',1.7);line(at(-5,86),at(-1,84),'#b84d2f',1.7)
  t(90,oy+87*s,'镜头朝 FRONT',12,'#b84d2f')
  leader(at(30,97),(375,565),'25×25模块：只示意外形，不代表PCB孔位')
  leader(at(13,66.5),(375,470),'M3俯仰轴；距底板上表面64')
  leader(at(14,4.5),(375,318),'01 上法兰直径40，厚4')
  leader(at(-8,1),(45,298),'定位柱直径19.4，长2.5')
  leader(at(-37,1),(45,210),'亚克力3厚；定位孔直径20')
  leader(at(15,-2),(375,190),'03 下垫片直径36，厚3')
  leader(at(0,-6),(375,145),'M4螺栓、金属垫片、锁紧螺母')
  t(45,101,'剖面示意：上下夹紧亚克力；定位柱不接触下垫片。',13)
  t(45,78,'静态竖直姿态示意，实际拍摄角度要看画面调整。',12)
  # Right notes, avoids crossing drawing callouts.
  rect(630,150,340,480,'#f0f5f7')
  y=602
  for title,body in [('尺寸与避空','孔径20来自你的描述。板厚3为暂定值。法兰需孔周围直径40平整区域，下垫片需底板下方36直径空间。'),('保护亚克力','M4只轻夹到不晃动。孔径偏紧或柱顶死时先改模型，不用拧紧来补救。'),('保护相机','载框使用细绑带与非导电软垫固定裸板边缘；背面元件、排线座和镜头不能被压住。'),('固定后再标定','圆孔安装可能转动，先检查抗转及振动。稳定后再做单摄像头桌面距离标定。')]:
   t(648,y,title,14);y=wrap(648,y-23,body,23)-25
 else:
  y=625
  rows=[('00a 定位柱试件','1','先试19.4柱能否自由进入20孔；不要硬塞。'),('00b / 00c 俯仰试件','各1','检查8.8叉口、8厚耳片、M3螺丝配合。'),('01 底座＋立柱','1','定位柱朝下打印；法兰底面环形悬空区加平台支撑。'),('02 摄像头俯仰框','1','框体平面朝下、连接耳朝上；横孔按切片情况局部支撑。'),('03 下垫片','1','平放打印；中心孔4.5配M4。')]
  for title,num,note in rows:
   rect(28,y-62,944,72,'#f0f5f7');t(42,y-10,title,15);t(360,y-10,'数量 '+num,13);t(42,y-38,note,12);y-=85
  y=wrap(35,174,'紧固件候选：M4×20螺栓、M4锁母及金属平垫片；M3×25螺栓、M3锁母及金属平垫片。长度需试装核对。',68)-8
  y=wrap(35,y,'顺序：先3个小试件 → 3个正式件 → 上法兰插入孔 → 下方放垫片并轻夹紧 → 安装俯仰框和相机 → 实时画面调角。',68)
  wrap(35,y-10,'MK4S：先用实验室PLA预设，0.20层高、4至5圈外壁、25%填充起步。最重要的是01法兰底面需要支撑；清理后再检查接触面及定位柱。',68)
 c.showPage()
c.save()
doc=pymupdf.open(P/'圆孔20_摄像头25_组装图.pdf')
for i,p in enumerate(doc):p.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(P/f'assembly_page_{i+1}.png')
