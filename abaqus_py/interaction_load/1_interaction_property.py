# -*- coding: utf-8 -*-

from abaqus import mdb
from abaqusConstants import *
from symbolicConstants import SymbolicConstant

modelName = 'HSS_Stud'

# Contact property names
steelUHPCPropName = 'Prop-Steel-UHPC-Cohesive'
studUHPCPropName = 'Prop-Stud-UHPC-Frictionless'

model = mdb.models[modelName]

# Some Abaqus versions do not expose QUAD_TRACTION directly
try:
    QUAD_TRACTION_CONST = QUAD_TRACTION
except NameError:
    QUAD_TRACTION_CONST = SymbolicConstant('QUAD_TRACTION')

# ------------------------------------------------------------
# Optional cleanup
# If old interactions already use these properties, delete them first.
# ------------------------------------------------------------

for interactionName in (
    'Int-Steel-UHPC-Cohesive',
    'Int-Stud-UHPC-Frictionless',
):
    if interactionName in model.interactions.keys():
        del model.interactions[interactionName]

for propName in (
    steelUHPCPropName,
    studUHPCPropName,
):
    if propName in model.interactionProperties.keys():
        del model.interactionProperties[propName]

# ------------------------------------------------------------
# 1. Steel-UHPC interface property
# Paper setting:
# normal: hard contact
# tangential: penalty friction, mu = 0.4
# cohesive: traction-separation behavior
# damage: quadratic nominal stress criterion
# tn = 1000 MPa, ts = tt = 0.3 MPa, failure displacement = 3.5 mm
# ------------------------------------------------------------

steelUHPCProp = model.ContactProperty(steelUHPCPropName)

steelUHPCProp.NormalBehavior(
    pressureOverclosure=HARD,
    allowSeparation=ON,
    constraintEnforcementMethod=DEFAULT
)

try:
    steelUHPCProp.TangentialBehavior(
        formulation=PENALTY,
        directionality=ISOTROPIC,
        slipRateDependency=OFF,
        pressureDependency=OFF,
        temperatureDependency=OFF,
        dependencies=0,
        table=((0.4,),),
        shearStressLimit=None,
        maximumElasticSlip=FRACTION,
        fraction=0.005,
        elasticSlipStiffness=None
    )
except TypeError:
    steelUHPCProp.TangentialBehavior(
        formulation=PENALTY,
        table=((0.4,),)
    )

try:
    steelUHPCProp.CohesiveBehavior(defaultPenalties=ON)
except TypeError:
    steelUHPCProp.CohesiveBehavior()

# Cohesive damage definition.
# Different Abaqus versions use slightly different keyword names,
# so try several compatible forms.
lastError = None

try:
    steelUHPCProp.Damage(
        criterion=QUAD_TRACTION_CONST,
        initTable=((1000.0, 0.3, 0.3),),
        useEvolution=ON,
        evolutionType=DISPLACEMENT,
        evolutionTable=((3.5,),),
        softening=LINEAR
    )
except Exception as e:
    lastError = e
else:
    lastError = None

if lastError is not None:
    try:
        steelUHPCProp.Damage(
            criterion=QUAD_TRACTION_CONST,
            initTable=((1000.0, 0.3, 0.3),),
            useEvolution=ON,
            evolutionType=DISPLACEMENT,
            evolTable=((3.5,),),
            softening=LINEAR
        )
    except Exception as e:
        lastError = e
    else:
        lastError = None

if lastError is not None:
    try:
        steelUHPCProp.Damage(
            initiationCriterion=QUAD_TRACTION_CONST,
            initTable=((1000.0, 0.3, 0.3),),
            useEvolution=ON,
            evolutionType=DISPLACEMENT,
            evolutionTable=((3.5,),),
            softening=LINEAR
        )
    except Exception as e:
        lastError = e
    else:
        lastError = None

if lastError is not None:
    raise lastError

# ------------------------------------------------------------
# 2. Stud-UHPC hole wall contact property
# Paper setting:
# normal: hard contact
# tangential: frictionless
# ------------------------------------------------------------

studUHPCProp = model.ContactProperty(studUHPCPropName)

studUHPCProp.NormalBehavior(
    pressureOverclosure=HARD,
    allowSeparation=ON,
    constraintEnforcementMethod=DEFAULT
)

studUHPCProp.TangentialBehavior(
    formulation=FRICTIONLESS
)

print('Done: contact properties created.')
print('Steel-UHPC property: %s' % steelUHPCPropName)
print('Stud-UHPC property: %s' % studUHPCPropName)
print('Steel-UHPC: Hard contact + friction 0.4 + cohesive damage QUAD_TRACTION')
print('Stud-UHPC: Hard contact + frictionless')