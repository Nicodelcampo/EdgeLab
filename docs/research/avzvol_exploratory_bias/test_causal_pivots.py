import importlib.util,random,unittest
from causal_pivots import CausalPivots
PATH='/data/edgelab-parameter-grid/edgelab/bridge/indicators/liqpool.py'
s=importlib.util.spec_from_file_location('reference',PATH);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_delayed(self):
  p=CausalPivots();hs=[1,2,5,3,2]
  for b,h in enumerate(hs):
   new=p.update(h,0)
   if b<4:self.assertEqual(new,[])
  self.assertEqual(p.events,[dict(side='H',pivot_bar=2,available_bar=4,level=5)])
 def test_prefix_parity(self):
  r=random.Random(89711)
  for trial in range(100):
   hs=[r.randint(0,100) for _ in range(80)];ls=[h-r.randint(0,20) for h in hs];left=1+trial%4;right=1+(trial//4)%4;p=CausalPivots(left,right)
   for b,(h,l) in enumerate(zip(hs,ls)):
    p.update(h,l);ref=m.find_pivots(hs[:b+1],ls[:b+1],{'pivot_left':left,'pivot_right':right})
    self.assertEqual([(e['pivot_bar'],e['side'],e['level']) for e in p.events],ref)
    self.assertTrue(all(e['available_bar']==e['pivot_bar']+right and e['available_bar']<=b for e in p.events))
 def test_future_extension(self):
  a=CausalPivots();b=CausalPivots()
  for h,l in [(4,1),(5,2),(8,4),(6,3),(5,1)]:a.update(h,l);b.update(h,l)
  frozen=[dict(e) for e in a.events]
  for h,l in [(100,-100),(101,-99),(100,-100)]:b.update(h,l)
  self.assertEqual([e for e in b.events if e['available_bar']<5],frozen)
if __name__=='__main__':unittest.main()
