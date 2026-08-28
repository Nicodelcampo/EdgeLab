"""Censo descriptivo de contextos - zonas HFT sobre ES. TARGET-FREE, SIN OUTCOMES.

PARA QUE SIRVE
==============
No se pueden pre-registrar contextos que uno no sabe que existen. Este censo describe
DONDE y COMO aparecen las zonas, para que la declaracion de contextos sea una eleccion
informada y no una herencia (regla de poblacion de CLAUDE.md).

LA LINEA QUE NO SE CRUZA
========================
Se miran propiedades de la zona y estado de mercado ANTERIOR o SIMULTANEO a su creacion.
NUNCA que paso despues. Si el censo mirara outcomes, elegir contextos con el resultado a
la vista seria data snooping con otro nombre, y la pre-registracion posterior seria
teatro.

Por eso aca no hay excursion, ni retorno, ni cruce, ni P&L.

LOS SIETE ANALISIS, Y POR QUE ESTOS
===================================
1. TASA NORMALIZADA POR ACTIVIDAD. "Hay mas zonas en la apertura" es casi seguro "hay
   mas ticks en la apertura". La tasa cruda por hora es la trampa mas obvia de todo el
   censo, asi que se publica zonas por millon de ticks y por millon de contratos junto
   a la cruda.
2. FASE DE SESION (Asia / Europa / RTH / cierre). Lo pidio Nico y es la particion mas
   citada. Se calcula con hora de NUEVA YORK y DST real, no con offset fijo: la etiqueta
   horaria mal resuelta ya bloqueo H-SWEEP-1.
3. SOLAPAMIENTO. Nadie lo midio. Si las zonas se pisan entre si, cada una no es un
   objeto independiente y el N efectivo es menor que el N contado.
4. AGRUPAMIENTO TEMPORAL (Fano). Si llegan en rafagas, la sesion no son N eventos
   independientes. Fano = var/media sobre bins; Poisson da 1.
5. POSICION EN EL RANGO DEL DIA al momento de crearse. Barato y plausible: no es lo
   mismo una zona en el extremo del dia que una en el medio.
6. REGIMEN DE VOLATILIDAD PREVIO. La variable de condicionamiento clasica. Se mide
   sobre la ventana ANTERIOR a la creacion, nunca posterior.
7. UBICACION RESPECTO DE VWAP / SMA / EMA. Pedido de Nico. Todas se calculan sobre
   barras de 1 minuto CERRADAS ANTES de la creacion de la zona, asi que no hay lookahead.
   Distancia con signo (la zona esta arriba o abajo) y en valor absoluto: si el efecto es
   bidireccional, el canal con signo lo promedia a cero (regla de los dos canales).
8. CARACTERISTICAS POR FASE. Ancho, pasos, velocidad, volumen, direccion y bucket
   cruzados con la fase, para ver si "zona de Asia" y "zona de RTH" son el mismo objeto.

POBLACION: oraculo Flat (HFTZonesESPureV2Flat), ES 03-26, 62 sesiones pre-firewall,
51,8%/48,2% por direccion. La poblacion corregida.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import (session_bounds_utc_ns,  # noqa: E402
                                         trade_date_ymd)

SCHEMA_VERSION = "censo_contextos_es_v1_target_free"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
CONTRATO = "ES 03-26"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
HOLDOUT_FIRST_TRADE_DATE = 20260701
CUTOFF_MS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0] // 1_000_000
NY = ZoneInfo("America/New_York")

# Fases con hora de NUEVA YORK y DST real. Los bordes son convencion de mercado, no
# numeros ajustados: apertura CME 18:00, Tokio ~19:00-03:00, Londres 03:00, cash 09:30.
FASES = [("asia", 18, 3), ("europa", 3, 8), ("premarket", 8, 9.5),
         ("rth_am", 9.5, 12), ("rth_pm", 12, 16), ("cierre", 16, 18)]
VENTANA_VOL_MS = 5 * 60 * 1000        # volatilidad realizada de los 5 min ANTERIORES
BIN_CLUSTER_MIN = 5                   # bins para el Fano
SOLAPE_VENTANA_MIN = 30               # dos zonas "conviven" si nacen a < 30 min

# Medias sobre barras de 1 minuto. Periodos convencionales, declarados antes de mirar:
# no se eligen despues por cual "funciona".
SMA_PERIODOS = (20, 50)
EMA_PERIODOS = (9, 21)


def ny_de(ts_ns: int) -> datetime:
    """UTC ns -> datetime en Nueva York, con DST real."""
    return datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).astimezone(NY)


def hora_ny_de(ts_ns: int) -> float:
    d = ny_de(ts_ns)
    return d.hour + d.minute / 60.0 + d.second / 3600.0


def fase_de(hora_ny: float) -> str:
    for nombre, ini, fin in FASES:
        if ini <= fin:
            if ini <= hora_ny < fin:
                return nombre
        else:                                   # cruza medianoche
            if hora_ny >= ini or hora_ny < fin:
                return nombre
    return "otro"


def barras_1min(ts, px, vol, ini_ns):
    """Barras de 1 minuto desde la apertura. Devuelve (borde_ns, close, vwap_acum)."""
    m = ((ts - ini_ns) // 60_000_000_000).astype(np.int64)
    corte = np.flatnonzero(np.diff(m)) + 1
    tramos = np.split(np.arange(len(m)), corte)
    borde = np.array([ts[t[-1]] for t in tramos], dtype=np.int64)   # cierre de la barra
    close = np.array([px[t[-1]] for t in tramos], dtype=np.float64)
    pv = np.array([float((px[t] * vol[t]).sum()) for t in tramos])
    vv = np.array([float(vol[t].sum()) for t in tramos])
    vwap = np.cumsum(pv) / np.maximum(np.cumsum(vv), 1e-9)
    return borde, close, vwap


def sma(x, n):
    if len(x) < n:
        return np.full(len(x), np.nan)
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(x, n):
    a = 2.0 / (n + 1.0)
    out = np.empty(len(x), dtype=np.float64)
    if not len(x):
        return out
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def _json(o):
    """numpy no es serializable por defecto; convertir en vez de castear a mano en
    cada campo evita que un campo nuevo rompa el script al final de una corrida larga."""
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def q(x, p):
    return round(float(np.percentile(x, p)), 2) if len(x) else None


def resumen(x):
    x = np.asarray(x, dtype=np.float64)
    if not len(x):
        return {}
    return dict(n=len(x), p25=q(x, 25), mediana=q(x, 50), p75=q(x, 75),
                media=round(float(x.mean()), 2))


def zonas_por_sesion(snapshot):
    con = sqlite3.connect("file:%s?mode=ro" % snapshot.as_posix(), uri=True)
    filas = con.execute(
        "SELECT id, start_ts, end_ts, bucket, dir, price_upper, price_lower, "
        "pasos, valid_steps, avg_ms, total_ms, total_vol, vol_rate, height_ticks, "
        "cvd_sweep, max_level_ticks "
        "FROM hft_zones WHERE instrument=? AND start_ts < ? ORDER BY start_ts",
        (CONTRATO, CUTOFF_MS)).fetchall()
    con.close()
    out = {}
    for f in filas:
        td = int(trade_date_ymd(np.array([f[1] * 1_000_000], dtype=np.int64))[0])
        out.setdefault(td, []).append(f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--out",
                    default=str(REPO / "docs" / "research" / "censo_contextos_es.json"))
    a = ap.parse_args()

    print("censo de contextos  -  %s" % SCHEMA_VERSION)
    zs = zonas_por_sesion(pathlib.Path(a.snapshot))
    claves = sorted(zs)
    if a.max_sesiones:
        claves = claves[:a.max_sesiones]
    print("  %d sesiones  -  %s  -  SIN OUTCOMES" % (len(claves), CONTRATO))

    filas, por_sesion, sin_pq = [], [], 0
    for k, td in enumerate(claves):
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(PARQUET, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError:
            sin_pq += 1
            continue
        ts, pxt, vol, tsz = tk.ts_ns, tk.price_ticks, tk.volume, tk.tick_size
        zl = zs[td]

        # --- actividad por fase, para normalizar la tasa -----------------------
        hora = np.array([hora_ny_de(int(t)) for t in ts[::5000]])
        idx = np.arange(0, len(ts), 5000)
        act = {}
        for i, h in enumerate(hora):
            f = fase_de(h)
            j0, j1 = idx[i], (idx[i + 1] if i + 1 < len(idx) else len(ts))
            d = act.setdefault(f, dict(ticks=0, vol=0.0))
            d["ticks"] += j1 - j0
            d["vol"] += float(vol[j0:j1].sum())

        # --- medias sobre barras de 1 min, para ubicar cada zona -------------
        b_ts, b_cl, b_vwap = barras_1min(ts, pxt.astype(np.float64), vol, ini)
        medias = {"vwap": b_vwap}
        for n in SMA_PERIODOS:
            medias["sma%d" % n] = sma(b_cl, n)
        for n in EMA_PERIODOS:
            medias["ema%d" % n] = ema(b_cl, n)

        rlo, rhi = int(pxt.min()), int(pxt.max())
        info_ses = dict(trade_date=td, n_zonas=len(zl), n_ticks=int(len(ts)),
                        volumen=float(vol.sum()), rango_ticks=int(rhi - rlo),
                        actividad_por_fase={f: dict(ticks=v["ticks"],
                                                    volumen=round(v["vol"], 1))
                                            for f, v in act.items()},
                        zonas_por_fase={})

        for zz in zl:
            (zid, st, en, bucket, dr, pu, pl, pasos, vsteps, avg_ms, tot_ms,
             tvol, vrate, hticks, cvd, maxlvl) = zz
            if pu is None or pl is None:
                continue
            hi, lo = int(round(pu / tsz)), int(round(pl / tsz))
            dt_ny = ny_de(st * 1_000_000)
            h_ny = dt_ny.hour + dt_ny.minute / 60.0
            f = fase_de(h_ny)
            info_ses["zonas_por_fase"][f] = info_ses["zonas_por_fase"].get(f, 0) + 1

            j = int(np.searchsorted(ts, st * 1_000_000, side="left"))
            # --- estado ANTERIOR a la creacion ---------------------------------
            j0 = int(np.searchsorted(ts, st * 1_000_000 - VENTANA_VOL_MS * 1_000_000))
            prev = pxt[j0:j] if j > j0 else pxt[max(j - 1, 0):j]
            vol_prev = (float(prev.max() - prev.min()) if len(prev) else 0.0)
            ticks_prev = int(j - j0)
            # rango del dia HASTA ese momento (nunca posterior)
            hasta = pxt[:max(j, 1)]
            d_lo, d_hi = int(hasta.min()), int(hasta.max())
            pos = ((hi + lo) / 2.0 - d_lo) / max(d_hi - d_lo, 1)

            # barra CERRADA antes de la creacion: -1 evita mirar la barra en curso
            ib = int(np.searchsorted(b_ts, st * 1_000_000, side="left")) - 1
            mid = (hi + lo) / 2.0
            dist = {}
            for nombre, serie in medias.items():
                if 0 <= ib < len(serie) and np.isfinite(serie[ib]):
                    dd = mid - float(serie[ib])
                    dist["d_" + nombre] = round(dd, 2)          # con signo
                    dist["abs_" + nombre] = round(abs(dd), 2)   # no direccional
                else:
                    dist["d_" + nombre] = None
                    dist["abs_" + nombre] = None

            filas.append(dict(
                id=zid, trade_date=td, start_ts=st, **dist, hora_ny=round(h_ny, 3), fase=f,
                dow=dt_ny.weekday(), bucket=bucket, dir=int(dr),
                ancho_ticks=hi - lo, pasos=pasos, valid_steps=vsteps,
                avg_ms=avg_ms, total_ms=tot_ms, total_vol=tvol, vol_rate=vrate,
                cvd_sweep=cvd, max_level_ticks=maxlvl,
                lo=lo, hi=hi,
                # --- estado previo ---------------------------------------------
                rango_prev_5min_ticks=round(vol_prev, 1),
                ticks_prev_5min=ticks_prev,
                pos_en_rango_del_dia=round(float(pos), 4),
                rango_del_dia_hasta_aqui=d_hi - d_lo,
                minutos_desde_apertura=round((st * 1_000_000 - ini) / 6e10, 1)))

        # --- solapamiento y agrupamiento, dentro de la sesion -------------------
        zsl = [f for f in filas if f["trade_date"] == td]
        solapes = []
        for i, x in enumerate(zsl):
            n = 0
            for y in zsl:
                if y is x:
                    continue
                if abs(y["start_ts"] - x["start_ts"]) > SOLAPE_VENTANA_MIN * 60000:
                    continue
                if x["lo"] <= y["hi"] and y["lo"] <= x["hi"]:
                    n += 1
            solapes.append(n)
            x["n_solapan_30min"] = n
        info_ses["solape"] = resumen(solapes)

        # --- C: memoria de nivel. Nulo = misma cantidad de zonas colocadas en ticks
        # reales al azar, lo que PRESERVA el tiempo que el precio paso en cada nivel.
        # Un nulo uniforme sobre el rango inventaria concentracion donde no la hay.
        if len(zsl) >= 10:
            mids = np.array([(x["lo"] + x["hi"]) / 2.0 for x in zsl])
            def concentracion(v):
                _, c = np.unique(np.round(v).astype(np.int64), return_counts=True)
                return float(c.max()), float(len(c)), float((c >= 3).sum())
            obs = concentracion(mids)
            rng = np.random.default_rng(20260820 + td)
            nulo = np.array([concentracion(
                pxt[rng.integers(0, len(pxt), len(mids))].astype(np.float64))
                for _ in range(200)])
            info_ses["memoria_nivel"] = dict(
                niveles_distintos=int(obs[1]),
                max_zonas_en_un_nivel=int(obs[0]),
                niveles_con_3_o_mas=int(obs[2]),
                nulo_max_mediana=round(float(np.median(nulo[:, 0])), 2),
                nulo_niveles_mediana=round(float(np.median(nulo[:, 1])), 2),
                nulo_3omas_mediana=round(float(np.median(nulo[:, 2])), 2),
                p_max=round(float(np.mean(nulo[:, 0] >= obs[0])), 4),
                p_3omas=round(float(np.mean(nulo[:, 2] >= obs[2])), 4))
        if zsl:
            mins = np.array([x["minutos_desde_apertura"] for x in zsl])
            nbins = max(int(np.ceil(mins.max() / BIN_CLUSTER_MIN)), 1)
            cnt, _ = np.histogram(mins, bins=nbins, range=(0, nbins * BIN_CLUSTER_MIN))
            info_ses["fano"] = (round(float(cnt.var() / cnt.mean()), 3)
                                if cnt.mean() > 0 else None)
        por_sesion.append(info_ses)
        if (k + 1) % 10 == 0:
            print("    %d/%d sesiones  -  %d zonas" % (k + 1, len(claves), len(filas)))

    print("  %d zonas en %d sesiones" % (len(filas), len(por_sesion)))

    # ------------------------------------------------------------------ agregados
    def por(campo):
        g = {}
        for f in filas:
            g.setdefault(f[campo], []).append(f)
        return g

    fases = por("fase")
    tot_t = {f: sum(s["actividad_por_fase"].get(f, {}).get("ticks", 0)
                    for s in por_sesion) for f in fases}
    tot_v = {f: sum(s["actividad_por_fase"].get(f, {}).get("volumen", 0.0)
                    for s in por_sesion) for f in fases}

    tabla_fase = {}
    for f, g in fases.items():
        tabla_fase[f] = dict(
            n_zonas=len(g),
            frac_zonas=round(len(g) / len(filas), 4),
            ticks=tot_t[f], volumen=round(tot_v[f], 0),
            frac_ticks=round(tot_t[f] / sum(tot_t.values()), 4) if sum(tot_t.values()) else None,
            zonas_por_millon_ticks=round(len(g) / (tot_t[f] / 1e6), 2) if tot_t[f] else None,
            zonas_por_millon_contratos=round(len(g) / (tot_v[f] / 1e6), 2) if tot_v[f] else None,
            frac_alcistas=round(float(np.mean([x["dir"] == 1 for x in g])), 4),
            ancho=resumen([x["ancho_ticks"] for x in g]),
            pasos=resumen([x["pasos"] for x in g]),
            avg_ms=resumen([x["avg_ms"] for x in g]),
            total_vol=resumen([x["total_vol"] for x in g]),
            solape=resumen([x.get("n_solapan_30min", 0) for x in g]),
            pos_en_rango=resumen([x["pos_en_rango_del_dia"] for x in g]),
            frac_absorb=round(float(np.mean([x["bucket"] == "Absorb" for x in g])), 4),
            vs_medias={
                nombre: dict(
                    abs_ticks=resumen([x["abs_" + nombre] for x in g
                                       if x.get("abs_" + nombre) is not None]),
                    frac_por_encima=round(float(np.mean(
                        [x["d_" + nombre] > 0 for x in g
                         if x.get("d_" + nombre) is not None])), 4)
                    if any(x.get("d_" + nombre) is not None for x in g) else None)
                for nombre in ["vwap"] + ["sma%d" % n for n in SMA_PERIODOS]
                              + ["ema%d" % n for n in EMA_PERIODOS]})

    # --- F: persistencia. Los niveles de hoy, reaparecen manana?
    por_td = {}
    for f in filas:
        por_td.setdefault(f["trade_date"], []).append((f["lo"] + f["hi"]) / 2.0)
    fechas = sorted(por_td)
    persist, persist_nulo = [], []
    rng = np.random.default_rng(20260820)
    for i in range(1, len(fechas)):
        ayer = np.array(por_td[fechas[i - 1]])
        hoy = np.array(por_td[fechas[i]])
        if len(ayer) < 10 or len(hoy) < 10:
            continue
        cerca = np.abs(hoy[:, None] - ayer[None, :]).min(axis=1) <= 2
        persist.append(float(cerca.mean()))
        # nulo: desplazar el mapa de ayer un offset al azar dentro del rango de hoy
        off = rng.uniform(-1, 1, 50) * max(hoy.max() - hoy.min(), 1)
        persist_nulo.append(float(np.mean([
            (np.abs(hoy[:, None] - (ayer + o)[None, :]).min(axis=1) <= 2).mean()
            for o in off])))

    zonas_ses = np.array([s["n_zonas"] for s in por_sesion], dtype=np.float64)
    fanos = [s["fano"] for s in por_sesion if s.get("fano") is not None]
    sol_all = [x.get("n_solapan_30min", 0) for x in filas]

    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]
    out = dict(
        schema_version=SCHEMA_VERSION,
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        proposito=("describir DONDE y COMO aparecen las zonas, para que la declaracion "
                   "de contextos sea informada. Nada de lo que pasa DESPUES entra aca"),
        estado_previo=("rango y ticks de los 5 min ANTERIORES, y rango del dia HASTA el "
                       "instante de creacion. Ninguna ventana posterior"),
        huso=("America/New_York con DST real via zoneinfo, no offset fijo: la etiqueta "
              "horaria mal resuelta es lo que bloqueo H-SWEEP-1"),
        fases={n: [i, f] for n, i, f in FASES},
        universo=dict(n_zonas=len(filas), n_sesiones=len(por_sesion),
                      sin_parquet=sin_pq),
        zonas_por_sesion=resumen(zonas_ses),
        agrupamiento=dict(
            fano_mediana=round(float(np.median(fanos)), 3) if fanos else None,
            fano_p25=q(fanos, 25), fano_p75=q(fanos, 75),
            bin_min=BIN_CLUSTER_MIN,
            lectura="Poisson = 1; > 1 significa que llegan en rafagas"),
        solapamiento=dict(
            ventana_min=SOLAPE_VENTANA_MIN,
            resumen=resumen(sol_all),
            frac_con_al_menos_uno=round(
                float(np.mean(np.array(sol_all) > 0)), 4) if sol_all else None),
        medias_declaradas=dict(sma=list(SMA_PERIODOS), ema=list(EMA_PERIODOS),
                               base="barras de 1 minuto cerradas ANTES de la creacion",
                               vwap="acumulado de sesion hasta la barra anterior"),
        memoria_de_nivel=dict(
            nota=("nulo = misma cantidad de zonas colocadas en ticks reales al azar; "
                  "preserva el tiempo que el precio paso en cada nivel"),
            p_max_mediana=round(float(np.median(
                [s["memoria_nivel"]["p_max"] for s in por_sesion
                 if "memoria_nivel" in s])), 4) if any(
                "memoria_nivel" in s for s in por_sesion) else None,
            frac_sesiones_p_max_menor_005=round(float(np.mean(
                [s["memoria_nivel"]["p_max"] < 0.05 for s in por_sesion
                 if "memoria_nivel" in s])), 4) if any(
                "memoria_nivel" in s for s in por_sesion) else None),
        persistencia_entre_sesiones=dict(
            tolerancia_ticks=2, n_pares=len(persist),
            frac_hoy_cerca_de_ayer=round(float(np.median(persist)), 4) if persist else None,
            nulo_desplazado=round(float(np.median(persist_nulo)), 4) if persist_nulo else None,
            contraste=round(float(np.median(persist) - np.median(persist_nulo)), 4)
            if persist else None),
        por_fase=tabla_fase,
        por_dow={str(d): len(g) for d, g in sorted(por("dow").items())},
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            snapshot=str(a.snapshot), archivos_sucios=sorted(sucios),
            medicion_comprometida=bool([x for x in sucios
                                        if x.startswith(("edgelab/", "diag/"))])),
        sesiones=por_sesion)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=_json), encoding="utf-8")

    print("\n  zonas por sesion: mediana %.0f  (p25 %.0f - p75 %.0f)"
          % (out["zonas_por_sesion"]["mediana"], out["zonas_por_sesion"]["p25"],
             out["zonas_por_sesion"]["p75"]))
    print("  agrupamiento Fano: mediana %s   (Poisson = 1)"
          % out["agrupamiento"]["fano_mediana"])
    print("  solape: %.1f%% de las zonas tienen >=1 zona pisandolas a <30 min"
          % (100 * (out["solapamiento"]["frac_con_al_menos_uno"] or 0)))
    print()
    print("  fase        zonas  %zon  %ticks  z/Mtick  z/Mcontr  ancho  alcist  absorb  solape  posRango")
    for f, t in sorted(tabla_fase.items(), key=lambda kv: -kv[1]["n_zonas"]):
        print("  %-10s %6d %5.3f  %6.3f %8.2f %9.2f %6.1f %7.3f %7.3f %7.2f %9.3f"
              % (f, t["n_zonas"], t["frac_zonas"], t["frac_ticks"] or 0,
                 t["zonas_por_millon_ticks"] or 0, t["zonas_por_millon_contratos"] or 0,
                 t["ancho"]["mediana"], t["frac_alcistas"], t["frac_absorb"],
                 t["solape"]["mediana"], t["pos_en_rango"]["mediana"]))
    if persist:
        print("  persistencia: %.3f de las zonas de hoy caen a <=2 ticks de una de ayer"
              "   (nulo desplazado %.3f  ->  contraste %+.3f)"
              % (np.median(persist), np.median(persist_nulo),
                 np.median(persist) - np.median(persist_nulo)))
    mm = [s["memoria_nivel"] for s in por_sesion if "memoria_nivel" in s]
    if mm:
        print("  memoria de nivel: max zonas en un nivel %.0f (nulo %.0f)   "
              "p<0,05 en %.0f%% de las sesiones"
              % (np.median([m["max_zonas_en_un_nivel"] for m in mm]),
                 np.median([m["nulo_max_mediana"] for m in mm]),
                 100 * np.mean([m["p_max"] < 0.05 for m in mm])))
    print()
    print("  ubicacion respecto de las medias (|distancia| en ticks, mediana / %arriba)")
    print("  fase        vwap        sma20       sma50       ema9        ema21")
    for f, t in sorted(tabla_fase.items(), key=lambda kv: -kv[1]["n_zonas"]):
        cel = []
        for nombre in ("vwap", "sma20", "sma50", "ema9", "ema21"):
            v = t["vs_medias"].get(nombre, {})
            m = (v.get("abs_ticks") or {}).get("mediana")
            fa = v.get("frac_por_encima")
            cel.append("%5s/%4s" % ("-" if m is None else "%.0f" % m,
                                    "-" if fa is None else "%.2f" % fa))
        print("  %-10s %s" % (f, "  ".join(cel)))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
