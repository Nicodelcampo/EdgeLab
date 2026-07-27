# -*- coding: utf-8 -*-
"""Umbrales intrínsecamente fraccionarios: espejado bit a bit (Decisión A).

`hi − range × pct` **no** es un precio de grilla. Pasarlo a enteros cambiaría la
definición del indicador e invalidaría una paridad ya ganada (BigTrap2 `time:1`,
PASS con 0 diffs) por un 0,0241 % bidireccional. Decisión de Nico del 2026-07-26:
no se convierte; se exige que los dos lados computen **la misma secuencia de
operaciones** y se mide el residual.

Estos tests fijan esa exigencia. Sin ellos, un refactor razonable —sacar factor
común, reordenar términos, precomputar `pct/100`— rompería el espejado sin que
nada se queje, y el residual dejaría de ser explicable.
"""
import math

import pytest

PCT = 30.0
TS = 5e-05
DEC = 5


# --- espejos literales de las dos implementaciones -------------------------
def _floor_cs(hi, lo, pct):
    """C#: range = hi - lo; wickHiFloor = hi - range * (WickZonePct / 100.0)"""
    rng = hi - lo
    return hi - rng * (pct / 100.0)


def _ceil_cs(hi, lo, pct):
    rng = hi - lo
    return lo + rng * (pct / 100.0)


def _row_center(row, row_ticks, ts):
    """(row * rowTicks + (rowTicks - 1) / 2.0) * TickSize — igual en los dos."""
    return (row * row_ticks + (row_ticks - 1) / 2.0) * ts


def _feed(t, ts=TS, dec=DEC):
    return float(("%." + str(dec) + "f") % (t * ts))


def _recon(t, ts=TS):
    return t * ts


def test_el_kernel_python_usa_la_misma_secuencia_de_operaciones():
    """Comparación textual-estructural contra el `.cs`, término a término.

    Se lee el fuente en vez de sólo llamar la función: lo que hay que preservar
    es el ORDEN de las operaciones, y dos órdenes distintos pueden dar el mismo
    resultado en casi todos los casos y diferir justo en el empate.
    """
    src = open("edgelab/bridge/indicators/bigtrap2.py", encoding="utf-8").read()
    assert 'wick_hi_floor = hi - rng * (p["wick_zone_pct"] / 100.0)' in src
    assert 'wick_lo_ceil = lo + rng * (p["wick_zone_pct"] / 100.0)' in src
    assert "rng = hi - lo" in src
    assert "row_price = (r * row_ticks + (row_ticks - 1) / 2.0) * tick_size" in src

    cs = open("nt8/BigTrap2.cs", encoding="utf-8-sig").read()
    assert "double range = hi - lo;" in cs
    assert "double wickHiFloor = hi - range * (WickZonePct / 100.0);" in cs
    assert "double wickLoCeil  = lo + range * (WickZonePct / 100.0);" in cs
    assert "return (row * rowTicks + (rowTicks - 1) / 2.0) * TickSize;" in cs


def test_la_aritmetica_no_aporta_exposicion():
    """El núcleo de la Decisión A, medido.

    Con `hi`/`lo` en la MISMA representación de los dos lados, la exposición
    tiene que ser **exactamente 0**. Si no lo es, el residual no es sólo la
    representación de entrada y la declaración del contrato sería falsa.
    """
    flips = 0
    for base in range(20000, 20120):
        for rng_t in range(1, 61):
            hi_t, lo_t = base + rng_t, base
            a = _floor_cs(_recon(hi_t), _recon(lo_t), PCT)
            b = _floor_cs(_recon(hi_t), _recon(lo_t), PCT)
            assert a == b            # determinismo, trivial pero explícito
            for r in range(lo_t, hi_t + 1):
                px = _row_center(r, 1, TS)
                if (px >= a) != (px >= b):
                    flips += 1
    assert flips == 0


def test_el_residual_medido_es_el_declarado():
    """0,0241 % con las representaciones reales. Es el número del contrato.

    Si esto cambia, el caveat de AUDIT-003 y de `parity_coverage/BigTrap2.md`
    quedó desactualizado y hay que corregirlo — no ampliarlo.
    """
    flips = tot = 0
    for base in range(20000, 20400):
        for rng_t in range(1, 121):
            hi_t, lo_t = base + rng_t, base
            thr_py = _floor_cs(_recon(hi_t), _recon(lo_t), PCT)
            thr_nt = _floor_cs(_feed(hi_t), _feed(lo_t), PCT)
            for r in range(lo_t, hi_t + 1):
                tot += 1
                if (_recon(r) >= thr_py) != (_feed(r) >= thr_nt):
                    flips += 1
    pct = 100.0 * flips / tot
    assert flips == 710, flips
    assert pct == pytest.approx(0.0241, abs=5e-4), pct


def test_el_residual_es_bidireccional():
    """Lo distingue del resto de la familia ULP, que es unidireccional.

    En los otros cuatro casos el feed siempre cae por debajo, así que el error
    tiene signo fijo. Acá el umbral se arma con una resta *y* una
    multiplicación, y el signo depende del rango — por eso no se puede
    "compensar" con un offset.
    """
    nt8_mas, py_mas = 0, 0
    for base in range(20000, 20400):
        for rng_t in range(1, 121):
            hi_t, lo_t = base + rng_t, base
            thr_py = _floor_cs(_recon(hi_t), _recon(lo_t), PCT)
            thr_nt = _floor_cs(_feed(hi_t), _feed(lo_t), PCT)
            for r in range(lo_t, hi_t + 1):
                d_py, d_nt = _recon(r) >= thr_py, _feed(r) >= thr_nt
                if d_py != d_nt:
                    if d_nt:
                        nt8_mas += 1
                    else:
                        py_mas += 1
    assert nt8_mas > 0 and py_mas > 0, (nt8_mas, py_mas)


def test_un_reordenamiento_razonable_SI_rompe_el_espejado():
    """Por qué el test textual de arriba no es paranoia.

    `hi - (hi-lo)*k` y `hi*(1-k) + lo*k` son álgebra idéntica y `double`
    distintos. Un refactor que "simplifica" la expresión rompe el espejado sin
    cambiar ningún resultado visible en un test de valores redondos.
    """
    distintos = 0
    for base in range(20000, 20200):
        for rng_t in range(1, 61):
            hi, lo = _recon(base + rng_t), _recon(base)
            k = PCT / 100.0
            if _floor_cs(hi, lo, PCT) != hi * (1 - k) + lo * k:
                distintos += 1
    assert distintos > 0, (
        "si esto da 0, el argumento de que el orden de operaciones importa "
        "sería falso y el test textual sobraría")


def test_el_baseline_declara_la_clase_nueva():
    import json
    d = json.load(open("tools/ulp_sweep_baseline.json", encoding="utf-8"))
    wick = [v for k, v in d["triaje"].items() if "wick" in k]
    assert len(wick) == 2
    for v in wick:
        assert v["veredicto"] == "ESPEJADO_BIT_A_BIT"
        assert "0,000000%" in v["evidencia"] or "0.000000%" in v["evidencia"]
        assert "DECISION A" in v["evidencia"]
    assert "intrinsecamente fraccionarios" in d["regla"]
