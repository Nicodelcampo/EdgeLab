from pathlib import Path
import json,math,hashlib,collections
r=Path(__file__).parent; j=json.loads((r/'output/results.json').read_text()); rows=[json.loads(x) for x in (r/'inputs/new_slots_PRIVATE.jsonl').read_text().splitlines()];checks={};contractmeans={}
for f,a in j['RTY'].items():
 s=[x for x in rows if x['asset']=='RTY' and x['family']==f];assert len(s)==a['trades'];assert len({x['id'] for x in s})==len(s)
 # Independent reconstruction from immutable bid/ask endpoints, no borrowed summary function.
 pn=[(x['exit_bid']-x['entry_ask'] if x['direction']==1 else x['entry_bid']-x['exit_ask'])-2-.9 for x in s]
 assert all(math.isclose(v,x['net_ticks'],abs_tol=1e-9) for v,x in zip(pn,s))
 assert math.isclose(math.fsum(pn)/len(s),a['mean_net_ticks'],abs_tol=1e-9)
 assert math.isclose(math.fsum(sorted(pn)[:-5]),a['top_trades']['5']['sum_remaining_ticks'],abs_tol=1e-8)
 cm={}
 for c,v in a['contract_folds'].items():
  sub=[x for x in s if x['contract']==c];assert len(sub)==v['n'];assert math.isclose(math.fsum(x['net_ticks'] for x in sub),v['net_ticks'],abs_tol=1e-8);cm[c]=v['net_ticks']/v['n']
 for m,v in a['monthly'].items():
  sub=[x for x in s if x['day'][:6]==m];assert len(sub)==v['n'];assert math.isclose(math.fsum(x['net_ticks'] for x in sub)/len(sub),v['mean_ticks'],abs_tol=1e-8)
 contractmeans[f]=cm;checks[f]={'quote_arithmetic':True,'counts_unique':True,'best5_trades_reconciled':True,'contract_and_month_crossfoot':True}
plan=[{'grain':'contract x frozen RTY momentum timeframe','population':'54 already exposed common Oct-Dec2025 dates; unequal exposure','unit':'mean net ticks/trade','finding':'MOM5 reverses sign in March2026 contract; MOM15 positive but only8 trades','derivation':'sum immutable netticks / contract tradecount','disposition':'chart','reason':'aggregate obscures contractual failure'}, {'grain':'month x timeframe','unit':'mean ticks/trade','finding':'all3 months positive, not monotonic','disposition':'table','reason':'secondary to contractual G1gate'}, {'grain':'profile','unit':'counts and gates','finding':'neither passesG1;G2blocked','disposition':'prose','reason':'gate classification, not a comparable magnitude'}]
spec={'version':1,'form':'categorical-bars','title':'MOM5 cambia de signo entre contratos de RTY','aside':'Ticks netos medios por trade; 12-25: n=94/78, 03-26: n=14/8 (MOM5/MOM15)','mode':'grouped','orientation':'vertical','axis':{'zero':True},'derived':True,'derivationReason':'Suma de ticks netos por contrato dividida por sus trades; misma regla y costos supuestos','labels':['RTY 12-25','RTY 03-26'],'series':[{'label':f,'valueKind':'number','role':'base','data':[contractmeans[f][c] for c in ['RTY 12-25','RTY 03-26']]} for f in ['MOM5','MOM15']]}
(r/'chart_spec.json').write_text(json.dumps(spec,ensure_ascii=False));(r/'output/audit_evidence.json').write_text(json.dumps({'independent_checks':checks,'contract_mean_ticks':contractmeans,'visual_plan':plan,'result_sha256':hashlib.sha256((r/'output/results.json').read_bytes()).hexdigest()},indent=2,ensure_ascii=False))
print(json.dumps({'checks':checks,'contract_mean_ticks':contractmeans},indent=2))
