import fcntl
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from PIL import Image
from import_coco import import_coco, convert_box, yolo_line
from studio import Store
from workflow import snapshot


class CocoTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.images = self.root/'images'
        self.images.mkdir()
        self.data = dict(images=[], annotations=[], categories=[{'id': 3, 'name': 'cap'}, {'id': 8, 'name': 'bottle'}])
        self.json = self.root/'annotations.json'

    def image(self, number, category=3, crowd=0, empty=False):
        name = f'batch_1/{number}.png'
        path = self.images/name; path.parent.mkdir(exist_ok=True)
        Image.new('RGB', (100, 80), (number*20, 100, 180)).save(path)
        self.data['images'].append(dict(id=number, file_name=name, width=100, height=80))
        if not empty:
            self.data['annotations'].append(dict(id=number, image_id=number, category_id=category,
                                                 bbox=[10, 20, 20, 40], iscrowd=crowd))

    def run_import(self, **kwargs):
        self.json.write_text(json.dumps(self.data))
        out = kwargs.pop('out', self.root/'converted')
        report = import_coco(self.json, self.images, out, **kwargs)
        return Store(out), report

    def test_box_math_and_prefilled_not_reviewed(self):
        self.image(1)
        store, report = self.run_import()
        record = store.read()['records'][0]
        self.assertEqual(record['boxes'], [[10, 20, 30, 60]])
        self.assertFalse(record['reviewed'])
        self.assertEqual((store.root/'yolo_labels/train/000001.txt').read_text().strip(),
                         '0 0.20000000 0.50000000 0.20000000 0.50000000')
        self.assertEqual(record['coco']['annotations'][0]['category_id'], 3)
        self.assertEqual(record['split'], 'train')
        self.assertEqual(report['target_class'], {'0': 'debris'})

    def test_confirmed_labels_work_with_existing_snapshot(self):
        self.image(1)
        store, _ = self.run_import(accept_labels=True)
        config = snapshot(store.root, self.root/'snapshot', required=('train',))
        self.assertTrue(config.exists())
        self.assertEqual((config.parent/'labels/train/000001.txt').read_text(),
                         '0 0.20000000 0.50000000 0.20000000 0.50000000')

    def test_category_filter_empty_and_crowd(self):
        self.image(1); self.image(2, category=8); self.image(3, empty=True); self.image(4, crowd=1)
        store, report = self.run_import(category_ids=[3], include_empty=True)
        self.assertEqual(len(report['imported']), 2)
        self.assertEqual(store.read()['records'][1]['boxes'], [])
        self.assertEqual(report['skipped'], {'no_selected_target': 1, 'crowd_or_ignore_image': 1})

    def test_original_mismatch_aborts_without_output(self):
        self.image(1); self.image(2)
        self.data['images'][1]['width'] = 101
        with self.assertRaises(ValueError): self.run_import()
        self.assertFalse((self.root/'converted').exists())
        self.assertFalse(list(self.root.glob('.coco-import-*')))

    def test_exif_rotation_rejected(self):
        self.image(1)
        path = self.images/self.data['images'][0]['file_name']
        exif = Image.Exif(); exif[274] = 6
        Image.new('RGB', (100, 80)).save(path, exif=exif)
        with self.assertRaisesRegex(ValueError, 'EXIF'): self.run_import()

    def test_path_and_bbox_validation(self):
        for b in ([0, 0, -3, 4], [0, 0, float('nan'), 4], [99, 0, 2, 5]):
            with self.assertRaises(ValueError): convert_box(b, 100, 80)
        self.assertEqual(convert_box([-5, 10, 20, 40], 100, 80), [0, 10, 15, 50])
        self.image(1)
        self.data['images'][0]['file_name'] = '../outside.png'
        with self.assertRaisesRegex(ValueError, 'Unsafe'): self.run_import()

    def test_merge_preserves_base_and_skips_validation_duplicate(self):
        self.image(1); self.image(2)
        base = Store(self.root/'old_workspace')
        r = base.add((self.images/'batch_1/1.png').read_bytes(), 'real_val', 'val')
        base.save(r['id'], [[10, 20, 30, 60]], False, 0)
        original = base.path.read_bytes()
        store, report = self.run_import(base_workspace=base.root)
        self.assertEqual(base.path.read_bytes(), original)
        self.assertEqual(report['skipped'], {'duplicate_image': 1})
        records = store.read()['records']
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['split'], 'val')
        self.assertTrue(records[0]['reviewed'])
        self.assertEqual(records[1]['split'], 'train')

    def test_active_base_and_existing_output_refused(self):
        self.image(1)
        out = self.root/'converted'; out.mkdir()
        (out/'keep.txt').write_text('keep')
        with self.assertRaises(ValueError): self.run_import()
        self.assertEqual((out/'keep.txt').read_text(), 'keep')
        base = Store(self.root/'base')
        with (base.root/'.studio.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'Close'):
                self.run_import(out=self.root/'other', base_workspace=base.root)


if __name__ == '__main__': unittest.main()
