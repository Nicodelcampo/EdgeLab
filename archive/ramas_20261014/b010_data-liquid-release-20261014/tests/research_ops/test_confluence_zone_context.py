from dataclasses import replace
from datetime import datetime
import math
import random
import unittest
from tools.research_ops.confluence.asof_intersections import Clock, ZoneKey, Snapshot
from tools.research_ops.confluence.zone_context import ZoneContext, union_cells, joint_cells, signed_gap

BASE = int(datetime.fromisoformat('2026-06-15T00:00:00+00:00').timestamp()) * 10**9

def clock(s, seq=0): return Clock(BASE + s * 10**9, seq)
def zone(i, lo, hi, family='AVZP2', s=1):
    c = clock(s)
    return Snapshot(ZoneKey(family, 'a'*64, 'b'*64, str(i)), 0, c, c, lo, hi)
def observe(ctx, s=30, mid=100, prior_mid=80, radius=4):
    return ctx.observe(clock(s), midpoint2=mid, prior_clock=clock(s-20),
                       prior_midpoint2=prior_mid, radius_ticks=radius)

class ContextTests(unittest.TestCase):
    def test_closed_cells_negative_point_and_adjacent(self):
        self.assertEqual(union_cells([(-4,-4),(-3,0),(0,2),(10,10)]),8)
        self.assertEqual(joint_cells([(-4,0),(0,3)],[(0,0),(2,6)]),3)

    def test_empty_explicit_not_physical_negative(self):
        r=observe(ZoneContext(trade_date='2026-06-15'))
        self.assertEqual(r['density'],(0.,)*8);self.assertEqual(r['geometry'],(0.,)*4)
        self.assertEqual(r['arrival'],(0.,)*4);self.assertFalse(any(r['nearest_present'].values()))
        self.assertIn('NOT_NATIVE_LIVENESS',r['scope']);self.assertIn('NOT_FIRST_TOUCH',r['arrival_scope'])

    def test_joint_occupancy_not_independent_votes(self):
        c=ZoneContext(trade_date='2026-06-15');c.apply(clock(1),upserts=(zone(0,96,104),zone(1,96,104,'RACIMO')))
        r=observe(c);self.assertEqual(r['geometry'],(0.,0.,9/17,1.))
        self.assertEqual(r['density'][2],9/17);self.assertEqual(r['arrival'][2:],(1.,1.))

    def test_nearest_outside_local_does_not_scan_all_zones(self):
        c=ZoneContext(trade_date='2026-06-15');c.apply(clock(1),upserts=(zone(0,200,210),zone(1,-300,-200)))
        r=observe(c);self.assertAlmostEqual(r['geometry'][0],math.tanh(100/8))
        self.assertAlmostEqual(r['arrival'][0],math.tanh(20/8));self.assertEqual(r['density'][3],0.)

    def test_new_birth_and_revision_cannot_explain_prior_arrival(self):
        c=ZoneContext(trade_date='2026-06-15');s=zone(0,90,110,s=15);c.apply(clock(15),upserts=(s,))
        self.assertEqual(observe(c)['arrival'],(0.,)*4)
        c.apply(clock(31),upserts=(replace(s,revision=1,available=clock(31),lo2=100),))
        self.assertEqual(observe(c,40)['arrival'],(0.,)*4)
        self.assertEqual(observe(c,60)['arrival'][2],1.)

    def test_future_same_timestamp_sequence_rejected(self):
        c=ZoneContext(trade_date='2026-06-15');s=replace(zone(0,90,110),available=clock(30,2),recognized=clock(30,2))
        c.apply(clock(30,2),upserts=(s,))
        with self.assertRaisesRegex(ValueError,'future snapshot'):
            c.observe(clock(30,1),midpoint2=100,prior_clock=clock(10),prior_midpoint2=80,radius_ticks=4)

    def test_late_mutation_after_anchor_rejected(self):
        c=ZoneContext(trade_date='2026-06-15');observe(c)
        with self.assertRaises(ValueError): c.apply(clock(30),upserts=(zone(0,90,110,s=30),))

    def test_revision_geometry_moves_both_indexes(self):
        c=ZoneContext(trade_date='2026-06-15');s=zone(0,90,110);c.apply(clock(1),upserts=(s,))
        c.apply(clock(2),upserts=(replace(s,revision=1,available=clock(2),lo2=200,hi2=200),))
        r=observe(c);self.assertEqual(c.width['AVZP2'],1);self.assertEqual(r['density'][2],0.)
        self.assertGreater(r['geometry'][0],0.)

    def test_no_resurrection_backdate_or_revision_skip(self):
        c=ZoneContext(trade_date='2026-06-15');s=zone(0,90,110);c.apply(clock(1),upserts=(s,))
        with self.assertRaises(ValueError): c.apply(clock(2),upserts=(replace(s,revision=2,available=clock(2)),))
        c.apply(clock(2),removals=(s.key,))
        with self.assertRaises(ValueError): c.apply(clock(3),upserts=(replace(s,available=clock(3),recognized=clock(3)),))
        with self.assertRaises(ValueError): c.apply(clock(3),upserts=(zone(1,90,110,s=2),))

    def test_capacity_poison_no_prefix_truncation(self):
        c=ZoneContext(trade_date='2026-06-15',max_active=1,max_seen=2)
        with self.assertRaisesRegex(ValueError,'capacity'):c.apply(clock(1),upserts=(zone(0,90,110),zone(1,80,120)))
        self.assertTrue(c.poisoned);self.assertEqual(c.active,{})
        with self.assertRaisesRegex(ValueError,'poisoned'):observe(c)

    def test_query_overflow_poison(self):
        c=ZoneContext(trade_date='2026-06-15',max_query_hits=1);c.apply(clock(1),upserts=(zone(0,90,110),zone(1,90,110)))
        with self.assertRaisesRegex(ValueError,'query capacity'):observe(c)
        self.assertTrue(c.poisoned)

    def test_session_binding_holdout_and_foreign_family(self):
        with self.assertRaises(ValueError):ZoneContext(trade_date='2026-10-01')
        c=ZoneContext(trade_date='2026-06-15')
        with self.assertRaises(ValueError):c.apply(clock(90000),upserts=())
        with self.assertRaises(ValueError):c.apply(clock(1),upserts=(zone(0,1,2,'BT2'),))
        with self.assertRaises(ValueError):observe(c,s=-7201)

    def test_randomized_queries_against_exhaustive_lattice_oracle(self):
        rng=random.Random(725)
        for tape in range(100):
            c=ZoneContext(trade_date='2026-06-15');zs=[]
            for i in range(60):
                lo=rng.randint(-150,150);hi=lo+rng.randint(0,60)
                zs.append(zone(i,lo,hi,'AVZP2' if i%2==0 else 'RACIMO'))
            c.apply(clock(1),upserts=zs)
            for anchor in range(12):
                mid=rng.randint(-200,200);prior=rng.randint(-200,200);radius=rng.randint(1,30)
                r=observe(c,s=30+anchor,mid=mid,prior_mid=prior,radius=radius)
                domain=set(range(mid-2*radius,mid+2*radius+1));sets=[];near=[];arr=[]
                for fi,f in enumerate(('AVZP2','RACIMO')):
                    fs=[s for s in zs if s.key.family==f];allcells=set().union(*(set(range(s.lo2,s.hi2+1)) for s in fs))
                    hits=[s for s in fs if s.lo2<=mid+2*radius and s.hi2>=mid-2*radius]
                    expected=(math.log1p(len(fs)),math.log1p(sum(s.hi2-s.lo2+1 for s in fs)),len(domain&allcells)/len(domain),math.log1p(len(hits)))
                    for a,b in zip(r['density'][fi*4:fi*4+4],expected):self.assertAlmostEqual(a,b)
                    ns=min(fs,key=lambda s:(abs(signed_gap(s,mid)),s.hi2-s.lo2,s.key))
                    near.append(math.tanh(signed_gap(ns,mid)/(2*radius)))
                    arr.append(math.tanh((abs(signed_gap(ns,prior))-abs(signed_gap(ns,mid)))/(2*radius)))
                    sets.append(allcells)
                expected=tuple(near+[len(domain&sets[0]&sets[1])/len(domain),float(mid in sets[0]&sets[1])])
                for a,b in zip(r['geometry'],expected):self.assertAlmostEqual(a,b)
                for a,b in zip(r['arrival'],tuple(arr+[1.,1.])):self.assertAlmostEqual(a,b)

if __name__=='__main__':unittest.main()
