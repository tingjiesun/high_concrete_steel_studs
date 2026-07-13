from abaqus import *
from abaqusConstants import *

# Unit: mm, MPa
model_name = 'HSS_MODEL_s_19'

# L angle
LEN_Z = 650.0
B_X = 130.0
B_Y = 130.0
T_X = 10.0
T_Y = 10.0

# Names
beam_part_name = 'L_Angle_130x130x10_Z650'
merged_part_name = 'L_Angle_With_2_Studs'
mat_name = 'Steel'
sec_name = 'Steel_Section_L_Angle_Studs'

model = mdb.models[model_name]
a = model.rootAssembly
a.DatumCsysByDefault(CARTESIAN)

# Clean old generated instances
for inst_name in (
    'L_Angle_Base_Instance',
    'L_Angle_With_2_Studs-1',
    'Stud_1_D26_L6',
    'Stud_1_D19_L64',
    'Stud_1_D32_L10',
    'Stud_2_D26_L6',
    'Stud_2_D19_L64',
    'Stud_2_D32_L10',
):
    if inst_name in a.instances.keys():
        del a.instances[inst_name]

# Clean old generated parts
for part_name in (
    beam_part_name,
    merged_part_name,
    'Stud_D26_L6',
    'Stud_D19_L64',
    'Stud_D32_L10',
):
    if part_name in model.parts.keys():
        del model.parts[part_name]

if sec_name in model.sections.keys():
    del model.sections[sec_name]

# Material and section
if mat_name not in model.materials.keys():
    mat = model.Material(name=mat_name)
    mat.Elastic(table=((206000.0, 0.30), ))
    mat.Density(table=((7.85e-9, ), ))

model.HomogeneousSolidSection(
    name=sec_name,
    material=mat_name,
    thickness=None
)

# Create L angle beam
sketch_name = 'L_Profile_XY_130x130x10'
s = model.ConstrainedSketch(name=sketch_name, sheetSize=500.0)

p1 = (0.0, 0.0)
p2 = (B_X, 0.0)
p3 = (B_X, T_Y)
p4 = (T_X, T_Y)
p5 = (T_X, B_Y)
p6 = (0.0, B_Y)

s.Line(point1=p1, point2=p2)
s.Line(point1=p2, point2=p3)
s.Line(point1=p3, point2=p4)
s.Line(point1=p4, point2=p5)
s.Line(point1=p5, point2=p6)
s.Line(point1=p6, point2=p1)

beam_part = model.Part(
    name=beam_part_name,
    dimensionality=THREE_D,
    type=DEFORMABLE_BODY
)

beam_part.BaseSolidExtrude(sketch=s, depth=LEN_Z)
del model.sketches[sketch_name]

beam_part.Set(cells=beam_part.cells[:], name='ALL_CELLS')
beam_part.SectionAssignment(
    region=beam_part.sets['ALL_CELLS'],
    sectionName=sec_name
)

a.Instance(
    name='L_Angle_Base_Instance',
    part=beam_part,
    dependent=ON
)

# Stud reference point:
# On Y-min XZ face, z max and x min point = (0, 0, 650)
REF_X = 0.0
REF_Y = 0.0
REF_Z = LEN_Z

STUD_X = REF_X + 40.0
STUD1_Z = REF_Z - 200.0
STUD2_Z = STUD1_Z - 250.0

# Studs extend outward from Y-min face, so direction is -Y
OUTWARD_SIGN = -1.0

stud_segments = (
    (26.0, 6.0),
    (19.0, 64.0),
    (32.0, 10.0),
)

def create_cylinder_part(part_name, diameter, length):
    radius = diameter / 2.0
    sketch_name = part_name + '_Sketch'

    s = model.ConstrainedSketch(name=sketch_name, sheetSize=100.0)
    s.CircleByCenterPerimeter(center=(0.0, 0.0), point1=(radius, 0.0))

    p = model.Part(
        name=part_name,
        dimensionality=THREE_D,
        type=DEFORMABLE_BODY
    )

    p.BaseSolidExtrude(sketch=s, depth=length)
    del model.sketches[sketch_name]

    p.Set(cells=p.cells[:], name='ALL_CELLS')
    p.SectionAssignment(
        region=p.sets['ALL_CELLS'],
        sectionName=sec_name
    )

    return p

stud_part_map = {}

for diameter, length in stud_segments:
    part_name = 'Stud_D%d_L%d' % (int(diameter), int(length))
    stud_part_map[(diameter, length)] = create_cylinder_part(
        part_name,
        diameter,
        length
    )

def place_stud(stud_id, center_x, surface_y, center_z):
    created_instances = []
    accumulated_length = 0.0

    for diameter, length in stud_segments:
        part = stud_part_map[(diameter, length)]
        inst_name = 'Stud_%d_D%d_L%d' % (
            stud_id,
            int(diameter),
            int(length)
        )

        a.Instance(
            name=inst_name,
            part=part,
            dependent=ON
        )

        # Cylinder is created along local Z.
        # Rotate local Z to global -Y.
        a.rotate(
            instanceList=(inst_name, ),
            axisPoint=(0.0, 0.0, 0.0),
            axisDirection=(1.0, 0.0, 0.0),
            angle=90.0
        )

        start_y = surface_y + OUTWARD_SIGN * accumulated_length

        a.translate(
            instanceList=(inst_name, ),
            vector=(center_x, start_y, center_z)
        )

        created_instances.append(a.instances[inst_name])
        accumulated_length += length

    return created_instances

