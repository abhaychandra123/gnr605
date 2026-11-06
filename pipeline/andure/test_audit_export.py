"""Synthetic fixtures test failure detection. These are not Beed observations."""
import csv
import tempfile
import unittest
from pathlib import Path
from audit_export import audit


class ExportAuditTests(unittest.TestCase):
    def run_fixture(self, updates=None, duplicate=False, second_updates=None):
        row = dict(date='2020-10', ndvi=0.4, lst_k=300, vci=40, tci=60,
                   vhi=50, alpha=0.5, valid_fraction=0.9,
                   valid_area_km2=90, district_area_km2=100,
                   rain_mm=50, rain_3month_mm=200, rain_days=31,
                   rain_expected_days=31, rain_3month_days=92,
                   rain_3month_expected_days=92)
        row.update(updates or {})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.csv'
            with path.open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=row.keys())
                writer.writeheader()
                writer.writerows([row] * (2 if duplicate else 1))
                if second_updates is not None:
                    writer.writerow(dict(row, **second_updates))
            return audit(path)

    def test_valid_formula(self):
        result = self.run_fixture()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['formula_max_abs_error'], 0)

    def test_incorrect_formula_fails(self):
        self.assertTrue(any('formula mismatch' in s for s in self.run_fixture({'vhi': 51})['errors']))

    def test_celsius_is_rejected(self):
        self.assertTrue(any('kelvin' in s for s in self.run_fixture({'lst_k': 27})['errors']))

    def test_missing_values_remain_missing(self):
        result = self.run_fixture(dict(vci='', tci='', vhi='', ndvi='', lst_k='',
                                       valid_fraction=0, valid_area_km2=0))
        self.assertEqual(result['errors'], [])
        self.assertIsNone(result['formula_max_abs_error'])
        self.assertTrue(result['warnings'])

    def test_duplicate_dates_fail(self):
        self.assertTrue(any('duplicate' in s for s in self.run_fixture(duplicate=True)['errors']))

    def test_outside_baseline_not_clipped(self):
        result = self.run_fixture(dict(vci=120, tci=100, vhi=110))
        self.assertEqual(result['errors'], [])
        self.assertTrue(any('not clipped' in s for s in result['warnings']))

    def test_nan_is_rejected(self):
        self.assertTrue(self.run_fixture({'vhi': 'nan'})['errors'])

    def test_same_month_different_settings_pass(self):
        result = self.run_fixture(dict(min_ndvi_years=15, min_lst_years=15),
                                  second_updates=dict(min_ndvi_years=12))
        self.assertEqual(result['errors'], [])

    def test_same_month_same_settings_fail(self):
        result = self.run_fixture(dict(min_ndvi_years=15, min_lst_years=15), duplicate=True)
        self.assertTrue(any('duplicate' in s for s in result['errors']))

    def test_missing_variant_setting_fails(self):
        self.assertTrue(self.run_fixture(dict(min_ndvi_years=12))['errors'])


if __name__ == '__main__':
    unittest.main()
