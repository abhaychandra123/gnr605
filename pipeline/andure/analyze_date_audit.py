"""Validate the user-exported date audit and write a reproducible comparison."""
import csv
import io
import json
import math
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/andure'


def main():
    source = json.loads((OUT / 'date_audit_input_extract.json').read_text())
    rows = list(csv.DictReader(io.StringIO(source['csv_text'])))
    errors = []
    years = [int(float(r['year'])) for r in rows]
    if years != list(range(2001, 2025)):
        errors.append('Expected exactly one ordered row per year, 2001–2024.')
    prior = json.loads((OUT / 'pilot_input_extract.json').read_text())
    # Historical rows are the only previous export with standalone NDVI coverage.
    history = next(v for v in prior.values() if isinstance(v, list) and v
                   and isinstance(v[0], dict) and 'ndvi_valid_fraction' in v[0])
    historical = {int(float(r['year'])): float(r['ndvi_valid_fraction']) for r in history}
    residuals, comparison = [], []
    for r in rows:
        y = int(float(r['year']))
        fields = ['old_valid_fraction', 'pixel_date_valid_fraction',
                  'common_fraction', 'gained_fraction', 'lost_fraction']
        vals = {k: float(r[k]) for k in fields}
        for k, v in vals.items():
            if not math.isfinite(v) or not 0 <= v <= 1:
                errors.append(f'{y}: invalid {k}')
        old, new = vals[fields[0]], vals[fields[1]]
        residuals.extend([abs(old - vals['common_fraction'] - vals['lost_fraction']),
                          abs(new - vals['common_fraction'] - vals['gained_fraction'])])
        if y in historical and abs(old - historical[y]) > 1e-10:
            errors.append(f'{y}: old coverage differs from prior reference audit')
        if y == 2020 and abs(old - 0.6704615416383498) > 1e-10:
            errors.append('2020: old coverage differs from console NDVI diagnostic')
        start, end = date(y, 10, 1), date(y, 11, 1)
        for prefix, lower in [('old_source', start), ('candidate', start - timedelta(days=15))]:
            field = 'old_source_start_dates' if prefix == 'old_source' else 'candidate_start_dates'
            count_field = 'old_source_count' if prefix == 'old_source' else 'candidate_source_count'
            dates = [date.fromisoformat(s.strip()) for s in r[field].strip('[]').split(',')]
            if len(dates) != int(r[count_field]) or not all(lower <= d < end for d in dates):
                errors.append(f'{y}: invalid dates/count for {prefix}')
        if r['qa'] != 'unchanged_strict' or int(r['boundary_code']) != 70179:
            errors.append(f'{y}: unexpected QA or boundary')
        comparison.append({'year': y, 'old_ndvi_coverage_pct': old * 100,
                           'pixel_date_ndvi_coverage_pct': new * 100,
                           'net_change_percentage_points': (new - old) * 100,
                           'gained_percentage_points': vals['gained_fraction'] * 100,
                           'lost_percentage_points': vals['lost_fraction'] * 100})
    maximum = max(residuals)
    if maximum > 1e-10:
        errors.append('Coverage decomposition does not balance.')
    report = {'source': source['provenance'], 'rows': len(rows), 'errors': errors,
              'historical_rows_crosschecked': len(historical),
              'max_decomposition_residual': maximum,
              'years_with_increased_coverage': sum(r['net_change_percentage_points'] > 0 for r in comparison),
              'years_with_decreased_coverage': sum(r['net_change_percentage_points'] < 0 for r in comparison)}
    (OUT / 'date_audit_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    if errors:
        raise SystemExit('\n'.join(errors))
    with (OUT / 'date_audit_comparison.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(comparison[0]))
        writer.writeheader()
        writer.writerows(comparison)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
