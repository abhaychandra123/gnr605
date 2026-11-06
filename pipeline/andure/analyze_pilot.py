"""Reproduce the analysis of the two uploaded CSVs from their parsed extract."""
import csv
import json
import tempfile
from pathlib import Path
from audit_export import audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/andure'
data = json.loads((OUT / 'pilot_input_extract.json').read_text())
rows = data['pilot']
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'parsed_upload.csv'
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    checks = audit(path)
checks['input'] = 'pilot_input_extract.json:pilot (parsed uploaded CSV contents)'
assert len(rows) == 10
assert {(r['date'], int(r['min_ndvi_years'])) for r in rows} == {
    (f'{y}-10', n) for y in range(2020, 2025) for n in (12, 15)}
assert not checks['errors'], checks['errors']
history = data['reference']
assert len(history) == 19
assert {int(float(r['year'])) for r in history} == set(range(2001, 2020))
assert all(0 <= float(r[k]) <= 1 for r in history
           for k in ('ndvi_valid_fraction', 'lst_valid_fraction'))
by = {(r['date'], int(r['min_ndvi_years'])): r for r in rows}
table = []
for year in range(2020, 2025):
    a, b = by[(f'{year}-10', 12)], by[(f'{year}-10', 15)]
    assert float(a['valid_area_km2']) >= float(b['valid_area_km2'])
    assert a['rain_mm'] == b['rain_mm']
    assert a['rain_3month_mm'] == b['rain_3month_mm']
    table.append(dict(year=year, coverage12_pct=100*float(a['valid_fraction']),
                      coverage15_pct=100*float(b['valid_fraction']),
                      vhi12=float(a['vhi']), vhi15=float(b['vhi']),
                      rain_oct_mm=float(a['rain_mm']), rain_aug_oct_mm=float(a['rain_3month_mm'])))
(OUT / 'pilot_upload_audit.json').write_text(json.dumps(checks, indent=2)+'\n')
with (OUT / 'pilot_comparison.csv').open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=table[0].keys())
    writer.writeheader()
    writer.writerows(table)
print(json.dumps({'comparison': table, 'formula_max_abs_error': checks['formula_max_abs_error'],
                  'audit_errors': checks['errors'], 'warnings': checks['warnings'],
                  'worst_historical_ndvi': sorted(history, key=lambda r: float(r['ndvi_valid_fraction']))[:4]}, indent=2))

# Plot observations without trend lines: footprints vary and coverage is inadequate.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)
for requirement, color, offset in [(12, '#087e8b', -0.09), (15, '#b04a35', 0.09)]:
    axes[0].scatter([r['year']+offset for r in table],
                    [r[f'coverage{requirement}_pct'] for r in table],
                    label=f'At least {requirement} NDVI years', color=color, s=55)
axes[0].set(title='October VHI coverage', ylabel='Percent of provisional district',
            xticks=list(range(2020, 2025)), ylim=(0, 100))
axes[0].legend(fontsize=8)
axes[1].bar([int(float(r['year'])) for r in history],
            [100*float(r['ndvi_valid_fraction']) for r in history], color='#526a8a')
axes[1].set(title='Historical October NDVI coverage', ylabel='Percent passing existing QA',
            xticks=[2001, 2005, 2010, 2015, 2019], ylim=(0, 100))
for ax in axes:
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)
fig.suptitle('Start-date composites: coverage limits interpretation', fontsize=13)
fig.savefig(OUT / 'pilot_coverage.png', dpi=160)
plt.close(fig)
