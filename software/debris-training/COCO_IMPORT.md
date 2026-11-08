# TACO / COCO annotation import

This tool converts downloaded COCO detection boxes into the single class `debris` and imports them into a **new training workspace**. Original images and existing labels are never overwritten. Ultralytics is not needed; the existing Pillow dependency is enough. It does not download data, does not train, and never creates labels for unlabelled images.

## Conversion rule

COCO: `bbox=[x,y,w,h]`, where x/y is the top-left corner in pixels.

YOLO, one line per object: `class centreX/width centreY/height boxW/width boxH/height`.

For a 640×480 image and the COCO box `[100,120,80,60]`:

```text
0 0.21875000 0.31250000 0.12500000 0.12500000
```

Original category IDs need not be continuous or start at 0. The tool filters by original ID, then maps every selected category to `0: debris`. This redefines the detection target; it does not teach the model metal vs. plastic. Only merge categories that match what the car really sweeps.

## 1. Get the data

Get the official annotations and matching images from https://github.com/pedropro/TACO. A common layout is below; the tool finds images by `images[].file_name` in the JSON:

```text
TACO/
  data/
    annotations.json
    batch_1/000000.jpg
    batch_2/...
```

So for this layout `--images` is `TACO/data`, not the whole TACO folder and not `batch_1`. Use the original images whose sizes match the JSON, not web thumbnails or a resized copy. Check yourself that the download is complete; this tool does not download real data for you.

In a Mac terminal, go to the tool's folder and activate the training environment:

```bash
cd software/debris-training
source .venv/bin/activate
```

Without an environment, run `python3 -m venv .venv`, activate it, then `python -m pip install -r requirements-label.txt`.

## 2. List the categories first

This example assumes the data is in the Mac's Downloads; replace the path with yours:

```bash
python import_coco.py \
  --annotations "$HOME/Downloads/TACO/data/annotations.json" \
  --list-categories
```

The terminal prints "original ID + name". Pick the categories that match your real debris, such as bottle caps or packaging scraps. Never guess IDs from another version of the dataset.

## 3. Convert and create a new workspace

This imports all categories, at most 200 images, **to train only**:

```bash
python import_coco.py \
  --annotations "$HOME/Downloads/TACO/data/annotations.json" \
  --images "$HOME/Downloads/TACO/data" \
  --out ./workspace_coco \
  --limit 200
```

Once you have chosen categories, add `--category-ids "ID1,ID2"` with the real integer IDs from the previous step. The output path must not exist yet; use a new name for each run.

To train together with your existing field data, stop the labelling studio first, then add:

```text
--base-workspace ./workspace
```

It copies the old workspace's images and manifest into the new workspace and then adds the public data; the old data stays. Only photos and labels are copied, not old models, logs or snapshots. To continue from old weights, pass the old `best.pt` path to `workflow.py train --model`.

Public images go to train only. Use separate field photos for val/test. Exact duplicate images are skipped (including ones already in the old val/test sets); near-duplicates and frames from the same clip still need a human check.

## 4. Check the boxes in the studio

```bash
python studio.py --root ./workspace_coco
```

Open http://127.0.0.1:8090/. The public boxes are pre-filled, so there is no need to redraw them; check them and click **Save boxes & next**. Images stay unconfirmed by default, so unreviewed images never enter a training snapshot.

If you have checked the source annotations, category mapping and image orientation/size and want to accept the source labels directly, add `--accept-labels` when creating the workspace. It only records that you accept them; it does not make them correct. Still spot-check at least one batch across categories.

Then collect and label your field photos into this new workspace, split by scene into train, val and test, and train. With public train data only, training refuses to start because there is no confirmed val positive; that is the normal split check.

## Output and checks

- `images/`: normalised JPEG files used by the studio.
- `manifest.json`: images, pre-filled pixel boxes, confirmation state; the studio's source of truth.
- `yolo_labels/train/*.txt`: a YOLO copy of this import's labels, named after the new image numbers.
- `coco_import_report.json`: source, source annotation hash, category mapping, original image IDs and new numbers, skip counts, licence metadata.

`yolo_labels` is a copy made at conversion; later box edits in the studio do not update it. Training uses the immutable snapshot built from the manifest, with standard `images/train`, `labels/train` and `data.yaml`.

The tool rejects mismatched image sizes, EXIF rotation, illegal paths and broken or tiny boxes. Boxes partly outside the image are clipped to the edge; if a clipped box is under 2 pixels, the import stops. Images whose selected categories include crowd/ignore annotations are skipped, so unhandled targets never become background. Images with no target after filtering are skipped; only `--include-empty` accepts images with no annotations at all, and you must still confirm they are really empty.

The new workspace is only published after a successful conversion; a failure leaves no half-built workspace. Targets that the real data never labelled cannot be found by format conversion.

Only **COCO JSON with bboxes** is supported. Pure semantic-segmentation colour maps and classification data without boxes (such as the original TrashNet) cannot be used directly. For ZeroWaste, check the annotation structure of your downloaded version first; renaming files does not make them COCO.

Local test: `python -m unittest -v test_import_coco.py`.

Format reference: https://docs.ultralytics.com/datasets/detect/
