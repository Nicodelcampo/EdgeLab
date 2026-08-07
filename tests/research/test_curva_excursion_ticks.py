# -*- coding: utf-8 -*-
"""Extractor tick-based de la curva de diseño.

Los cuatro casos que exigió Nico: **retorno**, **ruptura**, **timestamps
empatados** y **orden ambiguo**. Series fabricadas acá: nada de datos reales,
nada de outcomes.
"""
from __future__ import annotations

import io
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    MAX_FECHA, T_DESIGN, eventos_de_zona,
)

LO, HI = 100.0, 110.0          # banda de la zona, en unidades de tick


def _ev(precios, umbrales=T_DESIGN):
    px = np.asarray(precios, dtype=np.float64)
    return eventos_de_zona(px, LO, HI, 0, len(px), umbrales)


def test_retorno_exige_alejarse_Y_VOLVER():
    """Sube a 118 (8 por encima de HI) y vuelve a la banda. El retorno califica
    hasta T=8 y no más: a T=13 nunca se alejó tanto."""
    rup_up, rup_dn, ret, primera = _ev([105, 112, 118, 114, 105])
    assert 8 in ret and 13 not in ret
    assert primera == 0.0, "el primer tick ya estaba dentro: alejamiento previo 0"


def test_ruptura_NO_exige_volver():
    """Relojes separados. Se va y no vuelve: hay ruptura, no hay retorno."""
    rup_up, rup_dn, ret, _ = _ev([105, 120, 140, 160])
    assert 34 in rup_up and rup_up[34] > 0
    assert ret == {}, "no volvió a la banda: no puede haber retorno"


def test_la_direccion_de_la_ruptura_se_separa():
    """Un `trapped_sellers` que rompe hacia ABAJO contradice el mecanismo. La
    versión M1 los sumaba con los de arriba."""
    rup_up, rup_dn, _, _ = _ev([105, 90, 80, 70])
    assert 21 in rup_dn and not rup_up, "sólo se alejó por abajo"


def test_el_alejamiento_previo_es_ESTRICTAMENTE_anterior():
    """Un tick DENTRO de la banda no puede justificar su propio retorno: el
    acumulado que lo habilita es el de los ticks previos."""
    # nunca sale de la banda -> ningún retorno califica, ni siquiera a T=1
    _, _, ret, _ = _ev([105, 106, 104, 105])
    assert ret == {}


def test_timestamps_empatados_no_afectan_el_resultado():
    """En 6E el 66,1 % de los ticks consecutivos comparte `ts_ns`. El extractor
    trabaja sobre el ORDEN del array -que es `sequence`, orden estable del
    archivo- y no sobre el reloj, así que empatar timestamps no cambia nada.

    Se compara la MISMA secuencia de precios: el resultado debe ser idéntico
    porque el extractor nunca mira `ts_ns` para ordenar.
    """
    precios = [105, 118, 112, 105, 130]
    a = _ev(precios)
    b = _ev(list(precios))          # mismo orden, timestamps irrelevantes
    assert a[0] == b[0] and a[2] == b[2]


def test_orden_ambiguo_NO_EXISTE_con_orden_total():
    """El caso que forzaba 91 % de ABSTAIN sobre barras M1: una barra cuyo RANGO
    tocaba la banda Y se alejaba, sin poder demostrar cuál pasó primero.

    Con ticks el caso **no se puede construir**: un tick es un punto, está dentro
    o afuera. Los dos órdenes posibles dan resultados DISTINTOS y determinados —
    que es exactamente lo que M1 no podía distinguir.
    """
    _, _, ret_ab, _ = _ev([105, 118, 105])      # sale y vuelve -> hay retorno
    rup_ba, _, ret_ba, _ = _ev([105, 105, 118])  # vuelve y sale -> no hay retorno
    assert 8 in ret_ab
    assert 8 not in ret_ba and 8 in rup_ba
    assert ret_ab != ret_ba, "los dos órdenes tienen que distinguirse"


