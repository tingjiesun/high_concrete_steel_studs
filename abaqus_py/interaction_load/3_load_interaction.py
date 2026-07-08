# -*- coding: utf-8 -*-

from abaqus import mdb
from abaqusConstants import *
from symbolicConstants import SymbolicConstant
import regionToolset

modelName = 'HSS_Stud'

concreteInstName = 'ConcretePlate_Final_Instance'
rebarInstName = 'RebarCage-1'

stepName = 'Step-Pushout-Explicit'
ampName = 'Amp-SmoothStep-Pushout'

steelUHPCPropName = 'Prop-Steel-UHPC-Cohesive'
studUHPCPropName = 'Prop-Stud-UHPC-Frictionless'
defaultGeneralPropName = 'Prop-GeneralContact-Default'

surfSteelInterfaceName = 'Surf-Steel-Interface'
surfConcreteInterfaceName = 'Surf-Concrete-SteelInterface'
surfStudName = 'Surf-Studs'
surfHoleName = 'Surf-Concrete-Holes'
surfSteelLoadName = 'Surf-Steel-Top-Load'
surfConcreteSupportName = 'Surf-Concrete-Bottom-Support'

setXSymConcreteName = 'Set-XSym-Concrete'
setXSymSteelName = 'Set-XSym-Steel'
setXSymRebarName = 'Set-XSym-Rebar'

rpLoadSetName = 'RP_LOAD'
rpSupportSetName = 'RP_SUPPORT'

# Loading and output settings
TIME_PERIOD = 0.02
LOAD_U3 = -5.0
FIELD_NUM_INTERVALS = 15
HISTORY_NUM_INTERVALS = 600

generalContactName = 'Int-GeneralContact-Explicit'

model = mdb.models[modelName]
a = model.rootAssembly

concreteInst = a.instances[concreteInstName]
rebarInst = a.instances[rebarInstName]

try:
    GLOBAL_CONST = GLOBAL
except NameError:
    GLOBAL_CONST = SymbolicConstant('GLOBAL')

try:
    SELF_CONST = SELF
except NameError:
    SELF_CONST = SymbolicConstant('SELF')


def require_surface(name):
    if name not in a.surfaces.keys():
        raise RuntimeError('Required surface not found: %s. Run script 2 first.' % name)
    return a.surfaces[name]


def require_set(name):
    if name not in a.sets.keys():
        raise RuntimeError('Required set not found: %s. Run script 2 first.' % name)
    return a.sets[name]


def require_property(name):
    if name not in model.interactionProperties.keys():
        raise RuntimeError('Required contact property not found: %s. Run script 1 first.' % name)
    return name


def delete_if_exists(container, name):
    if name in container.keys():
        del container[name]


def apply_xsymm_bc(name, region):
    if name in model.boundaryConditions.keys():
        del model.boundaryConditions[name]

    try:
        model.XsymmBC(
            name=name,
            createStepName='Initial',
            region=region,
            localCsys=None
        )
    except:
        model.DisplacementBC(
            name=name,
            createStepName='Initial',
            region=region,
            u1=0.0,
            u2=UNSET,
            u3=UNSET,
            ur1=UNSET,
            ur2=0.0,
            ur3=0.0,
            amplitude=UNSET,
            distributionType=UNIFORM,
            fieldName='',
            localCsys=None
        )


def ensure_default_general_contact_property():
    if defaultGeneralPropName in model.interactionProperties.keys():
        del model.interactionProperties[defaultGeneralPropName]

    prop = model.ContactProperty(defaultGeneralPropName)

    prop.NormalBehavior(
        pressureOverclosure=HARD,
        allowSeparation=ON,
        constraintEnforcementMethod=DEFAULT
    )

    prop.TangentialBehavior(
        formulation=FRICTIONLESS
    )


def append_contact_property_assignment(gc, assignments):
    try:
        gc.contactPropertyAssignments.appendInStep(
            stepName=stepName,
            assignments=assignments
        )
        return
    except TypeError:
        pass

    gc.contactPropertyAssignments.appendInStep(
        assignments=assignments,
        stepName=stepName
    )


def create_general_contact_exp(name, pairAssignments):
    if name in model.interactions.keys():
        del model.interactions[name]

    gc = model.ContactExp(
        name=name,
        createStepName=stepName
    )

    pairRegions = tuple([(item[0], item[1]) for item in pairAssignments])
    selectedPairOK = False

    try:
        gc.includedPairs.setValuesInStep(
            stepName=stepName,
            useAllstar=OFF,
            addPairs=pairRegions
        )
        selectedPairOK = True
    except TypeError:
        selectedPairOK = False

    if not selectedPairOK:
        try:
            gc.includedPairs.setValuesInStep(
                stepName=stepName,
                useAllstar=OFF,
                pairs=pairRegions
            )
            selectedPairOK = True
        except TypeError:
            selectedPairOK = False

    if not selectedPairOK:
        gc.includedPairs.setValuesInStep(
            stepName=stepName,
            useAllstar=ON
        )
        print('Warning: selected-pair general contact failed; using allstar general contact.')

    append_contact_property_assignment(
        gc,
        ((GLOBAL_CONST, SELF_CONST, defaultGeneralPropName),)
    )

    pairSpecificAssignments = tuple([
        (item[0], item[1], item[2]) for item in pairAssignments
    ])

    append_contact_property_assignment(gc, pairSpecificAssignments)

    return gc


