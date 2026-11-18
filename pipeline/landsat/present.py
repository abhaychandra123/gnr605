"""Display executed Landsat results and document coverage/interpretation limits."""
import argparse,csv,json,os
os.environ.setdefault('MPLCONFIGDIR','/tmp/gnr605-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import rasterio
from common import DATA,OUT,ROOT,YEARS

def read(path):return [{k:float(v) for k,v in row.items()} for row in csv.DictReader(path.open())]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--reuse-maps',action='store_true');args=parser.parse_args()
 if args.reuse_maps:
  for name in ['october_vegetation.png','october_false_colour.png']:assert (OUT/name).exists()
 rows=read(OUT/'annual_vegetation.csv');sens=read(OUT/'area_sensitivities.csv')
 trends=json.loads((OUT/'trend_summary.json').read_text());primary=next(t for t in trends if t['threshold']==.3)
 man=json.loads((DATA/'download_manifest.json').read_text());val=json.loads((OUT/'validation.json').read_text());assert val['status']=='passed'
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 years=[r['year'] for r in rows]
 fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True,constrained_layout=True)
 axes[0].fill_between(years,[r['observed_vegetation_km2'] for r in rows],[r['upper_bound_vegetation_km2'] for r in rows],color='#c9d5c9',label='Bounds over unknown pixels (not a confidence interval)')
 axes[0].plot(years,[r['observed_vegetation_km2'] for r in rows],'o-',color='#257747',label='Observed vegetation; footprint varies by year')
 axes[0].set_ylabel('Whole-district bounds (km²)');axes[0].set_ylim(0,rows[0]['district_grid_area_km2']*1.04);axes[0].legend(fontsize=8,loc='lower left')
 axes[0].set_title('Unknown pixels are not counted as bare land')
 for threshold,color in zip([.2,.3,.4],['#91af92','#257747','#b67b38']):
  subset=[r for r in sens if r['threshold']==threshold]
  axes[1].plot(years,[r['common_vegetation_km2'] for r in subset],'o-',color=color,label=f'NDVI > {threshold:.2f}')
 axes[1].set_ylim(0,rows[0]['common_area_km2']*1.05);axes[1].set_ylabel('Fixed-footprint vegetation (km²)');axes[1].set_xlabel('Year (October)');axes[1].legend(loc='lower left')
 axes[1].set_title(f'Diagnostic only: {int(rows[0]["common_pixels"])} pixels in every year, {rows[0]["common_area_km2"]:.4f} km² ({rows[0]["common_coverage_pct"]:.6f}% of district)')
 for ax in axes:ax.set_xticks(YEARS);ax.grid(alpha=.2)
 fig.suptitle('Beed: October vegetation-covered area from Landsat 8, 2015–2024\n30 m imagery; at least one accepted acquisition date per pixel',fontsize=13)
 fig.savefig(OUT/'year_vs_vegetation_area.png',dpi=170);plt.close(fig)

 fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,constrained_layout=True)
 axes[0].plot(years,[r['mean_ndvi_common'] for r in rows],'o-',color='#257747',label=f'Fixed common footprint ({int(rows[0]["common_pixels"])} pixels only)')
 axes[0].plot(years,[r['mean_ndvi_valid'] for r in rows],'o--',color='#b67b38',label='Each year’s valid footprint')
 axes[0].set_ylim(0,1);axes[0].set_ylabel('Mean October NDVI');axes[0].legend();axes[0].grid(alpha=.2)
 axes[1].plot(years,[r['valid_coverage_pct'] for r in rows],'o-',label='At least one accepted date')
 axes[1].plot(years,[r['valid_two_dates_pct'] for r in rows],'s--',label='At least two accepted dates')
 axes[1].axhline(rows[0]['common_coverage_pct'],color='#777777',linestyle=':',label='Valid in all ten Octobers (min1)')
 axes[1].set_ylim(0,100);axes[1].set_ylabel('District coverage (%)');axes[1].set_xlabel('Year (October)');axes[1].set_xticks(YEARS);axes[1].legend(fontsize=9);axes[1].grid(alpha=.2)
 fig.suptitle('Continuous greenness and usable observation coverage\nFiner pixels do not guarantee complete cloud-free coverage',fontsize=13)
 fig.savefig(OUT/'ndvi_and_coverage.png',dpi=170);plt.close(fig)

 hist=read(OUT/'ndvi_histograms.csv');image=np.zeros((40,10))
 for r in hist:image[round((r['bin_lower']+1)/.05),int(r['year'])-2015]=100*r['common_pixel_count']/rows[0]['common_pixels']
 fig,ax=plt.subplots(figsize=(11,5),constrained_layout=True)
 im=ax.imshow(image,origin='lower',aspect='auto',extent=[2014.5,2024.5,-1,1],cmap='YlGnBu')
 ax.set_ylim(-.2,1);ax.set_xticks(YEARS);ax.set_xlabel('Year (October)');ax.set_ylabel('October mean NDVI');ax.set_title(f"NDVI distribution on the same valid pixels in every year\nEach bin spans 0.05 NDVI; only {int(rows[0]['common_pixels'])} common pixels, not a district-wide distribution")
 fig.colorbar(im,ax=ax,label='Common pixels in NDVI bin (%)');fig.savefig(OUT/'ndvi_distribution.png',dpi=170);plt.close(fig)

 with rasterio.open(DATA/'processed/district_mask.tif') as src:
  H=360;W=round(H*src.width/src.height);mask=src.read(1,out_shape=(H,W))
 for kind in ([] if args.reuse_maps else ['vegetation','false_colour']):
  fig,axes=plt.subplots(2,5,figsize=(16,7))
  for ax,year in zip(axes.flat,YEARS):
   display=np.ones((H,W,3),dtype='float32')
   filename=f'october_{year}_vegetation.tif' if kind=='vegetation' else f'october_{year}_reflectance.tif'
   with rasterio.open(DATA/'processed'/filename) as src:a=src.read(out_shape=(src.count,H,W))
   palette={0:(.83,.74,.53),1:(.12,.48,.25),254:(1,1,1),255:(.73,.75,.78)}
   for r in range(H):
    for c in range(W):
     if kind=='vegetation':rgb=palette[int(a[0,r,c])]
     elif not mask[r,c]:rgb=(1,1,1)
     elif a[0,r,c]==-9999:rgb=(.73,.75,.78)
     else:
      rgb=[]
      for band,scale in [(4,.6),(3,.3),(2,.3)]:
       value=float(a[band,r,c])/scale
       if value<0:value=0
       if value>1:value=1
       rgb.append(value**.7)
     for band in range(3):display[r,c,band]=rgb[band]
   ax.imshow(display,interpolation='nearest');ax.set_title(str(year));ax.axis('off')
  if kind=='vegetation':
   fig.suptitle('Landsat October vegetation maps: NDVI > 0.30\nGray = unknown; beige = below threshold; green = vegetation',fontsize=14)
   fig.legend(handles=[Patch(color=(.12,.48,.25),label='Vegetation'),Patch(color=(.83,.74,.53),label='Below threshold'),Patch(color=(.73,.75,.78),label='Unknown')],loc='lower center',ncol=3,frameon=False)
  else:fig.suptitle('Landsat October false-colour composites, 2015–2024\nR=NIR, G=red, B=green; same display stretch in each year; gray gaps',fontsize=14)
  fig.subplots_adjust(top=.82,bottom=.10,wspace=.03,hspace=.10)
  fig.savefig(OUT/f'october_{kind}.png',dpi=170);plt.close(fig)

 audit=read(OUT/'aerosol_coverage_diagnostic.csv');pairs=read(OUT/'pairwise_changes.csv')
 audit_info=json.loads((OUT/'aerosol_audit.json').read_text())
 fig,axes=plt.subplots(2,1,figsize=(11,8),constrained_layout=True)
 axes[0].plot(years,[r['primary_coverage_pct'] for r in audit],'o-',color='#257747',label='Primary: high aerosol excluded')
 axes[0].plot(years,[r['if_high_aerosol_included_coverage_pct'] for r in audit],'o--',color='#b67b38',label='Diagnostic only: high aerosol included')
 axes[0].set_ylim(0,100);axes[0].set_ylabel('District with observations (%)');axes[0].set_xticks(YEARS);axes[0].legend(fontsize=9);axes[0].grid(alpha=.2)
 axes[0].set_title('Coverage cost of excluding high-aerosol observations\nAdditional coverage is not evidence of reliable reflectance')
 delta=[r['net_change_km2'] for r in pairs[:9]]
 axes[1].bar(range(9),delta,color=['#257747' if v>=0 else '#ae554d' for v in delta])
 axes[1].axhline(0,color='black',lw=.7)
 axes[1].set_xticks(range(9),[f"{int(r['before'])}–{int(r['after'])}\n{r['shared_district_pct']:.3f}% shared" for r in pairs[:9]],rotation=30,ha='right',fontsize=8)
 axes[1].set_ylabel('Net vegetation-area change (km²)');axes[1].grid(axis='y',alpha=.2)
 axes[1].set_title('Adjacent-year changes on each pair’s shared valid pixels\nDifferent footprints: bars cannot be added into a district-wide trend')
 fig.savefig(OUT/'quality_and_pairwise_changes.png',dpi=170);plt.close(fig)

 quality_table='| Year | Primary valid district % | If high aerosol admitted % (diagnostic only) |\n| --- | ---: | ---: |\n'
 for r in audit:quality_table+=f"| {int(r['year'])} | {r['primary_coverage_pct']:.1f} | {r['if_high_aerosol_included_coverage_pct']:.1f} |\n"
 pair_table='| Years | Shared district % | Vegetation gain km² | Vegetation loss km² | Net change km² |\n| --- | ---: | ---: | ---: | ---: |\n'
 for r in pairs:pair_table+=f"| {int(r['before'])}–{int(r['after'])} | {r['shared_district_pct']:.4f} | {r['gain_km2']:.4f} | {r['loss_km2']:.4f} | {r['net_change_km2']:+.4f} |\n"
 table='| Year | Valid district % | Observed vegetation km² | Fixed-footprint vegetation km² | Fixed-footprint vegetation % | Fixed-footprint mean NDVI |\n| --- | ---: | ---: | ---: | ---: | ---: |\n'
 for r in rows:table+=f'| {int(r["year"])} | {r["valid_coverage_pct"]:.1f} | {r["observed_vegetation_km2"]:.1f} | {r["common_vegetation_km2"]:.4f} | {r["common_vegetation_pct"]:.1f} | {r["mean_ndvi_common"]:.3f} |\n'
 sensitivity='| Threshold | OLS km²/year | Median pairwise slope km²/year | Decreasing transitions / 9 |\n| --- | ---: | ---: | ---: |\n'
 for t in trends:sensitivity+=f'| {t["threshold"]:.2f} | {t["ols_km2_per_year"]:+.6f} | {t["sen_km2_per_year"]:+.6f} | {t["decreasing_transitions"]} |\n'
 low=min(rows,key=lambda r:r['mean_ndvi_common']);high=max(rows,key=lambda r:r['mean_ndvi_common'])
 report=f'''# Landsat refinement: Beed October vegetation cover, 2015–2024

## Execution and direct answer

Downloaded **{man['scene_count']} Landsat 8 scenes**, cropped into **{man['tile_count']} native-grid tiles** ({man['total_bytes']/1e9:.2f} GB of local source TIFFs). Every tile contains seven surface-reflectance bands including NIR/SWIR plus three quality bands. All ten October years have been processed locally at **30 m**. Original MODIS outputs are preserved.

**A district-wide ten-year Landsat trend is not supported by these data.** Only **{int(rows[0]['common_pixels'])} pixels**, covering **{rows[0]['common_area_km2']:.4f} km² ({rows[0]['common_coverage_pct']:.6f}% of Beed)**, pass the fixed quality rule in every October. This tiny selected footprint is unsuitable for a district-level trend conclusion.

For reproducibility only, with **NDVI > 0.30**, that tiny footprint has **{primary['decreasing_transitions']} decreases and {primary['increasing_transitions']} increases and {primary['unchanged_transitions']} unchanged transition(s)** across nine transitions. The descriptive slope is **{primary['ols_km2_per_year']:+.6f} km²/year**. These are observations, not significance or causal drought claims.

The all-year valid footprint is **{rows[0]['common_area_km2']:.4f} km² ({rows[0]['common_coverage_pct']:.6f}% of the mapped district)**. Valid annual coverage ranges from **{min(r['valid_coverage_pct'] for r in rows):.1f}% to {max(r['valid_coverage_pct'] for r in rows):.1f}%**. This selected footprint is not a random district sample; its trend must not be extrapolated to missing pixels. Compare the fixed footprint rather than mistaking changing cloud gaps for area change. If this common fraction is small, the ten-year Landsat slope describes only that small selected area and is not evidence of district-wide improvement or decline.

![Year versus vegetation area](year_vs_vegetation_area.png)

**Role in the submission:** retain the MODIS result as the broader-coverage historical baseline. Use Landsat for finer spatial evidence in adequately observed years and an explicit coverage/quality comparison. A severely restricted ten-year Landsat footprint must not replace the MODIS series as a district-wide conclusion.

## What the finer-resolution analysis adds

The native Landsat grid resolves 30 m cells versus approximately 463 m in the MODIS baseline. It can separate some land-cover mixtures hidden within a coarse cell; it does not provide field verification. Landsat also supplies fewer observation opportunities within October, so spatial detail and temporal coverage must be considered separately. No declining trend is assumed in advance.

On these **{int(rows[0]['common_pixels'])} selected pixels only**, mean NDVI is lowest in **{int(low['year'])} ({low['mean_ndvi_common']:.3f})**, and highest in **{int(high['year'])} ({high['mean_ndvi_common']:.3f})**. Continuous NDVI and its distribution retain variation that a binary threshold may miss. This is greenness, not a direct yield or water-deficit measurement, and it must not be interpreted as a district-wide ranking of drought years.

![NDVI and coverage](ndvi_and_coverage.png)
![NDVI distributions](ndvi_distribution.png)

## Actual annual values

{table}

Observed vegetation uses each year's valid pixels and is a lower bound under this classification. The upper bound adds unknown area; these bounds are not confidence intervals. Fixed-footprint columns use exactly the same eligible 30 m pixels in every year.

## Method and course restriction

Source: [USGS Landsat 8 Collection 2 Tier 1 Level 2](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2). All October scenes intersecting the official Beed polygon were included; scene-wide cloud percentages were not used to discard data. Seven optical bands and QA were downloaded in tiles using Earth Engine's image-download endpoint. No server-side index, monthly composite, classification or area reduction was used.

Reflectance is **DN × 0.0000275 − 0.2**. The offset is applied before calculating **(NIR − red)/(NIR + red)**; omitting it would give a different NDVI. Reject fill, dilated cloud, cirrus, cloud, shadow, snow, optical saturation, terrain occlusion and high-aerosol flags. Aerosol climatology/interpolated values are retained and separately counted in QA records. Require valid spectral DNs, red/NIR reflectances in [0,1], and a positive denominator. The full predetermined rule is in [protocol.md](protocol.md).

Handwritten scalar loops implement the coordinate projection, scanline polygon mask, QA, reflectance conversion, NDVI, accumulation, classification and area counting. A small C++ kernel compiles those loops for speed; it calls no image-analysis or statistical library. Rasterio performs image I/O, NumPy stores arrays, and Matplotlib displays results. The native UTM grid alignment of all scenes is checked; no input resampling is performed. Pixel-centre inclusion and projected 900 m² cell areas introduce normal boundary/map-scale approximations.

Each pixel is counted at most once per acquisition date. Overlapping same-date scenes use the first valid sample in sorted scene-ID order. October NDVI is the arithmetic mean of accepted dates, not a daily time-weighted average. One accepted date is sufficient for the primary result; coverage with two dates is shown separately. All-year common min2 coverage is recorded in computation provenance.

Valid water pixels remain eligible here, whereas MODIS QA excluded non-land. Sensors also differ in observation dates, spectral response, QA and their all-year valid footprints. Differences between their district summaries cannot therefore be attributed solely to resolution or treated as a classification-accuracy score.

![False colour](october_false_colour.png)
![Vegetation maps](october_vegetation.png)

## Sensitivity on the tiny common footprint

These numerical results describe only {int(rows[0]['common_pixels'])} pixels. They are retained for reproducibility, not used for a district-wide trend claim.

{sensitivity}

Thresholds were fixed before interpreting the results. NDVI is a greenness proxy; these are whole-pixel classification areas, not fractional canopy cover. A one-month annual series cannot separate drought from crop timing, harvest, irrigation or land-use change. The prior official drought records establish Beed's suitability as a study location; they do not validate individual Landsat classes.

## Quality limitations and pairwise spatial changes

{quality_table}

An initial 2015 audit found that the high-aerosol exclusion removes much of the otherwise eligible imagery. The primary rule was retained. The diagnostic above measures possible coverage if that exclusion were removed, keeping other quality/physical checks fixed; these extra pixels are **not** used for the primary vegetation estimates. [USGS cautions against high-aerosol pixels](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance) and documents [atmospheric-correction issues](https://www.usgs.gov/landsat-missions/landsat-collection-2-known-issues). Admitting them would raise the all-year common footprint to {audit_info['common_if_high_aerosol_included_pct']:.1f}%, but that coverage is not established-quality evidence.

{pair_table}

These pairs use only pixels observed in both named years, rather than requiring all ten years. This retains more locations for individual comparisons, but each pair has a different spatial population. Gains and losses are threshold crossings, not independently verified conversion of land cover. Do not add pairwise net changes together or extrapolate them to the district.

![Quality and pairwise changes](quality_and_pairwise_changes.png)

## Verification and outstanding scientific work

All {man['tile_count']} source hashes and grid checks passed. Five algorithm tests passed, including reflectance offset, cloud/saturation screening, same-date deduplication and unknown-pixel treatment. An independent Python implementation reconstructed **{val['independent_sampled_pixel_years']} sampled pixel-year histories** from downloaded scene values and matched the calculated NDVI, date counts and classes. The main spatial sample was chosen without selecting on greenness or clear status; up to ten additional common-valid pixels ensure that observed values are checked in every year. These checks establish computational consistency, not field accuracy.

**Independent vegetation reference labels are still needed before claiming classification accuracy or an ML improvement.** Finer-resolution imagery is an improvement in spatial evidence, not a substitute for those labels. A supervised comparison must keep reference-label creation independent of the NDVI threshold and reserve spatially separate test locations. No ML model or drought forecast has been trained in this stage.

Reproduction: [pipeline instructions](../../pipeline/landsat/README.md). Source IDs, tile coordinates, dates and checksums are retained in `data/landsat/inventory.json` and `download_manifest.json`. Large TIFFs remain local and ignored by Git. Processed NDVI, seven-band composites, classes and unique-date counts are in `data/landsat/processed/`. The primary numerical table is [annual_vegetation.csv](annual_vegetation.csv).
'''
 (OUT/'landsat_report.md').write_text(report)
 print('LANDSAT REPORT AND FIGURES COMPLETE',flush=True)
if __name__=='__main__':main()
