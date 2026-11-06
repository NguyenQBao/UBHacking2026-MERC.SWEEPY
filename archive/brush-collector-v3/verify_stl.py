"""Independent binary STL validation; Python standard library only."""
from pathlib import Path
from collections import Counter
import struct,json,math
out={}
for path in sorted(Path(__file__).parent.glob('*.stl')):
    data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0]
    assert len(data)==84+50*n,path.name
    edges=Counter();directed=Counter();vertices=set();volume=0
    for i in range(n):
        a=struct.unpack_from('<12fH',data,84+50*i)
        vs=[tuple(round(v,5) for v in a[j:j+3]) for j in (3,6,9)]
        assert all(math.isfinite(v) for p in vs for v in p)
        assert len(set(vs))==3
        p,q,r=vs
        u=[q[k]-p[k] for k in range(3)];v=[r[k]-p[k] for k in range(3)]
        cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        assert sum(c*c for c in cross)>1e-14
        volume+=sum(p[k]*cross[k] for k in range(3))/6
        for j in range(3):
            e=(vs[j],vs[(j+1)%3]);directed[e]+=1;edges[tuple(sorted(e))]+=1
        vertices.update(vs)
    assert all(n==2 for n in edges.values()),path.name
    assert all(directed[(a,b)]==directed[(b,a)]==1 for a,b in edges),path.name
    assert volume>0 and abs(min(p[2] for p in vertices))<1e-5,path.name
    out[path.name]={'triangles':n,'closed_two_faces_per_edge':True,'opposite_edge_winding':True,'nondegenerate':True,'z_min_mm':0,'volume_cm3':round(volume/1000,3)}
Path(__file__).with_name('independent_stl_check.json').write_text(json.dumps(out,indent=2))
print('PASS:',len(out),'STL files; edge topology, winding, triangle area, positive volume, Z=0')
