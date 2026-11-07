import json
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from control import Action, Controller, Motors, Target, validate
from vision import Ground, Vision, fit_ground

HERE = Path(__file__).resolve().parent


class Clock:
    def __init__(self): self.now = 100.
    def __call__(self): return self.now
    def advance(self, n): self.now += n


class Tests(unittest.TestCase):
    def setUp(self):
        self.cfg = validate(json.loads((HERE/'config.json').read_text()))
        self.clock = Clock()
        self.motors = Motors(self.cfg, clock=self.clock, background=False)
        self.addCleanup(self.motors.close)
        self.controller = Controller(self.cfg, self.motors, self.clock)
        self.frame = 0

    def arm(self):
        for name in ('directions_verified', 'ground_calibration_verified', 'speed_calibration_verified', 'supervised_clear_floor'):
            self.cfg[name] = True
        self.controller.start(True)

    def observe(self, xy, n=3):
        result = None
        for _ in range(n):
            self.controller.heartbeat()
            self.frame += 1
            result = self.controller.tick([Target((300, 200, 330, 230), .9, xy)], self.clock(), self.frame)
            self.clock.advance(.05)
        return result

    def ready(self):
        self.clock.now = self.controller.ready_at + .01
        self.controller.heartbeat()

    def test_config_and_hardware_gate(self):
        with self.assertRaises(ValueError): Motors(self.cfg, hardware=True)
        with self.assertRaises(ValueError): self.controller.start(True)
        for key, val in [('move_seconds', -1), ('wheel_speed', float('nan')), ('stable_frames', 2.5)]:
            cfg = dict(self.cfg, **{key: val})
            with self.assertRaises(ValueError): validate(cfg)
        self.cfg['motors']['brush']['enable'] = 18
        with self.assertRaises(ValueError): validate(self.cfg)

    def test_left_right_approach(self):
        self.arm()
        a = self.observe((100, 200))
        self.assertEqual(a.label, 'ALIGN_RIGHT')
        self.assertGreater(a.left, 0); self.assertLess(a.right, 0)
        self.ready()
        a = self.observe((-100, 200))
        self.assertEqual(a.label, 'ALIGN_LEFT')
        self.ready()
        a = self.observe((0, 200))
        self.assertEqual(a.label, 'APPROACH')
        self.assertEqual(a.brush, 0)

    def test_full_cycle_stops_unverified(self):
        self.arm()
        a = self.observe((0, 55))
        self.assertEqual(a.label, 'BRUSH_SPINUP'); self.assertEqual(a.left, 0)
        self.assertAlmostEqual(self.motors.sequence[0].seconds, .65)
        self.clock.now = self.motors.until+.01; self.motors.expire()
        self.assertEqual(self.motors.label, 'SWEEP'); self.assertGreater(self.motors.values[2], 0)
        self.clock.now = self.motors.until+.01; self.motors.expire()
        self.assertEqual(self.motors.label, 'BRUSH_TAIL'); self.assertEqual(self.motors.values[0], 0)
        self.ready()
        self.observe((0, 55), 1)
        self.assertEqual(self.controller.status, 'VERIFY_CONTAINER_MANUALLY')
        self.assertEqual(self.motors.values, (0, 0, 0))
        self.assertFalse(self.controller.auto)

    def test_final_push_too_long_refuses_to_move(self):
        self.cfg['forward_mm_per_second'] = 20
        self.arm(); self.observe((0, 55))
        self.assertEqual(self.controller.status, 'FINAL_PUSH_EXCEEDS_TIME_LIMIT')
        self.assertEqual(self.motors.values, (0, 0, 0))

    def test_no_stale_or_repeated_authorization(self):
        self.arm()
        self.frame += 1
        t = [Target((300, 200, 330, 230), .9, (0, 200))]
        self.controller.tick(t, self.clock()-10, self.frame)
        self.assertEqual(self.motors.values, (0, 0, 0))
        for _ in range(5): self.controller.tick(t, self.clock(), self.frame)
        self.assertEqual(self.controller.stable, 1)
        self.assertEqual(self.motors.values, (0, 0, 0))
        self.observe((0, 200), 2)
        self.ready()
        self.controller.tick(t, self.clock()-1, 999)
        self.assertEqual(self.controller.status, 'WAIT_FRESH_FRAME')

    def test_stop_does_not_rearm_from_late_frame(self):
        self.arm(); self.observe((0, 200))
        self.controller.stop('STOP')
        self.ready(); self.observe((0, 200), 5)
        self.assertFalse(self.controller.auto)
        self.assertEqual(self.motors.values, (0, 0, 0))

    def test_target_loss_operator_timeout_and_cycle_limit(self):
        self.arm()
        self.controller.tick([], self.clock(), 1)
        self.assertFalse(self.controller.auto)
        self.arm(); self.clock.advance(3.1)
        self.controller.tick([], self.clock(), 2)
        self.assertEqual(self.controller.status, 'OPERATOR_TIMEOUT')
        self.arm(); self.clock.advance(41); self.controller.heartbeat()
        self.controller.tick([], self.clock(), 3)
        self.assertEqual(self.controller.status, 'CYCLE_LIMIT')

    def test_motor_expiry_and_real_watchdog(self):
        self.motors.pulse(Action(.2, .2, .5, .1))
        self.clock.advance(.11); self.motors.expire()
        self.assertEqual(self.motors.values, (0, 0, 0))
        live = Motors(self.cfg)
        try:
            live.pulse(Action(.2, .2, .4, .04))
            time.sleep(.1)
            self.assertEqual(live.values, (0, 0, 0))
        finally: live.close()

    def test_wheels_only_never_opens_brush_pins(self):
        self.cfg['wheel_driver_verified'] = True
        opened = []
        class Pin:
            value = 0
            def close(self): pass
        def factory(pin, pwm): opened.append(pin); return Pin()
        m = Motors(self.cfg, hardware=True, brush_enabled=False, background=False, factory=factory)
        try:
            c = Controller(self.cfg, m, self.clock)
            c.manual('forward')
            self.assertEqual(set(opened), {17, 27, 18, 22, 23, 13})
            with self.assertRaises(ValueError): c.manual('brush')
            with self.assertRaises(ValueError): c.start(True)
            self.assertEqual(m.values, (0, 0, 0))
        finally: m.close()

    def test_gpio_adapter_invert_disable_close(self):
        self.cfg.update(wheel_driver_verified=True, brush_driver_verified=True)
        self.cfg['brush_mode'] = 'hbridge'
        self.cfg['motors']['left']['invert'] = False
        self.cfg['motors']['right']['invert'] = True
        made = {}
        class Pin:
            value = 0
            def __init__(self, pin): made[pin] = self; self.closed = False
            def close(self): self.closed = True
        m = Motors(self.cfg, hardware=True, background=False, factory=lambda pin, pwm: Pin(pin))
        try:
            m.pulse(Action(.2, .2, .4, .1))
            # left = GPIO22/23 forward; right = GPIO17/27 inverted
            self.assertTrue(made[22].value); self.assertFalse(made[23].value)
            self.assertFalse(made[17].value); self.assertTrue(made[27].value)
            self.assertEqual(made[19].value, .4)
            m.stop()
            self.assertTrue(all(made[p].value == 0 for p in (18, 19, 13)))
        finally: m.close()
        self.assertTrue(all(x.closed for x in made.values()))

    def test_ccm6n_relay_is_digital_only_and_stops(self):
        self.cfg.update(wheel_driver_verified=True, brush_driver_verified=True, relay_active_high=False)
        opened = []
        class Pin:
            value = 0
            def close(self): pass
        def factory(pin, pwm, active_high=True):
            opened.append((pin, pwm, active_high)); return Pin()
        m = Motors(self.cfg, hardware=True, background=False, factory=factory)
        try:
            self.assertIn((19, False, False), opened)
            self.assertFalse(any(p[0] in (24, 25) for p in opened))
            m.pulse(Action(0, 0, .25, .1))
            self.assertIs(m.relay.value, True)
            m.stop(); self.assertIs(m.relay.value, False)
        finally: m.close()

    def test_emergency_stop_cancels_scheduled_sweep(self):
        self.motors.run_sequence([Action(0, 0, .2, .1), Action(.2, .2, .2, .2)])
        self.motors.stop()
        self.clock.advance(.15); self.motors.expire()
        self.assertEqual(self.motors.values, (0, 0, 0)); self.assertEqual(self.motors.sequence, [])

    def test_partial_gpio_init_failure_disables_created_output(self):
        self.cfg.update(wheel_driver_verified=True, brush_driver_verified=True)
        class Pin:
            value = 0
            closed = False
            def close(self): self.closed = True
        en = Pin()
        def factory(pin, pwm):
            if pwm: return en
            raise RuntimeError('pin busy')
        with self.assertRaises(RuntimeError): Motors(self.cfg, hardware=True, factory=factory)
        self.assertEqual(en.value, 0); self.assertTrue(en.closed)

    def test_calibration_and_outside_hull(self):
        points = [{'uv': [u, v], 'xy_mm': [(u-320)/2, (480-v)/2]}
                  for u, v in [(100, 100), (500, 100), (100, 400), (500, 400), (200, 250), (400, 250)]]
        data = fit_ground(points, (640, 480))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'ground.json'; p.write_text(json.dumps(data))
            g = Ground(p, False)
            np.testing.assert_allclose(g.project(320, 300), [0, 90], atol=.01)
            self.assertIsNone(g.project(10, 10))
            with self.assertRaises(ValueError): Ground(p, True)
        for point in points: point['uv'] = [100, 100]
        with self.assertRaises(ValueError): fit_ground(points, (640, 480))

    def test_hsv_is_independent_of_static_background(self):
        vision = Vision(self.cfg, hsv=[0, 240, 240])
        for shift in (0, 100):
            frame = np.zeros((480, 640, 3), np.uint8)
            frame[200:220, 300+shift:320+shift] = [10, 10, 240]
            targets = vision.detect(frame)
            self.assertEqual(len(targets), 1)
            self.assertIsNone(targets[0].ground)
            self.assertAlmostEqual(targets[0].center[0], 310+shift, delta=1)


if __name__ == '__main__': unittest.main()
