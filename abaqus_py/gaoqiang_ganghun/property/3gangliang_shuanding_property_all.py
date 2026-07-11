# -*- coding: utf-8 -*-

from abaqus import mdb
from abaqusConstants import *

modelName = 'HSS_Stud'
partName = 'L_Angle_With_2_Studs'

steelMatName = 'Q690D_Steel'
studMatName = 'ML15Al_Stud_D13'

steelSecName = 'Q690D_Steel_Section'
studSecName = 'ML15Al_Stud_D13_Section'

steelSetName = 'STEEL_BEAM_CELLS'
studSetName = 'STUD_CELLS'

model = mdb.models[modelName]
p = model.parts[partName]

# ------------------------------------------------------------
# Helper: convert cell indices to Abaqus mask
# ------------------------------------------------------------

def indices_to_mask(indices):
    indices = sorted(list(set(indices)))
    if len(indices) == 0:
        raise RuntimeError('Empty index list cannot be converted to mask.')

    nWords = indices[-1] // 32 + 1
    words = [0] * nWords

    for idx in indices:
        wordIndex = idx // 32
        bitIndex = idx % 32
        words[wordIndex] = words[wordIndex] | (1 << bitIndex)

    return '[#' + ' #'.join(['%x' % w for w in words]) + ' ]'

# ------------------------------------------------------------
# 1. Classify cells
# Your geometry:
# steel angle is at Y >= 0
# studs extend outward to negative Y
# ------------------------------------------------------------

steelIndex = []
studIndex = []

for c in p.cells:
    y = c.pointOn[0][1]

    if y < -1.0e-6:
        studIndex.append(c.index)
    else:
        steelIndex.append(c.index)

if len(studIndex) == 0:
    raise RuntimeError('No stud cells selected. Check merged geometry: studs should be at Y < 0.')

if len(steelIndex) == 0:
    raise RuntimeError('No steel cells selected. Check merged geometry: steel should be at Y >= 0.')

steelMask = indices_to_mask(steelIndex)
studMask = indices_to_mask(studIndex)

steelCells = p.cells.getSequenceFromMask(mask=(steelMask,))
studCells = p.cells.getSequenceFromMask(mask=(studMask,))

# ------------------------------------------------------------
# 2. Clear old section assignments first
# ------------------------------------------------------------

for i in range(len(p.sectionAssignments) - 1, -1, -1):
    del p.sectionAssignments[i]

# ------------------------------------------------------------
# 3. Delete old sets, sections, materials
# ------------------------------------------------------------

for setName in (steelSetName, studSetName):
    if setName in p.sets.keys():
        del p.sets[setName]

for secName in (steelSecName, studSecName):
    if secName in model.sections.keys():
        del model.sections[secName]

for matName in (steelMatName, studMatName):
    if matName in model.materials.keys():
        del model.materials[matName]

# ------------------------------------------------------------
# 4. Create sets
# ------------------------------------------------------------

p.Set(cells=steelCells, name=steelSetName)
p.Set(cells=studCells, name=studSetName)

# ------------------------------------------------------------
# 5. Q690D steel material, nominal values
# Units: N, mm, MPa, s
# Density: tonne/mm3
# ------------------------------------------------------------

steelMat = model.Material(name=steelMatName)
steelMat.Elastic(table=((206000.0, 0.30),))
steelMat.Density(table=((7.85e-9,),))
steelMat.Plastic(table=(
    (690.0, 0.0),
))

# ------------------------------------------------------------
# 6. ML15Al D13 stud material
# D13 stud: fy = 373 MPa, fu = 455 MPa
# Trilinear approximation with post-yield hardening
# ------------------------------------------------------------

E_STUD = 206000.0
FY_STUD = 373.0
FU_STUD = 455.0

eps_y = FY_STUD / E_STUD
eps_u = eps_y + (FU_STUD - FY_STUD) / (0.01 * E_STUD)

plastic_y = 0.0
plastic_u = eps_u - FU_STUD / E_STUD

studMat = model.Material(name=studMatName)
studMat.Elastic(table=((E_STUD, 0.30),))
studMat.Density(table=((7.85e-9,),))
studMat.Plastic(table=(
    (FY_STUD, plastic_y),
    (FU_STUD, plastic_u),
))

# ------------------------------------------------------------
# 7. Ductile damage for stud fracture
# Initial parameters; calibrate later if needed.
# Columns:
# fracture strain, stress triaxiality, strain rate
# ------------------------------------------------------------

studMat.DuctileDamageInitiation(table=(
    (0.20, -0.333333, 0.0),
    (0.15,  0.000000, 0.0),
    (0.10,  0.333333, 0.0),
    (0.06,  0.666667, 0.0),
))

studMat.ductileDamageInitiation.DamageEvolution(
    type=DISPLACEMENT,
    table=((3.0,),)
)

# ------------------------------------------------------------
# 8. Create solid sections
# ------------------------------------------------------------

model.HomogeneousSolidSection(
    name=steelSecName,
    material=steelMatName,
    thickness=None
)

model.HomogeneousSolidSection(
    name=studSecName,
    material=studMatName,
    thickness=None
)

# ------------------------------------------------------------
# 9. Assign sections
# ------------------------------------------------------------

p.SectionAssignment(
    region=p.sets[steelSetName],
    sectionName=steelSecName,
    offset=0.0,
    offsetType=MIDDLE_SURFACE,
    offsetField='',
    thicknessAssignment=FROM_SECTION
)

p.SectionAssignment(
    region=p.sets[studSetName],
    sectionName=studSecName,
    offset=0.0,
    offsetType=MIDDLE_SURFACE,
    offsetField='',
    thicknessAssignment=FROM_SECTION
)

print('Done: steel and stud properties assigned.')
print('Steel cells: %d' % len(steelCells))
print('Stud cells: %d' % len(studCells))
print('Steel section: %s -> %s' % (steelSecName, steelMatName))
print('Stud section: %s -> %s' % (studSecName, studMatName))
