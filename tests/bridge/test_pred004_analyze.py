# -*- coding: utf-8 -*-
"""Batería sintética de `tools/pred004_analyze.py`.

Los logs se FABRICAN acá. **No se usa el oráculo nuevo ni ningún outcome**: el
instrumento tiene que quedar validado ANTES de que exista la captura que va a
medir, o se estaría calibrando contra el resultado.

Cada test corresponde a un ítem exigido por el auditor.

## REGLA OBLIGATORIA — citar la línea del `.cs` que emite cada evento

La batería v1 daba 30/30 y **validaba un emisor imaginario**: fabricaba un
`ANCLAJE_VERIFICADO` por barra, algo que el emisor real NO hace (se emite dentro
de `if (!anclado)`, `BigTrap2.cs:423`, o sea UNA VEZ POR SESIÓN). Por eso no vio
que el denominador de P1/P2 no existía en el log.

**Todo test que fabrique un evento debe citar la línea del `.cs` que lo emite.**
Si no se puede citar, el test valida una ficción.

| evento fabricado | lo emite | frecuencia real |
|---|---|---|
| `BARRA_PROCESADA` | `BigTrap2.cs:481` (v2.4) | **una por barra**, sólo camino de tick |
| `ANCLAJE_VERIFICADO` | `BigTrap2.cs:449`, dentro de `if (!anclado)` (423) | **una por sesión** |
| `ANCLAJE_AMBIGUO` | `BigTrap2.cs:493`, en `Abstener()` | por abstención |
| `FOOTPRINT_MISMATCH` | `BigTrap2.cs:529` y `589` | por barra con desajuste |
| `TRAP` / `ZONE_*` | `BigTrap2.cs:598+` | sólo con detección |
"""
from __future__ import annotations

import io
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))

import pred004_analyze as P  # noqa: E402

TZ = "America/Argentina/Buenos_Aires"   # tz del CHART, obligatoria (B1)

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


