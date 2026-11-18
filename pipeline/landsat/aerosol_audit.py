"""Audit added coverage if high aerosol were admitted, without using it as truth."""
import ctypes,json,subprocess,csv
from pathlib import Path
import numpy as np
import rasterio
from analyze import ptr,read,write,table
from common import DATA,OUT,ROOT,YEARS,sha,save

def main():
 src=Path(__file__).with_suffix('.cpp');target=src.parent/'build/aerosol_audit.dylib'
 subprocess.run(['clang++','-O3','-std=c++17','-dynamiclib',str(src),'-o',str(target)],check=True)
 lib=ctypes.CDLL(str(target));P=ctypes.c_void_p;I=ctypes.c_int
 lib.coverage_without_high_aerosol_exclusion.argtypes=[P,I,I,I,I,I,P,P];lib.coverage_without_high_aerosol_exclusion.restype=None
 lib.audit_counts.argtypes=[I,P,P,P,P,P];lib.audit_counts.restype=None
 cfg=json.loads((DATA/'grid.json').read_text());man=json.loads((DATA/'download_manifest.json').read_text())
 mask=read('district_mask.tif');common=np.ones(mask.shape,dtype='uint8');rows=[]
 for year in YEARS:
  possible=np.zeros(mask.shape,dtype='uint8')
  for rec in man['files']:
   j=rec['request']
   if j['scene'][-8:-4]!=str(year):continue
   with rasterio.open(ROOT/rec['path']) as s:b=s.read()
   lib.coverage_without_high_aerosol_exclusion(ptr(b),j['height'],j['width'],j['row'],j['col'],cfg['width'],ptr(mask),ptr(possible))
  strict=read(f'october_{year}_observations.tif');counts=np.zeros(5,dtype='uint64')
  lib.audit_counts(mask.size,ptr(mask),ptr(strict),ptr(possible),ptr(common),ptr(counts));assert counts[3]==0
  row={'year':year,'district_pixels':int(counts[0]),'primary_valid_pixels':int(counts[1]),'if_high_aerosol_included_pixels':int(counts[2]),'primary_coverage_pct':100*int(counts[1])/int(counts[0]),'if_high_aerosol_included_coverage_pct':100*int(counts[2])/int(counts[0])}
  rows.append(row);print(year,round(row['primary_coverage_pct'],1),'->',round(row['if_high_aerosol_included_coverage_pct'],1),'% diagnostic only',flush=True)
 table(OUT/'aerosol_coverage_diagnostic.csv',rows)
 save(OUT/'aerosol_audit.json',{'interpretation':'Counterfactual coverage only. High-aerosol pixels are not admitted to the primary NDVI/vegetation calculation.','common_if_high_aerosol_included_pct':100*int(counts[4])/int(counts[0]),'strict_nested_in_diagnostic':'passed','code_sha256':sha(__file__),'kernel_sha256':sha(src)})
if __name__=='__main__':main()
