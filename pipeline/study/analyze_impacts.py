"""Validate corrected real observations and run the declared exploratory checks."""
import hashlib,json,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/gnr605-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from analysis import spi,SCENARIOS
ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/'data/study_corrected';OUT=ROOT/'results/study_corrected'
WEIGHTS=['all_land','worldcover2021_crop_fraction']

def read_verified(stage,expected,keys):
 path=DATA/f'{stage}.csv';df=pd.read_csv(path)
 manifest=json.loads((DATA/f'{stage}.provenance.json').read_text())
 assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['csv_sha256']
 assert len(df)==expected and not df.duplicated(keys).any()
 cp=[r for p in sorted((DATA/'checkpoints'/stage).glob('*.json')) for r in json.loads(p.read_text())['rows']]
 check=pd.DataFrame(cp).sort_values(keys).reset_index(drop=True)
 pd.testing.assert_frame_equal(df.sort_values(keys).reset_index(drop=True).sort_index(axis=1),check.sort_index(axis=1),check_dtype=False,atol=1e-10,rtol=1e-12)
 assert (df.boundary_code==523).all()
 assert not np.isinf(df.select_dtypes('number')).any().any()
 return df

def validate():
 c=read_verified('comparison',240,['date','spatial_weighting','scenario','support'])
 h=read_verified('impacts',288,['date','spatial_weighting','scenario'])
 r=read_verified('rainfall',528,['date'])
 assert set(zip(c.date,c.spatial_weighting,c.scenario,c.support))=={(f'{y}-{m:02d}',w,s,p) for y in range(2020,2025) for m in [10,11,12] for w in WEIGHTS for s in SCENARIOS for p in ['own','all_variants_common']}
 assert set(zip(h.date,h.spatial_weighting,h.scenario))=={(f'{y}-{m:02d}',w,s) for y in range(2001,2025) for m in [10,11,12] for w in WEIGHTS for s in SCENARIOS[2:]}
 for df in [c,h]:
  assert df.valid_fraction.between(0,1+1e-8).all()
  assert np.allclose(df.valid_area_km2/df.weighted_support_area_km2,df.valid_fraction)
  good=df.valid_fraction>0
  assert df.loc[good,['vhi','vci','tci','ndvi','lst_k']].notna().all().all()
  assert np.allclose(df.loc[good,'vhi'],.5*(df.loc[good,'vci']+df.loc[good,'tci']),atol=1e-7)
  assert df.loc[good,'vhi_outside_0_100_fraction_valid'].between(0,1+1e-8).all()
 assert np.allclose(c[[f'class_{i}_fraction_valid' for i in range(5)]].sum(axis=1),1)
 common=c[c.support=='all_variants_common'];own=c[c.support=='own']
 assert common.groupby(['date','spatial_weighting']).valid_fraction.apply(lambda x:x.max()-x.min()).max()<1e-8
 joint=common.merge(own,on=['date','spatial_weighting','scenario'],suffixes=('_common','_own'))
 assert (joint.valid_fraction_common<=joint.valid_fraction_own+1e-8).all()
 current=h[h.year>=2020].merge(own,on=['date','spatial_weighting','scenario'],suffixes=('_h','_c'))
 for col in ['vhi','ndvi','lst_k','valid_fraction']:
  assert np.allclose(current[col+'_h'],current[col+'_c'],atol=1e-7)
 r=r.set_index(pd.PeriodIndex(r.date,freq='M')).sort_index()
 assert r.index.equals(pd.period_range('1981-01','2024-12',freq='M'))
 assert (r.rain_days==r.expected_days).all() and np.array_equal(r.expected_days,r.index.days_in_month)
 assert np.allclose(r.rain_valid_fraction,1,atol=1e-6) and r.rain_mm.ge(0).all()
 return c,h,r

def trend_predictions(years,yields,fit_mask):
 x=np.asarray(years,dtype=float)-2010;y=np.asarray(yields,dtype=float);mask=np.asarray(fit_mask,dtype=bool)
 coefficients=np.linalg.lstsq(np.column_stack([np.ones(mask.sum()),x[mask]]),y[mask],rcond=None)[0]
 return coefficients[0]+coefficients[1]*x,coefficients