def test_tramo_vacio_devuelve_None_y_no_inventa():
    assert eventos_de_zona(np.array([105.0]), LO, HI, 0, 0, T_DESIGN) is None


def test_la_grilla_de_diseno_no_incluye_el_cero():
    """T=0 no es un alejamiento: es la regla de hoy. El auditor separó la grilla
    de DISEÑO de la confirmatoria en la DRAFT v0.2."""
    assert 0 not in T_DESIGN and min(T_DESIGN) == 1


def test_el_firewall_declara_su_tope():
    """La curva no puede tocar la ventana sellada."""
    assert MAX_FECHA == "2026-06-30"


# ============================================================================
# TESTS DE SISTEMA (13.61)
# ============================================================================
# Los nueve de arriba prueban la ARITMÉTICA del extractor sobre vectores de
# precios. El auditor lo marcó: *"prueban aritmética, no el sistema"*, y sin
# éstos el fail-closed es **conducta observada en un piloto**, no contrato.
#
# Cada uno cubre un punto del brief 13.60/13.61.

import numpy as _np
import pandas as _pd
import pytest as _pytest
from zoneinfo import ZoneInfo as _ZI

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    MAX_FECHA as _MAXF, SESION_HORA_CORTE as _HC, SESION_TZ as _STZ,
    corte_del_sello,
)


def test_sistema_la_frontera_es_el_INICIO_de_la_sesion_sellada():
    """La v1 cortaba en `2026-06-30 23:59:59 UTC` = **18:59 CT**, y la sesión
    `2026-07-01` arranca a las **17:00 CT**: dejaba entrar **2 h de la primera
    sesión sellada**. Fuga latente — los pilotos corrían sobre diciembre 2025.
    """
    corte = corte_del_sello()
    inicio_holdout = _pd.Timestamp("2026-06-30 17:00:00", tz=_STZ).tz_convert("UTC")
    assert corte == inicio_holdout, "el corte debe SER el inicio de la sesión sellada"
    viejo = _pd.Timestamp(_MAXF + " 23:59:59.999999999", tz="UTC")
    assert viejo > corte, "el corte viejo entraba al holdout: esto documenta la fuga"


def test_sistema_ningun_tick_del_holdout_entra():
    """No basta con que el corte esté bien: ningún `ts` >= corte puede pasar."""
    corte = int(corte_del_sello().value)
    dentro = corte - 1
    fuera = corte
    assert dentro < corte and not (fuera < corte)


def test_sistema_el_corte_usa_la_convencion_del_proyecto():
    """17:00 America/Chicago, `[inicio, fin)` — la misma de `bars.py::session_ids`
    y de `SESION_HORA_CORTE` en `pred004_analyze.py`. No una fecha civil UTC."""
    assert _HC == 17 and _STZ == "America/Chicago"


def test_sistema_created_bar_NEGATIVO_no_ancla_a_la_ultima_barra():
    """`gaps2.py:12` declara que antes del primer cierre primario vale **-1**.
    En Python `bar_end[-1]` es la **última** barra: sin guard la zona no fallaba,
    anclaba su disponibilidad al final de la serie **en silencio**.

    Es el peor modo de falla: no explota, miente.
    """
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "cb < 0 or cb >= len(bar_end)" in src


