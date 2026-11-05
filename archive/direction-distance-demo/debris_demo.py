"""Stationary-camera debris direction + planar range demo. No GPIO/motor access."""
import argparse, base64, json, math, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import cv2
import numpy as np

W,H=640,480

def make_calibration(points,width,depth,near):
    p=np.asarray(points,dtype=np.float32)
    vals=np.array([width,depth,near],dtype=float)
    if p.shape!=(4,2) or not np.isfinite(p).all() or not np.isfinite(vals).all():
        raise ValueError('需要4个有效点和有限尺寸')
    if width<=0 or depth<=0 or near<0 or np.any(p<0) or np.any(p[:,0]>=W) or np.any(p[:,1]>=H):
        raise ValueError('点须位于图内，尺寸>0、近边距离>=0')
    if not cv2.isContourConvex(p.astype(np.int32)) or abs(cv2.contourArea(p))<1000:
        raise ValueError('四点需按边界顺序形成足够大的凸四边形')
    # Image: near-left, near-right, far-right, far-left. Mirror must be corrected first.
    if p[0,0]>=p[1,0] or p[3,0]>=p[2,0] or np.mean(p[:2,1])<=np.mean(p[2:,1]):
        raise ValueError('顺序应为近左、近右、远右、远左；检查相机朝向与画面旋转')
    world=np.float32([[-width/2,near],[width/2,near],[width/2,near+depth],[-width/2,near+depth]])
    matrix=cv2.getPerspectiveTransform(p,world)
    if not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix)<3:
        raise ValueError('标定退化，请重新选择四角')
    return {'matrix':matrix,'polygon':p,'world':world}

def ground_point(cal,u,v):
    if cv2.pointPolygonTest(cal['polygon'],(float(u),float(v)),False)<0:
        return None
    q=np.array([u,v,1.],dtype=float);r=cal['matrix']@q
    if abs(r[2])<1e-9:return None
    x,y=(r[:2]/r[2]).tolist()
    if not all(map(math.isfinite,(x,y))) or y<0:return None
    return {'x_right_mm':round(x,1),'y_forward_mm':round(y,1),
            'ground_range_mm':round(math.hypot(x,y),1),
            'bearing_right_deg':round(math.degrees(math.atan2(x,y)),1)}

