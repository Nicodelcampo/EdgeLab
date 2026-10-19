from pathlib import Path
import argparse,json,hashlib,math,importlib.util
from collections import Counter,defaultdict
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

def helpers(repo):
    sp=importlib.util.spec_from_file_location('screen',repo/'tools/review_avzvol_indicator_screen.py')
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

def native_weights(d):
    keys=list(d[['session','contract','t0']].itertuples(index=False,name=None))
    rowcounts=Counter(keys);anchors=defaultdict(set);contracts=defaultdict(set)
    for day,ct,t0 in keys:anchors[day,ct].add(t0);contracts[day].add(ct)
    return np.array([1/(rowcounts[k]*len(anchors[k[:2]])*len(contracts[k[0]])) for k in keys])

def cutoff_ticks(height,level):
    return np.ceil(height*level-1e-12).astype(np.int64)

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--profile-only',action='store_true');a=p.parse_args();A=a.out;A.mkdir(parents=True,exist_ok=True)
    plan=json.loads(a.plan.read_text())
    for artifact in plan['prior_artifacts']:
        assert hashlib.sha256((a.repo/artifact['path']).read_bytes()).hexdigest()==artifact['sha256'],artifact['path']
    (A/'analysis-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    m=helpers(a.repo);frames=[];profiles=[]
    for pin in sorted(plan['pins'],key=lambda x:x['basename']):
        paths=list(a.input_dir.rglob(pin['basename']));assert len(paths)==1;f=paths[0]
        assert hashlib.sha256(f.read_bytes()).hexdigest()==pin['sha256']
        pf=pq.ParquetFile(f);assert pf.metadata.num_rows==pin['rows'];si=pf.schema_arrow.names.index('session')
        for rg in range(pf.metadata.num_row_groups):
            st=pf.metadata.row_group(rg).column(si).statistics;assert st is not None and st.has_min_max and st.max<20261001
        d=pq.read_table(f,columns=plan['columns']).to_pandas();assert d.notna().all().all()
        assert np.isfinite(d[['t0','te','pos','o2','amp','h','mx_h']].to_numpy()).all()
        if a.profile_only:d.to_csv(A/(pin['basename'].replace('.parquet','.projection.csv')),index=False)
        profiles.append({'basename':pin['basename'],'rows':len(d),'sha256':pin['sha256'],'nulls':0,'duplicate_identity_rows':int(d.duplicated(['contract','cell','kind','session','t0']).sum()),'min_session':int(d.session.min()),'max_session':int(d.session.max())});frames.append(d)
    (A/'native-profile.json').write_text(json.dumps({'files':profiles,'grain':'event x cell, not independent','duplicates':'retained and share anchor weight','generic_parquet_profiler':'unsupported parsing, not corruption; native profile + projected CSV profile'},indent=2))
    if a.profile_only:print('Profiled six exact pinned exports');return
    d=pd.concat(frames,ignore_index=True);assert len(d)==544531
    ledger=[]
    for cohort in ['real','pseudo']:
        z=d[d.kind.eq(cohort)&d.pos.eq(0)]
        ledger.append({'cohort':cohort,'inside_rows':len(z),'no_exit':int(z.te.lt(0).sum()),'unresolved_o2_after_exit':int((z.te.ge(0)&~z.o2.isin([0,1])).sum())})
    q=d[d.pos.eq(0)&d.te.ge(0)&d.o2.isin([0,1])].copy();assert (q.h>0).all() and (q.te>=q.t0).all() and (q.mx_h>=0).all()
    q['delay']=q.te-q.t0;q['range_band']=q.amp/q.h
    excursion=q.mx_h*q.h;assert np.allclose(excursion,np.rint(excursion),atol=1e-10,rtol=0)
    q['excursion_ticks']=np.rint(excursion).astype(np.int64)
    assert np.array_equal(q.excursion_ticks.ge(q.h),q.o2.eq(1))
    old=a.repo/'docs/research/avzvol_indicator_screen_20261011';prior=json.loads((old/'evidence.json').read_text());buckets=pd.read_csv(old/'test-bucket-metrics.csv')
    records=[];scenario=[];support=[];checks=[];contract_records=[]
    for fold in prior['folds']:
      for cohort in ['real','pseudo']:
        z=q[q.kind.eq(cohort)&q.session.between(fold['test_first'],fold['test_last'])].copy();w=m.weights(z);nw=native_weights(z);assert np.allclose(w,nw,atol=1e-12,rtol=0)
        ref=buckets[(buckets.feature=='delay_x_range_band')&(buckets.endpoint=='continuation')&(buckets.cohort==cohort)&(buckets.fold==fold['fold'])]
        edges=json.loads(ref.training_only_edges.iloc[0]);x=np.searchsorted(edges['exit_delay_bars'],z.delay,side='right');y=np.searchsorted(edges['range_over_band'],z.range_band,side='right');z['bucket']=np.char.add(np.char.add(x.astype(str),':'),y.astype(str))
        for bucket in ['ALL']+sorted(z.bucket.unique()):
          mask=np.ones(len(z),dtype=bool) if bucket=='ALL' else z.bucket.eq(bucket).to_numpy();mass=math.fsum(map(float,w[mask]));zz=z.loc[mask];ww=w[mask]
          sup={'fold':fold['fold'],'cohort':cohort,'bucket':bucket,'rows':len(zz),'anchor_keys':len(zz[['contract','session','t0']].drop_duplicates()),'sessions':int(zz.session.nunique()),'weight_mass':mass,'coverage':mass/math.fsum(map(float,w)),'training_edges':edges};support.append(sup)
          if bucket!='ALL':
            expected=ref[ref.bucket.eq(bucket)].iloc[0];actual=float(np.dot(ww,zz.o2)/mass);assert abs(actual-expected.weighted_label_rate)<1e-12 and len(zz)==expected.rows
          for unit,levels in [('h',plan['distance_thresholds_h']),('ticks',plan['absolute_distance_thresholds_ticks'])]:
            for level in levels:
              required=cutoff_ticks(zz.h.to_numpy(),level) if unit=='h' else np.full(len(zz),int(level));hit=zz.excursion_ticks.to_numpy()>=required
              rate=float(np.dot(ww,hit)/mass)
              if bucket in ['ALL','0:2','2:0']:
                numerator=math.fsum(float(weight) for exc,h,weight in zip(zz.excursion_ticks,zz.h,ww) if exc >= (math.ceil(h*level-1e-12) if unit=='h' else level));assert abs(numerator/mass-rate)<1e-12
              records.append({'fold':fold['fold'],'cohort':cohort,'bucket':bucket,'unit':unit,'distance':level,'reach_rate':rate,'rows':len(zz),'sessions':int(zz.session.nunique()),'coverage':sup['coverage']})
          for offset in plan['assumed_entry_offsets_h']:
            for target in plan['scenario_remaining_targets_h']:
              hit=zz.excursion_ticks.to_numpy()>=cutoff_ticks(zz.h.to_numpy(),offset+target)
              scenario.append({'fold':fold['fold'],'cohort':cohort,'bucket':bucket,'assumed_entry_offset_h':offset,'remaining_target_h':target,'optimistic_full_window_reach_upper_bound':float(np.dot(ww,hit)/mass),'actual_entry_win_rate':None,'rows':len(zz),'sessions':int(zz.session.nunique())})
        for ct in sorted(z.contract.unique()):
          cz=z[z.contract.eq(ct)].copy();cw=m.weights(cz)
          for bucket in ['ALL','0:2','2:0']:
            mask=np.ones(len(cz),dtype=bool) if bucket=='ALL' else cz.bucket.eq(bucket).to_numpy();mass=math.fsum(map(float,cw[mask]))
            for unit,levels in [('h',plan['distance_thresholds_h']),('ticks',plan['absolute_distance_thresholds_ticks'])]:
              for level in levels:
                hit=cz.loc[mask,'excursion_ticks'].to_numpy()>=(cutoff_ticks(cz.loc[mask,'h'].to_numpy(),level) if unit=='h' else level)
                contract_records.append({'fold':fold['fold'],'cohort':cohort,'contract':ct,'bucket':bucket,'unit':unit,'distance':level,'reach_rate':None if mass==0 else float(np.dot(cw[mask],hit)/mass),'rows':int(mask.sum()),'sessions':int(cz.loc[mask,'session'].nunique()),'anchor_keys':len(cz.loc[mask,['session','t0']].drop_duplicates())})
        checks.append({'fold':fold['fold'],'cohort':cohort,'weights_oracle_matches':True,'all_prior_bucket_rates_and_rows_reproduced':True})
    for name,rows in [('reach-by-fold.csv',records),('entry-offset-scenarios.csv',scenario),('context-support.json',support),('reach-by-contract.csv',contract_records)]:
      if name.endswith('.json'):(A/name).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
      else:pd.DataFrame(rows).to_csv(A/name,index=False)
    result=pd.DataFrame(records);summary=result.groupby(['cohort','bucket','unit','distance'],sort=False).agg(mean_rate=('reach_rate','mean'),min_fold_rate=('reach_rate','min'),max_fold_rate=('reach_rate','max'),folds=('fold','nunique')).reset_index();summary.to_csv(A/'reach-summary.csv',index=False)
    e={'scope':plan['scope'],'plan':plan,'prior_evidence_sha256':hashlib.sha256((old/'evidence.json').read_bytes()).hexdigest(),'ledger':ledger,'folds':prior['folds'],'support':support,'summaries':summary.to_dict(orient='records'),'checks':checks,'integer_excursion_reconstruction_verified':True,'one_h_reach_equals_existing_o2_verified':True,'independent_numerator_and_weights_verified':True,'operational_entry_target_or_profit_estimated':False,'new_price_outcomes_created':False,'return_path_or_peaks_measured':False,'blind_confirmation':False}
    (A/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2,allow_nan=False))
    print(summary[(summary.cohort=='real')&summary.bucket.isin(['ALL','0:2','2:0'])].to_string(index=False))
    print('0.25h target, optimistic offset scenarios in favorable context')
    s=pd.DataFrame(scenario);print(s[(s.cohort=='real')&s.bucket.eq('0:2')&s.remaining_target_h.eq(.25)][['fold','assumed_entry_offset_h','optimistic_full_window_reach_upper_bound']].to_string(index=False))
    return A
