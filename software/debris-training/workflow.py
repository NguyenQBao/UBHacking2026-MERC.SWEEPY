"""Cumulative YOLO training with immutable, scene-separated dataset snapshots."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

from studio import Store, SPLITS, write_json

HERE = Path(__file__).resolve().parent


def unique_name(prefix):
    return prefix + '_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')


def snapshot(root, destination, required=('train', 'val')):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    data = Store(root).read()
    records = [r for r in data['records'] if r['reviewed']]
    sessions, hashes = {}, {}
    for r in records:
        if r['split'] not in SPLITS:
            raise ValueError('Bad split: ' + r['id'])
        if sessions.setdefault(r['session'], r['split']) != r['split']:
            raise ValueError('One scene appears in several splits; export refused')
        if hashes.setdefault(r['sha256'], r['split']) != r['split']:
            raise ValueError('Duplicate image across splits; export refused')
    for split in required:
        subset = [r for r in records if r['split'] == split]
        if not subset or not any(r['boxes'] for r in subset):
            raise ValueError(f'{split} needs at least one labelled photo with debris; collect an independent scene and save its labels')
    destination.mkdir(parents=True, exist_ok=False)
    counts = {}
    for split in SPLITS:
        (destination / 'images' / split).mkdir(parents=True)
        (destination / 'labels' / split).mkdir(parents=True)
        counts[split] = dict(images=0, positive=0, negative=0)
    for r in records:
        source = root / r['file']
        content = source.read_bytes()
        if sha256(content).hexdigest() != r['sha256']:
            raise ValueError('Original photo was modified; export refused: ' + r['id'])
        split, width, height = r['split'], r['width'], r['height']
        rows = []
        for box in r['boxes']:
            if len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box):
                raise ValueError('Corrupt label: ' + r['id'])
            x1, y1, x2, y2 = box
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError('Box outside image: ' + r['id'])
            rows.append(f'0 {(x1+x2)/(2*width):.8f} {(y1+y2)/(2*height):.8f} '
                        f'{(x2-x1)/width:.8f} {(y2-y1)/height:.8f}')
        (destination / 'images' / split / (r['id'] + '.jpg')).write_bytes(content)
        (destination / 'labels' / split / (r['id'] + '.txt')).write_text('\n'.join(rows), encoding='utf-8')
        counts[split]['images'] += 1
        counts[split]['positive' if rows else 'negative'] += 1
    config = f'path: {json.dumps(str(destination), ensure_ascii=False)}\ntrain: images/train\nval: images/val\n'
    if counts['test']['images']:
        config += 'test: images/test\n'
    config += 'names:\n  0: debris\n'
    (destination / 'data.yaml').write_text(config, encoding='utf-8')
    write_json(destination / 'provenance.json', dict(created=datetime.now(timezone.utc).isoformat(),
               counts=counts, ignored_unreviewed=len(data['records'])-len(records), records=records))
    print('Snapshot: ' + json.dumps(counts, ensure_ascii=False), flush=True)
    print(f'{len(data["records"])-len(records)} unconfirmed photo(s) are left out of training and evaluation.', flush=True)
    return destination / 'data.yaml'


EXPORT_README = '''METALSWEEP debris 训练数据导出
导出时间：{created}
格式：{kind}

yolo   = 标准YOLO检测数据集（只含已确认标注）。images/{{train,val,test}}、labels/{{train,val,test}}、data.yaml、provenance.json。
         类别 0 = debris。可直接用于 Ultralytics：yolo detect train data=data.yaml（data.yaml 的 path 为解压目录 .）。
backup = 完整工作区备份（含未确认图片）。images/ + manifest.json；解压成一个文件夹后用
         python studio.py --root 该文件夹  即可继续标注/训练。
'''


def export_dataset(root, out, kind='yolo'):
    """Write a portable ZIP of the training data. kind='yolo' (reviewed, standard layout) or 'backup' (everything)."""
    if kind not in ('yolo', 'backup'):
        raise ValueError('Export format must be yolo or backup')
    root, out = Path(root).resolve(), Path(out).resolve()
    store = Store(root)
    data = store.read()
    if not data['records']:
        raise ValueError('No photos to export yet')
    out.parent.mkdir(parents=True, exist_ok=True)
    partial = out.with_name(out.name + '.partial')
    created = datetime.now(timezone.utc).isoformat()
    counts = {}
    with tempfile.TemporaryDirectory() as temp, zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('README_EXPORT.txt', EXPORT_README.format(created=created, kind=kind))
        if kind == 'yolo':
            folder = Path(temp) / 'dataset'
            snapshot(root, folder, required=())
            text = (folder / 'data.yaml').read_text(encoding='utf-8').splitlines()
            (folder / 'data.yaml').write_text('\n'.join(['path: .'] + text[1:]) + '\n', encoding='utf-8')
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    # JPEGs are already compressed; store them to keep export fast.
                    method = zipfile.ZIP_STORED if path.suffix == '.jpg' else zipfile.ZIP_DEFLATED
                    archive.write(path, path.relative_to(folder).as_posix(), compress_type=method)
            counts = json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))['counts']
        else:
            for r in data['records']:
                source = root / r['file']
                if sha256(source.read_bytes()).hexdigest() != r['sha256']:
                    raise ValueError('Original photo was modified; export refused: ' + r['id'])
                archive.write(source, r['file'], compress_type=zipfile.ZIP_STORED)
            archive.writestr('manifest.json', json.dumps(data, ensure_ascii=False, indent=2))
            counts = dict(images=len(data['records']), reviewed=sum(r['reviewed'] for r in data['records']))
    partial.replace(out)
    print(f'Exported {out}: ' + json.dumps(counts, ensure_ascii=False), flush=True)
    return out, counts


def import_collection(root, source):
    """Import a Pi data-collector ZIP (or its folder): photos keep their scene and split, labels stay unreviewed."""
    store = Store(root)
    source = Path(source).expanduser().resolve()
    added, skipped, errors = 0, 0, []
    def entries():
        if source.is_dir():
            manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
            for r in manifest['records']:
                yield r, (source / r['file']).read_bytes()
        else:
            with zipfile.ZipFile(source) as archive:
                manifest = json.loads(archive.read('manifest.json'))
                for r in manifest['records']:
                    yield r, archive.read(r['file'])
    for record, raw in entries():
        if record.get('split') not in SPLITS or not record.get('scene'):
            errors.append(f'{record.get("file")}: missing scene or split')
            continue
        if sha256(raw).hexdigest() != record.get('sha256'):
            errors.append(f'{record["file"]}: checksum mismatch, file may be corrupt')
            continue
        tag = 'collector:' + record['file'] + (':empty' if record.get('empty') else '')
        try:
            store.add(raw, record['scene'], record['split'], tag)
            added += 1
        except ValueError as error:
            if 'already exists' in str(error):
                skipped += 1
            else:
                errors.append(f'{record["file"]}: {error}')
    result = dict(added=added, skipped_duplicates=skipped, errors=errors[:50], error_count=len(errors))
    print('Collection import: ' + json.dumps(result, ensure_ascii=False), flush=True)
    return result


def latest_model(root):
    candidates = list((Path(root) / 'runs').glob('round_*/weights/best.pt'))
    # Only successfully completed rounds become the default for the next round.
    candidates = [p for p in candidates if (p.parent.parent / 'round.json').exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.parent.parent.name)


def device_choice(requested):
    if requested != 'auto':
        return requested
    import torch
    if torch.cuda.is_available():
        return '0'
    if torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'


def model_path(args, initial=False):
    if args.model:
        return args.model
    if initial and getattr(args, 'fresh', False):
        return 'yolo11n.pt'
    previous = latest_model(args.root)
    if previous:
        return str(previous)
    if initial:
        return 'yolo11n.pt'
    raise ValueError('No trained model yet; train first, or pass your own weights with --model')


def metrics_dict(result):
    return {key: float(value) for key, value in result.results_dict.items()}


def run(args):
    root = Path(args.root).resolve()
    Store(root)
    # Keep library settings and font caches with this workspace, not global app preferences.
    os.environ.setdefault('YOLO_CONFIG_DIR', str(root / 'runtime' / 'ultralytics'))
    os.environ.setdefault('MPLCONFIGDIR', str(root / 'runtime' / 'matplotlib'))
    if args.command == 'import-collection':
        if not args.source:
            raise ValueError('Pass the collection ZIP or folder with --source')
        import_collection(root, args.source)
        return
    if args.command == 'export-dataset':
        out = Path(args.out) if args.out else root / 'exports' / (unique_name('dataset_' + args.format) + '.zip')
        export_dataset(root, out, args.format)
        return
    if args.command == 'prepare':
        output = root / 'snapshots' / unique_name('dataset')
        print(snapshot(root, output), flush=True)
        return
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise ValueError('Training dependencies missing. Run: python -m pip install -r requirements-train.txt') from error
    device = device_choice(args.device)
    if args.command == 'train':
        if not 1 <= args.epochs <= 300 or not 32 <= args.imgsz <= 1280 or args.batch < 1:
            raise ValueError('epochs must be 1-300, imgsz 32-1280, batch > 0')
        name = unique_name('round')
        config = snapshot(root, root / 'snapshots' / name)
        weights = model_path(args, initial=True)
        print(f'Using {weights} on device {device}; this round uses all confirmed training photos. '
              f'Early stop after {args.patience} epochs without improvement.', flush=True)
        # New data starts a new fine-tuning round, never resume=True on the old dataset.
        model = YOLO(weights)
        if args.patience < 0:
            raise ValueError('patience must be >= 0')
        model.train(data=str(config), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                    device=device, workers=0, project=str(root / 'runs'), name=name,
                    seed=42, patience=args.patience, pretrained=True, plots=True, save=True,
                    cache=False, close_mosaic=min(5, args.epochs), exist_ok=False)
        output = Path(model.trainer.save_dir)
        best = output / 'weights' / 'best.pt'
        if not best.exists():
            raise ValueError('Training produced no best.pt; check the log')
        write_json(output / 'round.json', dict(model=str(best), started_from=weights, patience=args.patience,
                   data=str(config), device=device, epochs=args.epochs, imgsz=args.imgsz,
                   ultralytics=importlib.metadata.version('ultralytics')))
        print(f'Training finished. Model: {best}\nValidation charts and results.csv: {output}', flush=True)
    elif args.command == 'evaluate':
        weights = model_path(args)
        name = unique_name('eval_' + args.split)
        config = snapshot(root, root / 'snapshots' / name, required=(args.split,))
        print(f'Evaluating split: {args.split}; weights: {weights}', flush=True)
        result = YOLO(weights).val(data=str(config), split=args.split, imgsz=args.imgsz,
                    batch=args.batch, device=device, workers=0, plots=True,
                    project=str(root / 'evaluations'), name=name)
        report = Path(result.save_dir) / 'metrics.json'
        write_json(report, dict(model=str(weights), split=args.split, data=str(config),
                               metrics=metrics_dict(result)))
        print(f'Evaluation finished: {report}\n' + json.dumps(metrics_dict(result), indent=2), flush=True)
    elif args.command == 'predict':
        if not args.source:
            raise ValueError('Pass a photo or photo folder with --source')
        output = root / 'predictions'
        name = unique_name('preview')
        # Consume the generator so prediction finishes without retaining every image in RAM.
        for _ in YOLO(model_path(args)).predict(source=args.source, conf=args.conf,
                 imgsz=args.imgsz, device=device, save=True, save_txt=True,
                 save_conf=True, project=str(output), name=name, stream=True):
            pass
        print(f'Predicted image (not human-checked): {output / name}', flush=True)
    elif args.command == 'export':
        weights = Path(model_path(args)).resolve()
        deployment = root / 'deploy' / unique_name('model')
        deployment.mkdir(parents=True)
        copy = deployment / 'best.pt'
        shutil.copy2(weights, copy)
        result = YOLO(str(copy)).export(format='ncnn', imgsz=args.imgsz, device='cpu')
        print(f'Pi model: {result}\nStill measure speed and accuracy on the Pi after export.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'train', 'evaluate', 'predict', 'export', 'export-dataset', 'import-collection'))
    parser.add_argument('--root', default=str(HERE / 'workspace'))
    parser.add_argument('--model', help='默认使用上一轮成功训练的best.pt，首轮用yolo11n.pt')
    parser.add_argument('--device', default='auto', choices=('auto', 'cpu', 'mps', '0'))
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--batch', type=int, default=4)
    parser.add_argument('--fresh', action='store_true', help='train: start from yolo11n.pt instead of the last round')
    parser.add_argument('--patience', type=int, default=50,
                        help='train: stop after this many epochs without val improvement (0 = never). '
                             'Fine-tuning dips first, so a small value stops too early')
    parser.add_argument('--split', choices=('val', 'test'), default='test')
    parser.add_argument('--source')
    parser.add_argument('--conf', type=float, default=.35)
    parser.add_argument('--format', choices=('yolo', 'backup'), default='yolo', help='export-dataset 格式')
    parser.add_argument('--out', help='export-dataset 输出 ZIP 路径；默认 workspace/exports/')
    args = parser.parse_args()
    try:
        run(args)
    except Exception as error:
        print(f'Failed: {error}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