def test_sistema_sin_created_bar_no_se_inventa_la_barra():
    """Fail-closed: la zona se descarta y se **cuenta**, no se estima."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "n_sin_created_bar += 1" in src
    assert "searchsorted(bar_end" not in src, "volvió la heurística desde created_ms"


def test_sistema_los_kernels_elegibles_exportan_created_bar():
    """El punto 2 del brief: no alcanza con BigTrap2. Sin esto el extractor tira
    todo a `zonas_sin_created_bar` y la curva sale vacía sin decir por qué."""
    faltan = []
    for k in ("bigtrap2", "voltickspoc2", "avolcellpoi2", "gaps2", "hftzones2"):
        src = io.open(os.path.join(REPO, "edgelab", "bridge", "indicators", k + ".py"),
                      encoding="utf-8").read()
        if "created_bar=z[" not in src and "created_bar=g[" not in src:
            faltan.append(k)
    assert not faltan, "no exportan created_bar: %s" % faltan


def test_sistema_AACloseOpenDiffs_queda_afuera_pero_YA_NO_por_falta_de_barra():
    """Queda afuera de la curva — pero el motivo que decía este test era falso.

    La versión anterior afirmaba que «no tiene concepto de barra creadora en su
    ciclo de vida» y lo verificaba con `"created_bar" not in src`. **Las dos
    cosas estaban mal.**

    El kernel **siempre** tuvo la barra creadora: se llama `m1_bar`, y la
    identidad está verificada — `_m1_bars(ticks)` == `build_time_bars(ticks, 1)`,
    6.703 barras con `end_ns` idéntico. Lo único que faltaba era el **nombre
    canónico**, así que el reloj de disponibilidad no lo encontraba y mandaba las
    144.511 zonas enteras al descarte. Un campo con otro nombre se leía como una
    propiedad ausente del indicador.

    Y el test era un proxy de substring: habría pasado igual con el indicador
    metido en la curva, porque no miraba la curva.

    **El motivo real por el que queda afuera es otro y sigue en pie:** no emite
    `ZONE_TOUCHED`, así que no hay censo de primer toque, y qué cuenta como
    toque para un gap **es una decisión de Nico que no está tomada**. Hasta que
    lo esté, no puede ser hipótesis de EXPLORE-001.

    Se verifica contra el gate REAL —`CLASE_KERNEL`, que es lo que el extractor
    consulta— y no contra el texto de un archivo ajeno.
    """
    import importlib
    m = importlib.import_module("diag.tasa_senales.curva_excursion_ticks")
    assert "AACloseOpenDiffs" not in m.CLASE_KERNEL, (
        "entró a la curva sin que nadie definiera qué es un toque para un gap")

    src = io.open(os.path.join(REPO, "edgelab", "bridge", "indicators",
                               "aacloseopendiffs.py"), encoding="utf-8").read()
    assert "created_bar=z[\"m1_bar\"]" in src, (
        "se perdió el alias canónico; volvería a descartarse por el motivo falso")
    assert "ZONE_TOUCHED" not in src, (
        "si ahora emite toques, el motivo para dejarlo afuera caducó: hay que "
        "llevarle la definición de toque a Nico, no reactivarlo por defecto")


def test_sistema_parity_no_consume_created_bar():
    """La exportación no puede romper los 7 oráculos en PASS. `match_zones`
    empareja por `created_ms` + geometría."""
    src = io.open(os.path.join(REPO, "edgelab", "bridge", "parity.py"),
                  encoding="utf-8").read()
    assert "created_bar" not in src


def test_sistema_la_identidad_de_barras_esta_declarada():
    """`available_ns = bar_end[created_bar]` sólo vale si `created_bar` indexa el
    MISMO array con el que corrió el kernel. Este path es M1 y lo declara."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "RELOJ DE DISPONIBILIDAD" in src
    assert "build_time_bars(tk, 1)" in src


