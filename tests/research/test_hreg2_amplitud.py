"""El tercil de H-REG-2 usa sólo sesiones ya cerradas y el mapa no se elige por el P&L."""
from tools.hreg2_amplitud import MAPA, evaluar, estado_tercil


def _dias(n):
    return {f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}": float(i + 1) for i in range(n)}


def test_el_estado_de_hoy_clasifica_ayer_y_no_hoy():
    rangos = _dias(25)
    estado = estado_tercil(rangos, ventana=20)
    primero = min(estado)
    assert primero == sorted(rangos)[20]
    assert estado[primero] == 2


def test_empate_en_el_corte_cae_en_el_tercil_inferior():
    rangos = {f"202501{d:02d}": 1.0 for d in range(1, 22)}
    estado = estado_tercil(rangos, ventana=20)
    assert estado["20250121"] == 0


def test_el_mapa_esta_congelado():
    assert MAPA["RANGO_PREAPERTURA"] == 0
    assert MAPA["COMPRESION_NR"] == 0
    assert MAPA["ABSORCION_CLIMAX"] == 2
    assert "DOBLE_RETROCESO" not in MAPA


def test_filtrar_el_tercil_previsto_sube_el_rop_y_es_determinista():
    rangos = {}
    for i in range(60):
        clave = f"2025{(i // 28) + 1:02d}{(i % 28) + 1:02d}"
        rangos[clave] = 1.0 if (i // 5) % 2 == 0 else 10.0
    estado = estado_tercil(rangos)
    celdas = {}
    for dia, tercil in estado.items():
        celdas[dia] = {"m": 1.0 if tercil == 0 else -1.0, "n": 2}
    regla = {"regla": "P", "familia": "RANGO_PREAPERTURA", "instrumento": "NQ", "celdas": celdas}
    a = evaluar([regla], {"NQ": rangos}, semilla=7, b=40, n_min_filtrado=1, n_min_elegible=1)
    b = evaluar([regla], {"NQ": rangos}, semilla=7, b=40, n_min_filtrado=1, n_min_elegible=1)
    assert a["delta"] > 0
    assert a["p"] == b["p"]
    assert a["p"] <= 0.05
    assert a["pasa"] is True