stud_instances = []
stud_instances += place_stud(1, STUD_X, REF_Y, STUD1_Z)
stud_instances += place_stud(2, STUD_X, REF_Y, STUD2_Z)

# Boolean merge steel beam and studs into one new part
merge_instances = [a.instances['L_Angle_Base_Instance']] + stud_instances

a.InstanceFromBooleanMerge(
    name=merged_part_name,
    instances=tuple(merge_instances),
    keepIntersections=ON,
    originalInstances=SUPPRESS,
    domain=GEOMETRY
)

merged_part = model.parts[merged_part_name]

if 'ALL_CELLS' not in merged_part.sets.keys():
    merged_part.Set(cells=merged_part.cells[:], name='ALL_CELLS')

merged_part.SectionAssignment(
    region=merged_part.sets['ALL_CELLS'],
    sectionName=sec_name
)

# Delete temporary cylinder parts
for part_name in ('Stud_D26_L6', 'Stud_D19_L64', 'Stud_D32_L10'):
    if part_name in model.parts.keys():
        del model.parts[part_name]

# Remove generated assembly instance; keep only the final part for later assembly
if 'L_Angle_With_2_Studs-1' in a.instances.keys():
    del a.instances['L_Angle_With_2_Studs-1']

mdb.save()

# ============================================================
# Appended contact surface: two studs' cylindrical sidewalls only
# ============================================================

import math

_STUD_SURFACE_NAME = 'shuanding_surface'
_STUD_FACE_SET_NAME = 'Set-shuanding_surface'
_STUD_SAMPLE_ANGLES = (45.0, 135.0, 225.0, 315.0)


def _surface_indices_to_mask(indices):
    indices = sorted(list(set(indices)))
    if len(indices) == 0:
        raise RuntimeError('No faces were selected for %s.' % _STUD_SURFACE_NAME)

    n_words = indices[-1] // 32 + 1
    words = [0] * n_words
    for index in indices:
        words[index // 32] = words[index // 32] | (1 << (index % 32))

    return '[#' + ' #'.join(['%x' % word for word in words]) + ' ]'


def _append_nearest_face_index(part, point, description):
    closest = part.faces.getClosest(
        coordinates=(point,),
        searchTolerance=1.0e-4,
    )
    if 0 not in closest:
        raise RuntimeError('Cannot locate %s at %s.' % (description, point))

    face, closest_point = closest[0]
    distance2 = (
        (closest_point[0] - point[0]) ** 2 +
        (closest_point[1] - point[1]) ** 2 +
        (closest_point[2] - point[2]) ** 2
    )
    if distance2 > 1.0e-8:
        raise RuntimeError('%s is not on the intended cylindrical sidewall.' % description)

    face_index = face.index
    if callable(face_index):
        face_index = face_index()
    return int(face_index)


if _STUD_SURFACE_NAME in merged_part.surfaces.keys():
    del merged_part.surfaces[_STUD_SURFACE_NAME]
if _STUD_FACE_SET_NAME in merged_part.sets.keys():
    del merged_part.sets[_STUD_FACE_SET_NAME]

_stud_wall_indices = []
_stud_surface_segments = (
    ('collar', 26.0 / 2.0, -6.0,   0.0),
    ('shank',  19.0 / 2.0, -70.0, -6.0),
    ('head',   32.0 / 2.0, -80.0, -70.0),
)

for _stud_id, _stud_z in enumerate((STUD1_Z, STUD2_Z), start=1):
    for _segment_name, _radius, _y_min, _y_max in _stud_surface_segments:
        _y_mid = 0.5 * (_y_min + _y_max)
        for _angle_deg in _STUD_SAMPLE_ANGLES:
            _angle = math.radians(_angle_deg)
            _point = (
                STUD_X + _radius * math.cos(_angle),
                _y_mid,
                _stud_z + _radius * math.sin(_angle),
            )
            _index = _append_nearest_face_index(
                merged_part,
                _point,
                'stud %d %s sidewall' % (_stud_id, _segment_name),
            )
            if _index not in _stud_wall_indices:
                _stud_wall_indices.append(_index)

_stud_wall_faces = merged_part.faces.getSequenceFromMask(
    mask=(_surface_indices_to_mask(_stud_wall_indices),)
)
merged_part.Set(name=_STUD_FACE_SET_NAME, faces=_stud_wall_faces)
merged_part.Surface(name=_STUD_SURFACE_NAME, side1Faces=_stud_wall_faces)

print('Created %s with %d cylindrical stud-sidewall faces.' % (
    _STUD_SURFACE_NAME, len(_stud_wall_faces)
))

mdb.save()
