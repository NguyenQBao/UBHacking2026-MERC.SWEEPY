"""Pack the slot-thickness variants into one PrusaSlicer 3MF plate with per-object supports.

The 3MF holds geometry + per-object settings only (no printer/print profile), so PrusaSlicer
keeps whatever printer/filament/print presets are currently selected.
Run after generate.py has written variants/*.stl:  python make_plate.py
"""
from pathlib import Path
import struct
import zipfile
import numpy as np

HERE = Path(__file__).resolve().parent
BED_CENTER = (125.0, 110.0)   # Prusa CORE One bed 250 x 220 mm
GAP = 12.0                    # clear space between neighbouring parts (room for supports/brim)
# Print lying on the cradle side wall: 30 mm tall instead of 58, 2.4x bed contact, and layers run
# along the neck so the post-to-cradle joint is not split by layer lines. Supports hold the sleeve.
ROT_Y_90 = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)
SUPPORT = {'support_material': '1', 'support_material_auto': '1',
           'support_material_buildplate_only': '1',  # only from the bed, never inside the slot
           'support_material_style': 'organic'}       # tree (organic) supports


def read_stl(path):
    raw = path.read_bytes()
    n = struct.unpack_from('<I', raw, 80)[0]
    tri = np.frombuffer(raw, dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]), count=n, offset=84)
    pts = tri['v'].reshape(-1, 3).astype(float)
    verts, idx = np.unique(np.round(pts, 5), axis=0, return_inverse=True)
    return verts, idx.reshape(-1, 3)


def main():
    files = sorted((HERE/'variants').glob('camera-slot-mount-slot*mm.stl'))
    objects, items, config = [], [], []
    meshes = []
    for f in files:
        v, t = read_stl(f)
        v = v @ ROT_Y_90.T
        v = v - [(v[:, 0].min()+v[:, 0].max())/2, (v[:, 1].min()+v[:, 1].max())/2, v[:, 2].min()]
        meshes.append((f, v, t))
    # One column along Y, each part's real depth + GAP, whole column centred on the bed.
    depths = [np.ptp(v[:, 1]) for _, v, _ in meshes]
    total = sum(depths) + GAP*(len(depths)-1)
    y = BED_CENTER[1] - total/2
    centres = []
    for d in depths:
        centres.append(y + d/2)
        y += d + GAP
    boxes = []
    for i, ((f, v, t), cy) in enumerate(zip(meshes, centres), 1):
        boxes.append((BED_CENTER[0]+v[:, 0].min(), cy+v[:, 1].min(), BED_CENTER[0]+v[:, 0].max(), cy+v[:, 1].max()))
        vs = ''.join(f'<vertex x="{a:.5f}" y="{b:.5f}" z="{c:.5f}"/>' for a, b, c in v)
        ts = ''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
        objects.append(f'<object id="{i}" type="model"><mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {BED_CENTER[0]:.3f} {cy:.3f} 0" printable="1"/>')
        meta = ''.join(f'<metadata type="object" key="{k}" value="{val}"/>' for k, val in SUPPORT.items())
        config.append(f'<object id="{i}" instances_count="1"><metadata type="object" key="name" value="{f.stem}"/>{meta}'
                      f'<volume firstid="0" lastid="{len(t)-1}"><metadata type="volume" key="name" value="{f.stem}"/></volume></object>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources>{"".join(objects)}</resources><build>{"".join(items)}</build></model>')
    out = HERE/'camera-slot-mount-variants.3mf'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model', model)
        z.writestr('Metadata/Slic3r_PE_model.config', '<?xml version="1.0" encoding="utf-8"?>\n<config>'+''.join(config)+'</config>')
    for a, b in zip(boxes, boxes[1:]):
        assert b[1]-a[3] >= GAP-1e-6, 'parts too close'
    assert all(0 < x0 and x1 < 250 and 0 < y0 and y1 < 220 for x0, y0, x1, y1 in boxes), 'off the bed'
    print(f'{out.name}: {len(files)} parts, footprints (x0,y0,x1,y1):')
    for f, b in zip(files, boxes):
        print(f'  {f.stem}: ' + ', '.join(f'{c:.1f}' for c in b))


if __name__ == '__main__':
    main()
