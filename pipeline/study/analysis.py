"""Local processing for real GEE exports. Never substitutes synthetic observations."""
import argparse
import csv
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ['A_start_strict_8day', 'B_pixel_strict_8day', 'C_pixel_screened_8day', 'D_pixel_screened_daily']


def union_bounds(strict, expanded, accepted_areas, excluded_sum):
    return (max(strict, max(accepted_areas, default=0), expanded - excluded_sum),
            min(expanded, sum(accepted_areas)))


def screened_bounds():
    """Set-theoretic bounds from actual grouped exports, not modelled coverage."""
    folder = ROOT / 'results/andure'
    def read(name):
        return list(csv.DictReader(io.StringIO(json.loads((folder / name).read_text())['csv_text'])))
    detailed = read('detailed_quality_input_extract.json')
    quality = read('qa_audit_input_extract.json')
    result = []
    for row in quality:
        year = int(float(row['year']))
        accepted_by_date = {}
        excluded_sum = 0.0
        for item in detailed:
            if int(float(item['year'])) != year or item['record_type'] != 'quality_group':
                continue
            fraction = float(item['fraction_of_district'])
            accepted = float(item['summary_qa']) == 0 or (
                float(item['summary_qa']) == 1 and float(item['modland_qa']) == 1
                and float(item['vi_usefulness']) in (1, 2) and float(item['aerosol']) == 2)
            if accepted:
                day = item['source_start']
                accepted_by_date[day] = accepted_by_date.get(day, 0) + fraction
            else:
                excluded_sum += fraction
        strict = float(row['06_strict_final'])
        expanded = float(row['08_good_or_marginal_all_original_flags'])
        lower, upper = union_bounds(strict, expanded, list(accepted_by_date.values()), excluded_sum)
        if lower > upper + 1e-10:
            raise ValueError(f'Inconsistent bounds in {year}')
        result.append({'year': year, 'strict_fraction': strict, 'screened_lower_bound': lower,
                       'screened_upper_bound': upper, 'all_marginal_fraction': expanded,
                       'interpretation': 'mathematical_coverage_bounds_not_confidence_intervals'})
    return pd.DataFrame(result)


def spi(series, scale, baseline_start=1981, baseline_end=2019, min_samples=30):
    """Calendar-month gamma MLE, zero mass q=n_zero/n, then normal inverse CDF.

    Computes SPI of DISTRICT MEAN rainfall, not mean of pixelwise SPI.
    Missing months invalidate the whole rolling window. Fits use reference only.
    Numerical probability clipping is recorded, not mistaken for observed extremes.
    """
    if not isinstance(series.index, pd.PeriodIndex) or series.index.freqstr != 'M':
        raise ValueError('Expected monthly PeriodIndex')
    if series.index.has_duplicates or not series.index.is_monotonic_increasing:
        raise ValueError('Dates must be unique and ordered')
    if scale < 1 or int(scale) != scale:
        raise ValueError('Accumulation must be a positive integer')
    if np.isinf(series.to_numpy(dtype=float)).any() or (series.dropna() < 0).any():
        raise ValueError('Rainfall must be finite, nonnegative or explicitly missing')
    complete = series.reindex(pd.period_range(series.index.min(), series.index.max(), freq='M'))
    accumulation = complete.rolling(scale, min_periods=scale).sum()
    output = pd.Series(np.nan, index=complete.index, name=f'spi_{scale}')
    fits = []
    for month in range(1, 13):
        ref = accumulation[(accumulation.index.year >= baseline_start) &
                           (accumulation.index.year <= baseline_end) &
                           (accumulation.index.month == month)].dropna().to_numpy()
        positive = ref[ref > 0]
        fit = {'scale_months': scale, 'calendar_month': month, 'baseline_start': baseline_start,
               'baseline_end': baseline_end, 'n_reference': len(ref), 'n_positive': len(positive),
               'method': 'gamma_MLE_floc0_zero_mass', 'probability_clip': 1e-8}
        if len(ref) < min_samples or len(positive) < 20 or np.ptp(positive) < 1e-10:
            fit['status'] = 'insufficient_or_degenerate_reference'
            fits.append(fit)
            continue
        shape, _, theta = stats.gamma.fit(positive, floc=0)
        if not np.isfinite([shape, theta]).all() or min(shape, theta) <= 0:
            raise ValueError('Invalid gamma fit')
        q = float(np.mean(ref == 0))
        take = (accumulation.index.month == month) & accumulation.notna()
        probabilities = q + (1 - q) * stats.gamma.cdf(accumulation[take], a=shape, scale=theta)
        clipped = np.clip(probabilities, 1e-8, 1 - 1e-8)
        output.loc[take] = stats.norm.ppf(clipped)
        fit.update(status='fitted', shape=float(shape), scale=float(theta), zero_probability=q,
                   numerical_clips=int(np.count_nonzero(clipped != probabilities)))
        fits.append(fit)
    return output, pd.DataFrame(fits)


