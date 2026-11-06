"""All-printed camera mount, mm. Custom threads are NOT standard metric hardware."""
from pathlib import Path
import json
import math
import numpy as np
import trimesh
from manifold3d import Manifold as M, Mesh

P = Path(__file__).resolve().parent
HOLE_D = 20.0
PLATE_T = 3.0                     # Provisional, accepted earlier; not measured.
PCB_SIZE = 25.0
PCB_T = 1.6                      # Provisional. Check the bare PCB, not the lens.
PCB_XY_CLEARANCE = 0.3
PCB_Z_CLEARANCE = 0.2
THREAD_RADIAL_CLEARANCE = 0.35
THREAD_AXIAL_CLEARANCE = 0.12
BASE_ROOT, BASE_MAJOR, BASE_PITCH = 14.6, 18.2, 3.2
PIVOT_ROOT, PIVOT_MAJOR, PIVOT_PITCH = 5.8, 7.8, 2.0
FOOT_T, PIVOT_Y = 12.0, 15.0
EAR_T, FORK_GAP, FORK_T = 10.0, 10.8, 6.0
HEAD_AXIS_Y, HEAD_AXIS_Z = 28.0, 20.0
BACK_Z = 3 + PCB_T + PCB_Z_CLEARANCE
SNAP_SHOULDER_Z = BACK_Z + 3 + .15
parts, poses = {}, {}


def box(w, d, h, x=0, y=0, z=0):
    return M.cube((w, d, h)).translate((x-w/2, y-d/2, z))


def cylinder(d, h, x=0, y=0, z=0, segments=72):
    return M.cylinder(h, d/2, circular_segments=segments).translate((x,y,z))


def cylinder_x(d, length, x=0, y=0, z=0):
    return cylinder(d, length).rotate((0,90,0)).translate((x,y,z))


def thread(root_d, major_d, pitch, height, radial=0, axial=0):
    """A clipped helical trapezoidal ridge, unioned with a cylindrical core."""
    root, crest = root_d/2 + radial, major_d/2 + radial
    profile = [(root-.18,-pitch*.34-axial), (crest,-pitch*.10-axial),
               (crest,pitch*.10+axial), (root-.18,pitch*.34+axial)]
    turns = height/pitch + 2
    steps = math.ceil(turns*72)
    vertices, triangles = [], []
    for i in range(steps+1):
        theta = -2*math.pi + i/steps*turns*2*math.pi
        center_z = pitch*theta/(2*math.pi)
        for radius,dz in profile:
            vertices.append((radius*math.cos(theta), radius*math.sin(theta), center_z+dz))
    for i in range(steps):
        for j in range(4):
            a, b = i*4+j, (i+1)*4+j
            c, d = (i+1)*4+(j+1)%4, i*4+(j+1)%4
            triangles.extend([(a,b,c),(a,c,d)])
    triangles.extend([(0,1,2),(0,2,3)])
    end = steps*4
    triangles.extend([(end,end+2,end+1),(end,end+3,end+2)])
    ridge = M(Mesh(np.asarray(vertices,np.float32),np.asarray(triangles,np.uint32)))
    assert ridge.status().name == 'NoError', str(ridge.status())
    clipped = (ridge + cylinder(root_d+2*radial,height)) ^ box(80,80,height)
    return clipped


def knob(diameter, height):
    result = cylinder(diameter,height)
    for angle in range(0,360,60):
        t = math.radians(angle)
        result += cylinder(diameter*.24,height,diameter*.43*math.cos(t),diameter*.43*math.sin(t))
    return result


base_male = thread(BASE_ROOT,BASE_MAJOR,BASE_PITCH,14)
# Female phase is translated back to z=0 after extending the cutter at both ends.
base_female = thread(BASE_ROOT,BASE_MAJOR,BASE_PITCH,FOOT_T+2*BASE_PITCH,
                     THREAD_RADIAL_CLEARANCE,THREAD_AXIAL_CLEARANCE).translate((0,0,-BASE_PITCH))
base_screw = knob(38,6) + base_male.translate((0,0,6))
parts['01_base_clamp_screw_x1'] = base_screw


def tower(height, forward=0):
    pivot_z = FOOT_T + height
    result = cylinder(44,FOOT_T) + box(24,14,FOOT_T,y=PIVOT_Y)
    for x in (-(FORK_GAP+FORK_T)/2,(FORK_GAP+FORK_T)/2):
        leg = box(FORK_T,14,height+1.2)
        leg = leg.transform([[1,0,0,x],[0,1,-forward/height,PIVOT_Y],
                             [0,0,1,FOOT_T-.2]])
        result += leg
        result += cylinder_x(20,FORK_T,x=x-FORK_T/2,y=PIVOT_Y-forward,z=pivot_z)
    result -= base_female
    result -= cylinder_x(8.6,40,x=-20,y=PIVOT_Y-forward,z=pivot_z)
    return result


