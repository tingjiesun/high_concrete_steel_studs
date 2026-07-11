# -*- coding: mbcs -*-
#装配混凝土板和钢筋笼
from abaqus import mdb
from abaqusConstants import *


# ============================================================
# Model, part, and instance names
# ============================================================
MODEL_NAME = 'HSS_Stud'

CONCRETE_PART_NAME = 'ConcretePlate_Final'
REBAR_PART_NAME = 'RebarCage'

CONCRETE_INSTANCE_NAME = 'ConcretePlate_Final-1'
REBAR_INSTANCE_NAME = 'RebarCage-1'


# ============================================================
# Get model and assembly
# ============================================================
if MODEL_NAME not in mdb.models.keys():
    raise RuntimeError('Model %s does not exist.' % MODEL_NAME)

model = mdb.models[MODEL_NAME]
assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)


# ============================================================
# Check parts
# ============================================================
if CONCRETE_PART_NAME not in model.parts.keys():
    raise RuntimeError('Part %s does not exist.' % CONCRETE_PART_NAME)

if REBAR_PART_NAME not in model.parts.keys():
    raise RuntimeError('Part %s does not exist.' % REBAR_PART_NAME)


# ============================================================
# Delete old instances if they already exist
# ============================================================
if CONCRETE_INSTANCE_NAME in assembly.instances.keys():
    del assembly.features[CONCRETE_INSTANCE_NAME]

if REBAR_INSTANCE_NAME in assembly.instances.keys():
    del assembly.features[REBAR_INSTANCE_NAME]


# ============================================================
# Create concrete plate instance
# ============================================================
assembly.Instance(
    name=CONCRETE_INSTANCE_NAME,
    part=model.parts[CONCRETE_PART_NAME],
    dependent=ON,
)


# ============================================================
# Create rebar cage instance
# ============================================================
assembly.Instance(
    name=REBAR_INSTANCE_NAME,
    part=model.parts[REBAR_PART_NAME],
    dependent=ON,
)


# ============================================================
# Step 1
# Align selected rebar point to selected concrete point
#
# Rebar cage original range:
# x: 0 ~ 270
# y: 0 ~ 110
# z: 0 ~ 550
#
# Selected rebar point:
# x minimum, y maximum, z maximum
# = (0, 110, 550)
#
# Concrete plate range:
# x: 0 ~ 300
# y: -20 ~ 130
# z: -35 ~ 615
#
# Selected concrete point:
# x minimum, y maximum, z maximum
# = (0, 130, 615)
#
# Alignment vector:
# concrete point - rebar point = (0, 20, 65)
# ============================================================
rebar_point = (0.0, 110.0, 550.0)
concrete_point = (0.0, 130.0, 615.0)

align_vector = (
    concrete_point[0] - rebar_point[0],
    concrete_point[1] - rebar_point[1],
    concrete_point[2] - rebar_point[2],
)

assembly.translate(
    instanceList=(REBAR_INSTANCE_NAME,),
    vector=align_vector,
)


# ============================================================
# Step 2
# Move rebar cage 20 in negative y direction
# ============================================================
assembly.translate(
    instanceList=(REBAR_INSTANCE_NAME,),
    vector=(0.0, -20.0, 0.0),
)


# ============================================================
# Step 3
# Move rebar cage 35 in negative z direction
# ============================================================
assembly.translate(
    instanceList=(REBAR_INSTANCE_NAME,),
    vector=(0.0, 0.0, -35.0),
)


# ============================================================
# Step 4
# Move rebar cage 30 in positive x direction
# ============================================================
assembly.translate(
    instanceList=(REBAR_INSTANCE_NAME,),
    vector=(30.0, 0.0, 0.0),
)


# ============================================================
# Regenerate assembly
# ============================================================
assembly.regenerate()


print('Assembly completed successfully.')
print('Concrete part: %s' % CONCRETE_PART_NAME)
print('Rebar part: %s' % REBAR_PART_NAME)
print('Concrete instance: %s' % CONCRETE_INSTANCE_NAME)
print('Rebar instance: %s' % REBAR_INSTANCE_NAME)
print('Alignment vector: %s' % (align_vector,))
print('Additional translations: y -20, z -35, x +30')
print('Total rebar translation from original position: x +30, y 0, z +30')
print('Final rebar range:')
print('x: 30 ~ 300')
print('y: 0 ~ 110')
print('z: 30 ~ 580')