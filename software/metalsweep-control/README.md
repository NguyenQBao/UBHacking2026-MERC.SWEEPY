# METALSWEEP control

Camera, wheels and brush on the Pi 4B + OV5647, with an L298N for the wheels. The brush motor is a TSINY TS-25GAH370-20 (12 V, 300 rpm, Hall encoder, encoder not read yet) switched through a relay in front of the CCM6N speed board. Currents are not measured yet. **By default the program only simulates outputs and never touches GPIO.**

The CCM6N has no confirmed GPIO control input, so the default brush mode is CCM6N + an extra dry-contact relay: the software only switches it on and off; speed and direction stay on the board's knob and switch. Without a relay, only run the brush by hand. Never connect potentiometer wires to a GPIO.

## 1. What it does

- Live CSI detection → boxes and direction on the page; with a ground calibration, X/Y in millimetres.
- Time-limited pulses for the left wheels, right wheels and brush from the browser; everything is off at power-up.
- `--wheels-only` never opens the brush GPIO and refuses brush and Auto commands.
- With a fixed camera and ground calibration, **Auto collect nearest** runs: detect → align → approach → brush spin-up → push → brush tail → check. **Auto collect all in view** repeats this nearest-first until nothing is left in range or `max_targets` is reached.
- After each sweep the car checks the push zone: if the target is gone it counts a collection and plays the success sound; if it is still in front of the scoop it plays the miss sound and stops.
- A separate thread stops every motor action when its lease ends; each lease is at most 1 s, with at most 4 in a row. The final push time is (target distance + `entry_margin_mm`) / measured speed, limited by `sweep_seconds` (0.80 s by default). The brush keeps running across the push stages without waiting for vision.
- Losing page focus asks for STOP. Auto also checks the operator heartbeat and time/step limits. Ctrl+C or SIGTERM stops all outputs.
- No target, lost association, outside the calibration, or a stale frame never authorises more motion. The car does not search on its own.

A software timeout is not a hardware emergency stop: if the process is killed, the system freezes or a driver fails, stopping is not guaranteed. Test first with the wheels in the air and the brush clear of debris, then on a floor with barriers. There is no table-edge, collision or stall detection, so never run Auto on an open table.

## 2. Wiring: wheels first, then the brush

Wire with the power off. Program numbers are BCM, not physical pin numbers. Full details are in [docs/HARDWARE.md](../../docs/HARDWARE.md).

| Pi BCM | Pin | L298N |
|---|---:|---|
| 17 | 11 | IN1, right direction 1 |
| 27 | 13 | IN2, right direction 2 |
| 18 | 12 | ENA, right PWM |
| 22 | 15 | IN3, left direction 1 |
| 23 | 16 | IN4, left direction 2 |
| 13 | 33 | ENB, left PWM |
| GND | 6 | Driver GND, common ground |

Checked on the car (2026-11-07): OUT1/OUT2 drive the right wheels and OUT3/OUT4 the left wheels; the left side needs `invert: true` (already in `config.json`). PWM 0.22 for 0.10 s did not start the wheels; the car uses 0.5 (the program maximum), 0.3 s forward steps and 0.1 s turn steps (about 4.1° per step, 88 steps per turn).

Remove the ENA and ENB jumpers. With the external 5 V logic option, only connect the Pi's 5 V (pin 2) to the module's +5V logic input once the L298N 5V-EN regulator jumper is removed. Never let two regulator outputs fight; if your module's silkscreen or regulator differs, check it first.

The two TT motors on each side form one group. Before paralleling them, check the group's start/stall current and the module's cooling. Connect one motor per side first with the wheels in the air and confirm "forward", then add the second. Front and back wheels on one side must push the car the same way; if one wheel is reversed, swap its two wires. If a whole side is reversed, change its `invert` and restart.

**Power the TT wheels at their rated voltage; a 12 V brush does not mean the yellow TT motors can take 12 V. The Pi gets its own regulated USB-C supply; motors never draw from the Pi's 5 V.**

### Default: keep the CCM6N, add a relay for on/off

The 6 A / 180 W in the photos is the controller rating, not the motor stall current, and does not mean 180 W continuous at 12 V. Choose a relay module whose input is clearly 3.3 V compatible, that is off at start-up, and has a driver and coil flyback protection; its dry-contact DC and inrush ratings must cover the measured load. Never drive a bare relay coil from a GPIO.

```text
Pi GPIO21 (pin 40) → relay module IN (3.3 V compatible)
Pi GND             → module logic GND (per the module datasheet)
Module VCC         → its rated supply; never from a GPIO signal pin

12 V supply + → suitable fuse → physical power switch → relay COM
relay NO (normally open) → CCM6N power + input
12 V supply −            → CCM6N power − input
CCM6N motor outputs      → brush motor
Keep the CCM6N knob and direction switch
```

