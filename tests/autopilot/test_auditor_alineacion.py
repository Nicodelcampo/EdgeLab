from edgelab.autopilot.auditor_alineacion import evaluar_alineacion_estado


def test_auditor_alineacion_detecta_desvios_reales_sv1():
    rep = evaluar_alineacion_estado(
        head_local="6c54ca75",
        head_remoto="faad4600",
        archivos_sucios_code=["docs/research/EVALUABLES.jsonl", "docs/research/LIBRO_LORD.json"],
        config_autopilot={"programador": {"activo": False}, "kaggle": {"max_concurrent": 8, "accounts": ["a", "b"]}},
        unidades_fallidas=["edgelab-autopilot-generate.service"],
        existe_aprendizajes_espiral=False,
        campanas_bloqueadas_sin_ticket=["U1-ORO-GRILLA"],
        reaperturas_sin_verificacion_o16=[],
        max_chars_contexto=12000,
    )
    assert rep.puntaje_salud < 0.25
    codigos_fallidos = {c.codigo for c in rep.checks if not c.ok}
    assert {"SLI-01", "SLI-02", "SLI-03", "SLI-05", "SLI-06", "SLI-07", "SLI-08"}.issubset(codigos_fallidos)


def test_auditor_alineacion_estado_sano_100pct():
    rep = evaluar_alineacion_estado(
        head_local="faad4600",
        head_remoto="faad4600",
        archivos_sucios_code=[],
        config_autopilot={"programador": {"activo": True}, "kaggle": {"max_concurrent": 8, "accounts": ["a", "b"]}},
        unidades_fallidas=[],
        existe_aprendizajes_espiral=True,
        campanas_bloqueadas_sin_ticket=[],
        reaperturas_sin_verificacion_o16=[],
        max_chars_contexto=64000,
    )
    assert rep.puntaje_salud == 1.0
    assert rep.acciones_pendientes == []
    md = rep.a_markdown()
    assert "100.0%" in md
