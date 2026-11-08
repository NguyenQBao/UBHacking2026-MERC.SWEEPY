# Release checks · 2026-11-08

The checks run on a Mac in a temporary Python 3.14 environment with Pillow, NumPy and OpenCV-headless. No Pi, camera, GPIO, relay or motor is connected.

| Software folder | Command | Result |
|---|---|---|
| software/debris-training | `python -m unittest -v test_workflow.py test_import_coco.py` | OK |
| software/debris-collector | `python -m unittest -v test_collect.py` | OK |
| software/metalsweep-control | `python -m unittest -v test_control.py test_http.py` | OK |

The tests cover synthetic labelling, conversion and snapshots, scene-independent data splits, HTTP boundaries, ground projection, the wheel/brush state machine, motor command expiry, STOP cancelling later actions, the full offline collection cycle, the Auto nearest/all modes, the collect check and sounds.

Also checked: Python syntax, relative Markdown links, file sizes, a scan for personal paths, private IPs and credentials, and the SHA-256 file list. Run from the repository root:

```bash
python tools/check_repository.py
```

The STL files and drawings come from earlier generated material and are kept unchanged with their mesh-check records. They were not re-sliced, re-printed or re-measured for this release. The repository contains no trained weights, no TACO images and no field photos.

To reproduce the software checks, install in a temporary environment:

```bash
python -m pip install 'Pillow>=10,<14' 'numpy>=1.26,<3' 'opencv-python-headless>=4.10,<6'
```

Then run the tests in each folder (Ultralytics is not needed for these simulated checks). The host must allow loopback HTTP binding.

These results show that the code runs from the repository paths. They say nothing about field detection rate, motion accuracy, safety rating or collection success.
