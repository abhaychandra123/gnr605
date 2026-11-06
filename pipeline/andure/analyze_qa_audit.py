"""Validate the uploaded QA gates against the prior observation-date audit."""
import csv
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/andure'


def main():
    source = json.loads((OUT / 'qa_audit_input_extract.json').read_text())
    rows = list(csv.DictReader(io.StringIO(source['csv_text'])))
    dates = json.loads((OUT / 'date_audit_input_extract.json').read_text())
    previous = {int(float(r['year'])): r for r in csv.DictReader(io.StringIO(dates['csv_text']))}
    errors, comparison, residuals = [], [], []
    if [int(float(r['year'])) for r in rows] != list(range(2001, 2025)):
        errors.append('Expected exactly 24 ordered rows, 2001–2024.')
    stages = ['01_date_and_value', '02_plus_land', '03_plus_SummaryQA_good',
              '04_plus_no_adjacent_cloud', '05_plus_no_mixed_cloud', '06_strict_final',
              '07_land_marginal_only', '08_good_or_marginal_all_original_flags']
    for row in rows:
        year = int(float(row['year']))
        v = [float(row[k]) for k in stages]
        if any(not math.isfinite(x) or x < 0 or x > 1 for x in v):
            errors.append(f'{year}: invalid coverage fraction')
        if any(v[i + 1] > v[i] + 1e-10 for i in range(5)):
            errors.append(f'{year}: cumulative stage increased')
        if not (v[5] - 1e-10 <= v[7] <= v[1] + 1e-10) or v[6] > v[1] + 1e-10:
            errors.append(f'{year}: invalid branch containment')
        residuals.append(abs(v[5] - float(previous[year]['pixel_date_valid_fraction'])))
        if int(row['candidate_source_count']) != int(previous[year]['candidate_source_count']):
            errors.append(f'{year}: candidate count mismatch')
        if int(row['boundary_code']) != 70179 or int(row['month']) != 10:
            errors.append(f'{year}: wrong boundary or month')
        if abs(float(row['district_area_km2']) - float(previous[year]['district_area_km2'])) > 1e-7:
            errors.append(f'{year}: district area mismatch')
        comparison.append({'year': year, 'date_value_pct': v[0] * 100,
                           'land_pct': v[1] * 100, 'good_before_extra_flags_pct': v[2] * 100,
                           'strict_pct': v[5] * 100, 'good_or_marginal_flags_pct': v[7] * 100,
                           'loss_at_good_requirement_pp': (v[1] - v[2]) * 100,
                           'loss_at_extra_flags_pp': (v[2] - v[5]) * 100,
                           'new_area_with_marginal_pp': (v[7] - v[5]) * 100,
                           'remaining_land_gap_pp': (v[1] - v[7]) * 100})
    if max(residuals) > 1e-10:
        errors.append('Strict final fractions disagree with date audit.')
    report = {'source': source['provenance'], 'rows': len(rows), 'errors': errors,
              'max_strict_vs_date_residual': max(residuals),
              'interpretation': 'Coverage consistency only; marginal-data accuracy remains unverified.'}
    (OUT / 'qa_audit_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    if errors:
        raise SystemExit('\n'.join(errors))
    with (OUT / 'qa_audit_comparison.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(comparison[0]))
        writer.writeheader()
        writer.writerows(comparison)
    print(json.dumps(report, indent=2))
    for row in comparison:
        if row['year'] >= 2019:
            print(row)


if __name__ == '__main__':
    main()
