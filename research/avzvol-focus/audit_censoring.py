"""Fixed-bank worst-case unresolved-outcome envelopes; retain every recipe."""
import os,json,sqlite3,math
from pathlib import Path
from collections import defaultdict
import pandas as pd
from scalar_checks import scalar_gate
P=Path('/data/analysis/avzvol-focus');C=os.environ.get('FOCUS_CONTRACT','MNQ_12-26');R=P/C;bank=json.load(open(P/'frozen-replication-bank.json'));con=sqlite3.connect(R/'thinned-private.sqlite');rows=[]
for recipe in bank['recipes']:
 a=pd.read_sql_query('SELECT * FROM signals WHERE family=? AND landmark=? AND D=? AND q=? AND endpoint=?',con,params=(recipe['family'],recipe['landmark'],recipe['D'],recipe['q'],recipe['endpoint'])).to_dict('records');groups=defaultdict(lambda:[[0,0,0],[0,0,0]]);totals=[[0,0,0],[0,0,0]]
 for r in a:
  if not scalar_gate(r,recipe['condition']):continue
  o=0 if r['origin']=='real' else 1;label=0 if r['status']=='TARGET_FIRST' else 1 if r['status']=='OPPOSITE_FIRST' else 2;span=min((r['volatility256_ticks'] if r['volatility256_ticks'] is not None else -40)//40,4);key=(r['session'],int(r['hour'])//3,span,min(r['remaining_ticks']//10,8));groups[key][o][label]+=1;totals[o][label]+=1
 weight=low=high=0.;common=0
 for rr,cc in groups.values():
  nr,nc=sum(rr),sum(cc)
  if nr and nc:
   w=min(nr,nc);weight+=w;low+=w*(rr[0]/nr-(cc[0]+cc[2])/nc);high+=w*((rr[0]+rr[2])/nr-cc[0]/nc);common+=1
 rows.append(dict(recipe_id=recipe['recipe_id'],contract=C,real_signals=sum(totals[0]),real_unresolved=totals[0][2],control_signals=sum(totals[1]),control_unresolved=totals[1][2],all_signal_matched_weight=weight,all_signal_common_strata=common,worst_case_unresolved_difference_points=100*low/weight if weight else None,best_case_unresolved_difference_points=100*high/weight if weight else None,worst_case_point_positive=bool(weight and low>0),does_not_include_statistical_uncertainty=True,does_not_reselect_bank=True))
con.close();out=dict(status='FIXED_BANK_CENSOR_ENVELOPES_COMPLETE',contract=C,recipe_count=len(rows),worst_case_point_positive_count=sum(r['worst_case_point_positive'] for r in rows),results=rows,meaning='common strata and min-count weights recalculated on ALL gated signals; unresolved real assigned loss/control assigned target for worst bound, reverse for best; envelopes are sensitivity bounds, not confidence intervals or proof of advantage');(R/'censor-audit-evidence.json').write_text(json.dumps(out,indent=2)+'\n');pd.DataFrame(rows).to_csv(R/'censor-audit.csv',index=False);print('CENSOR_ENVELOPES',C,len(rows),out['worst_case_point_positive_count'],flush=True)
