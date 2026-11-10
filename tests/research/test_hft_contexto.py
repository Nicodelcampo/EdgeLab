"""HFT-CONTEXTO: variables de contexto causales, estratos correctos, compuerta de potencia y regla de elección de la definición."""
import numpy as np
import pandas as pd

from edgelab.research import hft_contexto as K

S = 1_000_000_000; X = 20.0; T0 = 1_700_000_000 * S


def _C(filas):  # (segundos desde T0, lo, hi)
    return pd.DataFrame([dict(t_ns=T0 + int(s * S), lo=lo, hi=hi) for s, lo, hi in filas])


def test_variables_en_el_sentido_del_rebote():
    # tocado [100, 104] (fila 0), rebote hacia arriba desde 104 (lado +1); evento a los 1.000 s, salida a los 400 s
    C = _C([(0, 100, 104), (100, 90, 95), (200, 86, 89), (300, 112, 115), (500, 101, 103), (1200, 60, 64), (-3000, 95, 99)])
    c = K.contexto(C, 0, T0 + 1000 * S, T0 + 400 * S, 104.0, +1, X)
    assert c["n_respaldo"] == 3                       # [90,95], [86,89] y [101,103] cortan y ∈ [−1, 0] (84–104); la vieja está muerta
    assert c["obstaculo"] == "cerca" and abs(c["dist_obstaculo"] - 0.4) < 1e-9          # [112,115] empieza a 8 pts = 0,4 X
    assert c["confluencia"] == "sí" and c["huella"] == "≥1" and c["n_huella"] == 1      # [101,103] solapa y nació durante la excursión
    assert c["mas_nuevo"] == "no"                                                        # hay vecinos más nuevos
    assert c["n_densidad"] == 4                                                          # la de los 1.200 s todavía no existe


def test_mismo_mapa_visto_desde_el_otro_lado():
    C = _C([(0, 100, 104), (100, 90, 95), (300, 112, 115)])
    c = K.contexto(C, 0, T0 + 1000 * S, T0 + 400 * S, 100.0, -1, X)                     # rebote hacia abajo desde 100
    assert c["n_respaldo"] == 1 and c["obstaculo"] == "cerca"                            # detrás queda [112,115]; adelante [90,95]


def test_sin_vecinos_mas_nuevo_queda_fuera_y_huella_cero():
    c = K.contexto(_C([(0, 100, 104)]), 0, T0 + 1000 * S, T0 + 400 * S, 104.0, +1, X)
    assert c["mas_nuevo"] is None and c["densidad"] == "0" and c["huella"] == "0" and c["obstaculo"] == "ninguno"


def test_compuerta_de_potencia_y_bh():
    rng = np.random.default_rng(2); filas = []
    for f in range(200):
        for _ in range(4):
            r = "≥2" if rng.random() < 0.5 else "0"
            filas.append(dict(inst="NQ", fecha=20250801 + f, resultado=(1 if rng.random() < (0.7 if r == "≥2" else 0.45) else -1), respaldo=r,
                              obstaculo="ninguno", densidad="1-2", confluencia="no", mas_nuevo=None, huella="0"))
    A = K.analizar(pd.DataFrame(filas), n_boot=2000)
    assert A["variables"]["respaldo"]["estado"] == "PROBADA" and A["variables"]["respaldo"]["p_declarada"] < 0.01
    assert A["variables"]["obstaculo"]["estado"].startswith("SIN_POTENCIA") and A["nominadas_bh_q010"] == ["respaldo"]


def test_regla_de_eleccion():
    r = dict(nominadas_bh_q010=["D1_FRESCO_LEJANO", "D4_MEMORIA"],
             por_definicion={"D1_FRESCO_LEJANO": {"conjunto": {"n_real": 900}}, "D4_MEMORIA": {"conjunto": {"n_real": 300}}})
    assert K.elegir_definicion(r) == "D1_FRESCO_LEJANO" and K.elegir_definicion({}) == "D0_BASE"


def test_control_recibe_contexto_y_el_analisis_lo_usa_solo_como_diagnostico():
    n = 40000; ts = T0 + np.arange(n) * S; px = 20000 + 30 * np.sin(2 * np.pi * np.arange(n) / 1500.0)
    C = pd.DataFrame(dict(t_ns=[int(ts[15000]), int(ts[25000])], lo=[px[15000] - 4, px[25000] - 4], hi=[px[15000] + 4, px[25000] + 4]))
    F = pd.DataFrame(K.contexto_del_dia("NQ", 20250805, ts, px, np.ones(n), C, 0.25, 1.5455, "D0_BASE"))
    assert set(F.placebo) <= {0, 1} and {"respaldo", "obstaculo", "huella"} <= set(F.columns)
    T = pd.concat([F.assign(fecha=20250801 + i) for i in range(200)], ignore_index=True)
    A = K.analizar(T, n_boot=500)
    assert set(A["variables"]) == set(K.CONTRASTES)                                       # el control no agrega pruebas


def test_contexto_es_causal_por_prefijo():
    """Los clusters detectados DESPUÉS del evento no cambian su contexto (sólo cuentan los ya detectados y vivos)."""
    import numpy as np
    import pandas as pd
    from edgelab.research import hft_contexto as K
    NS = 10**9; t0 = 1_700_000_000 * NS
    C = pd.DataFrame(dict(t_ns=[t0, t0 + 100 * NS, t0 + 200 * NS, t0 + 900 * NS, t0 + 950 * NS], lo=[100.0, 96.0, 104.0, 99.0, 101.0],
                          hi=[102.0, 98.0, 106.0, 101.0, 103.0]))
    t_ev = t0 + 600 * NS
    a = K.contexto(C, 0, t_ev, t0 + 300 * NS, 102.0, +1, 4.0)
    b = K.contexto(C[C.t_ns < t_ev].reset_index(drop=True), 0, t_ev, t0 + 300 * NS, 102.0, +1, 4.0)
    assert {k: v for k, v in a.items() if not (isinstance(v, float) and np.isnan(v))} == {k: v for k, v in b.items() if not (isinstance(v, float) and np.isnan(v))}
