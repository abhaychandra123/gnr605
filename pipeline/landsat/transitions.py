"""Compare adjacent years on pair-specific shared pixels, never a chained area trend."""
import ctypes,json,subprocess
from pathlib import Path
import numpy as np
from common import DATA,OUT,YEARS,sha,save
from analyze import read,write,ptr,table

def library():
 src=Path(__file__).with_suffix('.cpp');target=src.parent/'build/transitions.dylib'
 if not target.exists() or target.stat().st_mtime<src.stat().st_mtime:
  subprocess.run(['clang++','-O3','-std=c++17','-dynamiclib',str(src),'-o',str(target)],check=True)
 lib=ctypes.CDLL(str(target));P=ctypes.c_void_p
 lib.transitions.argtypes=[ctypes.c_int,P,P,P,P,P,P];lib.transitions.restype=None;return lib

def main():
 lib=library();cfg=json.loads((DATA/'grid.json').read_text());mask=read('district_mask.tif');rows=[]
 for before,after in [(y,y+1) for y in YEARS[:-1]]+[(2015,2024)]:
  a=read(f'october_{before}_ndvi.tif');b=read(f'october_{after}_ndvi.tif');counts=np.zeros(8,dtype='uint64');sums=np.zeros(2);classes=np.empty(mask.shape,dtype='uint8')
  lib.transitions(mask.size,ptr(mask),ptr(a),ptr(b),ptr(counts),ptr(sums),ptr(classes));n=[int(x) for x in counts]
  assert n[1]==n[4]+n[5]+n[6]+n[7] and n[3]-n[2]==n[5]-n[6]
  rows.append({'before':before,'after':after,'shared_pixels':n[1],'shared_area_km2':n[1]*.0009,'shared_district_pct':100*n[1]/n[0],'before_vegetation_km2':n[2]*.0009,'after_vegetation_km2':n[3]*.0009,'net_change_km2':(n[3]-n[2])*.0009,'gain_km2':n[5]*.0009,'loss_km2':n[6]*.0009,'mean_ndvi_before':sums[0]/n[1] if n[1] else None,'mean_ndvi_after':sums[1]/n[1] if n[1] else None})
  if (before,after)==(2015,2024):write(DATA/'processed/transition_2015_2024.tif',classes,cfg,['0_stable_below_1_stable_vegetation_2_gain_3_loss_254_outside_255_unknown'],254)
 table(OUT/'pairwise_changes.csv',rows)
 save(OUT/'pairwise_provenance.json',{'code_sha256':sha(__file__),'kernel_sha256':sha(Path(__file__).with_suffix('.cpp')),'area_accounting':'passed','interpretation':'Each pair uses its own shared footprint; differences cannot be added or interpreted as a fixed-population time series. Threshold crossings are not proven land-use changes or drought impacts.'})
 print('PAIRWISE ANALYSIS COMPLETE')
if __name__=='__main__':main()
