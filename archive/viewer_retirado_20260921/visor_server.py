"""Backend local del visor: corre los kernels REALES del proyecto.

POR QUE HACE FALTA UN SERVIDOR, SI EL VISOR ERA ESTATICO
========================================================
La vista de gráfico y la de corredores siguen siendo estáticas: leen JSON exportado y
no necesitan nada. Pero «activar un indicador y cambiarle los parámetros» exige
**ejecutar** el indicador, y ahí sólo hay tres caminos:

1. precomputar todas las combinaciones de parámetros  -> imposible (espacio infinito)
2. reimplementar los kernels en JavaScript            -> **prohibido**: seria un segundo
   implementador del mismo objeto, que es exactamente lo que P-52 y la regla del visor
   existen para impedir. El que diverge seria el que se mira.
3. un backend local que llama a los kernels de `edgelab.bridge.indicators`

Este archivo es (3). El indicador que se dibuja **es** el que mide el research: mismo
`run()`, mismos `DEFAULTS`, mismo `PARAM_SPEC`.

QUE EXPONE
==========
    GET  /                     estaticos de viewer/hz2a/
    GET  /api/indicadores      REGISTRY + PARAM_SPEC + DEFAULTS de cada kernel
    POST /api/run              {indicador, params, instrumento, sesiones} -> zonas

El formulario de parámetros del visor **se genera desde `PARAM_SPEC`**, que es el
espacio paramétrico declarado de cada kernel (F6.1). No hay una lista de campos escrita
a mano en el HTML: si un kernel agrega un parámetro, aparece solo.

    .venv\\Scripts\\python tools\\visor_server.py            (luego abrir localhost:8777)

Target-free: dibuja zonas y eventos. Sin MAE/MFE, sin P&L. Holdout excluido.
"""
from __future__ import annotations

import argparse
import inspect
import json
import pathlib
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.bars import build_tick_bars, build_time_bars, session_ids  # noqa: E402
from edgelab.bridge.indicators import (BAR_DRIVEN, M1_DRIVEN, REGISTRY,  # noqa: E402
                                       TICK_DRIVEN)
from edgelab.bridge.ticks import TickSeries, load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns  # noqa: E402

# `aVolClusterPOI` no expone `run()` (P-40). Se consume via SessionProfile /
# detect_block, y el censo de H-Z2A YA tiene esa secuencia escrita y auditada en
# `producir_zonas`. Se IMPORTA de ahi en vez de reescribirla: el visor tiene que
# mostrar exactamente las zonas que el censo mide, no una segunda version parecida.
import importlib.util as _ilu  # noqa: E402
_spec_censo = _ilu.spec_from_file_location(
    "censo_hz2a_visor", REPO / "diag" / "tasa_senales" / "censo_hz2a_superficie.py")
_censo = _ilu.module_from_spec(_spec_censo)
_spec_censo.loader.exec_module(_censo)

# Estado de paridad, CITADO del board -- no inventado. Nico pidio ver todos los
# indicadores "aunque no este 100% la paridad": mostrarlos sin decir cual esta en
# falla seria peor que no mostrarlos.
PARIDAD = {
    "BigTrap2Absorption": ("EXACT", "Headline AbsMagnitude: GC DEC26 27.328/27.328 cubetas (100%), 365/365 zonas/fills post-burnin (100%), 26.824/26.824 umbral causal (100%), 4/4 residuales - PASS Puerta 0"),
    "aVolCellPOI2": ("FAIL", "P-42: 671 vs 678, 16 diferencias reales; causa acotada al umbral"),
    "HFTZones2": ("PARCIAL", "P-43: 6E PASS 4.821/4.821; GC 3.626/3.630 = 99,89 %, residual abierto"),
    "BigTrap2": ("EXACT", "junio 3.628/3.638 EXACT (99,73 %); abril+mayo 171/171"),
    "aVolClusterPOI": ("MEDIDA", "6E 72/72 creaciones, delta score 0 exacto; sin run() (P-40)"),
    "Gaps2": ("SIN DATO", "P-44: params no transportan entre activos (10 vs 113.298 zonas)"),
    "VolTicksPOC2": ("SIN DATO", "hay doc de cobertura; no hay veredicto reciente en el board"),
    "AACloseOpenDiffs": ("SIN DATO", "hay doc de cobertura; no hay veredicto reciente en el board"),
}

