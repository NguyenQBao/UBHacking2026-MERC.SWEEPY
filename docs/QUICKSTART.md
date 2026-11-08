# Quick start

Run every relative path below from the repository root. The examples use the Pi user `pi` and the address `raspberrypi.local`; replace them with your own. Give each foreground service its own terminal. Only one program at a time can own the CSI camera.

## 1. Pi camera and simulated control

Copy `software/metalsweep-control` from the Mac to the Pi:

```bash
scp -r software/metalsweep-control pi@raspberrypi.local:~/
```

On the Pi (stop any other camera program, such as `rpicam-hello`, first):

```bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv python3-numpy python3-gpiozero python3-lgpio python3-venv
cd ~/metalsweep-control
python3 run.py --hsv 0,220,220
```

This is the red test-object mode, not general debris detection. It runs in simulation by default, with no GPIO output. Do not add `--hardware` until the drivers and voltages have been checked.

In another Mac terminal, open the tunnel:

```bash
ssh -N -L 8091:127.0.0.1:8091 pi@raspberrypi.local
```

Open http://127.0.0.1:8091/ on the Mac. The unannotated camera image is at http://127.0.0.1:8091/raw.jpg. Keep the tunnel terminal running.

## 2. Mac training studio

From the repository root, in a new Mac terminal:

```bash
cd software/debris-training
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-train.txt
python studio.py --camera-url http://127.0.0.1:8091/raw.jpg
```

Open http://127.0.0.1:8090/. For collecting and labelling only, `requirements-label.txt` is enough; install the full requirements before training.

The default workspace is `software/debris-training/workspace`, excluded by `.gitignore`. The first run downloads the official pretrained weights, so it needs internet. Training defaults: 30 epochs, batch 4, imgsz 640, patience 50, and automatic CUDA/MPS/CPU selection. You can keep labelling during training; the snapshot of the current round does not change.

Photos can also come from the Pi data collector: see [software/debris-collector](../software/debris-collector).

## 3. Field data and public annotations

Collect real debris first, following the [data plan](DATA.md). To convert COCO-format annotations:

```bash
python import_coco.py --annotations /path/to/TACO/data/annotations.json --list-categories
python import_coco.py --annotations /path/to/TACO/data/annotations.json --images /path/to/TACO/data --out ./workspace_coco --category-ids 7,8,33 --limit 200
python studio.py --root ./workspace_coco
```

These paths are placeholders, not files in this repository. A new workspace gets pre-filled boxes that wait for human review. Public images go to train only; your own field data provides separate val/test sets. For merging into an existing workspace, see the [COCO import guide](../software/debris-training/COCO_IMPORT.md).

## 4. Calibration and real control

Verify distance mapping, measured speed, wheel directions and the brush driver one by one, then set the matching `*_verified` flags in `config.json`. Ground calibration uses 6 or more hand-measured points; automatic chessboard/ArUco calibration is not implemented. Commands and wiring conditions are in the [control guide](../software/metalsweep-control/README.md).

The CCM6N brush board keeps its own speed knob. By default the software switches it on and off through an extra relay. Never connect the potentiometer wires directly to the Pi. Without a relay, or before the brush interface is verified, use `--wheels-only`.

The trained model must contain the `debris` class. Test inference speed on the real Pi 4B. The NCNN export has a fixed 640 input, so the runtime `imgsz` does not change its results.
