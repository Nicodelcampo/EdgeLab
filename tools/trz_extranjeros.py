#!/usr/bin/env python3
"""TRZ-EXTRANJEROS (pre-registro docs/research/trz_extranjeros_20261127/PREREGISTRO.md): T, R y Z de la cartera NT8, sin cambios, en
índices extranjeros con M1 de HistData.

  python tools/trz_extranjeros.py bajar      # zips anuales/mensuales de HistData → data/trz_extranjeros/raw/ (sólo hasta 2026-09)
  python tools/trz_extranjeros.py preparar   # velas para el arnés: apertura local → 09:30 NY, escala a nivel NQ, volumen 1
  python tools/trz_extranjeros.py calibrar   # Nasdaq CFD de HistData por el mismo circuito contra NQ futuros canónico (K28)
  python tools/trz_extranjeros.py correr     # T, R y Z congelados (arnés C# de la cartera NT8, modo broker) en los 6 índices → RESULTADO.json

Transformaciones declaradas en el pre-registro (sin mirar retornos):
- hora: cada día local d se desplaza para que su apertura de contado caiga a las 09:30 de Nueva York de la fecha d;
- escala: precio × (cierre NQ del día hábil anterior / cierre del índice del día anterior), para que los parámetros en puntos de T sean
  proporcionales; la escala es constante dentro de cada día;
- volumen: 1 por vela (HistData no trae volumen; el VWAP de R pasa a ser promedio en el tiempo); sin veto de noticias de EE. UU.
"""
import http.cookiejar, re, sys, time, urllib.parse, urllib.request, zipfile, io, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "data/trz_extranjeros/raw"
INDICES = {"GRXEUR": "DAX", "UKXGBP": "FTSE", "ETXEUR": "EuroStoxx", "FRXEUR": "CAC", "JPXJPY": "Nikkei", "AUXAUD": "ASX200"}
CALIBRACION = {"NSXUSD": "Nasdaq100CFD"}     # mismo circuito (CFD, volumen 1, escala, sin noticias) contra NQ futuros canónico
APERTURA = {"DAX": ("Europe/Berlin", 9, 0), "FTSE": ("Europe/London", 8, 0), "EuroStoxx": ("Europe/Berlin", 9, 0), "CAC": ("Europe/Paris", 9, 0),
            "Nikkei": ("Asia/Tokyo", 9, 0), "ASX200": ("Australia/Sydney", 10, 0), "Nasdaq100CFD": ("America/New_York", 9, 30)}
ANIOS = range(2010, 2026)


def _op():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())); op.addheaders = [("User-Agent", "Mozilla/5.0")]
    return op


def _bajar(sym: str, anio: int, mes: int | None) -> bytes | None:
    op = _op(); ruta = f"{sym.lower()}/{anio}" + (f"/{mes}" if mes else "")
    u = f"https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{ruta}"
    h = op.open(u, timeout=60).read().decode("latin1")
    campos = dict(re.findall(r'<input type="hidden" name="(\w+)" id="\w+" value="([^"]*)"', h))
    if "tk" not in campos: return None
    req = urllib.request.Request("https://www.histdata.com/get.php", data=urllib.parse.urlencode(campos).encode(), headers={"Referer": u})
    b = op.open(req, timeout=180).read()
    return b if b[:2] == b"PK" else None


