import http.client
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import cv2
import numpy as np
from http.server import ThreadingHTTPServer
from control import Motors
from run import App, Handler
from vision import Vision, fit_ground


class HTTPTests(unittest.TestCase):
    def test_offline_camera_browser_single_cycle(self):
        here = Path(__file__).resolve().parent
        cfg = json.loads((here/'config.json').read_text())
        cfg.update(directions_verified=True, ground_calibration_verified=True, speed_calibration_verified=True, supervised_clear_floor=True)
        points = [{'uv': [u, v], 'xy_mm': [(u-320)/2, (480-v)/2]}
                  for u, v in [(100, 100), (500, 100), (100, 400), (500, 400), (200, 250), (400, 250)]]
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            frame = np.zeros((480, 640, 3), np.uint8)
            frame[350:370, 310:330] = [10, 10, 240]
            cv2.imwrite(str(d/'test.png'), frame)
            (d/'config.json').write_text(json.dumps(cfg))
            (d/'ground.json').write_text(json.dumps(fit_ground(points, (640, 480))))
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            process = subprocess.Popen([sys.executable, str(here/'run.py'), '--image', str(d/'test.png'),
                                        '--config', str(d/'config.json'), '--ground', str(d/'ground.json'),
                                        '--hsv', '0,240,240', '--port', str(port)],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            def call(path, command=None, token=''):
                conn = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
                headers = {'Origin': f'http://127.0.0.1:{port}', 'X-Control-Token': token,
                           'Content-Type': 'application/json'}
                conn.request('POST' if command else 'GET', path,
                             json.dumps({'command': command}) if command else None, headers)
                response = conn.getresponse(); raw = response.read(); status = response.status
                conn.close()
                self.assertEqual(status, 200, raw)
                return raw
            try:
                deadline = time.monotonic()+8
                state = {}
                while time.monotonic() < deadline:
                    try:
                        state = json.loads(call('/state'))
                        if state.get('frame_id'): break
                    except (OSError, http.client.HTTPException): pass
                    time.sleep(.05)
                self.assertTrue(state.get('frame_id'), state)
                html = call('/').decode()
                token = html.split("const token='")[1].split("'")[0]
                self.assertEqual(state['targets'][0]['image_direction'], 'CENTER')
                self.assertAlmostEqual(state['targets'][0]['xy_mm'][1], 55, delta=1)
                raw = call('/frame.jpg')
                decoded = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                self.assertEqual(decoded.shape, (480, 640, 3))
                call('/command', 'auto', token)
                statuses = set()
                while time.monotonic() < deadline:
                    call('/command', 'heartbeat', token)
                    state = json.loads(call('/state')); statuses.add(state['motor_phase'])
                    if state['status'] == 'VERIFY_CONTAINER_MANUALLY': break
                    time.sleep(.05)
                self.assertEqual(state['status'], 'VERIFY_CONTAINER_MANUALLY', statuses)
                self.assertTrue({'BRUSH_SPINUP', 'SWEEP', 'BRUSH_TAIL'}.issubset(statuses), statuses)
                self.assertEqual(state['motors'], [0, 0, 0]); self.assertTrue(state['simulated'])
            finally:
                process.send_signal(signal.SIGTERM)
                output, _ = process.communicate(timeout=4)
            self.assertEqual(process.returncode, 0, output)

    def test_session_auth_stop_and_camera_error_gate(self):
        cfg = json.loads(Path(__file__).with_name('config.json').read_text())
        motors = Motors(cfg)
        app = App(cfg, motors, Vision(cfg, hsv=[0, 220, 220]), True)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        server.app = app
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_port
        def request(method, path, data=None, authenticated=True):
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
            headers = {}
            if authenticated:
                headers = {'Origin': f'http://127.0.0.1:{port}', 'X-Control-Token': app.token,
                           'Content-Type': 'application/json'}
            conn.request(method, path, json.dumps(data) if data else None, headers)
            response = conn.getresponse()
            result = response.status, response.read()
            conn.close()
            return result
        try:
            self.assertEqual(request('GET', '/')[0], 200)
            self.assertEqual(request('POST', '/command', {'command': 'forward'}, False)[0], 403)
            self.assertEqual(motors.values, (0, 0, 0))
            self.assertEqual(request('POST', '/command', {'command': 'forward'})[0], 200)
            self.assertGreater(motors.values[0], 0)
            self.assertEqual(request('POST', '/command', {'command': 'stop'})[0], 200)
            self.assertEqual(motors.values, (0, 0, 0))
            self.assertEqual(request('POST', '/command', {'command': 'auto'})[0], 400)
            # Camera failure must not prevent emergency stop handling.
            app.state['error'] = 'camera unavailable'
            self.assertEqual(request('POST', '/command', {'command': 'stop'})[0], 200)
            state = json.loads(request('GET', '/state')[1])
            self.assertTrue(state['simulated']); self.assertEqual(state['motors'], [0, 0, 0])
        finally:
            server.shutdown(); server.server_close(); thread.join(2); motors.close()


if __name__ == '__main__': unittest.main()
