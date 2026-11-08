# Data plan

The model predicts a single class, `debris`: every small item the car should sweep up (brass tubes and caps on the car today; paper balls and bottle caps in the original plan). Shoot from the final OV5647 camera position: fix the mount first, then collect. Use the unannotated raw image, never a VNC screenshot or a prediction image with boxes.

## Hackathon budget

Run the whole loop on 50 photos first; about 100 photos is the budget for version 1, for example 35 of each main debris type, 10 mixed and 20 empty scenes. Most photos should hold 1–3 targets. Split train/val/test by separate shooting scenes, roughly 70/15/15; keeping scenes separate matters more than the exact ratio.

Cover different sizes, colours and poses (face up, face down, on the side), near/middle/far and left/centre/right positions, and real lighting with shadows. Draw tight boxes around every target that should be swept, and confirm empty photos as empty.

Plan the next 50 photos around validation failures: missed shapes, backgrounds that cause false positives, and new lighting. Keep the test set for milestone checks; do not tune repeatedly against it. Pause photo collection while calibration paper is on the floor or you are measuring; Mac training can continue.

Lesson from the car: every training photo so far shows light floors, while val/test include dark carpet. A model can win on mAP and still be unsure on the car. Always check confidence on the car before deploying, and add photos of each new floor and camera angle.

## TACO as a supplement

Official source: https://github.com/pedropro/TACO

Categories checked in the original `annotations.json`: 7 Plastic bottle cap, 8 Metal bottle cap, 33 Normal paper; add 31 Tissues only if tissues are also collected. Downloaded versions may renumber categories, so run `--list-categories` first. TACO "Normal paper" is not crumpled paper; field photos are still needed.

Example filter: `--category-ids "7,8,33"`. Public images do not need to be warped to the robot's view: keep the original images that match the JSON; training resizes them and merges the original categories into `debris`. A 2-D warp cannot create sides the photo never showed; only real low-angle photos close that gap.

The COCO converter pre-fills boxes for human review and imports to train only. Photos and labels from an old workspace can be copied into a new one; the originals stay. It never downloads data or turns unlabelled images into correct labels.

Other references:
- ZeroWaste: https://ai.bu.edu/zerowaste/ (industrial scenes, CC BY-NC 4.0; check the annotation version separately).
- TrashNet: https://github.com/garythung/trashnet (classification images; cannot be used as a detection set directly).

## Evaluation

Look at every prediction image, and compare precision, recall, mAP and false-positive patterns on the same field validation set. On the Pi, check missed detections and processing time. When a small target is only a few pixels, improve the image or distance first. Record detection, alignment and collection success separately.
