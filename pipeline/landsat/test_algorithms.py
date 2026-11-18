import unittest,ctypes
import numpy as np
from common import utm43
from analyze import library,ptr,alg
class Tests(unittest.TestCase):
 def setUp(self):self.lib=library()
 def sample(self):
  b=np.full((10,1,1),10000,dtype='uint16');b[3,0,0]=12000;b[4,0,0]=20000;b[7:]=0;return b
 def test_utm_known_reference(self):
  x,y=utm43(75,19);self.assertAlmostEqual(x,500000,places=6);self.assertAlmostEqual(y,2100827.4518009634,delta=.01)
 def test_cloud_saturation_aerosol_and_offset(self):
  b=self.sample();self.assertEqual(self.lib.valid_observation(ptr(b),1,0),0)
  for band,value in [(7,1),(7,2),(7,4),(7,8),(7,16),(7,32),(8,1),(8,2048),(9,192)]:
   a=b.copy();a[band,0,0]=value;self.assertNotEqual(self.lib.valid_observation(ptr(a),1,0),0)
  a=b.copy();a[7]=128;self.assertEqual(self.lib.valid_observation(ptr(a),1,0),0)
 def test_same_date_dedup_scale_and_class(self):
  b=self.sample();mask=np.ones((1,1),dtype='uint8');last=np.zeros((1,1),dtype='uint16');count=last.copy();total=np.zeros((1,1));ref=np.zeros((7,1,1));qa=np.zeros(10,dtype='uint64')
  for date in [1,1,2]:self.lib.accumulate(ptr(b),1,1,0,0,1,1,ptr(mask),date,ptr(last),ptr(count),ptr(total),ptr(ref),ptr(qa))
  self.assertEqual(count[0,0],2)
  expected=(.35-.13)/(.35+.13);self.assertAlmostEqual(total[0,0]/2,expected)
  self.assertNotAlmostEqual(expected,(20000-12000)/(20000+12000))
  ndvi=np.empty((1,1));mean=np.empty((7,1,1),dtype='float32');classes=np.empty((1,1),dtype='uint8')
  self.lib.finish(1,ptr(mask),ptr(count),ptr(total),ptr(ref),ptr(ndvi),ptr(mean),ptr(classes))
  self.assertAlmostEqual(ndvi[0,0],expected);self.assertEqual(classes[0,0],1)
 def test_unknown_and_outside_stay_distinct(self):
  mask=np.array([[1,0]],dtype='uint8');count=np.zeros((1,2),dtype='uint16');total=np.zeros((1,2));ref=np.zeros((7,1,2));ndvi=total.copy();mean=ref.astype('float32');classes=mask.copy()
  self.lib.finish(2,ptr(mask),ptr(count),ptr(total),ptr(ref),ptr(ndvi),ptr(mean),ptr(classes))
  self.assertEqual(classes.tolist(),[[255,254]]);self.assertEqual(ndvi.tolist(),[[-9999,-9999]])
 def test_transition_accounting_and_unknown(self):
  from transitions import library as transitions_library
  a=np.array([[.5,.2,.6,.1,-9999]],dtype='float64');b=np.array([[.6,.4,.2,.2,.5]],dtype='float64')
  mask=np.ones((1,5),dtype='uint8');counts=np.zeros(8,dtype='uint64');sums=np.zeros(2);classes=mask.copy()
  transitions_library().transitions(5,ptr(mask),ptr(a),ptr(b),ptr(counts),ptr(sums),ptr(classes))
  self.assertEqual(classes.tolist(),[[1,2,3,0,255]])
  self.assertEqual(counts.tolist(),[5,4,2,2,1,1,1,1])
if __name__=='__main__':unittest.main()
