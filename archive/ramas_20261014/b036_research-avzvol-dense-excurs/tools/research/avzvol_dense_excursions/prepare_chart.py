import json,csv,math
from pathlib import Path
P=Path('/data/analysis/avzvol-expansion');rows=[]
with (P/'corridor-sensitivity-summary.csv').open() as f:
 for r in csv.DictReader(f):
  if (r['family'],r['D'],r['bin_records'],r['corridor_threshold'],r['segment'])==('P80_W5_R8_1000_20','40','6250','0.25','all10'):rows.append(r)
assert len(rows)==6
for r in rows:assert abs(float(r['target_percent'])-100*int(r['target_first'])/int(r['resolved']))<1e-12
q=[.25,.5,.75];series=[]
for origin,label,role in [('real','Racimo real','subject'),('delayed_translated_250bars','Control trasladado','base')]:
 a=[next(r for r in rows if r['origin']==origin and float(r['q'])==v) for v in q];series.append(dict(label=label,valueKind='percent',role=role,data=[float(r['target_percent']) for r in a],derived=True,derivationReason='Target-first divided by resolved, times100; same rule and temporal sampling'))
spec=dict(version=1,form='categorical-bars',mode='grouped',title='La señal de retorno aparece en una vuelta del 50%, no en todas',aside='Probabilidad observada de tocar antes la barrera contraria en 10 sesiones',labels=['Vuelta 25%','Vuelta 50%','Vuelta 75%'],axis={'zero':True,'cap':100},series=series,colorMap={'Racimo real':'blue','Control trasladado':'orange'})
plan=dict(grain='retracement threshold',population='MNQ12-26 ten selected dates; P80/W5 racimo8/1000/20; minimum excursion40 ticks; first-D-qualifying; corridor occupancy<25%; one earliest trigger per6250record bin',unit='percent among resolved signals',finding='Peak at q50 for real racimos weakens at neighboring retracement thresholds; control benefit remains uncertain',disposition='chart',reason='preserves post-discovery nonrobustness instead of plotting only selected optimum',coverage='all six real/control cells, sample counts in response',multiplicity='post-discovery, not adjusted')
(P/'chart-evidence.json').write_text(json.dumps({'plan':plan,'rows':rows},indent=2)+'\n');(P/'corridor-chart-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n');print('Chart six-cell arithmetic verified')