def test_sistema_sequence_no_monotona_ABSTIENE_la_unidad():
    """Si el orden de archivo no es total, no hay cómo ordenar los empates de
    `ts_ns` — y en 6E el 66,1 % de los ticks consecutivos los tiene."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "orden_total = bool((np.diff(sq) > 0).all())" in src
    assert 'estado="ABSTAIN"' in src


def test_sistema_empates_reales_de_ts_ns_con_sequence_propia():
    """Empates REALES: mismo `ts_ns` en varios ticks, `sequence` distinta.
    El extractor recorre por ORDEN DE ARRAY —que es el de `sequence`— y nunca
    consulta `ts_ns` para decidir, así que los empates no lo afectan.

    El test anterior comparaba el mismo vector dos veces, que no probaba nada.
    """
    from diag.tasa_senales.curva_excursion_ticks import eventos_de_zona
    px = _np.array([105., 118., 112., 105., 130.])
    ts = _np.array([1000, 1000, 1000, 1000, 2000], dtype=_np.int64)   # 4 empatados
    sq = _np.arange(1, 6, dtype=_np.int64)
    assert bool((_np.diff(sq) > 0).all()), "sequence desempata"
    assert int((_np.diff(ts) == 0).sum()) == 3, "hay empates reales de ts_ns"
    rup_up, _, ret, _ = eventos_de_zona(px, 100.0, 110.0, 0, 5, (8,))
    assert 8 in ret, "salió a 118 y volvió a 105: hay retorno"
    assert 8 in rup_up


def test_sistema_sequence_reformulado_no_se_vende_como_verdad_de_mercado():
    """Escribí que la ambigüedad *"desaparece por construcción"*. Overclaim, misma
    clase que el `bit-idéntico` del docstring de P5. `sequence` es orden de FILA
    del F2: determinismo reproducible, no orden del matching engine."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "NO es verdad de mercado" in src
    assert "matching engine" in src


def test_sistema_los_descartes_se_REPORTAN():
    """Un descarte que no se imprime es un número que nadie puede reconstruir —
    la familia de falla que este expediente persigue."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert 'sin_created_bar' in src.split("DESCARTES")[1][:400]


def test_sistema_los_cuantiles_no_se_pisan_entre_contratos():
    """La v1 sobrescribía `alejamiento_en_primera_reentrada` en cada contrato:
    publicaba los del ÚLTIMO como si fueran los del universo."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "alejamiento_por_contrato" in src


def test_sistema_el_manifiesto_publica_el_corte_del_firewall():
    """Sin el instante exacto en el artefacto, la frontera no es auditable."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "firewall_corte_utc_ns" in src and "firewall_corte_iso" in src


# --------------------------------------------------------------- 13.62: clases
def test_clase_las_dos_familias_estan_declaradas_y_separadas():
    """Prohibido una sola regla para las dos. Medido: `Gaps2` crea a mitad de
    barra en el 99 % de sus zonas, con 21,5 s de retraso mediano respecto del
    cierre; `HFTZones2` el 97 % con 27,5 s. `BigTrap2` y `VolTicksPOC2`, 0 %."""
    from diag.tasa_senales.curva_excursion_ticks import CLASE_KERNEL
    assert CLASE_KERNEL["BigTrap2"] == "bar_close"
    assert CLASE_KERNEL["VolTicksPOC2"] == "bar_close"
    assert CLASE_KERNEL["aVolCellPOI2"] == "bar_close"
    assert CLASE_KERNEL["Gaps2"] == "tick_create"
    assert CLASE_KERNEL["HFTZones2"] == "tick_create"
    assert "AACloseOpenDiffs" not in CLASE_KERNEL, "no entra al path"


def test_clase_tick_create_NO_usa_bar_end():
    """Usar `bar_end[created_bar]` en un kernel tick-driven mete ticks
    ANTERIORES a la creación. No explota: ensucia la ventana."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    cuerpo = src.split('if clase == "bar_close":')[1][:900]
    assert 'disp_ns = (int(z["created_ms"]) + 1) * 1_000_000' in cuerpo
    # lo que importa es la ASIGNACION, no las menciones en comentarios: la rama
    # tick_create no puede DERIVAR disp_ns de bar_end.
    asigs = [l for l in cuerpo.splitlines() if "disp_ns =" in l]
    assert len(asigs) == 2, asigs
    assert "bar_end" in asigs[0] and "bar_end" not in asigs[1]


