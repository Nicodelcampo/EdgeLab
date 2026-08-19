"""Audita y CONGELA el log SQLite antes de llamarlo oráculo.

POR QUÉ NO SE PUEDE LLAMAR ORÁCULO TODAVÍA
==========================================
`C:\\LoggerHFT\\data\\hft_logger.sqlite` recibe escrituras de **tres indicadores
distintos**, verificado leyendo los `.cs`:

    HFTZonesESPureV2   -> C:\\LoggerHFT\\data\\hft_logger.sqlite
    HFTZonesNQPureV2   -> el mismo archivo
    HFTZonesNQPureV3   -> el mismo archivo

Los tres hacen `CREATE TABLE IF NOT EXISTS hft_zones` con **el mismo esquema**, y la
tabla **no tiene ninguna columna que identifique quién escribió cada fila**. O sea que
la atribución de una fila a un indicador **no es verificable desde los datos**.

Que las filas de `ES 06-26` vengan de `HFTZonesESPureV2` es una inferencia razonable —es
el indicador con nombre ES— pero es una inferencia sobre qué gráfico estaba abierto, no
un hecho del artefacto. Esa distinción es exactamente la que este proyecto viene
cazando.

QUÉ HACE ESTE SCRIPT
====================
1. **Congela** una copia consistente con la API `backup` de SQLite (no `cp`: la base
   está en WAL y puede estar recibiendo escrituras) y la hashea.
2. **Audita** la copia congelada: duplicados, reinicios/recargas, saltos de `id`,
   solapes, cobertura por sesión, y **zonas vivas al cruzar el firewall**.
3. **Declara la brecha de atribución** en el propio manifiesto, en vez de dejarla en
   prosa.

EL FIREWALL NO ALCANZA CON `start_ts < cutoff`
==============================================
Una zona puede **empezar antes y terminar después** del corte. Se cuentan aparte y se
censuran: exportar su `end_ts` o cualquier feature calculada al cierre haría cruzar
información del holdout.

Target-free: geometría y procedencia. Sin outcomes, sin P&L.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import sys
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.kaggle.sessions_cme import session_bounds_utc_ns, trade_date_ymd  # noqa: E402

import numpy as np  # noqa: E402

SCHEMA_VERSION = "auditar_oraculo_sqlite_v1"
ORIGEN = pathlib.Path(r"C:\LoggerHFT\data\hft_logger.sqlite")
NT8_DIR = pathlib.Path(r"C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators")
ESCRIBEN_LA_MISMA_BASE = ("HFTZonesESPureV2", "HFTZonesNQPureV2", "HFTZonesNQPureV3")

HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]
CUTOFF_MS = FIREWALL_CUTOFF_NS // 1_000_000


def sha256_archivo(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def congelar(origen, destino):
    """Copia consistente con la API `backup`. `cp` sobre una base en WAL puede dar un
    archivo a medio escribir; `backup` toma un snapshot coherente aunque haya escritores."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()
    src = sqlite3.connect("file:%s?mode=ro" % origen.as_posix(), uri=True)
    dst = sqlite3.connect(str(destino))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    return dict(origen=str(origen), copia=str(destino),
                bytes=destino.stat().st_size, sha256=sha256_archivo(destino))


