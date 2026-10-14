import unittest,random
from collections import Counter
from tools.research_ops.confluence.geometry_counts import GeometryCountStream
from tools.research_ops.confluence.episodes import EpisodeStream
from tools.research_ops.confluence.geometry_replay import GeometryReplay
from tools.research_ops.confluence.detector_capture import Capture
from tools.research_ops.confluence.asof_intersections import ZoneKey,Clock,Snapshot
H='a'*64;B='b'*64

def snap(f,i,c,lo=0,hi=10,rev=0,born=None):return Snapshot(ZoneKey(f,H,B,str(i)),rev,c,born or c,lo,hi)
def counter(events):return Counter(e.action+':'+ '+'.join(sorted(s.key.family for s in e.episode.components)) for e in events)
def engine(cls,**kw):return cls(contract='SYN',tape_sha256=H,trade_date='2026-06-16',**kw)
class CountTests(unittest.TestCase):
 def test_randomized_reference_all_families_atomic_revisions(self):
  for seed in range(8):
   rng=random.Random(seed);a=engine(EpisodeStream);b=engine(GeometryCountStream);serial=0
   for step in range(100):
    c=Clock(100+step,step);up=[];rem=[];active=a.join.active
    if active and rng.random()<.5:
     old=rng.choice(list(active.values()))
     if rng.random()<.5:rem=[old.key]
     else:
      lo=rng.randrange(-20,20);up=[Snapshot(old.key,old.revision+1,c,old.recognized,lo,lo+rng.randrange(15),old.side)]
    for _ in range(rng.randrange(3)):
     serial+=1;lo=rng.randrange(-20,20);up.append(snap(rng.choice(['AVZP2','RACIMO','BT2','BT2A']),serial,c,lo,lo+rng.randrange(15)))
    self.assertEqual(counter(a.apply(c,upserts=up,removals=rem)),b.apply(c,upserts=up,removals=rem))
    self.assertEqual(a.join.active,b.join.active)
 def test_dense_live_graph_over_cap_but_small_atomic_batches(self):
  ref=engine(EpisodeStream,max_pairs=10000);candidate=engine(GeometryCountStream,max_pairs=30)
  for i in range(80):
   c=Clock(100+i,i);s=snap('AVZP2' if i<40 else 'BT2',i,c)
   # Candidate has 40 affected pairs after 40AVZ births: choose budget50, still far below1600 live.
   if i==0:candidate=engine(GeometryCountStream,max_pairs=50)
   self.assertEqual(counter(ref.apply(c,upserts=[s])),candidate.apply(c,upserts=[s]))
  self.assertEqual(len(ref.pairs),1600);self.assertLessEqual(candidate.peak_affected_pairs,40);self.assertFalse(hasattr(candidate,'pairs'))
 def test_pair_and_triple_end_and_rebirth(self):
  a=engine(EpisodeStream);b=engine(GeometryCountStream);born=Clock(1,0)
  zs=[snap(f,i,born) for i,f in enumerate(['AVZP2','RACIMO','BT2','BT2A'])]
  self.assertEqual(counter(a.apply(born,upserts=zs)),b.apply(born,upserts=zs))
  for step,lo in [(2,30),(3,0)]:
   c=Clock(step,step);s=Snapshot(zs[2].key,step-1,c,born,lo,lo+10)
   self.assertEqual(counter(a.apply(c,upserts=[s])),b.apply(c,upserts=[s]))
 def test_capacity_still_explicit(self):
  s=engine(GeometryCountStream,max_pairs=1);c=Clock(1,0)
  with self.assertRaises(ValueError):s.apply(c,upserts=[snap('AVZP2',1,c),snap('BT2',2,c),snap('BT2A',3,c)])
  self.assertTrue(s.poisoned)
 def test_empty_atomic_batch_no_repeated_count(self):
  s=engine(GeometryCountStream);self.assertEqual(s.apply(Clock(1,0)),Counter());self.assertEqual(s.apply(Clock(2,1)),Counter())
 def test_edge_contact_and_opposed_orientation_retained(self):
  a=engine(EpisodeStream);b=engine(GeometryCountStream);c=Clock(1,0)
  zs=[snap('AVZP2',0,c,0,3),snap('BT2',1,c,3,6),snap('BT2A',2,c,3,3)]
  self.assertEqual(counter(a.apply(c,upserts=zs)),b.apply(c,upserts=zs))
 def test_geometry_replay_racimo_upstream_equivalence(self):
  params=[{'racimo_min':3,'racimo_bars':250,'racimo_altura_ticks':20}]
  a=GeometryReplay(contract='SYN',tape_sha256=H,racimo_params=params);b=GeometryReplay(contract='SYN',tape_sha256=H,racimo_params=params,count_only=True)
  for obj in (a,b):obj.begin_session('2026-06-16')
  for i in range(12):
   c=Clock(100+i,i);f=['AVZP2','BT2','BT2A'][i%3];x=Capture('BIRTH',ZoneKey(f,H,B,str(i)),c,i,i,0,10,1,())
   ea,xa=a.apply(c,[x],origin_date=lambda x:'2026-06-16');eb,xb=b.apply(c,[x],origin_date=lambda x:'2026-06-16')
   self.assertEqual(counter(ea),eb);self.assertEqual(xa,xb)
 def test_default_engine_unchanged(self):
  s=GeometryReplay(contract='SYN',tape_sha256=H);s.begin_session('2026-06-16');self.assertIsInstance(s.episodes,EpisodeStream)
if __name__=='__main__':unittest.main()
