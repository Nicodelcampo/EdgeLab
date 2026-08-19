"""C1 - Censo-superficie H-Z2A, outcome-free.

Cuenta POBLACION por celda de la grilla congelada. NO mide que paso despues: no hay
acceso, ni penetracion, ni MFE/MAE, ni P&L. La pregunta es "hay N suficiente para
testear esta celda?", y su respuesta legitima incluye "no, esta variante muere por N".

Grilla (entrada 014, congelada ANTES de correr):

    D_far in {10, 20, 40, 80}  x  delta_nm in {1, 2, 3, 5, 8}  x  R_min in {5, 10, 20}  =  60

Definiciones (v4, textuales):

  A1         entra al corredor desde d >= D_far
  near-miss  1 <= d_min <= delta_nm  Y  ningun trade dentro de [L,U] antes del giro
             Y  despues de d_min la distancia aumenta >= R_min antes de cualquier acceso
  A2         primer retorno elegible al corredor tras el rechazo, zona aun activa

Dos predicados, declarados y NO mezclados:
  trade  (PRIMARIO)     ningun trade dentro de [L,U]
  quote  (sensibilidad) ni bid ni ask alcanzan el borde

Por que este script NO llama al runner del portador: `run_avolcluster_tick_formal`
corre carreras de primer pasaje, o sea toca outcomes. La orden 019 dice que si el
runner los toca, el artefacto no entra. Se reproduce SOLO la produccion de zonas,
con las mismas primitivas (SessionProfile, detect_block, RESEARCH_DEFAULTS).

Por que trae su propio calculo de distancia: v4 exige "la distancia se calcula por
zone_id; nunca por zona mas cercana". `features.py` usa argmin sin zone_id (P-39) y
no se toca durante la medicion (orden 019). Aca la distancia es POR ZONA y en TICKS
ENTEROS, sin float.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import pathlib
import subprocess
import sys
import time

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.bars import build_footprints, build_time_bars, session_ids  # noqa: E402
from edgelab.bridge.indicators.avolclusterpoi import (  # noqa: E402
    RESEARCH_DEFAULTS, SessionProfile, detect_block)
from edgelab.bridge.ticks import TickSeries, load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns  # noqa: E402

SCHEMA_VERSION = "censo_hz2a_superficie_v2_episodio"

# --- grilla CONGELADA (entrada 014) ------------------------------------------
D_FAR = (10, 20, 40, 80)
DELTA_NM = (1, 2, 3, 5, 8)
R_MIN = (5, 10, 20)
PREDICADOS = ("trade", "quote")
PREDICADO_PRIMARIO = "trade"

# piso de potencia a nivel variante (v4, recomputado y cerrado al digito)
N_MINIMO_VARIANTE = 403

# 6E: medido sobre 5.554.201 quotes en la auditoria del 15-ago (ver P-44)
SPREAD_MEDIO_TICKS = 1.141

HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]

# Serie formal del portador: CUATRO contratos de 6E encadenados y ordenados. No es
# una eleccion nuestra -- es la misma que usa avolcluster_tick_formal.py, y hace falta
# porque SessionProfile pide lookback_sessions=20 y ningun contrato solo las tiene
# despues del firewall (6E_09-26 tiene 17).
CONTRATOS_6E = (
    ("6E_12-25_ticks.parquet", "ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336"),
    ("6E_03-26_ticks.parquet", "b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76"),
    ("6E_06-26_ticks.parquet", "124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1"),
    ("6E_09-26_ticks.parquet", "6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4"),
)


def sha256_archivo(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def blob(p):
    return subprocess.check_output(
        ["git", "-C", str(REPO), "hash-object", str(p)], text=True).strip()


def producir_zonas(bars, fps):
    """Replica la produccion de zonas del portador SIN tocar su camino de carreras.
    Mismas primitivas y mismos parametros (RESEARCH_DEFAULTS)."""
    ses = session_ids(bars.end_ns)
    prof = SessionProfile(lookback_sessions=RESEARCH_DEFAULTS["lookback_sessions"])
    zonas = []
    for s_id in np.unique(ses):
        b_idx = np.flatnonzero(ses == s_id)
        if len(b_idx) < 10:
            continue
        s_start_ns = bars.start_ns[b_idx[0]]
        for blk in range(len(b_idx) // 10):
            blk_b = b_idx[blk * 10:(blk + 1) * 10]
            cells = {}
            for b in blk_b:
                for p, v in fps.total[b].items():
                    cells[p] = cells.get(p, 0.0) + v
            min_from_open = (bars.end_ns[blk_b[-1]] - s_start_ns) // (60 * 1_000_000_000)
            bucket = min(int(min_from_open // 30), 45)
            out = detect_block(cells, prof.history_scores(bucket),
                               close_tick=int(bars.close_t[blk_b[-1]]))
            prof.add_block(bucket, out["best_score"])
            for z in out["zones"]:
                if z["kind"] != "OFF_PRICE":
                    continue
                zonas.append(dict(
                    zone_id="Z%06d" % len(zonas),
                    session_id=int(s_id),
                    creado_ns=int(bars.end_ns[blk_b[-1]]),
                    lower_tick=int(z["lower_tick"]),
                    upper_tick=int(z["upper_tick"])))
        # `commit()` al CERRAR la sesion: SessionProfile acumula en `pending` y
        # `history_scores()` lee de `history`. Sin este commit el perfil queda vacio
        # para siempre, `detect_block` abstiene por "warmup" y el censo da 0 zonas
        # sobre 4.412 bloques -- que es exactamente lo que paso en el primer intento.
        # El portador lo hace en avolcluster_tick_formal.py l. 504.
        prof.commit()
    return zonas


def recorrido_de_zona(z, ts, px, bid, ask, fin_sesion_ns):
    """Serie de distancia EN TICKS ENTEROS para UNA zona, desde su creacion hasta el
    fin de su sesion. d == 0 significa dentro de [L,U]. Por zone_id, nunca por zona
    mas cercana."""
    i0 = int(np.searchsorted(ts, z["creado_ns"], side="right"))
    i1 = int(np.searchsorted(ts, fin_sesion_ns, side="right"))
    if i1 - i0 < 2:
        return None
    L, U = z["lower_tick"], z["upper_tick"]
    p = px[i0:i1]
    d = np.where(p < L, L - p, np.where(p > U, p - U, 0)).astype(np.int64)
    b, a = bid[i0:i1], ask[i0:i1]
    toca_quote = ((b >= L) & (b <= U)) | ((a >= L) & (a <= U))
    return d, (d == 0), toca_quote


def censar_zona(d, toca_trade, toca_quote):
    """Maquina de estados A1 -> near-miss -> post-rejection -> A2, evaluada para las
    60 celdas sobre la MISMA serie.

    Outcome-free por construccion: cuenta cuantos A1 / near-miss / A2 existen. Lo que
    pasa DESPUES de A2 no se mira -- ni acceso, ni penetracion, ni nada.

    ESCANEO POR CICLOS, no por minimo global (corregido 2026-08-18, C-A). La version
    anterior tomaba `argmin` sobre TODO el corredor, y el corredor se extiende hasta
    que el precio vuelve a `d >= D_far`. Si no vuelve, un acceso posterior se
    convertia en el `d_min` y MATABA un near-miss legitimo anterior. v4 condicion 3
    dice literal que la separacion tiene que ocurrir "antes de cualquier acceso": si
    ocurrio, el near-miss existe, y lo que pase despues no lo borra.

    Lo detecto el gate de ceguera (`tests/research/test_censo_hz2a_ceguera.py`):
    truncar la serie despues del A2 cambiaba los conteos, que es justamente la
    dependencia del futuro que el censo no debe tener.
    """
    n = len(d)
    out = {}
    for D in D_FAR:
        lejos = d >= D
        entradas = np.flatnonzero(lejos[:-1] & ~lejos[1:]) + 1
        # un corredor por entrada: hasta que el precio vuelve a d >= D_far
        tramos = []
        for e in entradas:
            j = e
            while j < n and d[j] < D:
                j += 1
            tramos.append((int(e), int(j)))
        for dl in DELTA_NM:
            for R in R_MIN:
                for pr in PREDICADOS:
                    toca = toca_trade if pr == "trade" else toca_quote
                    n_a1 = n_nm = n_a2 = 0
                    for (e, j) in tramos:
                        dd = d[e:j]
                        if len(dd) == 0:
                            continue
                        tt = toca[e:j]
                        # A1 = una entrada al corredor desde d >= D_far (v4).
                        n_a1 += 1
                        i = 0
                        while i < len(dd):
                            # descender hasta el minimo local (atraviesa plateaus)
                            k = i
                            while k + 1 < len(dd) and dd[k + 1] <= dd[k]:
                                k += 1
                            d_min = int(dd[k])
                            # cond 1: 1 <= d_min <= delta
                            if not (1 <= d_min <= dl):
                                i = k + 1
                                continue
                            # cond 2: ningun toque ANTES del giro. Se mide desde la
                            # entrada al corredor, no desde el ciclo: si la zona ya
                            # fue accedida en este corredor, un giro posterior no es
                            # un near-miss en el sentido de H-Z2A.
                            if tt[:k + 1].any():
                                i = k + 1
                                continue
                            # cond 3: separacion >= R despues de d_min, ANTES de
                            # cualquier acceso
                            post, toca_post = dd[k:], tt[k:]
                            alcanza_R = np.flatnonzero(post >= d_min + R)
                            if len(alcanza_R) == 0:
                                # Este ciclo no llega a separarse. NO se abandona el
                                # corredor: un minimo POSTERIOR mas profundo tiene un
                                # umbral de separacion mas bajo (d_min' + R) y puede
                                # alcanzarlo. El `break` que habia aca --introducido
                                # con el escaneo por ciclos el 2026-08-18-- mataba
                                # esos near-miss legitimos. Es la MISMA falla que el
                                # `argmin`: un fracaso local borrando eventos validos
                                # que vienen despues.
                                i = k + 1
                                continue
                            r = k + int(alcanza_R[0])
                            primer_toque = np.flatnonzero(toca_post)
                            if len(primer_toque) and primer_toque[0] < alcanza_R[0]:
                                i = k + 1      # toco antes de separarse: no es rechazo
                                continue
                            n_nm += 1
                            # ---- P-45 (c): EPISODIO. Decision de Nico, 2026-08-18 ----
                            # Un near-miss cumplido ABRE UN EPISODIO. El acercamiento
                            # siguiente, si es el retorno, es A2 -- NO un segundo
                            # near-miss. Otro near-miss solo si, DESPUES de cerrado
                            # ese episodio, se cumplen otra vez las condiciones.
                            #
                            # Por eso no alcanza con `i = r + 1`: eso reanudaba el
                            # escaneo dentro de la misma aproximacion de vuelta, que
                            # volvia a bajar a d_min y a separarse, y el retorno se
                            # contaba como near-miss nuevo. El episodio se cierra
                            # consumiendo el retorno ENTERO: se reanuda recien cuando
                            # el precio vuelve a salir de la banda delta.
                            vuelve = np.flatnonzero(dd[r:] <= dl)
                            if len(vuelve) == 0:
                                # Sin retorno no puede haber otro near-miss: un
                                # near-miss exige d_min <= delta, o sea al menos un
                                # punto con d <= delta. Este `break` SI es seguro --
                                # a diferencia del que estaba en la rama de
                                # separacion, que abandonaba el corredor por un
                                # fracaso local y borraba eventos posteriores validos.
                                break
                            a = r + int(vuelve[0])
                            n_a2 += 1
                            sale = np.flatnonzero(dd[a:] > dl)
                            if len(sale) == 0:
                                break          # el corredor termina dentro de delta
                            i = a + int(sale[0])
                    out[(D, dl, R, pr)] = (n_a1, n_nm, n_a2)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="E:/EdgeLab/data/nt8/6E",
                    help="carpeta con los 4 contratos canonicos de 6E")
    ap.add_argument("--dias", type=int, default=None, help="smoke: recorta la carga")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    t0 = time.time()
    n_celdas = len(D_FAR) * len(DELTA_NM) * len(R_MIN)
    print("censo-superficie H-Z2A  ·  %s" % SCHEMA_VERSION)
    print("  grilla %d x %d x %d = %d celdas  ·  predicados %s (primario=%s)"
          % (len(D_FAR), len(DELTA_NM), len(R_MIN), n_celdas, PREDICADOS, PREDICADO_PRIMARIO))

    # --- serie formal: 4 contratos, verificados por sha256, ordenados -----------
    #
    # MEMORIA (2026-08-18). La version anterior sostenia simultaneamente: los 4
    # TickSeries, las 6 columnas concatenadas, el indice de orden, las 6 columnas
    # reordenadas y las 5 filtradas. Pico medido analiticamente: 3,38 GB para 17,9M
    # ticks a 48 B/tick. No fue lo que crasheo la maquina --eso fue la matriz de
    # kernels, que lee 103M filas de MNQ-- pero no hay razon para pagarlo.
    #
    # Ahora se libera a medida que se avanza: cada columna se concatena y su lista de
    # trozos se descarta en el acto, y el reorden reemplaza columna por columna. El
    # pico pasa a ser "todo lo ya hecho + una columna en transito" en vez de "dos
    # copias completas". El RESULTADO es identico por construccion: misma
    # concatenacion, mismo `argsort` estable, misma mascara.
    d_in = pathlib.Path(a.dir)
    hashes = {}
    crudo = {k: [] for k in ("ts", "px", "vol", "bid", "ask", "seq")}
    tick_size = None
    for fn, esperado in CONTRATOS_6E:
        ruta = d_in / fn
        real = sha256_archivo(ruta)
        hashes[fn] = dict(sha256=real, canonico=real == esperado)
        if real != esperado:
            print("  ABORTA: %s tiene sha256 %s, esperado %s" % (fn, real, esperado))
            return 3
        parte = load_canonical_parquet(ruta, instrument="6E")
        print("  %-26s %9d ticks  sha256 CANONICO" % (fn, len(parte.ts_ns)))
        crudo["ts"].append(parte.ts_ns)
        crudo["px"].append(parte.price_ticks)
        crudo["vol"].append(parte.volume)
        crudo["bid"].append(parte.bid_ticks)
        crudo["ask"].append(parte.ask_ticks)
        crudo["seq"].append(parte.sequence)
        tick_size = parte.tick_size
        del parte                      # el TickSeries se va; las columnas quedan

    col = {}
    for k in ("ts", "px", "vol", "bid", "ask", "seq"):
        col[k] = np.concatenate(crudo.pop(k))   # `pop` suelta los trozos en el acto
    del crudo
    gc.collect()

    orden = np.argsort(col["ts"], kind="stable")
    for k in ("ts", "px", "vol", "bid", "ask", "seq"):
        previo = col[k]
        col[k] = previo[orden]
        del previo                     # una columna en transito, no seis
    del orden
    gc.collect()

    n_bruto = len(col["ts"])
    keep = col["ts"] < FIREWALL_CUTOFF_NS
    if a.dias:
        keep = keep & (col["ts"] < int(col["ts"][0]) + a.dias * 86_400_000_000_000)
    n_fw = int(keep.sum())
    for k in ("ts", "px", "vol", "bid", "ask", "seq"):
        previo = col[k]
        col[k] = previo[keep]
        del previo
    del keep
    gc.collect()
    print("  ticks   %d brutos -> %d tras firewall (excluidos %d)"
          % (n_bruto, n_fw, n_bruto - n_fw))

    ts, px = col["ts"], col["px"]
    bid, ask = col["bid"], col["ask"]
    tkf = TickSeries(ts, px, col["vol"], bid, ask, col["seq"],
                     tick_size, "6E", "6E_FORMAL_4C")
    bars = build_time_bars(tkf, minutes=1)
    fps = build_footprints(tkf, bars)
    zonas = producir_zonas(bars, fps)
    ses_bars = session_ids(bars.end_ns)
    fin_de_sesion = {int(s): int(bars.end_ns[np.flatnonzero(ses_bars == s)[-1]])
                     for s in np.unique(ses_bars)}
    print("  barras  %d   sesiones %d   zonas del portador %d"
          % (len(bars.close_t), len(fin_de_sesion), len(zonas)))

    acc, sesiones = {}, {}
    n_usadas = 0
    for z in zonas:
        rec = recorrido_de_zona(z, ts, px, bid, ask, fin_de_sesion[z["session_id"]])
        if rec is None:
            continue
        n_usadas += 1
        d, tt, tq = rec
        for clave, (a1, nm, a2) in censar_zona(d, tt, tq).items():
            if clave not in acc:
                acc[clave] = [0, 0, 0]
                sesiones[clave] = set()
            acc[clave][0] += a1
            acc[clave][1] += nm
            acc[clave][2] += a2
            if nm:
                sesiones[clave].add(z["session_id"])

    # anillos: acumulado (delta <= X) y MARGINAL (delta == X exacto).
    #
    # ATENCION -- los anillos NO anidan, contra lo que decia este comentario y contra
    # lo que la entrada 014 asumia al pedirlos. El conjunto de EVENTOS si anida (un
    # near-miss con d_min=2 califica para todo delta >= 2), pero el conteo no, porque
    # la segmentacion es GOLOSA: con delta grande un minimo poco profundo califica
    # primero, consume el corredor hasta su punto de rechazo y saltea minimos mas
    # profundos que un delta chico si habria contado por separado. Por eso
    # `n_near_miss_marginal` puede ser NEGATIVO, y por eso cada celda publica
    # `anillo_anida` computado en vez de que el lector lo asuma.
    #
    # Que la segmentacion dependa de delta es una DECISION DE ESTIMAND que nadie tomo
    # por escrito (P-45). No se resuelve aca.
    celdas = []
    for D in D_FAR:
        for R in R_MIN:
            for pr in PREDICADOS:
                prev_nm = prev_a2 = 0
                for dl in DELTA_NM:
                    a1, nm, a2 = acc.get((D, dl, R, pr), [0, 0, 0])
                    celdas.append(dict(
                        D_far=D, delta_nm=dl, R_min=R, predicado=pr,
                        n_A1=a1, n_near_miss=nm, n_A2=a2,
                        n_near_miss_marginal=nm - prev_nm,
                        n_A2_marginal=a2 - prev_a2,
                        n_sesiones=len(sesiones.get((D, dl, R, pr), ())),
                        delta_nm_en_spreads=round(dl / SPREAD_MEDIO_TICKS, 3),
                        # La separacion exige llegar a d >= d_min + R, pero el
                        # corredor TERMINA en d >= D_far. Si d_min + R >= D_far la
                        # separacion es inobservable POR ARITMETICA, sin mirar un
                        # solo tick. delta efectivo = min(delta, D_far - R - 1).
                        # 17 de las 60 celdas de la grilla congelada (entrada 014)
                        # estan en esa condicion; 15 no pueden dar mas que cero.
                        delta_efectivo=min(dl, D - R - 1),
                        celda_degenerada=bool(dl + R >= D),
                        separacion_observable=bool(D - R - 1 >= 1),
                        anillo_anida=bool(nm >= prev_nm),
                        vive_por_N=bool(nm >= N_MINIMO_VARIANTE)))
                    prev_nm, prev_a2 = nm, a2

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]
    criticos = [f for f in sucios if f.startswith(("edgelab/", "diag/"))]

    payload = dict(
        schema_version=SCHEMA_VERSION,
        procedencia=dict(
            contratos=hashes,
            todos_canonicos=all(v["canonico"] for v in hashes.values()),
            runner_blob=blob(pathlib.Path(__file__)),
            kernel_blob=blob(REPO / "edgelab/bridge/indicators/avolclusterpoi.py"),
            head_commit=subprocess.check_output(
                ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios), sucios_criticos=sorted(criticos),
            medicion_comprometida=bool(criticos)),
        firewall=dict(
            criterio="trade_date_cme",
            primer_trade_date_holdout=HOLDOUT_FIRST_TRADE_DATE,
            cutoff_ns=int(FIREWALL_CUTOFF_NS),
            ticks_brutos=n_bruto, ticks_conservados=n_fw,
            ticks_excluidos=n_bruto - n_fw,
            ts_max_conservado_ns=int(ts[-1]),
            holdout_included=bool(ts[-1] >= FIREWALL_CUTOFF_NS)),
        outcomes_accessed=False, pnl_accessed=False,
        grilla=dict(
            D_far=list(D_FAR), delta_nm=list(DELTA_NM), R_min=list(R_MIN),
            predicados=list(PREDICADOS), predicado_primario=PREDICADO_PRIMARIO,
            n_celdas=n_celdas, N_minimo_variante=N_MINIMO_VARIANTE,
            spread_medio_ticks_6E=SPREAD_MEDIO_TICKS,
            nota_spread=("delta_nm se reporta tambien en unidades de spread (entrada "
                         "014 cond. 1): en 6E el spread es 1 tick el 89,0% del tiempo, "
                         "asi que delta_nm=1 esta SOBRE el spread, no cerca de el")),
        universo=dict(zonas_portador=len(zonas), zonas_censadas=n_usadas,
                      barras=len(bars.close_t), sesiones=len(fin_de_sesion)),
        censo=celdas,
        segundos=round(time.time() - t0, 1))

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str),
                   encoding="utf-8")

    prim = [c for c in celdas if c["predicado"] == PREDICADO_PRIMARIO]
    vivas = [c for c in prim if c["vive_por_N"]]
    print()
    print("  celdas                 %d  (primario %d)" % (len(celdas), len(prim)))
    print("  vivas por N (>= %d)    %d de %d" % (N_MINIMO_VARIANTE, len(vivas), len(prim)))
    print("  near-miss max de celda %d" % max((c["n_near_miss"] for c in prim), default=0))
    print("  holdout_included       %s" % payload["firewall"]["holdout_included"])
    print("  medicion_comprometida  %s" % payload["procedencia"]["medicion_comprometida"])
    print("  informe %s  (%.1fs)" % (out, payload["segundos"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
