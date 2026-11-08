# Hardware and wiring

| Part | Known | Still to confirm |
|---|---|---|
| Controller | Raspberry Pi 4B | Real power supply and cooling |
| Camera | Hiwonder TY-9251-OV5-V1.0 on the CSI ribbon (treated as OV5647), board 25×25 mm | Component/ribbon clearance, bare board thickness |
| Wheels | Existing four-wheel acrylic chassis, yellow TT motors, L298N | Current per side, rated voltage, wiring and direction |
| Brush | Nameplate (2026-11-06): TSINY TS-25GAH370-20, 12 V, 300 RPM, Hall encoder; replaces the JGB37-520/600 rpm motor from early shop screenshots | Rated/stall current; shaft fit in the orange brush shaft; whether to keep the CCM6N speed board; brush speed vs. collection |
| Battery | Purchase record (2026-11-03): Shentec 11.1 V 3500 mAh Li-ion pack, 3S1P 18650, robot-vacuum replacement (CEN330/CR330), 3-pin plug | Shared by the whole car?; 3-pin pinout (probably +/−/temperature); protection board; charger |
| Printer | Prusa MK4S (seen in site photos) | Real nozzle, material and lab presets |
| Distance sensor | Planned, not confirmed as installed | Model, wiring, suitability for the targets |

## Parts identified from photos (2026-11-06)

Recorded from the team's part photos. Items marked "to confirm" are not measured; do not wire from them directly.

Some parts come from the same kit and do not all need to be fitted. Current advice:

| Part | Advice | Reason |
|---|---|---|
| Brush motor, camera | Use (confirmed) | Core of collection and vision |
| Buck converter | Use the kit's LM2596-type module for the TT wheels: set it to about 7.5 V with no load and a multimeter before connecting the L298N (the L298N drops about 2 V, so the motors get about 5.5 V) | Buy a separate 5 V / 3 A+ module for the Pi (XL4015-type, or a 5 V / 5 A USB-C buck); never share one module with the wheels |
| IR obstacle sensor (facing down) | Recommended | Table-edge detection closes the "no edge sensing" gap; not yet in the software |
| HC-SR04 ultrasonic | Not for now | The main flow uses vision; add front collision protection later if needed |
| ULN2003 stepper board | Do not use | The car has no stepper motor, and it cannot reverse a DC brush motor |

| Part | Visible in the photo | Use / effect | To confirm |
|---|---|---|---|
| Brush motor | TSINY TS-25GAH370-20, DC 12.0 V, 300 RPM, 25 mm gearbox, Hall encoder at the back, 6 wires | Confirmed for the brush; 12 V can come straight from the battery; the encoder can measure speed/stall | 6-wire pinout (usually motor +/−, encoder VCC/GND/A/B); shaft diameter (often a 4 mm D-shaft); fit in the orange shaft |
| Buck converter | Blue adjustable DC-DC, 100 µF/50 V input and 220 µF/35 V output capacitors, looks like an LM2596 | Battery → TT wheel voltage or → 5 V | Real chip; LM2596-type is rated 3 A, about 2 A continuous, too tight for a Pi 4B (5 V / 3 A) |
| Camera | Hiwonder, board TY-9251-OV5-V1.0, extra 4-pin white socket on the back | Connected to the Pi by ribbon (CSI), matching the Picamera2 code | Exact sensor (treated as OV5647); 4-pin socket use (leave it unconnected); board size and hole spacing |
| Ultrasonic | HC-SR04, back marked Trig/Rx/SCL, Echo/Tx/SDA, R4/R5 select IIC/UART/1-WIRE (2020 multi-mode version) | Front obstacle/distance | Whether it works at 3.3 V; at 5 V the Echo pin is 5 V and needs a divider (e.g. 1 kΩ/2 kΩ) before the Pi |
| IR obstacle | MH-Sensor-Series (Flying-Fish), VCC/GND/OUT, comparator + potentiometer | Facing down: table edge; facing forward: close obstacles | Power at 3.3 V so OUT is not 5 V; range set by the potentiometer; dark or shiny surfaces cause false readings |
| Buzzer | GPIO 12 (pin 32). Beeps once when debris newly appears (80 ms by default, at most once per second) and plays the control page's sounds | `buzzer` in `config.json`: `passive=false` for an active buzzer (sounds when powered), `true` for a passive one (PWM tones, melodies, volume) | A bare buzzer may draw more than a GPIO can supply; use a module with a transistor; set `active_high` to false for a low-level-trigger module |
| Brush relay | Red 1-channel relay module, JQC-3FF-S-Z (12 VDC coil; contacts 10 A 30 VDC), opto input, high/low trigger jumper, DC+/DC−/IN and COM/NO/NC terminals | Confirmed: GPIO 21 switches the brush power | Jumper must be on H (high trigger); the 12 V coil runs straight from the 11.1 V battery (12.6 V when full is fine) |
| Stepper board | ULN2003, IN1–IN4, A–D LEDs, 5–12 V, 5-pin socket (usually for a 28BYJ-48) | Low-side switching in one direction only; cannot reverse a DC motor | Planned use; current and flyback if used as a switch |

## Battery and power

The battery is a 3-series Li-ion pack: 11.1 V nominal, about 12.6 V full, about 9 V empty; 3500 mAh ≈ 38.9 Wh. The limits below follow from that; check them with a multimeter before wiring.

