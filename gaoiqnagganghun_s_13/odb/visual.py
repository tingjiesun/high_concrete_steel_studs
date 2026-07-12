# -*- coding: utf-8 -*-
from odbAccess import openOdb
import os
import csv

# ============================================================
# User settings
# ============================================================

ODB_PATH = r'D:\temp\Job-3.odb'
STEP_NAME = 'Step-Pushout-Explicit'

OUT_DIR = os.path.dirname(ODB_PATH)
OUT_CSV = os.path.join(OUT_DIR, 'U3_RF3_data.csv')
OUT_PNG = os.path.join(OUT_DIR, 'U3_RF3_curve.png')

# x-axis and y-axis settings
X_MIN = 0.0
X_MAX = 6.0

# y = abs(RF3) / 1000 / 2
RF3_SCALE = 1000.0 * 2.0

# ============================================================
# Read interface slip and RF3 from ODB history output
# ============================================================

odb = openOdb(ODB_PATH, readOnly=True)

if STEP_NAME not in odb.steps.keys():
    odb.close()
    raise RuntimeError('Step not found: %s' % STEP_NAME)

step = odb.steps[STEP_NAME]

def history_region_text(region_name, region):
    text = region_name
    try:
        text = text + ' ' + region.description
    except:
        pass
    return text.upper()


def output_keys(region):
    return region.historyOutputs.keys()


def find_rf3_region(step):
    candidates = []

    for region_name, region in step.historyRegions.items():
        if 'RF3' in output_keys(region):
            candidates.append((region_name, region))

    if len(candidates) == 0:
        return None, None

    for region_name, region in candidates:
        text = history_region_text(region_name, region)
        if 'RP_LOAD' in text or 'RP' in text:
            return region_name, region

    if len(candidates) == 1:
        return candidates[0]

    return None, None


def find_u3_region(step, tokens):
    matches = []

    for region_name, region in step.historyRegions.items():
        keys = output_keys(region)

        if 'U3' not in keys or 'RF3' in keys:
            continue

        text = history_region_text(region_name, region)
        matched = True

        for token in tokens:
            if token.upper() not in text:
                matched = False
                break

        if matched:
            matches.append((region_name, region))

    if len(matches) == 1:
        return matches[0]

    return None, None


def find_slip_u3_regions(step):
    steel_name, steel_region = find_u3_region(step, ('SLIP', 'STEEL'))
    concrete_name, concrete_region = find_u3_region(step, ('SLIP', 'CONCRETE'))

    if steel_region is not None and concrete_region is not None:
        return steel_name, steel_region, concrete_name, concrete_region

    u3_candidates = []

    for region_name, region in step.historyRegions.items():
        keys = output_keys(region)

        if 'U3' in keys and 'RF3' not in keys:
            u3_candidates.append((region_name, region))

    if steel_region is not None and concrete_region is None:
        remaining = []
        for region_name, region in u3_candidates:
            if region_name != steel_name:
                remaining.append((region_name, region))

        if len(remaining) == 1:
            return steel_name, steel_region, remaining[0][0], remaining[0][1]

    if concrete_region is not None and steel_region is None:
        remaining = []
        for region_name, region in u3_candidates:
            if region_name != concrete_name:
                remaining.append((region_name, region))

        if len(remaining) == 1:
            return remaining[0][0], remaining[0][1], concrete_name, concrete_region

    if len(u3_candidates) == 2:
        return (
            u3_candidates[0][0],
            u3_candidates[0][1],
            u3_candidates[1][0],
            u3_candidates[1][1],
        )

    return None, None, None, None


def history_candidates_text(step):
    lines = []

    for region_name, region in step.historyRegions.items():
        lines.append('%s: %s' % (region_name, output_keys(region)))

    return '\n'.join(lines)


rf3_region_name, rf3_region = find_rf3_region(step)

if rf3_region is None:
    odb.close()
    raise RuntimeError(
        'Cannot find RF3 history output in odb. Available history outputs:\n%s'
        % history_candidates_text(step)
    )

steel_region_name, steel_region, concrete_region_name, concrete_region = find_slip_u3_regions(step)

if steel_region is None or concrete_region is None:
    odb.close()
    raise RuntimeError(
        'Cannot find two interface U3 history outputs in odb. '
        'Run interaction_load/2_interaction_jihe.py and interaction_load/3_load_interaction.py first. '
        'Available history outputs:\n%s'
        % history_candidates_text(step)
    )

rf3_data = rf3_region.historyOutputs['RF3'].data
u3_steel_data = steel_region.historyOutputs['U3'].data
u3_concrete_data = concrete_region.historyOutputs['U3'].data

rows = []
count = min(len(rf3_data), len(u3_steel_data), len(u3_concrete_data))

for i in range(count):
    t_rf3, rf3 = rf3_data[i]
    t_steel, u3_steel = u3_steel_data[i]
    t_concrete, u3_concrete = u3_concrete_data[i]
    slip = u3_steel - u3_concrete

    rows.append((t_rf3, slip, u3_steel, u3_concrete, rf3))

odb.close()

# ============================================================
# Export CSV
# U3 means the relative interface slip: U3_steel - U3_concrete.
# ============================================================

with open(OUT_CSV, 'w') as f:
    writer = csv.writer(f)
    writer.writerow([
        'time',
        'U3',
        'U3_steel',
        'U3_concrete',
        'RF3'
    ])
    writer.writerows(rows)

# ============================================================
# Plot PNG
# x = abs(U3_steel - U3_concrete), fixed 0-5
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

    plt.xlabel('Interface slip |U3_steel - U3_concrete| (mm)')
    plt.ylabel('|RF3| / 1000 / 2 (kN)')
    plt.title('Interface slip-RF3 curve')

    plt.grid(True, linestyle='--', linewidth=0.6, alpha=0.5)

    peak_index = ys.index(max(ys))
    peak_x = xs[peak_index]
    peak_y = ys[peak_index]

    plt.scatter([peak_x], [peak_y], color='red', s=25, zorder=5)
    plt.annotate(
        'Peak = %.3f kN\nSlip = %.3f mm' % (peak_y, peak_x),
        xy=(peak_x, peak_y),
        xytext=(peak_x + 0.15, peak_y * 0.92),
        fontsize=9,
        arrowprops=dict(arrowstyle='->', color='red', linewidth=0.8)
    )

    plt.tight_layout()
    plt.savefig(OUT_PNG)
    plt.close()

    print('Export finished.')
    print('RF3 history region: %s' % rf3_region_name)
    print('Steel U3 history region: %s' % steel_region_name)
    print('Concrete U3 history region: %s' % concrete_region_name)
    print('CSV: %s' % OUT_CSV)
    print('PNG: %s' % OUT_PNG)
    print('Peak y = %.6g' % peak_y)
    print('Peak x = %.6g' % peak_x)

except Exception as e:
    raise RuntimeError(
        'PNG generation failed. Abaqus Python may not have matplotlib. '
        'Error: %s' % str(e)
    )