for h in (60,90,120):
    parts[f'02_mast_{h}mm_choose_one'] = tower(h)
    parts[f'02_mast_{h}mm_forward45_choose_one'] = tower(h,45)


def snap_pin(x=0,y=0,z=3):
    stem_h = SNAP_SHOULDER_Z-z
    pin = cylinder(3.6,stem_h,x,y,z)
    pin += M.cylinder(1.7,2.2,1.4,circular_segments=48).translate((x,y,SNAP_SHOULDER_Z))
    pin -= box(.8,6,12,x=x,y=y,z=z+1)
    return pin


frame = box(42,42,3) - box(22,22,5,z=-1)
frame += box(EAR_T,18,32,y=HEAD_AXIS_Y)
frame -= cylinder_x(8.6,18,x=-9,y=HEAD_AXIS_Y,z=HEAD_AXIS_Z)
for x in (-17.5,17.5):
    for y in (-17.5,17.5):
        frame += snap_pin(x,y)
# Short guides constrain both PCB axes, leaving the middle of each edge open.
guide_x = PCB_SIZE/2 + PCB_XY_CLEARANCE + .8
for x in (-guide_x,guide_x):
    for y in (-9,9):
        frame += box(1.6,4,min(1.4,PCB_T),x=x,y=y,z=3)
for y in (-guide_x,guide_x):
    for x in (-9,9):
        frame += box(4,1.6,min(1.4,PCB_T),x=x,y=y,z=3)
retainer = box(42,42,3) - box(22,22,5,z=-1)
retainer -= box(EAR_T+.8,6,5,y=21,z=-1)
retainer -= box(29,14,5,y=-15,z=-1)  # Open edge for the back-side FFC connector.
for x in (-17.5,17.5):
    for y in (-17.5,17.5):
        retainer -= cylinder(3.95,5,x,y,-1)
parts['03_camera25_pitch_frame_x1'] = frame
parts['04_camera_back_retainer_x1'] = retainer

pivot_male = thread(PIVOT_ROOT,PIVOT_MAJOR,PIVOT_PITCH,36)
pivot_screw = knob(22,6) + pivot_male.translate((0,0,6))
pivot_cutter = thread(PIVOT_ROOT,PIVOT_MAJOR,PIVOT_PITCH,14,
                     THREAD_RADIAL_CLEARANCE,THREAD_AXIAL_CLEARANCE).translate((0,0,-2))
pivot_nut = knob(22,10) - pivot_cutter
parts['05_pitch_thumb_screw_x1'] = pivot_screw
parts['06_pitch_thumb_nut_x1'] = pivot_nut
# Optional shim for a thinner PCB: use only after measuring actual PCB/gap.
parts['07_camera_edge_shim_0p4_optional'] = box(25,25,.4) - box(22,22,2,z=-.5)

# Fit tests should be printed before a full mast and camera frame.
parts['00a_base_thread_screw_coupon'] = knob(26,4) + thread(BASE_ROOT,BASE_MAJOR,BASE_PITCH,10).translate((0,0,4))
parts['00a_base_thread_nut_coupon'] = cylinder(28,8) - base_female
parts['00b_pitch_thread_screw_coupon'] = knob(18,4) + thread(PIVOT_ROOT,PIVOT_MAJOR,PIVOT_PITCH,16).translate((0,0,4))
parts['00b_pitch_thread_nut_coupon'] = cylinder(19,8) - pivot_cutter
parts['00c_snap_post_coupon'] = box(12,12,3) + snap_pin()
parts['00c_snap_retainer_coupon'] = box(12,12,3) - cylinder(3.95,5,z=-1)

