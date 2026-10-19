# -*- coding: utf-8 -*-
"""Arnés de EXPLORE — probado SOLO con zonas sintéticas y placebos.

Ninguna zona real entra acá. El arnés tiene que demostrar que funciona sobre
datos con respuesta conocida antes de tocar el oráculo: si sobre un paseo
aleatorio con zonas al azar diera significancia, el problema sería el arnés y
cualquier resultado posterior no significaría nada.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pytest

from edgelab.research import explore as E
from edgelab.research import preregistro as PR


# ------------------------------------------------------------------ pre-registro
def _spec_valido():
    return dict(
        id="EXPLORE-001-TEST",
        hipotesis_unica="el primer toque de una zona produce excursion favorable",
        geometria=dict(objetivo_ticks=8, stop_ticks=13, horizonte_min=120),
        direccion_por_side={"trapped_buyers": -1, "trapped_sellers": 1},
        universo=dict(tipos_de_dia=["COMPLETO", "CIERRE_SEMANAL"],
                      instrumento="6E", manifiesto="runs/censo/manifiesto_universo.json"),
        nulo=dict(atlas_config_hash="deadbeef", estratos="4 franjas x 3 terciles"),
        metrica="tasa de objetivo antes que stop",
        criterio_exito="p95 del nulo + MCPT",
        inferencia=dict(bootstrap="estacionario_politis_white", permutacion="estratificada_por_dia", reps=10000),
        friccion_rt_ticks=2.7040,
        convencion_timeout="a_mercado",
        que_mata_la_idea="tasa dentro del IC del nulo en global y en todos los estratos",
        secundarios_no_deciden=["dosis-respuesta", "muerte de zona"])


def test_el_runner_se_niega_sin_preregistro(tmp_path):
    with pytest.raises(PR.PreRegistroError) as e:
        E.correr(str(tmp_path / "no_existe.json"),
                 geometria=dict(objetivo_ticks=8, stop_ticks=13, horizonte_min=120),
                 universo=dict(tipos_de_dia=["COMPLETO"]), cargar_series=None)
    assert "NO corre" in str(e.value)


def test_campo_faltante_no_se_puede_sellar(tmp_path):
    s = _spec_valido(); del s["direccion_por_side"]
    with pytest.raises(PR.PreRegistroError) as e:
        PR.sellar(s, str(tmp_path / "p.json"))
    assert "direccion_por_side" in str(e.value)


def test_direccion_sin_declarar_signo_no_pasa(tmp_path):
    """El grado de libertad mas barato de todos: elegir el signo que dio bien."""
    s = _spec_valido(); s["direccion_por_side"] = {"trapped_buyers": 0}
    with pytest.raises(PR.PreRegistroError) as e:
        PR.sellar(s, str(tmp_path / "p.json"))
    assert "+1 o -1" in str(e.value)


def test_editar_el_preregistro_despues_de_sellarlo_lo_invalida(tmp_path):
    p = str(tmp_path / "p.json")
    PR.sellar(_spec_valido(), p)
    d = json.load(open(p, encoding="utf-8"))
    d["geometria"]["objetivo_ticks"] = 13          # tuneo a posteriori
    json.dump(d, open(p, "w", encoding="utf-8"))
    with pytest.raises(PR.PreRegistroError) as e:
        PR.cargar_sellado(p)
    assert "se edito despues de sellarlo" in str(e.value)


def test_no_se_puede_resellar_encima(tmp_path):
    p = str(tmp_path / "p.json")
    PR.sellar(_spec_valido(), p)
    with pytest.raises(PR.PreRegistroError) as e:
        PR.sellar(_spec_valido(), p)
    assert "hipotesis NUEVA" in str(e.value)


def test_correr_con_geometria_distinta_de_la_sellada_levanta(tmp_path):
    p = str(tmp_path / "p.json")
    PR.sellar(_spec_valido(), p)
    with pytest.raises(PR.PreRegistroError) as e:
        E.correr(p, geometria=dict(objetivo_ticks=13, stop_ticks=8, horizonte_min=120),
                 universo=dict(tipos_de_dia=["COMPLETO", "CIERRE_SEMANAL"]),
                 cargar_series=None)
    assert "sello" in str(e.value)


def test_alcance_por_tipo_de_dia_distinto_levanta(tmp_path):
    p = str(tmp_path / "p.json")
    PR.sellar(_spec_valido(), p)
    with pytest.raises(PR.PreRegistroError) as e:
        E.correr(p, geometria=dict(objetivo_ticks=8, stop_ticks=13, horizonte_min=120),
                 universo=dict(tipos_de_dia=["COMPLETO"]), cargar_series=None)
    assert "MISMOS tipos" in str(e.value)


# ------------------------------------------------------------- clasificación
def test_objetivo_antes_que_stop_gana_el_primero():
    """Sube 8 y despues baja 13: tiene que dar OBJETIVO, no STOP."""
    px = np.array([0, 3, 8, -13, -20])
    r, v = E.clasificar_excursion(px, 0, +1, P=8, N=13, n_pasos=4)
    assert (r, v) == ("OBJETIVO", 8.0)


def test_stop_antes_que_objetivo_gana_el_primero():
    px = np.array([0, -13, 8, 20])
    r, v = E.clasificar_excursion(px, 0, +1, P=8, N=13, n_pasos=3)
    assert (r, v) == ("STOP", -13.0)


def test_la_direccion_declarada_invierte_el_resultado():
    px = np.array([0, -13, 0, 0])
    assert E.clasificar_excursion(px, 0, +1, 8, 13, 3)[0] == "STOP"
    assert E.clasificar_excursion(px, 0, -1, 8, 13, 3)[0] == "OBJETIVO"


def test_timeout_a_mercado_no_vale_cero():
    """La leccion de la tabla de decision: puntuar el timeout como 0 hace que
    las geometrias de objetivo cercano parezcan ventajosas cuando su esperanza
    a mercado es exactamente 0."""
    px = np.array([0, 1, 2, -5])
    assert E.clasificar_excursion(px, 0, +1, 8, 13, 3) == ("TIMEOUT", -5.0)
    assert E.clasificar_excursion(px, 0, +1, 8, 13, 3, "cero") == ("TIMEOUT", 0.0)


def test_sin_futuro_se_descarta_no_se_puntua_como_timeout():
    px = np.array([0, 1])
    assert E.clasificar_excursion(px, 1, +1, 8, 13, 10)[0] == "SIN_FUTURO"


# ------------------------------------------------ placebo: el arnés no inventa
def test_zonas_al_azar_sobre_paseo_aleatorio_NO_dan_significancia():
    """EL test que importa. Zonas colocadas al azar sobre una martingala: el
    p-valor tiene que ser aproximadamente uniforme, o sea rechazar al 5% en
    aproximadamente el 5% de las corridas. Si diera menos, el arnés fabrica
    significancia y ningun resultado suyo valdria nada."""
    rng = np.random.default_rng(20260727)
    rechazos = 0
    corridas = 60
    for c in range(corridas):
        por_dia_real, por_dia_cand = {}, {}
        for d in range(40):                       # 40 dias sinteticos
            px = np.cumsum(rng.choice([-1, 1], size=800)).astype(float)
            cand = []
            for i0 in range(0, 700, 20):          # anclas placebo del "atlas"
                _, v = E.clasificar_excursion(px, i0, +1, 8, 13, 60)
                cand.append(v)
            k = int(rng.integers(2, 6))           # 2..5 "zonas" ese dia
            elegidas = rng.choice(len(cand), size=k, replace=False)
            por_dia_real[d] = [cand[i] for i in elegidas]
            por_dia_cand[d] = cand
        r = E.permutacion_estratificada_por_dia(por_dia_real, por_dia_cand,
                                                reps=400, seed=1000 + c)
        if r and r["p_valor"] <= 0.05:
            rechazos += 1
    tasa = rechazos / corridas
    assert tasa <= 0.20, ("el arnes rechaza la nula en %.0f%% de los placebos; "
                          "deberia ser ~5%%" % (100 * tasa))


def test_una_senal_verdadera_SI_se_detecta():
    """Contraparte: si las zonas se colocan donde el futuro es favorable, el
    p-valor tiene que caer. Sin esto, el test anterior se pasaria con un arnes
    que nunca detecta nada."""
    rng = np.random.default_rng(5)
    por_dia_real, por_dia_cand = {}, {}
    for d in range(40):
        px = np.cumsum(rng.choice([-1, 1], size=800)).astype(float)
        cand = []
        for i0 in range(0, 700, 20):
            _, v = E.clasificar_excursion(px, i0, +1, 8, 13, 60)
            cand.append(v)
        orden = np.argsort(cand)[::-1]            # las 4 mejores del dia
        por_dia_real[d] = [cand[i] for i in orden[:4]]
        por_dia_cand[d] = cand
    r = E.permutacion_estratificada_por_dia(por_dia_real, por_dia_cand, reps=400)
    assert r["p_valor"] < 0.01, r


def test_marca_resolucion_baja_con_pocos_toques_por_dia():
    """Con 1-2 toques por dia hay pocas reasignaciones distintas y el p-valor
    pierde resolucion. Tiene que quedar dicho, no escondido."""
    rng = np.random.default_rng(2)
    real = {d: [float(rng.normal())] for d in range(30)}
    cand = {d: list(rng.normal(size=30)) for d in range(30)}
    r = E.permutacion_estratificada_por_dia(real, cand, reps=200)
    assert r["resolucion_baja"] is True


# ------------------------------------------------------------------ unidad = zona
def test_primer_toque_deja_un_evento_por_zona():
    toques = [dict(zone_id="A", ts="2026-06-15T10:00:00", side="x"),
              dict(zone_id="A", ts="2026-06-15T11:00:00", side="x"),
              dict(zone_id="B", ts="2026-06-15T09:00:00", side="x")]
    out = E.primer_toque(toques)
    assert len(out) == 2
    assert {t["zone_id"] for t in out} == {"A", "B"}
    assert next(t for t in out if t["zone_id"] == "A")["ts"].endswith("10:00:00")
