# -*- coding: utf-8 -*-
# Build steel rebar cage.
# Abaqus/CAE command script for the T3D2 rebar cage in model HSS_MODEL_s_19.
# Run with:
#   abaqus cae noGUI=steel_longzi.py
# or in Abaqus/CAE: File -> Run Script

from abaqus import mdb
from abaqusConstants import *
import mesh
import regionToolset


# -----------------------------
# Geometry parameters
# -----------------------------
MODEL_NAME = 'HSS_MODEL_s_19'
PART_NAME = 'RebarCage'

LX = 270.0
LY = 110.0

# x positions used to split the x-direction bars and share nodes.
x_all = [0.0, 90.0, 180.0, 270.0]

# Connector positions described as c1, c2, c3 and y-direction bars.
x_cage = [0.0, 90.0, 180.0]

y_all = [0.0, LY]

z_spacing = [100.0, 150.0, 150.0, 150.0]
z_all = [0.0]
for dz in z_spacing:
    z_all.append(z_all[-1] + dz)

# Replace this with pi*d*d/4 if the rebar diameter d is known.
BAR_AREA = 1.0


# -----------------------------
# Model and orphan mesh part
# -----------------------------
if MODEL_NAME in mdb.models.keys():
    model = mdb.models[MODEL_NAME]
else:
    model = mdb.Model(name=MODEL_NAME)

assembly = model.rootAssembly
for feature_name in list(assembly.features.keys()):
    if feature_name.startswith(PART_NAME):
        del assembly.features[feature_name]

if PART_NAME in model.parts.keys():
    del model.parts[PART_NAME]

part = model.Part(
    name=PART_NAME,
    dimensionality=THREE_D,
    type=DEFORMABLE_BODY,
)

nodes = {}
element_keys = set()
x_elem_labels = []
z_elem_labels = []
y_elem_labels = []


def key(point):
    return tuple(round(float(v), 6) for v in point)


def get_node(point):
    k = key(point)
    if k not in nodes:
        nodes[k] = part.Node(coordinates=k)
    return nodes[k]


def add_t3d2(point_a, point_b, label_list):
    ka = key(point_a)
    kb = key(point_b)
    if ka == kb:
        return None

    get_node(ka)
    get_node(kb)

    ekey = tuple(sorted([ka, kb]))
    if ekey in element_keys:
        return None

    element = part.Element(nodes=(nodes[ka], nodes[kb]), elemShape=LINE2)
    element_keys.add(ekey)
    label_list.append(element.label)
    return element.label


def add_polyline(points, label_list):
    for i in range(len(points) - 1):
        add_t3d2(points[i], points[i + 1], label_list)


# -----------------------------
# 1) x-direction bars: a/b bars
#    z = 0, 100, 250, 400, 550
#    y = 0 and 110
# -----------------------------
for z in z_all:
    for y in y_all:
        add_polyline([(x, y, z) for x in x_all], x_elem_labels)


# -----------------------------
# 2) z-direction bars: c1/c2/c3
#    x = 0, 90, 180
#    y = 0 and 110
# -----------------------------
for x in x_cage:
    for y in y_all:
        add_polyline([(x, y, z) for z in z_all], z_elem_labels)


# -----------------------------
# 3) y-direction bars between a and b
#    x = 0, 90, 180
#    copied at all z levels
# -----------------------------
for z in z_all:
    for x in x_cage:
        add_t3d2((x, 0.0, z), (x, LY, z), y_elem_labels)


# -----------------------------
# Element type, material, and section
# -----------------------------
if len(part.nodes) != 40:
    raise RuntimeError('Expected 40 shared nodes, got %d.' % len(part.nodes))
if len(x_elem_labels) != 30:
    raise RuntimeError('Expected 30 x-direction T3D2 elements, got %d.' % len(x_elem_labels))
if len(z_elem_labels) != 24:
    raise RuntimeError('Expected 24 z-direction T3D2 elements, got %d.' % len(z_elem_labels))
if len(y_elem_labels) != 15:
    raise RuntimeError('Expected 15 y-connector T3D2 elements, got %d.' % len(y_elem_labels))
if len(part.elements) != 69:
    raise RuntimeError('Expected 69 T3D2 elements, got %d.' % len(part.elements))

all_elem_labels = x_elem_labels + z_elem_labels + y_elem_labels
all_node_labels = [node.label for node in part.nodes]

x_elements = part.elements.sequenceFromLabels(labels=tuple(x_elem_labels))
z_elements = part.elements.sequenceFromLabels(labels=tuple(z_elem_labels))
y_elements = part.elements.sequenceFromLabels(labels=tuple(y_elem_labels))
all_elements = part.elements.sequenceFromLabels(labels=tuple(all_elem_labels))
all_nodes = part.nodes.sequenceFromLabels(labels=tuple(all_node_labels))

part.Set(name='X_REBAR', elements=x_elements)
part.Set(name='Z_REBAR', elements=z_elements)
part.Set(name='Y_CONNECT_REBAR', elements=y_elements)
part.Set(name='ALL_REBAR', elements=all_elements)
part.Set(name='ALL_NODES', nodes=all_nodes)

model.Material(name='Steel')
model.materials['Steel'].Elastic(table=((200000.0, 0.3),))
model.TrussSection(name='RebarSection', material='Steel', area=BAR_AREA)

part.SectionAssignment(
    region=regionToolset.Region(elements=all_elements),
    sectionName='RebarSection',
)

elem_type = mesh.ElemType(elemCode=T3D2, elemLibrary=STANDARD)
part.setElementType(regions=(all_elements,), elemTypes=(elem_type,))

mdb.save()

print('Created model: %s' % MODEL_NAME)
print('x_all: %s' % x_all)
print('x_cage: %s' % x_cage)
print('y_all: %s' % y_all)
print('z_all: %s' % z_all)
print('Node count: %d' % len(part.nodes))
print('T3D2 element count: %d' % len(part.elements))
print('  x-direction element count: %d' % len(x_elem_labels))
print('  z-direction element count: %d' % len(z_elem_labels))
print('  y-connector element count: %d' % len(y_elem_labels))
print('No assembly instance was created.')
print('Saved current CAE file.')
