from abaqus import *
from abaqusConstants import *
import mesh

model_name = 'HSS_Stud'
part_name = 'L_Angle_With_2_Studs'

# Mesh size, unit: mm
BEAM_MESH_SIZE = 20.0
STUD_MESH_SIZE = 4.0

model = mdb.models[model_name]
p = model.parts[part_name]

# ============================================================
# Basic geometry parameters
# ============================================================
LEN_Z = 650.0

# L angle:
# 0 <= X <= 130, 0 <= Y <= 10
# 0 <= X <= 10,  0 <= Y <= 130

# Stud centers
STUD_X = 40.0
STUD1_Z = 450.0
STUD2_Z = 200.0

# Studs extend from Y = 0 to Y = -80
STUD_Y0 = 0.0
STUD_Y1 = -5.0
STUD_Y2 = -72.0
STUD_Y3 = -80.0

# Stud radii
R19 = 19.0 / 2.0
R13 = 13.0 / 2.0
R22 = 22.0 / 2.0
RMAX = R22

# Local partition range around studs
LOCAL_BOX = 14.0

# ============================================================
# Delete old mesh
# ============================================================
try:
    p.deleteMesh()
except:
    pass

# ============================================================
# Safe partition helper
# ============================================================
def safe_partition(principal_plane, offset):
    try:
        d = p.DatumPlaneByPrincipalPlane(
            principalPlane=principal_plane,
            offset=offset
        )
        p.PartitionCellByDatumPlane(
            datumPlane=p.datums[d.id],
            cells=p.cells[:]
        )
    except:
        pass

# ============================================================
# Partition L-angle beam for regular hex mesh
# ============================================================
# Split L-section into regular rectangular regions
safe_partition(YZPLANE, 10.0)    # X = 10
safe_partition(XZPLANE, 10.0)    # Y = 10

# Add several regular Z partitions along the beam length
# These help the long L-angle body form cleaner sweep blocks.
for z in (
    100.0,
    200.0,
    300.0,
    400.0,
    500.0,
    600.0
):
    safe_partition(XYPLANE, z)

# ============================================================
# Partition around two studs
# ============================================================
# X-direction local partitions through and around stud center
for x in (
    STUD_X - LOCAL_BOX,
    STUD_X,
    STUD_X + LOCAL_BOX
):
    safe_partition(YZPLANE, x)

# Z-direction local partitions around each stud
for stud_z in (STUD1_Z, STUD2_Z):
    for z in (
        stud_z - LOCAL_BOX,
        stud_z,
        stud_z + LOCAL_BOX
    ):
        safe_partition(XYPLANE, z)

# Y-direction partitions at stud stepped-cylinder boundaries
for y in (
    STUD_Y1,
    STUD_Y2,
    STUD_Y3
):
    safe_partition(XZPLANE, y)

# ============================================================
# Global seed for beam
# ============================================================
p.seedPart(
    size=BEAM_MESH_SIZE,
    deviationFactor=0.1,
    minSizeFactor=0.1
)

# ============================================================
# Local fine seed for two studs
# ============================================================
tol = 3.0

def fine_seed_stud_edges(stud_z):
    stud_edges = p.edges.getByBoundingBox(
        xMin=STUD_X - RMAX - tol,
        xMax=STUD_X + RMAX + tol,
        yMin=STUD_Y3 - tol,
        yMax=STUD_Y0 + tol,
        zMin=stud_z - RMAX - tol,
        zMax=stud_z + RMAX + tol
    )

    if len(stud_edges) > 0:
        p.seedEdgeBySize(
            edges=stud_edges,
            size=STUD_MESH_SIZE,
            deviationFactor=0.1,
            minSizeFactor=0.1,
            constraint=FINER
        )

fine_seed_stud_edges(STUD1_Z)
fine_seed_stud_edges(STUD2_Z)

# Add slightly refined transition area at beam-stud connection
TRANSITION_MESH_SIZE = 8.0

def seed_stud_transition(stud_z):
    transition_edges = p.edges.getByBoundingBox(
        xMin=STUD_X - LOCAL_BOX - tol,
        xMax=STUD_X + LOCAL_BOX + tol,
        yMin=-2.0,
        yMax=12.0,
        zMin=stud_z - LOCAL_BOX - tol,
        zMax=stud_z + LOCAL_BOX + tol
    )

    if len(transition_edges) > 0:
        p.seedEdgeBySize(
            edges=transition_edges,
            size=TRANSITION_MESH_SIZE,
            deviationFactor=0.1,
            minSizeFactor=0.1,
            constraint=FINER
        )

seed_stud_transition(STUD1_Z)
seed_stud_transition(STUD2_Z)

# ============================================================
# Hex mesh control
# ============================================================
cells = p.cells[:]

p.setMeshControls(
    regions=cells,
    elemShape=HEX,
    technique=SWEEP
)

elem_type = mesh.ElemType(
    elemCode=C3D8R,
    elemLibrary=STANDARD
)

p.setElementType(
    regions=(cells,),
    elemTypes=(elem_type,)
)

# ============================================================
# Generate mesh
# ============================================================
p.generateMesh()

mdb.save()