"""All prices/clocks/configs below invented. No market or network access."""
import random
import unittest
from tools.research_ops.confluence.asof_intersections import Clock,ZoneKey,Snapshot,AsOfJoin

H='a'*64;B='b'*64

def snap(fam,i,lo,hi,c,revision=0,born=None,side=0,config=H):
    return Snapshot(ZoneKey(fam,config,B,str(i)),revision,c,born or c,lo,hi,side)

def join(**kw):return AsOfJoin(contract='INVENTED_MNQ',tape_sha256=H,trade_date='2026-09-01',**kw)

def oracle(active,changed,c):
    # Independent exhaustive geometry, orientation and relation derivation.
    zs=sorted(active.values(),key=lambda s:s.key);out=[]
    for i,a in enumerate(zs):
        for b in zs[i+1:]:
            if a.key.family==b.key.family or not ({a.key,b.key}&changed):continue
            if a.lo2>b.hi2 or b.lo2>a.hi2:continue
            l=max(a.lo2,b.lo2);h=min(a.hi2,b.hi2)
            if (a.lo2,a.hi2)==(b.lo2,b.hi2):r='IDENTICAL'
            elif (a.lo2<=b.lo2 and a.hi2>=b.hi2) or (b.lo2<=a.lo2 and b.hi2>=a.hi2):r='CONTAINMENT'
            elif l==h:r='EDGE_CONTACT'
            else:r='PARTIAL_OVERLAP'
            d='UNSPECIFIED' if 0 in (a.side,b.side) else ('SAME' if a.side==b.side else 'OPPOSED')
            out.append((a,b,c,l,h,r,d))
    return out

def flatten(ps):return [(p.left,p.right,p.observed,p.lo2,p.hi2,p.relation,p.orientation) for p in ps]