def render_outputs(folder):
    e=json.loads((folder/'evidence.json').read_text());s=pd.read_csv(folder/'reach-summary.csv');f=pd.read_csv(folder/'reach-by-fold.csv');c=pd.read_csv(folder/'reach-by-contract.csv');scenario=pd.read_csv(folder/'entry-offset-scenarios.csv')
    fixed=f[f.cohort.eq('real')&f.unit.eq('ticks')&f.bucket.isin(['ALL','0:2'])].pivot(index=['fold','distance'],columns='bucket',values='reach_rate')
    fixed['gap_pp']=(fixed['0:2']-fixed.ALL)*100;assert (fixed.gap_pp>0).all()
    all_contract=c[c.cohort.eq('real')&c.unit.eq('ticks')&c.bucket.isin(['ALL','0:2'])].groupby(['contract','bucket','distance']).reach_rate.mean().unstack('bucket');all_contract['gap_pp']=(all_contract['0:2']-all_contract.ALL)*100;assert (all_contract.gap_pp>0).all()
    def rate(cohort,bucket,unit,distance):return float(s[(s.cohort==cohort)&(s.bucket==bucket)&(s.unit==unit)&(s.distance==distance)].mean_rate.iloc[0])
    levels=e['plan']['absolute_distance_thresholds_ticks'];similarity=max(abs(rate('real','0:2','ticks',level)-rate('pseudo','0:2','ticks',level))*100 for level in levels);assert similarity<1
    offsets=scenario[scenario.cohort.eq('real')&scenario.bucket.eq('0:2')&scenario.remaining_target_h.eq(.25)].groupby('assumed_entry_offset_h').optimistic_full_window_reach_upper_bound.mean()
    assert offsets.loc[0]>offsets.loc[.25]>offsets.loc[.5]
    cover=[v['coverage'] for v in e['support'] if v['cohort']=='real' and v['bucket']=='0:2']
    e['claims']={'fixed_tick_context_gap_positive_every_fold_and_threshold':True,'fixed_tick_gap_positive_in_each_contract_mean':True,'max_filtered_real_vs_pseudo_gap_pp':similarity,'favorable_weighted_coverage_range':[min(cover),max(cover)],'quarter_h_target_optimistic_offsets':{str(k):float(v) for k,v in offsets.items()},'first_half_band_chase_bound_drop_pp':float((offsets.loc[0]-offsets.loc[.5])*100)}
    e['comparison_plan']=[{'question':'Is the normalized advantage also actual fixed-tick movement?','grain':'cohort x prior mechanism context x distance','population':'same resolved O2 forward-test exits; filter nested within all','unit':'observed excursion reach percent','derivation':'same weighted reach rates, mean of3block rates','finding':'Filtered fixed-tick reach exceeds all real exits across all4 thresholds and3blocks; filtered pseudo rates within1pp of real','disposition':'chart','reason':'Single ordered profile answers geometry vs movement and preserves controls; no stacked or summed nested groups'},
      {'question':'How stable across dates and contracts?','grain':'block and contract x fixed tick threshold','population':'same real test subsets; contract metrics equal session weights within contract','unit':'percentage-point gap vs all','finding':'All examined differences positive, variable strength; MNQ_12-26 low support','disposition':'table','reason':'Complete short period and contract lookup retains dispersion; no opposing sign hidden by pooling'},
      {'question':'What happens with a later assumed entry price?','grain':'block x hypothetical entry offset x fixed remaining target','population':'favorable resolved test exits','unit':'optimistic full-window reach upper bound percent','finding':'Bound for .25h remaining target drops sharply with larger assumed offset','disposition':'table','reason':'Only illustrative modeled bound, no actual entry time/price/fill/adverse move; full grid retained'},
      {'question':'Which triggers and peaks validate an entry?','grain':'real path after executable entry','population':'unavailable in this export','unit':'unavailable','finding':'No return path, as-of geometry certification, fills/costs or peak-confirmation data','disposition':'prose','reason':'Keep proposed hypotheses separate from observed excursion'}]
    series=[];colors={}
    for cohort,bucket,label,hue in [('real','0:2','Contexto favorable · real','blue'),('real','ALL','Todos los casos · real','purple'),('pseudo','0:2','Contexto favorable · control','teal'),('pseudo','ALL','Todos los casos · control','orange')]:
      series.append({'label':label,'valueKind':'percent','role':'subject' if not series else 'base','derived':True,'derivationReason':'Mean of3 block weighted observed-excursion reach rates, not trade wins','data':[rate(cohort,bucket,'ticks',v)*100 for v in levels]});colors[label]=hue
    spec={'version':1,'form':'multiline','title':'El contexto favorable mejora el alcance en ticks','aside':'Alcance observado desde el borde; media igual de3bloques, no ganancias','labels':[str(v)+' ticks' for v in levels],'axis':{'zero':True,'cap':100},'series':series,'colorMap':colors}
    (folder/'chart-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2));(folder/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2,allow_nan=False))
    text=['# AVZVOL: recorrido disponible y precio de entrada','','## Resultado para decidir','**Mantener como prioridad una continuación temprana y selectiva, sin perseguir el precio.** El contexto rápido/rango-amplio mejora también el alcance en ticks fijos: no es sólo un objetivo más fácil en alturas de banda. Pero no está validada una entrada rentable y el precio al que se logra entrar puede consumir la ventaja.','','## Recorrido desde el borde, no desde una operación','Misma población que la exploración anterior: ancla dentro, salida observada, O2 resuelto; tres bloques temporales internos ya inspeccionados. Rápida/amplia es el grupo 0:2 de los terciles aprendidos exclusivamente del pasado, reutilizados sin volver a ajustar. No es una nueva confirmación ni un filtro promovido.','La distancia es el máximo high/low observado desde el borde después de la barra de salida, hasta el primer cierre dentro o el fin acotado de ventana/sesión. Incluye el high/low de la barra que cierra dentro. No mide orden intrabar, fills, stops ni beneficio.','','| Distancia fija | Todos los reales | Contexto favorable real | Contexto favorable control |','|---|---:|---:|---:|']
    for level in levels:text.append(f"| {level} ticks | {rate('real','ALL','ticks',level)*100:.2f}% | {rate('real','0:2','ticks',level)*100:.2f}% | {rate('pseudo','0:2','ticks',level)*100:.2f}% |")
    text+=['','La mejora es positiva en los tres bloques para cada distancia fija. El contexto favorable de los controles da resultados muy parecidos: no atribuir el efecto a una propiedad especial de las zonas. Los controles legacy todavía no están certificados como zone-free.','',f"Cobertura ponderada del contexto favorable: {min(cover)*100:.2f}%–{max(cover)*100:.2f}% de la población elegible por bloque. No es porcentaje de trades que se podrían llenar.",'','## Distancias relativas a la banda','h = H-L+1 ticks. El contexto favorable no asegura un recorrido de una banda.','','| Máximo observado al menos | Todos los reales | Contexto favorable |','|---|---:|---:|']
    for level in e['plan']['distance_thresholds_h']:text.append(f"| {level:g}h | {rate('real','ALL','h',level)*100:.2f}% | {rate('real','0:2','h',level)*100:.2f}% |")
    text+=['','No elegir el objetivo de mayor porcentaje como “ganador”: reducir distancia naturalmente eleva alcance, pero no resuelve recorrido adverso ni costos. Por ejemplo, alcanzar 0,25h no equivale a ganar una entrada con target 0,25h.','','## Sensibilidad al precio supuesto de entrada','**Ejemplo hipotético, no objetivo recomendado:** pedir 0,25h adicional después de una entrada posterior a la barra de salida. Si el precio de esa entrada estuviera más lejos del borde, el máximo registrado tendría que llegar a offset +0,25h.','Se usa el máximo de toda la ventana, que puede haber ocurrido ANTES de la entrada hipotética: por eso es una **cota optimista de cobertura geométrica**, no probabilidad de fill ni win-rate. El denominador son TODOS los casos del contexto favorable, incluso los que no cubren el avance supuesto hasta la entrada. No condicionar esta cifra como si fueran operaciones efectivamente llenadas. Tampoco se sabe si un stop habría sido tocado antes. La barra de salida queda excluida: no aplicar esta cota a entradas intrabar en esa barra.','','| Precio supuesto de entrada más allá del borde | Fracción de todos los casos que cubre offset +0,25h |','|---|---:|']
    for offset in e['plan']['assumed_entry_offsets_h']:text.append(f"| {offset:g}h | {offsets.loc[offset]*100:.2f}% |")
    text+=['','El descenso orienta a estudiar el precio ejecutable y el retardo antes de sumar más indicadores. No certifica que una entrada cercana al borde sea posible ni que esperar un retest conserve el recorrido.','','## Variación temporal: ventaja de contexto sobre todos los reales','Brecha en puntos porcentuales de alcance, no retorno ni efecto causal.','','| Bloque | 5 ticks | 10 ticks | 20 ticks | 40 ticks |','|---|---:|---:|---:|---:|']
    for fold,g in fixed.groupby('fold'):text.append('| '+str(fold)+' | '+' | '.join(f"{g.loc[(fold,level),'gap_pp']:+.2f}" for level in levels)+' |')
    text+=['','## Variación entre contratos','Los dos contratos antiguos sólo aparecen en entrenamiento; cuatro tienen prueba. Promedios de los bloques soportados, ponderaciones de sesión dentro de contrato, no réplicas independientes del mercado MNQ. Se conservan todas las filas/celdas, no sólo contratos favorables.','','| Contrato | Sesiones favorables / anclas | Brecha a20 ticks |','|---|---|---:|']
    for ct in sorted(c.contract.unique()):
      support=c[c.cohort.eq('real')&c.contract.eq(ct)&c.bucket.eq('0:2')&c.unit.eq('ticks')&c.distance.eq(20)]
      text.append(f"| {ct} | {int(support.sessions.sum())} / {int(support.anchor_keys.sum())} | {all_contract.loc[(ct,20),'gap_pp']:+.2f} pp |")
    text+=['','MNQ_12-26 tiene sólo10 sesiones de prueba total en el estudio anterior: soporte pequeño, no una confirmación independiente. CSV completo retiene denominadores y todos los cortes.','','## Lógicas concretas a contrastar, todavía hipótesis','1. **Ruptura con entrada posterior ejecutable y distancia limitada al borde:** contexto rápido/amplio conocido al finalizar la salida; medir el primer precio realmente ejecutable, no asumir compra/venta retrospectiva en el borde.','2. **Retest que evita perseguir:** distinguir retest superficial con compresión y rechazo fuera, retest agresivo, y recuperación del interior. No asumir que el mismo filtro anticipa el lado del rebote: las26 pruebas anteriores no mejoraron en promedio O3b.','3. **Vuelta y picos causales:** cadenas confirmadas, máximos decrecientes/mínimos crecientes, velocidad real de vuelta/salida y precio de confirmación; no usar un pico en su índice original antes de i+R ni un segmento final backfilled como señal al nacer.','4. **Comparación decisiva pendiente:** mismo trigger y regla de gestión, con/sin contexto, desde fills posibles y neto de costos, después de las autorizaciones y requisitos de fuente/método correspondientes. Este estudio no realiza esa comparación económica.','5. **Prioridad:** primero precio y retardo de entrada, luego estructura del retest; no añadir nuevos indicadores por acumularlos.','','## Método, límites y reproducción','Seis exports con hash exacto, 544.531 filas evento×celda; no lecturas de ticks, reserva ciega ni nuevos desenlaces de precios. Sólo se agregan etiquetas de excursión existentes. Duplicados retenidos compartiendo peso por ancla.','Se reproducen todas las tasas O2 y tamaños de los nueve grupos publicados anteriormente; 1h reconstruido en ticks reproduce exactamente O2. Pesos contrastados con un contador independiente y numeradores con math.fsum. La reconstrucción mx_h ×h es entera a tolerancia numérica.','Media igual de tres tasas de bloque, no tasa pooled de filas. Los contratos usan pesos propios por sesión, no se suman como eventos independientes. Cada alcance usa el peso original restringido al grupo; no se reigualan sólo sus sesiones sobrevivientes.','O2 no resuelto excluido sólo para reproducir la población anterior y contado aparte. mx_h puede terminar por límite de ventana/sesión sin una vuelta completa; representa máximo OBSERVADO acotado, no trayectoria futura completa. No hay p-valores, significancia ni selección del mejor objetivo.','La fuente y geometría as-of siguen sin certificar, y no se despejan gates. Ausencia de timestamps/precio de entrada/trayectoria impide medir velocidad real de vuelta, picos y excursión adversa después del fill.','Profilado genérico de los Parquets no soportó su formato (ParserError): hashes/footers/perfil nativo y proyecciones CSV confirmados. La única advertencia CSV, contrato constante por archivo, es esperada. El cálculo canónico usa directamente Parquet, no las proyecciones.','','```bash','python tools/review_avzvol_entry_distance.py --repo . --input-dir /ruta/privada/exports --out /ruta/salida --plan docs/research/avzvol_entry_distance_20261011/analysis-plan.json','```','','[Plan](avzvol_entry_distance_20261011/analysis-plan.json) · [Evidencia](avzvol_entry_distance_20261011/evidence.json) · [Alcance completo](avzvol_entry_distance_20261011/reach-summary.csv) · [Por bloque](avzvol_entry_distance_20261011/reach-by-fold.csv) · [Por contrato](avzvol_entry_distance_20261011/reach-by-contract.csv) · [Todos los escenarios](avzvol_entry_distance_20261011/entry-offset-scenarios.csv) · [Estudio anterior](AVZVOL_INDICADORES_SALIDA_Y_ENTRADAS_20261011.md)']
    (folder/'report.md').write_text('\n'.join(text)+'\n')

if __name__=='__main__':
    folder=main()
    if folder is not None:render_outputs(folder)
