"""METALSWEEP data collector: capture-only web page that runs on the Pi.

Photos are sorted by split (train/val/test) and scene, then exported as one ZIP
that the Mac training studio imports. No labelling, no training, no motors here.

Camera source (pick one):
  default        take frames from the running car backend: http://127.0.0.1:8091/raw.jpg
  --picamera     own the CSI camera directly (stop run.py first; only one process may own it)

Python standard library only (Picamera2 is needed only with --picamera).
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
from threading import RLock
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener
import zipfile

HERE = Path(__file__).resolve().parent
SPLITS = ('train', 'val', 'test')
MAX_IMAGE = 12 * 1024 * 1024
SCENE = re.compile(r'[A-Za-z0-9_-]{1,60}')


def now():
    return datetime.now(timezone.utc).isoformat()


class Collection:
    """images/<split>/<scene>/<n>.jpg + manifest.json; a scene belongs to exactly one split."""

    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'manifest.json'
        self.lock = RLock()
        if not self.path.exists():
            self._write(dict(version=1, kind='metalsweep-collection', records=[]))

    def _write(self, data):
        partial = self.path.with_suffix('.partial')
        partial.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(partial, self.path)

    def read(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def add(self, raw, scene, split, empty=False):
        if not isinstance(scene, str) or not SCENE.fullmatch(scene.strip()):
            raise ValueError('Scene name: 1-60 letters, digits, _ or - (e.g. deskA_day)')
        scene = scene.strip()
        if split not in SPLITS:
            raise ValueError('Split must be train, val or test')
        if not raw or len(raw) > MAX_IMAGE or raw[:3] != b'\xff\xd8\xff':
            raise ValueError('Camera did not return a JPEG image')
        digest = sha256(raw).hexdigest()
        with self.lock:
            data = self.read()
            records = data['records']
            other = next((r['split'] for r in records if r['scene'] == scene and r['split'] != split), None)
            if other:
                raise ValueError(f'Scene "{scene}" is already used for {other}. One scene = one split; '
                                 'use a really different place/table/light and a new name.')
            if any(r['sha256'] == digest for r in records):
                raise ValueError('Identical frame already saved (camera frame did not change)')
            folder = self.root / 'images' / split / scene
            folder.mkdir(parents=True, exist_ok=True)
            number = len(list(folder.glob('*.jpg'))) + 1
            while (folder / f'{number:04}.jpg').exists():
                number += 1
            file = f'images/{split}/{scene}/{number:04}.jpg'
            (self.root / file).write_bytes(raw)
            record = dict(file=file, scene=scene, split=split, empty=bool(empty),
                          sha256=digest, captured=now())
            records.append(record)
            self._write(data)
            return record

    def undo(self):
        with self.lock:
            data = self.read()
            if not data['records']:
                raise ValueError('Nothing to undo')
            record = data['records'].pop()
            (self.root / record['file']).unlink(missing_ok=True)
            self._write(data)
            return record

    def summary(self):
        with self.lock:
            records = self.read()['records']
        scenes = {}
        for r in records:
            s = scenes.setdefault(r['scene'], dict(split=r['split'], total=0, empty=0))
            s['total'] += 1
            s['empty'] += r['empty']
        splits = {k: dict(total=0, empty=0, scenes=0) for k in SPLITS}
        for s in scenes.values():
            splits[s['split']]['total'] += s['total']
            splits[s['split']]['empty'] += s['empty']
            splits[s['split']]['scenes'] += 1
        last = records[-1] if records else None
        return dict(total=len(records), splits=splits, scenes=scenes, last=last, root=str(self.root))

    def export(self, out):
        """ZIP with manifest.json + images/, imported by the training studio as-is."""
        out = Path(out)
        with self.lock:
            data = self.read()
            if not data['records']:
                raise ValueError('No photos yet')
            data['exported'] = now()
            with zipfile.ZipFile(out, 'w') as archive:
                for r in data['records']:
                    content = (self.root / r['file']).read_bytes()
                    if sha256(content).hexdigest() != r['sha256']:
                        raise ValueError('Photo changed on disk: ' + r['file'])
                    archive.writestr(r['file'], content, compress_type=zipfile.ZIP_STORED)
                archive.writestr('manifest.json', json.dumps(data, ensure_ascii=False, indent=2),
                                 compress_type=zipfile.ZIP_DEFLATED)
        return out


class UrlCamera:
    def __init__(self, url):
        self.url, self.opener = url, build_opener(ProxyHandler({}))

    def jpeg(self):
        try:
            with self.opener.open(self.url, timeout=5) as response:
                raw = response.read(MAX_IMAGE + 1)
        except OSError as error:
            raise ValueError(f'No camera image from {self.url}. Is the car backend (run.py) running? ({error})')
        if len(raw) > MAX_IMAGE:
            raise ValueError('Camera image too large')
        return raw

    def close(self):
        pass


class PiCamera:
    def __init__(self, rotate180):
        from picamera2 import Picamera2
        from libcamera import Transform
        self.lock = RLock()
        self.camera = Picamera2()
        config = self.camera.create_still_configuration(main={'size': (640, 480)},
                                                        transform=Transform(hflip=rotate180, vflip=rotate180))
        self.camera.configure(config)
        self.camera.start()

    def jpeg(self):
        with self.lock:
            buffer = BytesIO()
            self.camera.capture_file(buffer, format='jpeg')
            return buffer.getvalue()

    def close(self):
        self.camera.stop()
        self.camera.close()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_):
        pass

    def reply(self, data, status=200, kind='application/json; charset=utf-8', headers=()):
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def check_local(self, post=False):
        host = f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host') not in (host, f'localhost:{self.server.server_port}'):
            raise PermissionError('Open this page at http://127.0.0.1:%d/' % self.server.server_port)
        if post and (self.headers.get('Origin') not in ('http://' + self.headers.get('Host'),)
                     or self.headers.get('Content-Type') != 'application/json'):
            raise PermissionError('Requests must come from this page')

    def do_GET(self):
        try:
            self.check_local()
            path = urlsplit(self.path).path
            if path == '/':
                self.reply((HERE / 'index.html').read_bytes(), kind='text/html; charset=utf-8')
            elif path == '/state':
                self.reply(self.server.collection.summary())
            elif path == '/preview.jpg':
                self.reply(self.server.camera.jpeg(), kind='image/jpeg')
            elif path == '/last.jpg':
                last = self.server.collection.summary()['last']
                if not last:
                    raise ValueError('No photo yet')
                self.reply((self.server.collection.root / last['file']).read_bytes(), kind='image/jpeg')
            elif path == '/export.zip':
                stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                with tempfile.TemporaryDirectory() as temp:
                    out = self.server.collection.export(Path(temp) / f'metalsweep_collection_{stamp}.zip')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/zip')
                    self.send_header('Content-Length', str(out.stat().st_size))
                    self.send_header('Content-Disposition', f'attachment; filename="{out.name}"')
                    self.end_headers()
                    with out.open('rb') as source:
                        while chunk := source.read(1 << 20):
                            self.wfile.write(chunk)
            else:
                self.reply({'error': 'not found'}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except PermissionError as error:
            self.reply({'error': str(error)}, 403)
        except Exception as error:
            self.reply({'error': str(error)}, 400)

    def do_POST(self):
        try:
            self.check_local(post=True)
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError('Bad request')
            body = json.loads(self.rfile.read(size))
            path = urlsplit(self.path).path
            c = self.server.collection
            if path == '/capture':
                record = c.add(self.server.camera.jpeg(), body.get('scene'), body.get('split'), body.get('empty') is True)
            elif path == '/undo':
                record = c.undo()
            else:
                self.reply({'error': 'not found'}, 404)
                return
            self.reply(dict(record=record, state=c.summary()))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except PermissionError as error:
            self.reply({'error': str(error)}, 403)
        except Exception as error:
            self.reply({'error': str(error)}, 400)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root', default='~/metalsweep-dataset', help='where photos are stored (default ~/metalsweep-dataset)')
    p.add_argument('--port', type=int, default=8092)
    p.add_argument('--camera-url', default='http://127.0.0.1:8091/raw.jpg')
    p.add_argument('--picamera', action='store_true', help='use the CSI camera directly (run.py must be stopped)')
    p.add_argument('--rotate180', action='store_true', help='with --picamera: rotate image 180 degrees')
    args = p.parse_args()
    if not 1024 <= args.port <= 65535:
        p.error('port must be 1024..65535')
    camera = PiCamera(args.rotate180) if args.picamera else UrlCamera(args.camera_url)
    collection = Collection(args.root)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.daemon_threads = True
    server.collection, server.camera = collection, camera
    print(f'Data collector: http://127.0.0.1:{args.port}/   photos -> {collection.root}', flush=True)
    print('Camera: ' + ('CSI camera (direct)' if args.picamera else args.camera_url), flush=True)
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        camera.close()


if __name__ == '__main__':
    main()
