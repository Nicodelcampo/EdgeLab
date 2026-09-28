"""Decaimiento empírico de clusters: fija las decisiones del estimador.

Lo que más importa que quede clavado no es la aritmética sino **el control**. La curva
de decaimiento cruda aparecería aunque el cluster no tuviera nada adentro, porque el
consumo está correlacionado con la edad y con que el precio ya estuvo cerca. El
estimando es el contraste contra el placebo, no la curva.
"""
import pytest

from edgelab.research import cluster_decay as cd


def _stream(precios, vol=10.0):
    ts = [i * 1_000_000 for i in range(len(precios))]
    return ts, list(precios), [float(vol)] * len(precios)


# ------------------------------------------------------------------ barras

def test_las_barras_agregan_el_perfil_de_volumen_por_nivel():
    """El perfil por barra es lo que hace viable el módulo.

    Sin él, calcular el consumo exigiría recorrer todos los ticks por cada cluster.
    Con él se intersecan los pocos niveles que la barra tocó.
    """
    ts, px, vo = _stream([100, 101, 100, 102, 102, 100], vol=5.0)
    barras, perfiles = cd.barras_desde_ticks(ts, px, vo, ticks_por_barra=6)
    assert len(barras) == 1
    b = barras[0]
    assert b["hi"] == 102 and b["lo"] == 100 and b["close"] == 100
    assert perfiles[0] == {100: 15.0, 101: 5.0, 102: 10.0}


def test_una_barra_incompleta_al_final_se_descarta():
    ts, px, vo = _stream([100] * 7)
    barras, _ = cd.barras_desde_ticks(ts, px, vo, ticks_por_barra=6)
    assert len(barras) == 1, "la cola de 1 tick no forma barra"


# ------------------------------------------------------------------ consumo

def test_el_consumo_cuenta_solo_el_volumen_DENTRO_del_rango():
    perfil = {98: 7.0, 100: 3.0, 101: 4.0, 105: 9.0}
    clusters = [dict(id=1, lower_tk=100, upper_tk=101),
                dict(id=2, lower_tk=200, upper_tk=201)]
    c = cd.consumo_por_barra(clusters, perfil)
    assert c == {1: 7.0}, "el cluster 2 no recibe nada y no aparece"


# ------------------------------------------------------------------ resultados

def test_los_tres_canales_son_NO_direccionales():
    """Entrar, atravesar y permanecer. Ninguno mira signo de retorno ni P&L."""
    barras = [dict(hi=90, lo=88, close=89, i0=0, i1=1) for _ in range(3)]
    barras += [dict(hi=101, lo=99, close=100, i0=0, i1=1)]      # entra
    barras += [dict(hi=120, lo=118, close=119, i0=0, i1=1)]     # sale por arriba
    r = cd.resultados(barras, i=0, lo_tk=99, hi_tk=101, h=10)
    assert r["reentra"] == 1
    assert r["cruza"] == 1, "estuvo abajo y arriba de la banda"
    assert r["barras_adentro"] == 1


def test_cruzar_exige_estar_de_LOS_DOS_lados():
    barras = [dict(hi=90, lo=88, close=89, i0=0, i1=1) for _ in range(4)]
    r = cd.resultados(barras, i=0, lo_tk=99, hi_tk=101, h=10)
    assert r["reentra"] == 0 and r["cruza"] == 0


def test_sin_horizonte_suficiente_devuelve_None():
    """Preferible a computar sobre una ventana truncada y no decirlo."""
    barras = [dict(hi=100, lo=99, close=99, i0=0, i1=1)]
    assert cd.resultados(barras, i=0, lo_tk=99, hi_tk=101, h=10) is None


# ------------------------------------------------------------------ el control

def test_el_placebo_va_del_lado_OPUESTO_a_la_misma_distancia():
    """Es el control que refutó a BigTrap2 como imán sobre 6E.

    Si el placebo se comporta igual que el cluster, no era la zona: era la geometría.
    """
    # cluster 10 ticks ARRIBA del precio, ancho 4
    ctrl = cd.muestra_control(precio_tk=1000, lo_tk=1010, hi_tk=1013, ocupados=[])
    assert ctrl is not None
    clo, chi = ctrl
    assert chi - clo == 3, "mismo ancho"
    assert chi < 1000, "del lado opuesto"
    assert 1000 - chi == 10, "misma distancia"


def test_el_placebo_se_DESCARTA_si_cae_sobre_un_cluster_real():
    """Un control contaminado atenúa el contraste hacia cero de forma espuria."""
    assert cd.muestra_control(1000, 1010, 1013, ocupados=[(985, 995)]) is None
    assert cd.muestra_control(1000, 1010, 1013, ocupados=[(2000, 2010)]) is not None


def test_no_hay_control_si_el_precio_esta_DENTRO_del_cluster():
    assert cd.muestra_control(precio_tk=1011, lo_tk=1010, hi_tk=1013, ocupados=[]) is None


# ------------------------------------------------------------------ la curva

def _m(consumo, reentra, reentra_ctrl=None):
    d = dict(consumo=consumo, real=dict(reentra=reentra))
    if reentra_ctrl is not None:
        d["control"] = dict(reentra=reentra_ctrl)
    return d


def test_la_curva_publica_el_CONTRASTE_no_la_curva_cruda():
    muestras = ([_m(0.1, 1, 1) for _ in range(50)]
                + [_m(0.9, 0, 1) for _ in range(50)])
    c = cd.curva(muestras, "reentra", (0.0, 0.5, 1.0001))
    assert c[0]["real"] == 1.0 and c[0]["placebo"] == 1.0
    assert c[0]["contraste"] == 0.0, "sin efecto: real y placebo iguales"
    assert c[1]["contraste"] == -1.0, "el consumo apaga la reentrada"


def test_la_curva_publica_TODOS_los_bins_incluidos_los_flacos():
    """Esconder un bin sin datos haría parecer suave una curva que no lo es."""
    muestras = [_m(0.1, 1, 1) for _ in range(5)]
    c = cd.curva(muestras, "reentra", (0.0, 0.5, 1.0001), minimo_por_bin=30)
    assert len(c) == 2
    assert c[0]["n"] == 5 and c[0]["suficiente"] is False
    assert c[1]["n"] == 0 and c[1]["real"] is None


# ------------------------------------------------------------------ MDE

def test_el_MDE_baja_con_n_y_sube_con_la_multiplicidad():
    chico = cd.mde_proporcion(100)
    grande = cd.mde_proporcion(10_000)
    assert grande < chico, "más muestra detecta efectos más chicos"
    corregido = cd.mde_proporcion(10_000, celdas=20)
    assert corregido > grande, "corregir por 20 celdas exige un efecto mayor"


def test_el_MDE_castiga_el_agrupamiento_por_sesion():
    """El panel por barra está autocorrelacionado: su n efectivo es mucho menor."""
    assert cd.mde_proporcion(10_000, deff=5.0) > cd.mde_proporcion(10_000, deff=1.0)


def test_el_cuantil_normal_es_correcto():
    assert cd._z(0.975) == pytest.approx(1.959964, abs=1e-4)
    assert cd._z(0.8) == pytest.approx(0.841621, abs=1e-4)
    assert cd._z(0.5) == pytest.approx(0.0, abs=1e-9)
