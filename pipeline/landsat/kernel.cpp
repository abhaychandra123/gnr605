// Handwritten scalar loops only; no numerical/image-analysis library.
#include <cstdint>
#include <cmath>
extern "C" {
int valid_observation(const uint16_t* b, int stride, int i) {
  for(int k=0;k<7;k++) if(b[k*stride+i]<1 || b[k*stride+i]>65455) return 1;
  if(b[7*stride+i]&63) return 2;
  if(b[8*stride+i]&(127|2048)) return 3;
  auto aerosol=b[9*stride+i];
  if((aerosol&1)||((aerosol>>6)&3)==3) return 4;
  double red=b[3*stride+i]*.0000275-.2,nir=b[4*stride+i]*.0000275-.2;
  if(red<0||nir<0||red>1||nir>1||red+nir<=0) return 5;
  return 0;
}
void accumulate(const uint16_t* b,int h,int w,int row0,int col0,int W,int H,
 const uint8_t* mask,int date,uint16_t* last,uint16_t* count,double* sum,
 double* refl,uint64_t* qa) {
 int stride=h*w;long long size=(long long)W*H;
 for(int r=0;r<h;r++)for(int c=0;c<w;c++) {
  int j=(r+row0)*W+c+col0,i=r*w+c;if(!mask[j])continue;
  int reason=valid_observation(b,stride,i);qa[reason]++;
  if(reason || last[j]==date)continue;
  last[j]=date;count[j]++;
  double red=b[3*stride+i]*.0000275-.2,nir=b[4*stride+i]*.0000275-.2;
  sum[j]+=(nir-red)/(nir+red);
  for(int k=0;k<7;k++)refl[k*size+j]+=b[k*stride+i]*.0000275-.2;
  qa[6]++;
  if(b[7*stride+i]&128)qa[7]++;
  if(b[9*stride+i]&32)qa[8]++;
  if(((b[9*stride+i]>>6)&3)==0)qa[9]++;
 }
}
void finish(int size,const uint8_t* mask,const uint16_t* count,const double* sum,
 const double* refl,double* ndvi,float* mean,uint8_t* classes) {
 for(int i=0;i<size;i++) {
  ndvi[i]=-9999;classes[i]=mask[i]?255:254;
  for(int k=0;k<7;k++)mean[(long long)k*size+i]=-9999;
  if(mask[i]&&count[i]){
   ndvi[i]=sum[i]/count[i];classes[i]=ndvi[i]>.3+1e-12;
   for(int k=0;k<7;k++)mean[(long long)k*size+i]=refl[(long long)k*size+i]/count[i];
  }
 }
}
void intersect(int size,const uint8_t* mask,const uint16_t* count,uint8_t* one,uint8_t* two){
 for(int i=0;i<size;i++){one[i]=one[i]&&mask[i]&&count[i]>=1;two[i]=two[i]&&mask[i]&&count[i]>=2;}
}
// totals: district,valid,common,validNDVIsum,commonNDVIsum,observed .2/.3/.4,
// common .2/.3/.4, eligible 2 dates. Histogram bins width .05 on [-1,1].
void summarize(int size,const uint8_t* mask,const uint8_t* common,const uint16_t* count,
 const double* ndvi,double* totals,uint64_t* histogram){
 for(int i=0;i<size;i++){
  if(!mask[i])continue;totals[0]++;
  if(!count[i])continue;
  double v=ndvi[i];totals[1]++;totals[3]+=v;
  if(count[i]>=2)totals[11]++;
  if(common[i]){totals[2]++;totals[4]+=v;int bin=(int)((v+1)/.05);if(bin<0)bin=0;if(bin>39)bin=39;histogram[bin]++;}
  for(int k=0;k<3;k++)if(v>(.2+.1*k)+1e-12){totals[5+k]++;if(common[i])totals[8+k]++;}
 }
}
}
