"""Persistencia del rendimiento de las celdas de una grilla (2026-10-26): la condición necesaria de una «canasta de estrategias de
régimen» (tesis de Nico: el valor de EdgeLab estaría en renovar, ponderar, retirar y sumar estrategias rápido).

Una canasta que rota hacia lo que viene funcionando gana sólo si el rendimiento reciente de una celda predice el siguiente. Esto lo
mide sin elegir ninguna celda: arma la matriz celda × mes del P&L neto (todas las celdas de la grilla, costos canónicos ya aplicados) y
calcula, para cada horizonte declarado:
  - `persistencia`: correlación de rangos (Spearman) entre el rendimiento de cada celda en una ventana de formación y en la ventana
    siguiente, y el diferencial del decil superior de formación contra el promedio en la ventana de prueba; una fila por ventana
    (ventanas de prueba sin solapamiento: la unidad de inferencia es la ventana, no la celda, porque las celdas están correlacionadas);
  - `meta_regla`: la canasta como UNA regla: cada mes las k celdas con mejor formación (con un mínimo de operaciones) se operan el mes
    siguiente; serie mensual del P&L neto por operación.
Pre-registro: docs/research/canasta_regimen_20261026/PREREGISTRO_PERSISTENCIA.md. Etapa `PERSIST` de `etapas.ejecutar`.
Ya existía `g2_ratio.walk_forward_ratio` (un ganador por pliegue entre configuraciones en un dict): no escala a millones de celdas ni
mide la persistencia de toda la sección cruzada; acá se trabaja con los tensores de `grilla_masiva`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import grilla_generica as GG
from edgelab.research import grilla_masiva as GM

HORIZONTES = ((1, 1), (3, 1), (3, 3), (6, 3))           # (meses de formación, meses de prueba), declarados antes
K_META = (10, 100)                                     # tamaños de canasta
MIN_OPS_FORMACION = (10, 10, 20, 30)                   # por horizonte (mismo orden): operaciones mínimas para rankear
MIN_OPS_PRUEBA = 5
DESFASES = (0, 12)                                     # 0 = estática + régimen; 12 = casi sólo estática


def matriz_mensual(exp, ctx, *, friccion, cortes=None, cx_ej=None, log=print) -> dict:
    """S (suma de P&L neto), Q (suma de cuadrados) y C (operaciones) por celda y mes, aplanados (meses × celdas, float32)."""
    D = exp.disparos(ctx).reset_index(drop=True)
    if "ses" not in D: D["ses"] = ctx["ses"][D.k.to_numpy()]
    cortes = cortes or GG.cortes_e0(D, exp.VARIABLES)
    di, ei, pnl, _amb, _dist = GG.simular_ops(exp, D, ctx, cx_ej=cx_ej)
    net = pnl - friccion
    if (norm := getattr(exp, "NORMALIZAR", None)):
        net = net / GG.escala_ops(norm, D.ses.to_numpy()[di], cx_ej if cx_ej is not None else ctx)
    P = GG.perillas(exp, cortes); idx = [b[di] for b in GG.discretizar(D, exp.VARIABLES, cortes)] + [ei]
    mes = pd.to_datetime(ctx["t"][D.k.to_numpy()[di]], unit="s", utc=True).strftime("%Y%m").to_numpy()
    meses = sorted(set(mes.tolist())); S, Q, C = [], [], []
    for m in meses:
        s, q, c = GM.tensor(P, idx, np.where(mes == m, net, np.nan))
        S.append(s.ravel().astype(np.float32)); Q.append(q.ravel().astype(np.float32)); C.append(c.ravel().astype(np.float32))
        log(f"mes {m}: {int(np.nansum(np.isfinite(net) & (mes == m)))} operaciones")
    return dict(S=np.stack(S), Q=np.stack(Q), C=np.stack(C), meses=meses, cortes=cortes, celdas=int(S[0].size),
                forma=[p.niveles for p in P])


def _rangos(x):
    return pd.Series(x).rank().to_numpy()


def persistencia(M: dict, form: int, prueba: int, min_f: int, min_p: int = MIN_OPS_PRUEBA, desfase: int = 0) -> dict:
    """Una fila por ventana: formación = `form` meses, prueba = `prueba` meses que empiezan `desfase` meses después del fin de la
    formación; las ventanas de prueba no se solapan. Con desfase 0 la correlación mezcla calidad ESTÁTICA de la celda (p. ej. celdas
    que pierden siempre por costos) y persistencia de RÉGIMEN; con desfase 12 queda casi sólo la estática. Régimen = la diferencia."""
    S, C, meses = M["S"], M["C"], M["meses"]; filas = []
    for t0 in range(form, len(meses) - prueba - desfase + 1, prueba):
        t = t0 + desfase
        sf, cf = S[t0 - form:t0].sum(0), C[t0 - form:t0].sum(0); sp, cp = S[t:t + prueba].sum(0), C[t:t + prueba].sum(0)
        ok = (cf >= min_f) & (cp >= min_p)
        if ok.sum() < 50: continue
        mf, mp = sf[ok] / cf[ok], sp[ok] / cp[ok]
        rho = float(np.corrcoef(_rangos(mf), _rangos(mp))[0, 1])
        top = mf >= np.quantile(mf, 0.9)
        filas.append(dict(prueba_desde=meses[t], celdas=int(ok.sum()), rho=rho, media_prueba=float(mp.mean()),
                          media_prueba_top10=float(mp[top].mean()), diferencial_top10=float(mp[top].mean() - mp.mean()),
                          media_prueba_top10_por_op=float(sp[ok][top].sum() / cp[ok][top].sum())))
    return dict(formacion=form, prueba=prueba, desfase=desfase, min_ops_formacion=min_f, ventanas=filas, **_resumen_ventanas(filas, ("rho", "diferencial_top10")))


def meta_regla(M: dict, form: int, k: int, min_f: int, criterio: str = "t") -> dict:
    """Cada mes t: las k celdas con mejor formación (meses t-form..t-1; `criterio` "t" = media/error estándar, "media") con >= min_f
    operaciones; se operan en el mes t. P&L neto por operación del mes (todas las operaciones de las k celdas, peso igual por operación)."""
    S, Q, C, meses = M["S"], M["Q"], M["C"], M["meses"]; filas = []
    for t in range(form, len(meses)):
        sf, qf, cf = S[t - form:t].sum(0), Q[t - form:t].sum(0), C[t - form:t].sum(0)
        ok = cf >= min_f
        if ok.sum() < k: continue
        mu = np.where(ok, sf / np.maximum(cf, 1), -np.inf)
        if criterio == "t":
            var = np.maximum(qf / np.maximum(cf, 1) - mu ** 2, 1e-12)
            puntaje = np.where(ok, mu / np.sqrt(var / np.maximum(cf, 1)), -np.inf)
        else:
            puntaje = mu
        sel = np.argpartition(-puntaje, k)[:k]
        n = float(C[t, sel].sum())
        filas.append(dict(mes=meses[t], operaciones=n, neto_total=float(S[t, sel].sum()), neto_por_op=float(S[t, sel].sum() / n) if n else None))
    x = [f["neto_por_op"] for f in filas if f["neto_por_op"] is not None]
    return dict(formacion=form, k=k, criterio=criterio, min_ops_formacion=min_f, meses=filas,
                **_resumen_ventanas([dict(neto_por_op=v) for v in x], ("neto_por_op",)),
                neto_total=float(sum(f["neto_total"] for f in filas)), operaciones=float(sum(f["operaciones"] for f in filas)))


def _resumen_ventanas(filas, claves) -> dict:
    """Media, error estándar entre ventanas y t (las ventanas son la unidad: no se cuentan celdas como independientes)."""
    out = {}
    for k in claves:
        v = np.array([f[k] for f in filas if f.get(k) is not None and np.isfinite(f[k])], float)
        if len(v) < 2: out[k] = dict(n=int(len(v))); continue
        se = float(v.std(ddof=1) / np.sqrt(len(v)))
        out[k] = dict(n=int(len(v)), media=float(v.mean()), se=se, t=float(v.mean() / se) if se > 0 else None,
                      frac_positivas=float((v > 0).mean()))
    return dict(resumen=out)


def correr(exp, ctx, *, friccion, cortes=None, cx_ej=None, log=print, horizontes=None, meta_formacion=None) -> dict:
    """`horizontes` [[form, prueba, min_ops], ...] y `meta_formacion` [[form, min_ops], ...] los fija el pre-registro (o su adenda)."""
    M = matriz_mensual(exp, ctx, friccion=friccion, cortes=cortes, cx_ej=cx_ej, log=log)
    hz = horizontes or [[f, p, mn] for (f, p), mn in zip(HORIZONTES, MIN_OPS_FORMACION)]
    pers = [persistencia(M, f, p, mn, desfase=d) for f, p, mn in hz for d in DESFASES]
    meta = [meta_regla(M, f, k, mn, cr) for f, mn in (meta_formacion or ((1, 10), (3, 20))) for k in K_META for cr in ("t", "media")]
    return dict(experimento=exp.NOMBRE, meses=M["meses"], celdas=M["celdas"], cortes=M["cortes"],
                ops_mes_celda_mas_ancha=[float(np.nanmax(c)) for c in M["C"]], persistencia=pers, meta_regla=meta)