class JoinTests(unittest.TestCase):
    def test_edge_contact_and_half_ticks(self):
        j=join();c=Clock(10,0);a=snap('AVZP2',0,1,3,c);b=snap('BT2',0,3,5,c,side=1)
        ps=j.apply(c,upserts=[a,b]);self.assertEqual(len(ps),1);self.assertEqual(ps[0].relation,'EDGE_CONTACT');self.assertEqual(ps[0].lo2,3)
    def test_containment_and_negative_prices(self):
        j=join();c=Clock(10,0);ps=j.apply(c,upserts=[snap('AVZP2',0,-5,5,c),snap('BT2A',0,-3,-1,c)])
        self.assertEqual(ps[0].relation,'CONTAINMENT')
    def test_same_family_not_independent_confluence(self):
        j=join();c=Clock(10,0);self.assertEqual(j.apply(c,upserts=[snap('BT2',0,1,3,c),snap('BT2',1,1,3,c,config='c'*64)]),())
    def test_same_timestamp_different_sequence_is_later(self):
        j=join();a=Clock(10,0);b=Clock(10,1);j.apply(a,upserts=[snap('AVZP2',0,1,3,a)])
        self.assertEqual(j.apply(b,upserts=[snap('BT2',0,1,3,b)])[0].observed,b)
    def test_duplicate_batch_clock_rejected(self):
        j=join();c=Clock(10,0);j.apply(c)
        with self.assertRaises(ValueError):j.apply(c)
    def test_future_snapshot_rejected_before_mutation(self):
        j=join();c=Clock(10,0)
        with self.assertRaises(ValueError):j.apply(c,upserts=[snap('AVZP2',0,1,3,Clock(11,0))])
        self.assertEqual(j.active,{})
    def test_racimo_no_retroactive_start(self):
        j=join();c=Clock(10,0)
        with self.assertRaises(ValueError):j.apply(c,upserts=[snap('RACIMO',0,1,3,c,born=Clock(5,0))])
    def test_expansion_new_revision_only_asof_now(self):
        j=join();a=Clock(10,0);b=Clock(20,0);r=snap('RACIMO',0,1,3,a);t=snap('BT2',0,5,7,a);self.assertEqual(j.apply(a,upserts=[r,t]),())
        ps=j.apply(b,upserts=[snap('RACIMO',0,1,6,b,revision=1,born=a)])
        self.assertEqual(ps[0].lo2,5);self.assertEqual(ps[0].observed,b);self.assertEqual(r.hi2,3)
    def test_remove_before_create_no_transient_overlap(self):
        j=join();a=Clock(10,0);z=snap('AVZP2',0,1,3,a);j.apply(a,upserts=[z]);b=Clock(20,0)
        self.assertEqual(j.apply(b,removals=[z.key],upserts=[snap('BT2',0,1,3,b)]),())
    def test_no_resurrection(self):
        j=join();a=Clock(10,0);z=snap('AVZP2',0,1,3,a);j.apply(a,upserts=[z]);j.apply(Clock(20,0),removals=[z.key])
        with self.assertRaises(ValueError):j.apply(Clock(30,0),upserts=[snap('AVZP2',0,1,3,Clock(30,0))])
    def test_conflicting_batch_rejected(self):
        j=join();a=Clock(10,0);z=snap('AVZP2',0,1,3,a);j.apply(a,upserts=[z]);b=Clock(20,0)
        with self.assertRaises(ValueError):j.apply(b,removals=[z.key],upserts=[snap('AVZP2',0,1,3,b,1,a)])
    def test_missing_removal_rejected(self):
        j=join()
        with self.assertRaises(ValueError):j.apply(Clock(10,0),removals=[ZoneKey('BT2',H,B,'x')])
    def test_pair_overflow_poisoned_not_truncated(self):
        j=join(max_pairs=1);c=Clock(10,0)
        with self.assertRaises(ValueError):j.apply(c,upserts=[snap('AVZP2',0,1,3,c),snap('BT2',0,1,3,c),snap('BT2A',0,1,3,c)])
        self.assertTrue(j.poisoned)
        with self.assertRaises(ValueError):j.apply(Clock(20,0))
    def test_active_capacity_precheck(self):
        j=join(max_active=1);c=Clock(10,0)
        with self.assertRaises(ValueError):j.apply(c,upserts=[snap('AVZP2',0,1,3,c),snap('BT2',0,1,3,c)])
        self.assertFalse(j.poisoned);self.assertEqual(j.active,{})
    def test_seen_capacity(self):
        j=join(max_active=1,max_seen=1);a=Clock(10,0);z=snap('AVZP2',0,1,3,a);j.apply(a,upserts=[z]);j.apply(Clock(20,0),removals=[z.key])
        with self.assertRaises(ValueError):j.apply(Clock(30,0),upserts=[snap('BT2',1,1,3,Clock(30,0))])
    def test_reject_holdout(self):
        with self.assertRaises(ValueError):AsOfJoin(contract='X',tape_sha256=H,trade_date='2026-10-01')
    def test_no_reemit_without_mutation(self):
        j=join();c=Clock(10,0);j.apply(c,upserts=[snap('AVZP2',0,1,3,c),snap('BT2',0,1,3,c)])
        self.assertEqual(j.apply(Clock(20,0)),())
    def test_duplicate_zone_ids_across_configs_are_distinct(self):
        j=join();c=Clock(10,0);zs=[snap('AVZP2',0,1,3,c),snap('BT2',0,1,3,c),snap('BT2',0,1,3,c,config='c'*64)]
        self.assertEqual(len(j.apply(c,upserts=zs)),2)
    def test_batch_order_invariant(self):
        c=Clock(10,0);zs=[snap('AVZP2',0,1,3,c),snap('BT2',0,1,3,c),snap('BT2A',0,2,4,c)]
        self.assertEqual(join().apply(c,upserts=zs),join().apply(c,upserts=zs[::-1]))
    def test_orientation(self):
        j=join();c=Clock(10,0);ps=j.apply(c,upserts=[snap('BT2',0,1,3,c,side=1),snap('BT2A',0,1,3,c,side=-1)])
        self.assertEqual(ps[0].orientation,'OPPOSED')
    def test_revision_jump_rejected(self):
        j=join();a=Clock(10,0);j.apply(a,upserts=[snap('AVZP2',0,1,3,a)])
        with self.assertRaises(ValueError):j.apply(Clock(20,0),upserts=[snap('AVZP2',0,1,3,Clock(20,0),2,a)])
    def test_prefix_same_as_full(self):
        batches=[]
        for i in range(25):
            c=Clock(10+i,i);batches.append((c,[snap(('AVZP2','BT2','BT2A','RACIMO')[i%4],i,i,i+5,c)]))
        a=join();full=[a.apply(c,upserts=z) for c,z in batches];b=join();prefix=[b.apply(c,upserts=z) for c,z in batches[:10]]
        self.assertEqual(full[:10],prefix)
    def test_randomized_reference_with_deletes_and_expansions(self):
        rng=random.Random(20261011);j=join();active={};serial=0
        for i in range(250):
            c=Clock(100+i,i);rem=[];up=[]
            if active and rng.random()<.4:rem=[rng.choice(list(active))]
            if active and rng.random()<.4:
                possible=[s for k,s in active.items() if k not in rem]
                if possible:
                    old=rng.choice(possible);up.append(Snapshot(old.key,old.revision+1,c,old.recognized,old.lo2-1,old.hi2+1,old.side))
            for _ in range(rng.randrange(1,4)):
                lo=rng.randrange(-200,200);serial+=1;up.append(snap(rng.choice(sorted(('AVZP2','BT2','BT2A','RACIMO'))),serial,lo,lo+rng.randrange(0,20),c,side=rng.choice([-1,0,1])))
            for k in rem:del active[k]
            for s in up:active[s.key]=s
            self.assertEqual(flatten(j.apply(c,upserts=up,removals=rem)),oracle(active,{s.key for s in up},c))
            self.assertEqual(j.active,active)
if __name__=='__main__':unittest.main()
