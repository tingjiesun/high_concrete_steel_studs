# -*- coding: utf-8 -*-

from odbAccess import openOdb
import csv
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# ============================================================
# User settings
# ============================================================

ODB_PATH = r'D:\temp\Job-3.odb'
STEP_NAME = 'Step-Pushout-Explicit'

# Recommended quasi-static criterion for the main loading phase.
RATIO_LIMIT = 0.05

# Do not judge the start/end transition, where internal energy is close to 0
# or the actuator is finishing its ramp.
CHECK_START_FRACTION = 0.05
CHECK_END_FRACTION = 0.95

OUT_DIR = os.path.dirname(ODB_PATH)
OUT_CSV = os.path.join(OUT_DIR, 'ALLKE_ALLIE_ratio.csv')
OUT_PNG = os.path.join(OUT_DIR, 'ALLKE_ALLIE_ratio.png')


def find_energy_region(step):
    """Find one history region containing both global energy outputs."""
    matches = []

    for region_name, region in step.historyRegions.items():
        keys = region.historyOutputs.keys()
        if 'ALLKE' in keys and 'ALLIE' in keys:
            matches.append((region_name, region))

    if len(matches) == 0:
        raise RuntimeError(
            'Cannot find ALLKE and ALLIE in the ODB history output. '
            'Run 3_load_interaction.py before submitting the job.'
        )

    for region_name, region in matches:
        text = (region_name + ' ' + region.description).upper()
        if 'ASSEMBLY' in text or 'MODEL' in text:
            return region_name, region

    return matches[0]


def interpolate_history(data, time_value, start_index):
    """Linearly interpolate a history output at one time point."""
    index = start_index

    while index < len(data) - 2 and data[index + 1][0] < time_value:
        index += 1

    time_1, value_1 = data[index]
    time_2, value_2 = data[index + 1]

    if time_2 == time_1:
        return value_1, index

    fraction = (time_value - time_1) / (time_2 - time_1)
    return value_1 + fraction * (value_2 - value_1), index


def align_energy_histories(ke_data, ie_data):
    """Use ALLKE time points and interpolate ALLIE as needed."""
    rows = []
    ie_index = 0

    for time_value, kinetic_energy in ke_data:
        if time_value < ie_data[0][0] or time_value > ie_data[-1][0]:
            continue

        internal_energy, ie_index = interpolate_history(
            ie_data, time_value, ie_index
        )
        rows.append((time_value, kinetic_energy, internal_energy))

    return rows


if not os.path.isfile(ODB_PATH):
    raise RuntimeError('ODB file not found: %s' % ODB_PATH)

odb = openOdb(ODB_PATH, readOnly=True)

if STEP_NAME not in odb.steps.keys():
    odb.close()
    raise RuntimeError('Step not found: %s' % STEP_NAME)

step = odb.steps[STEP_NAME]
region_name, region = find_energy_region(step)

ke_data = region.historyOutputs['ALLKE'].data
ie_data = region.historyOutputs['ALLIE'].data

if len(ke_data) < 2 or len(ie_data) < 2:
    odb.close()
    raise RuntimeError('ALLKE/ALLIE history output has too few data points.')

rows = align_energy_histories(ke_data, ie_data)
odb.close()

if len(rows) == 0:
    raise RuntimeError('No overlapping ALLKE and ALLIE history data found.')

final_time = rows[-1][0]
start_time = CHECK_START_FRACTION * final_time
end_time = CHECK_END_FRACTION * final_time
max_internal_energy = max([abs(row[2]) for row in rows])
internal_energy_floor = max(1.0e-12, max_internal_energy * 1.0e-8)

csv_rows = []
check_ratios = []

for time_value, kinetic_energy, internal_energy in rows:
    if abs(internal_energy) <= internal_energy_floor:
        ratio = None
    else:
        ratio = abs(kinetic_energy / internal_energy)

    in_check_window = (
        ratio is not None and
        time_value >= start_time and
        time_value <= end_time
    )

    if in_check_window:
        check_ratios.append(ratio)

    csv_rows.append((
        time_value,
        kinetic_energy,
        internal_energy,
        ratio,
        ratio * 100.0 if ratio is not None else None,
        int(in_check_window),
    ))

if len(check_ratios) == 0:
    raise RuntimeError('No valid energy-ratio points in the check window.')

max_ratio = max(check_ratios)
mean_ratio = sum(check_ratios) / len(check_ratios)
above_limit_count = len([ratio for ratio in check_ratios if ratio > RATIO_LIMIT])
pass_check = (above_limit_count == 0)

with open(OUT_CSV, 'w') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow([
        'time_s', 'ALLKE', 'ALLIE', 'abs_ALLKE_over_ALLIE',
        'ratio_percent', 'in_main_loading_check_window'
    ])
    writer.writerows(csv_rows)

times = []
ratio_percentages = []
for row in csv_rows:
    if row[3] is not None:
        times.append(row[0])
        ratio_percentages.append(row[4])

fig = plt.figure(figsize=(10, 6), dpi=160)
ax = fig.add_subplot(111)
ax.plot(
    times,
    ratio_percentages,
    color='#1f77b4',
    linewidth=1.5,
    label='abs(ALLKE / ALLIE)'
)
ax.axhline(
    y=RATIO_LIMIT * 100.0,
    color='#2e8b57',
    linestyle='--',
    linewidth=1.5,
    label='Recommended limit: %.1f%%' % (RATIO_LIMIT * 100.0)
)
ax.axvspan(
    start_time,
    end_time,
    color='#d9edf7',
    alpha=0.35,
    label='Main loading check window'
)
ax.set_xlabel('Step time (s)')
ax.set_ylabel('abs(ALLKE / ALLIE) (%)')
ax.set_title('Explicit quasi-static energy check')
ax.grid(True, linestyle='--', alpha=0.45)
ax.legend(loc='upper right')

status = 'PASS' if pass_check else 'FAIL'
status_color = '#2e8b57' if pass_check else '#b22222'
summary = (
    'Status: %s\n'
    'Max in check window: %.2f%%\n'
    'Mean in check window: %.2f%%\n'
    'Points above %.1f%%: %d / %d'
    % (
        status,
        max_ratio * 100.0,
        mean_ratio * 100.0,
        RATIO_LIMIT * 100.0,
        above_limit_count,
        len(check_ratios),
    )
)
ax.text(
    0.02,
    0.98,
    summary,
    transform=ax.transAxes,
    verticalalignment='top',
    color=status_color,
    bbox=dict(boxstyle='round', facecolor='white', edgecolor=status_color, alpha=0.92)
)

fig.tight_layout()
fig.savefig(OUT_PNG, bbox_inches='tight')

print('Energy history region: %s' % region_name)
print('CSV written: %s' % OUT_CSV)
print('Plot written: %s' % OUT_PNG)
print('Main loading check window: %.6g s to %.6g s' % (start_time, end_time))
print('Maximum abs(ALLKE/ALLIE): %.4f (%.2f%%)' % (
    max_ratio, max_ratio * 100.0
))
print('Mean abs(ALLKE/ALLIE): %.4f (%.2f%%)' % (
    mean_ratio, mean_ratio * 100.0
))
print('Points above %.1f%%: %d / %d' % (
    RATIO_LIMIT * 100.0, above_limit_count, len(check_ratios)
))
print('QUASI_STATIC_CHECK: %s' % status)
