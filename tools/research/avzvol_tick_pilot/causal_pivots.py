"""As-of pivot inventory for exploratory campaign. Not liquidity lifecycle.
Only feed CLOSED bars available before the signal. Mirrors liqpool asymmetrical
plateau rule, emits available_bar explicitly, never retrospective final zones.
"""
class CausalPivots:
 def __init__(self,left=2,right=2):
  if left<1 or right<1:raise ValueError('positive left/right required')
  self.left=left;self.right=right;self.high=[];self.low=[];self.events=[]
 def update(self,high,low):
  if high<low:raise ValueError('invalid closed bar')
  self.high.append(high);self.low.append(low);b=len(self.high)-1;i=b-self.right
  new=[]
  if i>=self.left:
   for label,a,sign in [('H',self.high,1),('L',self.low,-1)]:
    x=sign*a[i]
    if all(x>=sign*a[i-d] for d in range(1,self.left+1)) and all(x>sign*a[i+d] for d in range(1,self.right+1)):
     new.append(dict(side=label,pivot_bar=i,available_bar=b,level=a[i]))
  self.events.extend(new);return new
