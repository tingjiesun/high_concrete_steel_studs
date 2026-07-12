# -*- coding: utf-8 -*-

from abaqus import mdb
from abaqusConstants import *

modelName = 'HSS_Stud'

concreteInstName = 'ConcretePlate_Final_Instance'
rebarInstName = 'RebarCage-1'
steelInstName = 'L_Angle_With_2_Studs_Instance'

model = mdb.models[modelName]
a = model.rootAssembly

concreteInst = a.instances[concreteInstName]
rebarInst = a.instances[rebarInstName]
steelInst = a.instances[steelInstName]

# ------------------------------------------------------------
# Geometry parameters from your model
# ------------------------------------------------------------

X_SYMM = 300.0

Y_INTERFACE = -20.0

Z_CONCRETE_MIN = -35.0
Z_STEEL_MAX = 715.0

HOLE_X = 260.0
HOLE1_Z = 515.0
HOLE2_Z = 265.0
SLIP_POINT_X = 235.0
SLIP_POINT_Z = 0.5 * (HOLE1_Z + HOLE2_Z)

TOL = 0.5

# ------------------------------------------------------------
# Names to be created
# ------------------------------------------------------------

surfSteelInterfaceName = 'Surf-Steel-Interface'
surfConcreteInterfaceName = 'Surf-Concrete-SteelInterface'
surfStudName = 'Surf-Studs'
surfHoleName = 'Surf-Concrete-Holes'
surfSteelLoadName = 'Surf-Steel-Top-Load'
surfConcreteSupportName = 'Surf-Concrete-Bottom-Support'

setSteelInterfaceName = 'Set-Steel-Interface-YMax'
setConcreteInterfaceName = 'Set-Concrete-SteelInterface'
setStudFacesName = 'Set-Stud-Faces'
setHoleFacesName = 'Set-Concrete-Hole-Faces'
studSourceFaceSetName = 'Set-shuanding_surface'
holeSourceFaceSetName = 'Set-shuanding_hole_surface'
setSteelLoadName = 'Set-Steel-Top-Load'
setConcreteSupportName = 'Set-Concrete-Bottom-Support'

setXSymConcreteName = 'Set-XSym-Concrete'
setXSymSteelName = 'Set-XSym-Steel'
setXSymRebarName = 'Set-XSym-Rebar'
setSlipSteelNodeName = 'Set-Slip-Steel-Interface-Node'
setSlipConcreteNodeName = 'Set-Slip-Concrete-Interface-Node'

rpLoadFeatureName = 'RP_LOAD_FEATURE'
rpSupportFeatureName = 'RP_SUPPORT_FEATURE'
rpLoadSetName = 'RP_LOAD'
rpSupportSetName = 'RP_SUPPORT'

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def indices_to_mask(indices):
    indices = sorted(list(set(indices)))
    if len(indices) == 0:
        raise RuntimeError('Empty index list.')

    nWords = indices[-1] // 32 + 1
    words = [0] * nWords

    for idx in indices:
        wordIndex = idx // 32
        bitIndex = idx % 32
        words[wordIndex] = words[wordIndex] | (1 << bitIndex)

    return '[#' + ' #'.join(['%x' % w for w in words]) + ' ]'


def faces_from_indices(faceArray, indices):
    mask = indices_to_mask(indices)
    return faceArray.getSequenceFromMask(mask=(mask,))


def faces_by_point(faceArray, check):
    indices = []

    for f in faceArray:
        x, y, z = f.pointOn[0]
        if check(x, y, z):
            indices.append(f.index)

    if len(indices) == 0:
        return ()

    return faces_from_indices(faceArray, indices)


def require_instance_face_set(instance, setName, description):
    """Return a named part face set inherited by the assembly instance."""
    if setName not in instance.sets.keys():
        raise RuntimeError(
            'Required %s set %s is missing on instance %s. '
            'Run the corresponding part-generation script first.'
            % (description, setName, instance.name)
        )

    faces = instance.sets[setName].faces
    if len(faces) == 0:
        raise RuntimeError('%s set %s contains no faces.' % (description, setName))

    return faces


