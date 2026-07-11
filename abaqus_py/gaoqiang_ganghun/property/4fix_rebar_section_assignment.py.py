# -*- coding: utf-8 -*-

from abaqus import mdb
from abaqusConstants import *
import regionToolset
import math
import mesh

modelName = 'HSS_Stud'
partName = 'RebarCage'

materialName = 'HRB400_Rebar'
sectionName = 'Rebar_D10_TrussSection'

# HRB400 nominal values
E_REBAR = 200000.0
NU_REBAR = 0.30
FY_REBAR = 400.0

# D10 rebar area
D_REBAR = 10.0
A_REBAR = math.pi * D_REBAR ** 2.0 / 4.0

model = mdb.models[modelName]
p = model.parts[partName]

# ------------------------------------------------------------
# 1. Create / replace material
# ------------------------------------------------------------

if materialName in model.materials.keys():
    del model.materials[materialName]

mat = model.Material(name=materialName)
mat.Elastic(table=((E_REBAR, NU_REBAR),))
mat.Plastic(table=((FY_REBAR, 0.0),))

# ------------------------------------------------------------
# 2. Create / replace truss section
# ------------------------------------------------------------

if sectionName in model.sections.keys():
    del model.sections[sectionName]

model.TrussSection(
    name=sectionName,
    material=materialName,
    area=A_REBAR
)

# ------------------------------------------------------------
# 3. Assign section to ALL ELEMENTS of RebarCage
# Important:
# RebarCage is an orphan mesh part with T3D2 elements,
# so assign section to elements, not edges.
# ------------------------------------------------------------

if len(p.elements) == 0:
    raise RuntimeError('RebarCage has no elements. Check mesh / orphan mesh creation.')

allElements = p.elements[:]

# Optional: delete old section assignments
for i in range(len(p.sectionAssignments) - 1, -1, -1):
    del p.sectionAssignments[i]

region = regionToolset.Region(elements=allElements)

p.SectionAssignment(
    region=region,
    sectionName=sectionName
)

# ------------------------------------------------------------
# 4. Ensure T3D2 element type
# ------------------------------------------------------------

elemType = mesh.ElemType(
    elemCode=T3D2,
    elemLibrary=EXPLICIT
)

p.setElementType(
    regions=(allElements,),
    elemTypes=(elemType,)
)

# ------------------------------------------------------------
# 5. Create useful sets
# ------------------------------------------------------------

if 'ALL_REBAR' in p.sets.keys():
    del p.sets['ALL_REBAR']

p.Set(
    name='ALL_REBAR',
    elements=allElements
)

print('Done: RebarCage section assignment fixed.')
print('Part: %s' % partName)
print('Material: %s' % materialName)
print('Section: %s' % sectionName)
print('Area: %.6f mm^2' % A_REBAR)
print('Element count: %d' % len(allElements))
print('Element type: T3D2 Explicit')