# -*- coding: utf-8 -*-
"""Batería sintética de `tools/pred004_analyze.py`.

Los logs se FABRICAN acá. **No se usa el oráculo nuevo ni ningún outcome**: el
instrumento tiene que quedar validado ANTES de que exista la captura que va a
medir, o se estaría calibrando contra el resultado.

Cada test corresponde a un ítem exigido por el auditor.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))

import pred004_analyze as P  # noqa: E402

META_21 = ("# meta indicator=BigTrap2,version=2.1,footprint=reconstructed_1tick_subseries,"
           "imbalance_mode=Diagonal,trap_volume=AggressiveSide,ticks_per_row=1,"
           "imbalance_ratio=3,wick_filter=True,wick_zone_pct=30,min_delta=0,"
           "max_age_bars=2000,tick_size=5E-05,instrument=6E 09-26")
META_23 = ("# meta indicator=BigTrap2,version=2.3,attribution=ohlcv_unique_match,"
           "anchor=bounded_verified,footprint=reconstructed_1tick_subseries,"
           "imbalance_mode=Diagonal,trap_volume=AggressiveSide,ticks_per_row=1,"
           "imbalance_ratio=3,wick_filter=True,wick_zone_pct=30,min_delta=0,"
           "max_age_bars=2000,tick_size=5E-05,instrument=6E 09-26")


def _eco(seq, ts, tipo="TRAP", extra="zone_id=1;lo=1.1;hi=1.2;vol=30"):
    return "%d|%s|%s|%s" % (seq, ts, tipo, extra)


def _log(path, meta, filas):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(meta + "\n")
        for f in filas:
            fh.write(f + "\n")
    return str(path)


def _eco_basico():
    return [_eco(0, "2026-06-15T09:00:00.0000000"),
            _eco(1, "2026-06-15T09:01:00.0000000"),
            _eco(2, "2026-06-15T09:02:00.0000000", "ZONE_CREATED",
                 "zone_id=1_S;created_bar=5;side=trapped_sellers;lo=1.1;hi=1.2;vol=44")]


# ---------------------------------------------------------------- P5


def test_p5_identico_salvo_version_permitida_es_PASS(tmp_path):
    """El caso que debe pasar: sólo difiere metadata de la lista cerrada."""
    a = _log(tmp_path / "h.csv", META_21, _eco_basico())
    b = _log(tmp_path / "n.csv", META_23, _eco_basico())
    r = P.modo_p5(a, b)
    assert r["estado"] == "PASS", r["diferencias"]


def test_p5_evento_cambiado_es_FAIL(tmp_path):
    a = _log(tmp_path / "h.csv", META_21, _eco_basico())
    f = _eco_basico()
    f[1] = _eco(1, "2026-06-15T09:01:00.0000000", "TRAP", "zone_id=1;lo=1.1;hi=1.9;vol=30")
    b = _log(tmp_path / "n.csv", META_23, f)
    r = P.modo_p5(a, b)
    assert r["estado"] == "FAIL"
    assert any("hi" in d for d in r["diferencias"])


def test_p5_fila_agregada_es_FAIL(tmp_path):
    a = _log(tmp_path / "h.csv", META_21, _eco_basico())
    b = _log(tmp_path / "n.csv", META_23, _eco_basico() + [_eco(3, "2026-06-15T09:03:00.0000000")])
    r = P.modo_p5(a, b)
    assert r["estado"] == "FAIL"
    assert any("cantidad de eventos" in d for d in r["diferencias"])


def test_p5_fila_eliminada_es_FAIL(tmp_path):
    a = _log(tmp_path / "h.csv", META_21, _eco_basico())
    b = _log(tmp_path / "n.csv", META_23, _eco_basico()[:-1])
    r = P.modo_p5(a, b)
    assert r["estado"] == "FAIL"


def test_p5_timestamp_cambiado_es_FAIL(tmp_path):
    a = _log(tmp_path / "h.csv", META_21, _eco_basico())
    f = _eco_basico()
    f[1] = _eco(1, "2026-06-15T09:01:00.5000000")
    b = _log(tmp_path / "n.csv", META_23, f)
    r = P.modo_p5(a, b)
    assert r["estado"] == "FAIL"
    assert any("ts" in d for d in r["diferencias"])


def test_p5_metadata_NO_permitida_cambiada_es_FAIL(tmp_path):
    """`imbalance_ratio` no está en la lista cerrada: cambiarlo debe romper P5."""
    a = _log(tmp_path / "h.csv", META_21, _eco_basico())
    b = _log(tmp_path / "n.csv", META_23.replace("imbalance_ratio=3", "imbalance_ratio=4"),
             _eco_basico())
    r = P.modo_p5(a, b)
    assert r["estado"] == "FAIL"
    assert any("imbalance_ratio" in d for d in r["diferencias"])


def test_p5_formatos_no_comparables_es_ABSTAIN_no_PASS(tmp_path):
    """Sin `# meta` no se puede comparar: ABSTAIN, nunca PASS."""
    a = str(tmp_path / "h.csv")
    with open(a, "w", encoding="utf-8") as fh:
        fh.write(_eco(0, "2026-06-15T09:00:00.0000000") + "\n")
    b = _log(tmp_path / "n.csv", META_23, _eco_basico())
    r = P.modo_p5(a, b)
    assert r["estado"] == "ABSTAIN"


def test_p5_sin_eventos_economicos_es_ABSTAIN(tmp_path):
    a = _log(tmp_path / "h.csv", META_21, ["0|2026-06-15T09:00:00.0000000|ERROR|code=x"])
    b = _log(tmp_path / "n.csv", META_23, _eco_basico())
    r = P.modo_p5(a, b)
    assert r["estado"] == "ABSTAIN"


# ---------------------------------------------------------------- P6


def test_p6_archivo_limpio_es_PASS(tmp_path):
    p = _log(tmp_path / "BigTrap2__Tick25.csv", META_23, _eco_basico())
    r = P.modo_p6(p, "Tick25")
    assert r["estado"] == "PASS", r["diferencias"]


def test_p6_dos_corridas_appendeadas_es_FAIL(tmp_path):
    """El defecto real de `BigTrap2_tick25_6E_0926_v22.csv`: tres corridas
    appendeadas, cada una arrancando en seq=0, con un solo `# meta`."""
    filas = _eco_basico() + [_eco(0, "2026-06-16T09:00:00.0000000"),
                             _eco(1, "2026-06-16T09:01:00.0000000")]
    p = _log(tmp_path / "x__Tick25.csv", META_23, filas)
    r = P.modo_p6(p, "Tick25")
    assert r["estado"] == "FAIL"
    assert any("inicios de seq" in d for d in r["diferencias"])


def test_p6_dos_meta_es_FAIL(tmp_path):
    p = str(tmp_path / "x__Tick25.csv")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(META_23 + "\n")
        fh.write(_eco(0, "2026-06-15T09:00:00.0000000") + "\n")
        fh.write(META_23 + "\n")
        fh.write(_eco(1, "2026-06-15T09:01:00.0000000") + "\n")
    r = P.modo_p6(p, "Tick25")
    assert r["estado"] == "FAIL"
    assert any("meta" in d for d in r["diferencias"])


def test_p6_resolucion_que_no_corresponde_es_FAIL(tmp_path):
    """No se asume el nombre: se verifica. El .cs compone BarsPeriodType+Value,
    así que minuto es `Minute1`, NO `time1`."""
    p = _log(tmp_path / "x__Tick10.csv", META_23, _eco_basico())
    r = P.modo_p6(p, "Tick25")
    assert r["estado"] == "FAIL"
    assert any("resolución" in d or "resolucion" in d for d in r["diferencias"])


# ---------------------------------------------------------------- P1/P2


def _sesiones(n_sesiones, por_sesion, tipo_gen):
    """Genera `n_sesiones` sesiones de `por_sesion` barras. `tipo_gen(s,b)`
    devuelve la lista de (tipo, payload_extra) de esa barra."""
    filas, seq = [], 0
    for s in range(n_sesiones):
        dia = 15 + s
        for b in range(por_sesion):
            ts = "2026-06-%02dT%02d:%02d:00.0000000" % (dia, 9 + (b // 60), b % 60)
            for tipo, extra in tipo_gen(s, b):
                filas.append("%d|%s|%s|bar=%d;%s" % (seq, ts, tipo, b, extra))
                seq += 1
    return filas


def test_p1p2_todo_verificado_sin_mismatch_es_PASS(tmp_path):
    g = lambda s, b: [("ANCLAJE_VERIFICADO", "k=25")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["estado"] == "PASS"
    assert r["tasa_mismatch_interior"] == 0.0
    assert r["barras_procesadas_interior"] == 60      # 4 sesiones - warmup - tail


def test_p1p2_mismatch_interior_se_cuenta(tmp_path):
    def g(s, b):
        out = [("ANCLAJE_VERIFICADO", "k=25")]
        if s == 1 and b < 15:            # 15 de 30 en una sesión interior
            out.append(("FOOTPRINT_MISMATCH", "n_eventos=25;k=25;open_blk=1;open_bar=2"))
        return out
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["footprint_mismatch_interior"] == 15
    assert r["estado"] == "FAIL"          # 15/60 = 25% > 1%
    assert r["pares_procesados_sin_igualdad_ohlcv"] == 15


def test_p1p2_mismatch_en_warmup_se_excluye(tmp_path):
    """Regla congelada: la PRIMERA sesión es warmup y no entra al denominador
    ni al numerador."""
    def g(s, b):
        out = [("ANCLAJE_VERIFICADO", "k=25")]
        if s == 0:                        # toda la sesión de warmup en mismatch
            out.append(("FOOTPRINT_MISMATCH", "n_eventos=25;k=25"))
        return out
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["footprint_mismatch_interior"] == 0
    assert r["estado"] == "PASS"
    assert r["excluidos_por_warmup_o_tail"].get("FOOTPRINT_MISMATCH") == 30


def test_p1p2_mismatch_en_tail_se_excluye(tmp_path):
    def g(s, b):
        out = [("ANCLAJE_VERIFICADO", "k=25")]
        if s == 3:                        # última sesión = maturity tail
            out.append(("FOOTPRINT_MISMATCH", "n_eventos=25;k=25"))
        return out
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["footprint_mismatch_interior"] == 0
    assert r["estado"] == "PASS"


def test_p1p2_candidato_cero_nunca_cuenta_como_procesada(tmp_path):
    def g(s, b):
        if s == 1 and b < 10:
            return [("ANCLAJE_AMBIGUO", "candidatos=0;disponibles=3;largo=25;k=25")]
        return [("ANCLAJE_VERIFICADO", "k=25")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["barras_ambiguas_interior"] == 10
    assert r["candidatos_cero"] == 10
    assert r["barras_procesadas_interior"] == 50     # 60 - 10 ambiguas
    assert r["estado"] == "PASS"


def test_p1p2_candidatos_multiples_nunca_cuenta_como_procesada(tmp_path):
    def g(s, b):
        if s == 2 and b < 5:
            return [("ANCLAJE_AMBIGUO", "candidatos=3;disponibles=9;largo=25;k=25")]
        return [("ANCLAJE_VERIFICADO", "k=25")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["candidatos_multiples"] == 5
    assert r["barras_procesadas_interior"] == 55


def test_p1p2_ambigua_con_mismatch_no_infla_el_denominador(tmp_path):
    """Una barra que abstuvo NO es procesada aunque también emita mismatch.
    Contarla convertiría una abstención fail-closed en un acierto."""
    def g(s, b):
        if s == 1 and b < 10:
            return [("ANCLAJE_AMBIGUO", "candidatos=0;disponibles=2;largo=25;k=25"),
                    ("FOOTPRINT_MISMATCH", "n_eventos=25;k=25")]
        return [("ANCLAJE_VERIFICADO", "k=25")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["barras_procesadas_interior"] == 50
    assert r["footprint_mismatch_interior"] == 0     # las 10 no están en `proc`


def test_p1p2_denominador_cero_es_ABSTAIN_no_PASS(tmp_path):
    g = lambda s, b: [("ANCLAJE_AMBIGUO", "candidatos=0;disponibles=1;largo=25;k=25")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 10, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["estado"] == "ABSTAIN"
    assert any("denominador 0" in d for d in r["diferencias"])


def test_p1p2_sin_interior_es_ABSTAIN(tmp_path):
    """Con 2 sesiones, warmup+tail consumen todo: no hay interior."""
    g = lambda s, b: [("ANCLAJE_VERIFICADO", "k=25")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(2, 30, g))
    r = P.modo_p1p2(p, "Tick25")
    assert r["estado"] == "ABSTAIN"


def test_p1p2_K25_y_K10_usan_las_MISMAS_reglas(tmp_path):
    """El contrato no puede cambiar entre resoluciones: mismo `contrato_sha`."""
    g = lambda s, b: [("ANCLAJE_VERIFICADO", "k=25")]
    a = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    b = _log(tmp_path / "b__Tick10.csv", META_23, _sesiones(4, 30, g))
    ra = P.modo_p1p2(a, "Tick25")
    rb = P.modo_p1p2(b, "Tick10")
    assert ra["contrato_sha"] == rb["contrato_sha"]
    assert ra["contrato"] == rb["contrato"]


# ---------------------------------------------------------------- contrato


def test_el_contrato_esta_congelado_y_es_hasheable():
    s1, s2 = P.contrato_sha(), P.contrato_sha()
    assert s1 == s2 and len(s1) == 64


def test_el_resultado_es_content_addressed(tmp_path):
    """El veredicto no se redacta a mano: sale con su propio sha256."""
    p = _log(tmp_path / "a__Tick25.csv", META_23, _eco_basico())
    out = str(tmp_path / "r.json")
    P.main(["p6-file", "--log", p, "--resolucion", "Tick25", "--out", out])
    d = json.load(open(out, encoding="utf-8"))
    assert len(d["resultado_sha256"]) == 64
    assert d["contrato_sha"] == P.contrato_sha()
