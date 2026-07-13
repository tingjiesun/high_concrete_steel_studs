# -*- coding: utf-8 -*-
from abaqus import mdb
from abaqusConstants import *
import regionToolset

# ============================================================
# Model and part names
# ============================================================

MODEL_NAME = 'HSS_MODEL_s_19'
FINAL_PART_NAME = 'ConcretePlate_Final'
BASE_PART_NAME = 'ConcretePlate_Base_For_Grid'

if MODEL_NAME in mdb.models.keys():
    model = mdb.models[MODEL_NAME]
else:
    model = mdb.Model(name=MODEL_NAME)

assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)

# ============================================================
# Concrete plate geometry, unchanged
# ============================================================

x_min_conc = 0.0
x_max_conc = 300.0

y_min_conc = -20.0
y_max_conc = 130.0

z_min_conc = -35.0
z_max_conc = 615.0

conc_length_x = x_max_conc - x_min_conc
conc_length_y = y_max_conc - y_min_conc
conc_length_z = z_max_conc - z_min_conc

# Hole locations, unchanged
ref_x = x_max_conc
ref_z = z_max_conc

hole_1_x = ref_x - 40.0
hole_1_z = ref_z - 100.0

hole_2_x = hole_1_x
hole_2_z = hole_1_z - 250.0

hole_points = (
    (hole_1_x, hole_1_z),
    (hole_2_x, hole_2_z),
)

# Hole segments, unchanged
hole_segments = (
    (26.4, 6.0),
    (19.4, 64.0),
    (32.4, 10.0),
)

CUT_FROM_Y_MIN_FACE = True

# Stepped hole y positions
Y0 = y_min_conc
Y1 = y_min_conc + 6.0
Y2 = Y1 + 64.0
Y3 = Y2 + 10.0

# Hole radii
R26 = 26.4 / 2.0
R19 = 19.4 / 2.0
R32 = 32.4 / 2.0
R_MAX = R32

# O-grid-like partition radii.  Keep the first ring outside the D32.4 hole.
O_GRID_R1 = 20.0
O_GRID_R2 = 30.0
O_GRID_R3 = 40.0

# ============================================================
# Clean old generated objects
# ============================================================

for feature_name in list(assembly.features.keys()):
    if (feature_name.startswith(FINAL_PART_NAME) or
            feature_name.startswith(BASE_PART_NAME) or
            feature_name.startswith('ConcretePlate_HoleCutter_')):
        del assembly.features[feature_name]

for part_name in list(model.parts.keys()):
    if (part_name == FINAL_PART_NAME or
            part_name == BASE_PART_NAME or
            part_name.startswith('ConcretePlate_HoleCutter_')):
        del model.parts[part_name]

for sketch_name in list(model.sketches.keys()):
    if sketch_name.startswith('ConcretePlate_'):
        del model.sketches[sketch_name]

# ============================================================
# Create base concrete plate
# ============================================================

base_part = model.Part(
    name=BASE_PART_NAME,
    dimensionality=THREE_D,
    type=DEFORMABLE_BODY,
)

base_sketch = model.ConstrainedSketch(
    name='ConcretePlate_Base_Profile',
    sheetSize=1000.0,
)

base_sketch.rectangle(
    point1=(0.0, 0.0),
    point2=(conc_length_x, conc_length_y),
)

base_part.BaseSolidExtrude(
    sketch=base_sketch,
    depth=conc_length_z,
)

del model.sketches['ConcretePlate_Base_Profile']

base_instance_name = BASE_PART_NAME + '-1'

assembly.Instance(
    name=base_instance_name,
    part=base_part,
    dependent=ON,
)

assembly.translate(
    instanceList=(base_instance_name,),
    vector=(x_min_conc, y_min_conc, z_min_conc),
)

# ============================================================
# Create cylindrical cutter
# ============================================================

