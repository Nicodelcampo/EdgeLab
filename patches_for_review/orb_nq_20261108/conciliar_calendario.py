"""Diagnóstico target-free de D-1. NO certifica elegibilidad ni reelige contratos.

Entrada: calendario CME reconstruido y registros de selección, no ticks.
El calendario debe contener cada día civil y una sesión anterior al inicio.
Salida sensible: mantener privada salvo licencia y autorización verificadas.
"""
from collections import Counter
from datetime import datetime, timedelta

CLASES = {'NORMAL', 'EARLY_CLOSE', 'CLOSED'}


def _fecha(x):
    return datetime.strptime(str(int(x)), '%Y%m%d').date()


def conciliar(calendario, registros, desde, hasta):
    inicio, fin = _fecha(desde), _fecha(hasta)
    if inicio > fin or hasta >= 20261001:
        raise ValueError('rango inválido o holdout')
    cal = {}
    for r in calendario:
        d = _fecha(r['trade_date'])
        if d in cal or r['session_class'] not in CLASES:
            raise ValueError('calendario duplicado o clase inválida')
        cal[d] = r['session_class']
    if (not cal or min(cal) >= inicio or max(cal) < fin
            or not any(d < inicio and clase != 'CLOSED' for d, clase in cal.items())):
        raise ValueError('calendario sin sesión previa o incompleto')
    x = min(cal)
    while x <= fin:
        if x not in cal:
            raise ValueError('calendario con fecha civil ausente')
        x += timedelta(days=1)
    reg = {}
    for r in registros:
        d = _fecha(r['trade_date'])
        if not inicio <= d <= fin:
            raise ValueError('registro fuera del intervalo')
        if d in reg:
            raise ValueError('registro de sesión duplicado')
        reg[d] = r
    prev = None
    rows = []
    for d in sorted(k for k in cal if k <= fin):
        kind = cal[d]
        if inicio <= d <= fin:
            r = reg.get(d)
            prev_reg = None if r is None or r.get('prev_trade_date') is None else _fecha(r['prev_trade_date'])
            if kind == 'CLOSED':
                estado = 'CERRADO_CON_REGISTRO' if r else 'CERRADO_SIN_REGISTRO'
            elif prev is None:
                estado = 'ANTERIOR_OFICIAL_DESCONOCIDO'
            elif r is None:
                estado = 'SESION_SIN_REGISTRO'
            elif prev_reg is None:
                estado = 'ANTERIOR_REGISTRO_DESCONOCIDO'
            elif prev_reg != prev:
                estado = 'ANTERIOR_DIFIERE'
            else:
                estado = 'ANTERIOR_COINCIDE'
            fmt = lambda q: int(q.strftime('%Y%m%d')) if q else None
            rows.append({'trade_date':fmt(d), 'clase_cme':kind, 'revision':estado,
                         'prev_cme':fmt(prev), 'prev_release':fmt(prev_reg),
                         'estado_release':None if r is None else r.get('status')})
        if kind != 'CLOSED':
            prev = d
    return {'estado':'DIAGNOSTICO_NO_ELEGIBILIDAD', 'desde':desde, 'hasta':hasta,
            'conteo_revision':dict(sorted(Counter(r['revision'] for r in rows).items())),
            'filas':rows,
            'limite':'Coincidencia no certifica calendario ex ante, selección, captura, noticias ni elegibilidad.'}