RAIZ = REPO / "viewer" / "hz2a"
HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]
BYTES_POR_TICK = 48
TECHO_GB = 2.0

_cache: dict = {}
_lock = threading.Lock()


def _dir_de(instrumento):
    base = REPO / "data" / "nt8"
    for cand in (base / instrumento, base / ("%s_parquet" % instrumento)):
        if cand.is_dir() and any(cand.glob("%s_*ticks*.parquet" % instrumento)):
            return cand
    raise FileNotFoundError("sin parquets de %s" % instrumento)


def cargar(instrumento, sesiones):
    """Ticks + barras de las ultimas N sesiones antes del firewall. Cacheado."""
    clave = (instrumento, int(sesiones))
    with _lock:
        if clave in _cache:
            return _cache[clave]
    d = _dir_de(instrumento)

    # Regla de P-25: filas x 48 B ANTES de cargar. Si pasa de 2 GB no se abre.
    import pyarrow.parquet as pq
    total = sum(pq.ParquetFile(f).metadata.num_rows
                for f in sorted(d.glob("%s_*ticks*.parquet" % instrumento)))
    gb = total * BYTES_POR_TICK / 2 ** 30
    if gb > TECHO_GB:
        raise MemoryError(
            "%s son %d filas = %.2f GB en arrays, por encima del techo de %.1f GB. "
            "No se abre: es la clase de archivo que ya crasheo la maquina (P-25)."
            % (instrumento, total, gb, TECHO_GB))

    cols = {k: [] for k in ("ts", "px", "vol", "bid", "ask", "seq")}
    tick_size = None
    for f in sorted(d.glob("%s_*ticks*.parquet" % instrumento)):
        p = load_canonical_parquet(f, instrument=instrumento)
        for k, v in (("ts", p.ts_ns), ("px", p.price_ticks), ("vol", p.volume),
                     ("bid", p.bid_ticks), ("ask", p.ask_ticks), ("seq", p.sequence)):
            cols[k].append(v)
        tick_size = p.tick_size
        del p
    for k in list(cols):
        cols[k] = np.concatenate(cols[k])
    orden = np.argsort(cols["ts"], kind="stable")
    for k in list(cols):
        cols[k] = cols[k][orden]
    keep = cols["ts"] < FIREWALL_CUTOFF_NS
    for k in list(cols):
        cols[k] = cols[k][keep]
    ses = session_ids(cols["ts"])
    sel = np.isin(ses, np.unique(ses)[-int(sesiones):])
    for k in list(cols):
        cols[k] = cols[k][sel]

    tk = TickSeries(cols["ts"], cols["px"], cols["vol"], cols["bid"], cols["ask"],
                    cols["seq"], tick_size, instrumento, "%s_VISOR" % instrumento)
    bars = build_time_bars(tk, minutes=1)
    # Los footprints se construyen UNA vez y viajan con la ventana: tres de los seis
    # kernels los piden como argumento posicional y sin ellos tiran TypeError.
    from edgelab.bridge.bars import build_footprints
    fps = build_footprints(tk, bars)
    with _lock:
        _cache[clave] = (tk, bars, fps)
    return tk, bars, fps


