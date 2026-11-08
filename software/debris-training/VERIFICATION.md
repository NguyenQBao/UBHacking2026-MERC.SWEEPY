# Verification before delivery

- Data and labels: 7 regression checks pass, covering the 50-photo batch boundary, save and restore, empty-image confirmation, duplicate/cross-scene split protection, cumulative YOLO export with unchanged snapshots, rejection of bad data, successful-model selection, and HTTP import/labelling.
- Pi camera: the unannotated `/raw.jpg` view is tested to contain no detection boxes.
- Browser: in real Chrome, a synthetic photo was loaded, a box dragged, saved to disk, and the next photo opened.
- Real training flow: 12 generated synthetic images (8 train, 2 val, 2 test); images of sizes other than 640×480 export correctly. YOLO11n trained at input 64 on CPU for 1 epoch and produced `best.pt`, `results.csv` and validation charts.
- Second round: a new fine-tune from the first round's successful `best.pt`; the old round is kept.
- Evaluation and prediction: evaluation on the separate test set wrote `metrics.json` and prediction images; folder prediction finished. The page's background-job API started an evaluation and reported exit code 0 with logs.
- Model export: the synthetic test model converted to NCNN with param, bin and metadata files. This does not mean it was deployed or speed-tested on the Pi.
- Environment: Apple Silicon, Python 3.14.7, Ultralytics 8.4.194, PyTorch 2.15.0, Pillow 13.0.0.

**Synthetic images only check the software flow; they do not prove debris detection. No ready-to-use real debris model is included.** Real OV5647 collection, real label quality, field accuracy, Pi inference speed and motor control are verified separately on the car.