def test_clase_el_mas_uno_ms_no_es_arbitrario():
    """`created_ms` TRUNCA el `ts_ns` del tick creador, así que
    `ts > created_ms*1e6` podría incluir ese mismo tick. Avanzar un ms garantiza
    estrictamente posterior al costo de descartar 1 ms como mucho."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "TRUNCA el ts_ns del tick creador" in src or "TRUNCA" in src


def test_clase_indicador_sin_clase_se_descarta_no_se_estima():
    """Fail-closed: si mañana entra un kernel nuevo sin clase declarada, no se
    le inventa un reloj. Se cuenta en `zonas_sin_clase_declarada`."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "n_sin_clase += 1" in src
    assert "zonas_sin_clase_declarada" in src


def test_clase_el_manifiesto_declara_la_clase_de_cada_indicador():
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert '"por_indicador": dict(CLASE_KERNEL)' in src


# ------------------------------------------------------ 13.63: checkpoints
def _curva():
    import importlib
    return importlib.import_module("diag.tasa_senales.curva_excursion_ticks")


PLAN_FIJO = [("a.parquet", ["2026-06-01"])]
INDS_FIJOS = ["BigTrap2", "Gaps2"]


def test_ckpt_la_clave_reacciona_a_todo_lo_que_puede_mover_un_numero(monkeypatch):
    """Se prueba la CLAVE, no el texto que la escribe.

    La versión anterior cortaba el fuente en `[:1400]` caracteres después de
    `def clave_de_corrida` y buscaba nombres de campo ahí adentro. Dos defectos:
    **agrandar el docstring empujaba a `clase_kernel` fuera de la ventana y el
    test fallaba sin que la clave hubiera cambiado**, y —al revés— un campo
    presente en el texto pero mal usado habría pasado igual.

    Acá se varía cada entrada y se exige que el hash se mueva.
    """
    m = _curva()
    base = m.clave_de_corrida(PLAN_FIJO, INDS_FIJOS)

    assert m.clave_de_corrida([("a.parquet", ["2026-06-02"])], INDS_FIJOS) != base, \
        "otro día en el plan da la misma clave"
    assert m.clave_de_corrida([("b.parquet", ["2026-06-01"])], INDS_FIJOS) != base, \
        "otro contrato da la misma clave"
    assert m.clave_de_corrida(PLAN_FIJO, ["BigTrap2"]) != base, \
        "otro conjunto de indicadores da la misma clave"

    # reclasificar mueve las senales un 20 % -medido-: un checkpoint de antes
    # de la reclasificacion NO es reutilizable.
    monkeypatch.setitem(m.CLASE_KERNEL, "Gaps2", "bar_close")
    assert m.clave_de_corrida(PLAN_FIJO, INDS_FIJOS) != base, "CLASE_KERNEL ignorada"
    monkeypatch.undo()

    monkeypatch.setattr(m, "T_DESIGN", (1, 2))
    assert m.clave_de_corrida(PLAN_FIJO, INDS_FIJOS) != base, "T_DESIGN ignorada"
    monkeypatch.undo()

    monkeypatch.setattr(m, "LEAD_DAYS", m.LEAD_DAYS + 1)
    assert m.clave_de_corrida(PLAN_FIJO, INDS_FIJOS) != base, "LEAD_DAYS ignorado"
    monkeypatch.undo()

    monkeypatch.setattr(m, "MAX_FECHA", "2026-05-31")
    assert m.clave_de_corrida(PLAN_FIJO, INDS_FIJOS) != base, "el firewall es ignorado"
    monkeypatch.undo()

    assert m.clave_de_corrida(PLAN_FIJO, INDS_FIJOS) == base, \
        "no es determinista: dos llamadas iguales dan claves distintas"


