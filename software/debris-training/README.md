# Debris Training Studio

Collect, label and train cumulatively. Version 1 has one class, `debris`, without telling materials apart. The Mac labels and trains; the Pi 4B + OV5647 takes photos. This studio never drives motors, never drives the car and never labels photos for you.

## Quick start (importing photos is enough to use everything)

In a Mac terminal, inside this `debris-training` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-train.txt
python studio.py --camera-url http://127.0.0.1:8091/raw.jpg
```

Open **http://127.0.0.1:8090/** in Chrome or Safari on the Mac. Keep this terminal open; do not double-click `index.html`, and do not open the page in VNC. Next time you only need:

```bash
source .venv/bin/activate
python studio.py --camera-url http://127.0.0.1:8091/raw.jpg
```

[start-studio.command](start-studio.command) does the same: the first time it creates the environment and installs the training requirements, then it just starts. If macOS blocks double-clicking it, use the terminal commands above; there is no need to change security settings.

Use Python 3.11 or newer with an available PyTorch build. The development environment was Apple Silicon / Python 3.14.7, Ultralytics 8.4.194, PyTorch 2.15.0, Pillow 13.0.0. Test other systems yourself; if pip finds no matching torch, create a new virtual environment with a compatible Python. Do not install the full training stack into the Pi's system Python.

For collecting and labelling only, `requirements-label.txt` is enough; install `requirements-train.txt` into the same environment before training and restart the studio.

## Connecting the Pi camera

The camera image comes from the car's control program (`software/metalsweep-control/run.py`), which serves an unannotated 640×480 view at `/raw.jpg`: no boxes, text or masks, no brightness changes or crop; `rotate180` in its config also rotates this view.

1. Start `run.py` on the Pi (see the [control guide](../metalsweep-control/README.md)).
2. In another Mac terminal, open the tunnel: `ssh -N -L 8091:127.0.0.1:8091 pi@raspberrypi.local`.
3. Check http://127.0.0.1:8091/raw.jpg in a Mac browser: you should see a single photo without boxes. Then click **Refresh Pi camera** or **Capture one raw photo** in the studio.

Do not run `rpicam-hello` or any other program that owns the CSI camera at the same time. An unavailable camera address does not stop importing photos, labelling or training.

## Taking photos with the Pi data collector (recommended)

You can take photos with the separate [Pi data collector](../debris-collector/README.md) instead: shoot in the Pi's VNC browser, sorted by scene and split, then export a ZIP. Back in the studio, use **Import collection ZIP** in section 1; scenes and splits are kept, then draw boxes or confirm each photo. Command line: `python workflow.py import-collection --source collection.zip`.

## The first 50 photos

This is the start of the loop, not an amount that guarantees accuracy.

| Split | Example count | What to do |
|---|---:|---|
| train | 30 | Scene name `deskA_day`, split train, 30 photos |
| val | 10 | A separate scene, `deskB_day`, split val, 10 photos |
| test | 10 | Another separate scene, `deskC_evening`, split test, 10 photos |

All photos of one shooting scene must belong to one split; the program blocks a scene name from crossing splits. This is only an example: renaming a scene does not make a run of near-identical frames independent data. Build up several independent scenes per split over time. The program blocks exact duplicate images, but cannot detect near-duplicates or the same real place.

Each split should contain debris and may contain confirmed empty floors; about 20% empty photos is a good start, adding more where false positives appear. Use the real mounted camera angle and real debris sizes; cover left/centre/right, near/middle/far, different orientations, floors and lighting. Move your hand away and let the car stop before shooting, and avoid many nearly identical frames. Keep raw images; never import VNC screenshots, prediction images with boxes or masks.

Lesson from the car: training only on light floors left the model unsure on dark carpet. Add photos of every floor and camera angle the car will see.

## Labelling each batch of 50

1. Choose batch 1 under **Batch**; tick **Unconfirmed only** if you like.
2. Drag the mouse to draw a box around each recognisable piece; the class is always `debris`. Boxes should be tight, and every target that should be swept must be boxed.
3. To fix mistakes, delete a box, **Undo last box** or **Clear boxes**, then redraw.
4. Click **Save boxes & next** (or Ctrl/Cmd+S). With no debris, click **Confirm no debris & next**.
5. Labels are saved to disk, so you can close and continue later. Boxes drawn but not saved are lost.

Unconfirmed images never enter training. An empty photo must be confirmed explicitly as a negative, so a forgotten photo is never treated as background. Model predictions are never turned into human labels automatically. After 50 photos the next batch starts. You can debug with fewer, but train and val each need at least one confirmed positive, otherwise training refuses to start. That minimum only prevents empty sets; it does not mean you have enough.

## Training the next round: all data, not only the newest 50

Click **Train one round**. Defaults: 30 epochs, batch 4, input size 640, patience 50, automatic CUDA → Apple MPS → CPU; if MPS fails, retry with CPU. No account or cloud upload is needed; the first round downloads the official `yolo11n.pt`.

Each round:

- Freezes a snapshot of all confirmed labels at that moment, copying images and YOLO labels to their own folder; labelling during training does not change the data in use.
- Starts the first round from the official pretrained YOLO11n, and later rounds from the last **successful** `best.pt` as a new fine-tune (no `resume=True` on old data). Tick **Start fresh (yolo11n)** to start from the official weights again.
- Trains on all accumulated training images and checks against val automatically; the test set never takes part in training or best-weight selection.
- Writes its own model, training curves, validation predictions and log. A failed or interrupted round never becomes the next default start.

Keep shooting and labelling batches 2, 3 and so on; do not delete earlier batches. Use the validation results for day-to-day comparison; keep the test set for milestones, because tuning against it repeatedly makes it useless as an independent check.

**Ultralytics keeps the best epoch by validation mAP.** If val looks very different from train (for example dark carpet only in val), it may keep an early, under-trained epoch with low confidence. A higher mAP is not proof of a better model on the car: check confidence on the car before deploying.

Jobs run in the background; reloading the page keeps showing the current job. Do not edit one workspace from two studio processes. Stopping the web server deletes no data, but a training subprocess that already started may keep running; a restarted server does not reconnect to it, so check `workspace/logs` before starting another.

## Testing for misses and false positives

After training, **Evaluate on test set** uses the latest successful model and the confirmed test images. It writes `metrics.json`, a confusion matrix and prediction images; with no test positives it asks you to shoot more. Each evaluation also keeps a snapshot of the images and labels it used.

- Low precision: too many false positives. Add photos of the confusing backgrounds and check for missing labels.
- Low recall: too many misses. Add the missed sizes, distances, lighting and shapes.
- mAP50 and mAP50-95 compare box quality; with few test images these numbers are unstable.
- Always look through the prediction images too. A high score on a tiny test set is not reliable performance.

Command line (activate `.venv` first, run in this folder):

```bash
# Cumulative training, 30 epochs by default; adjust epochs and device
python workflow.py train --epochs 30 --device auto

