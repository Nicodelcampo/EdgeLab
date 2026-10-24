"""Controles de la gramática de hipótesis del agente: diversidad sin resultados, nunca repropone lo medido, campos obligatorios."""
from edgelab.research.agente import gramatica as G


def test_control_ruido(monkeypatch):
    """Sin nada medido, las cartas se reparten por el espacio (objetos e instrumentos variados), no se amontonan."""
    monkeypatch.setattr(G, "MEDIDO", [])
    cs = G.cartas(n=12, semilla=3)
    assert len(cs) == 12
    assert len({c["coordenadas"]["objeto"] for c in cs}) >= 6 and len({c["coordenadas"]["evento"] for c in cs}) >= 5


def test_control_plantado(monkeypatch):
    """Una familia medida plantada nunca vuelve como carta, aunque el sorteo la encuentre."""
    plantada = dict(familia="X", estado="MUERTA", c=dict(objeto="vwap", evento="estado_continuo", lectura="reversion"))
    monkeypatch.setattr(G, "MEDIDO", G.MEDIDO + [plantada])
    for s in range(5):
        for c in G.cartas(n=20, semilla=s, candidatos=4000):
            assert not G._coincide(c["coordenadas"], plantada["c"])


def test_cartas_deterministas_compatibles_y_distintas():
    a, b = G.cartas(n=10, semilla=7), G.cartas(n=10, semilla=7)
    assert [c["id"] for c in a] == [c["id"] for c in b]
    for i, x in enumerate(a):
        assert G.compatible(x["coordenadas"]) and G.medida(x["coordenadas"]) is None
        for y in a[i + 1:]: assert G.distancia(x["coordenadas"], y["coordenadas"]) >= 3


def test_campos_obligatorios_de_cada_carta():
    for c in G.cartas(n=5, semilla=1):
        assert "COMPLETAR" in c["justificacion_economica"] and "COMPLETAR" in c["como_podria_refutarse"]
        assert set(c["espacio_de_eventos"]["alternativas_consideradas"]) | {c["espacio_de_eventos"]["elegido"]} == set(G.EJES["evento"])
        assert c["regimen"]["declarado_ex_ante"] and "test_causal" in c["controles"] and c["paridad"]


def test_medido_usa_valores_de_los_ejes():
    for m in G.MEDIDO:
        for k, v in m["c"].items(): assert k in G.EJES and (v is None or v in G.EJES[k]), (m["familia"], k, v)
