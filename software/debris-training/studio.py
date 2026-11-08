"""Local collection and box-labeling studio. No motor control, no cloud uploads."""
import argparse
import fcntl
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from threading import RLock
from urllib.parse import parse_qs, urlsplit
from urllib.request import build_opener, ProxyHandler

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
SPLITS = ('train', 'val', 'test')
MAX_UPLOAD = 12 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        (self.root / 'images').mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'manifest.json'
        self.lock = RLock()
        if not self.path.exists():
            write_json(self.path, dict(version=1, records=[]))

    def read(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def add(self, raw, session, split, source='camera'):
        if not isinstance(session, str) or not 1 <= len(session.strip()) <= 80:
            raise ValueError('Enter a scene name such as deskA_day; one scene always belongs to one split')
        session = session.strip()
        if split not in SPLITS:
            raise ValueError('Split must be train / val / test')
        if not raw or len(raw) > MAX_UPLOAD:
            raise ValueError('Image is empty or larger than 12 MB')
        with Image.open(BytesIO(raw)) as original:
            if original.width * original.height > 16_000_000:
                raise ValueError('Image exceeds 16 megapixels; shrink it first')
            if original.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValueError('Only JPG, PNG and WEBP images are supported')
            image = ImageOps.exif_transpose(original).convert('RGB')
            if min(image.size) < 32:
                raise ValueError('Image too small; at least 32×32 pixels')
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=95)
            content = buffer.getvalue()
            width, height = image.size
        digest = sha256(content).hexdigest()
        with self.lock:
            data = self.read()
            records = data['records']
            if any(r['session'] == session and r['split'] != split for r in records):
                raise ValueError('A scene cannot span train/val/test; use a really different place before creating a new name')
            if any(r['sha256'] == digest for r in records):
                raise ValueError('This image already exists; not added again')
            number = max((int(r['id']) for r in records), default=0) + 1
            while (self.root / 'images' / f'{number:06}.jpg').exists():
                number += 1
            identifier = f'{number:06}'
            filename = f'images/{identifier}.jpg'
            record = dict(id=identifier, file=filename, width=width, height=height,
                          batch=len(records) // 50 + 1, session=session, split=split,
                          source=str(source)[:200], sha256=digest, created=now(),
                          reviewed=False, boxes=[], revision=0)
            (self.root / filename).write_bytes(content)
            records.append(record)
            write_json(self.path, data)
            return record

    def save(self, identifier, boxes, negative, revision):
        if not isinstance(boxes, list) or len(boxes) > 1000:
            raise ValueError('Bad box format')
        if not boxes and negative is not True:
            raise ValueError('No boxes: draw a box, or click "Confirm no debris" explicitly')
        if boxes and negative:
            raise ValueError('A photo with boxes cannot be marked as no debris')
        with self.lock:
            data = self.read()
            record = next((r for r in data['records'] if r['id'] == identifier), None)
            if record is None:
                raise ValueError('Image not found')
            if type(revision) is not int or revision != record['revision']:
                raise ValueError('Image was changed in another window; refresh and label again')
            for box in boxes:
                if not isinstance(box, list) or len(box) != 4 or any(
                    type(v) not in (int, float) or not math.isfinite(v) for v in box
                ):
                    raise ValueError('Each box must be four finite numbers x1,y1,x2,y2')
                x1, y1, x2, y2 = box
                if not (0 <= x1 < x2 <= record['width'] and 0 <= y1 < y2 <= record['height']
                        and x2 - x1 >= 2 and y2 - y1 >= 2):
                    raise ValueError('Boxes must be inside the image and at least 2 pixels wide and high')
            record.update(boxes=boxes, reviewed=True, revision=revision + 1, updated=now())
            write_json(self.path, data)
            return record

    def summary(self):
        with self.lock:
            records = self.read()['records']
        counts = {s: dict(total=0, reviewed=0, positive=0, negative=0) for s in SPLITS}
        for r in records:
            c = counts[r['split']]
            c['total'] += 1
            if r['reviewed']:
                c['reviewed'] += 1
                c['positive' if r['boxes'] else 'negative'] += 1
        return dict(records=records, counts=counts, total=len(records),
                    reviewed=sum(r['reviewed'] for r in records),
                    next_batch=len(records) // 50 + 1, in_batch=len(records) % 50)


class Jobs:
    def __init__(self, root):
        self.root = root
        self.lock = RLock()
        self.process = None
        self.log = None
        self.kind = None

    def start(self, kind, epochs, device, fresh=False):
        if kind not in ('train', 'evaluate', 'export'):
            raise ValueError('Unknown task')
        if type(epochs) is not int or not 1 <= epochs <= 300:
            raise ValueError('Epochs must be 1-300')
        if device not in ('auto', 'cpu', 'mps', '0'):
            raise ValueError('Device must be auto / cpu / mps / 0')
        if type(fresh) is not bool:
            raise ValueError('fresh must be true or false')
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise ValueError('A task is already running; wait for it to finish')
            folder = self.root / 'logs'
            folder.mkdir(exist_ok=True)
            self.log = folder / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.log')
            command = [sys.executable, '-u', str(HERE / 'workflow.py'), kind,
                       '--root', str(self.root), '--device', device]
            if kind == 'train':
                command += ['--epochs', str(epochs)] + (['--fresh'] if fresh else [])
            with self.log.open('wb') as output:
                self.process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
            self.kind = kind
            return self.state()

    def state(self):
        with self.lock:
            code = self.process.poll() if self.process is not None else None
            tail = ''
            if self.log:
                with self.log.open('rb') as source:
                    source.seek(max(0, self.log.stat().st_size - 16000))
                    tail = source.read().decode('utf-8', errors='replace')
            return dict(started=self.process is not None,
                        running=self.process is not None and code is None,
                        exit_code=code, kind=self.kind, log=tail)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_):
        pass

    def reply(self, data, status=200, kind='application/json; charset=utf-8'):
        raw = data if isinstance(data, bytes) else (
            data.encode() if isinstance(data, str) else json.dumps(data, ensure_ascii=False).encode())
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def local_request(self):
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        host = self.headers.get('Host', '')
        if host not in allowed:
            raise ValueError('Open this studio via localhost or 127.0.0.1')
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + host:
            raise ValueError('Changes from other web pages are not accepted')

    def import_collection(self, size):
        import tempfile
        from workflow import import_collection   # workflow imports studio; import lazily
        if self.headers.get('Content-Type') != 'application/zip':
            raise ValueError('Choose the ZIP exported by the data collector')
        if not 0 < size <= 2 * 1024**3:
            raise ValueError('Collection ZIP is empty or larger than 2 GB')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'collection.zip'
            with path.open('wb') as out:
                left = size
                while left:
                    chunk = self.rfile.read(min(left, 1 << 20))
                    if not chunk:
                        raise ValueError('Upload interrupted')
                    out.write(chunk)
                    left -= len(chunk)
            return import_collection(self.server.store.root, path)

    def send_export(self, kind):
        import tempfile
        from workflow import export_dataset   # workflow imports studio; import lazily
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with tempfile.TemporaryDirectory() as temp:
            out, _ = export_dataset(self.server.store.root, Path(temp) / f'metalsweep_{kind}_{stamp}.zip', kind)
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Length', str(out.stat().st_size))
            self.send_header('Content-Disposition', f'attachment; filename="{out.name}"')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            with out.open('rb') as source:
                while chunk := source.read(1 << 20):
                    self.wfile.write(chunk)

    def camera(self):
        if not self.server.camera_url:
            raise ValueError('No Pi camera configured; import photos, or restart with --camera-url')
        opener = build_opener(ProxyHandler({}))
        with opener.open(self.server.camera_url, timeout=8) as response:
            raw = response.read(MAX_UPLOAD + 1)
        if len(raw) > MAX_UPLOAD:
            raise ValueError('Camera image too large')
        return raw

    def do_GET(self):
        try:
            self.local_request()
            path = urlsplit(self.path).path
            if path == '/':
                self.reply((HERE / 'index.html').read_bytes(), kind='text/html; charset=utf-8')
            elif path == '/api/state':
                self.reply(self.server.store.summary())
            elif path == '/api/job':
                self.reply(self.server.jobs.state())
            elif path == '/camera.jpg':
                self.reply(self.camera(), kind='image/jpeg')
            elif path in ('/api/export/yolo.zip', '/api/export/backup.zip'):
                self.send_export(path.rsplit('/', 1)[1][:-4])
            elif re.fullmatch(r'/image/\d{6,}\.jpg', path):
                image = self.server.store.root / 'images' / path.rsplit('/', 1)[1]
                self.reply(image.read_bytes(), kind='image/jpeg')
            else:
                self.reply({'error': 'not found'}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            self.reply({'error': str(error)}, 400)

    def do_POST(self):
        try:
            self.local_request()
            parsed = urlsplit(self.path)
            size = int(self.headers.get('Content-Length', '0'))
            if parsed.path == '/api/import-collection':
                self.reply(self.import_collection(size))
                return
            if not 0 < size <= MAX_UPLOAD:
                raise ValueError('Request is empty or larger than 12 MB')
            body = self.rfile.read(size)
            if parsed.path == '/api/import':
                if self.headers.get('Content-Type') != 'application/octet-stream':
                    raise ValueError('Bad import format')
                query = parse_qs(parsed.query)
                result = self.server.store.add(body, query.get('session', [''])[0],
                                               query.get('split', [''])[0],
                                               query.get('name', ['import'])[0])
            else:
                if self.headers.get('Content-Type') != 'application/json':
                    raise ValueError('JSON request required')
                data = json.loads(body)
                if not isinstance(data, dict):
                    raise ValueError('JSON object required')
                if parsed.path == '/api/capture':
                    result = self.server.store.add(self.camera(), data.get('session'), data.get('split'))
                elif parsed.path == '/api/label':
                    result = self.server.store.save(data.get('id'), data.get('boxes'),
                                                    data.get('negative'), data.get('revision'))
                elif parsed.path == '/api/job':
                    result = self.server.jobs.start(data.get('kind'), data.get('epochs', 30),
                                                    data.get('device', 'auto'), data.get('fresh', False))
                else:
                    self.reply({'error': 'not found'}, 404)
                    return
            self.reply(result)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            self.reply({'error': str(error)}, 400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(HERE / 'workspace'))
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--camera-url', default='', help='Pi detector /raw.jpg URL')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1-65535')
    if args.camera_url and (urlsplit(args.camera_url).scheme not in ('http', 'https')
                            or not urlsplit(args.camera_url).hostname):
        parser.error('camera-url must be an http/https image URL')
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    workspace_lock = (root / '.studio.lock').open('a')
    try:
        fcntl.flock(workspace_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.exit(1, 'A studio is already running for this workspace; go back to its page. Do not run two editors at once.\n')
    store = Store(root)
    with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
        server.store, server.jobs, server.camera_url = store, Jobs(store.root), args.camera_url
        print(f'Open http://127.0.0.1:{args.port} in the Mac browser\nPhotos and labels are stored in {store.root}', flush=True)
        print('Batches of 50 are made automatically; training runs in the background. Ctrl+C stops the web server without deleting data.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nWeb server stopped; any running training task continues, logs are in workspace/logs.')


if __name__ == '__main__':
    main()
