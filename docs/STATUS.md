# Status and verification

Updated 2026-11-08. This page records what exists in code and on the prototype. Features that were only discussed are not counted as done.

| Area | Done | Not yet verified or implemented |
|---|---|---|
| Mac training studio | Capture, box labelling, batches of 50, cumulative snapshot training, separate evaluation, NCNN export, start-fresh option | Accuracy across floors (dark carpet and new camera angles are missing from the data) |
| Pi data collector | Photos sorted by scene and split, progress, ZIP export for the studio | — |
| COCO import | Category filter, normalisation, single-class merge, image size/orientation checks, new or merged workspace | Full real downloads; pure semantic-mask import |
| Vision control | CSI camera, HSV test or trained debris model, ground X/Y, short-pulse closed loop | Long-run latency; success rate of automatic collection |
| Auto modes | Collect nearest; collect all in view (nearest first, up to `max_targets`); check after each sweep with success/miss sounds | Searching when nothing is in view (not implemented) |
| Sound | Detection beep, named melodies, extra melodies from `sounds.json`, volume and mute | Melodies need a passive buzzer |
| Wheel and brush drivers | L298N for both wheel sides; CCM6N relay on/off; optional H-bridge | Real current, voltage, relay timing and brush run-down |
| Calibration | Hand-measured homography (6+ points), fit residual about 2.6 mm on the car | Automatic chessboard/ArUco, lens undistortion |
| CAD v8 | 7 STL files: 3 camera holder parts, brush shaft, cleaning wheel, ramp, storage box; mesh checks; box/ramp/shaft printed and test-fitted | Fixing method, second brush-shaft support, powered collection test |
| Whole-car safety | Motor commands expire on their own, STOP, operator heartbeat, cycle limits | Table edge, collision and stall sensing |

The software folders keep `VERIFICATION.md` files with earlier test records. They use synthetic data and simulated GPIO and do not replace tests on the car. Results after this clean-up are in [RELEASE_CHECKS.md](RELEASE_CHECKS.md).

## 24-hour plan

- 0–3 h: fix the camera; confirm the manual wheels, brush and intake can collect.
- 3–5 h: shoot and label the first 50 photos; start training.
- 5–9 h: add targeted data; calibrate distance and motion while training runs.
- 9–17 h: integrated tests on the Pi.
- 17–21 h: fix the main failures; add a batch of data if needed.
- 21–24 h: freeze the model and parameters, rehearse, record a backup video.

This is a time budget for the team, not a promise of training time or finish time.
