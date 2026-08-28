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

SCHEMA_VERSION = "auditar_oraculo_sqlite_v2_end_ts_e_inventario"
ORIGEN_DEFAULT = pathlib.Path(r"C:\LoggerHFT\data\oraculo_espurev2_ES.sqlite")
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
    # `end_ts` NULL: la version anterior lo reemplazaba por `start_ts`, o sea que una
    # zona ABIERTA quedaba clasificada como terminada al instante, y de ahi "0 vivas al
    # corte" no estaba probado. Ahora NULL se trata como +infinito --lo conservador-- y
    # se publica cuantos hay, para que la afirmacion sea verificable y no confiada.
    n_end_null = sum(1 for r in filas if r[2] is None)
    INF = np.iinfo(np.int64).max
    en = np.array([r[2] if r[2] is not None else INF for r in filas], dtype=np.int64)
    pre = st < CUTOFF_MS
    vivas_al_corte = int(((st < CUTOFF_MS) & (en >= CUTOFF_MS)).sum())
    dur = en[en != INF] - st[en != INF]

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
        nota_retrocesos=("demuestra ORDEN TEMPORAL NO MONOTONO por id. Es compatible "
                         "con recargas historicas, reinicios del indicador o varios "
                         "escritores concurrentes: no distingue cual, y decir 'indica "
                         "reinicio o recarga' era afirmar de mas."),
        end_ts=dict(
            n_null=n_end_null,
            dur_ms_min=int(dur.min()) if len(dur) else None,
            dur_ms_max=int(dur.max()) if len(dur) else None,
            dur_ms_mediana=float(np.median(dur)) if len(dur) else None,
            nota=("NULL se trata como +inf para el chequeo del cutoff. Las duraciones "
                  "de 0-500 ms muestran que `hft_zones` registra el BARRIDO, no el "
                  "ciclo de vida de la zona: en esta tabla no hay toques ni "
                  "invalidacion.")),
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


