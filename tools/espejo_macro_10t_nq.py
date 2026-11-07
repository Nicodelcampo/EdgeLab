"""Candidatos a espejo en velas de 10 ticks de NQ, para clasificar a ojo.

Lee el cache local de nicolasbuttaro/edgelab-ticks-nq-preholdout. No toca el
holdout sellado. Una sesión CME y, si el roll cae ese día en dos archivos, el
contrato con más trades. Las velas del candidato llegan hasta el cierre que
deshizo el 50 %; lo de después no se guarda.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.kaggle.sessions_cme import is_maintenance_break, trade_date_ymd
from edgelab.research.espejo_macro_10t import (
    MITAD, RETRO_MARCADO, TICKS_POR_VELA, VIAJES_EN_LO_QUE_FALTA, ancho_minimo_ticks,
    detectar, velas_de_ticks,
)

MIN_W = float(ancho_minimo_ticks("NQ"))
# El mismo ritmo que el piso chico (unos 10 ticks de avance por vela), para que
# una zona ancha no sea un latigazo de ocho velas.
MIN_BARRAS_IDA = max(8, int(np.ceil(MIN_W / TICKS_POR_VELA)))
MIN_BARRAS_VUELTA = max(4, int(np.ceil(0.5 * MIN_W / TICKS_POR_VELA)))
MAX_BARRAS_IDA = 2500

CACHE = Path.home() / ".cache" / "edgelab-ticks" / "nq"
ARCHIVOS = ("NQ_06-26_ticks.parquet", "NQ_09-26_ticks.parquet")
DESDE = 20260401
HASTA = 20260630
HOLDOUT = 20261001
TICK = 0.25
CONTEXTO = 20
NS0 = int(datetime(2026, 3, 31, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
NS1 = int(datetime(2026, 7, 2, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
OUT = Path(__file__).resolve().parents[1] / "viewer" / "nt8_bridge" / "bundles" / "espejo_macro_10t_nq.json"
RECIBO = Path(__file__).resolve().parents[1] / "docs" / "research" / "espejo_macro_10t_20261107" / "recibo.json"


def _trades(path: Path):
    pf = pq.ParquetFile(path)
    for i in range(pf.metadata.num_row_groups):
        col = pf.metadata.row_group(i).column(0)
        if col.statistics is not None and (col.statistics.max < NS0 or col.statistics.min >= NS1):
            continue
        for batch in pf.iter_batches(batch_size=1_000_000, row_groups=[i],
                                     columns=["ts_utc_ns", "price_ticks", "volume", "tick_type"]):
            m = pc.equal(batch.column("tick_type"), "trade").to_numpy(zero_copy_only=False)
            if not m.any():
                continue
            ts = batch.column("ts_utc_ns").to_numpy(zero_copy_only=False)[m]
            vivo = ~is_maintenance_break(ts)
            if not vivo.any():
                continue
            ts = ts[vivo]
            ymd = trade_date_ymd(ts)
            queda = (ymd >= DESDE) & (ymd <= HASTA) & (ymd < HOLDOUT)
            if not queda.any():
                continue
            px = batch.column("price_ticks").to_numpy(zero_copy_only=False)[m][vivo][queda]
            vol = batch.column("volume").to_numpy(zero_copy_only=False)[m][vivo][queda]
            yield ts[queda], px, vol, ymd[queda]


def _sesiones(path: Path):
    dia = None
    trozos = []

    def cerrar():
        if dia is None or not trozos:
            return None
        ts = np.concatenate([t[0] for t in trozos])
        px = np.concatenate([t[1] for t in trozos])
        vol = np.concatenate([t[2] for t in trozos])
        orden = np.argsort(ts, kind="mergesort")
        return dia, int(len(ts)), ts[orden], px[orden], vol[orden]

    for ts, px, vol, ymd in _trades(path):
        cortes = np.r_[0, np.flatnonzero(ymd[1:] != ymd[:-1]) + 1, len(ymd)]
        for a, b in zip(cortes[:-1], cortes[1:]):
            d = int(ymd[a])
            if dia is None:
                dia = d
            if d != dia:
                hecho = cerrar()
                if hecho is not None:
                    yield hecho
                dia = d
                trozos = []
            trozos.append((ts[a:b], px[a:b], vol[a:b]))
    hecho = cerrar()
    if hecho is not None:
        yield hecho


def _item(ymd: int, contrato: str, n: int, ts, px, vol, min_w, min_ida, min_vuelta, max_ida) -> list:
    o, h, lo, c, v = velas_de_ticks(px, vol, TICKS_POR_VELA)
    if len(c) < min_ida + min_vuelta:
        return []
    m = len(c)
    print(f"    {ymd} {m} velas de 10 ticks", flush=True)
    fin = ts[:m * TICKS_POR_VELA].reshape(m, TICKS_POR_VELA)[:, -1]
    items = []
    for j, cand in enumerate(detectar(c, min_w=min_w, min_ida=min_ida, min_vuelta=min_vuelta, max_ida=max_ida)):
        i0, iext, k = cand["i0"], cand["iext"], cand["k"]
        a = max(0, i0 - CONTEXTO)
        velas = []
        for t in range(a, k + 1):
            velas.append({
                "time": t - a + 1,
                "open": round(float(o[t]) * TICK, 2),
                "high": round(float(h[t]) * TICK, 2),
                "low": round(float(lo[t]) * TICK, 2),
                "close": round(float(c[t]) * TICK, 2),
            })
        items.append({
            "id": f"{ymd}-{contrato}-{j}",
            "sesion": ymd,
            "contrato": contrato,
            "lado": int(cand["lado"]),
            "A": round(float(cand["A"]) * TICK, 2),
            "B": round(float(cand["B"]) * TICK, 2),
            "W_ticks": round(float(cand["W"]), 1),
            "i0": i0 - a,
            "iext": iext - a,
            "k": k - a,
            "barras_ida": int(iext - i0 + 1),
            "barras_vuelta": int(k - iext),
            "ts_senal_utc": datetime.fromtimestamp(int(fin[k]) / 1e9, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "candles": velas,
        })
    return items


def main() -> None:
    print(f"ancho minimo {MIN_W:.0f} ticks ({MIN_W * TICK:.2f} puntos), ida>={MIN_BARRAS_IDA} velas", flush=True)
    mejores: dict[int, dict] = {}
    for nombre in ARCHIVOS:
        path = CACHE / nombre
        contrato = nombre.split("_ticks")[0].replace("_", " ")
        print(f"leyendo {nombre}", flush=True)
        for ymd, n, ts, px, vol in _sesiones(path):
            previo = mejores.get(ymd)
            if previo is not None and previo["trades"] >= n:
                print(f"  {ymd} {contrato} {n} trades, se queda el otro contrato", flush=True)
                continue
            items = _item(ymd, contrato, n, ts, px, vol, MIN_W, MIN_BARRAS_IDA, MIN_BARRAS_VUELTA, MAX_BARRAS_IDA)
            mejores[ymd] = {"trades": n, "contrato": contrato, "items": items}
            print(f"  {ymd} {contrato} trades {n} candidatos {len(items)}", flush=True)
    dias = sorted(mejores)
    items = [it for d in dias for it in mejores[d]["items"]]
    doc = {
        "schema": "EDGELAB_ESPEJO_MACRO_10T_V1",
        "instrumento": "NQ",
        "tick": TICK,
        "ticks_por_vela": TICKS_POR_VELA,
        "retro_marcado": RETRO_MARCADO,
        "mitad": MITAD,
        "min_w_ticks": MIN_W,
        "min_w_puntos": round(MIN_W * TICK, 2),
        "viajes_severos_en_lo_que_falta": VIAJES_EN_LO_QUE_FALTA,
        "min_barras_ida": MIN_BARRAS_IDA,
        "min_barras_vuelta": MIN_BARRAS_VUELTA,
        "max_barras_ida": MAX_BARRAS_IDA,
        "ventana": [DESDE, HASTA],
        "holdout_desde": HOLDOUT,
        "sesiones": len(dias),
        "nota": "Las velas terminan en el cierre que deshizo el 50 % del impulso. Lo posterior no está.",
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    recibo = {k: doc[k] for k in doc if k != "items"}
    recibo.update({
        "n_candidatos": len(items),
        "por_contrato": {nombre: sum(1 for d in dias if mejores[d]["contrato"] == nombre) for nombre in {mejores[d]["contrato"] for d in dias}},
        "por_lado": {"compra": sum(1 for it in items if it["lado"] == 1), "venta": sum(1 for it in items if it["lado"] == -1)},
        "paquete": str(OUT),
        "bytes": OUT.stat().st_size,
    })
    RECIBO.parent.mkdir(parents=True, exist_ok=True)
    RECIBO.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"candidatos {len(items)} sesiones {len(dias)} -> {OUT} ({OUT.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    main()
