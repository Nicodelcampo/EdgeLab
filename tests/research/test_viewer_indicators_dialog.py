"""Diálogo único de indicadores (EDGELAB_INDICATORS_V2, 2026-09-26, pedido de Nico): un solo lugar para todos los
indicadores, igual para todos los activos; si un indicador no aplica al activo, no dibuja nada."""
from pathlib import Path

HTML = (Path(__file__).resolve().parents[2] / "viewer" / "nt8_bridge" / "index.html").read_text(encoding="utf-8")
DIALOG = HTML[HTML.index('id="nt8-props-modal"'):HTML.index("MODAL DE NUEVO GRÁFICO")]


def test_registro_y_paneles_de_todos_los_indicadores():
    for ind in ("zonas", "corredores", "tbz", "ema", "l2", "lux"):
        assert f'id: "{ind}"' in HTML
        assert f'data-ind="{ind}"' in DIALOG


def test_los_controles_de_indicadores_viven_en_el_dialogo():
    for el in ("runsel", "chk-tbz-exp", "chk-ema-f", "chk-vwap", "chk-show-l2", "inp-lux-max", "btn-mode-fixed",
               "corridors-options-wrap", "chk-show-exploratory"):
        assert f'id="{el}"' in DIALOG, el
    assert "btn-add-dummy" not in HTML                       # los botones de relleno se reemplazaron por add/remove reales
    assert 'id="btn-ind-add"' in DIALOG and 'id="btn-ind-rem"' in DIALOG


def test_no_aplica_no_dibuja_y_config_global():
    assert "if (!state.run || state.zonesHidden) return;" in HTML
    assert "no disponible en este activo" in HTML
    assert "indApplyAll()" in HTML                             # se reaplica al cargar cualquier activo
    assert "edgelab_indicators_v2" in HTML


def test_deteccion_en_solo_lectura():
    # el visor no recalcula zonas: los umbrales de detección se muestran fijos, con el valor de la corrida
    assert "IND_EDITABLE_KEYS" in HTML and "ind-readonly" in HTML