def nodes_by_point(nodeArray, check):
    nodes = []

    for n in nodeArray:
        x, y, z = n.coordinates
        if check(x, y, z):
            nodes.append(n)

    return tuple(nodes)


def nearest_node(nodes, target):
    if len(nodes) == 0:
        raise RuntimeError('No nodes available near slip measurement point.')

    tx, ty, tz = target
    bestNode = None
    bestDistance2 = None

    for n in nodes:
        x, y, z = n.coordinates
        distance2 = (x - tx) ** 2 + (y - ty) ** 2 + (z - tz) ** 2

        if bestDistance2 is None or distance2 < bestDistance2:
            bestDistance2 = distance2
            bestNode = n

    return bestNode


def near_stud_hole(x, y, z):
    near1 = (abs(x - HOLE_X) <= 14.0 and abs(z - HOLE1_Z) <= 14.0)
    near2 = (abs(x - HOLE_X) <= 14.0 and abs(z - HOLE2_Z) <= 14.0)
    return near1 or near2


def delete_assembly_object(name):
    if name in a.features.keys():
        try:
            del a.features[name]
        except:
            pass

    if name in a.surfaces.keys():
        try:
            del a.surfaces[name]
        except:
            pass

    if name in a.sets.keys():
        try:
            del a.sets[name]
        except:
            pass


def make_face_set(name, faces):
    if len(faces) == 0:
        raise RuntimeError('Face set %s has no faces.' % name)

    delete_assembly_object(name)

    a.Set(
        name=name,
        faces=faces
    )

    return a.sets[name]


def make_surface(name, faces):
    if len(faces) == 0:
        raise RuntimeError('Surface %s has no faces.' % name)

    delete_assembly_object(name)

    try:
        a.Surface(
            name=name,
            side1Faces=faces
        )
    except:
        delete_assembly_object(name)
        a.Surface(
            name=name,
            side2Faces=faces
        )

    return a.surfaces[name]


def make_node_set(name, nodes):
    delete_assembly_object(name)

    if len(nodes) == 0:
        print('Warning: node set %s has no nodes and will not be created.' % name)
        return None

    a.Set(
        name=name,
        nodes=nodes
    )

    return a.sets[name]


def make_instance_node_set_from_labels(name, instance, labels):
    delete_assembly_object(name)

    labels = tuple(labels)

    if len(labels) == 0:
        print('Warning: node set %s has no nodes and will not be created.' % name)
        return None

    try:
        a.SetFromNodeLabels(
            name=name,
            nodeLabels=((instance.name, labels),)
        )
    except:
        nodeSeq = instance.nodes.sequenceFromLabels(labels=labels)
        a.Set(
            name=name,
            nodes=nodeSeq
        )

    return a.sets[name]


def create_or_replace_rp(featureName, setName, point):
    delete_assembly_object(setName)

    if featureName in a.features.keys():
        del a.features[featureName]

    rpFeature = a.ReferencePoint(point=point)
    a.features.changeKey(
        fromName=rpFeature.name,
        toName=featureName
    )

    rp = a.referencePoints[rpFeature.id]

    a.Set(
        name=setName,
        referencePoints=(rp,)
    )

    return a.sets[setName]


# ------------------------------------------------------------
# 1. Steel-UHPC interface surface
# Steel contact surface: y-maximum x-z plane of steel beam
# ------------------------------------------------------------

steelCandidateFaces = steelInst.faces.getByBoundingBox(
    xMin=150.0,
    yMin=-250.0,
    zMin=50.0,
    xMax=320.0,
    yMax=-19.0,
    zMax=730.0
)

if len(steelCandidateFaces) == 0:
    raise RuntimeError('No candidate steel interface faces found.')