- **Brush**: the TS-25GAH370-20 is rated 12 V and can run from the battery through fuse → main switch → relay → CCM6N (see the CCM6N brush mode below).
- **Yellow TT wheel motors**: usually rated 3–6 V and must **not** get battery voltage directly. The L298N drops about 1.5–2 V, which still leaves 7–10 V at the motor. Limiting voltage with PWM duty is only a workaround; use battery → buck converter (set to the TT rating) → L298N motor supply.
- **Raspberry Pi 4B**: needs a stable 5 V / 3 A: battery → 5 V / 3 A+ buck → USB-C or the 5 V pin. Never power it from the L298N's onboard 5 V.
- **Charging**: only use a 3S Li-ion charger (12.6 V cut-off), and never leave it charging on the car unattended. The 3-pin plug pinout is unverified; do not wire by wire colour.
- The main positive goes through a fuse and a physical main switch, then splits to brush, wheels and Pi. All negatives share a ground (except the brush circuit, isolated by the relay's dry contact).

### One battery for the whole car

```text
Battery+ → fuse → main switch ─┬→ relay → CCM6N → brush motor (12 V direct)
                               ├→ buck A (set to the TT rating, e.g. 6 V) → L298N motor supply → 4 TT wheels
                               └→ buck B (5 V / 3 A+) → Raspberry Pi 4B
Battery− → common ground (brush circuit isolated by the relay dry contact)
```

Rough power estimate (to be measured): Pi 4B + camera 5–7 W, TT wheels 3–6 W average, brush 3–8 W average, about 10–20 W in total; 38.9 Wh gives roughly 1.5–3 hours.

Notes:

1. **Pi brown-out resets**: motor starts and stalls pull the voltage down. Give the Pi its own buck converter (input range covering 9–12.6 V); add a 470–1000 µF electrolytic capacitor at the L298N and CCM6N power inputs; the software never starts wheels and brush at the same instant (the brush starts first).
2. **Battery discharge limit**: the protection board's maximum current is unknown. A brush stall plus four wheels starting together may trip it. Measure the brush stall current before choosing a fuse; use 5 A for now.
3. **Over-discharge**: stop and charge when a cell drops below about 3.3 V under load (about 9.9 V in total). Software voltage monitoring can be added later.
4. **Routing**: run motor wires apart from the Pi/camera wires, and join grounds at one point.

To buy or confirm: two buck converters (adjustable for the TT wheels; 5 V / 3 A+ for the Pi, LM2596/XL4015/MP1584-type), fuse holder and fuses, main switch, electrolytic capacitors, 3S Li-ion charger.

## L298N wheels (BCM numbering)

Wired to the car on 2026-11-07: ENB moved from GPIO 19 to GPIO 13, and the brush relay moved to GPIO 21 (pin 40). The [wiring PDF](../hardware/wiring/pi4b-l298n-wiring.pdf) matches this table. Checked on the car: IN1/IN2/ENA drive the right side and IN3/IN4/ENB the left side; the left side is reversed in software (`invert`).

| Pi GPIO | Pin | Module terminal |
|---|---:|---|
| 17 | 11 | IN1 right |
| 27 | 13 | IN2 right |
| 18 | 12 | ENA right PWM |
| 22 | 15 | IN3 left |
| 23 | 16 | IN4 left |
| 13 | 33 | ENB left PWM |
| GND | 6 | GND (common ground) |

The power and jumper plan is in the [Pi 4B wiring PDF](../hardware/wiring/pi4b-l298n-wiring.pdf) and the [control guide](../software/metalsweep-control/README.md). The external 5 V logic option only applies when the module's 5V-EN regulator jumper is removed. The drawing is not a power guarantee for every L298N clone.

Before paralleling the two motors on one side, check their total start/stall current and cooling. A 12 V brush does not mean the yellow TT motors can take 12 V; motor power never comes from the Pi's supply pins.

## CCM6N brush mode

The default is `brush_mode=ccm6n_relay`. The original board sets brush speed and direction; an extra 3.3 V-compatible relay module switches it on and off. GPIO 21 (pin 40) drives the module input. Power the module logic and set the active level as its datasheet says; never drive a bare relay coil from the Pi.

The module on the car (photo 2026-11-07): JQC-3FF-S-Z, 12 VDC coil, opto-isolated, high/low trigger jumper. Wiring:

| Module terminal | Connect to | Note |
|---|---|---|
| DC+ | Battery+ after the main switch (about 11.1–12.6 V) | 12 V coil; do not use the Pi's 5 V/3.3 V |
| DC− | Battery− (shared with Pi GND) | In high-trigger mode the IN current returns through DC−, so the grounds must be shared |
| IN | GPIO 21 (pin 40) | `relay_active_high=true` in the config, matching jumper H |
| Jumper | H (high) | Never L: in low-level mode IN is pulled up to DC+ (12 V) and would damage the GPIO |
| COM / NO | See below | Leave NC open, so the brush stops by default when power is lost or the program exits |

```text
12V+ → fuse / physical power switch → relay COM
relay NO → CCM6N power+
12V− → CCM6N power−
CCM6N motor output → brush motor
```

The relay's DC and inrush current ratings must cover the real load. The 6 A in the shop listing is the controller rating, not the motor current. This mode never sends PWM to the mechanical relay, never turns the knob and never flips the board's direction switch. Run-down after power-off and stored energy in the controller still need testing.

The optional three-signal H-bridge uses GPIO 24/25 for direction plus GPIO 21 PWM. It needs `brush_mode=hbridge` and its own driver check; it is not the CCM6N pin map.

## Print files

- Current print model: [hardware/cad-v8](../hardware/cad-v8): camera holder, brush shaft, cleaning wheel, ramp and storage box.
- Camera slot mount: [hardware/camera-slot-mount](../hardware/camera-slot-mount).
- No G-code is included; slice with your own printer's material and nozzle presets.
