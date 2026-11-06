"""Small mathematical fixtures, never substituted for observed satellite data."""
import unittest
from vegetation import polygon_mask,quality_ok,ndvi_value,is_vegetation,linear_slope,statistics
class AlgorithmTests(unittest.TestCase):
 def test_scanline_square_with_hole(self):
  outer=[(0,0),(4,0),(4,4),(0,4),(0,0)];hole=[(1,1),(3,1),(3,3),(1,3),(1,1)]
  m=polygon_mask([outer,hole],4,4,[1,0,0,0,-1,4])
  expected=[[1,1,1,1],[1,0,0,1],[1,0,0,1],[1,1,1,1]]
  self.assertEqual(m.tolist(),expected)
 def test_qa_rejects_cloud_shadow_aerosol_and_bad_red_nir(self):
  land=1<<3
  self.assertTrue(quality_ok(0,land))
  for bit in [0,2,8,10,12,13,15]:self.assertFalse(quality_ok(0,land|(1<<bit)))
  self.assertFalse(quality_ok(0,land|(3<<6)))
  self.assertFalse(quality_ok(1,land));self.assertFalse(quality_ok(1<<2,land));self.assertFalse(quality_ok(1<<6,land))
  self.assertFalse(quality_ok(0,0))
 def test_ndvi_scale_cancels_and_invalid_denominator_stays_missing(self):
  self.assertAlmostEqual(ndvi_value(1000,3000),.5)
  self.assertAlmostEqual(ndvi_value(.1,.3),.5)
  self.assertIsNone(ndvi_value(0,0));self.assertIsNone(ndvi_value(-1,3000))
  self.assertFalse(is_vegetation(.3,.3));self.assertFalse(is_vegetation(.3+1e-15,.3))
  self.assertTrue(is_vegetation(.300001,.3))
 def test_known_slope_and_every_year_decline(self):
  slope,intercept=linear_slope([0,1,2],[10,8,6]);self.assertEqual((slope,intercept),(-2,10))
  s=statistics([2015,2016,2017],[10,8,6]);self.assertTrue(s['decreases_every_year']);self.assertEqual(s['sen_km2_per_year'],-2)
  self.assertFalse(statistics([2015,2016,2017],[10,8,9])['decreases_every_year'])
if __name__=='__main__':unittest.main()
