import json
from datetime import date

import tools.estado_produccion as EP


def _c(**kw):
    c = json.loads(EP.FUENTE.read_text(encoding="utf-8")); c.update(kw); return c


def test_resumen_versionado_coincide_con_el_json():
    assert EP.SALIDA.read_text(encoding="utf-8") == EP.render(json.loads(EP.FUENTE.read_text(encoding="utf-8")))


def test_resumen_corto():
    assert len(EP.render(_c()).splitlines()) <= EP.MAX_LINEAS


def test_avisa_balance_vencido_y_falta_de_auditoria():
    c = _c()
    w = EP.avisos(c, date(2026, 12, 31))
    assert any("balance observado" in x for x in w) and any("sin auditoría" in x for x in w)
    c["auditorias_ejecucion"] = [{"fecha": "2026-12-30"}]
    assert not any("auditoría" in x for x in EP.avisos(c, date(2026, 12, 31)))
