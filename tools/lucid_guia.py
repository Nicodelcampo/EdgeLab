#!/usr/bin/env python3
"""LucidFlex con el marco de la guía «Cómo exprimir a las casas de fondeo» (EV por examen comprado, cascada evaluación → primer retiro →
retiros siguientes, plan de riesgo por día) y con las reglas oficiales de los 4 tamaños leídas el 2026-11-19. Pedido de Nico (2026-11-19):
«rehacé los cálculos aprovechando esta guía … el tiempo que se demora en pasar o quemar una cuenta, sobre todo si el máximo es 5 en Lucid».

Reutiliza `tools/lucid_canastas.py::serie_senales` (las series diarias en USD de cada canasta, MNQ con tamaño por riesgo) y generaliza su
`_sim` (que sólo tenía el 25K): `existente.py buscar` encontró además `edgelab/propfirm/ev.py`, que simula estrategias paramétricas (p de
acierto, objetivo, stop) y no series empíricas ni cuentas en paralelo, así que no sirve para esto.

Dos simulaciones, descriptivas (no eligen reglas ni tocan el holdout; ventana 2020-01 → 2025-07 de desarrollo, sin cambios):
  1. Por cuenta: la cascada de la guía y los TIEMPOS (días hábiles) hasta pasar, quemar la evaluación, primer retiro, quemar la fondeada.
  2. Cartera con los límites de Lucid (5 fondeadas, 10 evaluaciones, 10 en total por hogar): todas las cuentas operan la misma canasta (el
     mismo P&L el mismo día: la regla de cobertura prohíbe otra cosa, ver el RESULTADO), se compra una evaluación nueva por día mientras
     haya lugar, y el paso a live (al 5.º retiro de cualquier cuenta) cierra todas las cuentas de simulación; la evaluación en curso se
     reembolsa si no tuvo retiros y le queda ≥ 50 % del drawdown. Lo que vale la cuenta live no se modela.
  python tools/lucid_guia.py   # -> docs/research/lucid_guia_20261119/LUCID_GUIA.json
"""
import json, sys
from pathlib import Path
import numpy as np
from numba import njit

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/lucid_guia_20261119"

# Reglas oficiales LucidFlex (support.lucidtrading.com y lucidtrading.com, leídas el 2026-11-19): objetivo, pérdida máxima EOD (se fija en
# +$100 al superar MLL + $100 o al primer retiro), DLL opcional, mínimo diario de los 5 días de retiro, tope por retiro, máximo de micros.
TAMANOS = {
    "25K": dict(objetivo=1250.0, mll=1000.0, dll=600.0, dia_min=100.0, tope=1000.0, micros=20),
    "50K": dict(objetivo=3000.0, mll=2000.0, dll=1200.0, dia_min=150.0, tope=2000.0, micros=40),
    "100K": dict(objetivo=6000.0, mll=3000.0, dll=1800.0, dia_min=200.0, tope=2500.0, micros=60),
    "150K": dict(objetivo=9000.0, mll=4500.0, dll=2700.0, dia_min=250.0, tope=3000.0, micros=100),
}
# Precios: lista LucidFlex con DLL (trader-review.io, verificado por ellos el 2026-10-07: $79 / $136 / $258 / $372; sin DLL +$10/+$10/+$35/+$35)
# con el código VAULT (≈ −30 %). El 25K coincide con lo verificado el 2026-11-17 (DLL $600 y 50 % = $55,30). La consistencia de 40 % (sin
# adicional) se estima con la razón del 25K (45,50 / 55,30): ESTIMADO, declarado.
LISTA = {"25K": 79.0, "50K": 136.0, "100K": 258.0, "150K": 372.0}; SIN_DLL = {"25K": 10.0, "50K": 10.0, "100K": 35.0, "150K": 35.0}
DESC_VAULT = 0.70; RAZON_40 = 45.50 / 55.30


def precio(tam, dll, cons):
    p = (LISTA[tam] + (0.0 if dll else SIN_DLL[tam])) * DESC_VAULT
    return round(p * (RAZON_40 if cons < 0.45 else 1.0), 2)


