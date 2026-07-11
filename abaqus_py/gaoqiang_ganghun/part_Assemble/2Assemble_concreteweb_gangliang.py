from abaqus import *
from abaqusConstants import *

model_name = 'HSS_Stud'

concrete_part_name = 'ConcretePlate_Final'
steel_part_name = 'L_Angle_With_2_Studs'

concrete_inst_name = 'ConcretePlate_Final_Instance'
steel_inst_name = 'L_Angle_With_2_Studs_Instance'

model = mdb.models[model_name]
a = model.rootAssembly
a.DatumCsysByDefault(CARTESIAN)

# Delete old assembly instances
for inst_name in (
    concrete_inst_name,
    steel_inst_name,
    'ConcretePlate_Final-1',
    'L_Angle_With_2_Studs-1'
):
    if inst_name in a.instances.keys():
        del a.instances[inst_name]

# Add concrete plate instance
a.Instance(
    name=concrete_inst_name,
    part=model.parts[concrete_part_name],
    dependent=ON
)

# Add steel beam + studs instance
a.Instance(
    name=steel_inst_name,
    part=model.parts[steel_part_name],
    dependent=ON
)

# Hole centers from simple_concrete_web.py
HOLE1_X = 260.0
HOLE1_Y = -20.0
HOLE1_Z = 515.0

HOLE2_X = 260.0
HOLE2_Y = -20.0
HOLE2_Z = 265.0

# Stud centers from gangliang_shuanding_both.py
STUD1_X = 40.0
STUD1_Y = 0.0
STUD1_Z = 450.0

STUD2_X = 40.0
STUD2_Y = 0.0
STUD2_Z = 200.0

# Rotate steel part 180 degrees about Z through stud centerline.
# This changes stud direction from -Y to +Y, so studs enter the concrete holes.
a.rotate(
    instanceList=(steel_inst_name,),
    axisPoint=(STUD1_X, STUD1_Y, 0.0),
    axisDirection=(0.0, 0.0, 1.0),
    angle=180.0
)

# Move steel so stud 1 center coincides with hole 1 center.
# Stud 2 also coincides because both vertical spacings are 250 mm.
dx = HOLE1_X - STUD1_X
dy = HOLE1_Y - STUD1_Y
dz = HOLE1_Z - STUD1_Z

a.translate(
    instanceList=(steel_inst_name,),
    vector=(dx, dy, dz)
)

mdb.save()