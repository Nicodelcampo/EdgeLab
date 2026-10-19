import json,hashlib
from pathlib import Path
import pandas as pd
P=Path('/data/analysis/avzvol-replication-rest');C=P/'combined';a=json.loads((C/'analysis-evidence.json').read_text());e=json.loads((C/'evidence.json').read_text());m=json.loads((C/'manifest.json').read_text());v=json.loads((C/'independent-primary-check.json').read_text());s=pd.DataFrame(a['primary']);co=pd.DataFrame(a['primary_contrasts']);order=m['contracts'];real=s[s.origin.eq('real_racimo')].set_index('contract').loc[order].reset_index();assert len(v['checks'])==30 and e['rule_groups']==270 and len(e['reference_checks'])==270
# Every displayed number comes from reconciled counts/analysis, not hand transcription.
rows=[]
for r in real.to_dict('records'):
 rows.append(f"| {r['contract'].replace('_',' ')} | {r['target_first']}/{r['resolved']} | {r['target_percent']:.2f}% | {r['day_lower']:.2f}–{r['day_upper']:.2f}% | {r['unresolved']} | {r['active_dates']}/{r['observed_dates']} |")
primary_table='| Contrato | Racimo primero / resueltos | Tasa | IC por sesiones, 95% | No resueltos | Sesiones activas / observadas |\n| --- | ---: | ---: | ---: | ---: | ---: |\n'+'\n'.join(rows)
control_rows=[]
for c in order:
 x=s[s.contract.eq(c)].set_index('origin');control_rows.append('| '+c.replace('_',' ')+' | '+' | '.join(f"{x.loc[o,'target_percent']:.2f}% ({int(x.loc[o,'resolved'])})" for o in m['origins'])+' |')
controls='| Contrato | Racimo | Traslado +250 | Precio ancho 1 | Precio ancho 10 | Precio ancho 20 |\n| --- | ---: | ---: | ---: | ---: | ---: |\n'+'\n'.join(control_rows)
failed=[c for c,p in a['contract_pass'].items() if not p];passed=[c for c,p in a['contract_pass'].items() if p]
headline=f"La regla fija cumple todos los criterios en {len(passed)} de los cinco contratos distintos del descubrimiento; no constituye una ventaja validada." if not passed else f"La regla fija cumple todos los criterios en {len(passed)} de cinco contratos; la heterogeneidad y multiplicidad requieren cautela."
a['finding']=headline;a['primary_table_markdown']=primary_table;a['control_table_markdown']=controls;a['all_six_complete']=True;a['new_contracts_this_extension']=e['new_contracts'];a['independent_primary_cells']=30;a['long_lived_zone_extension']='protocol recorded; not evaluated';a['comparison_plan']=[dict(grain='contract × origin',population='fixedD40/q50/touch/first-D-qualified/corridor<25%/bin6250 selected-date resolved signals',unit='target-first percent',finding=headline,derivation='target_first/resolved*100',disposition='chart',reason='complete six-contract comparison; real and fixed-width10/20 references'),dict(grain='contract',population='same primary with all five origins',unit='counts and uncertainty',finding='finite followup and frequency accompany every rate',derivation='reconciled numerator denominator',disposition='table',reason='retain denominators, censoring and omitted width1/delayed references'),dict(grain='zone age and prior revisits',population='new user hypothesis, no computed labels yet',unit='unmeasured',finding='planned causal landmark study, not a discovered effect',derivation=None,disposition='prose',reason='separate proposed experiment from measured replication')]
(C/'analysis-evidence.json').write_text(json.dumps(a,indent=2,allow_nan=False)+'\n')
series=[]
for origin,label,role in [('real_racimo','Racimo','subject'),('clock_price_width10','Precio: ancho 10','base'),('clock_price_width20','Precio: ancho 20','base')]:
 data=[]
 for c in order:
  r=s[s.contract.eq(c)&s.origin.eq(origin)].iloc[0];assert abs(r.target_percent-100*r.target_first/r.resolved)<1e-12;data.append(float(r.target_percent))
 series.append(dict(label=label,valueKind='percent',role=role,data=data))