steelYMax = max([f.pointOn[0][1] for f in steelCandidateFaces])

steelInterfaceFaces = faces_by_point(
    steelInst.faces,
    lambda x, y, z:
        abs(y - steelYMax) <= TOL and
        150.0 <= x <= 320.0 and
        50.0 <= z <= 730.0 and
        not near_stud_hole(x, y, z)
)

make_face_set(setSteelInterfaceName, steelInterfaceFaces)
make_surface(surfSteelInterfaceName, steelInterfaceFaces)

# ------------------------------------------------------------
# 2. Concrete-UHPC interface surface
# Concrete contact surface: y-min face around steel interface
# ------------------------------------------------------------

concreteInterfaceFaces = faces_by_point(
    concreteInst.faces,
    lambda x, y, z:
        abs(y - Y_INTERFACE) <= TOL and
        150.0 <= x <= 320.0 and
        50.0 <= z <= 630.0 and
        not near_stud_hole(x, y, z)
)

make_face_set(setConcreteInterfaceName, concreteInterfaceFaces)
make_surface(surfConcreteInterfaceName, concreteInterfaceFaces)

# ------------------------------------------------------------
# 3. Stud contact surface from the named part-level face set
# ------------------------------------------------------------

studFaces = require_instance_face_set(
    steelInst,
    studSourceFaceSetName,
    'stud contact'
)

make_face_set(setStudFacesName, studFaces)
make_surface(surfStudName, studFaces)

# ------------------------------------------------------------
# 4. Concrete-hole contact surface from the named part-level face set
# ------------------------------------------------------------

holeFaces = require_instance_face_set(
    concreteInst,
    holeSourceFaceSetName,
    'concrete-hole contact'
)

make_face_set(setHoleFacesName, holeFaces)
make_surface(surfHoleName, holeFaces)

# ------------------------------------------------------------
# 5. Steel top loading surface
# Steel loading end face: z maximum end
# ------------------------------------------------------------

steelTopFaces = faces_by_point(
    steelInst.faces,
    lambda x, y, z:
        abs(z - Z_STEEL_MAX) <= TOL
)

make_face_set(setSteelLoadName, steelTopFaces)
make_surface(surfSteelLoadName, steelTopFaces)

# ------------------------------------------------------------
# 6. Concrete bottom support surface
# ------------------------------------------------------------

concreteBottomFaces = faces_by_point(
    concreteInst.faces,
    lambda x, y, z:
        abs(z - Z_CONCRETE_MIN) <= TOL
)

make_face_set(setConcreteSupportName, concreteBottomFaces)
make_surface(surfConcreteSupportName, concreteBottomFaces)

# ------------------------------------------------------------
# 7. X symmetry sets
# ------------------------------------------------------------

xSymConcreteFaces = faces_by_point(
    concreteInst.faces,
    lambda x, y, z:
        abs(x - X_SYMM) <= TOL
)

if len(xSymConcreteFaces) > 0:
    make_face_set(setXSymConcreteName, xSymConcreteFaces)

xSymSteelFaces = faces_by_point(
    steelInst.faces,
    lambda x, y, z:
        abs(x - X_SYMM) <= TOL
)

if len(xSymSteelFaces) > 0:
    make_face_set(setXSymSteelName, xSymSteelFaces)

xSymRebarNodes = rebarInst.nodes.getByBoundingBox(
    xMin=X_SYMM - TOL,
    yMin=-1.0e6,
    zMin=-1.0e6,
    xMax=X_SYMM + TOL,
    yMax=1.0e6,
    zMax=1.0e6
)

make_node_set(setXSymRebarName, xSymRebarNodes)

# ------------------------------------------------------------
# 8. Slip measurement node sets
# Interface slip is extracted as U3(steel node) - U3(concrete node).
# The point is placed between the two studs and away from hole contact.
# ------------------------------------------------------------