# Export all parts with their actual print orientation and minimum Z at zero.
# The camera frame is printed front-face-down. Ear needs slicer support.
report = {}
for name, solid in parts.items():
    solid = solid.simplify(.001)
    parts[name] = solid
    assert solid.status().name == 'NoError', (name,solid.status())
    assert len(solid.decompose()) == 1, name
    raw = solid.to_mesh64()
    mesh = trimesh.Trimesh(np.asarray(raw.vert_properties)[:,:3],np.asarray(raw.tri_verts),process=False)
    mesh.vertices = np.round(mesh.vertices,4)
    mesh.merge_vertices(digits_vertex=4)
    mesh.update_faces(mesh.nondegenerate_faces() & mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0, name
    mesh.apply_translation(-mesh.bounds[0])
    mesh.export(P/(name+'.stl'))
    report[name] = dict(bounds_mm=mesh.extents.round(3).tolist(),
                       volume_cm3=round(mesh.volume/1000,3),watertight=True,one_solid=True)


def camera_pose(solid, angle, height=90, forward=0):
    pivot_z = FOOT_T+height
    pivot_y = PIVOT_Y-forward
    posed = solid.rotate((-90,0,0)).translate((0,pivot_y-HEAD_AXIS_Z,pivot_z+HEAD_AXIS_Y))
    return posed.translate((0,-pivot_y,-pivot_z)).rotate((angle,0,0)).translate((0,pivot_y,pivot_z))


collision = {}
hardware_collision = {}
for height in (60,90,120):
    for forward in (0,45):
        suffix = '_forward45' if forward else ''
        mast = parts[f'02_mast_{height}mm{suffix}_choose_one']
        outer = FORK_GAP/2+FORK_T
        screw = pivot_screw.rotate((0,90,0)).translate((-outer-6,PIVOT_Y-forward,FOOT_T+height))
        nut = pivot_nut.rotate((0,0,2*outer/PIVOT_PITCH*360)).rotate((0,90,0)).translate((outer,PIVOT_Y-forward,FOOT_T+height))
        for angle in range(25,56,5):
            head = camera_pose(frame,angle,height,forward)
            cover = camera_pose(retainer.translate((0,0,BACK_Z)),angle,height,forward)
            volume = (mast ^ (head+cover)).volume()
            assert volume < 1e-4, ('head/mast',height,forward,angle,volume)
            collision[f'{height}mm_f{forward}_{angle}deg'] = round(volume,6)
            checks = dict(head_bolt=(head^screw).volume(),head_nut=(head^nut).volume(),
                          mast_bolt=(mast^screw).volume(),mast_nut=(mast^nut).volume(),
                          bolt_nut=(screw^nut).volume())
            assert all(abs(v)<1e-4 for v in checks.values()), checks
            hardware_collision[f'{height}mm_f{forward}_{angle}deg'] = {k:round(v,6) for k,v in checks.items()}
# Check theoretical helical fit at selected thread engagements.
thread_checks = {}
for depth in (2,3,4,5):
    # A full-pitch translation leaves the female thread phase unchanged.
    shift = -float(depth)
    turned = base_male.rotate((0,0,shift/BASE_PITCH*360)).translate((0,0,shift))
    volume = (turned ^ parts['02_mast_90mm_choose_one']).volume()
    assert volume < 1e-4, ('base thread',depth,volume)
    thread_checks[f'base_plate_{depth}mm'] = round(volume,6)
for distance in (23,24,25):
    screw = pivot_male.translate((0,0,-distance))
    nut = pivot_nut.rotate((0,0,distance/PIVOT_PITCH*360))
    volume = (screw ^ nut).volume()
    assert volume < 1e-4, ('pitch thread',distance,volume)
    thread_checks[f'pitch_engagement_offset_{distance}'] = round(volume,6)
# Plate clearance and nominal PCB pocket are geometric checks, not physical fit.
plate = box(100,100,PLATE_T,z=-PLATE_T)-cylinder(HOLE_D,PLATE_T+2,z=-PLATE_T-1)
base_in_place = base_screw.rotate((0,0,-PLATE_T/BASE_PITCH*360)).translate((0,0,-PLATE_T-6))
assert (plate ^ base_in_place).volume()<1e-4
assert (frame ^ retainer.translate((0,0,BACK_Z))).volume()<1e-4
pcb = box(PCB_SIZE,PCB_SIZE,PCB_T,z=3)
assert ((frame+retainer.translate((0,0,BACK_Z)))^pcb).volume()<1e-4
connector_proxy = box(25,6,3,y=-11.8,z=3+PCB_T)
assert ((frame+retainer.translate((0,0,BACK_Z)))^connector_proxy).volume()<1e-4
parameters = dict(hole_diameter=HOLE_D,assumed_plate_thickness=PLATE_T,pcb_size=PCB_SIZE,
                  assumed_pcb_thickness=PCB_T,mast_pivot_above_foot_mm=[60,90,120],
                  forward_options_mm=[0,45],
                  assumed_connector_envelope_mm=[25,6,3],
                  radial_thread_clearance=THREAD_RADIAL_CLEARANCE,
                  custom_base_thread=[BASE_MAJOR,BASE_PITCH],custom_pivot_thread=[PIVOT_MAJOR,PIVOT_PITCH])
(P/'validation.json').write_text(json.dumps(dict(parameters=parameters,parts=report,
    sampled_head_mast_intersections_mm3=collision,thread_fit_intersections_mm3=thread_checks,
    sampled_printed_hardware_intersections_mm3=hardware_collision,
    note='No actual print, slicer, PCB component, ribbon, chassis, retention-force, creep or vibration test.'),indent=2))
print('PASS',len(parts),'solids; sampled thread fit, plate and head/mast clearances.')