def correlation(x,y):
 if len(x)<3 or np.ptp(x)==0 or np.ptp(y)==0:return np.nan
 return float(stats.spearmanr(x,y).statistic)

def main():
 c,h,r=validate();fits=[]
 for scale in [1,3,6,12]:
  r[f'spi_{scale}'],f=spi(r.rain_mm,scale);fits.append(f)
 r.to_csv(OUT/'rainfall_spi.csv',index=False)
 pd.concat(fits).to_csv(OUT/'spi_fit_diagnostics.csv',index=False)
 # Each seasonal statistic requires three eligible monthly observations.
 season=[]
 for (year,w,s),g in h.groupby(['year','spatial_weighting','scenario']):
  assert set(g.month)=={10,11,12}
  eligible=(g.valid_fraction>=.5).all()
  season.append(dict(year=year,spatial_weighting=w,scenario=s,minimum_monthly_coverage=g.valid_fraction.min(),
   eligible_50pct=bool(eligible),eligible_75pct=bool((g.valid_fraction>=.75).all()),
   vhi=g.vhi.mean() if eligible else np.nan,ndvi=g.ndvi.mean() if eligible else np.nan,
   lst_observations=g.lst_observations.mean(),outside_fraction=g.vhi_outside_0_100_fraction_valid.mean()))
 season=pd.DataFrame(season);season.to_csv(OUT/'seasonal_indicators.csv',index=False)
 yields=pd.read_csv(OUT/'crop_yields.csv');targets=[]
 for crop,g in yields[yields.crop.isin(['rabi_jowar','wheat','chickpea'])].groupby('crop'):
  g=g.sort_values('start_year').copy();g['year']=g.start_year
  train=g.year.between(2001,2019)
  g['trend_prediction'],coef=trend_predictions(g.year,g.yield_kg_ha,train)
  g['climatology_prediction']=g.loc[train,'yield_kg_ha'].mean()
  g['persistence_prediction']=g.yield_kg_ha.shift(1)
  g['yield_residual']=g.yield_kg_ha-g.trend_prediction
  g['yield_residual_pct']=100*g.yield_residual/g.trend_prediction
  g['trend_kg_ha_per_year']=coef[1]
  targets.append(g)
 targets=pd.concat(targets);targets.to_csv(OUT/'yield_targets.csv',index=False)
 # Predeclared features; rainfall is whole-district native-grid, not crop-weighted.
 features=[]
 for (w,s),g in season.groupby(['spatial_weighting','scenario']):
  for indicator in ['vhi','ndvi']:
   q=g[['year',indicator,'eligible_75pct']].rename(columns={indicator:'indicator'}).copy()
   q['feature']=f'{w}__{s[0]}__{indicator}';q['family']=indicator;features.append(q)
 for scale in [3,6]:
  q=r[(r.month==12)&r.year.between(2001,2024)][['year',f'spi_{scale}']].rename(columns={f'spi_{scale}':'indicator'}).copy()
  q['feature']=f'district_SPI{scale}_December';q['family']='spi';q['eligible_75pct']=True
  features.append(q)
 features=pd.concat(features,ignore_index=True)
 predictions=[];summaries=[];coefs=[]
 for crop,g in targets.groupby('crop'):
  for feature,f in features.groupby('feature'):
   merged=g.merge(f,on='year');train=merged[merged.year.between(2001,2019)].dropna(subset=['indicator','yield_residual'])
   test=merged[merged.year.between(2020,2024)].dropna(subset=['indicator','yield_residual']).copy()
   if len(train)<10 or len(test)<3:
    summaries.append(dict(crop=crop,feature=feature,n_train=len(train),n_test=len(test),status='insufficient'))
    continue
   coef=np.linalg.lstsq(np.column_stack([np.ones(len(train)),train.indicator]),train.yield_residual,rcond=None)[0]
   test['indicator_prediction']=test.trend_prediction+coef[0]+coef[1]*test.indicator
   test['feature']=feature
   predictions.append(test)
   coefs.append(dict(crop=crop,feature=feature,intercept=coef[0],slope=coef[1],train_first=int(train.year.min()),train_last=int(train.year.max())))
   rho=correlation(test.indicator,test.yield_residual)
   loo=[correlation(test.indicator.drop(i),test.yield_residual.drop(i)) for i in test.index]
   summary=dict(crop=crop,feature=feature,n_train=len(train),n_test=len(test),status='exploratory',
    train_spearman=correlation(train.indicator,train.yield_residual),test_spearman=rho,
    test_spearman_leave_one_out_min=float(np.nanmin(loo)),test_spearman_leave_one_out_max=float(np.nanmax(loo)),
    test_years=','.join(str(int(x)) for x in test.year),test_eligible_75pct=int(test.eligible_75pct.sum()))
   for model in ['climatology','trend','persistence','indicator']:
    error=test[model+'_prediction']-test.yield_kg_ha
    summary[model+'_mae']=error.abs().mean();summary[model+'_rmse']=np.sqrt(np.mean(error**2))
   gain=(test.trend_prediction-test.yield_kg_ha).abs()-(test.indicator_prediction-test.yield_kg_ha).abs()
   summary['mae_gain_over_trend']=gain.mean()
   summary['mae_gain_leave_one_test_year_out_min']=min(gain.drop(i).mean() for i in gain.index)
   summary['mae_gain_leave_one_test_year_out_max']=max(gain.drop(i).mean() for i in gain.index)
   tight=test[test.eligible_75pct]
   summary['mae_gain_at_75pct_coverage']=((tight.trend_prediction-tight.yield_kg_ha).abs()-(tight.indicator_prediction-tight.yield_kg_ha).abs()).mean()
   summaries.append(summary)
 summary=pd.DataFrame(summaries);summary.to_csv(OUT/'impact_agreement.csv',index=False)
 pred=pd.concat(predictions);pred.to_csv(OUT/'test_predictions.csv',index=False)
 pd.DataFrame(coefs).to_csv(OUT/'indicator_regression_parameters.csv',index=False)
 # Differences include changing valid support; this is not a pure condition effect.
 old=pd.read_csv(ROOT/'data/study/beed_controlled_seasonal_2020_2024.csv')
 delta=c[c.spatial_weighting=='all_land'].merge(old,on=['date','scenario','support'],suffixes=('_soi','_gaul'))
 for col in ['vhi','valid_fraction','ndvi']:delta[col+'_difference']=delta[col+'_soi']-delta[col+'_gaul']
 delta[['date','scenario','support','vhi_difference','valid_fraction_difference','ndvi_difference']].to_csv(OUT/'boundary_effect.csv',index=False)
 cropdiff=c[c.spatial_weighting==WEIGHTS[1]].merge(c[c.spatial_weighting=='all_land'],on=['date','scenario','support'],suffixes=('_crop','_land'))
 for col in ['vhi','valid_fraction','ndvi']:cropdiff[col+'_difference']=cropdiff[col+'_crop']-cropdiff[col+'_land']
 cropdiff[['date','scenario','support','vhi_difference','valid_fraction_difference','ndvi_difference']].to_csv(OUT/'crop_weight_effect.csv',index=False)
 plot(c,season,targets,summary)
 validation=dict(comparison_rows=len(c),impact_month_rows=len(h),rainfall_rows=len(r),crop_rows=len(yields),
  csv_checkpoint_identity='passed',expected_keys='passed',vhi_identity='passed',class_partitions='passed',
  common_support_consistency='passed',comparison_vs_impact_post2019='passed',rainfall_full_support_months=int(r.rain_valid_fraction.ge(1-1e-6).sum()),
  all_land_grid_area_km2=float(c[c.spatial_weighting=='all_land'].weighted_support_area_km2.iloc[0]),
  cropland_weighted_area_km2=float(c[c.spatial_weighting==WEIGHTS[1]].weighted_support_area_km2.iloc[0]),
  eligible_seasons_50pct=int(season.eligible_50pct.sum()),eligible_seasons_75pct=int(season.eligible_75pct.sum()))
 (OUT/'validation.json').write_text(json.dumps(validation,indent=2))
 print(json.dumps(validation,indent=2));print(summary[['crop','feature','n_train','n_test','test_spearman','mae_gain_over_trend']].to_string(index=False))

