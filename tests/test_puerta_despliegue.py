import copy
from datetime import date

import tools.puerta_despliegue as P

HOY = date(2026, 11, 25)
OK_DERIVA = [{"repo": "nt8/strategies/EdgeLabFundedSyncPortfolio.cs", "estado": "IGUAL"}]


def _c():
    k = {"id": "X", "dinero_real": True, "balance": 25500.0, "balance_observado": "2026-11-25",
         "reglas": {"piso_usd": 24000, "piso_verificado": True, "flat_hhmm_et": 1640, "noticias_permitidas": True},
         "bot": {"instrumento": "MES", "fuente_repo": "nt8/strategies/EdgeLabFundedSyncPortfolio.cs",
                 "riesgo_max_por_sleeve_usd": 100, "sleeves_simultaneos_max": 6, "tope_neto_micros": 1,
                 "daily_loss_bot_usd": 300, "hard_flatten_hhmm_et": 1635, "exec_audit_log": True}}
    canon = P.costos.friccion_rt_ticks("MES") * P.costos.tick_size("MES")
    return {"cuentas": [k], "auditorias_ejecucion": [{"fecha": "2026-11-20", "instrumento": "MES", "n": 15, "implied_rt_pts": canon * 0.9}],
            "umbrales": {"dias_balance_vencido": 3, "dias_auditoria_vencida": 14}}


def test_configuracion_sana_pasa():
    assert P.evaluar(_c(), "X", HOY, OK_DERIVA)[0] == []


def test_sin_tope_neto_el_peor_caso_suma_todos_los_sleeves():
    c = _c(); c["cuentas"][0]["bot"].update(tope_neto_micros=None, riesgo_max_por_sleeve_usd=150)
    assert any("peor caso abierto $900" in x for x in P.evaluar(c, "X", HOY, OK_DERIVA)[0])


def test_bloqueos_de_ejecucion_reglas_y_deriva():
    c = _c(); c["auditorias_ejecucion"][0]["implied_rt_pts"] = 99
    assert any("fricción implícita" in x for x in P.evaluar(c, "X", HOY, OK_DERIVA)[0])
    c = _c(); c["cuentas"][0]["bot"]["hard_flatten_hhmm_et"] = 1638
    assert any("cierre forzado" in x for x in P.evaluar(c, "X", HOY, OK_DERIVA)[0])
    c = _c()
    assert any("difiere del repo" in x for x in P.evaluar(c, "X", HOY, [dict(OK_DERIVA[0], estado="DERIVA")])[0])
    c = _c(); c["cuentas"][0]["reglas"]["piso_verificado"] = False
    assert any("piso" in x for x in P.evaluar(c, "X", HOY, OK_DERIVA)[0])
    c = _c(); c["auditorias_ejecucion"] = []
    assert any("sin auditoría" in x for x in P.evaluar(c, "X", HOY, OK_DERIVA)[0])
