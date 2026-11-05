"""Pi4/CSI debris candidate detector. OpenCV + Picamera2 + stdlib HTTP; no GPIO."""
import argparse
import base64
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
import json
import math
from pathlib import Path
import sys
import time
import cv2
import numpy as np

WIDTH, HEIGHT = 640, 480
DEFAULTS = dict(mode='background', threshold=28, min_area=40, max_area=20000,
                roi=[32, 96, 576, 360], hue_tolerance=12, sv_tolerance=65,
                max_aspect=0, min_fill_percent=0)

def settings(values, previous):
    if not isinstance(values, dict): raise ValueError('设置必须是对象')
    out = dict(previous)
    for key in values:
        if key not in DEFAULTS: raise ValueError('未知设置: '+key)
    out.update(values)
    if out['mode'] not in ('background', 'color'): raise ValueError('未知模式')
    bounds = {'threshold':(1,255), 'min_area':(1,50000), 'max_area':(1,200000),
              'hue_tolerance':(1,90), 'sv_tolerance':(1,255),
              'max_aspect':(0,100), 'min_fill_percent':(0,100)}
    for name,(lo,hi) in bounds.items():
        v=out[name]
        if type(v) is not int or not lo<=v<=hi: raise ValueError(name+'超出范围')
    if out['min_area']>out['max_area']: raise ValueError('最小面积不能超过最大面积')
    r=out['roi']
    if not isinstance(r,list) or len(r)!=4 or any(type(x) is not int for x in r): raise ValueError('区域格式错误')
    x,y,w,h=r
    if x<0 or y<0 or w<32 or h<32 or x+w>WIDTH or y+h>HEIGHT: raise ValueError('区域需在画面内且至少32×32')
    return out

def sample_color(frame,u,v):
    if type(u) is not int or type(v) is not int or not 0<=u<WIDTH or not 0<=v<HEIGHT:
        raise ValueError('取色点无效')
    hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
    patch=hsv[max(0,v-4):min(HEIGHT,v+5),max(0,u-4):min(WIDTH,u+5)].reshape(-1,3)
    sat=float(np.median(patch[:,1]));value=float(np.median(patch[:,2]))
    # Hue wraps at 180: ordinary median fails for red split across 179 and 0.
    angles=patch[:,0].astype(float)*math.pi/90
    hue=(math.atan2(np.mean(np.sin(angles)),np.mean(np.cos(angles)))*90/math.pi)%180
    return [float(hue),sat,value]

