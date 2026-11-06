"""Regression and corruption checks using downloaded exports when available."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from analysis import ROOT, SCENARIOS, check_comparison, check_history, load_rainfall, screened_bounds

DATA = ROOT / 'data/study'


@unittest.skipUnless((DATA / 'beed_policy_history_2001_2024.csv').exists(), 'Real exports not downloaded')
class RealExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'corrupted.csv'

    def test_all_real_exports_pass(self):
        self.assertEqual(len(check_comparison(DATA / 'beed_controlled_seasonal_2020_2024.csv')), 120)
        self.assertEqual(len(check_history(DATA / 'beed_policy_history_2001_2024.csv', screened_bounds())), 288)
        self.assertEqual(load_rainfall(DATA / 'beed_chirps_monthly_1981_2024.csv').rain_for_spi_mm.notna().sum(), 528)

    def test_detects_changed_vhi(self):
        d = pd.read_csv(DATA / 'beed_controlled_seasonal_2020_2024.csv')
        d.loc[0, 'vhi'] += 1
        d.to_csv(self.path, index=False)
        with self.assertRaisesRegex(ValueError, 'formula identity'):
            check_comparison(self.path)

    def test_detects_missing_policy_row(self):
        d = pd.read_csv(DATA / 'beed_policy_history_2001_2024.csv').iloc[1:]
        d.to_csv(self.path, index=False)
        with self.assertRaisesRegex(ValueError, '288'):
            check_history(self.path, screened_bounds())

    def test_detects_screened_bound_violation(self):
        d = pd.read_csv(DATA / 'beed_policy_history_2001_2024.csv')
        d.loc[(d.year == 2023) & (d.month == 10) & (d.scenario == SCENARIOS[2]), 'ndvi_valid_fraction'] = .1
        d.to_csv(self.path, index=False)
        with self.assertRaisesRegex(ValueError, 'set bounds'):
            check_history(self.path, screened_bounds())

    def test_incomplete_rain_is_excluded_from_spi(self):
        d = pd.read_csv(DATA / 'beed_chirps_monthly_1981_2024.csv')
        d.loc[0, 'rain_days'] -= 1
        d.to_csv(self.path, index=False)
        loaded = load_rainfall(self.path)
        self.assertTrue(pd.isna(loaded.rain_for_spi_mm.iloc[0]))


if __name__ == '__main__':
    unittest.main()
