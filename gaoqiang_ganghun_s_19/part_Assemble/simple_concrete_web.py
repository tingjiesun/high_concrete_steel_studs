# -*- coding: utf-8 -*-
# Build concrete plate part.
from abaqus import mdb
from abaqusConstants import *
import regionToolset


# ============================================================
# Model
# ============================================================
MODEL_NAME = 'HSS_MODEL_s_19'
FINAL_PART_NAME = 'ConcretePlate_Final'
BASE_PART_NAME = 'ConcretePlate_Base'

if MODEL_NAME in mdb.models.keys():
    model = mdb.models[MODEL_NAME]
else:
    model = mdb.Model(name=MODEL_NAME)

assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)


# ============================================================
# Concrete plate coordinate range
# Rebar cage:
# x: 0 ~ 270
# y: 0 ~ 110
# z: 0 ~ 550
#
# Concrete plate:
# x: 0 ~ 300
# y: -20 ~ 130
# z: -35 ~ 615
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


# ============================================================
# Hole location on x-z face
# Reference point: right upper point
# Hole point 1: left 40, down 100
# Hole point 2: from hole point 1, down 250
# ============================================================
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

# From outer surface to inner direction:
# diameter, length
hole_segments = (
    (26.4, 6.0),
    (19.4, 64.0),
    (32.4, 10.0),
)

# True: cut from y = -20 toward +Y
# False: cut from y = 130 toward -Y
CUT_FROM_Y_MIN_FACE = True


# ============================================================
# Clean old generated objects if rerun
# ============================================================
for feature_name in list(assembly.features.keys()):
    if (feature_name.startswith(BASE_PART_NAME) or
            feature_name.startswith(FINAL_PART_NAME) or
            feature_name.startswith('HoleCutter_')):
        del assembly.features[feature_name]

for part_name in list(model.parts.keys()):
    if (part_name.startswith(BASE_PART_NAME) or
            part_name.startswith(FINAL_PART_NAME) or
            part_name.startswith('HoleCutter_')):
        del model.parts[part_name]


# ============================================================
# Create base concrete block
# Sketch on x-y plane, extrude along z direction
# ============================================================
base_part = model.Part(
    name=BASE_PART_NAME,
    dimensionality=THREE_D,
    type=DEFORMABLE_BODY,
)

sketch = model.ConstrainedSketch(
    name='ConcretePlate_Profile',
    sheetSize=1000.0,
)

sketch.rectangle(
    point1=(0.0, 0.0),
    point2=(conc_length_x, conc_length_y),
)

base_part.BaseSolidExtrude(
    sketch=sketch,
    depth=conc_length_z,
)

del model.sketches['ConcretePlate_Profile']

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
# Create cylindrical cutter part
# Cylinder is created along local z direction first
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
# Create all cutter instances
# Two hole points, each with three cylindrical cuts
# ============================================================
cutter_instances = []
cutter_part_names = []

for hole_id, (hole_x, hole_z) in enumerate(hole_points, start=1):

    current_depth = 0.0

    for seg_id, (diameter, length) in enumerate(hole_segments, start=1):

        cutter_part_name = 'HoleCutter_%d_%d' % (hole_id, seg_id)
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
# Create the final concrete plate part, then remove the assembly instance.
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
# Only ConcretePlate_Final remains
# ============================================================
if BASE_PART_NAME in model.parts.keys():
    del model.parts[BASE_PART_NAME]

for cutter_part_name in cutter_part_names:
    if cutter_part_name in model.parts.keys():
        del model.parts[cutter_part_name]


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

if final_instance.name in assembly.features.keys():
    del assembly.features[final_instance.name]


print('Final concrete plate created.')
print('Only final part kept: %s' % FINAL_PART_NAME)
print('No final assembly instance was kept.')
print('Concrete size: %.1f x %.1f x %.1f' % (
    conc_length_x, conc_length_y, conc_length_z
))
print('Hole point 1: x = %.1f, z = %.1f' % (hole_1_x, hole_1_z))
print('Hole point 2: x = %.1f, z = %.1f' % (hole_2_x, hole_2_z))
print('Hole segments: D26.4-L6, D19.4-L64, D32.4-L10')