@njit(cache=False)
def _cuenta(y, N, seed, objetivo, mll, dll, dia_min, tope, cons, max_dias):
    """Una cuenta por trayectoria: bootstrap por bloques de 5 sesiones de y (ya recentrada). Devuelve tiempos y montos."""
    np.random.seed(seed); L = len(y)
    pasa = np.zeros(N); de = np.zeros(N); npg = np.zeros(N); cob = np.zeros(N); df = np.zeros(N); quema_f = np.zeros(N)
    t1 = np.full(N, -1.0); tpag = np.zeros((N, 5)) - 1.0
    for k in range(N):
        pos = np.random.randint(L); paso = 0
        bal = 0.0; piso = -mll; maxc = 0.0; mayor = 0.0; d = 0; ok = False
        while d < max_dias:
            if paso % 5 == 0: pos = np.random.randint(L)
            p = y[(pos + paso % 5) % L]; paso += 1
            if dll > 0 and p < -dll: p = -dll
            bal += p; d += 1; mayor = max(mayor, p)
            if bal <= piso: break
            maxc = max(maxc, bal); piso = min(max(piso, maxc - mll), 100.0)
            if bal >= objetivo and mayor / bal <= cons: ok = True; break
        de[k] = d
        if not ok: continue
        pasa[k] = 1.0; bal = 0.0; piso = -mll; maxc = 0.0; c0 = 0.0; dok = 0; f = 0; n = 0; tot = 0.0
        while f < max_dias and n < 5:
            if paso % 5 == 0: pos = np.random.randint(L)
            p = y[(pos + paso % 5) % L]; paso += 1
            if dll > 0 and p < -dll: p = -dll
            bal += p; f += 1
            if p >= dia_min: dok += 1
            if bal <= piso: quema_f[k] = 1.0; break
            maxc = max(maxc, bal)
            if piso < 100.0: piso = 100.0 if maxc > mll + 100.0 else max(piso, maxc - mll)
            monto = min(tope, 0.5 * bal)
            if dok >= 5 and bal > c0 and monto >= 500.0 and monto >= tope:       # política de la guía: esperar el retiro máximo
                tot += 0.9 * monto; bal -= monto; tpag[k, n] = f; n += 1; piso = 100.0; c0 = bal; dok = 0
        npg[k] = n; cob[k] = tot; df[k] = f
    return pasa, de, npg, cob, df, quema_f, tpag


