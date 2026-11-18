// Diagnostic coverage only: do NOT interpret high-aerosol inclusion as valid data.
#include <cstdint>
extern "C" {
void coverage_without_high_aerosol_exclusion(const uint16_t* b,int h,int w,int row0,int col0,int W,const uint8_t* district,uint8_t* possible){
 int n=h*w;
 for(int r=0;r<h;r++)for(int c=0;c<w;c++){
  int i=r*w+c,j=(r+row0)*W+c+col0;
  if(!district[j]||possible[j])continue;
  bool valid=true;for(int k=0;k<7;k++)if(b[k*n+i]<1||b[k*n+i]>65455)valid=false;
  if(!valid||(b[7*n+i]&63)||(b[8*n+i]&(127|2048))||(b[9*n+i]&1))continue;
  double red=b[3*n+i]*.0000275-.2,nir=b[4*n+i]*.0000275-.2;
  if(red<0||nir<0||red>1||nir>1||red+nir<=0)continue;
  possible[j]=1;
 }
}
void audit_counts(int n,const uint8_t* mask,const uint16_t* strict,const uint8_t* possible,uint8_t* common,uint64_t* counts){
 for(int i=0;i<n;i++){
  if(!mask[i]){common[i]=0;continue;}
  counts[0]++;if(strict[i])counts[1]++;if(possible[i])counts[2]++;
  if(strict[i]&&!possible[i])counts[3]++;
  common[i]=common[i]&&possible[i];if(common[i])counts[4]++;
 }
}
}
