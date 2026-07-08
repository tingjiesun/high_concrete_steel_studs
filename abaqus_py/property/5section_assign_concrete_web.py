from abaqus import mdb
from abaqusConstants import *
import regionToolset

modelName = 'HSS_Stud'
partName = 'ConcretePlate_Final'

# 改成你已经定义好的 UHPC 材料名称
materialName = 'UHPC_CDP'

sectionName = 'ConcretePlate_UHPC_Section'

model = mdb.models[modelName]
p = model.parts[partName]

# 如果同名截面已存在，先删除，便于重复运行
if sectionName in model.sections.keys():
    del model.sections[sectionName]

# 创建混凝土板实体截面
model.HomogeneousSolidSection(
    name=sectionName,
    material=materialName,
    thickness=None
)

# 将该截面赋给 ConcretePlate_Final 的全部实体区域
region = regionToolset.Region(cells=p.cells[:])

p.SectionAssignment(
    region=region,
    sectionName=sectionName,
    offset=0.0,
    offsetType=MIDDLE_SURFACE,
    offsetField='',
    thicknessAssignment=FROM_SECTION
)

print('完成：已将材料 %s 通过截面 %s 赋给部件 %s。' % (
    materialName, sectionName, partName
))