"""Build pi4b-l298n-wiring.pdf and its PNG pages from the official photos.

Needs: pip install reportlab pymupdf
"""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import pymupdf

P = Path(__file__).resolve().parent
PDF = P/'pi4b-l298n-wiring.pdf'
c = canvas.Canvas(str(PDF), pagesize=(1120, 850))


def t(x, y, s, n=13, col='#18384c', bold=False):
    c.setFont('Helvetica-Bold' if bold else 'Helvetica', n)
    c.setFillColor(HexColor(col))
    c.drawString(x, y, s)


def box(x, y, w, h, col='#eef4f7'):
    c.setFillColor(HexColor(col)); c.setStrokeColor(HexColor('#71909e')); c.roundRect(x, y, w, h, 7, fill=1)


def img(name, x, y, w, h):
    c.drawImage(str(P/name), x, y, w, h, preserveAspectRatio=True, anchor='c', mask='auto')


def line(a, b, col='#78929e', width=1):
    c.setStrokeColor(HexColor(col)); c.setLineWidth(width); c.line(*a, *b)


def link(x, y, label, url):
    t(x, y, label, 10, '#286c95')
    c.linkURL(url, (x, y-2, x+len(label)*5.5, y+12), relative=0)


# Physical pin, function, destination (wired on the car, 2026-11-07).
rows = [('2', '5V power', '+5V (see red note)'), ('6', 'GND', 'GND'),
        ('11', 'GPIO17', 'IN1 right'), ('13', 'GPIO27', 'IN2 right'), ('12', 'GPIO18', 'ENA right'),
        ('15', 'GPIO22', 'IN3 left'), ('16', 'GPIO23', 'IN4 left'), ('33', 'GPIO13', 'ENB left'),
        ('40', 'GPIO21', 'Brush relay IN'), ('32', 'GPIO12', 'Buzzer')]

# Page 1: photo of the Pi, wiring table, L298N pin photo.
t(28, 810, 'Raspberry Pi 4B + L298N wiring, on official photos', 26, bold=True)
t(28, 782, 'Left: Raspberry Pi official 4B photo. Right: SunFounder official L298N pin photo. The table is this project\'s wiring plan.', 13)
box(25, 336, 420, 410, '#ffffff'); t(42, 719, 'Raspberry Pi 4 Model B (official photo)', 16, bold=True)
img('raspberry-pi-4b-official-photo.jpg', 35, 392, 400, 305)
t(42, 372, 'The 40-pin GPIO header is on the board edge. Find pin 1 first, then count.', 12)
t(42, 349, 'Page 2 has the official enlarged pin map.', 12)
box(730, 336, 365, 410, '#ffffff'); t(748, 719, 'L298N: SunFounder official pin photo', 15, bold=True)
img('sunfounder-l298n-pins.jpg', 740, 360, 345, 335)
box(460, 336, 255, 410, '#f0f6f9'); t(475, 718, 'Wire by wire', 18, bold=True)
t(475, 692, 'Pi pin / function  ->  destination', 11)
y = 664
for pin, gpio, port in rows:
    t(475, y, f'{pin} / {gpio}', 12)
    t(590, y, '-> '+port, 11, '#bd342b' if pin == '2' else '#18384c')
    line((470, y-9), (705, y-9), '#c8d6df'); y -= 32
box(25, 251, 1070, 65, '#fff0d9')
t(40, 290, 'Power everything off first, then remove the ENA, ENB and 5V-EN jumpers.', 17, '#9d341e', True)
t(40, 267, 'Only connect Pi pin 2 (5V) to the board\'s +5V after the 5V-EN regulator jumper is removed. Never put 5V on a GPIO pin.', 13, '#9d341e')
box(25, 92, 520, 140); t(42, 205, 'Power', 18, bold=True)
t(42, 178, 'Pi: its own regulated 5V / 3A supply through USB-C.', 13)
t(42, 153, 'Motor supply: + through a switch to the 12V/VS terminal, - to GND.', 13)
t(42, 128, 'Pi GND, driver GND and motor-supply negative share one ground.', 13)
t(42, 103, 'Check the motor voltage before switching on; never join the two positives.', 12, '#a44022')
box(560, 92, 535, 140); t(578, 205, 'Motors, brush and camera', 18, bold=True)
t(578, 178, 'OUT1 + OUT2: right-side motors. OUT3 + OUT4: left-side motors.', 13)
t(578, 153, 'Two motors per side in parallel: check their total current first.', 12)
t(578, 128, 'Camera ribbon -> Pi CAMERA (CSI), not the GPIO header.', 13)
t(578, 103, 'Brush: relay on GPIO21 (pin 40). First motor test with wheels in the air.', 12)
link(28, 60, 'Raspberry Pi official documentation', 'https://www.raspberrypi.com/documentation/computers/raspberry-pi.html')
link(410, 60, 'SunFounder official documentation', 'https://docs.sunfounder.com/projects/3in1-kit-v2/en/latest/components/component_l298n_module.html')
t(28, 26, 'Official photos placed as-is, board parts not redrawn; check the terminals against your own board\'s silkscreen. Page 1 of 2.', 10)
c.showPage()

# Page 2: full official pin map.
t(28, 810, 'Official Raspberry Pi 40-pin header (applies to the Pi 4B)', 24, bold=True)
t(28, 781, 'The board outline is generic; wire by the circled physical numbers 1-40. GPIO17 is physical pin 11.', 13)
img('raspberry-pi-40pin-official.png', 25, 220, 1070, 540)
box(25, 96, 1070, 100)
t(42, 172, 'Physical pins used by this project: 2, 6, 11, 12, 13, 15, 16, 32, 33, 40.', 18, bold=True)
t(42, 142, 'Software GPIO18 = jumper wire on physical pin 12; GPIO13 = pin 33; GPIO21 = pin 40; GPIO12 = pin 32.', 14)
t(42, 115, '"3V3 power" in the official image is the 3.3V supply, not 5V logic. Pin 2 (5V power) is not GPIO2.', 13, '#a44022')
link(28, 62, 'Source: Raspberry Pi official hardware documentation / GPIO', 'https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio')
t(28, 26, 'Official pin map kept complete. Page 2 of 2. Wire with power off; check jumpers and motor voltage before powering up.', 10)
c.save()

doc = pymupdf.open(PDF)
for i, page in enumerate(doc):
    page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(P/f'pi4b-l298n-wiring-page{i+1}.png')
