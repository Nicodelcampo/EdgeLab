"""Huella del UNIVERSO, no de los archivos. Resuelve «cuales parquets gobiernan».

## Por que la pregunta original no se puede contestar comparando archivos

`c28a6c0` dejo establecido que los 6E individuales de las dos maquinas son
**post-fix**, pero **con distinta ventana de descarga**. Comparar tamanos o el
sha256 del archivo entero dice que diferen — y no dice si eso importa.

**No importa por si mismo.** Lo que entra al computo no es el archivo: es la
rebanada que sobrevive a la ventana de carga y al firewall. Y esa rebanada puede
ser IDENTICA aunque los archivos difieran, porque:

- el firewall corta en `MAX_FECHA` (2026-06-30), asi que todo lo que una maquina
  bajo despues de esa fecha queda afuera;
- `6E_09-26` es front month y crece: la maquina que descargo mas tarde tiene mas
  bytes y **exactamente el mismo universo**;
- `6E_09-25` tiene `APTO=0`: cero dias suyos entran al universo alguna vez.

Por eso este modulo no hashea archivos. Hashea **lo que se computa**.

## Que emite

Por contrato, sobre la rebanada exacta que cargan los modulos de medicion
—mismo `LEAD_DAYS`, mismo `corte_del_sello()`, mismo orden—:

    ticks, primer y ultimo ts, y el sha256 de (ts_ns, price_ticks, sequence)

Mas la identidad de ENTORNO, que es el agujero por el que entro el venv global el
2026-08-09: `recuento_kT.py` emite `code_commit` y `measurement_code_sha256`
—identidad de CODIGO— pero **nada del interprete**. Un artefacto puede ser
reproducible en codigo e irreproducible en entorno.

## Como se usa

Correr en las dos maquinas **con el `.venv` del repo** y comparar
`huella_universo`:

    ./.venv/Scripts/python.exe diag/tasa_senales/huella_universo.py

- **Coinciden** -> la pregunta se disuelve: los dos parquets producen el mismo
  universo y no hay nada que sincronizar. Se declara la huella, no una maquina.
- **No coinciden** -> recien ahi hay que decidir cual gobierna, y el diff por
  contrato dice cual difiere.

No lee outcomes. No toca el holdout. No decide nada por su cuenta.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    LEAD_DAYS, MAX_FECHA, corte_del_sello, dias_research, git_head, pd,
    ticks_mod,
)

SCHEMA_VERSION = "huella_universo_v1"
SALIDA = Path(__file__).resolve().parent / "huella_universo.json"


def identidad_entorno():
    """Lo que `recuento_kT` NO emite y por eso no detecto el venv global."""
    en_venv = sys.prefix != sys.base_prefix
    paquetes = {}
    for nombre in ("numpy", "pandas", "pyarrow"):
        try:
            paquetes[nombre] = __import__(nombre).__version__
        except Exception as exc:                       # noqa: BLE001
            paquetes[nombre] = "NO_IMPORTABLE: %s" % type(exc).__name__
    try:
        venv_del_repo = (Path(sys.prefix).resolve()
                         == (REPO_PATH / ".venv").resolve())
    except Exception:                                  # noqa: BLE001
        venv_del_repo = False
    return dict(
        python=sys.version.split()[0],
        ejecutable=str(Path(sys.executable)),
        en_venv=en_venv,
        es_el_venv_del_repo=venv_del_repo,
        plataforma=platform.platform(),
        paquetes=paquetes,
        numpy_resuelto_desde=str(Path(np.__file__).parent),
    )


def huella_contrato(archivo, fechas):
    """Hashea la rebanada que se computa, con la ventana de los medidores."""
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())

    ruta = REPO_PATH / "data" / "nt8" / "6E" / archivo
    if not ruta.exists():
        return dict(estado="AUSENTE", archivo=archivo)

    tk = ticks_mod.load_canonical_parquet(
        str(ruta), start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    ts = np.asarray(tk.ts_ns)
    px = np.asarray(tk.price_ticks)
    sq = np.asarray(tk.sequence)
    if not len(ts):
        return dict(estado="VACIO", archivo=archivo, sesiones=len(fechas))

    h = hashlib.sha256()
    for arr in (ts, px, sq):
        # `ascontiguousarray` + dtype explicito: el hash no puede depender del
        # layout ni de que una maquina infiera int32 y la otra int64.
        h.update(np.ascontiguousarray(arr, dtype=np.int64).tobytes())

    return dict(
        estado="OK", archivo=archivo, sesiones=len(fechas),
        ticks=int(len(ts)),
        primer_ts_ns=int(ts[0]), ultimo_ts_ns=int(ts[-1]),
        primer_ts_iso=str(pd.Timestamp(int(ts[0]), unit="ns", tz="UTC")),
        ultimo_ts_iso=str(pd.Timestamp(int(ts[-1]), unit="ns", tz="UTC")),
        tick_size=float(tk.tick_size),
        ventana_carga_ini=str(ini), ventana_carga_fin=str(fin),
        sha256_rebanada=h.hexdigest(),
        # el sha del ARCHIVO va aparte y es INFORMATIVO: puede diferir entre
        # maquinas sin que el universo cambie. No se compara para decidir.
        bytes_archivo=int(ruta.stat().st_size),
    )


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)

    ent = identidad_entorno()
    if not ent["es_el_venv_del_repo"]:
        print("AVISO: no estas en el .venv del repo. La huella se calcula igual, "
              "pero la comparacion entre maquinas solo es concluyente si las dos "
              "corren con el mismo entorno declarado.", file=sys.stderr)

    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(arch, sorted(f)) for arch, f in sorted(por_arch.items())]
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)

    print(f"universo: {ns} sesiones | max {peor} <= {MAX_FECHA}")
    print(f"entorno : python {ent['python']} | venv del repo: "
          f"{ent['es_el_venv_del_repo']} | numpy {ent['paquetes']['numpy']}")
    print()

    contratos, h_total = {}, hashlib.sha256()
    for arch, fechas in plan:
        r = huella_contrato(arch, fechas)
        contratos[arch] = r
        if r["estado"] != "OK":
            print(f"  {arch:<28} {r['estado']}")
            h_total.update(("%s|%s" % (arch, r["estado"])).encode())
            continue
        print(f"  {arch:<28} {r['sesiones']:>3} ses  {r['ticks']:>9} ticks  "
              f"{r['sha256_rebanada'][:16]}")
        h_total.update(("%s|%s" % (arch, r["sha256_rebanada"])).encode())

    huella = h_total.hexdigest()
    print(f"\n  HUELLA DEL UNIVERSO  {huella}")
    print("  ^ es esto lo que tiene que coincidir entre maquinas, NO los archivos")

    payload = dict(
        schema_version=SCHEMA_VERSION,
        que_es="huella de la rebanada COMPUTADA por contrato, no del archivo. "
               "Dos maquinas con parquets de distinta ventana de descarga pueden "
               "tener la misma huella: es eso lo que decide si hay que sincronizar",
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()), lead_days=LEAD_DAYS,
        code_commit=git_head(),
        identidad_entorno=ent,
        universe_filter_report=info,
        outcomes_accessed=False,
        contratos=contratos,
        huella_universo=huella)
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    Path(a.out).write_text(json.dumps(payload, indent=2, default=str),
                           encoding="utf-8")
    print(f"\n-> {a.out}")
    print("EXIT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
