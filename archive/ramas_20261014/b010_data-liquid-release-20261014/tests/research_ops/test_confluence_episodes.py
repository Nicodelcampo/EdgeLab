import itertools
import random
import unittest
from tools.research_ops.confluence.asof_intersections import Clock,Snapshot,ZoneKey
from tools.research_ops.confluence.episodes import EpisodeStream,TRIPLES
H='a'*64;B='b'*64

def z(f,i,l,h,c,rev=0,born=None):return Snapshot(ZoneKey(f,H,B,str(i)),rev,c,born or c,l,h)
def stream(**kw):return EpisodeStream(contract='INVENTED_MNQ',tape_sha256=H,trade_date='2026-09-01',**kw)
class EpisodeTests(unittest.TestCase):
    def test_triple_common_band_and_no_same_family_votes(self):
        c=Clock(10,0);s=stream();events=s.apply(c,upserts=[z('AVZP2',0,0,5,c),z('BT2',0,3,8,c),z('BT2A',0,4,9,c),z('AVZP2',1,0,5,c)])
        t=[e for e in events if len(e.episode.components)==3];self.assertEqual(len(t),2);self.assertTrue(all((e.episode.lo2,e.episode.hi2)==(4,5) for e in t))
    def test_revision_preserves_origin_and_id_not_new_observation(self):
        s=stream();a=Clock(10,0);s.apply(a,upserts=[z('AVZP2',0,0,5,a),z('BT2',0,3,8,a),z('BT2A',0,4,9,a)]);old=next(iter(s.triples.values()));b=Clock(20,0)
        es=s.apply(b,upserts=[z('AVZP2',0,0,6,b,1,a)]);t=next(e for e in es if len(e.episode.components)==3)
        self.assertEqual(t.action,'UPDATE');self.assertEqual(t.episode.episode_id,old.episode_id);self.assertEqual(t.episode.recognized,a);self.assertEqual(old.hi2,5)
    def test_pair_and_triple_end_on_invalidation(self):
        s=stream();a=Clock(10,0);zs=[z('AVZP2',0,0,5,a),z('BT2',0,3,8,a),z('BT2A',0,4,9,a)];s.apply(a,upserts=zs)
        es=s.apply(Clock(20,0),removals=[zs[1].key]);self.assertEqual(sum(e.action=='END' for e in es),3);self.assertFalse(s.triples);self.assertEqual(len(s.pairs),1)
    def test_shrink_and_reexpand_new_episode_after_actual_loss(self):
        s=stream();a=Clock(10,0);x=z('RACIMO',0,0,5,a);y=z('BT2',0,3,8,a);s.apply(a,upserts=[x,y]);old=next(iter(s.pairs.values()))
        s.apply(Clock(20,0),upserts=[z('RACIMO',0,0,1,Clock(20,0),1,a)]);self.assertFalse(s.pairs)
        es=s.apply(Clock(30,0),upserts=[z('RACIMO',0,0,5,Clock(30,0),2,a)]);self.assertEqual(es[0].action,'START');self.assertNotEqual(es[0].episode.episode_id,old.episode_id)
    def test_no_repeat_on_empty_batch(self):
        s=stream();a=Clock(10,0);s.apply(a,upserts=[z('BT2',0,0,5,a),z('BT2A',0,0,5,a)]);self.assertEqual(s.apply(Clock(20,0)),())
    def test_triple_capacity_poisoned(self):
        s=stream(max_triples=1);a=Clock(10,0)
        with self.assertRaises(ValueError):s.apply(a,upserts=[z('AVZP2',0,0,5,a),z('AVZP2',1,0,5,a),z('BT2',0,0,5,a),z('BT2A',0,0,5,a)])
        self.assertTrue(s.poisoned)
    def test_final_atomic_graph_not_transient(self):
        s=stream();a=Clock(10,0);x=z('AVZP2',0,0,5,a);s.apply(a,upserts=[x,z('BT2',0,0,5,a)]);b=Clock(20,0)
        es=s.apply(b,removals=[x.key],upserts=[z('BT2A',0,0,5,b)]);self.assertFalse(s.triples);self.assertTrue(all(len(e.episode.components)==2 for e in es))
    def test_randomized_final_graph_matches_exhaustive(self):
        rng=random.Random(42);s=stream();serial=0
        for i in range(130):
            c=Clock(100+i,i);up=[];rem=[];active=s.join.active
            if active and rng.random()<.4:rem=[rng.choice(list(active))]
            for _ in range(rng.randrange(1,4)):
                serial+=1;l=rng.randrange(-80,80);up.append(z(rng.choice(['AVZP2','RACIMO','BT2','BT2A']),serial,l,l+rng.randrange(0,15),c))
            s.apply(c,upserts=up,removals=rem);zs=sorted(s.join.active.values(),key=lambda x:x.key)
            pairs=set();triples=set()
            for a,b in itertools.combinations(zs,2):
                if a.key.family!=b.key.family and max(a.lo2,b.lo2)<=min(a.hi2,b.hi2):pairs.add((a.key,b.key))
            for a,b,c0 in itertools.combinations(zs,3):
                if frozenset((a.key.family,b.key.family,c0.key.family)) in TRIPLES and max(a.lo2,b.lo2,c0.lo2)<=min(a.hi2,b.hi2,c0.hi2):triples.add((a.key,b.key,c0.key))
            self.assertEqual(set(s.pairs),pairs);self.assertEqual(set(s.triples),triples)
if __name__=='__main__':unittest.main()
