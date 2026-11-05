"""Tests unitarios para `gestor_canastas_regimen.py`, `emisor_senales_nt8.py` y `simulador_challenges_propfirm.py` (2026-10-29)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research import gestor_canastas_regimen as GCR
from tools import emisor_senales_nt8 as ESN, simulador_challenges_propfirm as SCP


def test_compuerta_anti_aplanamiento_rechaza_curva_plana_y_acepta_sostenida() -> None:
    # Caso 1: Estrategia sostenida en H1 (Abr-Jun) y H2 (Jul-Sep)
    t_sostenida = [
        1775500000 + i * 350000 for i in range(40)  # distribuida entre Abril y Septiembre 2026
    ]
    ses_sostenida = [20260405 + (i * 5) for i in range(20)] + [20260705 + (i * 5) for i in range(20)]
    neto_sostenida = [12.0 if i % 3 != 0 else -6.0 for i in range(40)]
    df_ok = pd.DataFrame({"celda": 0, "t": t_sostenida, "ses": ses_sostenida, "k": range(40), "neto": neto_sostenida})

    rep_ok = GCR.auditar_aplanamiento_oos(df_ok, instrumento="NQ", cid="TEST_SOSTENIDA")
    assert rep_ok["aprobada"] is True
    assert rep_ok["veredicto"] == "APROBADA_OOS_SOSTENIDA"
    assert rep_ok["h1_usd"] > 0 and rep_ok["h2_usd"] > 0
    assert rep_ok["r2_linealidad"] >= 0.85

    # Caso 2: Estrategia sobreajustada que gana en H1 pero se aplana/pierde en H2
    neto_plana = [25.0 for _ in range(20)] + [-5.0 for _ in range(20)]
    df_plana = pd.DataFrame({"celda": 0, "t": t_sostenida, "ses": ses_sostenida, "k": range(40), "neto": neto_plana})
    rep_plana = GCR.auditar_aplanamiento_oos(df_plana, instrumento="NQ", cid="TEST_PLANA")
    assert rep_plana["aprobada"] is False
    assert "aplanada_mitad_2<=0" in rep_plana["motivos_rechazo"]


def test_podar_canasta_ortogonal_elimina_redundantes_y_aplanadas() -> None:
    t_base = [1775500000 + i * 350000 for i in range(30)]
    ses_base = [20260405 + i * 3 for i in range(15)] + [20260705 + i * 3 for i in range(15)]
    # Celda 0 y Celda 1 idénticas (correlación 1.0 -> debe quedarse sólo con una), Celda 2 ortogonal, Celda 3 aplanada en H2
    filas = []
    for i in range(30):
        filas.append({"celda": 0, "t": t_base[i], "ses": ses_base[i], "k": i, "neto": 15.0 if i % 2 == 0 else -4.0})
        filas.append({"celda": 1, "t": t_base[i], "ses": ses_base[i], "k": i, "neto": 15.0 if i % 2 == 0 else -4.0})
        filas.append({"celda": 2, "t": t_base[i] + 1800, "ses": ses_base[i], "k": i + 1, "neto": 14.0 if i % 2 == 1 else -3.0})
        filas.append({"celda": 3, "t": t_base[i] + 3600, "ses": ses_base[i], "k": i + 2, "neto": 20.0 if i < 15 else -10.0})
    df_ops = pd.DataFrame(filas)

    res = GCR.podar_canasta_ortogonal(df_ops, n_celdas=4, instrumento="NQ", cid="TEST_CANASTA", max_k=3, max_corr=0.35)
    assert res["aprobada"] is True
    # No puede elegir simultáneamente 0 y 1 (correlación 1.0), ni puede elegir 3 (aplanada en H2)
    sel = res["pistas_seleccionadas"]
    assert 3 not in sel
    assert not (0 in sel and 1 in sel)
    assert len(sel) == 2


def test_gestor_dinamico_causal_es_estrictamente_causal() -> None:
    filas = []
    for s_idx in range(20):
        ses = 20260401 + s_idx
        # Unidad A gana siempre; Unidad B pierde durante 10 sesiones seguidas
        filas.append({"t": 1775000000 + s_idx * 86400, "ses": ses, "usd": 100.0, "unit_id": "U_A"})
        filas.append({"t": 1775000100 + s_idx * 86400, "ses": ses, "usd": -80.0 if s_idx < 15 else 500.0, "unit_id": "U_B"})
    df = pd.DataFrame(filas)

    out_total = GCR.gestor_dinamico_causal_sesion(df, ventana_sesiones_freno=8, min_ops_warmup=5, umbral_pf_freno=0.85)
    out_parcial = GCR.gestor_dinamico_causal_sesion(df[df["ses"] <= 20260412], ventana_sesiones_freno=8, min_ops_warmup=5, umbral_pf_freno=0.85)

    # Verificar causalidad estricta: los pesos hasta 20260412 no cambian al ver sesiones posteriores
    for s in range(20260401, 20260413):
        assert out_total["pesos_por_sesion"][s] == out_parcial["pesos_por_sesion"][s]
    # Verificar que el freno de sombra bloqueó a U_B tras su racha negativa y mejoró el resultado neto
    assert out_total["n_ops_frenadas_en_sombra"] > 0


def test_emisor_nt8_y_simulador_propfirm(tmp_path: Path) -> None:
    res_nt8 = ESN.generar_artefactos_nt8(tmp_path)
    assert res_nt8["ok"] is True
    assert res_nt8["n_unidades_aprobadas"] == 12
    assert (tmp_path / "config/autopilot/nt8_canasta_aprobada_20261029.json").exists()
    assert (tmp_path / "config/autopilot/nt8_regime_mask_20261029.txt").exists()

    pnl_dias = np.array([220.0, 180.0, -90.0, 310.0, 150.0] * 25, dtype=float)
    sim = SCP.simular_challenge_montecarlo(pnl_dias, SCP.PERFILES_CUENTAS_PROPFIRM[0], n_simulaciones=500)
    assert sim["pass_rate_pct"] > 90.0
    assert sim["ev_neto_primer_payout_usd"] > 1000.0


def test_desduplicar_exposicion_simultanea_activo_y_pesos_regimen() -> None:
    df = pd.DataFrame([
        {"t": 1775000000, "ses": 20260401, "usd": 50.0, "unit_id": "U1", "inst": "MNQ", "regimen_tipo": "EXPANSION_REVERSION"},
        {"t": 1775000100, "ses": 20260401, "usd": 60.0, "unit_id": "U2", "inst": "MNQ", "regimen_tipo": "EXPANSION_REVERSION"},
        {"t": 1775000200, "ses": 20260401, "usd": -40.0, "unit_id": "U3", "inst": "MNQ", "regimen_tipo": "COMPRESION_RUPTURA"},
        {"t": 1775000200, "ses": 20260401, "usd": 70.0, "unit_id": "U4", "inst": "MGC", "regimen_tipo": "COMPRESION_RUPTURA"},
    ])
    df_cap = GCR.desduplicar_exposicion_simultanea_activo(df, max_slots_simultaneos_por_activo=2, ventana_solapamiento_s=900)
    assert len(df_cap) == 3
    assert set(df_cap["unit_id"].tolist()) == {"U1", "U2", "U4"}