def _sesiones(n_sesiones, por_sesion, tipo_gen, anclaje_por_sesion=True):
    """Log FIEL al emisor real.

    `ANCLAJE_VERIFICADO` va UNA VEZ POR SESIÓN (`BigTrap2.cs:449`, dentro de
    `if (!anclado)` en 423) — ése fue el error de la v1, que lo ponía por barra.
    `BARRA_PROCESADA` va una por barra (`BigTrap2.cs:481`, v2.4)."""
    filas, seq, bar = [], 0, 0
    for s in range(n_sesiones):
        dia = 15 + s
        for b in range(por_sesion):
            ts = "2026-06-%02dT%02d:%02d:00.0000000" % (dia, 9 + (b // 60), b % 60)
            if b == 0 and anclaje_por_sesion:
                filas.append("%d|%s|ANCLAJE_VERIFICADO|bar=%d;offset=0;largo=25;k=25"
                             % (seq, ts, bar))
                seq += 1
            for tipo, extra in tipo_gen(s, b):
                filas.append("%d|%s|%s|bar=%d;%s" % (seq, ts, tipo, bar, extra))
                seq += 1
            bar += 1
    return filas


def test_p1p2_todo_verificado_sin_mismatch_es_PASS(tmp_path):
    g = lambda s, b: [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["estado"] == "PASS"
    assert r["tasa_mismatch_interior"] == 0.0
    assert r["barras_procesadas_interior"] == 120     # ancla en barra 0 => sin exclusion


def test_p1p2_mismatch_interior_se_cuenta(tmp_path):
    def g(s, b):
        out = [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
        if s == 1 and b < 15:            # 15 de 30 en una sesión interior
            out.append(("FOOTPRINT_MISMATCH", "n_eventos=25;k=25;open_blk=1;open_bar=2"))
        return out
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["footprint_mismatch_interior"] == 15
    assert r["estado"] == "FAIL"          # 15/120 = 12,5% > 1%
    assert r["p3_pares_procesados_sin_igualdad_ohlcv"] == 15
    assert r["p3_estado"] == "FAIL"


def test_p1p2_candidato_cero_nunca_cuenta_como_procesada(tmp_path):
    def g(s, b):
        if s == 1 and b < 10:
            return [("ANCLAJE_AMBIGUO", "candidatos=0;disponibles=3;largo=25;k=25")]
        return [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["candidatos_cero"] == 10
    assert r["barras_procesadas_interior"] == 110    # 120 - 10 ambiguas
    assert r["estado"] == "PASS"


def test_p1p2_candidatos_multiples_nunca_cuenta_como_procesada(tmp_path):
    def g(s, b):
        if s == 2 and b < 5:
            return [("ANCLAJE_AMBIGUO", "candidatos=3;disponibles=9;largo=25;k=25")]
        return [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["candidatos_multiples"] == 5
    assert r["barras_procesadas_interior"] == 115


def test_p1p2_ambigua_con_mismatch_no_infla_el_denominador(tmp_path):
    """Una barra que abstuvo NO es procesada aunque también emita mismatch.
    Contarla convertiría una abstención fail-closed en un acierto."""
    def g(s, b):
        if s == 1 and b < 10:
            return [("ANCLAJE_AMBIGUO", "candidatos=0;disponibles=2;largo=25;k=25"),
                    ("FOOTPRINT_MISMATCH", "n_eventos=25;k=25")]
        return [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["barras_procesadas_interior"] == 110
    assert r["footprint_mismatch_interior"] == 0     # las 10 no están en `proc`
    assert r["p4_estado"] == "PASS"                  # abstuvieron y NO se procesaron


def test_p1p2_denominador_cero_es_ABSTAIN_no_PASS(tmp_path):
    g = lambda s, b: [("ANCLAJE_AMBIGUO", "candidatos=0;disponibles=1;largo=25;k=25")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 10, g))
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["estado"] == "ABSTAIN"
    assert any("denominador 0" in d or "BARRA_PROCESADA" in d for d in r["diferencias"])


def test_p1p2_K25_y_K10_usan_las_MISMAS_reglas(tmp_path):
    """El contrato no puede cambiar entre resoluciones: mismo `contrato_sha`."""
    g = lambda s, b: [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
    a = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    b = _log(tmp_path / "b__Tick10.csv", META_23, _sesiones(4, 30, g))
    ra = P.modo_p1p2(a, TZ, "Tick25")
    rb = P.modo_p1p2(b, TZ, "Tick10")
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


# ---------------------------------------------------------------- v2: bloqueantes

def test_B1_la_tz_del_chart_cambia_la_sesion():
    """B1: `sesion_de` DEBE convertir. Con chart en ART, un evento a las 18:00
    locales son las 16:00 CT -> sesión anterior. Sin convertir, v1 lo mandaba a
    la siguiente."""
    ts = "2026-06-15T18:00:00.0000000"
    ses_art = P.sesion_de(ts, "America/Argentina/Buenos_Aires")
    ses_ct = P.sesion_de(ts, "America/Chicago")
    assert ses_art != ses_ct, "la tz del chart no está afectando la sesión: B1 sin arreglar"


def test_B1_sesion_tz_esta_realmente_en_uso():
    """El hash no puede certificar un parámetro inerte."""
    import inspect
    src = inspect.getsource(P.sesion_de)
    assert "SESION_TZ" in src and "astimezone" in src


def test_B2_CONTROL_NEGATIVO_defecto_real_de_v22_K25_da_FAIL(tmp_path):
    """CONTROL NEGATIVO obligatorio. Reproduce el defecto REAL de v2.2/K=25:
    485 mismatch confinados a las barras 1..2571 de 12.395.

    Con la regla vieja (warmup = primera sesión completa) esto borraba entre el
    48 % y el 80 % de la evidencia y el veredicto quedaba a 0,05 puntos del
    umbral, dependiendo de cuántas sesiones tuviera la captura. Debe dar FAIL
    de forma estable."""
    import random
    N, NSES, NMAL, TOPE = 12395, 5, 485, 2571
    por = N // NSES
    random.seed(7)
    malas = set(random.sample(range(1, TOPE + 1), NMAL))
    filas, seq = [], 0
    for b in range(N):
        ses = b // por
        ts = "2026-06-%02dT%02d:%02d:00.0000000" % (15 + ses, 9 + ((b % por) // 60) % 10, (b % por) % 60)
        if b % por == 0:
            filas.append("%d|%s|ANCLAJE_VERIFICADO|bar=%d;offset=0;largo=25;k=25" % (seq, ts, b)); seq += 1
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25;residual=False" % (seq, ts, b)); seq += 1
        if b in malas:
            filas.append("%d|%s|FOOTPRINT_MISMATCH|bar=%d;n_eventos=25;k=25;open_blk=1;open_bar=2"
                         % (seq, ts, b)); seq += 1
    p = _log(tmp_path / "v22__Tick25.csv", META_23, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["estado"] == "FAIL", "el contrato BORRA el defecto conocido de v2.2"
    assert r["footprint_mismatch_total"] == NMAL
    # La regla nueva NO borra evidencia: con el ancla establecida en la barra 0,
    # la tasa interior coincide con la total. Y esa total reproduce el 3,91 %
    # documentado para K=25 en PRED-003, que es el control externo del control.
    assert r["tasa_mismatch_interior"] == r["tasa_mismatch_total"]
    assert abs(r["tasa_mismatch_total"] - 0.0391) < 0.0002
    assert r["excluidos_por_warmup_barras"] == 0


def test_B3_P4_barra_ambigua_que_igual_se_proceso_es_FAIL(tmp_path):
    """B3: la abstención se VERIFICA, no se asume. Si una barra ambigua también
    emite ANCLAJE_VERIFICADO, P4 debe FALLAR — v1 la borraba del denominador y
    la reportaba como abstención, ocultando la violación."""
    filas, seq = [], 0
    for b in range(200):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25" % (seq, ts, b)); seq += 1
        if b == 100:
            filas.append("%d|%s|ANCLAJE_AMBIGUO|bar=%d;candidatos=3;disponibles=9;largo=25;k=25"
                         % (seq, ts, b)); seq += 1
    p = _log(tmp_path / "a__Tick25.csv", META_23, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["p4_estado"] == "FAIL"
    assert r["estado"] == "FAIL"
    assert 100 in r["p4_violaciones"]


def test_B3_P4_barra_ambigua_con_evento_economico_es_FAIL(tmp_path):
    """Una sesión con ambigüedad que igual sigue emitiendo ZONE_CREATED."""
    filas, seq = [], 0
    for b in range(200):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25" % (seq, ts, b)); seq += 1
    ts = "2026-06-15T10:30:00.0000000"
    filas.append("%d|%s|ANCLAJE_AMBIGUO|bar=150;candidatos=0;disponibles=2;largo=25;k=25" % (seq, ts)); seq += 1
    filas.append("%d|%s|ZONE_CREATED|bar=150;zone_id=9;lo=1.1;hi=1.2" % (seq, ts)); seq += 1
    p = _log(tmp_path / "a__Tick25.csv", META_23, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["p4_estado"] == "FAIL"
    assert 150 in r["p4_violaciones"]


def test_B4_P3_tiene_veredicto_propio_y_es_alcanzable(tmp_path):
    """B4: P3 debe fallar cuando un par PROCESADO no tiene igualdad OHLCV."""
    filas, seq = [], 0
    for b in range(200):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25" % (seq, ts, b)); seq += 1
        if b == 120:
            filas.append("%d|%s|FOOTPRINT_MISMATCH|bar=%d;n_eventos=25;k=25;open_blk=7;open_bar=9"
                         % (seq, ts, b)); seq += 1
    p = _log(tmp_path / "a__Tick25.csv", META_23, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["p3_estado"] == "FAIL"
    assert r["p3_pares_procesados_sin_igualdad_ohlcv"] == 1
    assert r["estado"] == "FAIL"


def test_B4_P3_no_cuenta_mismatch_de_barras_no_procesadas(tmp_path):
    """El contador de P3 se intersecta con `proc`: un mismatch en una barra que
    no fue procesada no puede inflarlo."""
    filas, seq = [], 0
    ts0 = "2026-06-15T09:00:00.0000000"
    filas.append("%d|%s|FOOTPRINT_MISMATCH|bar=0;n_eventos=25;k=25;open_blk=1;open_bar=2" % (seq, ts0)); seq += 1
    for b in range(1, 200):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25" % (seq, ts, b)); seq += 1
    p = _log(tmp_path / "a__Tick25.csv", META_23, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["p3_pares_procesados_sin_igualdad_ohlcv"] == 0
    assert r["p3_estado"] == "PASS"


def test_N3_sin_meta_es_ABSTAIN_nunca_medicion(tmp_path):
    p = str(tmp_path / "a__Tick25.csv")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("0|2026-06-15T09:00:00.0000000|BARRA_PROCESADA|bar=0;largo=25;k=25\n")
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["estado"] == "ABSTAIN"


def test_exigencia_transversal_publica_total_interior_y_exclusiones(tmp_path):
    """La exclusión no puede ser invisible."""
    filas, seq = [], 0
    for b in range(300):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25" % (seq, ts, b)); seq += 1
    p = _log(tmp_path / "a__Tick25.csv", META_23, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")
    for k in ("tasa_mismatch_total", "tasa_mismatch_interior",
              "excluidos_por_warmup_barras", "excluidos_por_tail_barras",
              "excluidos_por_warmup_eventos", "excluidos_por_tail_eventos",
              "barras_procesadas_total", "desglose_por_sesion"):
        assert k in r, "falta %s en la salida" % k


# ---------------------------------------------------------------- v2.4: H1 y H2

def _cs():
    return io.open(os.path.join(REPO, "nt8", "BigTrap2.cs"), encoding="utf-8").read()


def test_H1_el_cs_no_tiene_identificadores_sin_declarar():
    """H1: v2.3 tenia `if (!ok) { }` con `ok` sin declarar (CS0103): el archivo
    NO COMPILABA. Sobrevivio porque el pin compara sha256, y un archivo que no
    compila tiene un hash perfectamente valido. Ninguna verificacion del repo
    ejercitaba el compilador."""
    import re as _re
    assert not _re.search(r"(^|[^A-Za-z_])ok([^A-Za-z0-9_]|$)", _cs()), \
        "quedo un identificador `ok` sin declarar: el .cs no compila"


def test_H2_el_cs_emite_BARRA_PROCESADA_en_el_camino_de_tick():
    """H2: el denominador tiene que EXISTIR en el log. `BigTrap2.cs:481`."""
    src = _cs()
    assert 'LogEvent("BARRA_PROCESADA"' in src
    assert src.index("private void DrenarPorOHLCV()") < src.index('LogEvent("BARRA_PROCESADA"'), \
        "BARRA_PROCESADA quedo fuera de DrenarPorOHLCV (camino de tick)"


def test_H2_el_camino_de_TIEMPO_no_emite_BARRA_PROCESADA():
    """P5 exige time:1 bit-identico: el camino de tiempo NO se toca."""
    src = _cs()
    ini = src.index("if (fpTicksPerBar <= 0)")
    fin = src.index("private void DrenarPorOHLCV()")
    assert "BARRA_PROCESADA" not in src[ini:fin], \
        "el camino de tiempo emite BARRA_PROCESADA: rompe P5"


def test_H2_log_sin_BARRA_PROCESADA_es_ABSTAIN_no_PASS(tmp_path):
    """Un log de v2.3 o anterior NO tiene denominador. Con la v1 del analizador
    esto daba PASS con denominador 4-5; ahora tiene que abstenerse."""
    filas, seq = [], 0
    for b in range(300):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        if b == 0:
            filas.append("%d|%s|ANCLAJE_VERIFICADO|bar=0;offset=0;largo=25;k=25" % (seq, ts))
            seq += 1
        filas.append("%d|%s|FOOTPRINT_MISMATCH|bar=%d;n_eventos=25;k=25;open_blk=1;open_bar=2"
                     % (seq, ts, b))
        seq += 1
    p = _log(tmp_path / "v23__Tick25.csv", META_23, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["estado"] == "ABSTAIN"
    assert any("BARRA_PROCESADA" in d for d in r["diferencias"])


def test_H2_denominador_es_por_barra_no_por_sesion(tmp_path):
    """Con el emisor FIEL (un anclaje por sesion) el denominador es el numero de
    BARRAS, no el de sesiones. Con la v1 esto daba 4."""
    g = lambda s, b: [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(4, 30, g))
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["barras_procesadas_interior"] == 120
    assert r["anclajes_verificados"] == 4


def test_menor1_P4_detecta_aunque_el_economico_preceda_al_ambiguo(tmp_path):
    """El orden intra-barra no puede decidir si se ve la violacion: dos pasadas."""
    filas, seq = [], 0
    for b in range(200):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25" % (seq, ts, b))
        seq += 1
    ts = "2026-06-15T10:30:00.0000000"
    filas.append("%d|%s|ZONE_CREATED|bar=150;zone_id=9;lo=1.1;hi=1.2" % (seq, ts))
    seq += 1
    filas.append("%d|%s|ANCLAJE_AMBIGUO|bar=150;candidatos=0;disponibles=2;largo=25;k=25"
                 % (seq, ts))
    p = _log(tmp_path / "a__Tick25.csv", META_23, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["p4_estado"] == "FAIL", "el economico precedia al ambiguo y se perdia"


def test_menor5_p5_time_rechaza_resolucion_que_no_corresponde(tmp_path):
    a = _log(tmp_path / "h__Minute1.csv", META_21, _eco_basico())
    b = _log(tmp_path / "n__Tick25.csv", META_23, _eco_basico())
    assert P.modo_p5(a, b, "Minute1")["estado"] == "ABSTAIN"


def test_menor6_ABSTAIN_no_comparte_exit_code_con_PASS(tmp_path):
    """Abstencion NO es aprobacion: 0=PASS, 1=FAIL, 2=ABSTAIN."""
    ok = _log(tmp_path / "a__Tick25.csv", META_23, _eco_basico())
    assert P.main(["p6-file", "--log", ok, "--resolucion", "Tick25"]) == 0
    sin = str(tmp_path / "b__Tick25.csv")
    with open(sin, "w", encoding="utf-8") as fh:
        fh.write("0|2026-06-15T09:00:00.0000000|ANCLAJE_VERIFICADO|bar=0;largo=25;k=25\n")
    assert P.main(["p1-p2-tick", "--log", sin, "--tz-chart", TZ, "--resolucion", "Tick25"]) == 2


# ======================================================================== G0
# Reproducciones de las tres iteraciones independientes. DEBEN FALLAR antes de
# G1. Cada fixture declara si es `emisor_fiel` o `emisor_adversarial`.

META_24 = META_23.replace("version=2.3", "version=2.4")


def test_G0_H_GPT_1_rama_denom_cero_alcanzada_de_verdad(tmp_path):
    """emisor_adversarial. H-GPT-1 / H-GROK-1 / F1.

    La rama `denom == 0` usa `verif`, que NO esta definido en el modulo:
    NameError. El test viejo que la nombra NO la alcanza -abstiene antes, en
    `primera_ok is None`- asi que el nombre prometia una alcanzabilidad que el
    fixture no entregaba. TERCERA instancia del modo de falla de B3 y H2.

    Adversarial a proposito: el emisor fiel no emite ANCLAJE_AMBIGUO
    (`BigTrap2.cs:493`) sobre una barra que ademas emitio BARRA_PROCESADA
    (`481`). El analizador tiene que SOBREVIVIR igual, porque una rama de
    defensa que explota no defiende.
    """
    filas, seq = [], 0
    for b in range(300):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25;residual=False"
                     % (seq, ts, b)); seq += 1
        filas.append("%d|%s|ANCLAJE_AMBIGUO|bar=%d;candidatos=0;disponibles=2;largo=25;k=25"
                     % (seq, ts, b)); seq += 1
    p = _log(tmp_path / "adv__Tick25.csv", META_24, filas)
    r = P.modo_p1p2(p, TZ, "Tick25")          # hoy: NameError
    assert r["estado"] == "ABSTAIN"
    assert r["barras_procesadas_interior"] == 0


def test_G0_H_GPT_1_la_rama_ABSTAIN_publica_los_mismos_campos(tmp_path):
    """H-KIMI-1 aplicado a H-GPT-1: si la rama de abstencion publica menos
    campos que la salida normal, el consumidor no puede distinguir un ABSTAIN
    de una salida TRUNCADA. Contabilidad, no cosmetica."""
    filas, seq = [], 0
    for b in range(300):
        ts = "2026-06-15T%02d:%02d:00.0000000" % (9 + b // 60, b % 60)
        filas.append("%d|%s|BARRA_PROCESADA|bar=%d;largo=25;k=25" % (seq, ts, b)); seq += 1
        filas.append("%d|%s|ANCLAJE_AMBIGUO|bar=%d;candidatos=2;disponibles=2;largo=25;k=25"
                     % (seq, ts, b)); seq += 1
    abst = P.modo_p1p2(_log(tmp_path / "a__Tick25.csv", META_24, filas), TZ, "Tick25")

    g = lambda s_, b_: [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
    ok = P.modo_p1p2(_log(tmp_path / "b__Tick25.csv", META_24, _sesiones(2, 200, g)),
                     TZ, "Tick25")
    faltantes = set(ok) - set(abst)
    assert not faltantes, "la rama ABSTAIN no publica: %s" % sorted(faltantes)


def test_G0_H_GPT_2_p5_sin_resolucion_no_puede_dar_PASS(tmp_path):
    """emisor_fiel. H-GPT-2 / F4. `--resolucion` es `default=None` y cada modo
    hace `if resolucion_esperada:`, asi que OMITIRLA saltea el chequeo entero.
    Un Tick25 se puede comparar contra el historico de minuto sin acreditar
    nada. Agregar la opcion no hizo obligatoria la precondicion."""
    a = _log(tmp_path / "h__Minute1.csv", META_21, _eco_basico())
    b = _log(tmp_path / "n__Minute1.csv", META_23, _eco_basico())
    assert P.modo_p5(a, b)["estado"] != "PASS"


def test_G0_H_GPT_2_cli_sin_resolucion_no_devuelve_cero(tmp_path):
    """La CLI es la superficie real. Sin `--resolucion` no puede salir 0."""
    a = _log(tmp_path / "h__Minute1.csv", META_21, _eco_basico())
    b = _log(tmp_path / "n__Minute1.csv", META_23, _eco_basico())
    assert P.main(["p5-time", "--historico", a, "--nuevo", b]) != 0


def test_G0_H_KIMI_3_toda_tasa_publicada_declara_su_poblacion(tmp_path):
    """H-KIMI-3. `footprint_mismatch_total` cuenta TODAS las barras con
    mismatch; `tasa_mismatch_total` divide sobre las PROCESADAS. Poblaciones
    distintas con nombres hermanos: quien reconcilie
    `tasa_total x barras_procesadas_total` contra el contador va a obtener otro
    numero. El contrato v3 declara este "menor 3" CORREGIDO -corregi la tasa y
    no el contador-.

    Misma familia que H2 y B1: un numero publicado cuyo denominador nadie puede
    reconstruir.
    """
    def gen(s_, b_):
        ev = [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
        if b_ % 50 == 7:
            ev.append(("FOOTPRINT_MISMATCH",
                       "n_eventos=25;k=25;open_blk=1;open_bar=2"))
        return ev
    filas = _sesiones(2, 200, gen)
    # mismatch en una barra del WARMUP -> queda fuera de `procesadas`? no: es
    # procesada. Se fabrica ademas un mismatch SIN BARRA_PROCESADA, que es el
    # caso que rompe la reconciliacion.
    filas.append("999999|2026-06-16T11:30:00.0000000|FOOTPRINT_MISMATCH|"
                 "bar=100000;n_eventos=25;k=25;open_blk=1;open_bar=2")
    r = P.modo_p1p2(_log(tmp_path / "a__Tick25.csv", META_24, filas), TZ, "Tick25")

    assert "barras_totales_en_log" in r, "no se publica el universo de barras"
    assert "nota_poblaciones" in r, "ninguna nota advierte la no-reconciliacion"
    # el contador que acompana a la tasa tiene que compartir su poblacion
    assert r["mismatch_total_en_procesadas"] == round(
        r["tasa_mismatch_total"] * r["barras_procesadas_total"])


def test_G0_H_GROK_4_meta_de_version_incoherente_es_ABSTAIN(tmp_path):
    """H-GROK-4 / H-KIMI-7 / K5. Un log `version=2.3` que trae BARRA_PROCESADA
    -evento que solo existe en v2.4- se mide igual. Escenario real: una v2.4
    mal instalada, o un binario viejo cacheado por NT8."""
    g = lambda s_, b_: [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
    p = _log(tmp_path / "a__Tick25.csv", META_23, _sesiones(2, 200, g))
    r = P.modo_p1p2(p, TZ, "Tick25", exigir_version="2.4")
    assert r["estado"] == "ABSTAIN"
    assert any("2.4" in d for d in r["diferencias"])


def test_G0_H_GPT_6_P3_no_certifica_OHLCV_sin_haber_visto_la_V(tmp_path):
    """emisor_adversarial. H-GPT-6. Un FOOTPRINT_MISMATCH de barra procesada
    con OHLC coincidente y SIN `vol_blk`/`vol_bar`: hoy `campos_p3` es True
    -alcanza con que este `open_blk`- y P3 sale PASS. Estaria certificando
    igualdad OHLC-V sin haber visto nunca la V."""
    def gen(s_, b_):
        ev = [("BARRA_PROCESADA", "largo=25;k=25;residual=False")]
        if b_ == 100:
            ev.append(("FOOTPRINT_MISMATCH",
                       "n_eventos=25;k=25;open_blk=1;open_bar=1;close_blk=2;close_bar=2"))
        return ev
    p = _log(tmp_path / "a__Tick25.csv", META_24, _sesiones(2, 200, gen))
    r = P.modo_p1p2(p, TZ, "Tick25")
    assert r["p3_estado"] != "PASS", "P3 certifico OHLCV sin ver vol_blk/vol_bar"


def test_G0_H_GROK_3_ningun_mensaje_habla_de_ANCLAJE_como_warmup():
    """H-GROK-3. El warmup usa BARRA_PROCESADA desde v3, pero quedaron mensajes
    y docstrings con la semantica vieja. No es nitpick: el proximo lector
    reintroduce el denominador-por-anclaje leyendo el mensaje."""
    src = io.open(os.path.join(REPO, "tools", "pred004_analyze.py"),
                  encoding="utf-8").read()
    import re as _re
    malos = [l for l in src.splitlines()
             if _re.search(r"(warm|warmup|interior)", l, _re.I)
             and "ANCLAJE_VERIFICADO" in l]
    assert not malos, "mensajes de warmup con semantica vieja: %s" % malos
