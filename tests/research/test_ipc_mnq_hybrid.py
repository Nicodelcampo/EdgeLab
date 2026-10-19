import json
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
import ipc_mnq_hybrid
from ipc_mnq_hybrid import Config, detect, to_ticks


def sequence(pulls, session="20260310", level=80000, offset=0):
    pairs=[(level-4,level-10)]
    for k in range(len(pulls)+1):
        pairs.append((level,level-1))
        if k<len(pulls):
            pairs.append((level-min(4,pulls[k]),level-pulls[k]))
    pairs.append((level-4,level-10))
    return [dict(session=session,high_ticks=h,low_ticks=l,
                 chart_time=offset+i,closed_at=offset+i+1)
            for i,(h,l) in enumerate(pairs)]


def creations(result,kind="H"):
    return [e for e in result["events"] if e["event"]=="CREATE"
            and e["state"]["kind"]==kind]


class HybridTest(unittest.TestCase):
    def test_dense(self):
        z=creations(detect(sequence([10]*5)))
        self.assertEqual(len(z),1)
        self.assertEqual((z[0]["state"]["peaks_count"],z[0]["state"]["visits"],z[0]["state"]["route"]),(6,1,"DENSE"))

    def test_mixed(self):
        z=creations(detect(sequence([10,16,10])))
        self.assertEqual(len(z),1)
        self.assertEqual((z[0]["state"]["peaks_count"],z[0]["state"]["visits"],z[0]["state"]["route"]),(4,2,"MIXED"))

    def test_spaced(self):
        z=creations(detect(sequence([16,16])))
        self.assertEqual(len(z),1)
        self.assertEqual((z[0]["state"]["peaks_count"],z[0]["state"]["visits"],z[0]["state"]["route"]),(3,3,"SPACED"))

    def test_two_visits_not_enough(self):
        self.assertFalse(creations(detect(sequence([30]))))

    def test_tiny_pull_not_counted(self):
        self.assertFalse(creations(detect(sequence([3]*8))))

    def test_append_only_prefix_invariance(self):
        bars=sequence([10]*6)
        bars.extend(dict(session="20260310",high_ticks=80020,
                         low_ticks=79990,chart_time=len(bars)+i,
                         closed_at=len(bars)+i+1) for i in range(3))
        full=detect(bars)
        for cut in range(1,len(bars)+1):
            self.assertEqual(detect(bars[:cut])["events"],
                             [e for e in full["events"] if e["available_i"]<cut])

    def test_confirmation_lag(self):
        result=detect(sequence([16,16]))
        for e in result["events"]:
            for p in e.get("state",{}).get("peaks",[]):
                self.assertEqual(p["confirmed_i"],p["i"]+1)
                self.assertLessEqual(p["confirmed_i"],e["available_i"])

    def test_session_reset(self):
        bars=sequence([10,10],session="A")
        bars+=sequence([10,10],session="B",offset=len(bars))
        self.assertFalse(creations(detect(bars)))

    def test_multiple_distinct_zones_preserved(self):
        bars=sequence([10]*5)
        n=len(bars)
        bars.append(dict(session="20260310",high_ticks=80030,low_ticks=80010,
                         chart_time=n,closed_at=n+1))
        bars+=sequence([16,16],level=79900,offset=len(bars))
        r=detect(bars);z=creations(r)
        self.assertEqual(len(z),2)
        self.assertNotEqual(z[0]["zone_id"],z[1]["zone_id"])
        self.assertEqual(len([x for x in r["zonas"] if x["kind"]=="H"]),2)
        self.assertEqual(next(x for x in r["zonas"] if x["zone_id"]==z[0]["zone_id"])["status"],"BROKEN")

    def test_expiration(self):
        bars=sequence([10]*5);n=len(bars)
        bars += [dict(session="20260310",high_ticks=79980,low_ticks=79970,
                      chart_time=n+i,closed_at=n+i+1) for i in range(65)]
        self.assertTrue(any(e["event"]=="CLOSE" and e["reason"]=="EXPIRED" for e in detect(bars)["events"]))

    def test_high_low_symmetry(self):
        a=sequence([16,16])
        b=[dict(x,high_ticks=160000-x["low_ticks"],
                low_ticks=160000-x["high_ticks"]) for x in a]
        hi=creations(detect(a))[0]["state"]
        lo=creations(detect(b),"L")[0]["state"]
        self.assertEqual((hi["peaks_count"],hi["visits"],hi["route"]),
                         (lo["peaks_count"],lo["visits"],lo["route"]))

    def test_endpoint_range_not_extra_visit(self):
        bars=sequence([10]*5)
        for b in bars:
            if b["high_ticks"]==80000:
                b["low_ticks"]=79950
        self.assertEqual(creations(detect(bars))[0]["state"]["visits"],1)

    def test_grid_and_clock_fail_closed(self):
        with self.assertRaises(ValueError):to_ticks(20000.01,.25)
        a=sequence([16,16]);a[2]["closed_at"]=-1
        with self.assertRaises(ValueError):detect(a)
        with self.assertRaises(ValueError):detect(sequence([16,16]),Config(visit_exit_ticks=7))

    def test_cli_source_untouched_and_index_mapping(self):
        bars=sequence([16,16],session="A")
        n=len(bars)
        bars.append(dict(session="A",high_ticks=79996,low_ticks=79990,chart_time=n,closed_at=n+1))
        bars+=sequence([10]*5,session="B",offset=len(bars))
        n=len(bars)
        bars.append(dict(session="B",high_ticks=79996,low_ticks=79990,chart_time=n,closed_at=n+1))
        bundle={"meta":{"asset":"MNQ_TEST","tick_size":.25},
                "bar_series":{"tick_25":{"candles":[
                  {"time":x["chart_time"],"high":x["high_ticks"]*.25,
                   "low":x["low_ticks"]*.25,"session":x["session"]}
                  for x in bars]}}}
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"MNQ_TEST.json";out=Path(td)/"layer.json"
            src.write_text(json.dumps(bundle));before=src.read_bytes()
            subprocess.run([sys.executable,str(Path(ipc_mnq_hybrid.__file__)),
                            "--input",str(src),"--output",str(out)],check=True,capture_output=True)
            r=json.loads(out.read_text())
            self.assertEqual(src.read_bytes(),before)
            self.assertEqual(r["closed_bars"],len(bars)-2)
            self.assertEqual(len(creations(r)),2)
            for z in r["zonas"]:
                self.assertEqual(z["t0"],bundle["bar_series"]["tick_25"]["candles"][z["i0"]]["time"])
            self.assertFalse(r["outcomes_computed"])

    def test_two_levels_can_coexist(self):
        bars=sequence([10]*5)
        bars+=sequence([10]*5,level=79950,offset=len(bars))
        z=[z for z in detect(bars)["zonas"] if z["kind"]=="H"]
        self.assertEqual(len(z),2)
        self.assertTrue(all(z["status"]=="ACTIVE" for z in z))

    def test_data_gap_not_bridged(self):
        bars=sequence([10,10])
        bars+=sequence([10,10],offset=4000)
        self.assertFalse(creations(detect(bars)))

    def test_duplicate_times_preserved(self):
        a=sequence([16,16])
        for b in a:b["chart_time"]=1;b["closed_at"]=1
        z=creations(detect(a))
        self.assertEqual(len(z),1)
        self.assertEqual(len(z[0]["state"]["peaks"]),3)

    def test_total_width_not_endless_staircase(self):
        bars=[]
        for k in range(8):
            level=80000-k*7
            for h,l in [(level-4,level-10),(level,level-1)]:
                i=len(bars);bars.append(dict(session="A",high_ticks=h,low_ticks=l,chart_time=i,closed_at=i+1))
        i=len(bars);bars.append(dict(session="A",high_ticks=79940,low_ticks=79930,chart_time=i,closed_at=i+1))
        z=[z for z in detect(bars)["zonas"] if z["kind"]=="H"]
        self.assertGreaterEqual(len(z),2)
        self.assertTrue(all(abs(x["p1"]-x["p0"])/.25<=21 for x in z))
        self.assertTrue(all(x["toques"]<=4 for x in z))


if __name__=="__main__":
    unittest.main(verbosity=2)