The dry contact only switches the 12 V positive, never bringing 12 V to the Pi; using NO (not NC) means the brush is off whenever the relay releases. The dry-contact circuit does not need the motor 12 V negative tied to the Pi; the L298N control circuit still needs a common ground.

The program defaults to `brush_mode="ccm6n_relay"`: a **digital on/off** on GPIO 21, no PWM, and GPIO 24/25 are neither wired nor opened. `relay_active_high=true` means high is on; set it to false only if the module datasheet or a test says low-active. First disconnect the 12 V and test only the relay with a multimeter: check that NO opens when the program stops, exits and when the Pi reboots. Then connect the CCM6N.

A mechanical relay is only for slow on/off switching, never for speed control. After the CCM6N loses power, stored energy and brush inertia keep it turning for a moment: measure the stop delay. If the brush takes too long to stop, change the circuit or use a driver with a supported enable input; the program cannot brake it.

### Alternative: a separate three-signal H-bridge

With a separate H-bridge that supports 3.3 V logic and enough current, set `brush_mode` to `hbridge`:

| Pi BCM | Pin | Brush H-bridge (3.3 V logic) |
|---|---:|---|
| 24 | 18 | IN1 |
| 25 | 22 | IN2 |
| 21 | 40 | EN/PWM, 500 Hz in software |
| GND | 6 / any GND | GND |

This table is **not the CCM6N wiring**. Check the new driver's interface, logic level, 500 Hz PWM support and default-off level. Its continuous and peak current must cover the brush, with flyback protection for a DC motor. Single-direction MOSFET modules or a BTS7960 need their own adapter.

Never put the brush on either channel of the wheel L298N; both are used. A GPIO can never drive a motor directly. Add about 10 kΩ pull-downs on the L298N ENA/ENB (and the H-bridge enable); **not** on a low-active relay input. Keep the brush 12 V positive separate from the wheel supply positive.

## 3. Install on the Pi (motors not powered yet)

On the Mac:

```bash
scp -r software/metalsweep-control pi@raspberrypi.local:~/
```

On the Pi, stop any other camera program first (Ctrl+C); only one program can own the CSI camera.

```bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv python3-numpy python3-gpiozero python3-lgpio python3-venv
cd ~/metalsweep-control
python3 run.py --hsv 0,220,220
```

Open **http://127.0.0.1:8091/** in the Pi's VNC browser. Buttons now only print simulated values; nothing moves.

To spare the Pi from running Chromium, use an SSH tunnel from the Mac:

```bash
ssh -N -L 8091:127.0.0.1:8091 pi@raspberrypi.local
```

Then open **http://127.0.0.1:8091/** on the Mac and keep the tunnel running. Motion control is never served on the LAN directly. If the tunnel prints `connect failed: Connection refused`, `run.py` is not running on the Pi.

`--hsv 0,220,220` matches a saturated red paper test piece (H 0–179, S/V 0–255); adjust and restart if the colour differs. Similar red objects are detected too, and the score 1 is only a colour match, **not model confidence**. Use a plain background and one test piece. If the image is upside down, set `rotate180` to true in `config.json`; calibration must use the same orientation.

Without calibration the page only shows boxes, no reliable millimetres, and Auto will not run.

## 4. Check the real wheels

After checking the wheel wiring, voltage and current, set **only `wheel_driver_verified` to true** in `config.json`, keep the other flags false, stop the simulation and run:

```bash
python3 run.py --hsv 0,220,220 --hardware --wheels-only
```

The **Wheels** section has four sliders: Drive speed, Drive step time, Turn speed and Turn step time (same ranges as the config check). Changes apply at once and are lost on restart unless you click **Save as default**, which writes them to `config.json`. **Use recommended** restores 0.50/0.10 s for both. Arrow keys ↑↓←→ step the car; Space stops everything. Re-measure step distance and angle after any change.

With the wheels in the air, click **Forward step**, **Turn left step**, **Turn right step** and **STOP ALL** one at a time. If a wheel does not start, do not leave it stalled; check power and wiring first, then raise the speed a little. `invert` only flips one side's electrical direction; never mirror the camera image, or left and right swap.

On the floor, measure the real distance d of one forward pulse and the angle of one turn, noting load and battery level. For example, 10 mm in 0.10 s is about 100 mm/s. PWM is duty cycle, **not speed**.

