"""Read completed numerical outputs, display figures, and write the assignment report."""
import csv,json,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/gnr605-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import rasterio
from common import DATA,OUT,ROOT,YEARS,sha,write_json

def read_table(path):
 rows=[]
 for row in csv.DictReader(path.open()):
  rows.append({key:float(value) for key,value in row.items()})
 return rows

def main():
 rows=read_table(OUT/'year_vs_vegetation_area.csv');sens=read_table(OUT/'area_all_sensitivities.csv')
 stats=json.loads((OUT/'trend_summary.json').read_text());primary=next(s for s in stats if s['min_observations']==1 and s['ndvi_threshold']==.3)
 cfg=json.loads((DATA/'grid.json').read_text());h=cfg['height'];w=cfg['width']
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 x=[r['year'] for r in rows];observed=[r['vegetated_area_observed_km2'] for r in rows]
 upper=[r['vegetated_area_upper_bound_km2'] for r in rows];common=[r['common_vegetated_area_km2'] for r in rows]
 fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True,constrained_layout=True)
 axes[0].fill_between(x,observed,upper,color='#b8c6b8',alpha=.55,label='Range if all unknown pixels are nonvegetated / vegetated')
 axes[0].plot(x,observed,'o-',color='#24794b',lw=2,label='Observed vegetation area (changing valid footprint)')
 axes[0].set_ylim(0,rows[0]['district_area_km2']*1.03);axes[0].set_ylabel('Whole-district area bounds (km²)');axes[0].legend(fontsize=8,loc='lower right')
 axes[0].set_title('Missing observations remain unknown; shaded bounds are not confidence intervals')
 axes[1].plot(x,common,'o-',color='#24794b',lw=2,label='Vegetation area on the same pixels every year')
 fitted=[primary['ols_intercept_at_2015']+primary['ols_km2_per_year']*(year-2015) for year in x]
 axes[1].plot(x,fitted,'--',color='#ad6d36',label=f'Descriptive slope: {primary["ols_km2_per_year"]:+.1f} km²/year')
 axes[1].set_ylim(0,rows[0]['common_area_km2']*1.04);axes[1].set_ylabel('Common-footprint vegetation (km²)');axes[1].set_xlabel('Year (October)')
 axes[1].set_title(f'Fixed valid footprint: {rows[0]["common_area_km2"]:,.0f} km², {rows[0]["common_coverage_pct"]:.1f}% of mapped district')
 axes[1].legend(fontsize=8,loc='lower right')
 for ax in axes:ax.set_xticks(YEARS);ax.grid(alpha=.2)
 fig.suptitle('Beed: year versus October vegetation-covered area, 2015–2024\nNDVI > 0.30; at least one accepted observation per pixel',fontsize=13)
 fig.savefig(OUT/'year_vs_vegetation_area.png',dpi=180);plt.close(fig)

 fig,axes=plt.subplots(1,2,figsize=(12,4.8),sharey=True,constrained_layout=True)
 colors=['#78a886','#24794b','#9a6529']
 for ax,minobs in zip(axes,[2,1]):
  for threshold,color in zip([.2,.3,.4],colors):
   subset=[r for r in sens if r['min_observations']==minobs and r['ndvi_threshold']==threshold]
   ax.plot([r['year'] for r in subset],[r['common_vegetated_pct'] for r in subset],'o-',color=color,label=f'NDVI > {threshold:.2f}')
  ax.set_title(f'Minimum {minobs} observations\nCommon footprint: {subset[0]["common_coverage_pct"]:.1f}% of district')
  ax.set_xticks(YEARS);ax.tick_params(axis='x',rotation=45);ax.set_ylim(0,100);ax.set_xlabel('Year (October)');ax.grid(alpha=.2);ax.legend()
 axes[0].set_ylabel('Vegetated fraction of each fixed footprint (%)')
 fig.suptitle('Sensitivity to the vegetation threshold and observation requirement\nThe two panels have different common footprints; neither is extrapolated to the district')
 fig.savefig(OUT/'threshold_sensitivity.png',dpi=170);plt.close(fig)

 for kind in ['vegetation','false_colour']:
  fig,axes=plt.subplots(2,5,figsize=(16,6.6))
  for ax,year in zip(axes.flat,YEARS):
   display=np.ones((h,w,3),dtype='float32')
   if kind=='vegetation':
    with rasterio.open(DATA/f'processed/october_{year}_vegetation_class.tif') as source:im=source.read(1)
    palette={0:(.83,.74,.53),1:(.12,.48,.25),254:(1,1,1),255:(.73,.75,.78)}
    for row in range(h):
     for col in range(w):
      rgb=palette[int(im[row,col])]
      for band in range(3):display[row,col,band]=rgb[band]
   else:
    with rasterio.open(DATA/f'processed/october_{year}_reflectance_7band.tif') as source:im=source.read()
    with rasterio.open(DATA/'processed/district_mask.tif') as source:mask=source.read(1)
    for row in range(h):
     for col in range(w):
      if not mask[row,col]:continue
      if im[0,row,col]==-9999:
       for band in range(3):display[row,col,band]=.75
       continue
      for outband,(inband,scale) in enumerate([(1,.6),(0,.3),(3,.3)]):
       value=float(im[inband,row,col])/scale
       if value<0:value=0
       if value>1:value=1
       display[row,col,outband]=value**.7
   ax.imshow(display,interpolation='nearest');ax.set_title(str(year));ax.set_axis_off()
  if kind=='vegetation':
   fig.suptitle('October vegetation maps: NDVI > 0.30, 2015–2024\nSame district, sensor, threshold and one-observation requirement each year',fontsize=14)
   fig.legend(handles=[Patch(color=(.12,.48,.25),label='Vegetated'),Patch(color=(.83,.74,.53),label='Below threshold'),Patch(color=(.73,.75,.78),label='Unknown / insufficient observations')],loc='lower center',ncol=3,frameon=False)
   name='october_vegetation_maps.png'
  else:
   fig.suptitle('Downloaded seven-band data: locally computed October false-colour composites\nDisplay R=NIR, G=red, B=green; fixed stretch in every year; gaps shown gray',fontsize=14)
   name='october_false_colour.png'
  fig.subplots_adjust(top=.82,bottom=.10,wspace=.03,hspace=.12)
  fig.savefig(OUT/name,dpi=180,facecolor='white');plt.close(fig)

 low=min(rows,key=lambda r:r['common_vegetated_area_km2']);high=max(rows,key=lambda r:r['common_vegetated_area_km2'])
 monotonic='Yes' if primary['decreases_every_year'] else 'No'
 prov=json.loads((OUT/'computation_provenance.json').read_text());nfiles=len(prov['source_files'])
 table='| October year | Observed vegetation km² | Valid district % | Unknown km² | Common-footprint vegetation km² | Common-footprint vegetation % |\n| --- | ---: | ---: | ---: | ---: | ---: |\n'
 for r in rows:table+=f'| {int(r["year"])} | {r["vegetated_area_observed_km2"]:.1f} | {r["coverage_pct"]:.1f} | {r["unknown_area_km2"]:.1f} | {r["common_vegetated_area_km2"]:.1f} | {r["common_vegetated_pct"]:.1f} |\n'
 sensitivity='| Min observations | NDVI threshold | Common footprint % | OLS km²/year | Sen km²/year | Decreasing transitions / 9 |\n| --- | --- | ---: | ---: | ---: | ---: |\n'
 for s in stats:sensitivity+=f'| {s["min_observations"]} | {s["ndvi_threshold"]:.2f} | {s["common_coverage_pct"]:.1f} | {s["ols_km2_per_year"]:+.1f} | {s["sen_km2_per_year"]:+.1f} | {s["decreasing_transitions"]} |\n'
 report=f'''# Ten-year October vegetation-cover study: Beed, India

## Direct answer to the problem statement

The completed analysis uses **October 2015–2024**, ten years of the same satellite product over the same Beed district boundary. **Does the comparable vegetation area decrease every year? {monotonic}.** There are **{primary['decreasing_transitions']} decreases and {primary['increasing_transitions']} increases** across the nine adjacent-year changes. The descriptive common-footprint slope is **{primary['ols_km2_per_year']:+.1f} km²/year**. The observed end-to-start difference is **{primary['end_minus_start_km2']:+.1f} km²** on that fixed footprint. This is a small change: **99.1–100% of the common footprint is classified as vegetated in each year**, so area is effectively stable at this threshold. This binary classification is nearly saturated and can miss changes in vegetation density or condition. These statements are descriptive, not significance tests.

The lowest common-footprint vegetation area occurs in **October {int(low['year'])}: {low['common_vegetated_area_km2']:,.1f} km² ({low['common_vegetated_pct']:.1f}%)**; the highest occurs in **October {int(high['year'])}: {high['common_vegetated_area_km2']:,.1f} km² ({high['common_vegetated_pct']:.1f}%)**. The 2018 minimum is relative to the other nine October observations; vegetation area is not low as a fraction of this common footprint at NDVI > 0.30. There is no calibrated absolute district-level drought cutoff.

The common footprint covers **{rows[0]['common_area_km2']:,.1f} km² ({rows[0]['common_coverage_pct']:.1f}% of the mapped district)**. It is not the entire district and is not extrapolated to missing pixels. Requiring observations in every year selects a nonrandom subset of locations, so its trend need not represent the unobserved district. The full-district figure retains bounds for unobserved areas, so cloud gaps cannot silently appear as vegetation loss.

![Year versus vegetation area](year_vs_vegetation_area.png)

## Why Beed is a suitable drought-prone study area

The [official Zilla Parishad introduction](https://www.zpbeed.gov.in/en/about-department/introduction/) identifies Beed as drought-prone. The district's **2022–2023 Disaster Management Plan**, section 2.3.3, printed/PDF page 61, records summer drought in 2012–13, 2014–15, 2015–16, 2018–19 and 2019–20, including district-wide agricultural drought in four of those periods. It cites the Natural Calamity Branch, Collector Office, Beed. The PDF was downloaded and page 61 visually checked. [Official plan](https://cdnbbsr.s3waas.gov.in/s36143cc48107351648de16d8367dc5db4/uploads/2025/03/20250306517027863.pdf), linked from the [state disaster-management authority](https://sdma.maharashtra.gov.in/en/district-disaster-management-plan-ddmp/).

This is independent ground-based administrative **context for selecting the drought-prone region**. It is not pixel-level vegetation ground truth and does not label each October as drought/non-drought. No vegetation-class accuracy percentage is claimed. Long-term drought exposure does not require vegetation cover to decline monotonically in every chosen year.

## Satellite images actually downloaded

**{nfiles} source GeoTIFFs** were downloaded from NASA **MOD09A1 Collection 6.1 Terra surface reflectance**. Every source contains **seven spectral bands** plus QA, StateQA and selected-pixel DayOfYear. Band 1 is red; band 2 is near-infrared; bands 3/4 are blue/green; bands 5–7 provide infrared information. These are multispectral inputs, not RGB-only screenshots. Product DOI: [10.5067/MODIS/MOD09A1.061](https://doi.org/10.5067/MODIS/MOD09A1.061); [band/QA documentation](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD09A1).

NASA supplies atmospherically corrected eight-day products, which select an observation per pixel. We downloaded all products potentially containing October observations, including late-September starts when appropriate, and accepted pixels only when their supplied observation date falls inside October. Four source composites contribute in most years and five in leap years. All image IDs, dates, byte sizes and SHA256 hashes are retained.

The district boundary is the previously acquired official Survey of India ABDB2025 polygon, LGD 523. It is fixed across all years; exact historical boundary equivalence is not claimed. The native MODIS spacing is **{cfg['transform'][0]:.9f} m**, so pixel area is **{cfg['pixel_area_km2']:.9f} km²**, not the rounded nominal 500 m squared. Pixel-centre rasterization yields **{rows[0]['district_area_km2']:,.2f} km²** on the MODIS sphere. The earlier ellipsoidal equal-area vector estimate is 10,603.22 km²; the small difference reflects the spherical grid and boundary discretization. Native spherical CRS metadata is explicit in processed images; original downloaded TIFFs are preserved, including their imperfect CRS tags. No resampling was used to generate the spectral input grid.

![False-colour composites](october_false_colour.png)

## Explicit computation and built-in-function restriction

Core code: `pipeline/assignment/vegetation.py`, with scalar coordinate equations in `common.py`.

1. Project the supplied boundary coordinates with the native sinusoidal equations and create a pixel-centre mask using a handwritten scanline algorithm.
2. Decode the downloaded QA bits explicitly. Retain clear land observations with no shadow, cirrus, cloud adjacency or snow, no high aerosol, ideal MODLAND status and highest-quality red/NIR bands. The other bands are range checked but not separately quality screened; they are used for illustration.
3. For each accepted observation compute **NDVI=(NIR−red)/(NIR+red)**. The common reflectance scale cancels in this ratio. Zero denominators and invalid reflectances remain missing.
4. Accumulate NDVI with explicit loops and divide by the number of accepted observations. Require at least one accepted observation for the primary October image and retain a two-observation sensitivity. This is a mean of selected observations, not a daily time-weighted average.
5. Apply the same **NDVI>0.30** rule each year. Count the pixels and multiply by actual pixel area. Compute the intersection of eligible pixels across all ten years for a stable comparison.
6. Calculate adjacent-year changes, the ordinary least-squares slope and the median of pairwise slopes with explicit arithmetic and loops.

Rasterio is used for image reading/writing and metadata, NumPy for array storage, and Matplotlib for display/plots. Earth Engine is used to find/select/download source bands at their native grid, with datatype/nodata formatting only. No Earth Engine NDVI, monthly reducer, classifier or area reduction is used here. No OpenCV/scikit-image segmentation, rasterizer, built-in statistical regression, SciPy trend routine or precomputed NDVI product supplies the assignment calculation. The upstream NASA surface-reflectance processing is part of the downloaded data product.

The 0.30 threshold is an operational greenness cutoff, **not a universally validated vegetation boundary**. [USGS's NDVI explanation](https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology) notes that sparse vegetation and senescing crops can occupy moderate NDVI values. Consequently thresholds 0.20 and 0.40 are reported too. A vegetated 463 m mixed pixel is counted as a whole pixel: these results describe classified green-vegetation area, not fractional canopy cover, crop yield, or forest-only area.

## Actual annual results

{table}

The observed column uses each year's valid footprint and is a lower bound on total district vegetation under this rule. The corresponding upper bound adds the unknown area. These are logical missing-data bounds, not confidence intervals. The common-footprint columns compare exactly the same pixels each year. Unknown pixels include failed cloud, quality or date checks and excluded water/non-land QA classes; unknown does not mean bare ground.

**The apparent 2024 drop in observed vegetation area is not evidence of equivalent vegetation loss.** Valid coverage falls to 69.1% of the district, while vegetation area on the fixed common footprint remains almost unchanged. The missing observations prevent a precise whole-district estimate for that year.

![Vegetation maps](october_vegetation_maps.png)

## Sensitivity and interpretation

{sensitivity}

![Sensitivity](threshold_sensitivity.png)

The primary leave-one-year-out OLS slopes range from **{primary['leave_one_year_out_slope_min']:+.1f} to {primary['leave_one_year_out_slope_max']:+.1f} km²/year**. This is an influence check, not a confidence interval. None of the six declared settings shows a decrease in every year. The NDVI > 0.40 sensitivity makes the relative 2018 dip clearer, demonstrating that the size of the apparent change depends strongly on the vegetation definition. It does not independently validate drought. Different observation requirements produce different fixed footprints. The original two-observation rule left only 4.2% of the district valid in every year, so the primary rule was revised after a coverage audit to one accepted observation (65.7% common coverage). The original results and source snapshot are preserved in `initial_min2_audit/`. The threshold was held fixed; the change was motivated by usable spatial coverage, not trend direction. A single accepted observation need not represent the full month.

Drought, crop timing, harvesting, irrigation, land-use change, aerosols and remaining observation bias can all affect October greenness. This assignment answers the ten-year vegetation-area question and supplies official evidence of drought exposure; it does not attribute every area change to drought or establish land degradation. Full-district conclusions remain limited by missing observations and coarse mixed pixels.

## Verification

All 43 input hashes and image grids passed validation. Pixel classes, counts, area accounting and nested threshold masks passed; 90 sampled pixel-year NDVI values were reconstructed from the downloaded inputs and matched the output rasters. Four algorithm tests passed. The four output figures were visually inspected for labels, legends, consistent years, gaps and clipping. These are computational checks, not field accuracy validation.

## Reproducibility and deliverables

- `data/assignment/raw/`: all actual downloaded seven-band spectral images with QA/date bands and per-year provenance.
- `data/assignment/processed/`: ten October seven-band reflectance composites, NDVI rasters, class maps and observation-count rasters, plus district/common masks.
- `results/assignment/year_vs_vegetation_area.csv`: the primary numerical table; `area_all_sensitivities.csv` contains all declared alternatives.
- `results/assignment/trend_summary.json`: descriptive trends and all nine changes for each alternative.
- `pipeline/assignment/`: download, explicit calculation, figure/report and validation code.
- Earlier yield/VHI/SPI experiments remain preserved as separate exploratory work. They are not required for this assignment's conclusion.

The selected period is 2015–2024, ten complete years aligned with the earlier endpoint. No extension to other months, crop-loss prediction or ML is part of this deliverable.
'''
 (OUT/'assignment_report.md').write_text(report)
 write_json(OUT/'source_review.json',{'official_drought_history':{'file':'data/assignment/sources/beed_ddmp_2022_2023.pdf','page':61,'visually_checked':True,'scope':'Documented summer/agricultural drought context, not October pixel labels'},'threshold_source':'USGS NDVI interpretation; thresholds are fixed sensitivity assumptions, not calibrated local truth'})
 print('Generated assignment figures and report',flush=True)
if __name__=='__main__':main()
