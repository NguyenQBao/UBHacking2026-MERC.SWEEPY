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
PITCH = 42.0                  # spacing between parts along X
SUPPORT = {'support_material': '1', 'support_material_auto': '1',
           'support_material_buildplate_only': '1'}   # only from the bed, never inside the slot


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
    x0 = BED_CENTER[0] - PITCH*(len(files)-1)/2
    for i, f in enumerate(files, 1):
        v, t = read_stl(f)
        v = v - [(v[:, 0].min()+v[:, 0].max())/2, (v[:, 1].min()+v[:, 1].max())/2, v[:, 2].min()]
        vs = ''.join(f'<vertex x="{a:.5f}" y="{b:.5f}" z="{c:.5f}"/>' for a, b, c in v)
        ts = ''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
        objects.append(f'<object id="{i}" type="model"><mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object>')
        x = x0 + PITCH*(i-1)
        items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {x:.3f} {BED_CENTER[1]:.3f} 0" printable="1"/>')
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
    print(f'{out.name}: {len(files)} parts ->', [f.stem for f in files])


if __name__ == '__main__':
    main()