@njit(cache=False)
def _cartera(y, N, seed, H, objetivo, mll, dll, dia_min, tope, cons, precio_, max_eval, max_fond, max_total, por_dia):
    """Calendario de H sesiones; todas las cuentas reciben el mismo P&L el mismo día. Estados: 0 libre, 1 evaluación, 2 aprobada esperando
    lugar de fondeada, 3 fondeada. El 5.º retiro de cualquier cuenta = paso a live: se cierra todo (evaluaciones reembolsadas si les queda
    ≥ 50 % del drawdown) y termina la trayectoria."""
    np.random.seed(seed); L = len(y); S = 10
    caja = np.zeros(N); comprado = np.zeros(N); cobrado = np.zeros(N); dia_live = np.full(N, -1.0); caja_min = np.zeros(N)
    caja_mes = np.zeros((N, H // 21 + 1)); fondeadas = np.zeros(N); retiros = np.zeros(N); quemadas = np.zeros(N); reemb = np.zeros(N)
    for k in range(N):
        est = np.zeros(S, np.int64); bal = np.zeros(S); piso = np.zeros(S); maxc = np.zeros(S); mayor = np.zeros(S)
        dok = np.zeros(S, np.int64); c0 = np.zeros(S); npg = np.zeros(S, np.int64)
        pos = np.random.randint(L); c = 0.0; cmin = 0.0
        for d in range(H):
            if d % 5 == 0: pos = np.random.randint(L)
            p = y[(pos + d % 5) % L]
            if dll > 0 and p < -dll: p = -dll
            live = False
            for i in range(S):
                if est[i] == 1:
                    bal[i] += p; mayor[i] = max(mayor[i], p)
                    if bal[i] <= piso[i]: est[i] = 0; quemadas[k] += 1; continue
                    maxc[i] = max(maxc[i], bal[i]); piso[i] = min(max(piso[i], maxc[i] - mll), 100.0)
                    if bal[i] >= objetivo and mayor[i] / bal[i] <= cons: est[i] = 2
                elif est[i] == 3:
                    bal[i] += p
                    if p >= dia_min: dok[i] += 1
                    if bal[i] <= piso[i]: est[i] = 0; quemadas[k] += 1; continue
                    maxc[i] = max(maxc[i], bal[i])
                    if piso[i] < 100.0: piso[i] = 100.0 if maxc[i] > mll + 100.0 else max(piso[i], maxc[i] - mll)
                    monto = min(tope, 0.5 * bal[i])
                    if dok[i] >= 5 and bal[i] > c0[i] and monto >= tope:
                        c += 0.9 * monto; cobrado[k] += 0.9 * monto; caja_mes[k, d // 21] += 0.9 * monto; retiros[k] += 1
                        bal[i] -= monto; npg[i] += 1; piso[i] = 100.0; c0[i] = bal[i]; dok[i] = 0
                        if npg[i] >= 5: live = True
            if live:
                for i in range(S):
                    if est[i] == 1 and bal[i] - piso[i] >= 0.5 * mll: c += precio_; comprado[k] -= precio_; reemb[k] += 1; caja_mes[k, d // 21] += precio_
                dia_live[k] = d; break
            nf = 0; ne = 0
            for i in range(S):
                if est[i] == 3: nf += 1
            for i in range(S):                                           # aprobadas pasan a fondeada si hay lugar
                if est[i] == 2 and nf < max_fond:
                    est[i] = 3; nf += 1; fondeadas[k] += 1; bal[i] = 0.0; piso[i] = -mll; maxc[i] = 0.0; dok[i] = 0; c0[i] = 0.0; npg[i] = 0
            for i in range(S):
                if est[i] == 1 or est[i] == 2: ne += 1
            compras = 0
            for i in range(S):                                           # comprar evaluaciones nuevas (empiezan a operar mañana)
                if compras >= por_dia or ne >= max_eval or ne + nf >= max_total: break
                if est[i] == 0:
                    est[i] = 1; bal[i] = 0.0; piso[i] = -mll; maxc[i] = 0.0; mayor[i] = 0.0
                    c -= precio_; comprado[k] += precio_; caja_mes[k, d // 21] -= precio_; ne += 1; compras += 1
            cmin = min(cmin, c)
        caja[k] = c; caja_min[k] = cmin
    return caja, comprado, cobrado, dia_live, caja_min, caja_mes, fondeadas, retiros, quemadas, reemb


def _q(a, qs=(0.1, 0.5, 0.9)):
    a = np.asarray(a, float); return [round(float(np.quantile(a, q)), 1) for q in qs] if len(a) else None


def por_cuenta(y, r, cons, N=20000, max_dias=500):
    pasa, de, npg, cob, df, qf, tpag = _cuenta(y, N, 7, r["objetivo"], r["mll"], r["dll"], r["dia_min"], r["tope"], cons, max_dias)
    p = pasa > 0; c1 = npg > 0
    return dict(
        pasa=float(p.mean()), quema_eval=float((~p & (de < max_dias)).mean()), sin_resolver_eval=float((~p & (de >= max_dias)).mean()),
        dias_pasar_p10_50_90=_q(de[p]), dias_quemar_eval_p10_50_90=_q(de[~p & (de < max_dias)]),
        cobra_dado_pasa=float(c1[p].mean()) if p.any() else 0.0, retiros_dado_cobra=float(npg[c1].mean()) if c1.any() else 0.0,
        dist_retiros={str(i): float((npg[p] == i).mean()) for i in range(6)} if p.any() else {},
        dias_fondeada_a_1er_retiro_p10_50_90=_q(tpag[c1, 0]), dias_fondeada_a_5to_p10_50_90=_q(tpag[npg == 5, 4]),
        quema_fondeada_dado_pasa=float(qf[p].mean()) if p.any() else 0.0, dias_quemar_fondeada_p10_50_90=_q(df[qf > 0]),
        llega_a_live=float((npg == 5).mean()), cobrado_medio=float(cob.mean()),
        dias_cuenta_media=float((de + df * pasa).mean()))


def cartera(y, r, cons, pr, max_eval, por_dia=1, N=4000, H=504):
    caja, comp, cobr, dlive, cmin, cmes, fond, ret, quem, reemb = _cartera(y, N, 11, H, r["objetivo"], r["mll"], r["dll"], r["dia_min"],
                                                                         r["tope"], cons, pr, max_eval, 5, 10, por_dia)
    vivo = dlive >= 0
    meses = np.where(vivo, (dlive + 1) / 21.0, H / 21.0)
    acum12 = cmes[:, :12].sum(1)
    return dict(neto_medio=float(caja.mean()), neto_p10_50_90=_q(caja), p_neto_positivo=float((caja > 0).mean()),
                neto_12m_medio=float(acum12.mean()), neto_12m_p10_50_90=_q(acum12),
                usd_por_mes_hasta_fin=float((caja / meses).mean()), p_live_en_24m=float(vivo.mean()),
                meses_a_live_p10_50_90=_q((dlive[vivo] + 1) / 21.0), caja_minima_p50_p10=[round(float(np.median(cmin)), 0), round(float(np.quantile(cmin, 0.1)), 0)],
                evaluaciones_compradas=float((comp / pr).mean()), fondeadas=float(fond.mean()), retiros=float(ret.mean()), quemadas=float(quem.mean()),
                reembolsos=float(reemb.mean()))


def main():
    from lucid_canastas import serie_senales
    OUT.mkdir(parents=True, exist_ok=True)
    canastas = (("T",), ("T", "R"), ("T", "R", "ZB"), ("T", "R", "ZB", "SOMEOD"))
    res = dict(nota=__doc__.split("\n\n")[0], tamanos=TAMANOS, precios={t: {f"{'DLL' if d else 'sinDLL'}|{int(c * 100)}%": precio(t, d, c)
               for d in (True, False) for c in (0.4, 0.5)} for t in TAMANOS}, por_cuenta={}, cartera={})
    for tam, r in TAMANOS.items():
        esc = r["mll"] / 1000.0
        for base in (100.0, 200.0):                     # USD de riesgo por operación en la 25K; se escala con la pérdida máxima del tamaño
            for reglas in canastas:
                x, info = serie_senales(base * esc, reglas, tope_micros=r["micros"] // 3)
                x = x.to_numpy(np.float64)
                for mu_nom, mu in (("dev", x.mean()), ("contraida", 0.5 * x.mean()), ("cero", 0.0)):
                    y = x - x.mean() + mu
                    for dll in (True, False):
                        cons = 0.5; pr = precio(tam, dll, cons); rr = dict(r, dll=r["dll"] if dll else 0.0)
                        nom = f"{tam}|riesgo{int(base)}|{'+'.join(reglas)}|{mu_nom}|{'DLL' if dll else 'sinDLL'}|50%"
                        a = por_cuenta(y, rr, cons); a.update(precio=pr, ev_examen=a["cobrado_medio"] - pr,
                                                             ev_por_mes_cuenta=(a["cobrado_medio"] - pr) / max(a["dias_cuenta_media"], 1) * 21,
                                                             usd_dia_media=float(y.mean()), usd_dia_sd=float(y.std()), micros_medio=info["micros_medio"])
                        res["por_cuenta"][nom] = a
                        if mu_nom != "dev" and dll:
                            for me in (1, 5, 10):
                                res["cartera"][f"{nom}|eval{me}"] = cartera(y, rr, cons, pr, me)
                        print(nom, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in a.items() if k in (
                            "pasa", "cobra_dado_pasa", "retiros_dado_cobra", "ev_examen", "dias_pasar_p10_50_90", "dias_quemar_eval_p10_50_90",
                            "dias_fondeada_a_1er_retiro_p10_50_90", "llega_a_live")}, flush=True)
    (OUT / "LUCID_GUIA.json").write_text(json.dumps(res, indent=1, default=float) + "\n")




def _ops_reglas():
    """Operaciones por regla (T, R, ZB) en NQ con R neto con la fricción canónica de NQ: para comparar períodos (2026-11-19)."""
    import pandas as pd
    from edgelab.research.embudo_runners import friccion
    fr = float(friccion("NQ")[0]); D = ROOT / "docs/research"
    t = pd.read_csv(D / "m1_largo_20261117/FS_OPS_T2008_NQ.csv.gz"); t = t[t.riesgo > 0]
    t = pd.DataFrame(dict(regla="T", ses=t.dia, bruto=t.neto + fr, riesgo=t.riesgo))
    o = pd.read_csv(D / "neto_pistas_20261119/RZ_OPS.csv.gz"); o = o[o.inst == "NQ"]; rg = 0.25 * o.atr20
    o = o.assign(bruto=np.where(o.mae_pts >= rg, -rg, o.pnl_pts), riesgo=rg)
    r = o[o.variante == "R_21_100_2.5_660"]; r = pd.DataFrame(dict(regla="R", ses=r.ses, bruto=r.bruto, riesgo=r.riesgo))
    banda = [f"Z_{a}_{b}_{e}" for (a, b) in ((10, 30), (15, 20), (30, 10)) for e in (35, 45, 55)]
    z = o[(o.modulo == "Z") & o.variante.isin(banda)].groupby("ses")[["bruto", "riesgo"]].mean().reset_index().assign(regla="ZB")
    x = pd.concat([t, r, z[["regla", "ses", "bruto", "riesgo"]]], ignore_index=True)
    x["fecha"] = pd.to_datetime(x.ses); x["R"] = (x.bruto - fr) / x.riesgo; x["mes"] = x.fecha.dt.to_period("M").astype(str)
    return x[x.riesgo > 0]


def _tabla_periodo(x, desde, hasta):
    import pandas as pd
    s = x[(x.fecha >= desde) & (x.fecha <= hasta)]; meses = pd.period_range(desde, hasta, freq="M").astype(str); out = {}
    for g, d in list(s.groupby("regla")) + [("T+R+ZB", s)]:
        m = d.groupby("mes").R.sum().reindex(meses, fill_value=0.0)
        out[g] = dict(ops=int(len(d)), ops_mes=len(d) / len(meses), R_op=float(d.R.mean()), R_mes=float(m.mean()),
                      t_mensual=float(m.mean() / m.std(ddof=1) * np.sqrt(len(m))), meses_pos=float((m > 0).mean()), meses=len(meses))
    return out


def extra():
    """Pedido de Nico (2026-11-19): «¿qué pasa después del desarrollo de 2025-07? ¿gana menos? ¿qué pasa si se operan minis en vez de micros?»
    Período 2025-08 → 2026-09 (lo último antes del terminal sellado del 2026-10-01; datos ya vistos al elegir las reglas, no fuera de muestra)."""
    from lucid_canastas import serie_senales
    x = _ops_reglas(); res = dict(periodos={}, por_anio={}, lucid_periodo={}, minis={})
    for nom, (a, b) in (("2020-01_2025-07", ("2020-01-01", "2025-07-31")), ("2025-08_2026-09", ("2025-08-01", "2026-09-30"))):
        res["periodos"][nom] = _tabla_periodo(x, a, b)
    for y in range(2018, 2027):
        res["por_anio"][str(y)] = _tabla_periodo(x, f"{y}-01-01", f"{y}-12-31" if y < 2026 else "2026-09-30")
    reglas = ("T", "R", "ZB")
    for tam in ("25K", "50K"):                                      # Lucid con la media propia de cada período (realizada, sin contraer)
        r = TAMANOS[tam]; esc = r["mll"] / 1000.0
        for nom, (a, b) in (("2020-01_2025-07", (20200101, 20250731)), ("2025-08_2026-09", (20250801, 20260930))):
            s, info = serie_senales(100.0 * esc, reglas, desde=a, hasta=b, tope_micros=r["micros"] // 3); y = s.to_numpy(np.float64)
            acc = por_cuenta(y, r, 0.5); pr = precio(tam, True, 0.5)
            acc.update(precio=pr, ev_examen=acc["cobrado_medio"] - pr, usd_dia=float(y.mean()), sd_dia=float(y.std()), sesiones=len(y))
            res["lucid_periodo"][f"{tam}|{nom}|media_propia"] = acc
    for tam, r in TAMANOS.items():                                   # micros (tamaño por riesgo) vs 1 mini por regla vs 10 micros por regla
        esc = r["mll"] / 1000.0; maxm = r["micros"] // 10
        casos = (("micros_por_riesgo", dict(usd_riesgo=100.0 * esc, tope_micros=r["micros"] // 3, contrato="MNQ")),
                 ("1_mini", dict(usd_riesgo=1.0, tope_micros=1, contrato="NQ")),
                 ("10_micros", dict(usd_riesgo=1e9, tope_micros=10, contrato="MNQ")))
        if maxm // 3 >= 2: casos += (("2_minis", dict(usd_riesgo=1e9, tope_micros=2, contrato="NQ")),)
        for nc, kw in casos:
            s, info = serie_senales(reglas=reglas, **kw); xx = s.to_numpy(np.float64)
            for mu_nom, mu in (("contraida", 0.5 * xx.mean()), ("cero", 0.0)):
                y = xx - xx.mean() + mu; acc = por_cuenta(y, r, 0.5); pr = precio(tam, True, 0.5)
                acc.update(precio=pr, ev_examen=acc["cobrado_medio"] - pr, ev_por_mes_cuenta=(acc["cobrado_medio"] - pr) / max(acc["dias_cuenta_media"], 1) * 21,
                           usd_dia=float(y.mean()), sd_dia=float(y.std()), peor_dia=float(y.min()), riesgo_usd_real_p10_50_90=info["riesgo_usd_real_p10_50_90"],
                           contratos_medio=info["micros_medio"], max_contratos_tamano=r["micros"] if kw["contrato"] == "MNQ" else maxm)
                k = f"{tam}|{nc}|{mu_nom}"; res["minis"][k] = acc
                if mu_nom == "contraida" and tam in ("25K", "50K", "150K"):
                    res["minis"][k]["cartera_eval10"] = cartera(y, r, 0.5, pr, 10, N=2000)
                print(k, round(acc["pasa"], 3), round(acc["ev_examen"]), acc["dias_pasar_p10_50_90"], flush=True)
    (OUT / "LUCID_GUIA_EXTRA.json").write_text(json.dumps(res, indent=1, default=float) + "\n")


if __name__ == "__main__":
    extra() if sys.argv[1:] == ["extra"] else main()
