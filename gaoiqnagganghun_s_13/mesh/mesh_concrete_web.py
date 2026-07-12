# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import mesh

MODEL_NAME = 'HSS_Stud'
PART_NAME = 'ConcretePlate_Final'

model = mdb.models[MODEL_NAME]
p = model.parts[PART_NAME]

# ============================================================
# Mesh parameters, unit: mm
# ============================================================

# Coarse mesh away from holes
GLOBAL_MESH_SIZE = 45.0

# Slightly refined mesh near holes
HOLE_MESH_SIZE = 4.0
TRANSITION_MESH_SIZE = 12.0

# Concrete plate range
X_MIN = 0.0
X_MAX = 300.0
Y_MIN = -20.0
Y_MAX = 130.0
Z_MIN = -35.0
Z_MAX = 615.0

# Hole centers
HOLE_X = 260.0
HOLE1_Z = 515.0
HOLE2_Z = 265.0

# Stepped hole depths
Y0 = -20.0
Y1 = -15.0
Y2 = 52.0
Y3 = 60.0

# Hole radii
R19 = 19.0 / 2.0
R13 = 13.0 / 2.0
R22 = 22.0 / 2.0
R_MAX = R22

# Hole local zones
HOLE_FINE_BOX = 24.0
HOLE_TRANS_BOX = 40.0

tol = 3.0

# ============================================================
# Delete old mesh
# ============================================================

try:
    p.deleteMesh()
except:
    pass

# ============================================================
# Global seed
# ============================================================

p.seedPart(
    size=GLOBAL_MESH_SIZE,
    deviationFactor=0.1,
    minSizeFactor=0.1
)

# ============================================================
# Local seed around holes
# ============================================================

def seed_hole_zone(hole_z):
    hole_edges = p.edges.getByBoundingBox(
        xMin=HOLE_X - HOLE_FINE_BOX - tol,
        xMax=HOLE_X + HOLE_FINE_BOX + tol,
        yMin=Y0 - tol,
        yMax=Y3 + tol,
        zMin=hole_z - HOLE_FINE_BOX - tol,
        zMax=hole_z + HOLE_FINE_BOX + tol
    )

    if len(hole_edges) > 0:
        p.seedEdgeBySize(
            edges=hole_edges,
            size=HOLE_MESH_SIZE,
            deviationFactor=0.1,
            minSizeFactor=0.1,
            constraint=FINER
        )

    transition_edges = p.edges.getByBoundingBox(
        xMin=HOLE_X - HOLE_TRANS_BOX - tol,
        xMax=HOLE_X + HOLE_TRANS_BOX + tol,
        yMin=Y0 - tol,
        yMax=Y3 + tol,
        zMin=hole_z - HOLE_TRANS_BOX - tol,
        zMax=hole_z + HOLE_TRANS_BOX + tol
    )

    if len(transition_edges) > 0:
        p.seedEdgeBySize(
            edges=transition_edges,
            size=TRANSITION_MESH_SIZE,
            deviationFactor=0.1,
            minSizeFactor=0.1,
            constraint=FINER
        )

    # Re-apply finer seed after transition seed
    if len(hole_edges) > 0:
        p.seedEdgeBySize(
            edges=hole_edges,
            size=HOLE_MESH_SIZE,
            deviationFactor=0.1,
            minSizeFactor=0.1,
            constraint=FINER
        )

seed_hole_zone(HOLE1_Z)
seed_hole_zone(HOLE2_Z)

# ============================================================
# Cell selections
# ============================================================

all_cells = p.cells[:]

def get_hole_cells(hole_z):
    return p.cells.getByBoundingBox(
        xMin=HOLE_X - HOLE_TRANS_BOX - tol,
        xMax=HOLE_X + HOLE_TRANS_BOX + tol,
        yMin=Y0 - tol,
        yMax=Y3 + tol,
        zMin=hole_z - HOLE_TRANS_BOX - tol,
        zMax=hole_z + HOLE_TRANS_BOX + tol
    )

hole1_cells = get_hole_cells(HOLE1_Z)
hole2_cells = get_hole_cells(HOLE2_Z)

if len(hole1_cells) == 0:
    raise RuntimeError('No cells selected around hole 1.')

if len(hole2_cells) == 0:
    raise RuntimeError('No cells selected around hole 2.')

# ============================================================
# Element types
# ============================================================

elem_type_hex = mesh.ElemType(
    elemCode=C3D8R,
    elemLibrary=EXPLICIT
)

elem_type_wedge = mesh.ElemType(
    elemCode=C3D6,
    elemLibrary=EXPLICIT
)

elem_type_tet = mesh.ElemType(
    elemCode=C3D4,
    elemLibrary=EXPLICIT
)

p.setElementType(
    regions=(all_cells,),
    elemTypes=(elem_type_hex, elem_type_wedge, elem_type_tet)
)

# ============================================================
# Mesh controls
# ============================================================

# First try HEX/SWEEP everywhere.
try:
    p.setMeshControls(
        regions=all_cells,
        elemShape=HEX,
        technique=SWEEP
    )
except:
    pass

# Enforce HEX/SWEEP near holes.
p.setMeshControls(
    regions=hole1_cells,
    elemShape=HEX,
    technique=SWEEP
)

p.setMeshControls(
    regions=hole2_cells,
    elemShape=HEX,
    technique=SWEEP
)

# ============================================================
# Generate mesh
# ============================================================

try:
    p.generateMesh()
except Exception as e:
    raise RuntimeError(
        'Mesh generation failed. Hole zones are required to use HEX/SWEEP. '
        'If this fails, the hole partition is still not sweepable. '
        + str(e)
    )

if len(p.elements) == 0:
    raise RuntimeError('ConcretePlate mesh was not generated.')

print('ConcretePlate mesh finished.')
print('Part: %s' % PART_NAME)
print('Total element number: %d' % len(p.elements))
print('Hole 1 cells: %d' % len(hole1_cells))
print('Hole 2 cells: %d' % len(hole2_cells))
print('Global mesh size: %.2f mm' % GLOBAL_MESH_SIZE)
print('Hole mesh size: %.2f mm' % HOLE_MESH_SIZE)
print('Transition mesh size: %.2f mm' % TRANSITION_MESH_SIZE)
print('Hole zones: HEX/SWEEP')
print('Other zones: try HEX/SWEEP with coarse mesh')

mdb.save()