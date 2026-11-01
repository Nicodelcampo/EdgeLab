"""El proponente recibe cartas de la gramática (sin resultados) y el paquete sigue acotado y sanitizable."""
from edgelab.autopilot.contexto import LENTES, armar_paquete
from edgelab.autopilot.roles import sanitize
from edgelab.research.agente import gramatica as G


def test_paquete_con_cartas_acotado_y_sanitizable():
    cs = G.cartas(n=6, semilla=1)
    p = armar_paquete(tablero={}, vacios=[], fichas=[], retiradas=[], lente="hueco_gramatica", cartas=cs)
    assert [c["id"] for c in p["cartas_gramatica"]] == [c["id"] for c in cs] and "hueco_gramatica" in LENTES
    sanitize(p)                                                            # ninguna coordenada parece una ruta local o un secreto
    chico = armar_paquete(tablero={}, vacios=["v" * 400] * 5, fichas=["f" * 400] * 5, retiradas=[], lente="regimen_declarado",
                          cartas=cs, max_chars=4500)
    assert not chico["fichas"] and len(chico["cartas_gramatica"]) <= len(cs)   # se recortan fichas antes que cartas


def test_directivas_de_nico_van_en_el_paquete_y_no_se_recortan():
    p = armar_paquete(tablero={}, vacios=["v" * 4000] * 5, fichas=["f" * 4000] * 5, retiradas=[], lente="regimen_declarado", max_chars=3000)
    assert "dos cuentas de Kaggle" in p["directivas_de_nico"] and "espiral" in p["directivas_de_nico"]
