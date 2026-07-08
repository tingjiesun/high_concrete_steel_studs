# -*- coding: utf-8 -*-

from abaqus import mdb
from abaqusConstants import *

modelName = 'HSS_Stud'

stepName = 'Step-Pushout-Explicit'
ampName = 'Amp-SmoothStep-Pushout'

fieldOutputName = 'F-Output-Pushout'
rpHistoryOutputName = 'H-RP-Load-U3-RF3'
energyOutputName = 'H-Energy-Pushout'

rpLoadSetName = 'RP_LOAD'

model = mdb.models[modelName]
assembly = model.rootAssembly

# ------------------------------------------------------------
# Fast quasi-static explicit settings
# ------------------------------------------------------------

TIME_PERIOD = 0.02

# Field output is heavy. Use few frames only for failure/deformation checks.
FIELD_NUM_INTERVALS = 15

# History output is light. Use enough points for smooth load-slip curve.
HISTORY_NUM_INTERVALS = 600

# ------------------------------------------------------------
# Clean old output requests
# ------------------------------------------------------------

for name in (
    fieldOutputName,
    'F-Output-1',
    'F-Output-2',
):
    if name in model.fieldOutputRequests.keys():
        del model.fieldOutputRequests[name]

for name in (
    rpHistoryOutputName,
    energyOutputName,
    'H-Output-1',
    'H-Output-2',
):
    if name in model.historyOutputRequests.keys():
        del model.historyOutputRequests[name]

# ------------------------------------------------------------
# Create or update Explicit dynamic step
# Do not delete the step here, otherwise existing BCs referring to this step
# may be removed or invalidated.
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

# ------------------------------------------------------------
# Create or update Smooth Step amplitude
# ------------------------------------------------------------

if ampName in model.amplitudes.keys():
    try:
        model.amplitudes[ampName].setValues(
            timeSpan=STEP,
            data=((0.0, 0.0), (TIME_PERIOD, 1.0))
        )
    except:
        del model.amplitudes[ampName]
        model.SmoothStepAmplitude(
            name=ampName,
            timeSpan=STEP,
            data=((0.0, 0.0), (TIME_PERIOD, 1.0))
        )
else:
    model.SmoothStepAmplitude(
        name=ampName,
        timeSpan=STEP,
        data=((0.0, 0.0), (TIME_PERIOD, 1.0))
    )

# ------------------------------------------------------------
# Field output
# Keep this small. These variables are enough to check:
# deformation, stress, plastic zone, and deleted/failed elements.
# Do not request RF/V/A/contact/damage globally for fast batch runs.
# ------------------------------------------------------------

model.FieldOutputRequest(
    name=fieldOutputName,
    createStepName=stepName,
    variables=(
        'U',
        'S',
        'PEEQ',
        'STATUS',
    ),
    numIntervals=FIELD_NUM_INTERVALS
)

# ------------------------------------------------------------
# History output: load-slip curve
# This is the key output for bearing capacity.
# Curve:
#   x = abs(U3 at RP_LOAD)
#   y = abs(RF3 at RP_LOAD)
# ------------------------------------------------------------

if rpLoadSetName not in assembly.sets.keys():
    raise RuntimeError(
        'Assembly set %s not found. Create RP_LOAD before running this step script.'
        % rpLoadSetName
    )

rpLoadRegion = assembly.sets[rpLoadSetName]

model.HistoryOutputRequest(
    name=rpHistoryOutputName,
    createStepName=stepName,
    variables=(
        'U3',
        'RF3',
    ),
    region=rpLoadRegion,
    numIntervals=HISTORY_NUM_INTERVALS
)

# ------------------------------------------------------------
# History output: energy check for quasi-static explicit
# Check ALLKE / ALLIE after analysis.
# Recommended: ALLKE should usually stay below about 5%-10% of ALLIE.
# ------------------------------------------------------------

model.HistoryOutputRequest(
    name=energyOutputName,
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

print('Done: fast explicit step and output requests created.')
print('Step name: %s' % stepName)
print('Time period: %.6f' % TIME_PERIOD)
print('Amplitude name: %s' % ampName)
print('Field output intervals: %d' % FIELD_NUM_INTERVALS)
print('History output intervals: %d' % HISTORY_NUM_INTERVALS)
print('Field output variables: U, S, PEEQ, STATUS')
print('History output: RP_LOAD U3/RF3 + ALLIE/ALLKE/ALLAE/ALLWK/ETOTAL')