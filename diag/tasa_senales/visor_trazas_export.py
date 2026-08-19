"""Exporta 3 corredores reales de 6E para el visor de los DOS ROLES de delta.

POR QUE ASI. La regla del visor es que NO puede re-implementar la logica: si la pagina
calcula la clasificacion por su cuenta, tenemos un segundo implementador que puede
diverger, y el que diverge es justo el que Nico mira.

Este exportador no reimplementa nada y tampoco toca `censar_zona`. Deriva las marcas
de la propia funcion, corriendola sobre PREFIJOS crecientes de la serie: el indice
donde un conteo se incrementa es el indice donde ese evento se completa.

Eso es legitimo porque el gate C-A ya prueba la propiedad que lo sostiene --apendear
datos nunca baja un conteo (`test_apendear_datos_NUNCA_baja_un_conteo`)-- asi que la
secuencia de conteos sobre prefijos es no decreciente y sus saltos son eventos.

El visor queda construido SOBRE la propiedad que el gate demuestra, en vez de sobre
una copia de la logica.

Target-free: solo geometria. No mira acceso, penetracion, MAE/MFE ni P&L.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location(
    "censo_hz2a", pathlib.Path(__file__).with_name("censo_hz2a_superficie.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

from edgelab.bridge.bars import build_footprints, build_time_bars, session_ids  # noqa: E402
from edgelab.bridge.ticks import TickSeries, load_canonical_parquet  # noqa: E402

D_FAR, R = 10, 5
DELTAS = (3, 8)          # los dos que exhiben el doble rol
MAX_PUNTOS = 700         # corredores mas largos se descartan para que el visor se lea


def marcas(d, toca, dl):
    """Indices donde se completa cada near-miss y cada A2, derivados de `censar_zona`
    sobre prefijos. No se replica la maquina de estados."""
    clave = (D_FAR, dl, R, "trade")
    nm_prev = a2_prev = 0
    nm_en, a2_en = [], []
    for k in range(2, len(d) + 1):
        a1, nm, a2 = C.censar_zona(d[:k], toca[:k], toca[:k].copy())[clave]
        if nm > nm_prev:
            nm_en += [k - 1] * (nm - nm_prev)
            nm_prev = nm
        if a2 > a2_prev:
            a2_en += [k - 1] * (a2 - a2_prev)
            a2_prev = a2
    return dict(delta=dl, near_miss=nm_en, a2=a2_en, n_nm=nm_prev, n_a2=a2_prev)


def main():
    d_in = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "E:/EdgeLab/data/nt8/6E")
    col = {k: [] for k in ("ts", "px", "vol", "bid", "ask", "seq")}
    tick_size = None
    for fn, esperado in C.CONTRATOS_6E:
        real = C.sha256_archivo(d_in / fn)
        assert real == esperado, "%s no es canonico" % fn
        p = load_canonical_parquet(d_in / fn, instrument="6E")
        for k, v in (("ts", p.ts_ns), ("px", p.price_ticks), ("vol", p.volume),
                     ("bid", p.bid_ticks), ("ask", p.ask_ticks), ("seq", p.sequence)):
            col[k].append(v)
        tick_size = p.tick_size
        del p
    for k in list(col):
        col[k] = np.concatenate(col[k])
    orden = np.argsort(col["ts"], kind="stable")
    keep_all = col["ts"][orden] < C.FIREWALL_CUTOFF_NS
    for k in list(col):
        col[k] = col[k][orden][keep_all]

    tkf = TickSeries(col["ts"], col["px"], col["vol"], col["bid"], col["ask"],
                     col["seq"], tick_size, "6E", "6E_FORMAL_4C")
    bars = build_time_bars(tkf, minutes=1)
    fps = build_footprints(tkf, bars)
    zonas = C.producir_zonas(bars, fps)
    ses = session_ids(bars.end_ns)
    fin = {int(s): int(bars.end_ns[np.flatnonzero(ses == s)[-1]])
           for s in np.unique(ses)}
    print("zonas del portador: %d" % len(zonas))

    elegidos = []
    for z in zonas:
        rec = C.recorrido_de_zona(z, col["ts"], col["px"], col["bid"], col["ask"],
                                  fin[z["session_id"]])
        if rec is None:
            continue
        d, tt, _ = rec
        lejos = d >= D_FAR
        ent = np.flatnonzero(lejos[:-1] & ~lejos[1:]) + 1
        for e in ent:
            j = e
            while j < len(d) and d[j] < D_FAR:
                j += 1
            if not (40 <= j - e <= MAX_PUNTOS):
                continue
            dd, ttt = d[e:j].copy(), tt[e:j].copy()
            m = [marcas(dd, ttt, dl) for dl in DELTAS]
            # se busca el contraste: los dos roles se ven cuando delta ancho da MENOS
            if m[1]["n_nm"] < m[0]["n_nm"] and m[0]["n_nm"] >= 1:
                elegidos.append(dict(zone_id=z["zone_id"], session_id=z["session_id"],
                                     lower_tick=z["lower_tick"], upper_tick=z["upper_tick"],
                                     d=[int(x) for x in dd],
                                     toca=[bool(x) for x in ttt], marcas=m))
                print("  corredor %s  n=%d  nm(d=3)=%d  nm(d=8)=%d"
                      % (z["zone_id"], len(dd), m[0]["n_nm"], m[1]["n_nm"]))
                break
        if len(elegidos) == 3:
            break

    out = dict(schema="visor_trazas_delta_v1", D_far=D_FAR, R_min=R, deltas=list(DELTAS),
               instrumento="6E", predicado="trade",
               runner_blob=C.blob(pathlib.Path(__file__).with_name("censo_hz2a_superficie.py")),
               outcomes_accessed=False, pnl_accessed=False,
               nota="marcas derivadas de censar_zona sobre prefijos; sin reimplementar",
               corredores=elegidos)
    destino = REPO / "runs" / "visor_trazas_delta.json"
    destino.write_text(json.dumps(out), encoding="utf-8")
    print("escrito %s  (%d corredores)" % (destino, len(elegidos)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