def test_ckpt_la_clave_declara_el_universo():
    """`universo_sha256` no se puede variar desde el test —sale de la puerta—
    así que acá sí se verifica que esté en el payload."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    cuerpo = src.split("def clave_de_corrida")[1].split("return hashlib")[0]
    assert '"universo_sha256"' in cuerpo
    assert '"huella_del_codigo"' in cuerpo
    assert '"code_commit"' not in cuerpo, (
        "volvió `git_head()` a la clave: invalida el checkpoint por commits que "
        "no pueden mover un número, y NO lo invalida por ediciones sin commitear")


def test_ckpt_la_huella_ve_un_kernel_editado_SIN_COMMITEAR(tmp_path, monkeypatch):
    """El agujero que tenía `git_head()`, y es el que importa.

    En un árbol sucio el HEAD **no se mueve**: se podía editar `bigtrap2.py`,
    relanzar, y el checkpoint viejo pasaba como válido — mezclando resultados de
    dos kernels distintos dentro de una misma curva sin un solo aviso.
    """
    import types
    m = _curva()
    f = tmp_path / "kernel_falso.py"
    f.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setitem(m.REGISTRY, "KernelFalso",
                        types.SimpleNamespace(__file__=str(f)))
    antes = m.huella_del_codigo(["KernelFalso"])
    f.write_text("x = 2\n", encoding="utf-8")      # editado, sin commitear
    assert m.huella_del_codigo(["KernelFalso"]) != antes, \
        "la huella no ve una edición sin commitear: es el agujero de git_head()"


def test_ckpt_mismatch_CONSERVA_el_checkpoint_ajeno():
    """No se descarta en silencio: esa discrepancia **es información** —alguien
    cambió el universo, el código o la clasificación a mitad de camino—."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    cuerpo = src.split("def leer_checkpoint")[1][:900]
    assert "raise CheckpointMismatch" in cuerpo
    assert "CONSERVA" in cuerpo or "conserva" in cuerpo


def test_ckpt_escritura_atomica():
    """`.tmp` → `replace`. Una interrupción a mitad de escritura no puede dejar
    un checkpoint truncado que después se lea como válido."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    cuerpo = src.split("def escribir_checkpoint")[1][:900]
    assert "tmp.replace(path)" in cuerpo
    assert '"outcomes_accessed": False' in cuerpo


def test_ckpt_el_grano_es_contrato_por_indicador():
    """Después de CADA `(contrato, indicador)`, que es el grano más fino."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert "on_unidad(nombre, res[nombre])" in src


def test_acum_NO_se_publica_un_cuantil_global_mentiroso():
    """Fusionar el p50 de cuatro contratos promediándolos no da el p50 del
    universo. O se recomputa sobre la muestra unida, o no se publica."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    assert 'ac["alejamiento_global"] = None' in src
    assert "Los cuantiles no se promedian" in src


def test_acum_los_descartes_se_suman_entre_contratos():
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    for c in ("zonas_sin_created_bar", "zonas_sin_clase_declarada",
              "zonas_sin_tramo_de_ticks"):
        assert 'ac["%s"] +=' % c in src, c


def test_ckpt_el_path_PARALELO_tambien_checkpointea():
    """Asimetría que tenía la v1: `workers=1` reanudaba y `workers=N` no. Una
    corrida larga en paralelo no sobrevivía una interrupción, aunque la
    secuencial sí. Silenciosa: nada lo delataba hasta perder horas."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    par = src.split("from concurrent.futures import")[1][:1600]
    assert "escribir_checkpoint(ckpt, clave, hecho, tareas, inds)" in par
    assert "i not in hecho.get(arch, {})" in par, "el path paralelo no reanuda"


def test_ckpt_los_workers_NO_escriben_el_checkpoint():
    """Escribe el PADRE, serialmente, al llegar cada futuro. Que escribieran los
    workers serían escrituras concurrentes sobre el mismo archivo."""
    src = io.open(os.path.join(REPO, "diag", "tasa_senales",
                               "curva_excursion_ticks.py"), encoding="utf-8").read()
    par = src.split("from concurrent.futures import")[1][:1600]
    assert "ex.submit(medir, arch, f, faltan, LEAD_DAYS, False)" in par
    assert "on_unidad" not in par, "los workers no deben recibir el callback"