steelSlipCandidateNodes = nodes_by_point(
    steelInst.nodes,
    lambda x, y, z:
        abs(y - steelYMax) <= TOL and
        150.0 <= x <= 320.0 and
        50.0 <= z <= 630.0 and
        not near_stud_hole(x, y, z)
)

concreteSlipCandidateNodes = nodes_by_point(
    concreteInst.nodes,
    lambda x, y, z:
        abs(y - Y_INTERFACE) <= TOL and
        150.0 <= x <= 320.0 and
        50.0 <= z <= 630.0 and
        not near_stud_hole(x, y, z)
)

slipSteelNode = nearest_node(
    steelSlipCandidateNodes,
    (SLIP_POINT_X, steelYMax, SLIP_POINT_Z)
)

slipConcreteNode = nearest_node(
    concreteSlipCandidateNodes,
    (SLIP_POINT_X, Y_INTERFACE, SLIP_POINT_Z)
)

make_instance_node_set_from_labels(
    setSlipSteelNodeName,
    steelInst,
    (slipSteelNode.label,)
)

make_instance_node_set_from_labels(
    setSlipConcreteNodeName,
    concreteInst,
    (slipConcreteNode.label,)
)

# ------------------------------------------------------------
# 9. Reference points for loading and support
# ------------------------------------------------------------

create_or_replace_rp(
    featureName=rpLoadFeatureName,
    setName=rpLoadSetName,
    point=(235.0, -85.0, Z_STEEL_MAX)
)

create_or_replace_rp(
    featureName=rpSupportFeatureName,
    setName=rpSupportSetName,
    point=(150.0, 55.0, Z_CONCRETE_MIN)
)

# ------------------------------------------------------------
# Done
# ------------------------------------------------------------

a.regenerate()

print('Done: all required sets, surfaces, and reference points were created.')
print('Steel interface y-max plane: %.6f' % steelYMax)

print('%s faces: %d' % (setSteelInterfaceName, len(steelInterfaceFaces)))
print('%s faces: %d' % (setConcreteInterfaceName, len(concreteInterfaceFaces)))
print('%s faces: %d' % (setStudFacesName, len(studFaces)))
print('%s faces: %d' % (setHoleFacesName, len(holeFaces)))
print('%s faces: %d' % (setSteelLoadName, len(steelTopFaces)))
print('%s faces: %d' % (setConcreteSupportName, len(concreteBottomFaces)))
print('%s faces: %d' % (setXSymConcreteName, len(xSymConcreteFaces)))
print('%s faces: %d' % (setXSymSteelName, len(xSymSteelFaces)))
print('%s nodes: %d' % (setXSymRebarName, len(xSymRebarNodes)))
print('%s node label: %d, coord: %s' % (
    setSlipSteelNodeName,
    slipSteelNode.label,
    slipSteelNode.coordinates
))
print('%s node label: %d, coord: %s' % (
    setSlipConcreteNodeName,
    slipConcreteNode.label,
    slipConcreteNode.coordinates
))

print('Created sets:')
print('  %s' % setSteelInterfaceName)
print('  %s' % setConcreteInterfaceName)
print('  %s' % setStudFacesName)
print('  %s' % setHoleFacesName)
print('  %s' % setSteelLoadName)
print('  %s' % setConcreteSupportName)
print('  %s' % setXSymConcreteName)
print('  %s' % setXSymSteelName)
print('  %s' % setXSymRebarName)
print('  %s' % setSlipSteelNodeName)
print('  %s' % setSlipConcreteNodeName)
print('  %s' % rpLoadSetName)
print('  %s' % rpSupportSetName)

print('Created surfaces:')
print('  %s' % surfSteelInterfaceName)
print('  %s' % surfConcreteInterfaceName)
print('  %s' % surfStudName)
print('  %s' % surfHoleName)
print('  %s' % surfSteelLoadName)
print('  %s' % surfConcreteSupportName)