def create_cylinder_cutter(part_name, diameter, length):
    radius = diameter / 2.0

    cutter_part = model.Part(
        name=part_name,
        dimensionality=THREE_D,
        type=DEFORMABLE_BODY,
    )

    cutter_sketch = model.ConstrainedSketch(
        name=part_name + '_Profile',
        sheetSize=100.0,
    )

    cutter_sketch.CircleByCenterPerimeter(
        center=(0.0, 0.0),
        point1=(radius, 0.0),
    )

    cutter_part.BaseSolidExtrude(
        sketch=cutter_sketch,
        depth=length,
    )

    del model.sketches[part_name + '_Profile']
    return cutter_part

# ============================================================
# Create hole cutter instances
# ============================================================

cutter_instances = []
cutter_part_names = []

for hole_id, (hole_x, hole_z) in enumerate(hole_points, start=1):

    current_depth = 0.0

    for seg_id, (diameter, length) in enumerate(hole_segments, start=1):

        cutter_part_name = 'ConcretePlate_HoleCutter_%d_%d' % (hole_id, seg_id)
        cutter_inst_name = cutter_part_name + '-1'

        cutter_part = create_cylinder_cutter(
            part_name=cutter_part_name,
            diameter=diameter,
            length=length,
        )

        cutter_part_names.append(cutter_part_name)

        assembly.Instance(
            name=cutter_inst_name,
            part=cutter_part,
            dependent=ON,
        )

        if CUT_FROM_Y_MIN_FACE:
            assembly.rotate(
                instanceList=(cutter_inst_name,),
                axisPoint=(0.0, 0.0, 0.0),
                axisDirection=(1.0, 0.0, 0.0),
                angle=-90.0,
            )
            y_start = y_min_conc + current_depth
        else:
            assembly.rotate(
                instanceList=(cutter_inst_name,),
                axisPoint=(0.0, 0.0, 0.0),
                axisDirection=(1.0, 0.0, 0.0),
                angle=90.0,
            )
            y_start = y_max_conc - current_depth

        assembly.translate(
            instanceList=(cutter_inst_name,),
            vector=(hole_x, y_start, hole_z),
        )

        cutter_instances.append(assembly.instances[cutter_inst_name])
        current_depth += length

# ============================================================
# Boolean cut
# ============================================================

final_instance = assembly.InstanceFromBooleanCut(
    name=FINAL_PART_NAME,
    instanceToBeCut=assembly.instances[base_instance_name],
    cuttingInstances=tuple(cutter_instances),
    originalInstances=DELETE,
)

final_part = model.parts[FINAL_PART_NAME]

# ============================================================
# Delete temporary parts
# ============================================================

if BASE_PART_NAME in model.parts.keys():
    del model.parts[BASE_PART_NAME]

for cutter_part_name in cutter_part_names:
    if cutter_part_name in model.parts.keys():
        del model.parts[cutter_part_name]

# ============================================================
# Partition helpers
# ============================================================

def safe_partition_by_datum(principal_plane, offset):
    try:
        d = final_part.DatumPlaneByPrincipalPlane(
            principalPlane=principal_plane,
            offset=offset,
        )
        final_part.PartitionCellByDatumPlane(
            datumPlane=final_part.datums[d.id],
            cells=final_part.cells[:],
        )
    except:
        pass


