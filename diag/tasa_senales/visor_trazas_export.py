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
# El par correcto es (5, 8), NO (3, 8). En el artefacto v2, D=10 R=5 da
# [438, 914, 1463, 2091, 1991] para delta = 1,2,3,5,8: el conteo BAJA recien entre
# 5 y 8. Con delta=3 sube, asi que ese par no exhibe el doble rol -- primer intento
# de este exportador eligio (3,8) por "angosto vs ancho" y devolvio 0 corredores.
DELTAS = (5, 8)
# La serie de distancia es POR TICK, no por barra: un corredor puede tener decenas de
# miles de puntos. El primer intento capaba en 700 y descarto los 575 corredores sin
# que ninguno pudiera calificar. Los limites de abajo estan puestos por COSTO, no por
# estetica, y el exportador publica la distribucion real para que se vean.
MIN_PUNTOS = 40
MAX_PUNTOS = 4000        # censar_zona es O(n x 120) en Python puro
MAX_CANDIDATOS = 900     # cuantos corredores se evaluan antes de rankear
N_CORREDORES = 12        # 3-20 en un JSON chico, no 575 zonas


def _cuenta(d, toca, dl, k=None):
    """Conteo (nm, a2) sobre el prefijo de largo k."""
    if k is None:
        k = len(d)
    _, nm, a2 = C.censar_zona(d[:k], toca[:k], toca[:k].copy())[(D_FAR, dl, R, "trade")]
    return nm, a2


