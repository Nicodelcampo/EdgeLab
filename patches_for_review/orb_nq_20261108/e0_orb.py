"""E0 preliminar ORB NQ: sólo conteos y cortes target-free, nunca resultados.

Ejecutar dentro del kernel autocontenido armado a partir de los archivos versionados.
No calcula SL, TP, retornos, fills, P&L ni accede al holdout. El E0 es preliminar
hasta resolver el universo elegible (noticias, sesiones y calendario).
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from edgelab.data.liquid_release import release_reader as RR
from senales_orb import disparos

DESDE, HASTA = 20250805, 20260331
MANIFEST_SHA = 'db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5'


def resumen_sesion(b):
    """Transformación determinista de ticks en M1 y señales, sin outcomes."""
    if b.empty:
        return pd.DataFrame()
    b = b.sort_values('ts_utc_ns', kind='stable')
    if b.trade_date.nunique() != 1:
        raise ValueError('bloque no corresponde a una sola sesión')
    if (b.ts_utc_ns >= RR.HOLDOUT_FIRST_TS_NS).any() or (b.trade_date >= RR.HOLDOUT_FIRST_TRADE_DATE).any():
        raise ValueError('frontera holdout')
    b = b.loc[~b.outside_regular].copy()
    if b.empty:
        return pd.DataFrame()
    if (b.price_ticks <= 0).any() or b[['price_ticks', 'ts_utc_ns', 'regime_id']].isna().any().any():
        raise ValueError('precio, timestamp o segmento inválido')
    b['t'] = (b.ts_utc_ns // 60_000_000_000 + 1) * 60
    g = b.groupby('t', sort=True, observed=True)
    if (g.regime_id.nunique(dropna=False) != 1).any():
        raise ValueError('un minuto contiene dos segmentos')
    m = g.agg(h=('price_ticks', 'max'), l=('price_ticks', 'min'), c=('price_ticks', 'last'),
              ses=('trade_date', 'first'), seg=('regime_id', 'first')).reset_index()
    return disparos(dict(t=m.t.to_numpy(np.int64), h=m.h.to_numpy(float)*.25,
                         l=m.l.to_numpy(float)*.25, c=m.c.to_numpy(float)*.25,
                         ses=m.ses.to_numpy(np.int64), seg=m.seg.to_numpy(np.int64)))


def run(root: Path, code_commit: str):
    manifest = root / 'release_manifest.json'
    if RR.sha256_file(manifest) != MANIFEST_SHA:
        raise RR.ReleaseStop('el manifiesto no es el aprobado y fijado')
    files = RR.load_manifest(root, verify_hash=True, purpose='research')
    pf = pq.ParquetFile(files['NQ'].path)
    grupos = RR.select_row_groups(pf, DESDE, HASTA)
    ci = pf.schema_arrow.names.index('trade_date'); sesiones = {}
    for g in grupos:
        stats = pf.metadata.row_group(g).column(ci).statistics
        lo, hi = int(stats.min), int(stats.max)
        if lo != hi:
            raise RR.ReleaseStop(f'row group {g} mezcla sesiones; no se reconstruye por suposición')
        sesiones.setdefault(lo, []).append(g)
    cols = ['ts_utc_ns','price_ticks','trade_date','regime_id','outside_regular']
    filas = []
    for fecha, gs in sorted(sesiones.items()):
        b = pf.read_row_groups(gs, columns=cols).to_pandas()
        if len(b) and (b.trade_date != fecha).any():
            raise RR.ReleaseStop('payload contradice footer de trade_date')
        d = resumen_sesion(b)
        if len(d): filas.append(d)
    d = pd.concat(filas, ignore_index=True) if filas else pd.DataFrame(columns=['ses','duracion','dia','hora','atr14'])
    valid = d.atr14[np.isfinite(d.atr14)].to_numpy(float)
    cuts = [float(x) for x in np.quantile(valid, [1/3, 2/3])] if len(valid) else []
    if len(cuts) != 2 or not cuts[0] < cuts[1]:
        raise ValueError('ATR sin cortes válidos no degenerados')
    counts = d.groupby(['duracion','dia','hora'], dropna=False).size().reset_index(name='n')
    return dict(estado='E0_PRELIMINAR_NO_CONGELAR', code_commit=code_commit,
                manifest_sha256=MANIFEST_SHA, nq_sha256=files['NQ'].sha256,
                desde=DESDE, hasta=HASTA, grupos=len(grupos), sesiones_disponibles=len(sesiones),
                sesiones_con_senal=int(d.ses.nunique()), senales=int(len(d)),
                atr_finitos=int(len(valid)), atr_cortes_preliminares=cuts,
                conteos=counts.to_dict(orient='records'),
                limitacion='Sin filtro de elegibilidad de noticias ni verificación de calendario completo; no congelar cortes ni inferir rentabilidad.')


if __name__ == '__main__':
    root = Path(os.environ['RELEASE_DIR'])
    result = run(root, os.environ['CODE_COMMIT'])
    Path('E0_ORB_NQ_PRELIMINAR.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'conteos'}, ensure_ascii=False), flush=True)