Set `forward_mm_per_second` from that measurement with the same PWM, load and battery. Short pulses and longer pushes can differ, so re-check with the expected push time. The final push is `t=(Y+entry_margin_mm)/forward_mm_per_second`; above `sweep_seconds` the car stops with `FINAL_PUSH_EXCEEDS_TIME_LIMIT` instead of stretching the move. Only then set `speed_calibration_verified` to true.

## 5. Fix the camera and calibrate distance

Point the camera at the floor ahead; start with 35–45° down so the image bottom shows the floor just in front of the brush and the centre looks about 200–400 mm ahead. The box must not hide the collection zone, and the ribbon must not move with the wheels or brush. Redo the calibration after any change of height, angle, resolution, lens or crop.

Coordinates: **X positive to the right of the robot, Y positive straight ahead; the origin is the centre of the scoop's front edge on the floor**, not the camera centre or the axle. Y is the forward distance from the scoop, not the slant distance from the lens.

1. With the robot still, place 6 or more small markers on the floor and measure them with a ruler. The XY values in `points.example.json` are only an example. Place markers where the camera really sees them and measure them.
2. Click **Save raw image for calibration** on the page to get `calibration.jpg`, or in another Pi terminal:

```bash
cd ~/metalsweep-control
curl http://127.0.0.1:8091/raw.jpg -o calibration.jpg
python3 calibrate.py --image calibration.jpg --points points.example.json --out ground.json
```

3. A window shows the raw image: click the markers in the order prompted; U undoes, Esc cancels. This writes `ground.json` (an existing file is not overwritten). If `rotate180` is true, add `--rotate180` here too (the raw image is already rotated; do not rotate it yourself). `/raw.jpg` is empty unless `run.py` is running.
4. If clicking the OpenCV window is awkward, click the page image to read u,v, fill each marker's `uv:[u,v]`, and add `--no-gui`. Locate markers on the raw image, never on a box edge.
5. Check with **3 more positions that were not used in the fit**: compare the ruler with the displayed millimetres. Aim for under 10 mm near the collection zone; otherwise redo. A small fit residual (2.6 mm on the car) does not prove real accuracy: lens distortion, an uneven floor and thick objects all add error.

The blue polygon is the area covered by the calibration points. A target whose box-bottom centre is outside it gets no distance and does not move the car; `ground_margin_px` relaxes this. The method suits thin debris on a near-flat floor; the box-bottom centre only approximates the contact point. Lens undistortion is not implemented.

## 6. Brush and one collection

With the default CCM6N mode, add the relay and verify its wiring, trigger level and DC load rating; set the knob to low speed and the switch to the right direction. Set `brush_driver_verified` to true and test wheels and brush in the air in full mode:

```bash
python3 run.py --hsv 0,220,220 --hardware
```

In the **Brush** section, **Brush pulse (0.3 s)** switches it on for 0.3 s; **Run brush test** runs only the brush for 0.5/1/2/3 s with the wheels off, and the badge shows ON/OFF. **Where the bristles touch the floor they must move towards the box intake/ramp.** In CCM6N mode the board's switch sets the direction; `brush.invert` only applies to the H-bridge mode. Let the bristles just touch the floor once nothing interferes.

The nameplate says 12 V, 300 rpm. The V8 orange shaft is about 30 mm across, about 0.47 m/s at the surface at 300 rpm; bristles or blades make it larger and faster, and too fast can flick light pieces away. **In CCM6N mode the knob sets the speed; `brush_speed` only means relay ON.** Judge by debris entering the box without bouncing or stalling.

The mechanics must form a continuous path: floor → low front lip/ramp → box. A step at the intake, a bare orange roller or a wide gap between roller and ramp cannot be fixed by software. Collect at least one test piece by pushing the car by hand with the brush on before trying Auto.

Once directions and distance are verified and the car is on a flat floor with barriers, set these to true:

```text
directions_verified
ground_calibration_verified
speed_calibration_verified
supervised_clear_floor
```

Set `half_brush_mm` to half the effective brush width, adjust `collect_y_mm` to the real view and intake, start `center_tolerance_mm` at 15. Check every value; never flip all flags at once to skip verification. Then run, with your trained model:

```bash
python3 run.py --model best_ncnn_model --ground ground.json --hardware
```

Keep the page in the foreground and click **Auto collect nearest** or **Auto collect all in view**. Space or STOP stops everything at any time. If no target is in view, the car stops; place the debris again and restart.

### Tuning on the page

| Control | Effect |
|---|---|
| **Final push extra (mm)**, 0–150 | `entry_margin_mm`: raise it if debris stops short of the scoop. The page shows the maximum total push |
| `tail_seconds` in `config.json`, up to 2 s | How long the brush keeps turning after the push (1.3 s in the repository config) |
| `max_targets` in `config.json`, 1–50 | Limit for Auto collect all in view |

