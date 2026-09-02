"""Driver de paridad kernel Python <-> oraculo NT8, para un indicador y un contrato.

Existia la API (`edgelab.bridge.parity.match_zones`) y existia un consumidor
(`tools/build_viewer.py`), pero no habia forma de correr UNA paridad desde la linea
de comandos sin pasar por el store. Esto es esa forma.

Que hace, en orden:

  1. Verifica identidad: sha256 del oraculo y del parquet, blob del `.cs` y del kernel.
     Todo va al informe -- una paridad sin procedencia no es evidencia.
  2. Carga ticks del parquet canonico, arma barras y footprints.
  3. Corre el kernel Python.
  4. Parsea el oraculo NT8 (`oracle.parse_nt8_log`, tz del chart declarada).
  5. Recorta AMBOS lados a la ventana comun y aplica el requisito del contrato de
     paridad §5: la ventana arranca en borde de sesion con al menos una sesion
     completa previa, para que exista calibracion congelada antes de las
     detecciones comparadas.
  6. `parity.match_zones` con frontera de madurez.

Lo que NO hace: no adjudica, no promueve, no escribe al store. Emite un informe
JSON y un veredicto. La etiqueta formal la decide quien lea el informe.

Uso:
    python tools/paridad_oraculo.py --indicador hftzones2 \
        --oraculo data/nt8_oracles/hftzones2_v23_6E_0626_time1_100d.csv.gz \
        --parquet E:/EdgeLab/data/nt8_research_v2/6E/6E_06-26_ticks.parquet \
        --chart-tz America/Argentina/Buenos_Aires \
        --out runs/paridad_hftzones2.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge import bars as bars_mod  # noqa: E402
from edgelab.bridge import oracle, parity  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402

# indicador -> (modulo del kernel, .cs canonico, si el kernel pide footprints)
KERNELS = {
    "hftzones2": ("edgelab.bridge.indicators.hftzones2", "nt8/HFTZones2.cs", False),
    "avolcellpoi2": ("edgelab.bridge.indicators.avolcellpoi2", "nt8/aVolCellPOI2.cs", True),
    "bigtrap2": ("edgelab.bridge.indicators.bigtrap2", "nt8/BigTrap2.cs", True),
    "gaps2": ("edgelab.bridge.indicators.gaps2", "nt8/Gaps2.cs", False),
    "voltickspoc2": ("edgelab.bridge.indicators.voltickspoc2", "nt8/VolTicksPOC2.cs", True),
    "aacloseopendiffs": ("edgelab.bridge.indicators.aacloseopendiffs", "nt8/AACloseOpenDiffs.cs", False),
    "avolclusterpoi": ("edgelab.bridge.indicators.avolclusterpoi", "nt8/aVolClusterPOI.cs", True),
}


def sha256_archivo(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def blob_git(p):
    out = subprocess.check_output(["git", "-C", str(REPO), "hash-object", str(p)], text=True)
    return out.strip()


def leer_oraculo(p):
    """Acepta `.csv` y `.csv.gz`. El .gz se descomprime en memoria: el archivo del
    repo es la evidencia y no se materializa una copia sin sellar al lado."""
    p = pathlib.Path(p)
    crudo = p.read_bytes()
    if p.suffix == ".gz":
        texto = gzip.decompress(crudo).decode("utf-8-sig", errors="replace")
    else:
        texto = crudo.decode("utf-8-sig", errors="replace")
    return crudo, texto.splitlines()


def primer_borde_de_sesion_utilizable(bars, n_sesiones_previas=1):
    """Contrato de paridad §5: la ventana comparable arranca en un borde de sesion
    que tenga al menos `n_sesiones_previas` COMPLETAS antes, para que el kernel
    llegue con calibracion/perfil congelado -- si no, la primera sesion emite
    CALIBRATION_PENDING y no crea zonas, y esa asimetria se leeria como diff."""
    sid = bars_mod.session_ids(bars.end_ns)
    cambios = [0] + [i for i in range(1, len(sid)) if sid[i] != sid[i - 1]]
    if len(cambios) <= n_sesiones_previas:
        return None, 0
    idx = cambios[n_sesiones_previas]
    return int(bars.end_ns[idx]) // 1_000_000, len(cambios)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--indicador", required=True, choices=sorted(KERNELS))
    ap.add_argument("--oraculo", required=True)
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--chart-tz", required=True,
                    help="tz del chart NT8 (los oraculos salen en hora local del chart)")
    ap.add_argument("--barras", default="time:1",
                    help="time:N o tick:N (default time:1)")
    ap.add_argument("--sesiones-warmup", type=int, default=1,
                    help="sesiones completas exigidas antes de la ventana comparada")
    ap.add_argument("--dias", type=int, default=None,
                    help="recorta la carga a los primeros N dias del contrato. El "
                         "ciclo de vida de HFTZones2 recorre las zonas activas en CADA "
                         "tick y las zonas crecen ~linealmente, asi que el costo es "
                         "CUADRATICO en ticks (exponente medido 2,0-2,5). Recortar no "
                         "es apurar: los indicadores que calibran de la sesion previa "
                         "(AdaptiveMode) no necesitan 71 sesiones de warmup -- eso lo "
                         "pedia el perfil de aVolCellPOI2, no este kernel.")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    t0 = time.time()
    mod_name, cs_rel, usa_fp = KERNELS[a.indicador]
    cs_path = REPO / cs_rel

    print("paridad %s" % a.indicador)
    print("  oraculo : %s" % a.oraculo)
    print("  parquet : %s" % a.parquet)
    print("  chart tz: %s" % a.chart_tz)

    # ---- 1. procedencia, antes de computar nada -------------------------------
    crudo_orc, lineas = leer_oraculo(a.oraculo)
    proc = dict(
        oraculo_archivo=str(a.oraculo),
        oraculo_sha256=hashlib.sha256(crudo_orc).hexdigest(),
        parquet=str(a.parquet),
        parquet_sha256=sha256_archivo(a.parquet),
        cs_blob=blob_git(cs_path),
        cs_path=cs_rel,
        kernel_blob=blob_git(REPO / (mod_name.replace(".", "/") + ".py")),
        chart_tz=a.chart_tz,
        bar_spec=a.barras,
        head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
        arbol_limpio=None,   # se completa abajo
    )

    # Procedencia dirty-aware (regla permanente): un `code_commit` sobre arbol dirty
    # NO garantiza que ese commit contenga el codigo que realmente corrio. El booleano
    # solo no alcanza: si esta sucio hay que poder decir QUE estaba sucio, porque no es
    # lo mismo un README sin commitear que el kernel que se esta midiendo.
    _porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    _sucios = [l[3:].strip() for l in _porcelain if l[:2] != "??"]
    _sin_seguimiento = [l[3:].strip() for l in _porcelain if l[:2] == "??"]
    proc["arbol_limpio"] = not _porcelain
    proc["archivos_sucios"] = sorted(_sucios)
    proc["archivos_sin_seguimiento"] = sorted(_sin_seguimiento)
    # lo unico que puede alterar la MEDICION es el codigo que participa de ella
    _criticos = [f for f in _sucios
                 if f.startswith(("edgelab/", "tools/paridad_oraculo.py", "diag/"))]
    proc["sucios_criticos"] = sorted(_criticos)
    proc["medicion_comprometida"] = bool(_criticos)
    print("  cs blob : %s" % proc["cs_blob"])

    # ---- 2. datos --------------------------------------------------------------
    if a.dias:
        _t0 = ticks_mod.load_canonical_parquet(a.parquet)
        ini_ns = int(_t0.ts_ns[0])
        tk = ticks_mod.load_canonical_parquet(
            a.parquet, start_utc_ns=ini_ns, end_utc_ns=ini_ns + a.dias * 86_400_000_000_000)
        proc["recorte_dias"] = a.dias
    else:
        tk = ticks_mod.load_canonical_parquet(a.parquet)
    spec_tipo, spec_val = a.barras.split(":")
    if spec_tipo == "time":
        bars = bars_mod.build_time_bars(tk, int(spec_val))
    else:
        bars = bars_mod.build_tick_bars(tk, int(spec_val))
    fps = bars_mod.build_footprints(tk, bars) if usa_fp else None
    tick_size = ticks_mod.instrument_spec(tk.instrument).tick_size
    print("  ticks=%d  barras=%d  tick_size=%s" % (len(tk.ts_ns), len(bars.close_t), tick_size))

    # ---- 3. kernel -------------------------------------------------------------
    mod = __import__(mod_name, fromlist=["run"])
    res = mod.run(tk, bars, fps) if usa_fp else mod.run(tk, bars)
    # `run()["zones"]` YA viene con la forma que `match_zones` consume
    # (id/top/bottom/created_ms/ended_ms/state/touches). No se remapea: el remapeo
    # de `build_viewer.py` existe porque ese lee del STORE, que tiene otro esquema
    # (`zone_id`, `final_state`). Copiarlo aca fue el bug de la primera corrida.
    kernel_zones = res["zones"] if isinstance(res, dict) else res
    print("  zonas kernel : %d" % len(kernel_zones))

    # ---- 4. oraculo ------------------------------------------------------------
    orc = oracle.parse_records(lineas, chart_tz=a.chart_tz, tick_size=tick_size)
    nt8_zones = orc["zones"]
    print("  zonas oraculo: %d" % len(nt8_zones))

    # ---- 5. ventana comun + requisito del contrato -----------------------------
    inicio_ms, n_sesiones = primer_borde_de_sesion_utilizable(bars, a.sesiones_warmup)
    if inicio_ms is None:
        print("ABSTAIN_WARMUP: el parquet no tiene %d sesiones completas previas"
              % a.sesiones_warmup)
        return 2
    fin_ms = int(bars.end_ns[len(bars.end_ns) - 1]) // 1_000_000

    def en_ventana(z):
        c = z.get("created_ms")
        return c is not None and inicio_ms <= c <= fin_ms

    kz = [z for z in kernel_zones if en_ventana(z)]
    nz = [z for z in nt8_zones if en_ventana(z)]
    print("  ventana : %d -> %d  (%d sesiones en el parquet, %d de warmup)"
          % (inicio_ms, fin_ms, n_sesiones, a.sesiones_warmup))
    print("  en ventana: kernel=%d  oraculo=%d" % (len(kz), len(nz)))

    # ---- 6. matching -----------------------------------------------------------
    # Frontera de madurez: NT8 exporta mas rango que la ventana Python, asi que las
    # zonas creadas en las ultimas `max_age_bars` barras NO PUEDEN completar su ciclo
    # de vida adentro de la ventana comun -- quedan ACTIVE de este lado y EXPIRED del
    # otro por la ventana, no por el kernel. `match_zones` las compara SOLO por
    # geometria + creacion (la geometria sigue al 100%: no es ampliar tolerancia).
    # Se deriva de `max_age_bars`, un parametro DECLARADO del indicador, no de mirar
    # los resultados. Se reportan las DOS corridas para que el lector vea que cambio.
    params = res.get("params", {}) if isinstance(res, dict) else {}
    max_age = int(params.get("max_age_bars", 0) or 0)
    frontier_ms = None
    if max_age and len(bars.end_ns) > max_age:
        frontier_ms = int(bars.end_ns[len(bars.end_ns) - 1 - max_age]) // 1_000_000

    rep_sin = parity.match_zones(kz, nz, tick_size)
    rep = parity.match_zones(kz, nz, tick_size, maturity_frontier_ms=frontier_ms) \
        if frontier_ms else rep_sin
    print("  frontera madurez: %s (max_age_bars=%d)" % (frontier_ms, max_age))
    print("  sin frontera : %s" % json.dumps(rep_sin["summary"]["counts"], sort_keys=True))
    payload = dict(indicador=a.indicador, procedencia=proc,
                   ventana=dict(inicio_ms=inicio_ms, fin_ms=fin_ms,
                                sesiones_en_parquet=n_sesiones,
                                sesiones_warmup=a.sesiones_warmup),
                   conteos=dict(kernel_total=len(kernel_zones), oraculo_total=len(nt8_zones),
                                kernel_en_ventana=len(kz), oraculo_en_ventana=len(nz)),
                   summary=rep["summary"], gate=rep.get("gate"),
                   maturity_frontier_ms=frontier_ms, max_age_bars=max_age,
                   sin_frontera=dict(summary=rep_sin["summary"], gate=rep_sin.get("gate"),
                                     diffs=[d for d in rep_sin["diagnostics"]
                                            if d.get("code") != "MATCHED"]),
                   # Los MATCHED dominan por conteo y salen primero, asi que truncar
                   # la lista entera tira justo lo unico que hay que mirar. Se guardan
                   # TODAS las diferencias y se recorta solo la evidencia de matcheo.
                   diagnostics=[d for d in rep["diagnostics"] if d.get("code") != "MATCHED"],
                   matched_muestra=[d for d in rep["diagnostics"]
                                    if d.get("code") == "MATCHED"][:50],
                   n_diagnostics=len(rep["diagnostics"]),
                   segundos=round(time.time() - t0, 1))

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str), encoding="utf-8")

    print()
    print("  summary : %s" % json.dumps(rep["summary"], sort_keys=True))
    print("  gate    : %s" % rep.get("gate"))
    print("  informe : %s  (%.1fs)" % (out, payload["segundos"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
