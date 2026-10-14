# -*- coding: utf-8 -*-
"""Tests rojos pre-fix para BigTrap2 v2.5.2 (defecto de export en tick:25).

Pre-registro completo, con las cuatro secciones D1-D4 y los criterios de
aceptacion: docs/BIGTRAP2_V252_PREREGISTRO_FIX_2026-08-11.md.

Alcance verificable desde este entorno: NO hay compilador de NinjaScript ni
runtime de NT8 aca, asi que T1-T4 se expresan como aserciones ESTATICAS sobre
el texto fuente de `nt8/BigTrap2.cs` (call sites, no comportamiento en vivo).
Confirman que el fix tiene la FORMA correcta a nivel de codigo; no sustituyen
la recaptura real de oraculos en NT8, que sigue siendo manual (ver el pre-
registro, seccion "como podria refutarse").

T5 y T6 corren contra codigo real (`edgelab.bridge.parity.match_zones`), pero
quedan xfail(strict=True) A PROPOSITO: prueban el matcher/gate de paridad
(`edgelab/bridge/parity.py`), que el pre-registro (D3, D4) declara FUERA DE
ALCANCE de este fix -- el fix es solo `.cs`. Van rojas antes Y despues de este
fix; se esperan verdes recien cuando alguien encare D3/D4 como campana propia.
"""
from __future__ import annotations

import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CS = os.path.join(REPO, "nt8", "BigTrap2.cs")

# los 7 call sites D1: reciben un BarSnap `s` (con s.Time correcto) y hoy
# formatean con el Time[0] vivo de LogEvent en vez de pasar s.Time.
SITIOS_D1 = ("ANCLAJE_VERIFICADO", "BARRA_PROCESADA", "TRAP",
             "ZONE_CREATED", "ZONE_EXPIRED", "ZONE_TOUCHED", "ZONE_INVALIDATED")
# subconjunto nombrado explicitamente en T2
SITIOS_T2 = ("ZONE_CREATED", "ZONE_TOUCHED", "ZONE_INVALIDATED",
             "ZONE_EXPIRED", "TRAP")


