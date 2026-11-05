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
            raise ValueError('用途错误: ' + r['id'])
        if sessions.setdefault(r['session'], r['split']) != r['split']:
            raise ValueError('同一场景跨集合，拒绝导出')
        if hashes.setdefault(r['sha256'], r['split']) != r['split']:
            raise ValueError('重复图片跨集合，拒绝导出')
    for split in required:
        subset = [r for r in records if r['split'] == split]
        if not subset or not any(r['boxes'] for r in subset):
            raise ValueError(f'{split} 至少需要一张已标碎片的图片；请采集独立场景并保存标注')
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
            raise ValueError('原始图片已被修改，拒绝导出: ' + r['id'])
        split, width, height = r['split'], r['width'], r['height']
        rows = []
        for box in r['boxes']:
            if len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box):
                raise ValueError('标注损坏: ' + r['id'])
            x1, y1, x2, y2 = box
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError('框越界: ' + r['id'])
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
    print('本次快照：' + json.dumps(counts, ensure_ascii=False), flush=True)
    print(f'未确认的 {len(data["records"])-len(records)} 张不会进入训练或评估。', flush=True)
    return destination / 'data.yaml'


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
    previous = latest_model(args.root)
    if previous:
        return str(previous)
    if initial:
        return 'yolo11n.pt'
    raise ValueError('还没有训练完成的模型，请先训练，或使用 --model 指定自己的权重')


def metrics_dict(result):
    return {key: float(value) for key, value in result.results_dict.items()}


def run(args):
    root = Path(args.root).resolve()
    Store(root)
    # Keep library settings and font caches with this workspace, not global app preferences.
    os.environ.setdefault('YOLO_CONFIG_DIR', str(root / 'runtime' / 'ultralytics'))
    os.environ.setdefault('MPLCONFIGDIR', str(root / 'runtime' / 'matplotlib'))
    if args.command == 'prepare':
        output = root / 'snapshots' / unique_name('dataset')
        print(snapshot(root, output), flush=True)
        return
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise ValueError('训练依赖未安装。在训练环境执行 python -m pip install -r requirements-train.txt') from error
    device = device_choice(args.device)
    if args.command == 'train':
        if not 1 <= args.epochs <= 300 or not 32 <= args.imgsz <= 1280 or args.batch < 1:
            raise ValueError('epochs需1–300，imgsz需32–1280，batch需大于0')
        name = unique_name('round')
        config = snapshot(root, root / 'snapshots' / name)
        weights = model_path(args, initial=True)
        print(f'使用 {weights}，设备 {device}；本轮累计使用所有已确认训练数据。', flush=True)
        # New data starts a new fine-tuning round, never resume=True on the old dataset.
        model = YOLO(weights)
        model.train(data=str(config), epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
                    device=device, workers=0, project=str(root / 'runs'), name=name,
                    seed=42, patience=10, pretrained=True, plots=True, save=True,
                    cache=False, close_mosaic=min(5, args.epochs), exist_ok=False)
        output = Path(model.trainer.save_dir)
        best = output / 'weights' / 'best.pt'
        if not best.exists():
            raise ValueError('训练没有生成best.pt，请查看日志')
        write_json(output / 'round.json', dict(model=str(best), started_from=weights,
                   data=str(config), device=device, epochs=args.epochs, imgsz=args.imgsz,
                   ultralytics=importlib.metadata.version('ultralytics')))
        print(f'训练完成。模型：{best}\n验证图表和results.csv：{output}', flush=True)
    elif args.command == 'evaluate':
        weights = model_path(args)
        name = unique_name('eval_' + args.split)
        config = snapshot(root, root / 'snapshots' / name, required=(args.split,))
        print(f'评估集合：{args.split}；权重：{weights}', flush=True)
        result = YOLO(weights).val(data=str(config), split=args.split, imgsz=args.imgsz,
                    batch=args.batch, device=device, workers=0, plots=True,
                    project=str(root / 'evaluations'), name=name)
        report = Path(result.save_dir) / 'metrics.json'
        write_json(report, dict(model=str(weights), split=args.split, data=str(config),
                               metrics=metrics_dict(result)))
        print(f'评估完成：{report}\n' + json.dumps(metrics_dict(result), indent=2), flush=True)
    elif args.command == 'predict':
        if not args.source:
            raise ValueError('请通过 --source 指定照片或照片文件夹')
        output = root / 'predictions'
        name = unique_name('preview')
        # Consume the generator so prediction finishes without retaining every image in RAM.
        for _ in YOLO(model_path(args)).predict(source=args.source, conf=args.conf,
                 imgsz=args.imgsz, device=device, save=True, save_txt=True,
                 save_conf=True, project=str(output), name=name, stream=True):
            pass
        print(f'预测图片（未经人工确认）：{output / name}', flush=True)
    elif args.command == 'export':
        weights = Path(model_path(args)).resolve()
        deployment = root / 'deploy' / unique_name('model')
        deployment.mkdir(parents=True)
        copy = deployment / 'best.pt'
        shutil.copy2(weights, copy)
        result = YOLO(str(copy)).export(format='ncnn', imgsz=args.imgsz, device='cpu')
        print(f'Pi部署模型：{result}\n导出完成后仍需在Pi实测速度和精度。', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'train', 'evaluate', 'predict', 'export'))
    parser.add_argument('--root', default=str(HERE / 'workspace'))
    parser.add_argument('--model', help='默认使用上一轮成功训练的best.pt，首轮用yolo11n.pt')
    parser.add_argument('--device', default='auto', choices=('auto', 'cpu', 'mps', '0'))
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--batch', type=int, default=4)
    parser.add_argument('--split', choices=('val', 'test'), default='test')
    parser.add_argument('--source')
    parser.add_argument('--conf', type=float, default=.35)
    args = parser.parse_args()
    try:
        run(args)
    except Exception as error:
        print(f'未完成：{error}', file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
