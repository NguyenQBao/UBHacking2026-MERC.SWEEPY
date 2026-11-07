"""Collector checks: storage rules, HTTP boundary, export ZIP. Standard library only."""
from http.server import ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
import zipfile

from collect import Collection, Handler


def jpeg(n):
    return b'\xff\xd8\xff\xe0' + n.to_bytes(4, 'big') * 50 + b'\xff\xd9'


class FakeCamera:
    def __init__(self):
        self.n = 0

    def jpeg(self):
        self.n += 1
        return jpeg(self.n)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.c = Collection(Path(self.temp.name) / 'data')

    def tearDown(self):
        self.temp.cleanup()

    def test_scene_split_rules_duplicates_undo(self):
        r = self.c.add(jpeg(1), 'deskA_day', 'train')
        self.assertEqual(r['file'], 'images/train/deskA_day/0001.jpg')
        self.c.add(jpeg(2), 'deskA_day', 'train', empty=True)
        with self.assertRaises(ValueError):          # same scene in another split
            self.c.add(jpeg(3), 'deskA_day', 'val')
        with self.assertRaises(ValueError):          # identical frame
            self.c.add(jpeg(1), 'deskA_day', 'train')
        for bad in ('', 'has space', '../x', 'a' * 61):
            with self.assertRaises(ValueError):
                self.c.add(jpeg(9), bad, 'train')
        with self.assertRaises(ValueError):
            self.c.add(b'not a jpeg', 'deskB', 'val')
        s = self.c.summary()
        self.assertEqual((s['total'], s['splits']['train']['empty'], s['splits']['train']['scenes']), (2, 1, 1))
        undone = self.c.undo()
        self.assertFalse((self.c.root / undone['file']).exists())
        self.assertEqual(self.c.summary()['total'], 1)

    def test_export_zip_and_tamper_check(self):
        self.c.add(jpeg(1), 'deskA_day', 'train')
        self.c.add(jpeg(2), 'deskB_day', 'val', empty=True)
        out = self.c.export(Path(self.temp.name) / 'c.zip')
        with zipfile.ZipFile(out) as z:
            manifest = json.loads(z.read('manifest.json'))
            self.assertEqual(len(manifest['records']), 2)
            self.assertEqual(z.read('images/val/deskB_day/0001.jpg'), jpeg(2))
        (self.c.root / 'images/train/deskA_day/0001.jpg').write_bytes(jpeg(7))
        with self.assertRaises(ValueError):
            self.c.export(Path(self.temp.name) / 'd.zip')

    def test_http_capture_state_export_and_origin_boundary(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.collection, server.camera = self.c, FakeCamera()
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        opener = build_opener(ProxyHandler({}))
        good = {'Content-Type': 'application/json', 'Origin': base}
        try:
            with opener.open(base + '/') as response:
                self.assertIn('Data Collector', response.read().decode())
            body = json.dumps(dict(scene='deskA_day', split='train', empty=False)).encode()
            with opener.open(Request(base + '/capture', body, good)) as response:
                self.assertEqual(json.load(response)['state']['total'], 1)
            with opener.open(base + '/last.jpg') as response:
                self.assertEqual(response.read()[:3], b'\xff\xd8\xff')
            with opener.open(base + '/export.zip') as response:
                self.assertIn('attachment', response.headers['Content-Disposition'])
                self.assertIn('manifest.json', zipfile.ZipFile(BytesIO(response.read())).namelist())
            for headers in ({'Content-Type': 'application/json', 'Origin': 'https://evil.example'},
                            {'Content-Type': 'text/plain', 'Origin': base},
                            {'Content-Type': 'application/json', 'Origin': base, 'Host': 'evil.example'}):
                with self.assertRaises(HTTPError) as caught:
                    opener.open(Request(base + '/capture', body, headers))
                self.assertEqual(caught.exception.code, 403)
                caught.exception.close()
            self.assertEqual(self.c.summary()['total'], 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)


if __name__ == '__main__':
    unittest.main()
