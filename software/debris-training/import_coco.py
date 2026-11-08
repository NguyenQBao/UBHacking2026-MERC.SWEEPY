"""Import COCO detection boxes into a NEW workbench workspace and YOLO labels.

No network or model dependency. Source images/workspaces are never overwritten.
"""
import argparse
from collections import Counter, defaultdict
import fcntl
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import shutil
import tempfile

from PIL import Image
from studio import Store, write_json


def load_coco(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    for name in ('images', 'annotations', 'categories'):
        if not isinstance(data.get(name), list):
            raise ValueError(f'Missing COCO {name} array; semantic masks alone are not supported')
    for name in ('images', 'annotations', 'categories'):
        ids = [item['id'] for item in data[name]]
        if any(type(v) is not int for v in ids) or len(set(ids)) != len(ids):
            raise ValueError(f'{name}: ids must be unique integers')
    images = {i['id'] for i in data['images']}
    categories = {i['id'] for i in data['categories']}
    for a in data['annotations']:
        if a['image_id'] not in images or a['category_id'] not in categories:
            raise ValueError('Annotation references unknown image/category')
    return data


def convert_box(bbox, width, height):
    if not isinstance(bbox, list) or len(bbox) != 4 or any(
        type(v) not in (int, float) or not math.isfinite(v) for v in bbox
    ):
        raise ValueError('COCO bbox must contain four finite numbers [x,y,width,height]')
    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        raise ValueError('Non-positive bbox size')
    box = [max(0., x), max(0., y), min(float(width), x+w), min(float(height), y+h)]
    if box[2]-box[0] < 2 or box[3]-box[1] < 2:
        raise ValueError('Box smaller than 2 pixels after clipping; inspect source annotation')
    return box


def yolo_line(box, width, height):
    x1, y1, x2, y2 = box
    return f'0 {(x1+x2)/(2*width):.8f} {(y1+y2)/(2*height):.8f} {(x2-x1)/width:.8f} {(y2-y1)/height:.8f}'


def copy_base(base, stage):
    """Copy dataset only; leave old weights/runs/logs in their original location."""
    data = json.loads((base/'manifest.json').read_text())
    if data.get('version') != 1:
        raise ValueError('Unsupported base workspace')
    (stage/'images').mkdir()
    for record in data['records']:
        file = Path(record['file'])
        if file.is_absolute() or len(file.parts) != 2 or file.parts[0] != 'images':
            raise ValueError('Invalid base image path')
        src = (base/file).resolve()
        if not src.is_relative_to(base) or sha256(src.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Base image missing, altered or outside workspace')
        shutil.copyfile(src, stage/file)
    write_json(stage/'manifest.json', data)


def import_coco(annotation_path, image_root, out, category_ids=None, limit=200,
                accept_labels=False, include_empty=False, base_workspace=None):
    data = load_coco(annotation_path)
    all_ids = {c['id'] for c in data['categories']}
    selected = set(category_ids) if category_ids is not None else all_ids
    if not selected or not selected <= all_ids:
        raise ValueError('Selected category IDs are empty or absent from this COCO JSON')
    if type(limit) is not int or limit < 1:
        raise ValueError('limit must be >=1')
    image_root = Path(image_root).resolve()
    out = Path(out).absolute()
    if out.exists() or out.is_symlink():
        raise ValueError('Output already exists; choose a NEW --out workspace')
    if not image_root.is_dir():
        raise ValueError('Image root not found; download the images before conversion')
    by_image = defaultdict(list)
    for a in data['annotations']:
        by_image[a['image_id']].append(a)
    out.parent.mkdir(parents=True, exist_ok=True)
    base_lock = None
    try:
        base = Path(base_workspace).resolve() if base_workspace else None
        if base:
            if not (base/'manifest.json').is_file() or out.resolve().is_relative_to(base):
                raise ValueError('Base must be an existing workspace; --out must be outside it')
            # Match the existing studio process lock; copying while it edits would be inconsistent.
            base_lock = (base/'.studio.lock').open('a')
            try:
                fcntl.flock(base_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Close the base workspace studio before merging') from None
        with tempfile.TemporaryDirectory(prefix='.coco-import-', dir=out.parent) as temporary:
            stage = Path(temporary)/'workspace'
            stage.mkdir()
            if base:
                copy_base(base, stage)
            store = Store(stage)
            imported, skipped = [], Counter()
            source_hash = sha256(Path(annotation_path).read_bytes()).hexdigest()
            for image in sorted(data['images'], key=lambda x: x['id']):
                if len(imported) >= limit:
                    break
                anns = by_image[image['id']]
                relevant = [a for a in anns if a['category_id'] in selected]
                if any(a.get('iscrowd', 0) or a.get('ignore', 0) for a in relevant):
                    skipped['crowd_or_ignore_image'] += 1
                    continue
                if not relevant and not (include_empty and not anns):
                    skipped['no_selected_target'] += 1
                    continue
                file = Path(image['file_name'])
                source = (image_root/file).resolve()
                if file.is_absolute() or not source.is_relative_to(image_root):
                    raise ValueError(f'Unsafe image path: {file}')
                raw = source.read_bytes()
                with Image.open(BytesIO(raw)) as original:
                    # Store auto-rotates EXIF; reject here rather than silently misalign imported boxes.
                    if original.getexif().get(274, 1) != 1:
                        raise ValueError(f'{file}: EXIF rotation needs coordinated image/box correction')
                    if original.size != (image['width'], image['height']):
                        raise ValueError(f'{file}: dimensions differ from COCO JSON; use matching original images')
                boxes = [convert_box(a['bbox'], image['width'], image['height']) for a in relevant]
                try:
                    record = store.add(raw, 'public_coco_'+source_hash[:12], 'train',
                                       source=f'coco:{source_hash[:12]}:{image["id"]}')
                except ValueError as e:
                    if str(e) == 'This image already exists; not added again':
                        skipped['duplicate_image'] += 1
                        continue
                    raise
                if accept_labels:
                    store.save(record['id'], boxes, not boxes, 0)
                else:
                    current = store.read()
                    current['records'][-1]['boxes'] = boxes
                    write_json(store.path, current)
                current = store.read()
                current['records'][-1]['coco'] = dict(image=image, annotations=relevant,
                                                     annotation_sha256=source_hash)
                write_json(store.path, current)
                # Label files are an interchange copy; the studio uses manifest.json as truth.
                folder = stage/'yolo_labels'/'train'
                folder.mkdir(parents=True, exist_ok=True)
                (folder/(record['id']+'.txt')).write_text('\n'.join(
                    yolo_line(b, record['width'], record['height']) for b in boxes)+'\n' if boxes else '')
                imported.append(dict(id=record['id'], coco_image_id=image['id'],
                                     source_file=str(file), boxes=len(boxes)))
            if not imported:
                raise ValueError('No new eligible images; check categories, duplicates and image paths')
            report = dict(format='COCO detection -> debris workspace', annotations=str(Path(annotation_path).resolve()),
                          annotation_sha256=source_hash, categories=data['categories'],
                          selected_category_ids=sorted(selected), target_class={'0': 'debris'},
                          licenses=data.get('licenses', []), base_workspace=str(base) if base else None,
                          imported=imported, skipped=dict(skipped), reviewed=accept_labels,
                          note='Public imports are train-only. Original per-image metadata is retained in manifest records.')
            write_json(stage/'coco_import_report.json', report)
            # Temporary workspace is published only after every imported image/box succeeds.
            if out.exists():
                raise ValueError('Output appeared during import; refusing to overwrite')
            stage.rename(out)
            return report
    finally:
        if base_lock:
            base_lock.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--annotations', required=True)
    p.add_argument('--images', help='Root containing paths from images[].file_name')
    p.add_argument('--out', help='NEW workbench workspace, must not exist')
    p.add_argument('--base-workspace', help='Optional existing dataset to copy read-only before adding public images')
    p.add_argument('--category-ids', help='Comma-separated COCO IDs; all categories if omitted')
    p.add_argument('--limit', type=int, default=200)
    p.add_argument('--list-categories', action='store_true')
    p.add_argument('--include-empty', action='store_true', help='Include genuinely unannotated empty images; verify them')
    p.add_argument('--accept-labels', action='store_true', help='Mark source labels reviewed; default is prefilled, pending review')
    args = p.parse_args()
    try:
        if args.list_categories:
            for c in load_coco(args.annotations)['categories']:
                print(f'{c["id"]}\t{c["name"]}')
            return
        if not args.images or not args.out:
            p.error('--images and --out are required for import')
        ids = [int(v.strip()) for v in args.category_ids.split(',')] if args.category_ids else None
        report = import_coco(args.annotations, args.images, args.out, ids, args.limit,
                             args.accept_labels, args.include_empty, args.base_workspace)
        print(f'Imported {len(report["imported"])} images into {args.out}; skipped={report["skipped"]}')
        print('All imported images are TRAIN only. Labels '+('accepted.' if args.accept_labels else 'prefilled; review and save them in the studio.'))
    except (ValueError, KeyError, OSError) as error:
        p.exit(1, f'未导入：{error}\n')


if __name__ == '__main__':
    main()
