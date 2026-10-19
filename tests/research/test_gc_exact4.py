from pathlib import Path
import copy
import json
import sys
import tempfile
import unittest
repo_tools=Path(__file__).resolve().parents[2]/"tools"
if repo_tools.exists():sys.path.insert(0,str(repo_tools))
from escalonadas_exact4 import Exact4
from gc_exact4_variants import resolve,census,round_half_up
from gc_exact4_prepare import capture,run_census

P=dict(w=1,max_gap=15,max_step=2,min_pull=5,dmax=35,total_min=0,
       step_min=0,confirm_ticks=2,confirmation_mode="precio",nmin=3)


def wave(n):
    out=[(100,99,99,0)]
    for k in range(n):
        peak=120-k
        out.extend([(peak,peak-1,peak-1,2*k+1),(peak-10,peak-11,peak-11,2*k+2)])
    return out


def run(rows,p=None):
    d=Exact4(P if p is None else p)
    for r in rows:d.append(*r,session_id="s")
    return d


def H(d):return [e for e in d.events if e["kind"]=="H"]


def baseline():
    return dict(scope="LOCAL_CAPTURED_CURRENT_CONFIG",instrument="GC",tick_size=.1,
        asset="SYNTHETIC_TEST_NOT_REAL_CONFIG",bar_type="LAST",bar_size=150,
        window="fixture",family="fixture",source_sha256="a"*64,params=copy.deepcopy(P))


class TestExact4(unittest.TestCase):
    def test_three_four(self):
        self.assertEqual(len(H(run(wave(3)))),0)
        e=H(run(wave(4)))[0]
        self.assertEqual(e["members"],[1,3,5,7])
        self.assertEqual((e["det_i"],e["pico4_i"],e["det_pico"],e["n_peaks"]),(8,7,4,4))

    def test_fifth_seventh_do_not_grow_or_redispatch(self):
        original=H(run(wave(4)))[0]
        for n in (5,6,7):
            events=H(run(wave(n)))
            self.assertEqual(events,[original])

    def test_eight_disjoint(self):
        events=H(run(wave(8)))
        self.assertEqual(len(events),2)
        self.assertEqual(events[1]["members"],[9,11,13,15])
        self.assertFalse(set(events[0]["members"])&set(events[1]["members"]))

    def test_no_fifth_rescue(self):
        p=dict(P,total_min=4)
        d=run(wave(5),p)
        self.assertEqual(H(d),[])
        rejects=[r for r in d.rejections if r["kind"]=="H"]
        self.assertEqual(len(rejects),1);self.assertEqual(rejects[0]["det_i"],8)

    def test_fourth_duration_reject(self):
        d=run(wave(4),dict(P,dmax=3))
        self.assertEqual(H(d),[])
        self.assertEqual([r for r in d.rejections if r["kind"]=="H"][0]["reasons"],["duration"])

    def test_prefix_every_bar(self):
        full=run(wave(8))
        for j in range(1,len(wave(8))+1):
            short=run(wave(8)[:j])
            self.assertEqual(short.events,[e for e in full.events if e["det_i"]<j])

    def test_mirror_symmetry(self):
        rows=wave(8);a=run(rows)
        reflected=[(300-l,300-h,300-c,t) for h,l,c,t in rows]
        b=run(reflected)
        for e in H(a):
            match=next(x for x in b.events if x["kind"]=="L" and x["det_i"]==e["det_i"])
            self.assertEqual(e["members"],match["members"])
            self.assertEqual(match["trigger_tick"],300-e["trigger_tick"])

    def test_caller_cannot_mutate_events(self):
        d=run(wave(4));copy1=d.events;copy1[0]["members"].append(999)
        self.assertTrue(all(len(e["members"])==4 for e in d.events))

    def test_duplicate_confirmation_not_fifth_or_second_event(self):
        d=run(wave(4));events=d.events
        self.assertIsNone(d._accept(1,7,8))
        self.assertEqual(events,d.events)

    def test_multiple_completed_bars_same_timestamp_preserve_prefix(self):
        rows=[(h,l,c,0) for h,l,c,t in wave(4)]
        d=run(rows)
        self.assertEqual(H(d)[0]["det_i"],8)
        self.assertEqual(H(d)[0]["members"],[1,3,5,7])
        self.assertEqual(H(d)[0]["publication_scope"],
            "COMPLETED_BAR_LOGICAL_ONLY_CALLER_MUST_ATTACH_RAW_AVAILABILITY")

    def test_eof_does_not_confirm_fourth(self):
        d=run(wave(4)[:-1]);self.assertEqual(H(d),[])
        d.finish_diagnostic();self.assertEqual(H(d),[])

    def test_session_and_gap_reset(self):
        rows=wave(4)
        d=Exact4(P)
        for i,r in enumerate(rows):d.append(*r,session_id="a" if i<7 else "b")
        self.assertEqual(H(d),[])
        shifted=[(h,l,c,t+(4000 if i>=7 else 0)) for i,(h,l,c,t) in enumerate(rows)]
        self.assertEqual(H(run(shifted)),[])

    def test_delayed_confirmation(self):
        rows=wave(4)
        # Last peak not confirmed until a later completed bar reaches threshold.
        rows[-1]=(116,116,116,8)
        d=run(rows,dict(P,confirm_ticks=2))
        self.assertEqual(H(d),[])
        d.append(115,114,114,9,session_id="s")
        self.assertEqual(H(d)[0]["det_i"],9)

    def test_gc_reported_thresholds_four_and_flat_variant_are_distinct(self):
        p=dict(P,w=1,max_gap=30,max_step=49,min_pull=25,dmax=1000000,confirm_ticks=28)
        rows=[(19000,18999,18999,0)]
        for k in range(4):
            peak=20000-30*k
            rows.extend([(peak,peak-1,peak-1,2*k+1),
                         (peak-110,peak-120,peak-115,2*k+2)])
        self.assertEqual(H(run(rows,p))[0]["members"],[1,3,5,7])
        self.assertEqual(H(run(rows,dict(p,max_step=25))),[])

    def test_velas_mode(self):
        d=run(wave(4),dict(P,confirmation_mode="velas",confirm_ticks=None))
        self.assertEqual(H(d)[0]["members"],[1,3,5,7])

    def test_ohlc_grid_order_fail_closed(self):
        d=Exact4(P)
        for args in ((1,2,1,0),(2.1,1,1,0),(2,1,1,float("nan"))):
            with self.assertRaises(ValueError):d.append(*args)
        d.append(2,1,1,1)
        with self.assertRaises(ValueError):d.append(2,1,1,0)


