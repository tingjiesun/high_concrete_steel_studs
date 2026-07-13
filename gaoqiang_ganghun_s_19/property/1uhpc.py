# -*- coding: utf-8 -*-

from abaqus import mdb
from abaqusConstants import *
import regionToolset

modelName = 'HSS_MODEL_s_19'
partName = 'ConcretePlate_Final'

matName = 'UHPC_CDP'
secName = 'ConcretePlate_UHPC_Section'

model = mdb.models[modelName]
p = model.parts[partName]

# Clear old section assignments
for i in range(len(p.sectionAssignments) - 1, -1, -1):
    del p.sectionAssignments[i]

# Delete old section and material
if secName in model.sections.keys():
    del model.sections[secName]

if matName in model.materials.keys():
    del model.materials[matName]

# Create UHPC material
mat = model.Material(name=matName)

# Unit system: N-mm-tonne-s. Stresses are in MPa.
EC = 50900.0
NU = 0.20
DENSITY = 2.55e-9

# Simplified UHPC surrogate for the current calibration runs.
# This is ordinary isotropic metal plasticity, not CDP. The two entries match
# the requested CAE material dialog: yield stress / equivalent plastic strain.
UHPC_YIELD_STRESS = 149.8
UHPC_HARDENED_STRESS = 160.0
UHPC_HARDENED_PLASTIC_STRAIN = 0.02

mat.Elastic(table=((EC, NU),))
mat.Density(table=((DENSITY,),))
mat.Plastic(table=(
    (UHPC_YIELD_STRESS, 0.0),
    (UHPC_HARDENED_STRESS, UHPC_HARDENED_PLASTIC_STRAIN),
))

model.HomogeneousSolidSection(
    name=secName,
    material=matName,
    thickness=None
)

region = regionToolset.Region(cells=p.cells[:])

p.SectionAssignment(
    region=region,
    sectionName=secName,
    offset=0.0,
    offsetType=MIDDLE_SURFACE,
    offsetField='',
    thicknessAssignment=FROM_SECTION
)

print('Done: UHPC_CDP material and section assigned.')
print('Material: %s' % matName)
print('Section: %s' % secName)
print('Elastic: E = %.1f MPa, nu = %.2f' % (EC, NU))
print('Plastic: %.1f MPa at eps_p=0.0; %.1f MPa at eps_p=%.4f' % (
    UHPC_YIELD_STRESS,
    UHPC_HARDENED_STRESS,
    UHPC_HARDENED_PLASTIC_STRAIN
))
print('UHPC is defined with elastic, density, and ordinary plastic behavior only.')
