from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
import pymupdf
P=Path(__file__).resolve().parent
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
c=canvas.Canvas(str(P/'树莓派4B_L298N_双官方原图接线.pdf'),pagesize=(1120,850))
def t(x,y,s,n=13,col='#18384c'):
 c.setFont('STSong-Light',n);c.setFillColor(HexColor(col));c.drawString(x,y,s)
def box(x,y,w,h,col='#eef4f7'):
 c.setFillColor(HexColor(col));c.setStrokeColor(HexColor('#71909e'));c.roundRect(x,y,w,h,7,fill=1)
def img(n,x,y,w,h):c.drawImage(str(P/n),x,y,w,h,preserveAspectRatio=True,anchor='c',mask='auto')
def line(a,b,col='#78929e',width=1):c.setStrokeColor(HexColor(col));c.setLineWidth(width);c.line(*a,*b)
def link(x,y,label,url):
 t(x,y,label,10,'#286c95');c.linkURL(url,(x,y-2,x+len(label)*10,y+12),relative=0)
rows=[('2','5V 电源','+5V（见红色条件）'),('6','GND','GND'),('12','GPIO18','ENA'),('11','GPIO17','IN1'),('13','GPIO27','IN2'),('15','GPIO22','IN3'),('16','GPIO23','IN4'),('33','GPIO13','ENB')]
t(28,810,'树莓派 4B + L298N：两端均使用官方原图',26)
t(28,780,'左：Raspberry Pi 官方4B照片；右：SunFounder官方引脚照片。接线表是本项目的连接方案。',14)
# Preserve originals without repainting electronic parts.
box(25,336,420,410,'#ffffff');t(42,719,'树莓派 4 Model B：官方实物照片',17)
img('RaspberryPi_4B_官方照片.jpg',35,392,400,305)
t(42,372,'GPIO 40针位于板边，先确认Pin 1再数脚。',13)
t(42,349,'具体数字位置请翻到第2页的官方放大图。',13)
box(730,336,365,410,'#ffffff');t(748,719,'L298N：SunFounder官方引脚图',16)
img('SunFounder_原始引脚图.jpg',740,360,345,335)
# table between the original photographs
box(460,336,255,410,'#f0f6f9');t(475,718,'逐线连接对照',18)
t(475,690,'Pi物理脚 / 功能 → 驱动板',12)
y=657
for pin,gpio,port in rows:
 t(475,y,f'{pin} / {gpio}',13);t(599,y,'→ '+port,12,'#bd342b' if pin=='2' else '#18384c')
 line((470,y-10),(705,y-10),'#c8d6df');y-=36
box(25,251,1070,65,'#fff0d9')
t(40,290,'本方案先全部断电，取下 ENA、ENB、5V-EN 三个跳帽。',17,'#9d341e')
t(40,267,'只有确认5V-EN稳压跳帽已取下，才把Pi物理2脚的5V接入驱动板+5V；GPIO针脚不能接5V。',14,'#9d341e')
# Power/output summary no inferred cable-colour or connector placement.
box(25,92,520,140);t(42,205,'电源',18)
t(42,178,'Pi：独立稳压5V / 3A，经USB-C供电。',14)
t(42,153,'电机电源：正极经开关接12V/VS端，负极接GND。',14)
t(42,128,'Pi GND、驱动板GND、电机电源负极共地。',14)
t(42,103,'电机电压待核对，电机电源先不接通；正极不互连。',13,'#a44022')
box(560,92,535,140);t(578,205,'电机与摄像头',18)
t(578,178,'OUT1 + OUT2：左侧一台；OUT3 + OUT4：右侧一台。',14)
t(578,153,'官网图右侧上OUT4、下OUT3；四电机并联先核对电流。',13)
t(578,128,'摄像头排线 → Pi CAMERA / CSI，不接GPIO排针。',14)
t(578,103,'滚刷需额外驱动通道。首次电机测试架空车轮。',13)
link(28,60,'Raspberry Pi官方文档','https://www.raspberrypi.com/documentation/computers/raspberry-pi.html')
link(410,60,'SunFounder官方文档','https://docs.sunfounder.com/projects/3in1-kit-v2/en/latest/components/component_l298n_module.html')
t(28,26,'官方原图嵌入排版，未重新绘制板上元件；端子按自己板上的丝印核对。第1/2页',11)
c.showPage()
# Full official pin map, retains image geometry and existing labels.
t(28,810,'树莓派官方40针引脚图：适用于 Raspberry Pi 4B',24)
t(28,781,'原图中的板形是通用示意；接线按圈内物理编号1–40核对。功能名GPIO17对应物理11脚。',14)
img('RaspberryPi_官方40针引脚图.png',25,220,1070,540)
box(25,96,1070,100)
t(42,172,'本项目使用的物理脚：2、6、11、12、13、15、16、35。',18)
t(42,142,'软件写GPIO18，杜邦线实际插物理12脚；软件写GPIO13，杜邦线实际插物理33脚。',15)
t(42,115,'官方图内 3V3 power 是3.3V电源，不是本方案的5V逻辑供电。2脚5V电源也不是GPIO2。',14,'#a44022')
link(28,62,'来源：Raspberry Pi官方硬件文档 / GPIO','https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio')
t(28,26,'原始官方引脚图保留完整；第2/2页。断电接线，查清跳帽和电机电压后再上电。',11)
c.showPage();c.save()
doc=pymupdf.open(P/'树莓派4B_L298N_双官方原图接线.pdf')
for i,p in enumerate(doc):p.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(P/f'4B_双官方原图_第{i+1}页.png')
