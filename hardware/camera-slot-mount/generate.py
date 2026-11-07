"""Camera slot mount: the camera PCB slides into a cradle that sits on top of the 10x10 mm camera post.

Requires: pip install manifold3d numpy
Run:      python generate.py            (writes camera-slot-mount.stl next to this file)
Change the parameters below after measuring your camera board with a caliper/ruler.
"""
from pathlib import Path
import struct
import numpy as np
from manifold3d import Manifold

# ---- Camera board (default = common 25 x 24 mm OV5647 board) ----
PCB_W = 25.0          # board width (mm), across
PCB_H = 24.0          # board height (mm), slide-in direction
PCB_T = 1.6           # board thickness (mm); slot = PCB_T + FIT = 2.0 mm
BACK_CLEAR = 6.0      # space behind the board for back-side parts (connector, 4-pin socket)
FIT = 0.4             # printing clearance added to width/height/thickness
LIP = 2.0             # how far the front lip overlaps each board edge
RIBBON_W = 18.0       # opening at the bottom for the ribbon cable
TILT_DEG = 30.0       # camera pitched down toward the floor (0 = straight ahead)

# ---- Post (camera-holder-vertical.stl): 10 x 10 mm, 4 mm holes every 10 mm ----
POST = 10.0
POST_FIT = 0.4
HOLE_D = 4.2          # bolt/pin through the post holes (M3 bolt or 4 mm pin)
SLEEVE_WALL = 2.5
SLEEVE_DEPTH = 22.0   # covers the first two post holes (5 mm and 15 mm from the end)
CAP = 3.0

WALL = 2.5            # cradle side walls
BACK = 2.0            # cradle back plate
FRONT = 1.5           # cradle front lip thickness
STOP = 2.0            # cradle bottom stop


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1-x0, y1-y0, z1-z0]).translate([x0, y0, z0])


def build():
    w, h, t = PCB_W+FIT, PCB_H+FIT, PCB_T+FIT
    W, D, H = w+2*WALL, BACK+BACK_CLEAR+t+FRONT, h+STOP
    y_slot0 = BACK+BACK_CLEAR
    # Cradle in local coordinates: x across, y toward the scene (lens side), z up; top is open for sliding in.
    cradle = box(-W/2, 0, 0, W/2, D, H)
    cradle -= box(-w/2+LIP, BACK, STOP, w/2-LIP, y_slot0+.01, H+1)        # room for back-side parts
    cradle -= box(-w/2, y_slot0, STOP, w/2, y_slot0+t, H+1)                 # board slot
    cradle -= box(-w/2+LIP, y_slot0+t-.01, STOP+LIP, w/2-LIP, D+1, H+1)     # front window (lens/view)
    stop_slab = box(-W/2, 0, 0, W/2, D, STOP)

    tilt = lambda m: m.rotate([-TILT_DEG, 0, 0])
    cradle, stop_slab = tilt(cradle), tilt(stop_slab)

    # Sleeve over the post top: post axis = z, post holes run along x.
    inner, outer = POST+POST_FIT, POST+POST_FIT+2*SLEEVE_WALL
    sleeve = box(-outer/2, -outer/2, -SLEEVE_DEPTH, outer/2, outer/2, CAP)
    sleeve -= box(-inner/2, -inner/2, -SLEEVE_DEPTH-1, inner/2, inner/2, 0)
    for z in (-5, -15):
        sleeve -= Manifold.cylinder(outer+2, HOLE_D/2, circular_segments=48).rotate([0, 90, 0]).translate([-outer/2-1, 0, z])

    # Place the cradle above the sleeve, centred over the post, then join with a solid neck.
    lift = 4.0
    b = stop_slab.bounding_box()
    shift = [0, -(b[1]+b[4])/2, CAP+lift-b[2]]
    cradle, stop_slab = cradle.translate(shift), stop_slab.translate(shift)
    cap_slab = box(-outer/2, -outer/2, 0, outer/2, outer/2, CAP)
    neck = Manifold.batch_hull([cap_slab, stop_slab])
    part = sleeve + neck + cradle
    # Ribbon channel: through the bottom stop, out the back of the neck.
    ribbon = box(-RIBBON_W/2, -30, -12, RIBBON_W/2, y_slot0+t, STOP+.01)
    part -= tilt(ribbon).translate(shift)
    return part


def write_stl(m, path):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    v = v - [0, 0, v[:, 2].min()]          # sit on the bed (sleeve opening down)
    tri = v[f]
    n = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True)+1e-12
    with open(path, 'wb') as fh:
        fh.write(b'METALSWEEP camera-slot-mount'.ljust(80, b' '))
        fh.write(struct.pack('<I', len(f)))
        for nn, t in zip(n, tri):
            fh.write(struct.pack('<12fH', *nn, *t.ravel(), 0))
    return v.min(0), v.max(0), len(f)


if __name__ == '__main__':
    part = build()
    out = Path(__file__).with_name('camera-slot-mount.stl')
    lo, hi, n = write_stl(part, out)
    print(f'{out.name}: {n} triangles, size {np.round(hi-lo, 1).tolist()} mm, volume {part.volume():.0f} mm3, genus {part.genus()}')
