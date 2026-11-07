"""Bounded stop-observe-move controller. This module needs only Python stdlib."""
from dataclasses import dataclass
import math
import threading
import time


@dataclass(frozen=True)
class Target:
    box: tuple
    confidence: float
    ground: tuple | None = None  # x right, y forward, mm from brush intake

    @property
    def center(self):
        a, b, c, d = self.box
        return ((a+c)/2, (b+d)/2)


@dataclass(frozen=True)
class Action:
    left: float = 0
    right: float = 0
    brush: float = 0
    seconds: float = .1
    label: str = 'STOP'


def validate(cfg):
    """Reject unsafe or ambiguous config before opening GPIO."""
    bounds = {
        'wheel_speed': (.05, .5), 'turn_speed': (.05, .5),
        'brush_speed': (.05, 1), 'move_seconds': (.02, .3),
        'turn_seconds': (.02, .3), 'sweep_seconds': (.02, 1),
        'forward_mm_per_second': (10, 500), 'entry_margin_mm': (0, 50),
        'spinup_seconds': (.05, 1), 'tail_seconds': (.05, 1),
        'settle_seconds': (.1, 2), 'confidence': (.1, .99),
        'angle_tolerance_deg': (1, 25), 'center_tolerance_mm': (2, 80),
        'collect_y_mm': (10, 200), 'max_y_mm': (100, 2000),
        'half_brush_mm': (10, 500), 'match_pixels': (10, 200),
        'observation_timeout': (.2, 5), 'operator_timeout': (1, 5),
        'max_cycle_seconds': (5, 120), 'max_steps': (1, 100),
        'stable_frames': (2, 10), 'imgsz': (64, 1280),
    }
    for key, (low, high) in bounds.items():
        v = cfg[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not low <= v <= high:
            raise ValueError(f'Invalid {key}: must be {low}..{high}')
    for key in ('max_steps', 'stable_frames', 'imgsz'):
        if type(cfg[key]) is not int:
            raise ValueError(f'{key} must be integer')
    if cfg['center_tolerance_mm'] >= cfg['half_brush_mm'] or cfg['collect_y_mm'] >= cfg['max_y_mm']:
        raise ValueError('Invalid brush / distance limits')
    for key in ('wheel_driver_verified', 'brush_driver_verified', 'directions_verified',
                'ground_calibration_verified', 'speed_calibration_verified', 'supervised_clear_floor', 'rotate180', 'relay_active_high'):
        if type(cfg[key]) is not bool:
            raise ValueError(f'{key} must be boolean')
    if cfg['brush_mode'] not in ('ccm6n_relay', 'hbridge'):
        raise ValueError('brush_mode must be ccm6n_relay or hbridge')
    pins = []
    for name in ('left', 'right', 'brush'):
        m = cfg['motors'][name]
        if type(m['invert']) is not bool:
            raise ValueError('invert must be boolean')
        for key in ('in1', 'in2', 'enable'):
            p = m[key]
            if type(p) is not int or not 2 <= p <= 27:
                raise ValueError('Use BCM GPIO 2..27')
            pins.append(p)
    if len(set(pins)) != 9:
        raise ValueError('GPIO pins must be distinct')
    return cfg


class Motors:
    """GPIO active only if hardware=True; a separate thread expires all motor leases.

    This is a software timeout, not a substitute for an electrical power switch.
    """
    def __init__(self, cfg, hardware=False, clock=time.monotonic, background=True, factory=None, brush_enabled=True):
        self.clock = clock
        self.lock = threading.RLock()
        self.devices = []
        self.relay = None
        self.sequence = []
        self.label = 'STOP'
        self.values = (0., 0., 0.)
        self.until = 0.
        self.closed = False
        self.brush_enabled = brush_enabled
        self.event = threading.Event()
        try:
            if hardware:
                if not cfg['wheel_driver_verified'] or (brush_enabled and not cfg['brush_driver_verified']):
                    raise ValueError('Verify BOTH driver interfaces and current capacity before --hardware')
                if factory is None:
                    from gpiozero import DigitalOutputDevice, PWMOutputDevice
                    factory = lambda pin, pwm, active_high=True: (PWMOutputDevice(pin, frequency=500, initial_value=0)
                                                if pwm else DigitalOutputDevice(pin, active_high=active_high, initial_value=False))
                bridge_brush = brush_enabled and cfg['brush_mode'] == 'hbridge'
                for name in (('left', 'right', 'brush') if bridge_brush else ('left', 'right')):
                    m = cfg['motors'][name]
                    # Enable goes low before setting direction pins.
                    en = factory(m['enable'], True)
                    self.devices.append([None, None, en, m['invert']])
                    self.devices[-1][0] = factory(m['in1'], False)
                    self.devices[-1][1] = factory(m['in2'], False)
                if brush_enabled and cfg['brush_mode'] == 'ccm6n_relay':
                    self.relay = factory(cfg['motors']['brush']['enable'], False, cfg['relay_active_high'])
            self.thread = threading.Thread(target=self._watch, daemon=True)
            if background:
                self.thread.start()
        except Exception:
            self.close()
            raise

    def _write(self, values):
        # Disable all bridges before any direction change (coast, no active brake).
        for a, b, en, invert in self.devices:
            en.value = 0
        for value, (a, b, en, invert) in zip(values, self.devices):
            value = -value if invert else value
            a.value = value > 0
            b.value = value < 0
            en.value = abs(value)
        if self.relay is not None:
            # Dry-contact relay is only ON/OFF; never send PWM to a mechanical relay.
            self.relay.value = bool(values[2])
        self.values = tuple(values)

    def pulse(self, action):
        self.run_sequence([action])

    def run_sequence(self, actions):
        if not 1 <= len(actions) <= 3:
            raise ValueError('Only 1..3 bounded actions per sequence')
        for a in actions:
            if a.brush and not self.brush_enabled:
                raise ValueError('Brush disabled: --wheels-only never opens brush GPIO')
            if any(not math.isfinite(x) or abs(x) > 1 for x in (a.left, a.right, a.brush)) or not .01 <= a.seconds <= 1:
                raise ValueError('Invalid motor pulse')
        with self.lock:
            if self.closed:
                raise RuntimeError('Motors closed')
            try:
                first = actions[0]
                self.sequence = list(actions[1:])
                self._write((first.left, first.right, first.brush))
                self.until = self.clock() + first.seconds
                self.label = first.label
            except Exception:
                self.stop()
                raise

    def stop(self):
        with self.lock:
            self.until = 0
            self.sequence = []
            self.label = 'STOP'
            # Even if one device fails, try to disable every remaining enable.
            for a, b, en, invert in self.devices:
                try:
                    en.value = 0
                except Exception:
                    pass
            self.values = (0., 0., 0.)
            if self.relay is not None:
                try:
                    self.relay.value = False
                except Exception:
                    pass

    def expire(self):
        with self.lock:
            if self.until and self.clock() >= self.until:
                try:
                    while self.sequence:
                        a = self.sequence.pop(0)
                        self.until += a.seconds
                        if self.clock() < self.until:
                            self._write((a.left, a.right, a.brush))
                            self.label = a.label
                            return
                    self.stop()
                except Exception:
                    self.stop()

    def _watch(self):
        while not self.event.wait(.02):
            self.expire()

    def close(self):
        self.stop()
        self.closed = True
        self.event.set()
        if self.relay is not None:
            self.relay.close()
        for a, b, en, invert in self.devices:
            for dev in (en, a, b):
                if dev is not None:
                    try:
                        dev.close()
                    except Exception:
                        pass


class Controller:
    def __init__(self, cfg, motors, clock=time.monotonic):
        self.cfg, self.motors, self.clock = cfg, motors, clock
        self.lock = threading.RLock()
        self.auto = False
        self.status = 'STOPPED'
        self.phase = 'OBSERVE'
        self.previous = None
        self.stable = 0
        self.ready_at = 0
        self.started = 0
        self.steps = 0
        self.operator_seen = self.clock()

    def heartbeat(self):
        with self.lock:
            self.operator_seen = self.clock()

    def stop(self, reason='STOPPED'):
        with self.lock:
            self.auto = False
            self.motors.stop()
            self.status = reason
            self.phase = 'OBSERVE'
            self.previous = None
            self.stable = 0

    def start(self, calibrated):
        with self.lock:
            self.stop()
            if not self.motors.brush_enabled:
                raise ValueError('Automatic collection needs a verified brush driver; use manual wheel steps first')
            for key in ('directions_verified', 'ground_calibration_verified', 'speed_calibration_verified', 'supervised_clear_floor'):
                if not self.cfg[key]:
                    raise ValueError(f'Set {key} only after physical verification')
            if not calibrated:
                raise ValueError('Measured ground calibration is required')
            self.operator_seen = self.started = self.clock()
            self.ready_at = self.started
            self.steps = 0
            self.auto = True
            self.status = 'OBSERVE'

    def manual(self, kind):
        c = self.cfg
        s, t, b = c['wheel_speed'], c['turn_speed'], c['brush_speed']
        actions = {
            'forward': Action(s, s, 0, c['move_seconds'], 'MANUAL_FORWARD'),
            'back': Action(-s, -s, 0, c['move_seconds'], 'MANUAL_BACK'),
            'left': Action(-t, t, 0, c['turn_seconds'], 'MANUAL_LEFT'),
            'right': Action(t, -t, 0, c['turn_seconds'], 'MANUAL_RIGHT'),
            'brush': Action(0, 0, b, .3, 'MANUAL_BRUSH'),
        }
        if kind not in actions:
            raise ValueError('Unknown command')
        with self.lock:
            self.stop()
            self._act(actions[kind])

    def brush_test(self, seconds):
        """Run only the brush for 0.3..3 s (split into <=1 s leases); wheels stay off."""
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not .3 <= seconds <= 3:
            raise ValueError('Brush test seconds must be 0.3..3')
        b, n = self.cfg['brush_speed'], math.ceil(seconds)
        actions = [Action(0, 0, b, seconds/n, 'BRUSH_TEST') for _ in range(n)]
        with self.lock:
            self.stop()
            self.motors.run_sequence(actions)
            self.ready_at = self.clock() + seconds + self.cfg['settle_seconds']
            self.status = 'BRUSH_TEST'

    TUNABLE = ('wheel_speed', 'turn_speed', 'move_seconds', 'turn_seconds')

    def set_setting(self, key, value):
        """Change one tunable value at runtime; same bounds as config validation."""
        if key not in self.TUNABLE:
            raise ValueError('Setting not adjustable')
        with self.lock:
            self.stop()
            validate(dict(self.cfg, **{key: value}))
            self.cfg[key] = value

    def settings(self):
        return {k: self.cfg[k] for k in self.TUNABLE}

    def _act(self, action):
        self.motors.pulse(action)
        self.ready_at = self.clock() + action.seconds + self.cfg['settle_seconds']
        self.status = action.label
        self.stable = 0
        self.steps += 1
        return action

    def tick(self, targets, captured_at, frame_id):
        """Only frames captured after motion+settling may authorize a new pulse."""
        with self.lock:
            self.motors.expire()
            if not self.auto:
                return None
            now, c = self.clock(), self.cfg
            if now-self.operator_seen > c['operator_timeout']:
                self.stop('OPERATOR_TIMEOUT')
                return None
            if now-self.started > c['max_cycle_seconds'] or self.steps >= c['max_steps']:
                self.stop('CYCLE_LIMIT')
                return None
            if now < self.ready_at:
                return None
            if now-captured_at > c['observation_timeout'] or captured_at < self.ready_at:
                self.status = 'WAIT_FRESH_FRAME'
                return None
            if frame_id == getattr(self, 'last_frame', None):
                return None
            self.last_frame = frame_id
            if self.phase == 'VERIFY':
                self.stop('VERIFY_CONTAINER_MANUALLY')
                return None
            good = [t for t in targets if t.confidence >= c['confidence'] and t.ground is not None
                    and all(math.isfinite(v) for v in t.ground) and 0 < t.ground[1] <= c['max_y_mm']]
            if not good:
                self.stop('TARGET_LOST_OR_OUTSIDE_CALIBRATION')
                return None
            if self.previous is None:
                target = min(good, key=lambda t: math.hypot(*t.ground))
            else:
                target = min(good, key=lambda t: math.dist(t.center, self.previous.center))
                if math.dist(target.center, self.previous.center) > c['match_pixels']:
                    self.stop('TARGET_ASSOCIATION_LOST')
                    return None
            # ponytail: nearest-centre association only; overlapping debris needs a proper tracker.
            self.previous = target
            self.stable += 1
            self.status = f'STABLE {self.stable}/{c["stable_frames"]}'
            if self.stable < c['stable_frames']:
                return None
            x, y = target.ground
            angle = math.degrees(math.atan2(x, y))
            tolerance = min(c['center_tolerance_mm'], c['half_brush_mm'] * .6)
            if abs(angle) > c['angle_tolerance_deg'] or abs(x) > tolerance:
                t = c['turn_speed']
                return self._act(Action(t if x > 0 else -t, -t if x > 0 else t,
                                        0, c['turn_seconds'], 'ALIGN_RIGHT' if x > 0 else 'ALIGN_LEFT'))
            if y > c['collect_y_mm']:
                return self._act(Action(c['wheel_speed'], c['wheel_speed'], 0, c['move_seconds'], 'APPROACH'))
            push_seconds = max(.02, (y+c['entry_margin_mm'])/c['forward_mm_per_second'])
            if push_seconds > c['sweep_seconds']:
                self.stop('FINAL_PUSH_EXCEEDS_TIME_LIMIT')
                return None
            actions = [Action(0, 0, c['brush_speed'], c['spinup_seconds'], 'BRUSH_SPINUP'),
                       Action(c['wheel_speed'], c['wheel_speed'], c['brush_speed'], push_seconds, 'SWEEP'),
                       Action(0, 0, c['brush_speed'], c['tail_seconds'], 'BRUSH_TAIL')]
            # Keep brush running across these stages; GPIO timing does not wait for inference.
            self.motors.run_sequence(actions)
            self.phase = 'VERIFY'
            self.ready_at = now + sum(a.seconds for a in actions) + c['settle_seconds']
            self.status = 'COLLECT_SEQUENCE'
            self.stable = 0
            self.steps += 1
            return actions[0]
