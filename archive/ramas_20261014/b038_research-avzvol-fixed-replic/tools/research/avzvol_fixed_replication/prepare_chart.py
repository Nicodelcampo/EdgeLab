import json
from pathlib import Path
P=Path('/data/analysis/avzvol-replication');a=json.loads((P/'analysis-evidence.json').read_text());rows=a['primary'];contracts=['MNQ_12-26','MNQ_09-25'];origins=[('real_racimo','Racimo real','subject'),('clock_price_width10','Precio, ancho 10','base'),('clock_price_width20','Precio, ancho 20','base')]
series=[]
for origin,label,role in origins:
 r=[next(x for x in rows if x['contract']==c and x['origin']==origin) for c in contracts]
 for x in r:assert abs(x['target_percent']-100*x['target_first']/x['resolved'])<1e-12
 series.append(dict(label=label,valueKind='percent',role=role,data=[x['target_percent'] for x in r],derived=True,derivationReason='Wins divided by resolved signals at the fixed primary rule, times100'))
spec=dict(version=1,form='categorical-bars',mode='grouped',title='El efecto inicial no se reproduce en el otro contrato',aside='Toque primero entre resultados resueltos de 10 y 29 sesiones seleccionadas',labels=['MNQ 12-26, inicial','MNQ 09-25, réplica'],axis={'zero':True,'cap':100},series=series,colorMap={'Racimo real':'blue','Precio, ancho 10':'orange','Precio, ancho 20':'purple'})
evidence=dict(grain='contract and origin',population='fixed D40/q50/touch/first-D-qualifying/corridor<25%/one first trigger per6250record bin',unit='percent among resolved',finding='54.6% on discovery source does not reproduce on another contract; clock price references remain near50',disposition='chart',reason='compares fixed replication without selecting new best parameters',rows=rows,omissions='delayed translated control and price point kept in report/table; point has109/127resolved and wide uncertainty',not_claimed='randomized causal effect, independent-event count, sealed holdout or profitability')
(P/'chart-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n');(P/'chart-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print('Chart arithmetic checked from independent-count-verified summary')