def detect(frame,background,cal,threshold=28,min_area=35):
    display=frame.copy();roi=np.zeros((H,W),np.uint8)
    if cal:cv2.fillConvexPoly(roi,cal['polygon'].astype(np.int32),255)
    else:roi[int(.25*H):int(.95*H),int(.05*W):int(.95*W)]=255
    if background is None:return display,{'status':'请先拍空桌面参考','targets':[]}
    a=cv2.GaussianBlur(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),(5,5),0)
    b=cv2.GaussianBlur(cv2.cvtColor(background,cv2.COLOR_BGR2GRAY),(5,5),0)
    _,mask=cv2.threshold(cv2.absdiff(a,b),threshold,255,cv2.THRESH_BINARY)
    mask=cv2.bitwise_and(mask,roi)
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    fraction=cv2.countNonZero(mask)/max(cv2.countNonZero(roi),1)
    if fraction>.25:return display,{'status':'画面变化过大：检查相机、光照并重拍空桌面','targets':[]}
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    targets=[]
    for contour in contours:
        area=cv2.contourArea(contour)
        if area<min_area:continue
        m=cv2.moments(contour)
        if m['m00']==0:continue
        u,v=m['m10']/m['m00'],m['m01']/m['m00']
        # centroid is only a tabletop approximation for small, flat debris.
        point=ground_point(cal,u,v) if cal else None
        if cal and point is None:continue
        x,y,w,h=cv2.boundingRect(contour)
        cv2.rectangle(display,(x,y),(x+w,y+h),(0,210,0),2)
        cv2.circle(display,(round(u),round(v)),4,(0,0,255),-1)
        offset=(u-W/2)/(W/2)
        metric=point['x_right_mm'] if point else offset
        deadband=10 if point else .06
        direction='右' if metric>deadband else '左' if metric<-deadband else '中间'
        targets.append({'u':round(u,1),'v':round(v,1),'area_px':round(area,1),
                        'direction':direction,'image_offset':round(offset,3),'measurement':point})
    if cal:cv2.polylines(display,[cal['polygon'].astype(np.int32)],True,(255,180,0),1)
    cv2.line(display,(W//2,0),(W//2,H),(0,210,255),1)
    targets.sort(key=lambda a:a['area_px'],reverse=True)
    for i,t in enumerate(targets):cv2.putText(display,str(i+1),(round(t['u'])+6,round(t['v'])),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,255),1)
    return display,{'status':'候选变化区域，需人工确认是碎屑' if targets else '未发现明显变化区域',
                    'changed_fraction':round(fraction,3),'targets':targets[:12]}

class Demo:
    def __init__(self,args):
        self.camera=None;self.image=None;self.background=None;self.cal=None;self.args=args
        if args.image:
            self.image=cv2.imread(args.image)
            if self.image is None:raise ValueError('无法读取测试图')
            self.image=cv2.resize(self.image,(W,H))
        else:
            from picamera2 import Picamera2
            self.camera=Picamera2()
            self.camera.configure(self.camera.create_video_configuration(main={'size':(W,H),'format':'RGB888'}))
            self.camera.start();time.sleep(2)
    def frame(self):
        f=self.image.copy() if self.image is not None else self.camera.capture_array('main')
        if f.shape[:2]!=(H,W):raise ValueError('图像尺寸改变，需要重新标定')
        return f
    def reference(self):
        if self.camera:
            meta=self.camera.capture_metadata()
            # Fix exposure and colour gains for this controlled lighting test.
            controls={'AeEnable':False,'AwbEnable':False}
            for name in ('ExposureTime','AnalogueGain','ColourGains'):
                if name in meta:controls[name]=meta[name]
            self.camera.set_controls(controls);time.sleep(.3)
        frames=[self.frame() for _ in range(5)]
        self.background=np.median(frames,axis=0).astype(np.uint8)
        return {'ok':True,'message':'参考已更新；相机、车身和光照保持不变'}
    def state(self):
        frame=self.frame()
        view,result=detect(frame,self.background,self.cal,self.args.threshold,self.args.min_area)
        ok,jpg=cv2.imencode('.jpg',view,[cv2.IMWRITE_JPEG_QUALITY,75])
        if not ok:raise ValueError('图像编码失败')
        result.update({'jpeg':base64.b64encode(jpg).decode(),'calibrated':self.cal is not None,
                       'server_time':time.time()})
        return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,data,code=200,kind='application/json; charset=utf-8'):
        raw=data.encode() if isinstance(data,str) else json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        try:
            if self.path=='/':self.reply(Path(__file__).with_name('index.html').read_text(),kind='text/html; charset=utf-8')
            elif self.path=='/state':self.reply(self.server.demo.state())
            else:self.reply({'error':'not found'},404)
        except Exception as e:self.reply({'error':str(e)},500)
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=10000:raise ValueError('请求过大')
            payload=json.loads(self.rfile.read(length) or '{}');demo=self.server.demo
            if self.path=='/reference':result=demo.reference()
            elif self.path=='/calibrate':
                demo.cal=make_calibration(payload['points'],float(payload['width_mm']),float(payload['depth_mm']),float(payload['near_mm']))
                result={'ok':True,'message':'标定已应用；请用独立点验证距离'}
            elif self.path=='/clear':demo.cal=None;result={'ok':True}
            elif self.path=='/check':
                if demo.cal is None:raise ValueError('请先标定')
                q=ground_point(demo.cal,float(payload['u']),float(payload['v']))
                if q is None:raise ValueError('检查点在标定范围外')
                x,y=float(payload['x_mm']),float(payload['y_mm'])
                if not np.isfinite([x,y]).all():raise ValueError('坐标无效')
                q['error_mm']=round(math.hypot(q['x_right_mm']-x,q['y_forward_mm']-y),1);result=q
            else:self.reply({'error':'not found'},404);return
            self.reply(result)
        except (ValueError,KeyError,TypeError) as e:self.reply({'error':str(e)},400)
        except Exception as e:self.reply({'error':str(e)},500)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8000);p.add_argument('--threshold',type=int,default=28)
    p.add_argument('--min-area',type=int,default=35);p.add_argument('--image',help='offline image, no camera needed')
    args=p.parse_args()
    if not 1<=args.port<=65535 or not 1<=args.threshold<=255 or args.min_area<=0:p.error('invalid parameters')
    demo=Demo(args);server=HTTPServer(('127.0.0.1',args.port),Handler);server.demo=demo
    print(f'Open http://127.0.0.1:{args.port} (Mac: use SSH port forwarding). Ctrl+C to stop.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        server.server_close()
        if demo.camera:demo.camera.stop();demo.camera.close()
if __name__=='__main__':main()