def bajar() -> int:
    RAW.mkdir(parents=True, exist_ok=True); proc = {}
    for sym in {**INDICES, **CALIBRACION}:
        piezas = [(a, None) for a in ANIOS] + [(2026, m) for m in range(1, 10)]
        for anio, mes in piezas:
            f = RAW / f"{sym}_{anio}{'' if mes is None else f'_{mes:02d}'}.zip"
            if not f.exists():
                b = None
                for intento in range(4):
                    try: b = _bajar(sym, anio, mes); break
                    except Exception as e: print("reintento", sym, anio, mes, repr(e)[:80], flush=True); time.sleep(10)
                if b is None: print("sin datos", sym, anio, mes, flush=True); continue
                f.write_bytes(b); time.sleep(2)
            proc[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        print(sym, "listo", flush=True)
    (RAW.parent / "PROCEDENCIA.json").write_text(json.dumps(dict(fuente="histdata.com ASCII M1 (hora de Nueva York con DST, sello = apertura; verificado contra NQ futuros)", archivos=proc), indent=1))
    return 0


HARN = ROOT / "data/trz_extranjeros/harness"; OUTD = ROOT / "docs/research/trz_extranjeros_20261127"
PRE = "docs/research/trz_extranjeros_20261127/PREREGISTRO.md"
FRONTERA_UTC = "2026-09-30 22:00"           # apertura de la sesión CME del 2026-10-01 (edgelab.holdout): nada desde ahí
FRIC_NQ = 1.5455                            # fricción canónica NQ en puntos (escala NQ), la que usa el arnés


def _leer(sym: str):
    import pandas as pd
    partes = []
    for f in sorted(RAW.glob(f"{sym}_*.zip")):
        z = zipfile.ZipFile(f); n = [x for x in z.namelist() if x.endswith(".csv")][0]
        d = pd.read_csv(io.BytesIO(z.read(n)), sep=";", header=None, names=["t", "o", "h", "l", "c", "v"])
        partes.append(d)
    d = pd.concat(partes).drop_duplicates("t")
    # Hora de Nueva York CON horario de verano y sello = apertura de la vela. La documentación de HistData dice «EST fijo», pero la
    # calibración contra NQ futuros (2026-11-27) mostró el desfase de 1 h en verano: ver CALIBRACION_DIAGNOSTICO.json.
    t = pd.to_datetime(d.t, format="%Y%m%d %H%M%S").dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    d = d.assign(utc=t.dt.tz_convert("UTC")).dropna(subset=["utc"]).sort_values("utc")
    return d[d.utc < pd.Timestamp(FRONTERA_UTC, tz="UTC")]


def _cierres_nq():
    import pandas as pd
    q = pd.read_parquet(ROOT / "data/m1nt8/NQ_M1_nonadj_utc.parquet", columns=["close"])
    ny = pd.DatetimeIndex(q.index).tz_localize("UTC").tz_convert("America/New_York")
    q = q[(ny.hour < 17)]; ny = ny[ny.hour < 17]
    return q.close.groupby(ny.date).last()


def _preparar_uno(nombre: str, sym: str):
    import numpy as np, pandas as pd
    from zoneinfo import ZoneInfo
    tzname, hh, mm = APERTURA[nombre]; tz = ZoneInfo(tzname); NY = ZoneInfo("America/New_York")
    d = _leer(sym); loc = d.utc.dt.tz_convert(tz); d["dia"] = loc.dt.date
    dias = sorted(d.dia.unique())
    off = {}
    for x in dias:
        a = pd.Timestamp(x.year, x.month, x.day, hh, mm, tz=tz).tz_convert("UTC")
        b = pd.Timestamp(x.year, x.month, x.day, 9, 30, tz=NY).tz_convert("UTC")
        off[x] = b - a
    d["t2"] = d.utc + d.dia.map(off)
    cierre_idx = d.groupby("dia").c.last(); nq = _cierres_nq()
    nq_s = pd.Series(nq.values, index=pd.to_datetime(list(nq.index))); idx_s = pd.Series(cierre_idx.values, index=pd.to_datetime(list(cierre_idx.index)))
    esc = {}
    for x in dias:
        t = pd.Timestamp(x); a = nq_s[nq_s.index < t]; b = idx_s[idx_s.index < t]
        esc[x] = float(a.iloc[-1] / b.iloc[-1]) if len(a) and len(b) else np.nan
    d["k"] = d.dia.map(esc); d = d.dropna(subset=["k"])
    d = d.drop_duplicates("t2", keep="first").sort_values("t2")
    d = d[d.t2 < pd.Timestamp(FRONTERA_UTC, tz="UTC")]
    out = pd.DataFrame({"t": d.t2.dt.as_unit("s").astype("int64") + 60, "o": d.o * d.k, "h": d.h * d.k, "l": d.l * d.k, "c": d.c * d.k, "v": 1.0})
    out = out[(out.h >= out.l)]
    HARN.mkdir(parents=True, exist_ok=True); f = HARN / f"{nombre}.csv"; out.round(4).to_csv(f, index=False)
    return f, len(out), str(d.t2.min()), str(d.t2.max())


def preparar() -> int:
    for sym, nombre in {**INDICES, **CALIBRACION}.items():
        if not list(RAW.glob(f"{sym}_*.zip")): print("sin zips", sym); continue
        print(nombre, _preparar_uno(nombre, sym), flush=True)
    return 0


def _arnes(nombre: str, comp: str = "NQ:T=1,R=1,Z=1"):
    import subprocess, pandas as pd
    sys.path.insert(0, str(ROOT / "tools"))
    import nt8_cartera_paridad as P
    exe = P.compilar(); vol = P.cboe_csv(ROOT / "data/harness_bars"); od = HARN / f"out_{nombre}"; od.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["mono", str(exe), "broker", str(od), "-", str(vol), "0", comp, f"NQ={HARN / f'{nombre}.csv'}"], capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit(r.stderr[-2000:])
    o = pd.read_csv(od / "broker_NQ.csv")
    o["dia"] = pd.to_datetime(o.ex_ny).dt.normalize()
    return o


def _r(o, fric):
    return (o.pnl_pts - fric) / o.riesgo_pts


EXCLUIDOS = {"Nikkei", "ASX200"}     # adenda del pre-registro: su hora no pasa la verificación de apertura (sin retornos)
MODS = {"T": "T_stop100_BE15R_calFalse", "R": "R_osc30_end660_ATR50", "Z": "Z_b15_e20_eff40_ATR50"}


def _por_sesion(o, mod):
    g = o[o.modulo == mod]
    return {int(k.strftime("%Y%m%d")): float(v) for k, v in _r(g, FRIC_NQ).groupby(g.dia).sum().items()}


def calibrar() -> int:
    import pandas as pd
    from edgelab.research.a5 import calibrar_por_sesion
    _preparar_uno("Nasdaq100CFD", "NSXUSD"); o = _arnes("Nasdaq100CFD")
    ref = pd.read_csv(ROOT / "docs/research/cartera_nt8_20261125/paridad_intradia/broker_NQ.csv.gz"); ref["dia"] = pd.to_datetime(ref.ex_ny).dt.normalize()
    a, b = pd.Timestamp("2019-07-01"), pd.Timestamp("2026-09-29")
    o = o[(o.dia >= a) & (o.dia <= b)]; ref = ref[(ref.dia >= a) & (ref.dia <= b)]
    res = {}
    for k, mod in MODS.items():
        c = calibrar_por_sesion(_por_sesion(ref, mod), _por_sesion(o, mod))
        c.update(ops_ref=int((ref.modulo == mod).sum()), ops_cfd=int((o.modulo == mod).sum())); res[k] = c
        print(k, c, flush=True)
    OUTD.mkdir(parents=True, exist_ok=True)
    (OUTD / "CALIBRACION.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


def _stats(x):
    import numpy as np
    from math import erf, sqrt
    x = x.dropna(); n = len(x)
    if n < 3 or x.std() == 0: return dict(meses=n)
    t = float(x.mean() / (x.std(ddof=1) / np.sqrt(n)))
    return dict(meses=n, media_R_mes=round(float(x.mean()), 4), sharpe_anual=round(float(x.mean() / x.std(ddof=1) * np.sqrt(12)), 3),
                t=round(t, 2), p_una_cola=round(0.5 * (1 - erf(t / sqrt(2))), 4), pct_meses_pos=round(float((x > 0).mean()), 3))


def correr() -> int:
    import pandas as pd
    from registro_global import exigir_contada
    exigir_contada(PRE)
    cal = json.loads((OUTD / "CALIBRACION.json").read_text(encoding="utf-8"))
    vivos = [k for k, v in cal.items() if v["calibra"]]
    partes = []
    for sym, nombre in INDICES.items():
        if nombre in EXCLUIDOS: continue
        if not (HARN / f"{nombre}.csv").exists(): _preparar_uno(nombre, sym)
        o = _arnes(nombre); o["indice"] = nombre; partes.append(o); print(nombre, len(o), flush=True)
    O = pd.concat(partes, ignore_index=True); inv = {v: k for k, v in MODS.items()}; O["mod"] = O.modulo.map(inv)
    O["R"] = _r(O, FRIC_NQ); O["R2"] = _r(O, 2 * FRIC_NQ); O["mes"] = O.dia.dt.to_period("M")
    O.to_csv(OUTD / "OPS.csv.gz", index=False)
    def canasta(df, col="R"):
        m = df.pivot_table(index="mes", columns=[df["mod"], df.indice], values=col, aggfunc="sum")
        return m.fillna(0.0).where(m.notna().cumsum() > 0).mean(axis=1).dropna()
    V = O[O["mod"].isin(vivos)]
    c = canasta(V)
    res = dict(calibracion=cal, modulos_leidos=vivos, operaciones={f"{k}_{i}": int(((O["mod"] == k) & (O.indice == i)).sum()) for k in MODS for i in O.indice.unique()},
               primaria=_stats(c), estres_2x=_stats(canasta(V, "R2")),
               antes_2020=_stats(c[c.index < pd.Period("2020-01", "M")]), desde_2020=_stats(c[c.index >= pd.Period("2020-01", "M")]),
               por_modulo={k: _stats(canasta(O[O["mod"] == k])) for k in vivos},
               por_indice={i: _stats(canasta(V[V.indice == i])) for i in sorted(V.indice.unique())},
               por_modulo_indice={f"{k}_{i}": _stats(canasta(O[(O["mod"] == k) & (O.indice == i)])) for k in vivos for i in sorted(O.indice.unique())},
               R_medio_por_op={k: round(float(O[O["mod"] == k].R.mean()), 4) for k in vivos})
    res["veredicto"] = "CONFIRMA" if res["primaria"].get("t", 0) >= 1.645 else ("NO_CONCLUYENTE" if res["primaria"].get("media_R_mes", 0) > 0 else "EN_CONTRA")
    (OUTD / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("modulos_leidos", "primaria", "veredicto", "por_modulo")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
    sys.exit({"bajar": bajar, "preparar": preparar, "calibrar": calibrar, "correr": correr}[sys.argv[1]]())
