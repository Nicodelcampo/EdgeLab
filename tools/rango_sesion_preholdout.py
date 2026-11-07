"""Rango de sesión (max − min) por trade_date, un contrato por día.

Lee parquets de pre-holdout ya descargados. No abre datasets sellados y descarta
cualquier trade_date >= 20261001. Si un día está en dos vencimientos, se queda
el archivo con más ticks: mezclar precios de dos contratos infla el rango.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.kaggle.sessions_cme import trade_date_ymd

HOLDOUT = 20261001
SALIDA = Path(__file__).resolve().parents[1] / "docs" / "research" / "regimen_corto_20261106" / "rangos_sesion_preholdout.json"
PRECIO = ("price", "price_ticks", "px", "last", "close")
FECHA = ("trade_date", "session_date", "fecha")


def _nombre(schema, opciones):
    nombres = set(schema.names)
    for candidato in opciones:
        if candidato in nombres:
            return candidato
    return None


def _fecha(valor) -> int | None:
    if hasattr(valor, "strftime"):
        return int(valor.strftime("%Y%m%d"))
    texto = str(valor)[:10].replace("-", "")
    if len(texto) >= 8 and texto[:8].isdigit():
        return int(texto[:8])
    return None


def _fundir(acum: dict, fechas, precios) -> None:
    fechas = np.asarray(fechas)
    precios = np.asarray(precios, float)
    ok = np.isfinite(precios)
    if fechas.dtype.kind in "SUO":
        texto = np.array([_fecha(x) or 0 for x in fechas])
        fechas = texto
    fechas = np.asarray(fechas, np.int64)
    ok = ok & (fechas > 0) & (fechas < HOLDOUT)
    if not ok.any():
        return
    fechas, precios = fechas[ok], precios[ok]
    orden = np.argsort(fechas, kind="mergesort")
    fechas, precios = fechas[orden], precios[orden]
    cortes = np.flatnonzero(np.diff(fechas)) + 1
    for tramo_f, tramo_p in zip(np.split(fechas, cortes), np.split(precios, cortes)):
        clave = f"{int(tramo_f[0]):08d}"
        n = int(tramo_p.size)
        lo = float(tramo_p.min())
        hi = float(tramo_p.max())
        previo = acum.get(clave)
        if previo is None:
            acum[clave] = [n, lo, hi]
        else:
            previo[0] += n
            previo[1] = min(previo[1], lo)
            previo[2] = max(previo[2], hi)


def rangos_de_directorio(raiz: Path) -> dict:
    """Devuelve {YYYYMMDD: rango} eligiendo, por día, el parquet con más ticks."""
    ganador: dict[str, tuple] = {}
    archivos = sorted(raiz.rglob("*.parquet"))
    if any("sellado" in str(p).lower() for p in archivos):
        raise SystemExit("hay un parquet sellado en el directorio; no se lee")
    for path in archivos:
        pf = pq.ParquetFile(path)
        col_px = _nombre(pf.schema_arrow, PRECIO)
        col_fe = _nombre(pf.schema_arrow, FECHA)
        if col_px is None:
            raise SystemExit(f"sin columna de precio en {path.name}: {pf.schema_arrow.names}")
        if col_fe is None and "ts_utc_ns" not in pf.schema_arrow.names:
            raise SystemExit(f"sin fecha ni ts_utc_ns en {path.name}: {pf.schema_arrow.names}")
        columnas = ["ts_utc_ns", col_px] if col_fe is None else [col_px, col_fe]
        acum: dict[str, list] = {}
        for lote in pf.iter_batches(batch_size=1_000_000, columns=columnas):
            frame = lote.to_pandas()
            if col_fe is None:
                fechas = trade_date_ymd(frame["ts_utc_ns"].to_numpy(np.int64))
            else:
                fechas = frame[col_fe].map(_fecha).to_numpy()
            _fundir(acum, fechas, frame[col_px].to_numpy())
        for clave, (n, lo, hi) in acum.items():
            previo = ganador.get(clave)
            if previo is None or n > previo[0]:
                ganador[clave] = (n, hi - lo)
    return {dia: par[1] for dia, par in sorted(ganador.items())}


def main(argv):
    if len(argv) < 3 or len(argv) % 2 != 1:
        raise SystemExit("uso: rango_sesion_preholdout.py NQ <dir> ES <dir> ...")
    salida = {}
    for i in range(1, len(argv), 2):
        inst, directorio = argv[i], Path(argv[i + 1])
        salida[inst] = rangos_de_directorio(directorio)
        print(f"{inst} {len(salida[inst])} sesiones")
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")
    print(SALIDA)


if __name__ == "__main__":
    main(sys.argv)
