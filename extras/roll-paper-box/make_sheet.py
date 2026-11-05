from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
import pymupdf
P=Path(__file__).resolve().parent
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
c=canvas.Canvas(str(P/'卷纸盒_尺寸与打印说明.pdf'),pagesize=(842,595))
def t(x,y,s,n=11):c.setFillColor(HexColor('#193d50'));c.setFont('STSong-Light',n);c.drawString(x,y,s)
def rect(x,y,w,h,col):c.setFillColor(HexColor(col));c.setStrokeColor(HexColor('#426d7f'));c.rect(x,y,w,h,fill=1)
def wrap(x,y,s,n=20):
 for i in range(0,len(s),n):t(x,y,s[i:i+n],10);y-=16
 return y

t(28,555,'粘贴式卷纸盒 / 普通卫生纸卷试装版',22)
t(28,527,'暂定适用：纸卷长度不超过115，满卷外径不超过120；单位mm，示意图不按比例量尺寸。',11)
s=1.5
rect(40,230,126*s,135*s,'#bcdae3')
rect(40+5*s,230+123*s,116*s,12*s,'#ffffff')
# lid floats above the body to indicate removability
rect(40,230+145*s,126*s,3*s,'#69a6bc')
t(40,471,'01 正面：上缘出纸口',13)
t(49,405,'116 × 12 出纸口',10)
t(65,330,'126 宽 × 135 高',11)
t(48,213,'上盖可取下，无刀片、无锁扣',10)
rect(295,230,126*s,132*s,'#bcdae3')
rect(295+3*s,230+3*s,120*s,126*s,'#ffffff')
# outlet interruption at front of open top
rect(295+5*s,230-1,116*s,3*s+1,'#ffffff')
t(295,471,'02 俯视：打开上盖',13)
t(310,345,'内腔 120 × 126',11)
t(310,324,'壁厚与底厚 3',11)
t(306,213,'纸卷轴向沿左右126方向',10)
y=480
for title,body in [('打印件','盒体×1、上盖×1；先打印两个小配合试片，确认每侧0.4间隙适合该机。'),('怎么打印','MK4S：PLA预设，0.20层高，4圈外壁。盒口朝上，上盖大平面朝下，导入100%毫米。'),('出纸方式','出口在前壁上缘，开口一直到顶部，避免长距离悬空桥接；纸头从此处拉出。'),('怎么粘贴','后壁为完整平面，可按胶带说明粘在合适竖直面。胶粘承重与抽纸剥离力均未验证。')]:
 t(555,y,title,12);y=wrap(555,y-21,body,23)-18
wrap(35,165,'装配：上盖打印时定位裙边向上，安装时翻面，使裙边插入盒口。让上盖裙边缺口与盒体出纸口朝同一侧。先试片，再打印盒体，最后打印盖。',68)
wrap(35,107,'尺寸检查：纸卷长度应小于内宽120，并保留侧向余量；满卷直径应小于内深126。建议115×120以内。大卷厨房纸需改尺寸，不要整体缩放模型。',68)
t(28,25,'原型图 | 网格及出纸通道检查通过，未做实际切片、打印、胶粘承重和抽纸测试',10)
c.save()
doc=pymupdf.open(P/'卷纸盒_尺寸与打印说明.pdf');doc[0].get_pixmap(matrix=pymupdf.Matrix(1.4,1.4)).save(P/'box_drawing.png')
