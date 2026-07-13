# -*- coding: utf-8 -*-
from odbAccess import openOdb
import os
import csv

# ============================================================
# User settings
# ============================================================

ODB_PATH = r'D:\temp\Job-4.odb'
STEP_NAME = 'Step-Pushout-Explicit'

OUT_DIR = os.path.dirname(ODB_PATH)
OUT_CSV = os.path.join(OUT_DIR, 'RP_U3_RF3_data.csv')
OUT_PNG = os.path.join(OUT_DIR, 'RP_U3_RF3_curve.png')

# x-axis and y-axis settings
X_MIN = 0.0
X_MAX = 6.0

# Same scale as visual.py:
# y = abs(RF3) / 1000 / 2
# If you want the total reaction force, change this to 1000.0.
RF3_SCALE = 1000.0 * 2.0

# ============================================================
# Read RP_LOAD U3 and RF3 from ODB history output
# ============================================================

odb = openOdb(ODB_PATH, readOnly=True)

if STEP_NAME not in odb.steps.keys():
    odb.close()
    raise RuntimeError('Step not found: %s' % STEP_NAME)

step = odb.steps[STEP_NAME]


def output_keys(region):
    return region.historyOutputs.keys()


def history_region_text(region_name, region):
    text = region_name
    try:
        text = text + ' ' + region.description
    except:
        pass
    return text.upper()


def history_candidates_text(step):
    lines = []

    for region_name, region in step.historyRegions.items():
        lines.append('%s: %s' % (region_name, output_keys(region)))

    return '\n'.join(lines)


def find_rp_u3_rf3_region(step):
    candidates = []

    for region_name, region in step.historyRegions.items():
        keys = output_keys(region)

        if 'U3' in keys and 'RF3' in keys:
            candidates.append((region_name, region))

    if len(candidates) == 0:
        return None, None

    for region_name, region in candidates:
        text = history_region_text(region_name, region)

        if 'RP_LOAD' in text:
            return region_name, region

    for region_name, region in candidates:
        text = history_region_text(region_name, region)

        if 'RP' in text:
            return region_name, region

    if len(candidates) == 1:
        return candidates[0]

    return None, None


target_region_name, target_region = find_rp_u3_rf3_region(step)

if target_region is None:
    odb.close()
    raise RuntimeError(
        'Cannot find RP_LOAD history outputs U3 and RF3 in odb. '
        'Run interaction_load/3_load_interaction.py again before submitting the job. '
        'Available history outputs:\n%s'
        % history_candidates_text(step)
    )

u3_data = target_region.historyOutputs['U3'].data
rf3_data = target_region.historyOutputs['RF3'].data

rows = []
count = min(len(u3_data), len(rf3_data))

for i in range(count):
    t_u3, u3 = u3_data[i]
    t_rf3, rf3 = rf3_data[i]

    rows.append((t_u3, u3, rf3))

odb.close()

# ============================================================
# Export CSV
# U3 is the displacement of RP_LOAD, not interface slip.
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
# x = abs(U3 at RP_LOAD), fixed 0-5
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

Y_MAX = Y_MAX * 1.08

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.figure(figsize=(8.5, 5.5), dpi=200)
    plt.plot(xs, ys, color='#1f77b4', linewidth=2.0)

    plt.xlim(X_MIN, X_MAX)
    plt.ylim(Y_MIN, Y_MAX)

    plt.xlabel('RP_LOAD displacement |U3| (mm)')
    plt.ylabel('|RF3| / 1000 / 2 (kN)')
    plt.title('RP_LOAD U3-RF3 curve')

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
