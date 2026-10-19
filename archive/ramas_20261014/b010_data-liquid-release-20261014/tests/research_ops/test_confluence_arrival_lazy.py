import hashlib,random,sys,types,unittest
from pathlib import Path
from dataclasses import asdict
from unittest.mock import patch
from tools.research_ops.confluence.arrival import ArrivalObserver,Tick
from tools.research_ops.confluence.episodes import Event
from test_confluence_arrival import ep
from tools.research_ops.confluence.asof_intersections import Clock

P='345a5fb451bcd4bea872d6c186a859c5263b7150ea677369f408d8d02fb4f890'
def eager():
    raw=(Path(__file__).parent/'fixtures/confluence_arrival_eager.py').read_bytes();assert hashlib.sha256(raw).hexdigest()==P
    name='tools.research_ops.confluence._arrival_eager_fixture';m=types.ModuleType(name);m.__package__='tools.research_ops.confluence';sys.modules[name]=m;exec(compile(raw,'pinned-eager-arrival','exec'),m.__dict__);return m

class LazyTests(unittest.TestCase):
    def test_exact_against_pinned_eager_random_mutations(self):
        ref=eager()
        for seed in range(10):
            r=random.Random(seed);a=ArrivalObserver(trade_date='2026-09-01',window_ticks=23);b=ref.ArrivalObserver(trade_date='2026-09-01',window_ticks=23);active={}
            for i in range(500):
                c=Clock(1000000000+(i//3)*1000000,i);events=[]
                for n in range(8):
                    id=str(n)
                    if id not in active and r.random()<.01:
                        lo=2*r.randrange(-10,10);z=ep(c,lo,lo+2*r.randrange(1,10),id=id);active[id]=z;events.append(Event('START',z,c,'new'))
                    elif id in active and r.random()<.02:
                        old=active[id]
                        if r.random()<.3:events.append(Event('END',old,c,'end'));del active[id]
                        else:
                            lo=2*r.randrange(-10,10);z=ep(c,lo,lo+2*r.randrange(1,10),id=id,rev=old.revision+1,born=old.recognized);active[id]=z;events.append(Event('UPDATE',z,c,'move'))
                vals=(c,2*r.randrange(-20,20),r.random()*10,r.choice((-1,0,1)))
                got=a.observe(Tick(*vals),events);expected=b.observe(ref.Tick(*vals),events)
                self.assertEqual([asdict(x) for x in got],[asdict(x) for x in expected])
    def test_no_anchor_does_not_calculate_features(self):
        a=ArrivalObserver(trade_date='2026-09-01')
        with patch.object(a,'_features',wraps=a._features) as f:
            for i in range(100):self.assertEqual(a.observe(Tick(Clock(i+1,i),0,1.)),())
            self.assertEqual(f.call_count,0)
    def test_many_same_clock_anchors_share_one_exact_features_object(self):
        a=ArrivalObserver(trade_date='2026-09-01',window_ticks=2);t=Tick(Clock(1,0),0,1.);a.observe(t,[Event('START',ep(t.clock,id=str(i)),t.clock,'new') for i in range(8)])
        with patch.object(a,'_features',wraps=a._features) as f:
            rs=a.observe(Tick(Clock(2,1),12,1.));self.assertEqual(len(rs),8);self.assertEqual(f.call_count,1);self.assertTrue(all(x.features is rs[0].features for x in rs))
if __name__=='__main__':unittest.main()