def load_rainfall(path):
    data = pd.read_csv(path)
    required = ['date', 'rain_mm', 'rain_days', 'expected_days', 'rain_valid_fraction', 'boundary_code']
    if not set(required) <= set(data):
        raise ValueError('Rainfall export is missing required columns')
    if data['date'].duplicated().any() or not data['date'].astype(str).str.fullmatch(r'\d{4}-\d{2}').all():
        raise ValueError('Invalid or duplicate rainfall dates')
    data['period'] = pd.PeriodIndex(data['date'], freq='M')
    data = data.set_index('period').sort_index()
    expected = pd.period_range('1981-01', '2024-12', freq='M')
    if not data.index.equals(expected):
        raise ValueError('Expected the complete 528-row 1981–2024 monthly export')
    if not (data['boundary_code'] == 70179).all():
        raise ValueError('Unexpected boundary; verify before mixing exports')
    if not (data['expected_days'].to_numpy() == data.index.days_in_month).all():
        raise ValueError('Incorrect calendar-day metadata')
    if np.isinf(data['rain_mm']).any() or (data['rain_mm'].dropna() < 0).any():
        raise ValueError('Invalid rainfall values')
    if not data['rain_valid_fraction'].between(0, 1 + 1e-9).all():
        raise ValueError('Invalid rainfall area fractions')
    complete = (data['rain_days'] == data['expected_days']) & (data['rain_valid_fraction'] >= 1 - 1e-6)
    # Fixed full district support is required; never fit SPI on drifting footprints.
    data['rain_for_spi_mm'] = data['rain_mm'].where(complete)
    return data


def trend_report(data):
    """Exploratory rainfall trends; naive p-values explicitly assume independence."""
    rows = []
    for name, months in [('JJAS', [6, 7, 8, 9]), ('OND', [10, 11, 12])]:
        s = data.loc[data.index.month.isin(months), 'rain_for_spi_mm']
        yearly = s.groupby(s.index.year).agg(['sum', 'count'])
        yearly = yearly[yearly['count'] == len(months)]
        x, y = yearly.index.to_numpy(), yearly['sum'].to_numpy()
        if len(y) < 20:
            rows.append({'season': name, 'status': 'insufficient_complete_years', 'n': len(y)})
            continue
        tau, p = stats.kendalltau(x, y)
        sen = stats.theilslopes(y, x, alpha=0.95)
        # Use genuinely adjacent years only for lag-one diagnostics.
        adjacent = np.diff(x) == 1
        lag1 = float(np.corrcoef(y[:-1][adjacent], y[1:][adjacent])[0, 1]) if adjacent.sum() > 2 else np.nan
        rows.append({'season': name, 'status': 'exploratory', 'n': len(y),
                     'kendall_tau': tau, 'p_independence_assumption': p,
                     'sen_mm_per_year': sen.slope, 'sen_ci95_low': sen.low_slope,
                     'sen_ci95_high': sen.high_slope, 'lag1_correlation': lag1,
                     'limitation': 'No serial-dependence correction; do not claim significance from naive p alone.'})
    return pd.DataFrame(rows)


