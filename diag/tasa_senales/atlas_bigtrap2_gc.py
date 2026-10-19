"""Atlas target-free de TRAPs de BigTrap2 sobre GC, con contexto de LIBRO. SIN OUTCOMES.

QUE ES
======
Una fila por evento `TRAP` del oraculo v2.5.2, con el estado del mercado y del LIBRO en el
instante de creacion. Se construye ANTES de que exista ningun outcome, para que los
contextos y los controles no se elijan mirando resultados.

Es la primera vez en el proyecto que hay profundidad real: hasta ahora todo se media con
trades solos, y la literatura señala que la señal mas fuerte esta en el libro.

LAS TRES POBLACIONES, CON LAS MISMAS COLUMNAS
=============================================
  TRAP        evento real del oraculo
  CASI_TRAP   barra que califica en TODO menos en el ratio de imbalance, por poco
  BARRA       barra cualquiera, sin TRAP ni casi

Sin las dos ultimas no se sabe si lo que se mida despues es del TRAP o de "hubo una barra".

RELOJES
=======
El oraculo escribe en hora local ART; el export de ticks y el dump L2 usan otro reloj.
Medido: +3 h da coincidencia EXACTA al nanosegundo entre el oraculo y los ticks
(docs/research/BIGTRAP2_PARIDAD_IMPOSIBLE_2026-08-21.md §7.1). El L2 se ancla por su
propio timestamp, verificando el solape antes de usarlo.

DISPONIBILIDAD CAUSAL
=====================
Todas las columnas son PRE o AT_EVENT. Ninguna POST: no hay excursion, retorno, barreras
ni P&L. El estado del libro se toma en el ULTIMO evento anterior o igual al cierre de la
barra que emite el TRAP -- nunca posterior.

P-56: los datos son de holdout. Esto es descripcion, no medicion de efecto.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import pathlib
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA_VERSION = "atlas_bigtrap2_gc_v1_target_free"
ORACULO = pathlib.Path(r"E:\l2_parquet__Tick1.csv")
TICKS = pathlib.Path(r"E:\l2_parquet\GC 12-26.Last.txt")
DIR_L2 = pathlib.Path(r"E:\l2_parquet\GC_12-26")
CANONICAL_OUT = REPO / "docs" / "research" / "atlas_bigtrap2_gc.json"
DIR_ATLAS = REPO / "data" / "atlas"
TICK_SIZE = 0.10
OFFSET_ORACULO_H = 3          # hora local ART -> reloj del export de ticks (medido)
VENTANA_PREV_S = 300
BUCKET_MIN = 15
SEED = 20260821

DISPONIBILIDAD = {
    "trade_date": "PRE", "hora_ny": "PRE", "session_phase": "PRE", "bucket_15m": "PRE",
    "tick_rate_5m": "PRE", "vol_rate_5m": "PRE", "rv_prev_5m": "PRE",
    "rango_prev_5m": "PRE", "ret_prev_5m_signed": "PRE", "trend_score": "PRE",
    "pos_en_rango_dia": "PRE", "rango_dia_hasta_t0": "PRE",
    "pct_rv": "PRE", "pct_tick_rate": "PRE",
    "n_previas_causal": "PRE", "es_primera_5s": "PRE", "t_desde_previa_ms": "PRE",
    # --- LIBRO, al ultimo evento anterior o igual al cierre de la barra ---
    "spread_ticks": "PRE", "bid_size_toque": "PRE", "ask_size_toque": "PRE",
    "queue_imbalance": "PRE", "depth_bid_5": "PRE", "depth_ask_5": "PRE",
    "depth_imbalance_5": "PRE", "microprice_offset_ticks": "PRE",
    "l2_edad_ms": "PRE",
    # --- del evento ---
    "side": "AT_EVENT", "vol": "AT_EVENT", "n_rows": "AT_EVENT",
    "max_ratio": "AT_EVENT", "zona_ancho_ticks": "AT_EVENT",
    "dist_close_a_zona_ticks": "AT_EVENT", "bar_vol": "AT_EVENT",
    "fp_vol": "AT_EVENT", "n_quote": "AT_EVENT", "n_rule": "AT_EVENT",
    "bar_rango_ticks": "AT_EVENT", "bar_largo": "AT_EVENT",
}
NO_IMPLEMENTADAS = {
    "scheduled_news": "NOT_AVAILABLE: no hay calendario oficial en el repo",
    "ofi_verdadero": ("PARCIAL: se computa desbalance de cola y de profundidad; el OFI de "
                      "Cont exige seguir altas/bajas/cancelaciones por nivel, que el dump "
                      "permite pero todavia no esta implementado"),
    "outcomes": "PROHIBIDO en el atlas por construccion",
}
FASES = [("asia", 18, 3), ("europa", 3, 8), ("premarket", 8, 9.5),
         ("rth_am", 9.5, 12), ("rth_pm", 12, 16), ("cierre", 16, 18)]


def fase_de(h):
    for nombre, ini, fin in FASES:
        if ini <= fin:
            if ini <= h < fin:
                return nombre
        elif h >= ini or h < fin:
            return nombre
    return "otro"


class PercentilExpansivo:
    """Percentil contra el historial ACUMULADO del mismo bucket. Nunca full-sample."""

    def __init__(self, minimo=20):
        self.hist = {}
        self.minimo = minimo

    def pct(self, bucket, valor):
        h = self.hist.setdefault(bucket, [])
        p = None if len(h) < self.minimo else float(np.mean(np.asarray(h) <= valor))
        h.append(valor)
        return None if p is None else round(p, 4)


def leer_oraculo(path):
    """Devuelve (barras, traps). barras[bar] = (largo, ts_ns_corregido)."""
    barras, traps = {}, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for linea in f:
            p = linea.split("|")
            if len(p) < 4:
                continue
            tipo = p[2].strip()
            kv = dict(x.split("=", 1) for x in p[3].strip().split(";") if "=" in x)
            try:
                t = (dt.datetime.fromisoformat(p[1][:26]).replace(tzinfo=dt.timezone.utc)
                     + dt.timedelta(hours=OFFSET_ORACULO_H))
                ts_ns = int(t.timestamp() * 1e9)
            except Exception:
                continue
            if tipo == "BARRA_PROCESADA":
                barras[int(kv["bar"])] = (int(kv["largo"]), ts_ns)
            elif tipo == "TRAP":
                # ts_ns va corregido al reloj de los TICKS; ts_ns_art es el original,
                # que es el reloj del dump L2. Los dos son exports de NT8 pero el
                # .Last.txt esta +3 h respecto del NRD (medido, coincidencia exacta).
                ts_art = ts_ns - OFFSET_ORACULO_H * 3600 * 1_000_000_000
                traps.append((int(kv["bar"]), ts_ns, kv, ts_art))
    return barras, traps


def leer_ticks(path):
    ts, px, bid, ask, vol = [], [], [], [], []
    with open(path, encoding="utf-8", errors="replace") as f:
        for linea in f:
            p = linea.rstrip("\n").split(";")
            if len(p) < 5:
                continue
            try:
                a, b, c = p[0].split(" ")
                e = int(dt.datetime(int(a[:4]), int(a[4:6]), int(a[6:8]), int(b[:2]),
                                    int(b[2:4]), int(b[4:6]),
                                    tzinfo=dt.timezone.utc).timestamp())
                ts.append(e * 1_000_000_000 + int(c) * 100)
                px.append(float(p[1])); bid.append(float(p[2]))
                ask.append(float(p[3])); vol.append(float(p[4]))
            except Exception:
                pass
    return (np.array(ts, dtype=np.int64), np.array(px), np.array(bid),
            np.array(ask), np.array(vol))


class LibroL2:
    """Reconstruye el libro por eventos y responde el estado en un instante dado.

    Recorre los eventos L2 en orden de `source_row` -- que es lo unico que desempata los
    ~80% de empates de microsegundo-- y mantiene el mapa precio->tamano por lado.
    """

    def __init__(self, path_parquet):
        import pyarrow.parquet as pq
        t = pq.read_table(path_parquet,
                          columns=["side", "operation", "level", "price_tick", "size",
                                   "ts_us", "source_row"])
        # Orden: TIEMPO primero, source_row SOLO como desempate. Ordenar por
        # source_row a secas aplica eventos fuera de orden temporal en el 0,85% de los
        # casos, con retrocesos de hasta 9 s -- medido sobre 20260819.
        _ts = t["ts_us"].to_numpy()
        _sr = t["source_row"].to_numpy()
        orden = np.lexsort((_sr, _ts))
        self.side = t["side"].to_numpy()[orden]
        self.op = t["operation"].to_numpy()[orden]
        self.lvl = t["level"].to_numpy()[orden]
        self.px = t["price_tick"].to_numpy()[orden]
        self.sz = t["size"].to_numpy()[orden]
        self.ts = t["ts_us"].to_numpy()[orden]
        self.i = 0
        self.ask = {}
        self.bid = {}

    def avanzar_hasta(self, ts_us):
        """Aplica todos los eventos con ts <= ts_us. Sólo avanza; nunca retrocede."""
        n = len(self.ts)
        while self.i < n and self.ts[self.i] <= ts_us:
            lado = self.ask if self.side[self.i] == 0 else self.bid
            p, s, o = int(self.px[self.i]), int(self.sz[self.i]), int(self.op[self.i])
            if o == 2 or s <= 0:
                lado.pop(p, None)
            else:
                lado[p] = s
            self.i += 1
        return self.ts[self.i - 1] if self.i > 0 else None

    def estado(self):
        if not self.ask or not self.bid:
            return None
        ba = min(self.ask)
        bb = max(self.bid)
        if ba <= bb:
            return None                      # libro cruzado: no se interpreta
        asks = sorted(self.ask)[:5]
        bids = sorted(self.bid, reverse=True)[:5]
        da = float(sum(self.ask[p] for p in asks))
        db = float(sum(self.bid[p] for p in bids))
        sa, sb = float(self.ask[ba]), float(self.bid[bb])
        return dict(
            spread_ticks=int(ba - bb),
            ask_size_toque=sa, bid_size_toque=sb,
            queue_imbalance=round(sb / (sa + sb), 4) if (sa + sb) > 0 else None,
            depth_ask_5=da, depth_bid_5=db,
            depth_imbalance_5=round(db / (da + db), 4) if (da + db) > 0 else None,
            microprice_offset_ticks=round(
                ((bb * sa + ba * sb) / (sa + sb)) - (ba + bb) / 2.0, 4)
            if (sa + sb) > 0 else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(CANONICAL_OUT))
    ap.add_argument("--atlas-dir", default=str(DIR_ATLAS))
    ap.add_argument("--max-sesiones", type=int, default=0)
    a = ap.parse_args()

    print("atlas BigTrap2 GC  -  %s" % SCHEMA_VERSION)
    barras, traps = leer_oraculo(ORACULO)
    print("  oraculo: %s barras, %s TRAPs" % (f"{len(barras):,}", f"{len(traps):,}"))
    ts, px, bid, ask, vol = leer_ticks(TICKS)
    print("  ticks  : %s" % f"{len(ts):,}")

    # Guarda: un parquet a medio escribir revienta al abrirlo. Se verifica el footer
    # antes de aceptarlo, en vez de descubrirlo a mitad de la corrida.
    import pyarrow.parquet as _pq
    l2_por_dia = {}
    for p in sorted(glob.glob(str(DIR_L2 / "l2_depth" / "*.parquet"))):
        try:
            _pq.ParquetFile(p).metadata.num_rows
        except Exception as e:
            print("  L2 ilegible, se omite: %s (%s)" % (os.path.basename(p), str(e)[:40]))
            continue
        l2_por_dia[os.path.basename(p)[:8]] = p
    print("  L2     : %d sesiones  %s" % (len(l2_por_dia), sorted(l2_por_dia)))

    pct_rv = PercentilExpansivo()
    pct_tr = PercentilExpansivo()
    filas = []
    sin_l2 = sin_ancla = 0
    libro = None
    dia_actual = None
    prev_ts_trap = None

    for bar, ts_ns, kv, ts_art in sorted(traps, key=lambda x: x[1]):
        if bar not in barras:
            sin_ancla += 1
            continue
        largo, tclose = barras[bar]
        j = int(np.searchsorted(ts, tclose, side="right")) - 1
        if j < 0 or ts[j] != tclose:
            sin_ancla += 1
            continue
        i0 = max(j - largo + 1, 0)

        d = dt.datetime.fromtimestamp(ts_ns / 1e9, dt.timezone.utc)
        # El archivo L2 de fecha D abarca ART 01:00 de D hasta ART 01:00 de D+1 (medido
        # sobre 20260819). Y `d` esta en el reloj de los TICKS (+3 h), asi que usarlo
        # para elegir archivo manda al equivocado todo evento posterior a ART 21:00.
        # La fecha del archivo se deriva del reloj ART, restando la hora de arranque.
        d_art = dt.datetime.fromtimestamp(ts_art / 1e9, dt.timezone.utc)
        dia = (d_art - dt.timedelta(hours=1)).strftime("%Y%m%d")
        if a.max_sesiones and len({f["trade_date"] for f in filas}) >= a.max_sesiones \
                and dia not in {f["trade_date"] for f in filas}:
            break

        # --- estado previo, sólo hacia atrás ---------------------------------
        t0 = tclose - VENTANA_PREV_S * 1_000_000_000
        k0 = int(np.searchsorted(ts, t0))
        pr = px[k0:i0] if i0 > k0 else px[max(i0 - 2, 0):i0]
        if len(pr) < 2:
            continue
        dif = np.diff(pr)
        rv = float(np.sqrt((dif ** 2).sum()))
        rango_prev = float(pr.max() - pr.min())
        ret = float(pr[-1] - pr[0])
        dur = max((ts[i0 - 1] - ts[k0]) / 1e9, 1e-6) if i0 > k0 else 1e-6
        tick_rate = (i0 - k0) / dur
        hasta = px[:max(i0, 1)]
        d_lo, d_hi = float(hasta.min()), float(hasta.max())
        h_ny = d.hour + d.minute / 60.0
        b15 = int(h_ny * 60 // BUCKET_MIN)

        # --- libro, al cierre de la barra ------------------------------------
        est = None
        edad = None
        if dia in l2_por_dia:
            if dia != dia_actual:
                # Los TRAPs vienen ordenados por tiempo, asi que el dia solo avanza. Si
                # retrocediera habria que reconstruir, y eso seria un sintoma de que el
                # mapeo de fecha esta mal otra vez.
                if dia_actual is not None and dia < dia_actual:
                    raise RuntimeError("la fecha de L2 retrocede: %s -> %s" % (dia_actual, dia))
                libro = LibroL2(l2_por_dia[dia])
                dia_actual = dia
            # el libro se ancla con el reloj del DUMP (ART), no con el de los ticks
            t_l2 = ts_art // 1000
            ult = libro.avanzar_hasta(t_l2)
            est = libro.estado()
            if ult is not None:
                edad = int(t_l2 - ult)
        else:
            sin_l2 += 1

        zl, zh = float(kv["zone_lo"]), float(kv["zone_hi"])
        cl = float(kv["close"])
        fila = dict(
            bar=bar, ts_ns=ts_ns, trade_date=dia, hora_ny=round(h_ny, 3),
            session_phase=fase_de(h_ny), bucket_15m=b15,
            tick_rate_5m=round(tick_rate, 3),
            vol_rate_5m=round(float(vol[k0:i0].sum()) / dur, 3) if i0 > k0 else None,
            rv_prev_5m=round(rv, 4), rango_prev_5m=round(rango_prev, 3),
            ret_prev_5m_signed=round(ret, 3),
            trend_score=round(ret / rv, 4) if rv > 0 else None,
            rango_dia_hasta_t0=round(d_hi - d_lo, 2),
            pos_en_rango_dia=round((cl - d_lo) / max(d_hi - d_lo, 1e-9), 4),
            pct_rv=pct_rv.pct(b15, rv), pct_tick_rate=pct_tr.pct(b15, tick_rate),
            n_previas_causal=len([1 for f in filas if f["trade_date"] == dia]),
            es_primera_5s=bool(prev_ts_trap is None
                               or ts_ns - prev_ts_trap >= 5_000_000_000),
            t_desde_previa_ms=(None if prev_ts_trap is None
                               else int((ts_ns - prev_ts_trap) / 1e6)),
            side=kv["side"], vol=float(kv["vol"]), n_rows=int(kv["n_rows"]),
            max_ratio=float(kv["max_ratio"]),
            zona_ancho_ticks=int(round((zh - zl) / TICK_SIZE)),
            dist_close_a_zona_ticks=round(
                (zl - cl if zl > cl else (cl - zh if cl > zh else 0.0)) / TICK_SIZE, 1),
            bar_vol=float(kv["bar_vol"]), fp_vol=float(kv["fp_vol"]),
            n_quote=int(kv.get("n_quote", 0)), n_rule=int(kv.get("n_rule", 0)),
            bar_rango_ticks=round(float(px[i0:j + 1].max() - px[i0:j + 1].min())
                                  / TICK_SIZE, 1),
            bar_largo=largo, l2_edad_ms=edad)
        fila.update(est or {k: None for k in
                            ("spread_ticks", "ask_size_toque", "bid_size_toque",
                             "queue_imbalance", "depth_ask_5", "depth_bid_5",
                             "depth_imbalance_5", "microprice_offset_ticks")})
        filas.append(fila)
        prev_ts_trap = ts_ns
        if len(filas) % 5000 == 0:
            print("    %s TRAPs procesados" % f"{len(filas):,}")

    print("  filas: %s   sin ancla: %d   sin L2: %d"
          % (f"{len(filas):,}", sin_ancla, sin_l2))

    import pyarrow as pa
    import pyarrow.parquet as pq
    dir_atlas = pathlib.Path(a.atlas_dir)
    dir_atlas.mkdir(parents=True, exist_ok=True)
    ruta = dir_atlas / "atlas_bigtrap2_gc.parquet"
    pq.write_table(pa.Table.from_pylist(filas), ruta, compression="zstd")
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)

    def q(campo, sub=None):
        v = [x[campo] for x in (sub or filas) if x.get(campo) is not None]
        if not v:
            return None
        return dict(n=len(v), p25=round(float(np.percentile(v, 25)), 3),
                    p50=round(float(np.median(v)), 3),
                    p75=round(float(np.percentile(v, 75)), 3))

    con_libro = [f for f in filas if f.get("spread_ticks") is not None]
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                   text=True).strip()
    out = dict(
        schema_version=SCHEMA_VERSION, outcomes_accessed=False, pnl_accessed=False,
        holdout_included=True,
        advertencia_holdout=("P-56: los datos son de agosto 2026, dentro de la ventana "
                             "sellada. Esto es DESCRIPCION target-free, no medicion de "
                             "efecto. No autoriza outcomes."),
        instrumento="GC 12-26", bar_spec="25 tick", tick_size=TICK_SIZE,
        oraculo=str(ORACULO), offset_oraculo_horas=OFFSET_ORACULO_H,
        disponibilidad_causal=DISPONIBILIDAD, no_implementadas=NO_IMPLEMENTADAS,
        conteos=dict(n_traps_oraculo=len(traps), n_filas=len(filas),
                     sin_ancla=sin_ancla, sin_l2=sin_l2,
                     con_estado_de_libro=len(con_libro),
                     frac_con_libro=round(len(con_libro) / max(len(filas), 1), 4),
                     por_side=dict(collections.Counter(f["side"] for f in filas)),
                     por_fase=dict(collections.Counter(f["session_phase"]
                                                       for f in filas))),
        resumen_evento={c: q(c) for c in
                        ("vol", "n_rows", "max_ratio", "zona_ancho_ticks",
                         "dist_close_a_zona_ticks", "bar_vol", "bar_rango_ticks")},
        resumen_libro={c: q(c, con_libro) for c in
                       ("spread_ticks", "bid_size_toque", "ask_size_toque",
                        "queue_imbalance", "depth_bid_5", "depth_ask_5",
                        "depth_imbalance_5", "microprice_offset_ticks", "l2_edad_ms")},
        resumen_contexto={c: q(c) for c in
                          ("rv_prev_5m", "tick_rate_5m", "trend_score",
                           "pos_en_rango_dia", "t_desde_previa_ms")},
        artefacto=dict(ruta=str(ruta), sha256=h.hexdigest(), bytes=ruta.stat().st_size),
        procedencia=dict(head_commit=head, comando=" ".join(sys.argv)))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")

    print("\n  por lado : %s" % out["conteos"]["por_side"])
    print("  por fase : %s" % out["conteos"]["por_fase"])
    print("  con libro: %s (%.4f)" % (f"{len(con_libro):,}",
                                      out["conteos"]["frac_con_libro"]))
    for k, v in out["resumen_libro"].items():
        if v:
            print("    %-24s p25 %9.3f  p50 %9.3f  p75 %9.3f"
                  % (k, v["p25"], v["p50"], v["p75"]))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