# Start again from the official yolo11n weights; change early-stopping patience
python workflow.py train --fresh --patience 50

# Repeat validation for debugging; use --split test for the formal test
python workflow.py evaluate --split val
python workflow.py evaluate --split test

# Draw predictions on new unlabelled photos (never changes human labels)
python workflow.py predict --source /absolute/path/to/new/photos

# Only write the current labels as a standard YOLO dataset, no training
python workflow.py prepare

# Continue from an older model by its full path
python workflow.py train --model /absolute/path/to/best.pt --epochs 20
```

## Exporting for the Pi

**Export NCNN model for Pi** copies the latest successful model to `workspace/deploy` and converts it to NCNN; the first conversion may install public converter packages. Copy the whole generated `best_ncnn_model` folder with its metadata, never just the `.param` or `.bin` file. The NCNN input is fixed at the export size (640 by default):

```bash
python workflow.py export --imgsz 320
```

If you export at 320 for speed, re-check small-debris misses at that size. Export success is not deployment: on the Pi, run `run.py --model best_ncnn_model` and check camera preprocessing, orientation, frame rate and real accuracy. It is even less a guarantee that the car can drive safely on its own.

## Exporting training data

Section 4 has two download buttons (the browser downloads a ZIP; the workspace is not changed):

| Button | Contents | Use |
|---|---|---|
| Download YOLO dataset | **Confirmed** labels only: `images/{train,val,test}`, `labels/{train,val,test}`, `data.yaml` (`path: .`), `provenance.json` | Train on another computer, Colab or Ultralytics directly: unzip, then `yolo detect train data=data.yaml` |
| Download full backup | All photos (including unconfirmed) + `manifest.json` | Back up or move to another computer: unzip to a folder, then `python studio.py --root <folder>` |

The same from the command line (output goes to `workspace/exports/` by default):

```bash
python workflow.py export-dataset --format yolo
python workflow.py export-dataset --format backup --out ~/Desktop/metalsweep_backup.zip
```

Export also checks that no scene or duplicate image crosses splits and that the raw-image checksums match; otherwise it refuses.

## Files and backup

| File / folder | Meaning |
|---|---|
| `workspace/images` | Imported/captured JPEG photos without boxes |
| `workspace/manifest.json` | Images, scenes, splits, batches, human boxes and confirmation; the single source of truth for labels |
| `workspace/snapshots/…` | Images, YOLO txt, data.yaml and provenance.json used by each round |
| `workspace/runs/round_…/weights/best.pt` | Best weights of the round |
| `workspace/runs/round_…/results.csv` | Training and validation metrics of the round |
| `workspace/evaluations/…` | Separate evaluations and prediction images |
| `workspace/logs` | Logs of jobs started from the page |
| `workspace/deploy` | Models exported for the Pi |

Back up the whole workspace after each batch, especially `images` and `manifest.json`. Never move, resize or overwrite the raw images by hand; a checksum mismatch blocks export. Relabelled images only affect the model after retraining; old snapshots stay unchanged. The studio is a local single-user service and listens on 127.0.0.1 only.

## Development checks and limits

```bash
python -m unittest -v test_workflow.py
```

Covers the 50-photo batch boundary, save and restore, explicit empty images, stale edits, scene/duplicate leaks, YOLO coordinate conversion, unchanged snapshots, cumulative export, missing splits, raw-image checksums, successful-model selection, and HTTP import/labelling. The training smoke test uses synthetic images; it only proves the flow runs, not field accuracy. See [VERIFICATION.md](VERIFICATION.md).

References: [YOLO label format](https://docs.ultralytics.com/datasets/detect/), [training](https://docs.ultralytics.com/modes/train/), [validation/test](https://docs.ultralytics.com/modes/val/), [NCNN export](https://docs.ultralytics.com/integrations/ncnn/). Ultralytics is used under its AGPL-3.0 or commercial licence; no pretrained weights or third-party photos are included.
