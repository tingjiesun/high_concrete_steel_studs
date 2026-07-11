# -*- coding: mbcs -*-
#
# Abaqus/CAE Release 2025 replay file
# Internal Version: 2024_09_20-21.00.46 RELr427 198590
# Run by suntj on Tue Jul  7 11:13:17 2026
#

# from driverUtils import executeOnCaeGraphicsStartup
# executeOnCaeGraphicsStartup()
#: Executing "onCaeGraphicsStartup()" in the site directory ...
from abaqus import *
from abaqusConstants import *
session.Viewport(name='Viewport: 1', origin=(1.71549, 1.71296), width=252.521, 
    height=169.926)
session.viewports['Viewport: 1'].makeCurrent()
from driverUtils import executeOnCaeStartup
executeOnCaeStartup()
#: Executing "onCaeStartup()" in the home directory ...
#: =======================================================
#: Abaqus MCP Plugin v4.0.0 (File IPC)
#: =======================================================
#: Home:   C:\Users\suntj\.abaqus-mcp
#: Abaqus: True
#: Start:  mcp_start()     (background, recommended)
#:         mcp_loop()      (blocking)
#: Stop:   mcp_stop()
#: Status: mcp_status()
#: =======================================================
execfile('_validate_parts_only.py', __main__.__dict__)
#: 模型 "HSS_Stud" 已创建.
#: Steel beam with studs created successfully.
#: Final part: SteelBeam_With_Studs
#: No final assembly instance was kept.
#: Studs are on y-min outside x-z face.
#: Stud direction: negative Y
#: Stud 1 base point: x = 40.0, y = 0.0, z = 550.0
#: Stud 2 base point: x = 40.0, y = 0.0, z = 300.0
#: Stud segments: D19-L5, D13-L67, D22-L8
#: Final concrete plate created.
#: Only final part kept: ConcretePlate_Final
#: No final assembly instance was kept.
#: Concrete size: 300.0 x 150.0 x 650.0
#: Hole point 1: x = 260.0, z = 515.0
#: Hole point 2: x = 260.0, z = 265.0
#: Hole segments: D19-L5, D13-L67, D22-L8
#: 模型数据库已保存到 "D:\abaqus_py\gaoqiang_ganghun\HSS_Stud.cae".
#: Created model: HSS_Stud
#: x_all: [0.0, 90.0, 180.0, 270.0]
#: x_cage: [0.0, 90.0, 180.0]
#: y_all: [0.0, 110.0]
#: z_all: [0.0, 100.0, 250.0, 400.0, 550.0]
#: Node count: 40
#: T3D2 element count: 69
#:   x-direction element count: 30
#:   z-direction element count: 24
#:   y-connector element count: 15
#: No assembly instance was created.
#: Saved CAE file: HSS_Stud.cae
#: Validation passed: all required parts exist and assembly has no instances.
print('RT script done')
#: RT script done