class TestResolverCensus(unittest.TestCase):
    def test_no_current_config_no_defaults(self):
        with self.assertRaises(ValueError):resolve({})

    def test_profiles_and_no_baseline_mutation(self):
        b=baseline();original=copy.deepcopy(b);r=resolve(b)
        self.assertEqual(b,original)
        self.assertEqual(len(r["profiles"]),5)
        self.assertEqual(r["profiles"][0]["params"],P)
        self.assertEqual(r["profiles"][1]["params"]["nmin"],4)
        self.assertEqual(r["profiles"][2]["params"]["max_gap"],11)
        self.assertEqual(r["profiles"][3]["params"]["max_gap"],23)
        self.assertEqual(r["profiles"][4]["params"]["max_step"],1)
        self.assertEqual(round_half_up(2.5),3)

    def test_unbounded_dmax(self):
        b=baseline();b["params"]["dmax"]=None
        self.assertIsNone(resolve(b)["profiles"][3]["params"]["dmax"])

    def test_user_report_keeps_duration_sentinel_and_discloses_no_bundle(self):
        b=baseline();b["scope"]="USER_REPORTED_CURRENT_CONFIG_CODE_CHECKED"
        b["params"]["dmax"]=1000000;b["dmax_unbounded_sentinel"]=True
        r=resolve(b)
        self.assertEqual(r["profiles"][3]["params"]["dmax"],1000000)
        self.assertFalse(r["baseline_bundle_independently_hashed"])

    def test_alias_dedup_before_census(self):
        b=baseline()
        b["params"].update(max_gap=1,min_pull=1,max_step=0,total_min=0,step_min=0,dmax=None)
        r=resolve(b)
        self.assertEqual(r["profiles"][2]["alias_of"],"C1_EXACT4")
        self.assertEqual(r["profiles"][4]["alias_of"],"C1_EXACT4")

    def test_census_does_not_fake_current_detector_or_live_publication(self):
        rows=[dict(high_tick=h,low_tick=l,close_tick=c,time=t,session_id="s") for h,l,c,t in wave(4)]
        results=census(rows,resolve(baseline()))
        self.assertEqual(results[0]["status"],"ABSTAIN_USE_CURRENT_DETECTOR_FOR_C0")
        r=results[1];self.assertEqual(r["counts"]["zones_H"],1)
        self.assertEqual(r["publications_metadata_pass"],0)
        self.assertTrue(all(not s["outcome_computed"] for s in r["signals_private"]))

    def test_publication_requires_observed_row_boundary(self):
        rows=[dict(high_tick=h,low_tick=l,close_tick=c,time=t,session_id="s",
            available_row=i*10+2,snapshot_asof_row=i*10+1,bar_close_row=i*10,
            available_ts_us=t*1000000+1,snapshot_ts_us=t*1000000,
            publication_mode="OBSERVED_NEXT_TIMESTAMP_ROW")
            for i,(h,l,c,t) in enumerate(wave(4))]
        r=census(rows,resolve(baseline()))[1]
        self.assertEqual(r["publications_metadata_pass"],len(r["signals_private"]))
        self.assertFalse(any(e["financial_use_certified"] for e in r["signals_private"]))

    def test_old_timestamp_is_not_valid_publication(self):
        rows=[dict(high_tick=h,low_tick=l,close_tick=c,time=t,session_id="s",
            available_row=i*10+2,snapshot_asof_row=i*10+1,bar_close_row=i*10,
            available_ts_us=t*1000000,snapshot_ts_us=t*1000000,
            publication_mode="OBSERVED_NEXT_TIMESTAMP_ROW")
            for i,(h,l,c,t) in enumerate(wave(4))]
        self.assertEqual(census(rows,resolve(baseline()))[1]["publications_metadata_pass"],0)

    def test_capture_selected_layer_without_guessing_series_or_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            params={k:v for k,v in P.items() if k not in ("confirmation_mode","confirm_ticks")}
            (d/"det.json").write_text(json.dumps(dict(asset="GC_fixture",
                parametros=params,variante="fixture · confirmación por precio (2 ticks)",zonas=[])))
            (d/"chart.json").write_text(json.dumps(dict(meta=dict(tick_size=.1),
                bar_series={"chosen":{"candles":[dict(time=0),dict(time=1)]}})))
            b=capture(d/"det.json",d/"chart.json","chosen","LAST",150)
            self.assertEqual(b["params"]["confirm_ticks"],2)
            with self.assertRaises(ValueError):
                capture(d/"det.json",d/"chart.json","not-selected","LAST",150)
            data=json.loads((d/"det.json").read_text());data["variante"]="unresolved"
            (d/"det.json").write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                capture(d/"det.json",d/"chart.json","chosen","LAST",150)

    def test_private_events_separate_and_do_not_overwrite_output(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);base=d/"base.json";bars=d/"bars.jsonl";out=d/"out"
            base.write_text(json.dumps(baseline()))
            rows=[dict(high_tick=h,low_tick=l,close_tick=c,close_ts_us=t*1000000,session_id="s")
                  for h,l,c,t in wave(4)]
            bars.write_text("".join(json.dumps(r)+"\n" for r in rows))
            result=run_census(base,bars,out)
            self.assertFalse(result["outcomes_computed"])
            self.assertNotIn("signals_private",json.dumps(result))
            self.assertTrue((out/"C1_EXACT4_events_private.jsonl").exists())
            with self.assertRaises(ValueError):run_census(base,bars,out)


if __name__=="__main__":unittest.main(verbosity=2)