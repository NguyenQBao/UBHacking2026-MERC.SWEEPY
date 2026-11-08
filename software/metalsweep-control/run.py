"""Pi4 camera + bounded drive/brush controller; default simulation and local browser."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cv2
from control import Buzzer, Controller, Motors, validate
from vision import Ground, Vision

HERE = Path(__file__).resolve().parent


class App:
    def __init__(self, cfg, motors, vision, simulated, config_path=None, buzzer=None):
        self.config_path = config_path
        self.buzzer = buzzer or Buzzer(cfg)
        self.controller = Controller(cfg, motors)
        self.cfg, self.vision = cfg, vision
        self.lock = threading.Lock()
        self.jpeg = b''
        self.state = {'status': 'STARTING', 'simulated': simulated}
        self.state['brush_enabled'] = motors.brush_enabled
        self.state['brush_mode'] = cfg['brush_mode']
        self.quit = threading.Event()
        self.token = secrets.token_urlsafe(24)
        self.session_seen = time.monotonic()
        self.frame_id = 0

    def save_config(self):
        """Write current runtime settings back to the config file (atomic replace)."""
        if not self.config_path:
            raise ValueError('No config file to save')
        path = Path(self.config_path)
        data = json.loads(path.read_text())
        data.update(self.controller.settings())
        validate(data)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
        os.replace(tmp, path)

    def run_camera(self, image=None):
        camera = None
        try:
            if image:
                still = cv2.imread(image)
                if still is None:
                    raise ValueError('Cannot read test image')
                still = cv2.resize(still, (640, 480))
            else:
                from picamera2 import Picamera2
                camera = Picamera2()
                camera.configure(camera.create_video_configuration(
                    main={'size': (640, 480), 'format': 'RGB888'},
                    controls={'FrameRate': 10}, queue=False))
                camera.start()
                time.sleep(2)
            while not self.quit.is_set():
                # Flush an older completed exposure after every pulse/settling interval.
                if time.monotonic() < self.controller.ready_at:
                    self.quit.wait(.02)
                    continue
                if camera:
                    camera.capture_array('main')
                    frame = camera.capture_array('main')
                else:
                    frame = still.copy()
                captured_at = time.monotonic()
                if self.cfg['rotate180']:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                targets = self.vision.detect(frame)
                try:
                    self.buzzer.update(bool(targets))
                except Exception as e:  # a buzzer fault must never stop the camera/motors loop
                    print(f'Buzzer error: {e}', flush=True)
                self.frame_id += 1
                action = self.controller.tick(targets, captured_at, self.frame_id)
                if action:
                    print(json.dumps({'action': action.__dict__}, ensure_ascii=False), flush=True)
                view = frame.copy()
                for t in targets:
                    x1, y1, x2, y2 = map(int, t.box)
                    cv2.rectangle(view, (x1, y1), (x2, y2), (40, 210, 40), 2)
                    label = f'{t.confidence:.2f}' if self.vision.model else 'HSV test'
                    offset = t.center[0]-320
                    direction = 'LEFT' if offset < -20 else 'RIGHT' if offset > 20 else 'CENTER'
                    label += ' '+direction
                    if t.ground:
                        label += f' X={t.ground[0]:.0f} Y={t.ground[1]:.0f}mm'
                    cv2.putText(view, label, (x1, max(18, y1-5)), cv2.FONT_HERSHEY_SIMPLEX, .45, (30, 210, 40), 1)
                if self.vision.ground:
                    cv2.polylines(view, [self.vision.ground.hull.astype('int32')], True, (255, 140, 0), 1)
                cv2.line(view, (320, 0), (320, 479), (0, 210, 255), 1)
                ok, jpeg = cv2.imencode('.jpg', view, [cv2.IMWRITE_JPEG_QUALITY, 75])
                raw_ok, raw = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                if not ok or not raw_ok:
                    raise RuntimeError('JPEG encoding failed')
                with self.lock:
                    self.jpeg, self.raw = jpeg.tobytes(), raw.tobytes()
                    self.state.update(frame_id=self.frame_id, status=self.controller.status,
                                      auto=self.controller.auto, beeps=self.buzzer.beeps, motors=list(self.controller.motors.values),
                                      processing_ms=round((time.monotonic()-captured_at)*1000),
                                      targets=[{'box': t.box, 'score': t.confidence, 'xy_mm': t.ground,
                                                'image_direction': ('LEFT' if t.center[0] < 300 else 'RIGHT' if t.center[0] > 340 else 'CENTER')}
                                               for t in targets],
                                      detector='learned debris' if self.vision.model else 'HSV TEST ONLY')
                self.quit.wait(.08)
        except Exception as e:
            self.controller.stop('CAMERA_OR_INFERENCE_ERROR')
            with self.lock:
                self.state.update(error=str(e), status=self.controller.status)
            print(f'Camera stopped: {e}', flush=True)
        finally:
            self.controller.stop('CAMERA_STOPPED')
            if camera:
                camera.stop()
                camera.close()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *args):
        pass

    def reply(self, data, kind='application/json', status=200):
        raw = data if isinstance(data, bytes) else json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        app = self.server.app
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
            self.reply({'error': 'Use 127.0.0.1 URL'}, status=403)
            return
        if self.path == '/':
            html = (HERE/'index.html').read_text().replace('__TOKEN__', app.token)
            self.reply(html.encode(), 'text/html; charset=utf-8')
        elif self.path in ('/frame.jpg', '/raw.jpg', '/state'):
            with app.lock:
                if self.path == '/state':
                    state = dict(app.state, status=app.controller.status,
                                 motors=list(app.controller.motors.values), auto=app.controller.auto,
                                 motor_phase=app.controller.motors.label,
                                 settings=app.controller.settings())
                    self.reply(state)
                else:
                    raw = app.jpeg if self.path == '/frame.jpg' else getattr(app, 'raw', b'')
                    self.reply(raw, 'image/jpeg', 200 if raw else 503)
        else:
            self.reply({'error': 'Not found'}, status=404)

    def do_POST(self):
        app = self.server.app
        origin = f'http://127.0.0.1:{self.server.server_port}'
        try:
            if (self.path != '/command' or self.headers.get('Host') != origin[7:]
                    or self.headers.get('Origin') != origin
                    or self.headers.get('X-Control-Token') != app.token):
                self.reply({'error': 'Local control session required'}, status=403)
                return
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1024:
                raise ValueError('Invalid body')
            body = json.loads(self.rfile.read(length))
            command = body['command']
            c = app.controller
            if command == 'stop':
                c.stop('OPERATOR_STOP')
            elif command == 'set':
                c.set_setting(body['key'], body['value'])
            elif command == 'brush_test':
                c.brush_test(body['seconds'])
            elif command == 'save':
                app.save_config()
            elif command == 'heartbeat':
                c.heartbeat()
            elif command == 'auto':
                with app.lock:
                    if app.state.get('error') or not app.state.get('frame_id'):
                        raise ValueError('Camera is not ready')
                c.start(app.vision.ground is not None)
            else:
                c.manual(command)
            self.reply({'ok': True, 'status': c.status})
        except (ValueError, KeyError, TypeError) as e:
            self.reply({'error': str(e)}, status=400)
        except Exception as e:
            app.controller.stop('CONTROL_ERROR')
            self.reply({'error': str(e)}, status=500)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default=str(HERE/'config.json'))
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--model', help='Own debris best.pt or *_ncnn_model directory')
    group.add_argument('--hsv', help='H,S,V for a coloured test object, e.g. 0,220,220')
    p.add_argument('--ground', help='Measured ground.json, required for automatic cycle')
    p.add_argument('--image', help='Offline image; simulation only')
    p.add_argument('--hardware', action='store_true', help='Actually open GPIO; otherwise no GPIO imports')
    p.add_argument('--wheels-only', action='store_true', help='Never open brush GPIO; refuse brush/automatic commands')
    p.add_argument('--port', type=int, default=8091)
    args = p.parse_args()
    if not 1024 <= args.port <= 65535 or (args.hardware and args.image):
        p.error('Invalid port or --hardware with offline image')
    motors = server = app = buzzer = None
    old_handlers = {}
    try:
        cfg = validate(json.loads(Path(args.config).read_text()))
        hsv = None
        if args.hsv:
            hsv = [int(x) for x in args.hsv.split(',')]
            if len(hsv) != 3 or not 0 <= hsv[0] <= 179 or any(not 0 <= x <= 255 for x in hsv[1:]):
                raise ValueError('HSV must be H0..179,S0..255,V0..255')
        ground = Ground(args.ground, cfg['rotate180'], cfg['ground_margin_px']) if args.ground else None
        os.environ.setdefault('YOLO_CONFIG_DIR', str(HERE/'runtime'/'ultralytics'))
        vision = Vision(cfg, args.model, hsv, ground)
        motors = Motors(cfg, hardware=args.hardware, brush_enabled=not args.wheels_only)
        buzzer = Buzzer(cfg, hardware=args.hardware)
        app = App(cfg, motors, vision, not args.hardware, args.config, buzzer)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
        server.daemon_threads = True
        server.app = app
        def stop_signal(signum, frame):
            app.controller.stop('SIGNAL_STOP')
            raise KeyboardInterrupt
        for sig in (signal.SIGINT, signal.SIGTERM):
            old_handlers[sig] = signal.signal(sig, stop_signal)
        threading.Thread(target=app.run_camera, args=(args.image,), daemon=True).start()
        print(f'{"HARDWARE" if args.hardware else "SIMULATION (no GPIO)"}: http://127.0.0.1:{args.port}/', flush=True)
        print('Stop old app.py first: only one process may own the CSI camera. Ctrl+C stops all outputs.', flush=True)
        server.serve_forever(poll_interval=.1)
    except KeyboardInterrupt:
        pass
    finally:
        if app:
            app.quit.set()
            app.controller.stop()
        if server:
            server.server_close()
        if motors:
            motors.close()
        if buzzer:
            buzzer.close()
        for sig, old in old_handlers.items():
            signal.signal(sig, old)


if __name__ == '__main__':
    main()