def catalogo():
    """REGISTRY + espacio parametrico DECLARADO de cada kernel.

    El formulario del visor se genera de aca, asi que no puede quedar desfasado de lo
    que el kernel realmente acepta.
    """
    out = {}
    for nombre, mod in sorted(REGISTRY.items()):
        spec = getattr(mod, "PARAM_SPEC", None)
        out[nombre] = dict(
            disponible=bool(spec) and hasattr(mod, "run"),
            driven=("tick" if nombre in TICK_DRIVEN else
                    "bar" if nombre in BAR_DRIVEN else
                    "m1" if nombre in M1_DRIVEN else "?"),
            defaults=getattr(mod, "DEFAULTS", {}),
            paridad=PARIDAD.get(nombre, ("SIN DATO", ""))[0],
            paridad_nota=PARIDAD.get(nombre, ("", ""))[1],
            doc_paridad=("docs/parity_coverage/%s.md" % nombre
                         if (REPO / "docs" / "parity_coverage" / ("%s.md" % nombre)).exists()
                         else None),
            params=spec or {})
    # `aVolClusterPOI` no esta en REGISTRY y no expone `run()` (P-40), pero SI se puede
    # dibujar: el censo de H-Z2A produce sus zonas con SessionProfile / detect_block, y
    # esa funcion se importa tal cual. Sus parametros salen de RESEARCH_DEFAULTS, que es
    # lo unico declarado que tiene -- no hay PARAM_SPEC que generar.
    from edgelab.bridge.indicators.avolclusterpoi import RESEARCH_DEFAULTS
    out["aVolClusterPOI"] = dict(
        disponible=True, driven="bar",
        defaults=dict(RESEARCH_DEFAULTS),
        paridad=PARIDAD["aVolClusterPOI"][0], paridad_nota=PARIDAD["aVolClusterPOI"][1],
        doc_paridad=None,
        params={k: {"type": ("int" if isinstance(v, int) and not isinstance(v, bool)
                             else "float" if isinstance(v, float)
                             else "bool" if isinstance(v, bool) else "str"),
                    "default": v, "class": "recompute",
                    "branches": ["research_defaults"]}
                for k, v in RESEARCH_DEFAULTS.items()},
        motivo=("no expone run() ni PARAM_SPEC (P-40). Se dibuja con la MISMA "
                "`producir_zonas` que usa el censo de H-Z2A; los parametros salen de "
                "RESEARCH_DEFAULTS, lo unico declarado que tiene."))
    return out


