"""Fill disjoint future-year checkpoints with at most two independent EE requests.

Run alongside execute_corrected only while its forward cursor remains before 2009.
Calculations and checkpoint signatures are exactly those of execute_corrected.py.
"""
import hashlib,json
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import ee
from execute_corrected import CorrectedStudy,OUT,GEO,ROOT
from execute_ee import compute,atomic_json

def chunk(years):
 ee.Initialize(project='weighttrack-493810');ee.data.setDeadline(180000)
 land=CorrectedStudy();crop=CorrectedStudy(True)
 files=[ROOT/'pipeline/study/execute_corrected.py',ROOT/'pipeline/study/execute_ee.py',GEO]
 signature=hashlib.sha256(b''.join(x.read_bytes() for x in files)).hexdigest()
 for year in years:
  for month in [10,11,12]:
   dest=OUT/'checkpoints/impacts'/f'{year}-{month:02d}.json'
   if dest.exists():
    assert json.loads(dest.read_text())['implementation_sha256']==signature;continue
   part=compute([f for s in [land,crop] for f in s.impacts(year,month)])
   if dest.exists():raise RuntimeError('Forward cursor reached prefill range; stop overlapping workers')
   atomic_json(dest,{'rows':part,'implementation_sha256':signature,'retrieved_utc':datetime.now(timezone.utc).isoformat()})
   print(f'prefill impacts {year}-{month:02d}: {len(part)} real rows',flush=True)
 return list(years)

if __name__=='__main__':
 with ProcessPoolExecutor(max_workers=2) as pool:
  for done in pool.map(chunk,[range(2009,2017),range(2017,2025)]):print('Completed years',done,flush=True)
