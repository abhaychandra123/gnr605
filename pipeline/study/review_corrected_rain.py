"""Fit and inspect corrected district rainfall before interpreting SPI."""
import json
import pandas as pd
from analyze_impacts import read_verified,OUT
from analysis import spi
import review_results

def main():
 rain=read_verified('rainfall',528,['date'])
 rain=rain.set_index(pd.PeriodIndex(rain.date,freq='M')).sort_index()
 assert rain.index.equals(pd.period_range('1981-01','2024-12',freq='M'))
 assert rain.rain_valid_fraction.ge(1-1e-6).all() and (rain.rain_days==rain.expected_days).all()
 fits=[]
 for scale in [1,3,6,12]:
  rain[f'spi_{scale}'],f=spi(rain.rain_mm,scale);fits.append(f)
 rain.to_csv(OUT/'rainfall_spi.csv',index=False);pd.concat(fits).to_csv(OUT/'spi_fit_diagnostics.csv',index=False)
 rain['rain_for_spi_mm']=rain.rain_mm
 review_results.OUT=OUT;review_results.gamma_review(rain)
 d=pd.read_csv(OUT/'spi_gamma_fit_review.csv')
 print(d.nsmallest(6,'bootstrap_p').to_string(index=False),flush=True)
 print('Corrected rainfall SPI and 1999-replicate gamma checks completed',flush=True)
if __name__=='__main__':main()