def _cs_source():
    if not os.path.exists(CS):
        pytest.skip("nt8/BigTrap2.cs no disponible")
    with open(CS, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _extract_block(source, signature_regex, max_lines=200):
    """Texto desde la primera linea que matchea `signature_regex` hasta la
    proxima declaracion de metodo (private/protected/public) al mismo nivel,
    o `max_lines` despues si no se encuentra antes. Evita depender de un
    contador de llaves balanceado -- varios metodos de este archivo tienen
    literales `string.Format("...{0}...")` que confundirian un brace-counter
    ingenuo."""
    lines = source.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.search(signature_regex, ln):
            start = i
            break
    assert start is not None, "no se encontro la firma /%s/ en BigTrap2.cs" % signature_regex
    end = min(len(lines), start + max_lines)
    for j in range(start + 1, end):
        if re.match(r"\s*(private|protected|public)\s+\S", lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


# --------------------------------------------------------------- T1, T2 (D1)
def test_t1_logeventat_existe_y_sesion_resincronizada_usa_tev():
    """T1 (general) + Fase 4 punto 3: LogEventAt(DateTime,...) debe existir
    como mecanismo, y el unico diagnostico nacido de un tick (no de un
    BarSnap) -- SESION_RESINCRONIZADA, dentro de AccumulateTick -- debe usar
    `tEv` (el timestamp propio del tick), no el Time[0] vivo."""
    source = _cs_source()
    assert re.search(r"private\s+void\s+LogEventAt\s*\(\s*DateTime\s+\w+", source), (
        "no existe un metodo LogEventAt(DateTime eventTime, ...) -- Fase 4 punto 1")
    assert 'LogEventAt(tEv, "SESION_RESINCRONIZADA"' in source, (
        "SESION_RESINCRONIZADA sigue estampado con Time[0] en vez de tEv "
        "(Fase 4 punto 3; tEv ya esta en scope en AccumulateTick, linea ~356)")


def test_t1_los_7_sitios_d1_usan_s_time():
    """T1: todo evento que procesa un BarSnap N conserva s.Time aunque
    LogEvent se invoque durante un callback posterior (drenaje diferido en
    tick:25). Cubre los 7 sitios D1, no solo los 5 que nombra T2 literalmente
    -- ANCLAJE_VERIFICADO y BARRA_PROCESADA comparten la misma exposicion
    estructural (mismo `s` en scope, mismo DrenarPorOHLCV) y quedaron
    incluidos por extension declarada en el pre-registro."""
    source = _cs_source()
    faltantes = []
    for tipo in SITIOS_D1:
        usa_s_time = ('LogEventAt(s.Time, "%s"' % tipo) in source
        usa_time0_viejo = ('LogEvent("%s"' % tipo) in source
        if not usa_s_time or usa_time0_viejo:
            faltantes.append((tipo, usa_s_time, usa_time0_viejo))
    assert not faltantes, (
        "sitios D1 que no pasaron a LogEventAt(s.Time, ...) (tipo, tiene_fix, "
        "conserva_llamada_vieja): %r" % faltantes)


def test_t2_zonas_y_trap_usan_tiempo_del_snapshot():
    """T2 literal: ZONE_CREATED, ZONE_TOUCHED, ZONE_INVALIDATED, ZONE_EXPIRED
    y TRAP usan el tiempo del snapshot correspondiente."""
    source = _cs_source()
    faltantes = [t for t in SITIOS_T2
                 if ('LogEventAt(s.Time, "%s"' % t) not in source]
    assert not faltantes, "sin s.Time todavia: %r" % faltantes


# --------------------------------------------------------------------- T3, T4 (D2)
def test_t3_bip1_drena_fifo_sin_exigir_otro_bip0():
    """T3: un snapshot cerrado que queda listo despues de AccumulateTick se
    drena sin exigir otro callback BIP0. Fix minimo: AccumulateTick (el
    handler de BIP1) tambien llama DrainReadyBars() -- la MISMA funcion que
    ya usa OnBarUpdate en BIP0, sin reanclar ni adivinar (DrenarPorOHLCV no
    se toca)."""
    source = _cs_source()
    body = _extract_block(source, r"private\s+void\s+AccumulateTick\s*\(\s*\)")
    assert "DrainReadyBars()" in body, (
        "AccumulateTick (BIP1) no llama DrainReadyBars() -- un snapshot "
        "listo debe poder drenar en el mismo tick que completa su bloque, "
        "no esperar al proximo cierre de barra primaria")


def test_t4_terminated_drena_sin_fabricar_barra_incompleta():
    """T4: el final del stream no pierde una barra completa ya cerrada, y no
    fabrica/procesa la barra primaria todavia incompleta. Fix minimo:
    State.Terminated llama DrainReadyBars() (que ya abstiene fail-closed
    ante datos incompletos -- ver DrenarPorOHLCV) ANTES de cerrar el writer."""
    source = _cs_source()
    idx = source.find("State == State.Terminated")
    assert idx >= 0, "no se encontro la rama State.Terminated"
    ventana = source[idx: idx + 1600]
    assert "DrainReadyBars()" in ventana, (
        "State.Terminated no llama DrainReadyBars() -- snapshots ya "
        "cerrados con bloque verificable quedan atrapados para siempre "
        "(ver D2: BARRA_PROCESADA se detuvo en bar=12397 con n_bars=12400)")
    pos_drain = ventana.index("DrainReadyBars()")
    pos_dispose = ventana.find("eventWriter.Dispose()")
    assert pos_dispose < 0 or pos_drain < pos_dispose, (
        "DrainReadyBars() debe correr ANTES de cerrar/disponer eventWriter, "
        "si no los eventos del drenaje final no llegan a escribirse")


# ------------------------------------------------- T5, T6 (D3/D4, xfail)
# Corren contra codigo real de edgelab/bridge/parity.py. Quedan xfail
# ESTRICTO A PROPOSITO: el pre-registro (D3, D4) declara el matcher y el gate
# de cobertura FUERA DE ALCANCE de v2.5.2 -- este fix es solo `.cs`. Si algun
# dia dejan de fallar sin que alguien haya encarado D3/D4 como campana propia,
# pytest reporta XPASS y la suite FALLA -- exactamente lo que se quiere: nadie
# lo relaja en silencio. Ver docs/BIGTRAP2_V252_PREREGISTRO_FIX_2026-08-11.md.
@pytest.mark.xfail(
    strict=True,
    reason="D3: el matcher de edgelab/bridge/parity.py no privilegia identidad "
           "estable sobre timestamp -- fuera de alcance del fix v2.5.2 (solo .cs). "
           "Ver docs/BIGTRAP2_V252_PREREGISTRO_FIX_2026-08-11.md")
def test_t5_matcher_no_cruza_zonas_de_geometria_identica():
    """T5: reproduccion sintetica minima del cruce 6095_S<->6093_S. Dos zonas
    Python con geometria IDENTICA (mismo nivel de precio, como 6093_S/6095_S
    en la campana real) y dos candidatas NT8 con timestamps corridos: el
    matcher greedy por (dt, geometria) de match_zones() no tiene ninguna
    nocion de identidad estable (created_bar/side/zone_id), asi que el par
    mas cercano EN TIEMPO gana aunque sea el equivocado."""
    from edgelab.bridge.parity import match_zones

    py_zones = [
        dict(id="Z93", created_ms=100_000, top=100.0, bottom=90.0),
        dict(id="Z95", created_ms=110_000, top=100.0, bottom=90.0),
    ]
    nt8_zones = [
        dict(id="Z93", created_ms=150_000, top=100.0, bottom=90.0),  # dt real=50000
        dict(id="Z95", created_ms=145_000, top=100.0, bottom=90.0),  # dt real=35000
    ]
    res = match_zones(py_zones, nt8_zones, tick_size=1.0)
    emparejado = dict(res["pairs"])
    assert emparejado == {"Z93": "Z93", "Z95": "Z95"}, (
        "el matcher cruzo identidades con geometria idntica y timestamps "
        "corridos: %r (se esperaba emparejamiento por id estable, no por "
        "cercania temporal)" % emparejado)


@pytest.mark.xfail(
    strict=True,
    reason="D4: no existe todavia una funcion de gate de cobertura "
           "BARRA_PROCESADA/TRAP en edgelab/bridge/parity.py -- fuera de "
           "alcance del fix v2.5.2 (solo .cs). Ver "
           "docs/BIGTRAP2_V252_PREREGISTRO_FIX_2026-08-11.md")
def test_t6_gate_falla_si_falta_cobertura_barra_procesada_o_trap():
    """T6: el gate de cobertura debe fallar si faltan BARRA_PROCESADA maduras
    o TRAP esperados, aunque las zonas coincidan -- el defecto D2 (3 barras y
    1 TRAP perdidos al final del stream) no dispara FAIL hoy porque
    match_zones() solo compara zonas, nunca cobertura de barras/trap."""
    import edgelab.bridge.parity as parity

    assert hasattr(parity, "check_coverage"), (
        "no existe parity.check_coverage(...) -- match_zones() no tiene "
        "ninguna nocion de cobertura BARRA_PROCESADA/TRAP; D2 (3 barras y 1 "
        "TRAP perdidos en tick:25 v2.5.1) pasaria el gate hoy sin ser detectado")
