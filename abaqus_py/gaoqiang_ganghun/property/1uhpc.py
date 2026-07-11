# -*- coding: utf-8 -*-

from abaqus import mdb
from abaqusConstants import *
import regionToolset

modelName = 'HSS_Stud'
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

# The appendix reports 149.8 MPa (cube) and 137.8 MPa (axial) for the UHPC.
# The Chapter 3 uniaxial constitutive curve needs the axial strength; using
# 137.8 MPa with epsilon_c0 = 0.0029 also gives a physically valid, nonnegative
# Abaqus inelastic-strain conversion. Keep 149.8 MPa for capacity comparisons.
FC_CUBE = 149.8
FC_AXIAL = 137.8
EPS_C0 = 0.0029

# Chapter 3 tensile parameters.
FCT = 9.0
FCH = 11.0

# These CDP flow parameters were not published in the thesis. They are kept as
# explicit calibration variables. Start with zero viscosity in Explicit so the
# material does not gain artificial rate regularization.
DILATION_ANGLE = 30.0
ECCENTRICITY = 0.1
FB0_FC0 = 1.16
KC = 0.667
VISCOSITY = 0.0

mat.Elastic(table=((EC, NU),))
mat.Density(table=((DENSITY,),))
mat.ConcreteDamagedPlasticity(table=((
    DILATION_ANGLE, ECCENTRICITY, FB0_FC0, KC, VISCOSITY
),))


def _clip_damage(value, previous):
    """Keep CDP damage valid and nondecreasing."""
    value = max(previous, value)
    return min(0.9999, max(0.0, value))


def _compression_stress(total_strain):
    """Chapter 3 Eq. (3.3), using the appendix axial strength."""
    xi = total_strain / EPS_C0
    alpha = EC / (FC_AXIAL / EPS_C0)
    if xi <= 1.0:
        return FC_AXIAL * (alpha * xi - xi * xi) / (1.0 + (alpha - 2.0) * xi)
    return FC_AXIAL * xi / (2.0 * (xi - 1.0) ** 2 + xi)


# Compression: derive the hardening and damage entries from the thesis curve
# instead of manually delaying post-peak softening. Abaqus expects inelastic
# strain, not total strain: eps_in = eps_total - sigma / E.
compression_xi = (0.40, 0.60, 0.80, 1.00, 1.20, 1.50, 2.00, 3.00, 4.00)
compression_raw = []
for xi in compression_xi:
    total_strain = xi * EPS_C0
    stress = _compression_stress(total_strain)
    inelastic_strain = total_strain - stress / EC
    raw_damage = 1.0 - stress / (EC * total_strain)
    compression_raw.append((stress, inelastic_strain, raw_damage))

# The first compression-hardening point must have zero inelastic strain.
compression_offset = compression_raw[0][1]
compression_damage_offset = compression_raw[0][2]
compression_hardening = []
compression_damage = []
previous_damage = 0.0
for stress, raw_inelastic, raw_damage in compression_raw:
    inelastic_strain = max(0.0, raw_inelastic - compression_offset)
    damage = _clip_damage(raw_damage - compression_damage_offset, previous_damage)
    compression_hardening.append((stress, inelastic_strain))
    compression_damage.append((damage, inelastic_strain))
    previous_damage = damage

mat.concreteDamagedPlasticity.ConcreteCompressionHardening(
    table=tuple(compression_hardening)
)
mat.concreteDamagedPlasticity.ConcreteCompressionDamage(
    table=tuple(compression_damage)
)

# Tension stiffening: the first two points reproduce Chapter 3 (9 MPa at
# cracking and 11 MPa at 2500 microstrain). The descending tail remains an
# explicit calibration tail because the readable thesis text does not provide
# all coordinates of the fitted descending branch in Eq. (3.4).
tension_stiffening = (
    (9.000000, 0.00000000),
    (11.000000, 0.00228389),
    (10.500000, 0.00350000),
    (9.000000, 0.00500000),
    (7.000000, 0.00700000),
    (4.500000, 0.01000000),
    (2.000000, 0.01400000),
    (0.500000, 0.02000000),
)

mat.concreteDamagedPlasticity.ConcreteTensionStiffening(
    table=tension_stiffening
)

# Chapter 3 Eq. (3.5): D = 1 - sigma / (E * epsilon_total).
# For tension, epsilon_total = cracking_strain + sigma / E.
# Abaqus internally converts cracking strain and damage to tensile plastic
# strain. Directly using Eq. (3.5) makes that plastic strain exactly zero;
# rounding then produces a negative/decreasing value and aborts input
# processing. Retain 98% of the Eq. (3.5) damage so plastic strain remains
# small, positive, and monotonic.
TENSION_DAMAGE_SCALE = 0.98
tension_damage = []
previous_damage = 0.0
previous_plastic_strain = 0.0
for stress, cracking_strain in tension_stiffening:
    total_strain = cracking_strain + stress / EC
    raw_damage = 1.0 - stress / (EC * total_strain)
    damage = _clip_damage(raw_damage * TENSION_DAMAGE_SCALE, previous_damage)

    # Same conversion used by Abaqus for the CDP tensile-damage consistency
    # check. Keep this guard so later edits to the tail cannot create an
    # invalid damage table silently.
    plastic_strain = cracking_strain - damage / (1.0 - damage) * stress / EC
    if plastic_strain < previous_plastic_strain - 1.0e-12:
        raise ValueError('Tension damage produces decreasing plastic strain.')
    if plastic_strain < -1.0e-12:
        raise ValueError('Tension damage produces negative plastic strain.')

    tension_damage.append((damage, cracking_strain))
    previous_damage = damage
    previous_plastic_strain = max(previous_plastic_strain, plastic_strain)

mat.concreteDamagedPlasticity.ConcreteTensionDamage(
    table=tuple(tension_damage)
)

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
print('Compression curve: fc_axial = %.1f MPa, fc_cube = %.1f MPa' % (
    FC_AXIAL, FC_CUBE
))
print('Tension stress: fct = %.1f MPa, fch = %.1f MPa' % (FCT, FCH))
print('Compression and tension CDP damage tables are defined.')
