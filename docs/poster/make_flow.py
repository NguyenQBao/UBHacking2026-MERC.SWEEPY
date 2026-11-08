"""Poster diagram: python3 make_flow.py -> system-flow.svg (render PNG with any browser, 2x scale)."""
import html
W,H=1800,1120
C={'train':('#1d7a56','#e6f4ee'),'perc':('#2558a8','#e8eff9'),'dec':('#b06a10','#fdf2e2'),'act':('#a1323b','#fbe9ea'),'ink':'#16262c','mute':'#55666b'}
out=[]
def t(x,y,s,size=15,w='400',fill=C['ink'],anchor='start'):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{html.escape(s)}</text>')
def box(x,y,w,h,kind,num,title,lines):
    s,f=C[kind]
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{f}" stroke="{s}" stroke-width="2"/>')
    out.append(f'<circle cx="{x+24}" cy="{y+26}" r="14" fill="{s}"/>')
    t(x+24,y+31,num,14,'700','#fff','middle')
    t(x+46,y+32,title,19,'700',s)
    for i,l in enumerate(lines): t(x+18,y+60+i*21,l,14.5)
def arrow(pts,color='#4a5a60',dash=False,label=None,lx=None,ly=None,anchor='middle'):
    d='M'+' L'.join(f'{a},{b}' for a,b in pts)
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5" {"stroke-dasharray=\"7 6\"" if dash else ""} marker-end="url(#a{color[1:]})"/>')
    if label: t(lx,ly,label,13.5,'600',color,anchor)
cols=[(40,'train','OFFLINE · TRAINING LOOP','Pi collects photos, Mac labels and trains'),
      (490,'perc','ONBOARD PERCEPTION','Raspberry Pi 4B, every frame'),
      (940,'dec','DECISION · CLOSED LOOP','one target per cycle, re-look after every move'),
      (1390,'act','ACTUATION & OPERATOR','GPIO outputs, human in the loop')]
BW=370;BH=112;Y0=190;G=26
for x,k,title,sub in cols:
    t(x,136,title,17,'800',C[k][0]); t(x,156,sub,13.5,'400',C['mute'])
markers=''.join(f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in ['#4a5a60',C['train'][0],C['perc'][0],C['dec'][0],C['act'][0]])
ys=[Y0+i*(BH+G) for i in range(5)]
train=[('Collect','Pi data collector (:8092)','train / val / test by scene, ~20% empty floor'),
       ('Label','Training studio (:8090) on Mac','tight box per debris, confirm empty shots'),
       ('Train YOLO11n','single class "debris", 640 px','fresh or cumulative, keep best epoch'),
       ('Evaluate','independent test scene','Precision · Recall · mAP50'),
       ('Export NCNN','~10 MB model for ARM CPU','copy to Pi, run.py --model')]
perc=[('Camera','OV5647 CSI, 640×480','mounted on post, tilted to floor'),
      ('Detect','YOLO11n NCNN → boxes + score','keep score ≥ 0.4  (≈0.3–0.7 s / frame)'),
      ('Ground mapping','homography from 6+ ruler points','pixel → X,Y mm from scoop (fit 2.6 mm)'),
      ('Track target','nearest target, match by centre','must persist 2–3 fresh frames')]
dec=[('Observe','target inside 0 < Y ≤ 700 mm?','none / lost → stop, never search blind'),
     ('Align','turn ≈4° steps toward target','until |angle| ≤ 6° and |X| ≤ 15 mm'),
     ('Approach','drive ≈5 cm step, stop, re-look','repeat until Y ≤ 200 mm'),
     ('Collect','brush spin-up 0.35 s → blind push','t = (Y + 40) / 483 mm/s → brush tail'),
     ('Stop & verify','car parks, operator checks scoop','start next cycle manually')]
act=[('Drive wheels','L298N H-bridge, PWM','R: 17/27/18 · L: 22/23/13'),
     ('Brush','relay GPIO21 → CCM6N → 12 V motor','bristles sweep debris onto scoop'),
     ('Buzzer','GPIO12','short beep when debris appears'),
     ('Operator panel','web page :8091 · live view','sliders, STOP / Space, heartbeat')]
for (x,k,*_),items in zip(cols,[train,perc,dec,act]):
    for i,(ti,a,b) in enumerate(items): box(x,ys[i],BW,BH,k,str(i+1),ti,[a,b])
# vertical flow arrows inside columns
for x,n,col in ((40,5,C['train'][0]),(490,4,C['perc'][0]),(940,5,C['dec'][0])):
    for i in range(n-1): arrow([(x+BW/2,ys[i]+BH),(x+BW/2,ys[i+1]-3)],col)