def check_comparison(path):
    data = pd.read_csv(path)
    keys = ['date', 'scenario', 'support']
    if not set(keys + ['vhi', 'vci', 'tci', 'alpha', 'valid_fraction', 'valid_area_km2', 'district_area_km2']) <= set(data):
        raise ValueError('Comparison export is missing required fields')
    expected = {(f'{y}-{m:02d}', s, p) for y in range(2020, 2025) for m in [10, 11, 12]
                for s in SCENARIOS for p in ['own', 'all_variants_common']}
    actual = set(map(tuple, data[keys].to_numpy()))
    if len(data) != len(expected) or actual != expected:
        raise ValueError('Expected exactly 120 unique date/scenario/support rows')
    numeric = data.select_dtypes(include='number')
    if np.isinf(numeric.to_numpy()).any():
        raise ValueError('Infinite numeric values')
    for column in ['valid_fraction', 'unknown_fraction', 'pair_A_valid_fraction', 'class_disagreement_vs_A']:
        if not data[column].dropna().between(-1e-9, 1 + 1e-9).all():
            raise ValueError(f'Invalid fraction: {column}')
    usable = data['valid_fraction'] > 0
    if data.loc[usable, ['ndvi', 'lst_k', 'vci', 'tci', 'vhi']].isna().any().any():
        raise ValueError('Missing metrics on positive support')
    for column in ['ndvi', 'lst_k', 'vci', 'tci', 'vhi']:
        if data.loc[~usable, column].notna().any():
            raise ValueError('A zero-area result must remain missing')
    if not np.allclose(data['valid_fraction'], data['valid_area_km2'] / data['district_area_km2'], atol=1e-9):
        raise ValueError('Area/fraction mismatch')
    if not np.allclose(data['valid_fraction'] + data['unknown_fraction'], 1):
        raise ValueError('Unknown fraction mismatch')
    if not np.allclose(data.loc[usable, 'vhi'], data.loc[usable, 'alpha'] * data.loc[usable, 'vci'] +
                       (1 - data.loc[usable, 'alpha']) * data.loc[usable, 'tci'], atol=1e-7):
        raise ValueError('VHI formula identity failed')
    class_cols = [f'class_{i}_fraction_valid' for i in range(5)]
    if not np.allclose(data.loc[usable, class_cols].sum(axis=1), 1):
        raise ValueError('Exclusive class fractions must sum to one')
    common = data[data['support'] == 'all_variants_common']
    if (common.groupby('date')['valid_fraction'].agg(lambda x: x.max() - x.min()) > 1e-9).any():
        raise ValueError('Shared support is not identical across variants')
    paired = data.pivot(index=['date', 'scenario'], columns='support', values='valid_fraction')
    if (paired['all_variants_common'] > paired['own'] + 1e-9).any():
        raise ValueError('Common support exceeds individual support')
    return data


