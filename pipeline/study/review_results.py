"""Inspect real exports, verify prior-run consistency, and create research figures."""
import io
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/gnr605-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from analysis import ROOT, SCENARIOS, check_comparison, check_history, screened_bounds, load_rainfall

OUT = ROOT / 'results/study'
DATA = ROOT / 'data/study'
COLORS = ['#355C7D', '#DF8A35', '#289E82', '#A34C85']
LABELS = ['A · strict/start', 'B · strict/pixel date', 'C · screened/pixel date', 'D · screened/daily LST']


def save(fig, name):
    fig.savefig(OUT / f'{name}.png', dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    comp = check_comparison(DATA / 'beed_controlled_seasonal_2020_2024.csv')
    hist = check_history(DATA / 'beed_policy_history_2001_2024.csv', screened_bounds())
    rain = load_rainfall(DATA / 'beed_chirps_monthly_1981_2024.csv')
    pilot = pd.read_csv(ROOT / 'results/andure/pilot_comparison.csv').set_index('year')
    october_a = comp[(comp.month == 10) & (comp.scenario == SCENARIOS[0]) & (comp.support == 'own')].set_index('year')
    checks = {}
    for new, old, factor in [('vhi', 'vhi15', 1), ('valid_fraction', 'coverage15_pct', 100)]:
        err = (october_a[new] * factor - pilot.loc[october_a.index, old]).abs().max()
        checks[f'prior_october_A_{new}_max_abs_error'] = float(err)
        if err > 1e-7:
            raise ValueError(f'Prior October A mismatch: {new}')
    old_rain = rain.loc['2020-01':'2024-12']
    october_rain = old_rain[old_rain.index.month == 10].copy()
    october_rain.index = october_rain.index.year
    err = (october_rain.rain_mm - pilot.loc[october_rain.index, 'rain_oct_mm']).abs().max()
    checks['prior_october_rain_max_abs_error_mm'] = float(err)
    if err > 1e-6:
        raise ValueError('Prior October rainfall mismatch')
    rolling = rain.rain_mm.rolling(3).sum()
    for y in range(2020, 2025):
        if abs(rolling.loc[f'{y}-10'] - pilot.loc[y, 'rain_aug_oct_mm']) > 1e-6:
            raise ValueError('Prior August–October rainfall mismatch')
    checks['prior_aug_oct_rain_consistency'] = 'passed'
    checks['history_audited_coverage_and_bounds'] = 'passed'
    checks['rain_full_coverage_months'] = int(rain.rain_for_spi_mm.notna().sum())
    (OUT / 'cross_run_validation.json').write_text(json.dumps(checks, indent=2) + '\n')

    # Within-month all-policy common support; it changes from month to month.
    fig, axes = plt.subplots(3, 2, figsize=(12, 11), sharex='col', constrained_layout=True)
    for row, month in enumerate([10, 11, 12]):
        for i, scenario in enumerate(SCENARIOS):
            own = comp[(comp.month == month) & (comp.scenario == scenario) & (comp.support == 'own')].sort_values('year')
            common = comp[(comp.month == month) & (comp.scenario == scenario) & (comp.support != 'own')].sort_values('year')
            axes[row, 0].plot(own.year, own.valid_fraction * 100, 'o-', color=COLORS[i], label=LABELS[i])
            axes[row, 1].plot(common.year, common.vhi, 'o-', color=COLORS[i])
        axes[row, 0].set_ylabel(f'{["October", "November", "December"][row]}\nVHI-valid area (%)')
        axes[row, 0].set_ylim(0, 100)
        axes[row, 1].set_ylabel('VHI on common support')
        axes[row, 1].axhline(40, color='#888888', ls=':', lw=1)
        for ax in axes[row]:
            ax.set_xticks(range(2020, 2025))
            ax.grid(alpha=.15)
    axes[0, 0].legend(fontsize=8, loc='upper left', bbox_to_anchor=(0, .8))
    axes[0, 0].set_title('Own support: coverage changes')
    axes[0, 1].set_title('All-policy common support: index changes')
    fig.suptitle('Beed provisional GAUL area · controlled MODIS comparison\nCommon support is matched within each month, not fixed across years', fontsize=13)
    save(fig, 'controlled_comparison')

    delta = []
    for support, group in comp.groupby('support'):
        for metric in ['vhi', 'valid_fraction', 'class_disagreement_vs_A', 'lst_observations']:
            p = group.pivot(index='date', columns='scenario', values=metric)
            for hi, lo, name in [(1, 0, 'B_minus_A'), (2, 1, 'C_minus_B'), (3, 2, 'D_minus_C')]:
                for date, value in (p[SCENARIOS[hi]] - p[SCENARIOS[lo]]).items():
                    delta.append({'date': date, 'support': support, 'metric': metric, 'contrast': name, 'difference': value})
    pd.DataFrame(delta).to_csv(OUT / 'policy_contrasts.csv', index=False)
    comp.groupby(['scenario', 'support'])[['valid_fraction', 'vhi', 'vhi_outside_0_100_fraction_valid',
                                         'class_disagreement_vs_A', 'lst_observations',
                                         'ndvi_reference_span', 'lst_reference_span']].agg(['min', 'median', 'max']).to_csv(OUT / 'policy_diagnostic_summary.csv')

    spi_data = pd.read_csv(OUT / 'rainfall_spi.csv')
    dates = pd.to_datetime(spi_data.date)
    fig, axes = plt.subplots(4, 1, figsize=(13, 10), sharex=True, constrained_layout=True)
    for ax, scale in zip(axes, [1, 3, 6, 12]):
        values = spi_data[f'spi_{scale}'].to_numpy()
        ax.plot(dates, values, color='#365F7D', lw=.8)
        ax.fill_between(dates, values, 0, where=values < 0, color='#CE7548', alpha=.7)
        ax.axhline(-1, color='#666666', ls='--', lw=.6)
        ax.axhline(-2, color='#666666', ls=':', lw=.6)
        ax.axvline(pd.Timestamp('2020-01-01'), color='#333333', lw=.8)
        ax.set_ylabel(f'SPI-{scale}')
        ax.grid(alpha=.12)
    fig.suptitle('District-average CHIRPS rainfall · 1981–2019 gamma reference\nProvisional GAUL area; meteorological indicator, not observed crop damage', fontsize=13)
    save(fig, 'rainfall_spi')
    spi_data[spi_data.year.between(2020, 2024) & spi_data.month.isin([10, 11, 12])].to_csv(OUT / 'evaluation_season_spi.csv', index=False)
    gamma_review(rain)
    print(json.dumps(checks, indent=2))


def gamma_review(rain):
    """Refit-parametric-bootstrap KS checks of positive gamma components.

    Zero frequency is estimated separately. This checks overall positive fit;
    it cannot validate rare tails or the district-average spatial aggregation.
    """
    fits = pd.read_csv(OUT / 'spi_fit_diagnostics.csv')
    rng = np.random.default_rng(605)
    diagnostics = []
    fig, axes = plt.subplots(4, 3, figsize=(11, 12), constrained_layout=True)
    for row, scale in enumerate([1, 3, 6, 12]):
        accum = rain.rain_for_spi_mm.rolling(scale, min_periods=scale).sum()
        for month in range(1, 13):
            f = fits[(fits.scale_months == scale) & (fits.calendar_month == month)].iloc[0]
            if f.status != 'fitted':
                continue
            ref = accum[(accum.index.year <= 2019) & (accum.index.month == month)].dropna()
            positive = ref[ref > 0].to_numpy()
            observed = stats.kstest(positive, 'gamma', args=(f['shape'], 0, f['scale'])).statistic
            exceeds = 0
            for _ in range(1999):
                simulated = rng.gamma(f['shape'], f['scale'], len(positive))
                shape, _, theta = stats.gamma.fit(simulated, floc=0)
                exceeds += stats.kstest(simulated, 'gamma', args=(shape, 0, theta)).statistic >= observed
            diagnostics.append({'scale': scale, 'month': month, 'positive_n': len(positive),
                                'ks_statistic_positive': observed, 'bootstrap_p': (exceeds + 1) / 2000,
                                'replicates': 1999, 'scope': 'positive_gamma_component_only'})
            if month in [10, 11, 12]:
                ax = axes[row, month - 10]
                theoretical = stats.gamma.ppf((np.arange(len(positive)) + .5) / len(positive), f['shape'], scale=f['scale'])
                ax.scatter(theoretical, np.sort(positive), s=13, color=COLORS[row], alpha=.8)
                high = max(theoretical.max(), positive.max())
                ax.plot([0, high], [0, high], color='#888888', lw=.7)
                ax.set_title(f'SPI-{scale} · {["Oct", "Nov", "Dec"][month - 10]} · n={len(positive)}')
                ax.set_xlabel('Gamma quantile (mm)')
                ax.set_ylabel('Observed positive total (mm)')
    diagnostics = pd.DataFrame(diagnostics)
    order = np.argsort(diagnostics.bootstrap_p.to_numpy())
    adjusted = np.maximum.accumulate((len(order) - np.arange(len(order))) * diagnostics.bootstrap_p.to_numpy()[order])
    diagnostics.loc[diagnostics.index[order], 'holm_adjusted_p'] = np.minimum(1, adjusted)
    diagnostics.to_csv(OUT / 'spi_gamma_fit_review.csv', index=False)
    fig.suptitle('Training-only gamma Q–Q checks · October–December\nPositive totals only; zero frequency fitted separately', fontsize=13)
    save(fig, 'spi_gamma_qq')


if __name__ == '__main__':
    main()
