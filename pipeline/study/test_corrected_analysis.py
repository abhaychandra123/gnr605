"""Regression checks for independent outcomes and temporal split integrity."""
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from analyze_impacts import trend_predictions
ROOT=Path(__file__).resolve().parents[2]
class CorrectedAnalysisTests(unittest.TestCase):
 def test_yield_trend_ignores_evaluation_outcomes(self):
  data=pd.read_csv(ROOT/'results/study_corrected/crop_yields.csv')
  for crop in ['rabi_jowar','wheat','chickpea']:
   g=data[data.crop==crop];mask=g.start_year.between(2001,2019)
   original,coef=trend_predictions(g.start_year,g.yield_kg_ha,mask)
   altered=g.yield_kg_ha.where(g.start_year<2020,1e9)
   new,coef_new=trend_predictions(g.start_year,altered,mask)
   np.testing.assert_array_equal(original,new);np.testing.assert_array_equal(coef,coef_new)
 def test_crop_rows_cover_exactly_the_sources(self):
  data=pd.read_csv(ROOT/'results/study_corrected/crop_yields.csv')
  self.assertEqual(set(zip(data.start_year,data.crop)),{(y,c) for y in range(2000,2025) for c in ['rabi_jowar','wheat','chickpea','soybean','cotton_lint']})
  self.assertEqual(len(data),125)
  self.assertTrue(data.rounding_compatible.all())
 def test_repaired_split_headers_and_border_columns(self):
  data=pd.read_csv(ROOT/'results/study_corrected/crop_yields.csv').set_index(['start_year','crop'])
  # Values visually checked in their original official PDF pages.
  self.assertEqual(data.loc[(2011,'rabi_jowar'),'yield_kg_ha'],691)
  self.assertEqual(data.loc[(2011,'wheat'),'yield_kg_ha'],1326)
  self.assertEqual(data.loc[(2019,'soybean'),'yield_kg_ha'],775.34)
  self.assertEqual(data.loc[(2024,'cotton_lint'),'yield_kg_ha'],215.90)
if __name__=='__main__':unittest.main()