def safe_partition_circular_thru_all_from_ymax():
    # Use the undamaged Y_MAX face as sketch plane.
    # This avoids invalid sketch plane errors caused by the opened Y_MIN face.
    try:
        sketch_plane = final_part.faces.findAt(
            ((0.5 * (x_min_conc + x_max_conc),
              y_max_conc,
              0.5 * (z_min_conc + z_max_conc)),)
        )
    except:
        faces = final_part.faces.getByBoundingBox(
            xMin=x_min_conc - 1.0,
            xMax=x_max_conc + 1.0,
            yMin=y_max_conc - 1.0e-3,
            yMax=y_max_conc + 1.0e-3,
            zMin=z_min_conc - 1.0,
            zMax=z_max_conc + 1.0,
        )
        if len(faces) == 0:
            print('Warning: Y_MAX sketch plane not found. Circular partition skipped.')
            return
        sketch_plane = faces[0]

    try:
        sketch_up_edge = final_part.edges.findAt(
            ((x_min_conc,
              y_max_conc,
              0.5 * (z_min_conc + z_max_conc)),)
        )
    except:
        try:
            sketch_up_edge = final_part.edges.findAt(
                ((0.5 * (x_min_conc + x_max_conc),
                  y_max_conc,
                  z_max_conc),)
            )
        except:
            print('Warning: sketch up edge not found. Circular partition skipped.')
            return

    try:
        transform = final_part.MakeSketchTransform(
            sketchPlane=sketch_plane,
            sketchUpEdge=sketch_up_edge,
            sketchPlaneSide=SIDE1,
            origin=(0.0, y_max_conc, 0.0),
        )
    except:
        print('Warning: MakeSketchTransform failed. Circular partition skipped.')
        return

    sketch_name = 'ConcretePlate_OGrid_Circular_Partition'

    if sketch_name in model.sketches.keys():
        del model.sketches[sketch_name]

    s = model.ConstrainedSketch(
        name=sketch_name,
        sheetSize=1000.0,
        gridSpacing=10.0,
        transform=transform,
    )

    final_part.projectReferencesOntoSketch(
        sketch=s,
        filter=COPLANAR_EDGES,
    )

    for hole_x, hole_z in hole_points:
        for r in (O_GRID_R1, O_GRID_R2, O_GRID_R3):
            s.CircleByCenterPerimeter(
                center=(hole_x, hole_z),
                point1=(hole_x + r, hole_z),
            )

    try:
        final_part.PartitionCellBySketchThruAll(
            cells=final_part.cells[:],
            sketchPlane=sketch_plane,
            sketchUpEdge=sketch_up_edge,
            sketchPlaneSide=SIDE1,
            sketch=s,
        )
    except:
        try:
            final_part.PartitionCellBySketchThruAll(
                cells=final_part.cells[:],
                sketchPlane=sketch_plane,
                sketchUpEdge=sketch_up_edge,
                sketchPlaneSide=SIDE2,
                sketch=s,
            )
        except:
            print('Warning: circular O-grid partition failed and was skipped.')

    if sketch_name in model.sketches.keys():
        del model.sketches[sketch_name]

# ============================================================
# Partition by stepped hole depth
# ============================================================

for y in (Y1, Y2, Y3):
    safe_partition_by_datum(XZPLANE, y)

# ============================================================
# Regular plane partitions around holes
# ============================================================

for hole_x, hole_z in hole_points:

    for x in (
        hole_x - O_GRID_R3,
        hole_x - O_GRID_R2,
        hole_x - O_GRID_R1,
        hole_x,
        hole_x + O_GRID_R1,
        hole_x + O_GRID_R2,
        hole_x + O_GRID_R3,
    ):
        if x_min_conc < x < x_max_conc:
            safe_partition_by_datum(YZPLANE, x)

    for z in (
        hole_z - O_GRID_R3,
        hole_z - O_GRID_R2,
        hole_z - O_GRID_R1,
        hole_z,
        hole_z + O_GRID_R1,
        hole_z + O_GRID_R2,
        hole_z + O_GRID_R3,
    ):
        if z_min_conc < z < z_max_conc:
            safe_partition_by_datum(XYPLANE, z)

# ============================================================
# Circular O-grid-like partition surfaces
# ============================================================

safe_partition_circular_thru_all_from_ymax()

# ============================================================
# Coarse regular partitions
# ============================================================

for x in (60.0, 120.0, 180.0, 240.0):
    safe_partition_by_datum(YZPLANE, x)

COARSE_Y_PARTITIONS = (20.0, 60.0, 100.0)

for y in COARSE_Y_PARTITIONS:
    safe_partition_by_datum(XZPLANE, y)

for z in (
    65.0,
    165.0,
    265.0,
    365.0,
    465.0,
    515.0,
):
    safe_partition_by_datum(XYPLANE, z)

# ============================================================
# Material and section
# ============================================================

if 'Concrete' not in model.materials.keys():
    model.Material(name='Concrete')
    model.materials['Concrete'].Elastic(table=((30000.0, 0.2),))

if 'ConcreteSection' not in model.sections.keys():
    model.HomogeneousSolidSection(
        name='ConcreteSection',
        material='Concrete',
        thickness=None,
    )

concrete_region = regionToolset.Region(cells=final_part.cells[:])

