"""Invented AVZ births/racimo snapshots flowing into the interval join."""
import unittest
from tools.research_ops.confluence.asof_intersections import Clock,Snapshot,ZoneKey,AsOfJoin
from tools.research_ops.confluence.racimo_asof import RacimoTape,Creation
H='a'*64;B='b'*64
class IntegrationTests(unittest.TestCase):
    def test_no_racimo_confluence_before_recognition_and_removal_atomic(self):
        r=RacimoTape(params={'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10},config_sha256=H,build_sha256=B)
        j=AsOfJoin(contract='INVENTED_MNQ',tape_sha256=H,trade_date='2026-09-01')
        bt=None
        for i in range(3):
            c=Clock(100+i,i);creation=Creation(str(i),i,100,101,'2026-09-01',c)
            observations=r.observe_batch([creation]);ups=[Snapshot(ZoneKey('AVZP2',H,B,str(i)),0,c,c,200,202)]
            if i==0:
                bt=Snapshot(ZoneKey('BT2',H,B,'trap'),0,c,c,201,203,1);ups.append(bt)
            ups.extend(o.snapshot for o in observations);pairs=j.apply(c,upserts=ups)
            rp=[p for p in pairs if 'RACIMO' in (p.left.key.family,p.right.key.family)]
            self.assertEqual(bool(rp),i==2)
            for p in rp:self.assertEqual(p.observed,c)
        c=Clock(103,3);obs=r.observe_batch([Creation('3',3,102,103,'2026-09-01',c)])
        pairs=j.apply(c,upserts=[o.snapshot for o in obs],removals=[bt.key])
        self.assertTrue(all('BT2' not in (p.left.key.family,p.right.key.family) for p in pairs))
    def test_cross_session_members_not_silently_labeled_session_only(self):
        r=RacimoTape(params={'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10},config_sha256=H,build_sha256=B)
        for i in range(2):r.observe_batch([Creation(str(i),i,100,101,'2026-09-01',Clock(100+i,i))])
        obs=r.observe_batch([Creation('2',2,100,101,'2026-09-02',Clock(102,2))]);self.assertTrue(obs[0].spans_sessions)
        # Consumer primary policy explicitly excludes this formation.
        primary=[o for o in obs if not o.spans_sessions];self.assertEqual(primary,[])
if __name__=='__main__':unittest.main()