def check_history(path, bounds):
    data = pd.read_csv(path)
    keys = ['year', 'month', 'scenario']
    required = keys + ['date', 'ndvi', 'ndvi_valid_fraction', 'lst_valid_fraction', 'boundary_code']
    if not set(required) <= set(data):
        raise ValueError('History export is missing required columns')
    expected = {(y, m, s) for y in range(2001, 2025) for m in (10, 11, 12) for s in SCENARIOS}
    if len(data) != 288 or set(map(tuple, data[keys].to_numpy())) != expected:
        raise ValueError('Expected 288 unique historical policy rows')
    if not (data.boundary_code == 70179).all():
        raise ValueError('Unexpected historical boundary')
    for column in ['ndvi_valid_fraction', 'lst_valid_fraction']:
        if not data[column].between(0, 1 + 1e-9).all():
            raise ValueError(f'Invalid historical fraction: {column}')
    october = data[data.month == 10].pivot(index='year', columns='scenario', values='ndvi_valid_fraction')
    old = pd.read_csv(io.StringIO(json.loads((ROOT / 'results/andure/date_audit_input_extract.json').read_text())['csv_text'])).set_index('year')
    for scenario, column in [(SCENARIOS[0], 'old_valid_fraction'), (SCENARIOS[1], 'pixel_date_valid_fraction')]:
        if not np.allclose(october[scenario], old.loc[october.index, column], atol=1e-8, rtol=0):
            raise ValueError(f'History disagrees with independently audited October coverage: {scenario}')
    aligned = bounds.set_index('year').loc[october.index]
    for scenario in SCENARIOS[2:]:
        if ((october[scenario] < aligned.screened_lower_bound - 1e-8) |
                (october[scenario] > aligned.screened_upper_bound + 1e-8)).any():
            raise ValueError('Screened October coverage violates derived set bounds')
    pivot = data.pivot(index=['year', 'month'], columns='scenario', values='ndvi_valid_fraction')
    if (pivot[SCENARIOS[2]] < pivot[SCENARIOS[1]] - 1e-9).any():
        raise ValueError('Screened NDVI coverage must include strict pixel-date coverage')
    for column in ['ndvi', 'ndvi_valid_fraction']:
        pivot = data.pivot(index=['year', 'month'], columns='scenario', values=column)
        if not np.allclose(pivot[SCENARIOS[2]], pivot[SCENARIOS[3]], equal_nan=True, atol=1e-9):
            raise ValueError('C and D must have identical current NDVI')
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', type=Path, default=ROOT / 'data/study')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'results/study')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    bounds = screened_bounds()
    bounds.to_csv(args.output_dir / 'screened_coverage_bounds.csv', index=False)
    status = {'coverage_bounds': 'computed_from_real_uploaded_exports', 'satellite_comparison': 'awaiting_export',
              'satellite_history': 'awaiting_export', 'rainfall_SPI': 'awaiting_export',
              'independent_impact_validation': 'not_available', 'ML': 'not_run'}
    rainfall = args.input_dir / 'beed_chirps_monthly_1981_2024.csv'
    if rainfall.exists():
        rain = load_rainfall(rainfall)
        fits = []
        for scale in [1, 3, 6, 12]:
            rain[f'spi_{scale}'], fit = spi(rain['rain_for_spi_mm'], scale)
            fits.append(fit)
        rain.to_csv(args.output_dir / 'rainfall_spi.csv', index_label='period')
        pd.concat(fits).to_csv(args.output_dir / 'spi_fit_diagnostics.csv', index=False)
        trend_report(rain).to_csv(args.output_dir / 'rainfall_trends_exploratory.csv', index=False)
        status['rainfall_SPI'] = 'computed_from_real_export_review_fit_diagnostics'
    comparison = args.input_dir / 'beed_controlled_seasonal_2020_2024.csv'
    if comparison.exists():
        metrics = check_comparison(comparison)
        metrics.to_csv(args.output_dir / 'validated_comparison.csv', index=False)
        status['satellite_comparison'] = 'real_export_passed_consistency_checks'
    history = args.input_dir / 'beed_policy_history_2001_2024.csv'
    if history.exists():
        check_history(history, bounds).to_csv(args.output_dir / 'validated_history.csv', index=False)
        status['satellite_history'] = 'real_export_passed_audited_october_and_screened_bounds_checks'
    boundary_review = args.output_dir / 'boundary_validation.json'
    if boundary_review.exists():
        status['boundary_verification'] = 'official_SOI_comparison_completed_material_mismatch_found'
        status['independent_impact_validation'] = 'not_run_requires_boundary_consistent_reconstruction'
    if (args.output_dir / 'beed_crop_statistics_raw.csv').exists():
        status['crop_data'] = '25_official_annual_PDFs_acquired_raw_Beed_rows_extracted_units_retained'
    if (args.output_dir / 'mask_validation.json').exists():
        status['candidate_masks'] = 'downloaded_and_inspected_not_applied_to_primary_experiment'
    (args.output_dir / 'execution_status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2))
    print(bounds[bounds.year >= 2019].to_string(index=False))


if __name__ == '__main__':
    main()
