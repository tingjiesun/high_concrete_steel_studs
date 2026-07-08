# -*- coding: utf-8 -*-
from odbAccess import openOdb
import os
import csv

# ============================================================
# User settings
# ============================================================

ODB_PATH = r'D:\temp\Job-2.odb'
STEP_NAME = 'Step-Pushout-Explicit'

OUT_DIR = os.path.dirname(ODB_PATH)
OUT_CSV = os.path.join(OUT_DIR, 'U3_RF3_data.csv')
OUT_PNG = os.path.join(OUT_DIR, 'U3_RF3_curve.png')

# x-axis and y-axis settings
X_MIN = 0.0
X_MAX = 5.0

# y = abs(RF3) / 1000 / 2
RF3_SCALE = 1000.0 * 2.0

# ============================================================
# Read U3 and RF3 from ODB history output
# ============================================================

odb = openOdb(ODB_PATH, readOnly=True)

if STEP_NAME not in odb.steps.keys():
    odb.close()
    raise RuntimeError('Step not found: %s' % STEP_NAME)

step = odb.steps[STEP_NAME]

target_region = None
target_region_name = None

for region_name, region in step.historyRegions.items():
    keys = region.historyOutputs.keys()

    if 'U3' in keys and 'RF3' in keys:
        if 'RP_LOAD' in region_name.upper():
            target_region = region
            target_region_name = region_name
            break

        if target_region is None:
            target_region = region
            target_region_name = region_name

if target_region is None:
    odb.close()
    raise RuntimeError('Cannot find history outputs U3 and RF3 in odb.')

u3_data = target_region.historyOutputs['U3'].data
rf3_data = target_region.historyOutputs['RF3'].data

rows = []

for (t1, u3), (t2, rf3) in zip(u3_data, rf3_data):
    rows.append((t1, u3, rf3))

odb.close()

# ============================================================
# Export CSV: only time, U3, RF3
# ============================================================

with open(OUT_CSV, 'w') as f:
    writer = csv.writer(f)
    writer.writerow([
        'time',
        'U3',
        'RF3'
    ])
    writer.writerows(rows)

# ============================================================
# Plot PNG
# x = abs(U3), fixed 0-5
# y = abs(RF3) / 1000 / 2
# ============================================================

xs = []
ys = []

with open(OUT_CSV, 'r') as f:
    reader = csv.DictReader(f)

    for row in reader:
        x = abs(float(row['U3']))
        y = abs(float(row['RF3'])) / RF3_SCALE

        if X_MIN <= x <= X_MAX:
            xs.append(x)
            ys.append(y)

if len(xs) == 0:
    raise RuntimeError('No data found in x range %.3f-%.3f.' % (X_MIN, X_MAX))

Y_MIN = 0.0
Y_MAX = max(ys)

if Y_MAX <= 0.0:
    Y_MAX = 1.0

# Add a little headroom
Y_MAX = Y_MAX * 1.08

# Try matplotlib first. If unavailable in Abaqus Python, fallback to SVG.
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.figure(figsize=(8.5, 5.5), dpi=200)
    plt.plot(xs, ys, color='#1f77b4', linewidth=2.0)

    plt.xlim(X_MIN, X_MAX)
    plt.ylim(Y_MIN, Y_MAX)

    plt.xlabel('Slip |U3| (mm)')
    plt.ylabel('|RF3| / 1000 / 2 (kN)')
    plt.title('U3-RF3 curve')

    plt.grid(True, linestyle='--', linewidth=0.6, alpha=0.5)

    peak_index = ys.index(max(ys))
    peak_x = xs[peak_index]
    peak_y = ys[peak_index]

    plt.scatter([peak_x], [peak_y], color='red', s=25, zorder=5)
    plt.annotate(
        'Peak = %.3f kN\nU3 = %.3f mm' % (peak_y, peak_x),
        xy=(peak_x, peak_y),
        xytext=(peak_x + 0.15, peak_y * 0.92),
        fontsize=9,
        arrowprops=dict(arrowstyle='->', color='red', linewidth=0.8)
    )

    plt.tight_layout()
    plt.savefig(OUT_PNG)
    plt.close()

    print('Export finished.')
    print('History region: %s' % target_region_name)
    print('CSV: %s' % OUT_CSV)
    print('PNG: %s' % OUT_PNG)
    print('Peak y = %.6g' % peak_y)
    print('Peak x = %.6g' % peak_x)

except Exception as e:
    raise RuntimeError(
        'PNG generation failed. Abaqus Python may not have matplotlib. '
        'Error: %s' % str(e)
    )