# training feedback loop
lx=40-0
arrow([(40,ys[3]+BH/2),(22,ys[3]+BH/2),(22,ys[0]+BH/2),(37,ys[0]+BH/2)],C['train'][0],True)
out.append(f'<text transform="translate(16,{(ys[0]+ys[3])/2+BH/2}) rotate(-90)" font-size="13.5" font-weight="600" fill="{C["train"][0]}" text-anchor="middle">misses &amp; false alarms → shoot more</text>')
# deploy arrow: Export -> Detect
ex=40+BW; arrow([(ex,ys[4]+BH/2),(450,ys[4]+BH/2),(450,ys[1]+BH/2),(487,ys[1]+BH/2)],C['train'][0],False,'deploy model',452,ys[4]+BH/2-10,'start')
# perception -> decision
arrow([(490+BW,ys[3]+BH/2),(905,ys[3]+BH/2),(905,ys[0]+BH/2),(937,ys[0]+BH/2)],C['perc'][0])
out.append(f'<text transform="translate(898,{ys[2]+BH/2}) rotate(-90)" font-size="13.5" font-weight="600" fill="{C["perc"][0]}" text-anchor="middle">target X,Y (mm)</text>')
# decision -> actuation
arrow([(940+BW,ys[1]+BH/2),(1387,ys[0]+BH/2)],C['dec'][0])
arrow([(940+BW,ys[2]+BH/2),(1387,ys[0]+BH/2+22)],C['dec'][0])
arrow([(940+BW,ys[3]+BH/2),(1387,ys[1]+BH/2)],C['dec'][0])
t(1318,ys[3]+BH/2+24,'brush +',13.5,'600',C['dec'][0]); t(1318,ys[3]+BH/2+41,'push',13.5,'600',C['dec'][0])
# detect -> buzzer
arrow([(490+BW/2+60,ys[1]+BH),(490+BW/2+60,ys[1]+BH+12),(1365,ys[1]+BH+12),(1365,ys[2]+BH/2),(1387,ys[2]+BH/2)],C['perc'][0],True)
# re-observe feedback from Approach back to Camera
arrow([(940,ys[2]+BH-22),(924,ys[2]+BH-22),(924,180),(490+BW/2,180),(490+BW/2,ys[0]-3)],C['dec'][0],True)
t(700,174,'re-look after every move',13.5,'600',C['dec'][0])
t(940+BW/2-140,ys[0]-8,'',1)
# operator panel -> decision (stop)
arrow([(1390,ys[3]+BH-20),(1340,ys[4]+BH/2),(1313,ys[4]+BH/2)],C['act'][0],True,'STOP any time',1330,ys[4]+BH+18,'middle')
# safety band
sy=ys[4]+BH+50
out.append(f'<rect x="40" y="{sy}" width="{W-80}" height="70" rx="12" fill="#f3f5f6" stroke="#c7d0d3"/>')
t(60,sy+28,'SAFETY LAYER',15,'800',C['ink'])
t(60,sy+52,'Short motor leases auto-expire  ·  stale frame → wait  ·  target lost / identity jump → stop  ·  step & time limits  ·  page loses focus → stop  ·  config validated before GPIO opens',14.5,'400',C['mute'])
# key numbers
ky=sy+92
nums=[('483 mm/s','calibrated forward speed'),('142 mm','camera blind zone → blind final push'),('≤ 700 mm','tracking range'),('2.6 mm','ground fit residual'),('0.89','typical debris score on car')]
cw=(W-80)/len(nums)
for i,(a,b) in enumerate(nums):
    x=40+i*cw
    out.append(f'<rect x="{x+4}" y="{ky}" width="{cw-8}" height="74" rx="10" fill="#fff" stroke="#c7d0d3"/>')
    t(x+cw/2,ky+34,a,24,'800',C['ink'],'middle'); t(x+cw/2,ky+58,b,13.5,'400',C['mute'],'middle')
H=ky+100
head=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica Neue, Helvetica, Arial, sans-serif"><defs>{markers}</defs><rect width="{W}" height="{H}" fill="#ffffff"/>'
t(40,64,'METALSWEEP',40,'800',C['ink'])
t(40,98,'Vision-guided debris-collecting robot: how detection, calibration, control and training connect',18,'400',C['mute'])
open(__import__('pathlib').Path(__file__).with_name('system-flow.svg'),'w').write(head+''.join(out)+'</svg>')
print(W,H)