# ------------------------------------------------------------
# 1. Create or update step and Smooth Step amplitude
# ------------------------------------------------------------

if stepName in model.steps.keys():
    model.steps[stepName].setValues(
        timePeriod=TIME_PERIOD,
        nlgeom=ON,
        linearBulkViscosity=0.06,
        quadBulkViscosity=1.2
    )
else:
    model.ExplicitDynamicsStep(
        name=stepName,
        previous='Initial',
        timePeriod=TIME_PERIOD,
        nlgeom=ON
    )

    model.steps[stepName].setValues(
        linearBulkViscosity=0.06,
        quadBulkViscosity=1.2
    )

if ampName in model.amplitudes.keys():
    del model.amplitudes[ampName]

model.SmoothStepAmplitude(
    name=ampName,
    timeSpan=STEP,
    data=((0.0, 0.0), (TIME_PERIOD, 1.0))
)

# ------------------------------------------------------------
# 2. Clean old interactions, constraints, BCs, and output requests
# ------------------------------------------------------------

for name in (
    'Int-Embedded-Rebar-UHPC',
    'Coupling-LoadRP-SteelTop',
    'Coupling-SupportRP-ConcreteBottom',
):
    delete_if_exists(model.constraints, name)

for name in (
    'Int-Steel-UHPC-Cohesive',
    'Int-Stud-UHPC-Frictionless',
    generalContactName,
):
    delete_if_exists(model.interactions, name)

for name in (
    'BC-Support-RP',
    'BC-Load-RP',
    'BC-Load-RP-Fix',
    'BC-Load-RP-U3',
    'BC-XSym-Concrete',
    'BC-XSym-Steel',
    'BC-XSym-Rebar',
):
    delete_if_exists(model.boundaryConditions, name)

for name in (
    'H-RP-Load-U3-RF3',
    'H-Energy-Pushout',
    'H-Output-1',
    'H-Output-2',
):
    delete_if_exists(model.historyOutputRequests, name)

for name in (
    'F-Output-Pushout',
    'F-Output-1',
    'F-Output-2',
):
    delete_if_exists(model.fieldOutputRequests, name)

# ------------------------------------------------------------
# 3. Required surfaces, sets, and properties
# ------------------------------------------------------------

steelSurf = require_surface(surfSteelInterfaceName)
concreteSurf = require_surface(surfConcreteInterfaceName)

studSurf = require_surface(surfStudName)
holeSurf = require_surface(surfHoleName)

steelLoadSurf = require_surface(surfSteelLoadName)
concreteSupportSurf = require_surface(surfConcreteSupportName)

rpLoadSet = require_set(rpLoadSetName)
rpSupportSet = require_set(rpSupportSetName)

ensure_default_general_contact_property()

require_property(defaultGeneralPropName)
require_property(steelUHPCPropName)
require_property(studUHPCPropName)

# ------------------------------------------------------------
# 4. Embedded rebar in UHPC
# ------------------------------------------------------------

rebarRegion = regionToolset.Region(elements=rebarInst.elements[:])
hostRegion = regionToolset.Region(cells=concreteInst.cells[:])

model.EmbeddedRegion(
    name='Int-Embedded-Rebar-UHPC',
    embeddedRegion=rebarRegion,
    hostRegion=hostRegion,
    weightFactorTolerance=1.0e-6,
    absoluteTolerance=0.0,
    fractionalTolerance=0.05,
    toleranceMethod=BOTH
)

# ------------------------------------------------------------
# 5. General contact for steel-UHPC and stud-UHPC
# ------------------------------------------------------------

create_general_contact_exp(
    name=generalContactName,
    pairAssignments=(
        (steelSurf, concreteSurf, steelUHPCPropName),
        (studSurf, holeSurf, studUHPCPropName),
    )
)

# ------------------------------------------------------------
# 6. Coupling: load RP to steel top surface
# ------------------------------------------------------------

model.Coupling(
    name='Coupling-LoadRP-SteelTop',
    controlPoint=rpLoadSet,
    surface=steelLoadSurf,
    influenceRadius=WHOLE_SURFACE,
    couplingType=KINEMATIC,
    localCsys=None,
    u1=ON,
    u2=ON,
    u3=ON,
    ur1=OFF,
    ur2=OFF,
    ur3=OFF
)

# ------------------------------------------------------------
# 7. Coupling: support RP to concrete bottom surface
# ------------------------------------------------------------

