"""Inventario E0 exclusivamente target-free: pie parquet + calendarios.

No lee columnas ni calcula señales, operaciones o P&L. No certifica captura,
noticias completas/point-in-time ni elegibilidad para ningún runner.
El output es privado: no distribuir datos fuera de Kaggle sin revisar licencia.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import pyarrow.parquet as pq
from edgelab.data.liquid_release import release_reader as RR

DESDE, HASTA = 20250805, 20260331
MANIFEST_SHA = 'db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5'
CAL_SHA = '9d8c318f84046844987dce247d6b67c2198771d6c00325157ea52605bfd92d86'
NEWS_SHA = '8a152d092314c42498638cbee2144cef0851b013a8536ed0b661c3fdb8381234'
CALENDAR = Path('docs/research/cme_equity_index_calendar_20260902/cme_equity_index_session_calendar_v1.json')
NEWS = Path('config/noticias/calendario_usd_tier1.csv')
ET = ZoneInfo('America/New_York')


def ymd(d):
    return d.year * 10000 + d.month * 100 + d.day


def parse_ymd(x):
    return datetime.strptime(str(int(x)), '%Y%m%d').date()


def resumir(calendario, observadas, noticias, start, end):
    """Cruce por fecha sin información de precios. `noticias` son UTC conscientes.

    Para eventos entre 09:29 y 15:56 inclusive hay intersección de ventana
    ±1 minuto con [09:30, 15:55] ET. Esto describe presencia en la sesión
    completa; NO decide si una señal específica se prohíbe.
    """
    if start > end or end >= RR.HOLDOUT_FIRST_TRADE_DATE:
        raise ValueError('rango inválido o reservado')
    inicio, fin = parse_ymd(start), parse_ymd(end)
    por_fecha = {}
    for x in calendario:
        d=int(x['trade_date']); parse_ymd(d)
        if d in por_fecha: raise ValueError('fecha de calendario duplicada')
        clase=x['session_class']
        if clase not in ('NORMAL','EARLY_CLOSE','CLOSED'): raise ValueError('clase desconocida')
        por_fecha[d]=clase
    fechas=[]; cur=inicio
    while cur<=fin:
        fechas.append(ymd(cur)); cur+=timedelta(days=1)
    faltan_calendario=[x for x in fechas if x not in por_fecha]
    if faltan_calendario:
        raise ValueError('calendario no cubre cada fecha del rango')
    obs=set(int(x) for x in observadas)
    if any(x < start or x > end for x in obs): raise ValueError('fecha observada fuera del rango')
    grupos={k:sorted(x for x in obs if por_fecha[x]==k) for k in ('NORMAL','EARLY_CLOSE','CLOSED')}
    sin_dato={k:sorted(x for x in fechas if por_fecha[x]==k and x not in obs) for k in ('NORMAL','EARLY_CLOSE','CLOSED')}
    por_noticia=set()
    for ts in noticias:
        if ts.tzinfo is None or ts.utcoffset() is None: raise ValueError('noticia sin zona horaria')
        local=ts.astimezone(ET); dia=ymd(local.date())
        minutes=local.hour*60+local.minute
        if start<=dia<=end and 569<=minutes<=956:
            por_noticia.add(dia)
    return dict(desde=start,hasta=end,observadas_por_clase=grupos,
                sin_grupo_por_clase=sin_dato,
                fechas_obs_con_noticia_listada=sorted(obs & por_noticia),
                fechas_obs_sin_noticia_listada=sorted(obs - por_noticia),
                advertencia=('Sólo footer y calendario retrospectivo parcial: no demuestra '
                             'captura íntegra, ausencia de noticias ni elegibilidad.'))


def cargar_eventos(path):
    with open(path,encoding='utf-8',newline='') as f:
        r=csv.DictReader(f)
        if r.fieldnames != ['ts_utc','evento','fuente_url','impacto']: raise ValueError('columnas de noticias inválidas')
        out=[]
        for row in r:
            if row['impacto'] not in ('tier1','tier2') or not row['fuente_url']:
                raise ValueError('noticia inválida')
            out.append(datetime.strptime(row['ts_utc'],'%Y-%m-%dT%H:%MZ').replace(tzinfo=ZoneInfo('UTC')))
    return out


def run(root, code_commit):
    if RR.sha256_file(root/'release_manifest.json') != MANIFEST_SHA: raise RR.ReleaseStop('manifiesto distinto')
    if RR.sha256_file(CALENDAR) != CAL_SHA or RR.sha256_file(NEWS) != NEWS_SHA: raise RR.ReleaseStop('calendario distinto')
    cal=json.loads(CALENDAR.read_text(encoding='utf-8'))
    if cal.get('schema_version') != 'cme_equity_index_session_calendar_v1': raise RR.ReleaseStop('esquema calendario distinto')
    base={k:v for k,v in cal.items() if k!='calendar_sha256'}
    h=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    if h != cal.get('calendar_sha256'): raise RR.ReleaseStop('hash canónico calendario distinto')
    files=RR.load_manifest(root,verify_hash=True,purpose='research')
    pf=pq.ParquetFile(files['NQ'].path)
    selected=RR.select_row_groups(pf,DESDE,HASTA)
    ci=pf.schema_arrow.names.index('trade_date'); dates=set()
    for g in selected:
        stats=pf.metadata.row_group(g).column(ci).statistics
        if int(stats.min)!=int(stats.max): raise RR.ReleaseStop('row group mezcla sesiones')
        dates.add(int(stats.min))
    result=resumir(cal['sessions'],dates,cargar_eventos(NEWS),DESDE,HASTA)
    return dict(estado='DIAGNOSTICO_TARGET_FREE_NO_ELEGIBILIDAD',code_commit=code_commit,
                manifest_sha256=MANIFEST_SHA,nq_sha256=files['NQ'].sha256,
                calendario_sha256=CAL_SHA,noticias_sha256=NEWS_SHA,row_groups=len(selected),**result)

if __name__ == '__main__':
    result=run(Path(os.environ['RELEASE_DIR']),os.environ['CODE_COMMIT'])
    Path('E0_ORB_NQ_UNIVERSO_PRIVADO.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DIAGNOSTICO_COMPLETO_NO_ELEGIBILIDAD: salida privada guardada',flush=True)