def inventario_familia(copia, prefijo):
    """Sesiones pre-firewall por contrato de una familia, VERSIONADO en el artefacto.

    v1 dejaba estos numeros solo en el acta, asi que N=23 no era verificable contra un
    archivo. Ademas chequea ALIAS: dos etiquetas distintas para el mismo contrato
    (`ES 09-26` y `ES SEP26`) comparten fechas, y sumar sus sesiones sin unir seria
    doble conteo.
    """
    con = sqlite3.connect("file:%s?mode=ro" % copia.as_posix(), uri=True)
    insts = [r[0] for r in con.execute(
        "SELECT DISTINCT instrument FROM hft_zones WHERE instrument LIKE ?",
        (prefijo + "%",)).fetchall()]
    por_contrato, union = {}, set()
    INF = np.iinfo(np.int64).max
    for inst in insts:
        rows = con.execute(
            "SELECT start_ts, end_ts FROM hft_zones WHERE instrument=?", (inst,)).fetchall()
        st = np.array([r[0] for r in rows], dtype=np.int64)
        en = np.array([r[1] if r[1] is not None else INF for r in rows], dtype=np.int64)
        pre = st < CUTOFF_MS
        ses = sorted(set(int(x) for x in trade_date_ymd(st[pre] * 1_000_000))) if pre.any() else []
        por_contrato[inst] = dict(
            zonas=len(rows), zonas_pre_firewall=int(pre.sum()),
            n_end_ts_null=int(sum(1 for r in rows if r[1] is None)),
            zonas_vivas_al_corte=int(((st < CUTOFF_MS) & (en >= CUTOFF_MS)).sum()),
            n_sesiones=len(ses), trade_dates=ses)
        if inst.startswith(prefijo + " "):
            union |= set(ses)
    alias = []
    nombres = list(por_contrato)
    for i, x in enumerate(nombres):
        for y in nombres[i + 1:]:
            sx = set(por_contrato[x]["trade_dates"])
            sy = set(por_contrato[y]["trade_dates"])
            if sx and sy and len(sx & sy) / min(len(sx), len(sy)) > 0.5:
                alias.append(dict(a=x, b=y, fechas_compartidas=len(sx & sy),
                                  fechas_de_a=len(sx), fechas_de_b=len(sy)))
    con.close()
    return dict(prefijo=prefijo, por_contrato=por_contrato,
                union_sesiones=sorted(union), n_union=len(union),
                posibles_alias=alias,
                nota_alias=("dos etiquetas que comparten mas de la mitad de sus fechas "
                            "pueden ser el MISMO contrato con distinto nombre de "
                            "display; sumarlas sin unir seria doble conteo"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contrato", default="ES 06-26")
    ap.add_argument("--familia", default="ES")
    ap.add_argument("--origen", default=str(ORIGEN_DEFAULT))
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "oraculo_es_auditoria.json"))
    a = ap.parse_args()

    print("auditoria del log SQLite  ·  %s" % SCHEMA_VERSION)
    origen = pathlib.Path(a.origen)
    if not origen.exists():
        raise SystemExit("ABORTA: no existe %s" % origen)

    copia = pathlib.Path(a.snapshot) if a.snapshot else (
        REPO / "runs" / ("%s_snapshot.sqlite" % origen.stem))
    snap = congelar(origen, copia)
    print("  congelado  %.1f MB  sha256 %s" % (snap["bytes"] / 2 ** 20, snap["sha256"][:16]))

    aud = auditar(copia, a.contrato)
    inv = inventario_familia(copia, a.familia)
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
        estado=("ORACULO_CONTROLADO" if origen.name != "hft_logger.sqlite"
                else "NO_ES_ORACULO_TODAVIA"),
        atribucion=(
            "base creada por una corrida controlada: DbPath NUEVO y vacio, y un solo "
            "indicador escribiendo. Eso resuelve el bloqueante del log compartido "
            "`hft_logger.sqlite`, donde tres indicadores (HFTZonesESPureV2, "
            "HFTZonesNQPureV2, HFTZonesNQPureV3) escriben la MISMA tabla con el MISMO "
            "esquema y sin columna de escritor."
            if origen.name != "hft_logger.sqlite" else
            "NO verificable: tres indicadores comparten la base y el esquema."),
        corrida=dict(
            indicador="HFTZonesESPureV2",
            cs_sha256=sha256_archivo(NT8_DIR / "HFTZonesESPureV2.cs")
            if (NT8_DIR / "HFTZonesESPureV2.cs").exists() else None,
            chart="ES 06-26 1 Minute / ES 03-26 25 Tick / ES 09-26 1 Tick",
            end_date="30/06/2026 (ES 06-26, ES 09-26) y 20/03/2026 (ES 03-26)",
            trading_hours="<Use instrument settings>",
            break_at_eod=True, calculate="On bar close",
            max_bars_look_back=256, tick_replay=False,
            enable_flow_log=False, enable_db_logging=True,
            parametros_efectivos=dict(
                TickResolution=1, MinPasos=10, MaxRangoTickPorVela=1, FallosTolerados=1,
                FiltroDireccionEstricto=True, MinSweepTicks=5, MaxAvgMs=15,
                MaxTotalMs=300, MaxPausaMs=50, MinVolumeRate=500, MinTotalVolume=200,
                PredatorAvgMs=3, UltraAvgMs=10, MostrarAbsorb=True, MinAbsorbPasos=8,
                ExtensionDibujo=600),
            nota_parametros="defaults del .cs, sin modificar (confirmado con Nico)"),
        outcomes_accessed=False, pnl_accessed=False,
        snapshot=snap, fuentes_que_comparten_la_base=fuentes,
        auditoria=aud, inventario_familia=inv,
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios), alcance_comprometida=["edgelab/", "diag/"],
            medicion_comprometida=bool([f for f in sucios if f.startswith(("edgelab/", "diag/"))])))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("  familia %s: %d contratos, union %d sesiones pre-firewall, alias %d"
          % (a.familia, len(inv["por_contrato"]), inv["n_union"],
             len(inv["posibles_alias"])))
    print("  escrito %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
