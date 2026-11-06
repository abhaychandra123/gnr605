"""Auditable five-crop extraction; repair merged headers, verify row alignment."""
import hashlib,json,re
from pathlib import Path
import pandas as pd
import pdfplumber
ROOT=Path(__file__).resolve().parents[2]
IN=ROOT/'data/study/ancillary'; OUT=ROOT/'results/study_corrected'
CROPS={'rabijowar':'rabi_jowar','wheat':'wheat','gram':'chickpea','soyabeen':'soybean',
 'soyabean':'soybean','khsoybean':'soybean','cotton':'cotton_lint','cottonlint':'cotton_lint'}
def clean(s):return re.sub('[^a-z]','',s.lower())
def halfunit(s):return .5*10**(-len(s.split('.')[1])) if '.' in s else .5

def main():
 rows=[];issues=[]
 for path in sorted(IN.glob('official_apy_*.pdf')):
  year=int(path.stem.split('_')[2])
  if year>2024:continue
  with pdfplumber.open(path) as doc:
   for pn,page in enumerate(doc.pages,1):
    text=page.extract_text() or '';lines=text.splitlines()
    beed=[re.split(r'Beed\s+',l,maxsplit=1)[1].split() for l in lines if re.match(r'^(?:\d+\s*)?Beed\s+',l)]
    for table in page.extract_tables():
     h=next((i for i,r in enumerate(table[:6]) if 'District' in r),None)
     if h is None:continue
     di=table[h].index('District');header=table[h]
     if sum(x=='A' for x in header)>1:header=table[h-1]
     labels=[''.join(x or '' for x in header[k:k+3]).replace('\n',' ') for k in range(di+1,len(header),3)]
     # Page's printed rightmost column falls outside detected table border in 2019.
     if year==2019 and pn==3:
      assert re.search(r'Kharif Sunflower\s+Soyabeen',text)
      assert len(labels)==6 and labels[-1]==''
      labels[-1]='Soyabeen'
     for gi,label in enumerate(labels):
      crop=CROPS.get(clean(label))
      if not crop:continue
      k=di+1+gi*3;tablevalues=None
      for row in table[h+1:]:
       districts=(row[di] or '').split('\n')
       if 'Beed' not in districts:continue
       take=districts.index('Beed');cells=row[k:k+3]
       if len(cells)==3 and all(len((c or '').split('\n'))==len(districts) for c in cells):
        tablevalues=[(c or '').split('\n')[take] for c in cells]
      linevalues=None
      if len(beed)==1 and len(beed[0])==len(labels)*3:
       linevalues=beed[0][gi*3:gi*3+3]
      if tablevalues is not None and linevalues is not None and tablevalues!=linevalues:
       raise ValueError((year,pn,crop,tablevalues,linevalues))
      values=tablevalues or linevalues
      if values is None or not all(re.fullmatch(r'\d+(?:\.\d+)?',x) for x in values):
       issues.append({'year':year,'page':pn,'crop':crop,'values':values});continue
      area,prod,yieldkg=map(float,values)
      assert area>0 and prod>0 and yieldkg>0
      factor=170 if crop=='cotton_lint' else 1000
      amin,amax=area-halfunit(values[0]),area+halfunit(values[0])
      pmin,pmax=prod-halfunit(values[1]),prod+halfunit(values[1])
      ymin,ymax=yieldkg-halfunit(values[2]),yieldkg+halfunit(values[2])
      compatible=(pmin*factor/amax<=ymax and pmax*factor/amin>=ymin)
      units='\n'.join(l for l in lines if any(t in l.lower() for t in ['area in','bales','tonnes','productivity in']))
      rows.append(dict(start_year=year,agricultural_year=f'{year}-{str(year+1)[-2:]}',crop=crop,
       area_ha=area*100,production_t=prod*(17 if crop=='cotton_lint' else 100),yield_kg_ha=yieldkg,
       area_raw=values[0],production_raw=values[1],yield_raw=values[2],crop_label_source=label,
       ratio_implied_yield_kg_ha=prod*factor/area,rounding_compatible=compatible,
       extraction='table_and_text_agree' if tablevalues and linevalues else ('table_aligned' if tablevalues else 'complete_text_row'),
       source_file=path.name,source_page=pn,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
       source_title=lines[0],source_units=units,
       yield_status='official_reported_not_independently_field_validated'))
  print(year,len(rows),flush=True)
 df=pd.DataFrame(rows)
 assert not df.duplicated(['start_year','crop']).any()
 expected={(y,c) for y in range(2000,2025) for c in set(CROPS.values())}
 missing=expected-set(map(tuple,df[['start_year','crop']].values))
 if missing:raise ValueError(f'Missing {missing}; issues {issues}')
 assert len(df)==125
 OUT.mkdir(exist_ok=True);df.to_csv(OUT/'crop_yields.csv',index=False)
 (OUT/'yield_validation.json').write_text(json.dumps({'rows':len(df),'issues':issues,
  'rounding_discrepancies':df.loc[~df.rounding_compatible,['start_year','crop','area_raw','production_raw','yield_raw','ratio_implied_yield_kg_ha','source_page']].to_dict('records'),
  'note':'Reported yield retained. Rounding-incompatible rows require source review, not silent correction.'},indent=2))
 print(df.loc[~df.rounding_compatible,['start_year','crop','yield_kg_ha','ratio_implied_yield_kg_ha']].to_string(index=False))
if __name__=='__main__':main()
