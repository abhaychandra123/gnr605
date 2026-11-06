"""Audit every record in the detailed QA export, without sampling rows."""
import csv
import io
import json
import math
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'results/andure'


def read_extract(name):
    data = json.loads((OUT / name).read_text())
    return data, list(csv.DictReader(io.StringIO(data['csv_text'])))


def main():
    source, rows = read_extract('detailed_quality_input_extract.json')
    _, date_rows = read_extract('date_audit_input_extract.json')
    _, qa_rows = read_extract('qa_audit_input_extract.json')
    errors, warnings = [], []
    expected = {d.strip() for r in date_rows for d in r['candidate_start_dates'].strip('[]').split(',')}
    qa_by_year = {int(float(r['year'])): r for r in qa_rows}
    if source['provenance']['reader_has_more']:
        errors.append('Reader reported incomplete content.')
    if source['provenance']['reader_total_lines'] != len(rows) + 1:
        errors.append('Reader line count differs from parsed records plus header.')
    seen, by_date, by_year, patterns = set(), defaultdict(list), defaultdict(lambda: defaultdict(float)), defaultdict(float)
    max_ratio_error = 0
    for n, r in enumerate(rows, 2):
        try:
            if None in r or any(v is None for v in r.values()):
                raise ValueError('malformed CSV field count')
            year = int(float(r['year']))
            if float(r['year']) != year or not 2001 <= year <= 2024:
                raise ValueError('invalid year')
            if int(r['boundary_code']) != 70179 or int(r['month']) != 10:
                raise ValueError('unexpected boundary or month')
            day = r['source_start']
            if day not in expected or not day.startswith(str(year)) or r['source_id'] != day.replace('-', '_'):
                raise ValueError('unexpected source date or ID')
            area, fraction, district = (float(r[k]) for k in ['area_km2', 'fraction_of_district', 'district_area_km2'])
            if not all(math.isfinite(v) for v in [area, fraction, district]) or not 0 <= fraction <= 1 or not 0 <= area <= district:
                raise ValueError('invalid area/fraction')
            if abs(district - float(qa_by_year[year]['district_area_km2'])) > 1e-7:
                raise ValueError('district denominator mismatch')
            max_ratio_error = max(max_ratio_error, abs(area / district - fraction))
            key = (day, r['joint_quality_code'])
            if key in seen:
                raise ValueError('duplicate date/code record')
            seen.add(key)
            by_date[day].append(r)
            if r['record_type'] == 'no_selected_observations':
                if area != 0 or fraction != 0 or any(r[k] for k in ['joint_quality_code', 'summary_qa', 'modland_qa', 'vi_usefulness', 'aerosol']):
                    raise ValueError('invalid empty-composite record')
                continue
            if r['record_type'] != 'quality_group':
                raise ValueError('unknown record type')
            names = ['summary_qa', 'modland_qa', 'vi_usefulness', 'aerosol', 'joint_quality_code']
            codes = [int(float(r[k])) for k in names]
            if any(float(r[k]) != v for k, v in zip(names, codes)):
                raise ValueError('noninteger quality code')
            summary, modland, usefulness, aerosol, joint = codes
            if summary not in (0, 1) or not 0 <= joint <= 511:
                raise ValueError('unexpected summary/joint code')
            decoded = [joint >> 8, joint & 3, (joint >> 2) & 15, (joint >> 6) & 3]
            if codes[:4] != decoded:
                raise ValueError('joint code does not match decoded fields')
            patterns[tuple(codes[:4])] += area
            by_year[year]['all_observation_area_km2'] += area
            by_year[year]['good_observation_area_km2' if summary == 0 else 'marginal_observation_area_km2'] += area
            if summary == 1:
                by_year[year]['high_aerosol_marginal_area_km2' if aerosol == 3 else 'other_marginal_area_km2'] += area
                if modland == 1 and usefulness in (1, 2) and aerosol == 2:
                    by_year[year]['candidate_marginal_area_km2'] += area
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f'CSV line {n}: {exc}')
    if set(by_date) != expected:
        errors.append(f'Source completeness mismatch: missing {sorted(expected - set(by_date))}, extra {sorted(set(by_date) - expected)}')
    if max_ratio_error > 1e-10:
        errors.append('Area/fraction mismatch exceeds tolerance.')
    # Disjoint groups within a composite: sums are valid there. Across composites
    # only union bounds are identifiable from aggregated records.
    for day, records in by_date.items():
        if any(r['record_type'] == 'no_selected_observations' for r in records) and len(records) != 1:
            errors.append(f'{day}: empty marker mixed with groups')
        if sum(float(r['fraction_of_district']) for r in records) > 1 + 1e-10:
            errors.append(f'{day}: disjoint group area exceeds district')
    for year, q in qa_by_year.items():
        dated = [rs for day, rs in by_date.items() if day.startswith(str(year))]
        for name, summary in [('06_strict_final', 0), ('08_good_or_marginal_all_original_flags', None)]:
            fractions = [sum(float(r['fraction_of_district']) for r in rs
                             if r['record_type'] == 'quality_group' and
                             (summary is None or float(r['summary_qa']) == summary)) for rs in dated]
            union = float(q[name])
            if not max(fractions) - 1e-10 <= union <= min(1, sum(fractions)) + 1e-10:
                errors.append(f'{year}: per-composite union bounds fail for {name}')
    if any(k[2] == 3 for k in patterns):
        warnings.append('Usefulness code 3 is observed and bit-consistent, but absent from the current catalogue enumerated labels. Preserve it as observed/unlabelled; do not map it to another value.')
    output_rows = []
    for year, totals in sorted(by_year.items()):
        marginal = totals['marginal_observation_area_km2']
        output_rows.append({'year': year, **dict(totals),
                            'high_aerosol_pct_of_marginal_observation_area': 100 * totals['high_aerosol_marginal_area_km2'] / marginal if marginal else None})
    report = {'source': source['provenance'], 'parsed_rows': len(rows),
              'quality_rows': sum(r['record_type'] == 'quality_group' for r in rows),
              'empty_composite_rows': sum(r['record_type'] == 'no_selected_observations' for r in rows),
              'expected_composites': len(expected), 'observed_composites': len(by_date),
              'max_area_fraction_residual': max_ratio_error, 'errors': errors, 'warnings': warnings,
              'quality_patterns': [{'summary_qa': k[0], 'modland_qa': k[1], 'vi_usefulness': k[2], 'aerosol': k[3],
                                    'summed_observation_area_km2': v} for k, v in sorted(patterns.items())]}
    (OUT / 'detailed_quality_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    if errors:
        raise SystemExit('\n'.join(errors))
    fields = sorted({k for r in output_rows for k in r}, key=lambda k: (k != 'year', k))
    with (OUT / 'detailed_quality_year_summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    print(json.dumps(report, indent=2))
    print('Recent marginal high-aerosol percentages (observation-area denominator):')
    for r in output_rows:
        if r['year'] >= 2019:
            print(r['year'], round(r['high_aerosol_pct_of_marginal_observation_area'], 4))


if __name__ == '__main__':
    main()