def detect(frame, background, color, cfg):
    if frame.shape!=(HEIGHT,WIDTH,3) or frame.dtype!=np.uint8: raise ValueError('需要640×480 BGR图像')
    view=frame.copy();mask=np.zeros((HEIGHT,WIDTH),np.uint8)
    x0,y0,w0,h0=cfg['roi'];roi=np.zeros_like(mask);roi[y0:y0+h0,x0:x0+w0]=255
    message=''
    if cfg['mode']=='background':
        if background is None: message='请清空区域，点击“拍空桌面参考”'
        else:
            # ponytail: static background only; use color/learned detection for a moving camera.
            difference=cv2.absdiff(cv2.GaussianBlur(frame,(5,5),0),cv2.GaussianBlur(background,(5,5),0))
            # Max channel difference also sees equal-brightness but differently coloured objects.
            _,mask=cv2.threshold(np.max(difference,axis=2),cfg['threshold'],255,cv2.THRESH_BINARY)
    elif color is None: message='点击“暂停并取色”，再点击目标的纯色区域'
    else:
        hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV).astype(np.float32)
        dh=np.abs(hsv[:,:,0]-color[0]);dh=np.minimum(dh,180-dh)
        hue_ok=(dh<=cfg['hue_tolerance']) if color[1]>=40 else np.ones_like(dh,dtype=bool)
        selected=hue_ok & (np.abs(hsv[:,:,1]-color[1])<=cfg['sv_tolerance']) & (np.abs(hsv[:,:,2]-color[2])<=cfg['sv_tolerance'])
        mask=selected.astype(np.uint8)*255
    mask=cv2.bitwise_and(mask,roi)
    kernel=np.ones((3,3),np.uint8)
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,kernel)
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel)
    fraction=cv2.countNonZero(mask)/(w0*h0)
    targets=[]
    limit=.25 if cfg['mode']=='background' else .65
    if fraction>limit:
        message='区域变化过大：背景模式检查相机/光照；颜色模式重新取色或缩小区域'
    elif not message:
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area=cv2.contourArea(contour)
            if not cfg['min_area']<=area<=cfg['max_area']: continue
            x,y,w,h=cv2.boundingRect(contour)
            aspect=max(w,h)/max(1,min(w,h))
            fill_percent=100*area/(w*h)
            if cfg['max_aspect'] and aspect>cfg['max_aspect']: continue
            if fill_percent<cfg['min_fill_percent']: continue
            m=cv2.moments(contour)
            if not m['m00']: continue
            u,v=m['m10']/m['m00'],m['m01']/m['m00']
            offset=u-WIDTH/2
            direction='LEFT' if offset<-20 else 'RIGHT' if offset>20 else 'CENTER'
            targets.append(dict(center_px=[round(u,1),round(v,1)],bbox_px=[x,y,w,h],
                                area_px=round(area,1),direction=direction,offset_x_px=round(offset,1),
                                aspect_ratio=round(aspect,2),fill_percent=round(fill_percent,1)))
        targets.sort(key=lambda t:t['area_px'],reverse=True);targets=targets[:20]
        message='检测到候选区域，需确认是碎屑' if targets else '没有候选碎屑'
    for i,t in enumerate(targets,1):
        x,y,w,h=t['bbox_px'];u,v=map(round,t['center_px'])
        cv2.rectangle(view,(x,y),(x+w,y+h),(0,220,0),2);cv2.circle(view,(u,v),3,(0,0,255),-1)
        cv2.putText(view,f"{i} {t['direction']}",(x,max(15,y-5)),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,220,0),1)
    cv2.rectangle(view,(x0,y0),(x0+w0-1,y0+h0-1),(255,180,0),1)
    cv2.line(view,(WIDTH//2,0),(WIDTH//2,HEIGHT-1),(0,210,255),1)
    return view,mask,dict(status=message,targets=targets,count=len(targets),mask_fraction=round(fraction,3))

def jpeg(array):
    ok,data=cv2.imencode('.jpg',array,[cv2.IMWRITE_JPEG_QUALITY,75])
    if not ok: raise RuntimeError('图像编码失败')
    return base64.b64encode(data).decode()

class Detector:
    def __init__(self,args):
        self.args=args;self.camera=None;self.cfg=dict(DEFAULTS);self.background=None;self.color=None
        self.frames=deque(maxlen=3);self.frame_id=0;self.image=None;self.lock=Lock()
        if args.image:
            self.image=cv2.imread(args.image)
            if self.image is None: raise ValueError('测试图片无法读取')
            self.image=cv2.resize(self.image,(WIDTH,HEIGHT))
        else:
            from picamera2 import Picamera2
            self.camera=Picamera2()
            try:
                # Picamera2 RGB888 produces B,G,R byte order for OpenCV.
                self.camera.configure(self.camera.create_video_configuration(main={'size':(WIDTH,HEIGHT),'format':'RGB888'},controls={'FrameRate':15}))
                self.camera.start();time.sleep(2)
            except Exception:
                self.close();raise
        if args.background:
            ref=cv2.imread(args.background)
            if ref is None: self.close();raise ValueError('参考图片无法读取')
            self.background=cv2.resize(ref,(WIDTH,HEIGHT))
            if args.rotate180:self.background=cv2.rotate(self.background,cv2.ROTATE_180)
    def frame(self):
        frame=self.image.copy() if self.image is not None else self.camera.capture_array('main')
        return cv2.rotate(frame,cv2.ROTATE_180) if self.args.rotate180 else frame
    def reference(self):
        if self.camera:
            meta=self.camera.capture_metadata();controls={'AeEnable':False,'AwbEnable':False}
            for key in ('ExposureTime','AnalogueGain','ColourGains'):
                if key in meta: controls[key]=meta[key]
            self.camera.set_controls(controls);time.sleep(.3)
        frames=[]
        for _ in range(5):frames.append(self.frame());time.sleep(.05)
        self.background=np.median(frames,axis=0).astype(np.uint8)
        return {'ok':True,'message':'参考已拍好；背景模式下车、相机及光照保持不变'}
    def state(self):
        begin=time.monotonic();frame=self.frame();self.frame_id+=1
        self.frames.append((self.frame_id,frame))
        view,mask,result=detect(frame,self.background,self.color,self.cfg)
        result.update(frame_id=self.frame_id,jpeg=jpeg(view),mask_jpeg=jpeg(cv2.resize(mask,(320,240))),
                      settings=self.cfg,color_ready=self.color is not None,background_ready=self.background is not None,
                      processing_ms=round((time.monotonic()-begin)*1000,1))
        return result
    def pick(self,request):
        for identifier,frame in self.frames:
            if identifier==request['frame_id']:
                self.color=sample_color(frame,request['u'],request['v']);self.cfg['mode']='color'
                return {'ok':True,'message':'已取色并切换颜色模式','hsv':self.color}
        raise ValueError('取色图像过期，请恢复预览后重新暂停取色')
    def close(self):
        if self.camera:
            try:self.camera.stop()
            finally:self.camera.close();self.camera=None

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)
    def log_message(self,*args): pass
    def reply(self,data,status=200,kind='application/json; charset=utf-8'):
        raw=data if isinstance(data,bytes) else (data.encode() if isinstance(data,str) else json.dumps(data,ensure_ascii=False,allow_nan=False).encode())
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        try:
            if self.path=='/':self.reply(Path(__file__).with_name('index.html').read_text(),kind='text/html; charset=utf-8')
            elif self.path=='/health':self.reply({'ok':True})
            elif self.path=='/raw.jpg':
                # A training photo must not contain the detector's boxes or mask.
                with self.server.detector.lock:
                    frame=self.server.detector.frame()
                    ok,encoded=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,95])
                    if not ok:raise RuntimeError('原图编码失败')
                    raw=encoded.tobytes()
                self.reply(raw,kind='image/jpeg')
            elif self.path=='/state':
                with self.server.detector.lock:
                    result=self.server.detector.state()
                self.reply(result)
            else:self.reply({'error':'not found'},404)
        except Exception as error:self.reply({'error':str(error)},500)
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=10000:raise ValueError('请求过大')
            data=json.loads(self.rfile.read(length) or '{}');d=self.server.detector
            with d.lock:
                if self.path=='/reference':result=d.reference()
                elif self.path=='/settings':d.cfg=settings(data,d.cfg);result={'ok':True,'settings':d.cfg}
                elif self.path=='/pick':result=d.pick(data)
                else:self.reply({'error':'not found'},404);return
            self.reply(result)
        except (ValueError,KeyError,TypeError) as error:self.reply({'error':str(error)},400)
        except Exception as error:self.reply({'error':str(error)},500)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',choices=('127.0.0.1','0.0.0.0'),default='127.0.0.1',
                        help='127.0.0.1 for local/SSH access; 0.0.0.0 for trusted LAN access')
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--image',help='optional offline test image')
    parser.add_argument('--background',help='optional offline empty reference image')
    parser.add_argument('--rotate180',action='store_true',help='rotate upside-down camera image')
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('端口应在1至65535')
    detector=None;server=None
    try:
        detector=Detector(args);server=ThreadingHTTPServer((args.host,args.port),Handler);server.detector=detector
        server.timeout=2
        if args.host=='0.0.0.0':
            print(f'局域网访问已开启：http://树莓派IP:{args.port}\n同网用户可看画面并修改检测设置；Ctrl+C停止。',flush=True)
        else:
            print(f'Pi4 debris detector: http://127.0.0.1:{args.port}\nMac浏览器通过SSH端口转发访问；Ctrl+C停止。',flush=True)
        server.serve_forever()
    except KeyboardInterrupt: pass
    except Exception as error:
        print(f'启动失败: {error}\n检查相机是否被其他程序占用；运行 rpicam-hello --list-cameras。',file=sys.stderr);return 1
    finally:
        if server:server.server_close()
        if detector:detector.close()
    return 0
if __name__=='__main__':sys.exit(main())