def marcas(d, toca, dl):
    """Indices donde se completa cada near-miss y cada A2, derivados de `censar_zona`.

    BUSQUEDA BINARIA, no barrido. El gate C-A prueba que apendear datos nunca baja un
    conteo, o sea que `conteo(prefijo)` es NO DECRECIENTE en el largo del prefijo. Eso
    habilita bisectar: el indice del k-esimo evento es el prefijo mas corto cuyo conteo
    llega a k. Son ~log2(n) llamadas por evento en vez de n.

    El barrido lineal era inviable: la serie es por tick y `censar_zona` es O(n x 120)
    en Python puro."""
    n = len(d)
    nm_tot, a2_tot = _cuenta(d, toca, dl)

    def primer_prefijo(objetivo, cual):
        lo, hi = 2, n
        while lo < hi:
            mid = (lo + hi) // 2
            if _cuenta(d, toca, dl, mid)[cual] >= objetivo:
                hi = mid
            else:
                lo = mid + 1
        return lo - 1

    return dict(delta=dl,
                near_miss=[primer_prefijo(k, 0) for k in range(1, nm_tot + 1)],
                a2=[primer_prefijo(k, 1) for k in range(1, a2_tot + 1)],
                n_nm=nm_tot, n_a2=a2_tot)


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

    # --- 1) enumerar corredores y publicar su distribucion REAL de largo ----------
    corredores = []
    for z in zonas:
        rec = C.recorrido_de_zona(z, col["ts"], col["px"], col["bid"], col["ask"],
                                  fin[z["session_id"]])
        if rec is None:
            continue
        d, tt, _ = rec
        lejos = d >= D_FAR
        for e in np.flatnonzero(lejos[:-1] & ~lejos[1:]) + 1:
            j = e
            while j < len(d) and d[j] < D_FAR:
                j += 1
            # La rebanada arranca en e-1, NO en e. `censar_zona` DETECTA el corredor
            # por su cuenta: busca la transicion de `d >= D_far` a `d < D_far`. Una
            # rebanada que empieza YA ADENTRO no tiene esa transicion, asi que no
            # produce A1 y no puede producir ningun near-miss: cero por construccion.
            #
            # Este era el bug de fondo de los tres "0 corredores" del 2026-08-19. Los
            # otros dos diagnosticos --el par (3,8) y el filtro por largo-- eran ciertos
            # pero secundarios: aunque los hubiera acertado, el resultado habria sido 0
            # igual.
            corredores.append((int(j - e), z, int(max(e - 1, 0)), int(j), d, tt))
    largos = np.array([c[0] for c in corredores])
    print("corredores D_far=%d: %d" % (D_FAR, len(largos)))
    print("  largo en TICKS  min %d  p25 %d  mediana %d  p75 %d  p95 %d  max %d"
          % (largos.min(), np.percentile(largos, 25), np.median(largos),
             np.percentile(largos, 75), np.percentile(largos, 95), largos.max()))

    # --- 2) SELECCION POR EVENTO, no por largo -----------------------------------
    #
    # Los dos intentos anteriores filtraron por largo y devolvieron 0 corredores. La
    # razon es que los near-miss son RAROS: 1.463 sobre 142.023 corredores, ~1%.
    # Elegir "los 200 mas cortos de tal ventana" es sortear 200 y esperar 2 eventos.
    #
    # Prefiltro barato en numpy antes de gastar `censar_zona` (que es O(n x 120) en
    # Python puro): un near-miss exige un minimo <= delta_max y una separacion posterior
    # de al menos R. Eso descarta la enorme mayoria --la mediana de corredor son 7
    # ticks-- sin evaluar nada.
    aptos = []
    for (ln, z, e, j, d, tt) in corredores:
        if not (MIN_PUNTOS <= ln <= MAX_PUNTOS):
            continue
        dd = d[e:j]
        if dd[0] < D_FAR:          # sin la barra de entrada no hay A1 posible
            continue
        if dd[1:].min() > max(DELTAS) or (dd.max() - dd[1:].min()) < R:
            continue
        aptos.append((ln, z, e, j, d, tt))
    print("  con largo en [%d, %d] y minimo <= %d: %d"
          % (MIN_PUNTOS, MAX_PUNTOS, max(DELTAS), len(aptos)))

    puntuados = []
    for (ln, z, e, j, d, tt) in aptos[:MAX_CANDIDATOS]:
        dd, ttt = d[e:j].copy(), tt[e:j].copy()
        n5 = _cuenta(dd, ttt, DELTAS[0])[0]
        n8 = _cuenta(dd, ttt, DELTAS[1])[0]
        if n5 == 0 and n8 == 0:
            continue
        puntuados.append((n5 - n8, n5, n8, z, dd, ttt))
    baja = sum(1 for p in puntuados if p[0] > 0)
    print("  evaluados %d  con eventos %d  con delta=8 MENOR que delta=5: %d"
          % (min(len(aptos), MAX_CANDIDATOS), len(puntuados), baja))

    # se prefiere el contraste que exhibe el doble rol (delta ancho da MENOS), y si no
    # hay, se toman los de mas eventos -- diciendolo, no en silencio
    puntuados.sort(key=lambda p: (-p[0], -p[1]))
    elegidos = []
    for (dif, n5, n8, z, dd, ttt) in puntuados[:N_CORREDORES]:
        m = [marcas(dd, ttt, dl) for dl in DELTAS]
        elegidos.append(dict(zone_id=z["zone_id"], session_id=z["session_id"],
                             lower_tick=z["lower_tick"], upper_tick=z["upper_tick"],
                             contraste=int(dif),
                             d=[int(x) for x in dd], toca=[bool(x) for x in ttt],
                             marcas=m))
        print("  %s  n=%4d  nm(d=5)=%d  nm(d=8)=%d  contraste %+d"
              % (z["zone_id"], len(dd), m[0]["n_nm"], m[1]["n_nm"], dif))

    out = dict(schema="visor_trazas_delta_v1", D_far=D_FAR, R_min=R, deltas=list(DELTAS),
               instrumento="6E", predicado="trade",
               runner_blob=C.blob(pathlib.Path(__file__).with_name("censo_hz2a_superficie.py")),
               outcomes_accessed=False, pnl_accessed=False,
               nota="marcas derivadas de censar_zona sobre prefijos; sin reimplementar",
               corredores=elegidos)
    destino = REPO / "viewer" / "hz2a" / "trazas.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(out), encoding="utf-8")
    if not elegidos:
        print("  NINGUN corredor cumple el filtro. El visor debe mostrar empty state,")
        print("  no un spinner: el JSON se escribe igual, con `corredores: []`.")
    print("escrito %s  (%d corredores)" % (destino, len(elegidos)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