spec=dict(version=1,form='categorical-bars',mode='grouped',title='La señal inicial no basta para validar el retorno al racimo',aside='Misma regla en seis contratos; tasas entre señales resueltas. MNQ12-26 es el descubrimiento, no una réplica nueva. Referencias no emparejadas exactamente en geometría.',labels=[c.replace('_',' ') for c in order],axis=dict(zero=True,cap=100),series=series);(C/'chart-spec.json').write_text(json.dumps(spec,indent=2)+'\n')
notes=dict(generic_profiler={'MNQ_03-26':'exit137','MNQ_12-25':'exit137','MNQ_06-26':'MemoryError','MNQ_09-26':'MemoryError'},interpretation='generic profiler resource failure, not a detected dataset defect',mitigation='no retries; Parquet-native SHA/bytes/footer and bounded streamed ordered source counts; all main campaign subprocesses completed successfully',bounded_csr_exact_parity_cases=45,source_mutated=False,raw_ticks_or_event_level_signals_published=False);(C/'attempt-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
report=f'''# AVZVOL: réplica fija en seis contratos

## Conclusión
{headline}

Parámetros congelados: P80, window bars5, racimo mínimo8, ventana1000, altura20 ticks; excursión mínima40ticks, regreso50%, tocar borde, primera salida que alcanza D, corredor ocupado por menos del25% de hasta256 barras cerradas y selección temporal6250registros. No se modificaron después de observar los nuevos contratos. El50% es una referencia descriptiva de barreras simétricas, no un nulo causal garantizado.

## Regla primaria
{primary_table}

## Las cinco referencias completas
Porcentaje de objetivo primero; entre paréntesis, resueltos. Orígenes distintos tienen poblaciones de señales distintas; no sumar sus observaciones.

{controls}

## Alcance y verificación
- Seis contratos y {sum(len(d) for d in m['event_dates'].values())} fechas seleccionadas. Los dos primeros contratos de PR114 reutilizan etiquetas; esta extensión añade cuatro contratos, no recontabiliza el descubrimiento como prueba independiente.
- {e['rule_groups']} grupos de mercado, {a['thinned_groups']} resúmenes con sensibilidades y {a['control_contrasts']} contrastes. Son análisis superpuestos, no tamaños muestrales independientes.
- {len(e['reference_checks'])} estratos comparados exactamente con una implementación Python de referencia, y30celdas primarias verificadas mediante ordenación estable/groupby independiente.
- Fuente exacta fijada por SHA256/tamaño/filas. Conteos del catálogo contrastados contra sesiones crudas completas. Cualquier observación seleccionada fuera del intervalo de lectura debe ser mantenimiento declarado; fallar de forma cerrada ante cualquier otra discrepancia.
- Solo fechas seleccionadas producen eventos. Warmup declarado anterior alimenta calibración, no señales. Hora16 excluida solo de derivados. Cero fugas observadas de alcance; originales intactos.
- CSR escrito por bloques de barras completas:45casos de igualdad exacta frente al constructor original. No cambia detector ni etiquetas. Borrado únicamente de cachés binarias derivadas después de validación, nunca de fuentes.

## Riesgos que siguen abiertos
1. Exploración previa y pruebas múltiples: CIs puntuales por20.000remuestreos de sesiones completas, sin corrección FWER. No es holdout virgen ni certificación de fuente.
2. Las referencias de precio tienen anchos centrados fijos y no están emparejadas exactamente en geometría/contexto con racimos reales; traslado250 es un control descriptivo, no intervención aleatoria.
3. El adelgazamiento reduce solapamiento, pero no asegura independencia entre zonas o sesiones. Parámetros vecinos D20/80,q25/75 y bin25000 son sensibilidades; no seleccionar el mejor como validación.
4. No resueltos por fin de sesión, horizonte o huecos publicados junto a cada tasa y bandas de censura. No descartar para simular operaciones ganadoras.
5. Hasta256barras previas cerradas, excluida la barra de activación. Sensibilidad full256 separada; nunca incluir información posterior en atributos.
6. El profiler genérico falló por recursos; esto no es un error del dataset. La auditoría Parquet nativa y todas las corridas principales completaron sus controles.
7. Las reglas históricas del catálogo incluyen elementos retrospectivos; seleccionar estas fechas no acredita selección ejecutable as-of. El warmup no produce eventos pero puede influir en calibración: la sensibilidad específica al salto1419ticks no seleccionado de MNQ09-26 sigue pendiente, sin tratarlo como corrupción ni borrarlo para mejorar resultados.
8. No se simulan comisiones, spread, ejecución o P&L. No invertir automáticamente una regla por un resultado negativo.

## Nueva hipótesis: zonas de2000–3000barras
Protocolo separado en `AVZVOL_LONG_LIVED_ZONES_PROTOCOL.md`. Antigüedad, ventana de detección y revisitas son conceptos distintos. La extensión está planificada, todavía no medida; no presentar esta idea como hallazgo.

## Evidencia reproducible
Agregados, manifiesto y código en `research/avzvol-six-contract-replication/`. Fuentes y señales tick-a-tick no se publican. Código snapshot con rutas locales explícitas y dependencias de los PR112/113/114; no es un runner portable ni un motor NT8 certificado. PR apilado sobre PR114, sin merge ni promoción automática.
'''
(C/'REPORT.md').write_text(report)
files=[];base='research/avzvol-six-contract-replication/'
for name in ['manifest.json','evidence.json','analysis-evidence.json','independent-primary-check.json','attempt-notes.json','replication-criteria.json','rule-counts.csv','thinned-summary.csv','paired-contrasts.csv','full-history-sensitivity.csv','chart-spec.json']:
 files.append(dict(path=base+name,content=(C/name).read_text()))
for name in ['run_replication.py','bounded_csr.py','check_contract.py','orchestrate.py','analyze_all.py','combine.py','package_all.py','bounded-csr-check.json']:
 files.append(dict(path=base+name,content=(P/name).read_text()))
files.extend([dict(path='docs/research/AVZVOL_SIX_CONTRACT_FIXED_REPLICATION.md',content=report),dict(path='docs/research/AVZVOL_LONG_LIVED_ZONES_PROTOCOL.md',content=(P/'LONG_LIVED_ZONES_PROTOCOL.md').read_text())]);payload=dict(owner='Nicodelcampo',repo='EdgeLab',branch='research/avzvol-six-contract-replication',message='research: complete fixed six-contract AVZVOL replication without retuning',files=files);(P/'push.json').write_text(json.dumps(payload,ensure_ascii=False));assert (P/'push.json').stat().st_size<1048576
print('PACKAGE',len(files),'files',(P/'push.json').stat().st_size,'bytes');print('FINDING',headline);print(primary_table)
