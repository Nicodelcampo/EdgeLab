"""Frontera del holdout — ÚNICA fuente de verdad en código (enmienda HOLDOUT-A4, decisión de Nico del 2026-10-22).

El holdout es el mismo para TODOS los instrumentos y para todo tipo de dato (ticks, barras, L2): las sesiones CME desde
el trade date 2026-10-01 en adelante. Esa sesión abre a las 17:00 CT del 2026-09-30 = 22:00 UTC.

Todo lo anterior a esa apertura es desarrollo (descubrimiento y, donde una familia lo pre-registró, réplica).
Ver `docs/incidents/AMENDMENT_HOLDOUT-A4_2026-10-22.md`.

Formas equivalentes (usar la que pida cada consumidor, nunca un literal propio):
"""
from __future__ import annotations

HOLDOUT_PRIMERA_SESION = "2026-10-01"                    # trade date CME (la sesión se etiqueta por su día de cierre)
HOLDOUT_PRIMERA_SESION_INT = 20261001                    # mismo, como YYYYMMDD
HOLDOUT_APERTURA_UTC_ISO = "2026-09-30T22:00:00"         # instante de apertura de esa sesión (17:00 CT, UTC-5)
HOLDOUT_APERTURA_UTC_NS = 1_790_805_600_000_000_000      # mismo, en ns desde epoch
HOLDOUT_APERTURA_UTC_S = HOLDOUT_APERTURA_UTC_NS // 1_000_000_000

# Corte FÍSICO de los artefactos de datos viejos (research-v2, datasets Kaggle `*-preholdout`, release v1): 2026-06-30 22:00 UTC.
# No es el holdout: es dónde terminan esos archivos. Lo que está entre esta fecha y la apertura del holdout es desarrollo
# y vive en las extensiones jul-sep (p. ej. `nt8_ext_2026q3`) o en el release líquido.
CORTE_FISICO_RESEARCH_V2_UTC_NS = 1_782_856_800_000_000_000


def es_holdout_trade_date(td) -> bool:
    """td: 'YYYY-MM-DD', YYYYMMDD (int/str) o date."""
    s = str(td).replace("-", "")[:8]
    return int(s) >= HOLDOUT_PRIMERA_SESION_INT


def es_holdout_ns(ts_utc_ns: int) -> bool:
    return int(ts_utc_ns) >= HOLDOUT_APERTURA_UTC_NS


# Sesiones del holdout que NINGÚN análisis usa (2026-11-02, Nico: «asegurate que cualquier agente no use los días que no se deben usar»).
# Medido target-free sobre el dataset sellado v5 (docs/research/canasta_7_20261030/SELLADO_CONTEO_v5.json): sesión con menos del 50 % de
# los ticks de la mediana del instrumento en octubre, más los días que NT8 no tiene (10-07 en CME). Los domingos de FX son restos del
# fin de semana, no sesiones. Los lectores sellados (`fuentes_ticks.bloques_nq_sellado` / `bloques_spot_sellado`) las descartan siempre;
# `tests/test_holdout_unico.py` lo verifica. Una sesión sólo sale de esta tabla con datos completos re-sellados y re-medidos.
_CME = ("NQ", "MNQ", "ES", "MES", "YM", "MYM", "GC", "MGC", "6B", "6E", "6J", "MBT")
SESIONES_EXCLUIDAS_HOLDOUT = {
    **{s: {20261007} for s in ("NQ", "MNQ", "ES", "MES", "GC", "MGC", "YM", "MYM")},     # NT8 no tiene el 7-oct (YM a medias)
    "ES": {20261007, 20261029, 20261030}, "MES": {20261007, 20261029, 20261030},          # 40 % y 47 % de una sesión normal
    "6B": {20261029}, "6E": {20261029},
    "USATECHIDXUSD": {20261029}, "USA500IDXUSD": {20261012, 20261029}, "USA30IDXUSD": {20261029}, "XAUUSD": {20261029},
    "EURUSD": {20261004, 20261011, 20261018, 20261025, 20261029}, "GBPUSD": {20261004, 20261011, 20261018, 20261025, 20261029},
    "USDJPY": {20261004, 20261011, 20261012, 20261018, 20261025, 20261029},
}


def sesion_excluida(instrumento: str, trade_date) -> bool:
    """True si la sesión `trade_date` (YYYYMMDD) del `instrumento` (futuro o símbolo Dukascopy) no se usa en ningún análisis."""
    return int(str(trade_date).replace("-", "")[:8]) in SESIONES_EXCLUIDAS_HOLDOUT.get(str(instrumento).upper().replace("DK:", ""), set())


