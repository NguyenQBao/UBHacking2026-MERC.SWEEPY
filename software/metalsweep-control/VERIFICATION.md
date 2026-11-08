# Verification log

## 2026-11-04 (first release)

Environment: Mac, temporary Python 3.14 environment; NumPy 2.5.4, OpenCV-headless 5.0.0.93. No Pi was changed; no real GPIO, power supply, motor or relay was connected.

Command: `python -m unittest -v test_control.py test_http.py`

Result: **Ran 17 tests in 2.723s — OK**.

- Config value/type checks, duplicate pins, hardware off by default.
- Three-frame stability check, left/right turn signs, stepwise approach.
- Final push computed from calibrated distance and speed; refuses to move when over the time limit.
- Brush spin-up, wheels + brush together, brush tail, then stop.
- The expiry thread really stops all simulated outputs after waiting; emergency stop clears pending push stages.
- Stale images, repeated frames, frames from before the motion, lost target, operator heartbeat timeout, cycle limit.
- A late frame after STOP never re-enables the motors.
- Simulated GPIO factory checks H-bridge reversal, enable off, and release of opened pins after a failure halfway through setup.
- CCM6N mode opens only the brush relay GPIO (now GPIO 21) as a digital output, never GPIO 24/25, never PWM to a mechanical relay; supports high- and low-level modules.
- Wheels-only opens only the wheel pins and refuses brush and Auto commands.
- Synthetic ground calibration projection, rejection outside the calibrated area, rejection of mismatched orientation/resolution.
- A synthetic red target is found anywhere in the image, without a static background.
- Loopback HTTP checks the control session, ignores unauthorised requests, STOP and the camera-error gate.
- A real `run.py` subprocess reads a synthetic camera image, serves JPEG and millimetre coordinates, starts one Auto cycle over HTTP with heartbeats; all three motor stages are seen, everything stops, SIGTERM exits with code 0.

## 2026-11-08 (Auto modes, sounds, tuning)

Same environment. Added tests for: Auto nearest and all-in-view modes, the collect check (success/miss), `max_targets`, named sounds on a passive buzzer, mute and volume, extra melodies from `sounds.json` and the melody importer, the Final push extra setting, and a brush tail longer than 1 s split into short leases. All tests pass; the control page was also clicked through in a simulation run.

## Not covered

Real CSI capture on the Pi, real PT/NCNN inference speed, CCM6N interface measurements, relay electrical/power-up state, brush run-down, wheel current, brush speed/torque, calibration accuracy, collection success rate, table-edge protection. The repository holds no model weights, real training photos or measured `ground.json`. All physical `*_verified` flags in the repository `config.json` stay false.