def correr_avolcluster(tk, bars, fps, params):
    """Zonas de `aVolClusterPOI` con la funcion del censo, no con una copia."""
    zonas = _censo.producir_zonas(bars, fps)
    ts_ = tk.tick_size
    return [dict(id=z["zone_id"],
                 top=z["upper_tick"] * ts_, bottom=z["lower_tick"] * ts_,
                 top_t=int(z["upper_tick"]), bottom_t=int(z["lower_tick"]),
                 created_ms=int(z["creado_ns"] // 1_000_000), ended_ms=None,
                 state="ACTIVE", kind="off_price")
            for z in zonas]


def aviso_de_warmup(params, sesiones):
    """Un 0 puede ser 'no hay nada' o 'no alcanzaste el warmup'. Son cosas distintas y
    el visor tiene que distinguirlas, o cada indicador mal configurado parece roto.

    El chequeo NO adivina: lee el propio parametro declarado del kernel.
    """
    lb = params.get("lookback_sessions")
    if lb and sesiones < int(lb):
        return ("este indicador declara lookback_sessions=%d y se cargaron %d sesiones: "
                "el perfil no llega a formarse y por eso no crea zonas. Subi las "
                "sesiones a >= %d." % (int(lb), sesiones, int(lb)))
    ms = params.get("min_sessions") or params.get("min_calib_samples")
    if params.get("min_sessions") and sesiones < int(params["min_sessions"]):
        return ("min_sessions=%s y se cargaron %d sesiones."
                % (params["min_sessions"], sesiones))
    return None


def correr(cuerpo):
    nombre = cuerpo["indicador"]
    sesiones = int(cuerpo.get("sesiones", 2))
    tk, bars, fps = cargar(cuerpo.get("instrumento", "6E"), sesiones)
    if nombre == "aVolClusterPOI":
        from edgelab.bridge.indicators.avolclusterpoi import RESEARCH_DEFAULTS
        pp = {**RESEARCH_DEFAULTS, **(cuerpo.get("params") or {})}
        zonas = correr_avolcluster(tk, bars, fps, pp)
        return dict(indicador=nombre, n_zonas=len(zonas), n_eventos=0,
                    aviso=aviso_de_warmup(pp, sesiones),
                    params_line="# aVolClusterPOI via producir_zonas del censo H-Z2A",
                    tick_size=tk.tick_size, zonas=zonas,
                    outcomes_accessed=False, pnl_accessed=False)
    mod = REGISTRY.get(nombre)
    if mod is None or not hasattr(mod, "run"):
        raise ValueError("indicador '%s' no esta en el REGISTRY o no expone run()" % nombre)
    params = {**getattr(mod, "DEFAULTS", {}), **(cuerpo.get("params") or {})}
    # QUE ARGUMENTOS PIDE, LEIDO DE LA FIRMA -- no de una lista escrita a mano.
    # `bigtrap2`, `avolcellpoi2` y `voltickspoc2` declaran `run(ticks, bars, footprints,
    # ...)`; los otros tres, `run(ticks, bars, ...)`. Llamarlos a todos igual producia
    # "TypeError: run() missing 1 required positional argument: 'footprints'", que es el
    # error que Nico vio en pantalla. Con `inspect` un kernel nuevo funciona solo.
    posicionales = [n for n, prm in inspect.signature(mod.run).parameters.items()
                    if prm.kind in (prm.POSITIONAL_ONLY, prm.POSITIONAL_OR_KEYWORD)
                    and prm.default is prm.empty]
    args = [tk, bars] + ([fps] if "footprints" in posicionales else [])
    res = mod.run(*args, params=params, chart_tz=cuerpo.get("chart_tz", "UTC"))
    # Los kernels devuelven `top`/`bottom` en PRECIO. El chart trabaja en TICKS
    # ENTEROS. La conversion se hace ACA y no en la pagina: las unidades son
    # exactamente donde se cuelan los errores, y el servidor es el unico lado que
    # conoce el `tick_size` del instrumento sin adivinarlo.
    ts_ = tk.tick_size
    a_ticks = lambda v: None if v is None else int(round(v / ts_))
    zonas = [dict(id=z.get("id"),
                  top=z.get("top"), bottom=z.get("bottom"),
                  top_t=a_ticks(z.get("top")), bottom_t=a_ticks(z.get("bottom")),
                  created_ms=z.get("created_ms"), ended_ms=z.get("ended_ms"),
                  state=z.get("state"), kind=z.get("kind"))
             for z in (res.get("zones") or [])]
    return dict(indicador=nombre, n_zonas=len(zonas),
                n_eventos=len(res.get("events") or []),
                aviso=aviso_de_warmup(params, sesiones),
                params_line=res.get("params_line", ""),
                tick_size=tk.tick_size, zonas=zonas,
                outcomes_accessed=False, pnl_accessed=False)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(RAIZ), **k)

    def log_message(self, *a):
        pass

    def _json(self, codigo, payload):
        b = json.dumps(payload).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/api/indicadores"):
            try:
                self._json(200, dict(ok=True, indicadores=catalogo()))
            except Exception as e:                      # noqa: BLE001
                self._json(500, dict(ok=False, error=str(e)))
            return
        super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/api/run"):
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            cuerpo = json.loads(self.rfile.read(n) or b"{}")
            self._json(200, dict(ok=True, **correr(cuerpo)))
        except MemoryError as e:
            self._json(413, dict(ok=False, error=str(e)))
        except Exception as e:                          # noqa: BLE001
            self._json(500, dict(ok=False, error="%s: %s" % (type(e).__name__, e)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8777)
    a = ap.parse_args()
    print("visor con indicadores  ->  http://127.0.0.1:%d" % a.port)
    print("  kernels disponibles: %s" % ", ".join(sorted(REGISTRY)))
    print("  los indicadores se ejecutan con el MISMO run() que usa el research")
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
