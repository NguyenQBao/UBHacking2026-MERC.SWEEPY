# Measurement log

Fill the blanks by measuring. Example and code default values are not real hardware parameters.

## Mounting dimensions

| Item | Current value / record |
|---|---|
| Acrylic mounting hole | Radius 10 mm (diameter 20 mm) as given; check with calipers |
| Base plate thickness | Assumed 3 mm, not measured |
| Camera board outline | 25×25 mm as given |
| Bare board thickness | Assumed 1.6 mm, not measured |
| Lens height above floor | To measure: ___ mm |
| Lens down angle | To measure: ___° |
| Effective brush width | To measure: ___ mm; `half_brush_mm` is half of it |
| Brush diameter (with bristles) | To measure: ___ mm |
| Intake front lip height | To measure: ___ mm |
| Nearest visible distance | To measure: targets visible from ___ mm in front of the intake |

## Ground calibration (6 fit points + 3 check points)

The origin is the centre of the scoop's front edge on the floor; X is positive to the right, Y positive forward, in mm. For each point record the pixel coordinates u,v and the ruler-measured X,Y. Redo it after any change of camera, resolution, rotation or crop.

| Point | u | v | X mm | Y mm | Use |
|---|---|---|---|---|---|
| 1 | | | | | Fit |
| 2 | | | | | Fit |
| 3 | | | | | Fit |
| 4 | | | | | Fit |
| 5 | | | | | Fit |
| 6 | | | | | Fit |
| 7 | | | | | Check |
| 8 | | | | | Check |
| 9 | | | | | Check |

## Motion

With the same PWM, floor, battery level and load, drive forward for 0.10/0.20/0.30 s several times each and measure the distance including the coast after stopping. Confirm directions first, and test on a floor with barriers. Then re-check the average speed with a duration close to the final push; short-pulse acceleration and longer runs differ.

For turning, count the number N of identical short pulses for one full turn each way, letting the car stop completely each time. The average angle is about 360/N degrees. Repeat 3 turns and check that 90° is close to the expected count. This is a coarse value; tyre slip is corrected by the vision loop.

| Direction | PWM | Pulse s | Distance mm / angle ° | Battery / floor | Run |
|---|---|---|---|---|---|
| Turn | 0.5 | 0.20 | 29 pulses per 360°, about 12.4° each | Not recorded | 2026-11-07 #1 |
| Turn | 0.5 | 0.10 | 88 pulses per 360°, about 4.1° each (used) | Not recorded | 2026-11-07 #2 |
| Forward | 0.5 | 0.30 | 145 mm per pulse (with coast) → `forward_mm_per_second` ≈ 483 (used) | Not recorded | 2026-11-07 #1 |
| | | | | | |

## Single-piece collection

| Run | Target / size | Start X/Y | Knob setting | Push time | Detected | Aligned | Really in the box | Failure reason |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |

The knob setting is not RPM, and a target leaving the image is not the same as entering the box. Start values such as `collect_y_mm`, `forward_mm_per_second` and `entry_margin_mm` must be tuned. The final push time is t = (Y + `entry_margin_mm`) / measured speed, limited by `sweep_seconds`. `entry_margin_mm` can also be tuned live on the control page (Final push extra).

## Camera view

| Date | Item | Measured | Effect on the config |
|---|---|---|---|
| 2026-11-07 (camera mount back to horizontal) | Image bottom edge to scoop/brush intake | 35 mm (blind zone) | Targets are invisible in the last 35 mm; `collect_y_mm` must be larger so the final push starts while the target is still visible |
| 2026-11-07 | Farthest detectable distance | > 400 mm | `max_y_mm` limits which targets trigger Auto |

After changing the mount angle or height, re-measure the blind zone and far limit, and redo the ground calibration.