**Save as default** keeps the page settings in `config.json`.

## 7. Sounds

The buzzer (GPIO 12) beeps when debris newly appears. The **Sound** section has:

- **All sounds on**: untick to silence every beep and melody, on the car and on the computer. Detection, Auto and STOP keep working.
- **Buzzer volume**, 0.25–0.5: the PWM duty of a passive buzzer (0.5 is loudest).
- Buttons: Test sound, Collected, Missed, All clear, Happy Birthday, and one button per extra melody. Collected / Missed / All clear also play automatically during Auto.
- **Also play on this computer**: plays the same notes in the browser.

`"passive": false` in the `buzzer` config means an active buzzer: one fixed pitch, so melodies are only rhythm. Set it to `true` for a passive piezo to hear real pitches and use the volume.

Extra melodies: put `{"name": [[hz, seconds], ...]}` in `sounds.json` next to `run.py` (max 20 melodies, 60 s each; the file is git-ignored). To copy a `[(hz, seconds), ...]` list from another Python file (parsed, never executed):

```bash
python3 melody_from_python.py other_project/controller.py melody rover_song
```

Restart `run.py` to see the new button.

## 8. Control loop and current limits

```text
Stop and wait for camera/car to settle
    ↓ 3 fresh frames in a row with the same candidate
Box-bottom centre (u,v) → ground homography H → (X,Y)
    ↓ angle = atan2(X,Y)
Right of centre → left wheels forward, right wheels back, short turn; left: the opposite
    ↓ after each pulse: stop, wait 0.35 s, detect again
Aligned and Y > collect_y_mm → one short forward pulse → measure again
    ↓ Y ≤ collect_y_mm and aligned
Brush spin-up → brush on while the wheels push (Y+margin)/speed s → wheels stop, brush tail
    ↓
Check the push zone: gone → COLLECTED (success sound) / still there → VERIFY_MISSED (miss sound)
All in view: next nearest target, until ALL_COLLECTED or MAX_TARGETS_REACHED
```

These times and thresholds are starting values. The collect stages are timed by the motor thread with the brush kept on, without stopping to look in between: a short, bounded blind push, so verify the intake and pulse distance first. The turn/approach steps confirm 3 frames **after stopping**. The nearest valid candidate goes first, and nearest-centre association stops the target from suddenly switching. It is not an appearance-based tracker: crossing or overlapping debris can still confuse it.

**A target leaving the image does not prove it entered the box.** It may have bounced sideways, entered the camera's blind zone in front of the scoop, or been missed. A sensor at the intake or a camera on the box would be needed to confirm.

Without encoders, PWM and time vary with friction, voltage and load, so the loop is stepwise and visual. Without calibration there is only left/centre/right; a single image of debris of unknown size gives no absolute distance. Without table-edge sensing, safe table-top cruising is impossible.

## 9. Using a trained model

Train on the Mac; the Pi only runs inference. The model must contain the class `debris`; a generic COCO model does not detect debris.

The Pi uses system packages for Picamera2/GPIO/OpenCV:

```bash
cd ~/metalsweep-control
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements-model.txt
python run.py --model ./best_ncnn_model --ground ground.json
```

Check detection and the action plan without `--hardware` first. The NCNN model exported by the training studio has a fixed 640 input, so `imgsz` in the config does not change its results. Watch `processing_ms`; a stale frame only makes the car wait, it never lengthens a motor action.

Record 20 single-piece runs on the floor: detections, alignments, real collections, average time and wrong moves, across materials, sizes and lighting. Detection accuracy and collection success are separate numbers. Model training, mechanics and distance calibration are three separate tuning jobs.

## 10. Local checks and references

```bash
python3 -m unittest -v test_control.py test_http.py
```

The tests cover state transitions, turn signs, lost/stale frames, motor expiry, the simulated GPIO adapter and setup failures, the collect check and Auto modes, sounds, wheels-only mode, ground calibration and rejection outside it. They use simulated outputs and synthetic images and do not replace tests of current, stopping distance, torque, bristles or the printed parts. See [VERIFICATION.md](VERIFICATION.md).

- L298 datasheet: https://www.st.com/resource/en/datasheet/l298.pdf
- Module power/interface: https://docs.sunfounder.com/projects/3in1-kit-v2/en/latest/components/component_l298n_module.html
- GPIO Zero outputs: https://gpiozero.readthedocs.io/en/stable/api_output.html
- Pi hardware/GPIO: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- OpenCV homography: https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html
- Ultralytics NCNN: https://docs.ultralytics.com/integrations/ncnn/