model.Coupling(
    name='Coupling-SupportRP-ConcreteBottom',
    controlPoint=rpSupportSet,
    surface=concreteSupportSurf,
    influenceRadius=WHOLE_SURFACE,
    couplingType=KINEMATIC,
    localCsys=None,
    u1=ON,
    u2=ON,
    u3=ON,
    ur1=OFF,
    ur2=OFF,
    ur3=OFF
)

# ------------------------------------------------------------
# 8. Boundary conditions
# ------------------------------------------------------------

model.DisplacementBC(
    name='BC-Support-RP',
    createStepName='Initial',
    region=rpSupportSet,
    u1=0.0,
    u2=0.0,
    u3=0.0,
    ur1=0.0,
    ur2=0.0,
    ur3=0.0,
    amplitude=UNSET,
    distributionType=UNIFORM,
    fieldName='',
    localCsys=None
)

model.DisplacementBC(
    name='BC-Load-RP-Fix',
    createStepName='Initial',
    region=rpLoadSet,
    u1=0.0,
    u2=0.0,
    u3=UNSET,
    ur1=0.0,
    ur2=0.0,
    ur3=0.0,
    amplitude=UNSET,
    distributionType=UNIFORM,
    fieldName='',
    localCsys=None
)

model.DisplacementBC(
    name='BC-Load-RP-U3',
    createStepName=stepName,
    region=rpLoadSet,
    u1=UNSET,
    u2=UNSET,
    u3=LOAD_U3,
    ur1=UNSET,
    ur2=UNSET,
    ur3=UNSET,
    amplitude=ampName,
    distributionType=UNIFORM,
    fieldName='',
    localCsys=None
)

if setXSymConcreteName in a.sets.keys():
    apply_xsymm_bc(
        name='BC-XSym-Concrete',
        region=a.sets[setXSymConcreteName]
    )
else:
    print('Warning: %s not found, concrete x-symmetry BC skipped.' % setXSymConcreteName)

if setXSymSteelName in a.sets.keys():
    apply_xsymm_bc(
        name='BC-XSym-Steel',
        region=a.sets[setXSymSteelName]
    )
else:
    print('Warning: %s not found, steel x-symmetry BC skipped.' % setXSymSteelName)

if setXSymRebarName in a.sets.keys():
    model.DisplacementBC(
        name='BC-XSym-Rebar',
        createStepName='Initial',
        region=a.sets[setXSymRebarName],
        u1=0.0,
        u2=UNSET,
        u3=UNSET,
        ur1=UNSET,
        ur2=UNSET,
        ur3=UNSET,
        amplitude=UNSET,
        distributionType=UNIFORM,
        fieldName='',
        localCsys=None
    )
else:
    print('Warning: %s not found, rebar x-symmetry BC skipped.' % setXSymRebarName)

# ------------------------------------------------------------
# 9. Output requests
# Fast batch setting:
# Field output is only for failure/deformation inspection.
# History output is for load-slip curve and quasi-static energy check.
# ------------------------------------------------------------

model.FieldOutputRequest(
    name='F-Output-Pushout',
    createStepName=stepName,
    variables=(
        'U',
        'S',
        'PEEQ',
        'STATUS',
    ),
    numIntervals=FIELD_NUM_INTERVALS
)

model.HistoryOutputRequest(
    name='H-RP-Load-U3-RF3',
    createStepName=stepName,
    variables=(
        'U3',
        'RF3',
    ),
    region=rpLoadSet,
    numIntervals=HISTORY_NUM_INTERVALS
)

model.HistoryOutputRequest(
    name='H-Energy-Pushout',
    createStepName=stepName,
    variables=(
        'ALLIE',
        'ALLKE',
        'ALLAE',
        'ALLWK',
        'ETOTAL',
    ),
    numIntervals=HISTORY_NUM_INTERVALS
)

a.regenerate()

print('Done: true interactions, couplings, BCs, loading, and fast outputs were created.')
print('Step name: %s' % stepName)
print('Time period: %.6f' % TIME_PERIOD)
print('General contact: %s' % generalContactName)
print('Default general contact property: %s' % defaultGeneralPropName)
print('  Steel-UHPC pair property: %s' % steelUHPCPropName)
print('  Stud-UHPC pair property: %s' % studUHPCPropName)
print('Embedded region: Int-Embedded-Rebar-UHPC')
print('Load RP: U3 = %.3f, amplitude = %s' % (LOAD_U3, ampName))
print('Support RP: U1=U2=U3=UR1=UR2=UR3=0')
print('X symmetry: concrete/steel use XsymmBC; rebar uses U1=0')
print('Field output: U, S, PEEQ, STATUS; intervals = %d' % FIELD_NUM_INTERVALS)
print('History output: RP_LOAD U3/RF3 and energy; intervals = %d' % HISTORY_NUM_INTERVALS)