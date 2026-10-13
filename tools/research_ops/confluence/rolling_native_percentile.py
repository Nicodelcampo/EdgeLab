"""Candidate-only stable rolling percentile; not wired into native detector."""
from bisect import bisect_left,bisect_right
from collections import deque
import math
class RollingNativePercentile:
 def __init__(self,lookback):
  if type(lookback) is not int or not 1<=lookback<=5000:raise ValueError('bounded native lookback')
  self.lookback=lookback;self.fifo=deque();self.ordered=[]
 def append(self,value):
  if not math.isfinite(value):raise ValueError('finite native score only')
  if len(self.fifo)==self.lookback:
   old=self.fifo.popleft();self.ordered.pop(bisect_left(self.ordered,old))
  self.fifo.append(value);self.ordered.insert(bisect_right(self.ordered,value),value)
 def percentile(self,q):
  # Native interpolation unchanged; stable tie order preserves signed zeros.
  arr=self.ordered
  if len(arr)==0:return float('nan')
  if len(arr)==1:return float(arr[0])
  n=len(arr);qq=max(0.0,min(100.0,float(q)));pos=(qq/100.0)*(n-1);lo=int(math.floor(pos));hi=int(math.ceil(pos))
  if lo==hi or hi>=n:return float(arr[min(lo,n-1)])
  return float(arr[lo]+(arr[hi]-arr[lo])*(pos-lo))
