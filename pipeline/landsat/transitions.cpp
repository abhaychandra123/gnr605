#include <cstdint>
extern "C" void transitions(int n,const uint8_t* mask,const double* before,const double* after,uint64_t* counts,double* sums,uint8_t* classes){
 for(int i=0;i<n;i++){
  classes[i]=mask[i]?255:254;if(!mask[i])continue;counts[0]++;
  if(before[i]==-9999||after[i]==-9999)continue;counts[1]++;
  bool a=before[i]>.3+1e-12,b=after[i]>.3+1e-12;
  sums[0]+=before[i];sums[1]+=after[i];if(a)counts[2]++;if(b)counts[3]++;
  if(a&&b){classes[i]=1;counts[4]++;}
  else if(!a&&b){classes[i]=2;counts[5]++;}
  else if(a&&!b){classes[i]=3;counts[6]++;}
  else{classes[i]=0;counts[7]++;}
 }
}