# ---------------------------------------------------------------------------------------------------------------------------------
# HOLDOUT-A5 (firmada por Nico el 2026-11-17): holdout INTERCALADO por bloques mensuales para las campañas NUEVAS que lo declaren
# (`"particion": "A5"` en la spec). Ver `docs/incidents/AMENDMENT_HOLDOUT-A5_2026-11-17.md`. No cambia nada de A3/A4: el holdout
# terminal sigue empezando en la sesión CME del 2026-10-01 y, para A5, pasa a vigilar y a dar tamaño.
# Cada año, una permutación fija de sus 12 meses: 7 DESC, 2 REP, 3 HOLDOUT. Embargo: el día hábil anterior y el posterior a cada mes
# HOLDOUT no pertenecen a ninguna partición. Desde la frontera A4, TERMINAL.
A5_SEMILLA = "EdgeLab-HOLDOUT-A5-v1"
A5_REPARTO = (("DESC", 7), ("REP", 2), ("HOLDOUT", 3))


def a5_meses(anio: int) -> dict:
    """{mes: 'DESC'|'REP'|'HOLDOUT'} del año (determinista: sha256 de la semilla y el año)."""
    import hashlib
    import numpy as np
    sem = int.from_bytes(hashlib.sha256(f"{A5_SEMILLA}:{int(anio)}".encode()).digest()[:8], "little")
    perm = np.random.default_rng(sem).permutation(np.arange(1, 13)); out, i = {}, 0
    for nombre, k in A5_REPARTO:
        for m in perm[i:i + k]: out[int(m)] = nombre
        i += k
    return out


def _dia_habil(td: int, paso: int) -> int:
    import datetime as dt
    d = dt.date(td // 10000, td // 100 % 100, td % 100) + dt.timedelta(days=paso)
    while d.weekday() >= 5: d += dt.timedelta(days=paso)
    return int(d.strftime("%Y%m%d"))


def a5_bloque(trade_date) -> str:
    """'DESC' | 'REP' | 'HOLDOUT' | 'EMBARGO' | 'TERMINAL' de una sesión (YYYYMMDD) en la partición A5."""
    td = int(str(trade_date).replace("-", "")[:8])
    if td >= HOLDOUT_PRIMERA_SESION_INT: return "TERMINAL"
    b = a5_meses(td // 10000)[td // 100 % 100]
    if b != "HOLDOUT":
        for v in (_dia_habil(td, 1), _dia_habil(td, -1)):
            if v < HOLDOUT_PRIMERA_SESION_INT and a5_meses(v // 10000)[v // 100 % 100] == "HOLDOUT": return "EMBARGO"
    return b


def mascara_a5_limpia(fechas_entrada, fechas_salida=None):
    """Devuelve lista/array bool True sólo cuando entrada (y salida si se pasa) caen estrictamente en DESC o REP de A5."""
    import numpy as np
    blq_in = [a5_bloque(f) in ("DESC", "REP") for f in fechas_entrada]
    if fechas_salida is None:
        return np.asarray(blq_in, dtype=bool)
    blq_out = [a5_bloque(f) in ("DESC", "REP") for f in fechas_salida]
    return np.asarray(blq_in, dtype=bool) & np.asarray(blq_out, dtype=bool)


def exigir_sin_holdout_no_abierto(fechas, familia: str, ventanas_path=None) -> None:
    """K60/A5: falla cerrado si `fechas` incluye sesiones HOLDOUT A5 o TERMINAL sin apertura vigente registrada para `familia`."""
    import json
    from pathlib import Path
    blqs = {a5_bloque(f) for f in fechas}
    if "TERMINAL" in blqs:
        raise ValueError(f"K60/A5 {familia}: incluye sesiones TERMINAL >= {HOLDOUT_PRIMERA_SESION} sin autorización")
    if "HOLDOUT" not in blqs:
        return
    ruta = Path(ventanas_path) if ventanas_path else Path(__file__).resolve().parents[1] / "docs/research/HOLDOUT_VENTANAS.jsonl"
    vig = []
    if ruta.exists():
        for line in ruta.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("familia") != familia:
                continue
            if r.get("tipo") == "apertura":
                vig = [v for v in vig if v["cid"] != r["cid"]] + [r]
            elif r.get("tipo") == "anulacion":
                vig = [v for v in vig if v["cid"] != r["cid"]]
    if not vig:
        raise ValueError(f"K60/A5 {familia}: intenta leer meses HOLDOUT sin apertura vigente registrada en HOLDOUT_VENTANAS.jsonl")