def auditar(copia, contrato):
    con = sqlite3.connect("file:%s?mode=ro" % copia.as_posix(), uri=True)
    c = con.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(hft_zones)")]

    tot = c.execute("SELECT COUNT(*) FROM hft_zones WHERE instrument = ?", (contrato,)).fetchone()[0]
    filas = c.execute(
        "SELECT id, start_ts, end_ts, bucket, dir, price_upper, price_lower, tick_res "
        "FROM hft_zones WHERE instrument = ? ORDER BY id", (contrato,)).fetchall()

    ids = [r[0] for r in filas]
    huecos = [b - a for a, b in zip(ids, ids[1:]) if b - a != 1]
    # una MISMA zona repetida: mismo inicio, mismo borde, misma direccion
    firmas = Counter((r[1], r[5], r[6], r[4]) for r in filas)
    dups = {k: v for k, v in firmas.items() if v > 1}
    # reinicios/recargas: `start_ts` que retrocede al avanzar el id
    retrocesos = sum(1 for a, b in zip(filas, filas[1:]) if b[1] < a[1])
    tick_res = Counter(r[7] for r in filas)

    st = np.array([r[1] for r in filas], dtype=np.int64)
    en = np.array([r[2] if r[2] is not None else r[1] for r in filas], dtype=np.int64)
    pre = st < CUTOFF_MS
    # EL PUNTO DEL AUDITOR: zonas que empiezan antes y terminan despues del corte
    vivas_al_corte = int(((st < CUTOFF_MS) & (en >= CUTOFF_MS)).sum())

    ses = trade_date_ymd(st[pre] * 1_000_000) if pre.any() else np.array([], dtype=np.int64)
    por_sesion = Counter(int(x) for x in ses)
    con.close()

    return dict(
        contrato=contrato, columnas=cols, zonas_totales=tot,
        ids=dict(min=min(ids) if ids else None, max=max(ids) if ids else None,
                 huecos=len(huecos), mayor_hueco=max(huecos) if huecos else 0),
        posibles_duplicados=dict(
            n_firmas_repetidas=len(dups),
            zonas_involucradas=int(sum(dups.values())),
            nota="firma = (start_ts, price_upper, price_lower, dir)"),
        retrocesos_de_start_ts=retrocesos,
        nota_retrocesos=("un `start_ts` que retrocede al avanzar el id indica reinicio "
                         "del indicador o recarga historica sobre la misma base"),
        tick_res=dict(tick_res),
        firewall=dict(
            cutoff_ms=int(CUTOFF_MS),
            zonas_pre=int(pre.sum()), zonas_post=int((~pre).sum()),
            zonas_vivas_al_corte=vivas_al_corte,
            nota=("`start_ts < cutoff` NO alcanza: una zona puede empezar antes y "
                  "terminar despues. Las vivas al corte se CENSURAN -- exportar su "
                  "end_ts o features de cierre haria cruzar informacion del holdout.")),
        sesiones=dict(n=len(por_sesion),
                      primera=min(por_sesion) if por_sesion else None,
                      ultima=max(por_sesion) if por_sesion else None,
                      zonas_por_sesion_mediana=float(np.median(list(por_sesion.values())))
                      if por_sesion else 0.0,
                      zonas_por_sesion_max=max(por_sesion.values()) if por_sesion else 0,
                      detalle={str(k): v for k, v in sorted(por_sesion.items())}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contrato", default="ES 06-26")
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "oraculo_es_auditoria.json"))
    a = ap.parse_args()

    print("auditoria del log SQLite  ·  %s" % SCHEMA_VERSION)
    if not ORIGEN.exists():
        raise SystemExit("ABORTA: no existe %s" % ORIGEN)

    copia = REPO / "runs" / "hft_logger_snapshot.sqlite"
    snap = congelar(ORIGEN, copia)
    print("  congelado  %.1f MB  sha256 %s" % (snap["bytes"] / 2 ** 20, snap["sha256"][:16]))

    aud = auditar(copia, a.contrato)
    print("  contrato %s: %d zonas  (%d pre-firewall, %d post, %d VIVAS AL CORTE)"
          % (a.contrato, aud["zonas_totales"], aud["firewall"]["zonas_pre"],
             aud["firewall"]["zonas_post"], aud["firewall"]["zonas_vivas_al_corte"]))
    print("  ids: %d huecos (mayor %d)  ·  retrocesos de start_ts: %d"
          % (aud["ids"]["huecos"], aud["ids"]["mayor_hueco"], aud["retrocesos_de_start_ts"]))
    print("  firmas repetidas: %d (%d zonas)"
          % (aud["posibles_duplicados"]["n_firmas_repetidas"],
             aud["posibles_duplicados"]["zonas_involucradas"]))
    print("  sesiones pre-firewall: %d  (%s -> %s)  mediana %.0f zonas/sesion"
          % (aud["sesiones"]["n"], aud["sesiones"]["primera"], aud["sesiones"]["ultima"],
             aud["sesiones"]["zonas_por_sesion_mediana"]))

    fuentes = {}
    for n in ESCRIBEN_LA_MISMA_BASE:
        f = NT8_DIR / ("%s.cs" % n)
        fuentes[n] = dict(existe=f.exists(),
                          sha256=sha256_archivo(f) if f.exists() else None,
                          lineas=len(f.read_text(encoding="utf-8", errors="replace").splitlines())
                          if f.exists() else None)

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]

    out = dict(
        schema_version=SCHEMA_VERSION,
        estado="NO_ES_ORACULO_TODAVIA",
        motivo_principal=(
            "tres indicadores escriben la MISMA base con el MISMO esquema "
            "(HFTZonesESPureV2, HFTZonesNQPureV2, HFTZonesNQPureV3) y `hft_zones` no "
            "tiene ninguna columna que identifique al escritor. La atribucion de una "
            "fila a un indicador NO es verificable desde los datos."),
        que_haria_falta=[
            "corrida controlada: SOLO HFTZonesESPureV2 sobre un grafico de ES, con "
            "DbPath a un archivo NUEVO y vacio",
            "registrar los 29 parametros efectivos, version de NT8, plantilla de "
            "sesion, huso horario y modo de calculo",
            "hashear el .cs y el archivo resultante ANTES de extraer",
        ],
        outcomes_accessed=False, pnl_accessed=False,
        snapshot=snap, fuentes_que_comparten_la_base=fuentes,
        auditoria=aud,
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios), alcance_comprometida=["edgelab/", "diag/"],
            medicion_comprometida=bool([f for f in sucios if f.startswith(("edgelab/", "diag/"))])))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("  escrito %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
