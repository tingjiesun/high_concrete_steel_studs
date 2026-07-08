from abaqus import mdb
from abaqusConstants import *
import regionToolset
import math

modelName = 'HSS_Stud'
partName = 'RebarCage'

materialName = 'HRB400_Rebar'
sectionName = 'Rebar_D10_TrussSection'

# HRB400 名义材料参数，单位 N-mm-MPa
E_REBAR = 200000.0
NU_REBAR = 0.30
FY_REBAR = 400.0

# 直径 10 mm 钢筋截面积
D_REBAR = 10.0
A_REBAR = math.pi * D_REBAR ** 2.0 / 4.0

model = mdb.models[modelName]
p = model.parts[partName]

# 删除同名材料和截面，便于重复运行
if materialName in model.materials.keys():
    del model.materials[materialName]

if sectionName in model.sections.keys():
    del model.sections[sectionName]

# 创建 HRB400 钢筋材料
mat = model.Material(name=materialName)
mat.Elastic(table=((E_REBAR, NU_REBAR),))

# 理想弹塑性：屈服应力 400 MPa，塑性应变 0
mat.Plastic(table=((FY_REBAR, 0.0),))

# 创建桁架截面，适用于 T3D2 单元
model.TrussSection(
    name=sectionName,
    material=materialName,
    area=A_REBAR
)

# 将截面赋给钢筋笼全部 wire/edge
region = regionToolset.Region(edges=p.edges[:])

p.SectionAssignment(
    region=region,
    sectionName=sectionName,
    offset=0.0,
    offsetType=MIDDLE_SURFACE,
    offsetField='',
    thicknessAssignment=FROM_SECTION
)

print('完成：已为钢筋笼 %s 定义 HRB400-D10 桁架截面。截面积 = %.6f mm^2' % (
    partName, A_REBAR
))