def plot(c,season,targets,summary):
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 fig,axs=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
 for j,w in enumerate(WEIGHTS):
  for i,s in enumerate(SCENARIOS):
   g=c[(c.spatial_weighting==w)&(c.month==10)&(c.scenario==s)&(c.support=='own')].sort_values('year')
   axs[0,j].plot(g.year,g.valid_fraction*100,'o-',label=s[0])
   axs[1,j].plot(g.year,g.vhi,'o-',label=s[0])
  axs[0,j].set_title('Whole district' if w=='all_land' else 'Cropland-fraction weighting')
  axs[0,j].set_ylim(0,100);axs[0,j].set_ylabel('October VHI coverage (%)');axs[0,j].legend(ncol=4)
  axs[1,j].set_ylabel('October mean VHI (own support)')
  for ax in axs[:,j]:ax.set_xticks(range(2020,2025));ax.grid(alpha=.2)
 fig.suptitle('Official Beed boundary: actual corrected reconstruction\nCoverage and means use the labelled weighted support')
 fig.savefig(OUT/'corrected_comparison.png',dpi=170);plt.close(fig)
 fig,axs=plt.subplots(3,1,figsize=(12,10),constrained_layout=True,sharex=True)
 cropseason=season[(season.spatial_weighting==WEIGHTS[1])&(season.scenario==SCENARIOS[2])].set_index('year')
 for ax,(crop,g) in zip(axs,targets.groupby('crop')):
  g=g[g.year>=2001];ax.bar(g.year,g.yield_residual_pct,color='#6585a1',alpha=.65,label='Reported yield minus training trend (%)')
  ax.axhline(0,color='gray',lw=.7);ax.axvline(2019.5,color='black',ls=':');ax.set_title(crop.replace('_',' ').title())
  ax.set_ylabel('Yield residual (%)');other=ax.twinx();other.plot(cropseason.index,cropseason.vhi,'o-',ms=3,color='#b35e27',label='Cropland VHI, policy C');other.set_ylabel('OND VHI')
  if crop==sorted(targets.crop.unique())[0]:
   lines,labs=ax.get_legend_handles_labels();l2,la2=other.get_legend_handles_labels();ax.legend(lines+l2,labs+la2,loc='lower left',fontsize=8)
 axs[-1].set_xticks(range(2001,2025,2));fig.suptitle('Exploratory crop-impact agreement: all three OND months required\n2001-2019 yield trend; 2020-2024 evaluation; dual axes show different units')
 fig.savefig(OUT/'yield_indicator_history.png',dpi=170);plt.close(fig)
 fig,axs=plt.subplots(1,3,figsize=(14,6),constrained_layout=True)
 feats=[f'{WEIGHTS[1]}__C__vhi',f'{WEIGHTS[1]}__D__vhi','district_SPI3_December','district_SPI6_December']
 for ax,(crop,g) in zip(axs,summary.groupby('crop')):
  q=g.set_index('feature').loc[feats];base=q.iloc[0]
  values=[base.climatology_mae,base.trend_mae,base.persistence_mae,*q.indicator_mae.tolist()]
  labels=['Training mean','Training trend','Previous-year yield','C crop VHI','D crop VHI','December SPI-3','December SPI-6']
  bars=ax.barh(labels,values,color=['#b8b8b8','#8d8d8d','#24764f','#628797','#529f91','#d49a56','#bd7157'])
  ax.bar_label(bars,fmt='%.0f',padding=4,fontsize=9);ax.invert_yaxis();ax.set_xlim(0,max(values)*1.17)
  ax.set_title(crop.replace('_',' ').title());ax.set_xlabel('Test MAE (kg/ha), lower is better');ax.grid(axis='x',alpha=.15)
 fig.suptitle('Previous-year yield beats the displayed indicator calibrations\n2020-2024: five years per crop; calibration fits use 2001-2019 only')
 fig.savefig(OUT/'holdout_error_comparison.png',dpi=170);plt.close(fig)

if __name__=='__main__':main()
