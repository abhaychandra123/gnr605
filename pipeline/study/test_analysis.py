"""Synthetic statistical tests only. No generated series is a Beed result."""
import unittest
import numpy as np
import pandas as pd
from scipy import stats
from analysis import spi, union_bounds


class StatisticalTests(unittest.TestCase):
    def series(self):
        index = pd.period_range('1981-01', '2024-12', freq='M')
        rng = np.random.default_rng(605)
        return pd.Series(rng.gamma(2.5, 30, len(index)), index=index)

    def test_fit_ignores_future_values(self):
        a = self.series()
        b = a.copy()
        b[b.index.year >= 2020] *= 100
        _, fa = spi(a, 3)
        _, fb = spi(b, 3)
        np.testing.assert_allclose(fa[['shape', 'scale', 'zero_probability']], fb[['shape', 'scale', 'zero_probability']])

    def test_missing_month_invalidates_accumulations(self):
        a = self.series().drop(pd.Period('2021-05', freq='M'))
        result, _ = spi(a, 3)
        self.assertTrue(result.loc['2021-05':'2021-07'].isna().all())
        self.assertTrue(np.isfinite(result.loc['2021-08']))

    def test_units_do_not_change_spi(self):
        a = self.series()
        x, _ = spi(a, 3)
        y, _ = spi(a / 10, 3)
        np.testing.assert_allclose(x, y, atol=1e-7, equal_nan=True)

    def test_zero_mass_and_normal_transform(self):
        a = self.series()
        a.loc['1981-01':'1985-12'] = 0
        x, fits = spi(a, 1)
        january = fits[fits.calendar_month == 1].iloc[0]
        self.assertAlmostEqual(january.zero_probability, 5 / 39)
        self.assertAlmostEqual(x.loc['1981-01'], stats.norm.ppf(5 / 39))

    def test_all_zero_reference_is_not_valid_spi(self):
        a = self.series() * 0
        x, fits = spi(a, 1)
        self.assertTrue(x.isna().all())
        self.assertTrue((fits.status == 'insufficient_or_degenerate_reference').all())

    def test_negative_rain_rejected(self):
        a = self.series()
        a.iloc[0] = -1
        with self.assertRaises(ValueError):
            spi(a, 3)

    def test_union_bounds_contain_exact_spatial_unions(self):
        rng = np.random.default_rng(13)
        for _ in range(200):
            expanded = rng.random((3, 100)) < 0.6
            accepted = expanded & (rng.random((3, 100)) < 0.7)
            strict = accepted & (rng.random((3, 100)) < 0.3)
            low, high = union_bounds(strict.any(axis=0).mean(), expanded.any(axis=0).mean(),
                                    accepted.mean(axis=1).tolist(), (expanded & ~accepted).mean(axis=1).sum())
            true = accepted.any(axis=0).mean()
            self.assertLessEqual(low, true + 1e-10)
            self.assertGreaterEqual(high + 1e-10, true)


if __name__ == '__main__':
    unittest.main()
