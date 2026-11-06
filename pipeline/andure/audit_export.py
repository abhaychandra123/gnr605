"""Audit a real GEE export. Standard library only; does not fit a drought model."""
import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path


REQUIRED = {
    'date', 'ndvi', 'lst_k', 'vci', 'tci', 'vhi', 'alpha',
    'valid_fraction', 'valid_area_km2', 'district_area_km2',
    'rain_mm', 'rain_3month_mm', 'rain_days', 'rain_expected_days',
    'rain_3month_days', 'rain_3month_expected_days',
}


def audit(path, min_coverage=0.8, tolerance=1e-6):
    """Coverage threshold is an exploratory screening choice, not calibrated."""
    if not 0 <= min_coverage <= 1:
        raise ValueError('min_coverage must lie in [0, 1]')
    with Path(path).open(newline='') as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing columns: {sorted(missing)}')
        rows = list(reader)
    if not rows:
        raise ValueError('Export contains no rows')
    errors, warnings, seen, residuals = [], [], set(), []
    for line, row in enumerate(rows, start=2):
        label = f'line {line} ({row["date"]})'
        try:
            date = dt.datetime.strptime(row['date'], '%Y-%m')
            if date.strftime('%Y-%m') != row['date']:
                raise ValueError
        except ValueError:
            errors.append(f'{label}: invalid YYYY-MM date')
        def number(key):
            text = row.get(key)
            if text is None or not text.strip():
                return None
            try:
                value = float(text)
                if not math.isfinite(value):
                    raise ValueError
                return value
            except ValueError:
                errors.append(f'{label}: {key} is not finite numeric data')
                return None

        values = {key: number(key) for key in REQUIRED - {'date'}}
        # Sensitivity exports legitimately repeat a month under different settings.
        variant = []
        if 'min_ndvi_years' in row or 'min_lst_years' in row:
            for key in ('min_ndvi_years', 'min_lst_years'):
                value = number(key)
                if value is None or value < 2 or not value.is_integer():
                    errors.append(f'{label}: invalid {key}')
                variant.append(value)
        identity = (row['date'], *variant)
        if identity in seen:
            errors.append(f'{label}: duplicate district-month/settings')
        seen.add(identity)
        coverage = values['valid_fraction']
        area, district = values['valid_area_km2'], values['district_area_km2']
        if coverage is None or not 0 <= coverage <= 1 + tolerance:
            errors.append(f'{label}: missing or invalid coverage')
        elif coverage < min_coverage:
            warnings.append(f'{label}: coverage {coverage:.1%} below {min_coverage:.0%}')
        if district is None or district <= 0 or area is None or area < 0:
            errors.append(f'{label}: invalid area')
        elif coverage is not None and abs(area / district - coverage) > tolerance:
            errors.append(f'{label}: coverage does not match area ratio')
        alpha = values['alpha']
        if alpha is None or not 0 <= alpha <= 1:
            errors.append(f'{label}: alpha must lie in [0, 1]')
        components = [values[key] for key in ('vci', 'tci', 'vhi')]
        if all(value is not None for value in components) and alpha is not None:
            vci, tci, vhi = components
            residual = vhi - (alpha * vci + (1 - alpha) * tci)
            residuals.append(residual)
            if abs(residual) > tolerance:
                errors.append(f'{label}: VHI formula mismatch ({residual:.6g})')
            if any(value < 0 or value > 100 for value in components):
                warnings.append(f'{label}: outside reference range; values deliberately not clipped')
        elif coverage is not None and coverage > 0:
            errors.append(f'{label}: missing indices despite positive valid coverage')
        if coverage == 0 and any(value is not None for value in components):
            errors.append(f'{label}: indices present despite zero valid coverage')
        n, t = values['ndvi'], values['lst_k']
        if n is not None and not -0.2 <= n <= 1:
            errors.append(f'{label}: NDVI outside product range; inspect scaling')
        if t is not None and not 150 <= t <= 400:
            errors.append(f'{label}: implausible LST in kelvin; inspect scaling/units')
        if coverage is not None and coverage > 0 and (n is None or t is None):
            errors.append(f'{label}: missing NDVI/LST despite positive coverage')
        for prefix, field in [('rain', 'rain_mm'), ('rain_3month', 'rain_3month_mm')]:
            if values[prefix + '_days'] != values[prefix + '_expected_days']:
                warnings.append(f'{label}: {prefix} daily source count incomplete')
            if values[field] is None:
                warnings.append(f'{label}: {field} missing; do not impute zero')
            elif values[field] < 0:
                errors.append(f'{label}: negative rainfall')
    return {
        'input': str(path), 'rows': len(rows), 'formula_rows': len(residuals),
        'formula_max_abs_error': max(map(abs, residuals), default=None),
        'coverage_screen': min_coverage, 'errors': errors, 'warnings': warnings,
        'interpretation': 'Formula agreement checks processing consistency, not independent drought accuracy.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--min-coverage', type=float, default=0.8)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit(args.csv, args.min_coverage)
    text = json.dumps(result, indent=2, allow_nan=False)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n')
    raise SystemExit(1 if result['errors'] else 0)
