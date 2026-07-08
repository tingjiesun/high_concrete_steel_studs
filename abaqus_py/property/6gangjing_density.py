# -*- coding: mbcs -*-
from abaqus import *
from abaqusConstants import *

MODEL_NAME = 'HSS_Stud'
PART_NAME = 'RebarCage'
MATERIAL_NAME = 'HRB400_Rebar'
REBAR_DENSITY = 7850.0

if MODEL_NAME not in mdb.models.keys():
    raise ValueError('Model not found: %s' % MODEL_NAME)

model = mdb.models[MODEL_NAME]

if PART_NAME not in model.parts.keys():
    raise ValueError('Part not found in model %s: %s' % (MODEL_NAME, PART_NAME))

if MATERIAL_NAME not in model.materials.keys():
    raise ValueError('Material not found in model %s: %s' % (MODEL_NAME, MATERIAL_NAME))

mat = model.materials[MATERIAL_NAME]
mat.Density(table=((REBAR_DENSITY, ), ))

print('Density has been added:')
print('  Model    = %s' % MODEL_NAME)
print('  Part     = %s' % PART_NAME)
print('  Material = %s' % MATERIAL_NAME)
print('  Density  = %.6g' % REBAR_DENSITY)

mdb.save()
