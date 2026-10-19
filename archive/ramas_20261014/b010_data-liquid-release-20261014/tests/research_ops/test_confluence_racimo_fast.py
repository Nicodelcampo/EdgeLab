import copy,random,unittest
from tools.research_ops.confluence.racimo_asof import RacimoTape,_racimo,_fast_rule
from test_confluence_racimo_asof import z,H,B

class FastRacimoTests(unittest.TestCase):
    def test_exact_observations_membership_geometry_and_ties(self):
        for seed in range(8):
            r=random.Random(seed);p={'racimo_min':r.choice((3,4,6,8)),'racimo_bars':r.choice((10,30,500)),'racimo_altura_ticks':r.choice((10,20,30,60))};a=RacimoTape(params=p,config_sha256=H,build_sha256=B);b=RacimoTape(params=p,config_sha256=H,build_sha256=B,optimized_candidates=False);id=0
            for bar in range(240):
                cs=[]
                for _ in range(r.randrange(1,5)):
                    id+=1;lo=r.randrange(90,120);cs.append(z(id,bar,lo,lo+r.randrange(0,25),session='2026-09-01' if bar<120 else '2026-09-02'))
                self.assertEqual(a.observe_batch(cs),b.observe_batch(cs))
            self.assertEqual(a.clusters,b.clusters)
    def test_dense_repeated_geometry_keeps_reversed_history_tie_choice(self):
        p={'racimo_min':3,'racimo_bars':500,'racimo_altura_ticks':30};a=RacimoTape(params=p,config_sha256=H,build_sha256=B);b=RacimoTape(params=p,config_sha256=H,build_sha256=B,optimized_candidates=False)
        for i in range(400):self.assertEqual(a.observe_batch([z(i,i,100+i%3,101+i%3)]),b.observe_batch([z(i,i,100+i%3,101+i%3)]))
    def test_selection_on_empty_wide_boundary_and_tied_bands(self):
        p={'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10}
        for lo,hi in ((100,120),(100,109),(90,90),(109,109)):
            zones=[dict(bar=i,low_tick=90+i%2*9,high_tick=90+i%2*9,rac=None,racimo_bar=-1) for i in range(10)];a=copy.deepcopy(zones);b=copy.deepcopy(zones);x=dict(bar=10,low_tick=lo,high_tick=hi,rac=None,racimo_bar=-1);y=copy.deepcopy(x);ca=[];cb=[]
            _racimo(x,a,ca,10,p);_fast_rule()(y,b,cb,10,p);self.assertEqual(x,y);self.assertEqual(a,b);self.assertEqual(ca,cb)
if __name__=='__main__':unittest.main()