final_part.SectionAssignment(
    region=concrete_region,
    sectionName='ConcreteSection',
)

final_part.Set(
    name='ALL_CONCRETE',
    cells=final_part.cells[:],
)

# ============================================================
# Remove final assembly instance; keep only part
# ============================================================

if final_instance.name in assembly.features.keys():
    del assembly.features[final_instance.name]

# ============================================================
# Report
# ============================================================

print('Final concrete plate created.')
print('Part name: %s' % FINAL_PART_NAME)
print('Concrete size: %.1f x %.1f x %.1f' % (
    conc_length_x,
    conc_length_y,
    conc_length_z,
))
print('Hole point 1: x = %.1f, z = %.1f' % (hole_1_x, hole_1_z))
print('Hole point 2: x = %.1f, z = %.1f' % (hole_2_x, hole_2_z))
print('Hole segments: D26.4-L6, D19.4-L64, D32.4-L10')
print('O-grid partition radii: %.1f, %.1f, %.1f' % (
    O_GRID_R1,
    O_GRID_R2,
    O_GRID_R3,
))
print('New part kept: %s' % FINAL_PART_NAME)

mdb.save()

# ============================================================
# Appended contact surface: stepped hole cylindrical walls only
# ============================================================

import math

_HOLE_SURFACE_NAME = 'shuanding_hole_surface'
_HOLE_FACE_SET_NAME = 'Set-shuanding_hole_surface'
_HOLE_SAMPLE_ANGLES = (45.0, 135.0, 225.0, 315.0)


def _surface_indices_to_mask(indices):
    indices = sorted(list(set(indices)))
    if len(indices) == 0:
        raise RuntimeError('No faces were selected for %s.' % _HOLE_SURFACE_NAME)

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
        raise RuntimeError('%s is not on the intended cylindrical wall.' % description)

    face_index = face.index
    if callable(face_index):
        face_index = face_index()
    return int(face_index)


if _HOLE_SURFACE_NAME in final_part.surfaces.keys():
    del final_part.surfaces[_HOLE_SURFACE_NAME]
if _HOLE_FACE_SET_NAME in final_part.sets.keys():
    del final_part.sets[_HOLE_FACE_SET_NAME]

_hole_wall_indices = []
_hole_surface_segments = (
    ('collar', R26, Y0, Y1),
    ('shank', R19, Y1, Y2),
    ('head', R32, Y2, Y3),
)


def _segment_y_samples(y_min, y_max):
    """Return one sample inside every axial face interval after partitioning."""
    break_points = [y_min]

    for partition_y in COARSE_Y_PARTITIONS:
        if y_min < partition_y < y_max:
            break_points.append(partition_y)

    break_points.append(y_max)
    break_points = sorted(list(set(break_points)))

    return tuple(
        0.5 * (break_points[i] + break_points[i + 1])
        for i in range(len(break_points) - 1)
    )


for _hole_id, (_hole_x, _hole_z) in enumerate(hole_points, start=1):
    for _segment_name, _radius, _y_min, _y_max in _hole_surface_segments:
        for _y_sample in _segment_y_samples(_y_min, _y_max):
            for _angle_deg in _HOLE_SAMPLE_ANGLES:
                _angle = math.radians(_angle_deg)
                _point = (
                    _hole_x + _radius * math.cos(_angle),
                    _y_sample,
                    _hole_z + _radius * math.sin(_angle),
                )
                _index = _append_nearest_face_index(
                    final_part,
                    _point,
                    'hole %d %s wall at y=%.3f'
                    % (_hole_id, _segment_name, _y_sample),
                )
                if _index not in _hole_wall_indices:
                    _hole_wall_indices.append(_index)

_hole_wall_faces = final_part.faces.getSequenceFromMask(
    mask=(_surface_indices_to_mask(_hole_wall_indices),)
)
final_part.Set(name=_HOLE_FACE_SET_NAME, faces=_hole_wall_faces)
final_part.Surface(name=_HOLE_SURFACE_NAME, side1Faces=_hole_wall_faces)

print('Created %s with %d cylindrical hole-wall faces.' % (
    _HOLE_SURFACE_NAME, len(_hole_wall_faces)
))

mdb.save()
