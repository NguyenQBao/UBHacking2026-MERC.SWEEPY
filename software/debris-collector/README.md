# Pi data collector

Only **takes photos**, separate from the training studio: no labelling, no training, no motor control. Use it in the Pi's VNC browser; no SSH tunnel or Mac is needed. Photos are stored on the Pi sorted by split/scene. When you are done, export a ZIP and use **Import collection ZIP** in the Mac training studio.

## Start

By default the camera image comes from the running car program (`run.py`, 127.0.0.1:8091); both can run at the same time:

```bash
cd ~/debris-collector && python3 collect.py
```

Open http://127.0.0.1:8092/ in the browser. Photos are saved to `~/metalsweep-dataset` (change with `--root`).

Without the car program, the collector can own the CSI camera itself (only one program can own the camera at a time):

```bash
python3 collect.py --picamera            # add --rotate180 if the image is upside down
```

## Page controls

| Control | What it does |
|---|---|
| Live camera | Live preview (about 2 frames per second); view only, nothing saved |
| Scene | Scene name (letters/digits/_/-); change it only when the floor, place or lighting changes |
| Split | train / val / test; one scene can belong to only one split, the program refuses otherwise |
| No debris in this shot | Tick for an empty floor (about 20% of photos) |
| Capture (Enter) | Saves the current frame; an identical frame is never saved twice |
| Undo last | Deletes the last photo |
| Progress | Count per split, first-round targets (30/10/10), share of empty photos, number of scenes |
| Scenes | Split and photo count of each scene |
| Download collection ZIP | Exports all photos + `manifest.json` to the Pi's Downloads folder |

## Moving to the Mac and importing

Copy it in a Mac terminal (adjust the file name):

```bash
scp pi@<pi-address>:~/Downloads/metalsweep_collection_*.zip ~/Downloads/
```

Or copy the whole collection folder: `scp -r pi@<pi-address>:~/metalsweep-dataset ~/Downloads/`.

In the Mac training studio, choose the ZIP under **Import collection ZIP** in section 1, or on the command line:

```bash
python workflow.py import-collection --source ~/Downloads/metalsweep_collection_XXXX.zip
```

Scenes and splits are kept. Photos arrive unconfirmed: draw boxes or confirm "no debris" for each one in the studio before it enters training. Importing the same ZIP again skips photos that already exist.

## Storage layout

```text
~/metalsweep-dataset/
  manifest.json                       # per photo: file, scene, split, empty, sha256, captured
  images/train/deskA_day/0001.jpg
  images/val/deskB_day/0001.jpg
```

Python standard library only (`--picamera` needs the system Picamera2). Test: `python3 -m unittest test_collect`.
