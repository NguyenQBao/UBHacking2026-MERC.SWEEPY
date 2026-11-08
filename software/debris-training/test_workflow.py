"""Checks actual labels/splits/snapshots; requires Pillow, not a GPU or camera."""
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler
from http.server import ThreadingHTTPServer
from PIL import Image, ImageDraw

from studio import Handler, Jobs, Store
from workflow import snapshot, latest_model, export_dataset, import_collection
import zipfile


def photo(index):
    image = Image.new('RGB', (100, 80), (index % 256, index // 256, 140))
    ImageDraw.Draw(image).text((10, 10), str(index), fill=(255, 255, 255))
    data = BytesIO()
    image.save(data, format='PNG')
    return data.getvalue()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'data')

    def tearDown(self):
        self.temp.cleanup()

    def add(self, index, split='train', reviewed=True, boxes=None):
        r = self.store.add(photo(index), 'scene_' + split, split)
        if reviewed:
            labels = [[10, 20, 50, 60]] if boxes is None else boxes
            r = self.store.save(r['id'], labels, not labels, 0)
        return r

    def test_batches_50_and_persistence(self):
        records = [self.add(i, reviewed=False) for i in range(51)]
        self.assertEqual(records[49]['batch'], 1)
        self.assertEqual(records[50]['batch'], 2)
        summary = Store(self.store.root).summary()
        self.assertEqual((summary['total'], summary['reviewed'], summary['in_batch']), (51, 0, 1))

    def test_explicit_negatives_and_stale_edits(self):
        r = self.add(1, reviewed=False)
        for labels, negative in (([], False), ([[5, 5, 20, 20]], True),
                                 ([[0, 0, 101, 20]], False), ([[0, 0, float('nan'), 20]], False)):
            with self.assertRaises(ValueError):
                self.store.save(r['id'], labels, negative, 0)
        self.store.save(r['id'], [], True, 0)
        self.assertEqual(self.store.summary()['counts']['train']['negative'], 1)
        with self.assertRaises(ValueError):
            self.store.save(r['id'], [], True, 0)

    def test_scene_and_duplicate_leakage_rejected(self):
        self.add(1)
        with self.assertRaises(ValueError):
            self.store.add(photo(2), 'scene_train', 'test')
        with self.assertRaises(ValueError):
            self.store.add(photo(1), 'other_scene', 'test')

    def test_cumulative_export_exact_yolo_and_frozen_snapshot(self):
        first = self.add(1)
        self.add(2, 'val')
        negative = self.add(3, 'train', boxes=[])
        self.add(4, 'test')
        pending = self.add(5, reviewed=False)
        destination = self.root / 'snapshot1'
        yaml = snapshot(self.store.root, destination)
        values = (destination / 'labels/train' / (first['id'] + '.txt')).read_text().split()
        self.assertEqual(values[0], '0')
        self.assertEqual([float(v) for v in values[1:]], [.3, .5, .4, .5])
        self.assertEqual((destination / 'labels/train' / (negative['id'] + '.txt')).read_text(), '')
        self.assertFalse((destination / 'images/train' / (pending['id'] + '.jpg')).exists())
        self.assertIn('names:\n  0: debris', yaml.read_text())
        frozen = (destination / 'labels/train' / (first['id'] + '.txt')).read_bytes()
        self.store.save(first['id'], [[20, 20, 60, 60]], False, 1)
        self.assertEqual((destination / 'labels/train' / (first['id'] + '.txt')).read_bytes(), frozen)
        self.store.save(pending['id'], [[5, 5, 15, 15]], False, 0)
        snapshot(self.store.root, self.root / 'snapshot2')
        provenance = json.loads((self.root / 'snapshot2/provenance.json').read_text())
        self.assertEqual(provenance['counts']['train']['images'], 3)

    def test_missing_validation_and_changed_images_rejected(self):
        r = self.add(1)
        with self.assertRaises(ValueError):
            snapshot(self.store.root, self.root / 'no_val')
        self.add(2, 'val')
        (self.store.root / r['file']).write_bytes(photo(30))
        with self.assertRaises(ValueError):
            snapshot(self.store.root, self.root / 'changed')

    def test_export_yolo_zip_and_full_backup(self):
        first = self.add(1)
        self.add(2, 'val')
        pending = self.add(3, reviewed=False)
        out, counts = export_dataset(self.store.root, self.root / 'out/yolo.zip', 'yolo')
        self.assertEqual(counts['train']['images'], 1)
        with zipfile.ZipFile(out) as z:
            names = set(z.namelist())
            self.assertIn(f'images/train/{first["id"]}.jpg', names)
            self.assertIn(f'labels/train/{first["id"]}.txt', names)
            self.assertNotIn(f'images/train/{pending["id"]}.jpg', names)   # unreviewed stays out
            yaml = z.read('data.yaml').decode()
            self.assertTrue(yaml.startswith('path: .\n'))                     # portable, no local path
            self.assertIn('0: debris', yaml)
            self.assertEqual(z.read(f'labels/train/{first["id"]}.txt').decode().split()[1:], ['0.30000000', '0.50000000', '0.40000000', '0.50000000'])
        out, counts = export_dataset(self.store.root, self.root / 'out/backup.zip', 'backup')
        self.assertEqual(counts, dict(images=3, reviewed=2))
        with zipfile.ZipFile(out) as z:
            z.extractall(self.root / 'restored')
        restored = Store(self.root / 'restored').summary()                     # backup reopens as a workspace
        self.assertEqual((restored['total'], restored['reviewed']), (3, 2))
        self.assertFalse(list((self.root / 'out').glob('*.partial')))
        with self.assertRaises(ValueError):
            export_dataset(self.store.root, self.root / 'x.zip', 'coco')

    def test_import_pi_collection_keeps_scene_and_split(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'debris-collector'))
        from collect import Collection
        def jpg(i):
            data = BytesIO(); Image.open(BytesIO(photo(i))).save(data, format='JPEG'); return data.getvalue()
        pi = Collection(self.root / 'pi')
        pi.add(jpg(1), 'deskA_day', 'train')
        pi.add(jpg(2), 'deskA_day', 'train', empty=True)
        pi.add(jpg(3), 'deskB_day', 'val')
        package = pi.export(self.root / 'collection.zip')
        result = import_collection(self.store.root, package)
        self.assertEqual((result['added'], result['error_count']), (3, 0))
        records = self.store.read()['records']
        self.assertEqual(sorted((r['session'], r['split']) for r in records),
                         [('deskA_day', 'train'), ('deskA_day', 'train'), ('deskB_day', 'val')])
        self.assertFalse(any(r['reviewed'] for r in records))             # still needs boxes / confirmation
        self.assertTrue(any(r['source'].endswith(':empty') for r in records))
        again = import_collection(self.store.root, self.root / 'pi')       # folder works too; duplicates skipped
        self.assertEqual((again['added'], again['skipped_duplicates']), (0, 3))
        clash = Collection(self.root / 'pi2')
        clash.add(jpg(4), 'deskA_day', 'test')                             # scene already used as train
        self.assertEqual(import_collection(self.store.root, clash.export(self.root / 'c2.zip'))['error_count'], 1)

    def test_failed_round_not_used_as_next_model(self):
        for name in ('round_001', 'round_002'):
            folder = self.store.root / 'runs' / name
            (folder / 'weights').mkdir(parents=True)
            (folder / 'weights/best.pt').write_bytes(b'test only')
        (self.store.root / 'runs/round_001/round.json').write_text('{}')
        self.assertIn('round_001', str(latest_model(self.store.root)))

    def test_http_import_label_and_origin_boundary(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.store, server.jobs, server.camera_url = self.store, Jobs(self.store.root), ''
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        opener = build_opener(ProxyHandler({}))
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with opener.open(base + '/') as response:
                self.assertIn('Debris Training Studio', response.read().decode())
            upload = Request(base + '/api/import?session=testdesk&split=train', photo(3),
                             {'Content-Type': 'application/octet-stream'})
            with opener.open(upload) as response:
                r = json.load(response)
            data = dict(id=r['id'], boxes=[[10, 10, 20, 20]], negative=False, revision=0)
            label = Request(base + '/api/label', json.dumps(data).encode(), {'Content-Type': 'application/json'})
            with opener.open(label) as response:
                self.assertTrue(json.load(response)['reviewed'])
            with opener.open(base + '/image/' + r['id'] + '.jpg') as response:
                self.assertEqual(Image.open(BytesIO(response.read())).size, (100, 80))
            with opener.open(base + '/api/export/yolo.zip') as response:
                self.assertEqual(response.headers['Content-Type'], 'application/zip')
                self.assertIn('attachment', response.headers['Content-Disposition'])
                with zipfile.ZipFile(BytesIO(response.read())) as z:
                    self.assertIn(f'labels/train/{r["id"]}.txt', z.namelist())
            with opener.open(base + '/api/export/backup.zip') as response:
                with zipfile.ZipFile(BytesIO(response.read())) as z:
                    self.assertIn('manifest.json', z.namelist())
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'debris-collector'))
            from collect import Collection
            pi = Collection(self.root / 'pi_http')
            data_jpg = BytesIO(); Image.open(BytesIO(photo(77))).save(data_jpg, format='JPEG')
            pi.add(data_jpg.getvalue(), 'deskZ', 'train')
            package = pi.export(self.root / 'pi_http.zip').read_bytes()
            with opener.open(Request(base + '/api/import-collection', package, {'Content-Type': 'application/zip'})) as response:
                self.assertEqual(json.load(response)['added'], 1)
            for headers in ({'Origin': 'https://unrelated.example'}, {'Host': 'unrelated.example'}):
                bad = Request(base + '/api/label', json.dumps(data).encode(),
                              {'Content-Type': 'application/json', **headers})
                with self.assertRaises(HTTPError) as caught:
                    opener.open(bad)
                caught.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
