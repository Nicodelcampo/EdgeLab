"""AUDIT-002 — fija la exposición medida a la familia de 1 ULP.

Estos números son un **detector de regresión**: si alguien cambia cómo se
construye un borde de zona o un umbral, la exposición cambia y el test lo dice
antes de que cueste un oráculo.

No son un contrato de negocio: si un fix aprobado baja la exposición, los
números se actualizan **con** el fix, en el mismo commit y con su justificación.
Lo que NO puede pasar en silencio es que **suban**.
"""
import importlib.util
import os

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "ulp_exposure",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "tools", "ulp_exposure.py"))
ulp = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ulp)

TS = 0.00005          # 6E
DEC = 5
LO, HI = 20000, 25000


def _kernel_key(prefix):
    """Match por PREFIJO: las claves llevan comentarios largos y un em-dash."""
    for k in ulp.KERNELS:
        if k.startswith(prefix):
            return k
    raise AssertionError("no hay kernel que empiece con %r" % prefix)


def _exp(kernel, threshold_substr):
    for name, off, op, thr in ulp.KERNELS[_kernel_key(kernel)]:
        if threshold_substr in name:
            pct, flips, total = ulp.exposure(off, op, thr, TS, LO, HI, DEC)
            return pct, flips
    raise AssertionError("umbral no encontrado: %s / %s" % (kernel, threshold_substr))


# --------------------------------------------------------------------------- #
# 1) El feed y la reconstrucción NO son el mismo double
# --------------------------------------------------------------------------- #
def test_feed_y_reconstruido_difieren_y_siempre_en_la_misma_direccion():
    arriba = abajo = 0
    for k in range(LO, HI + 1):
        f, r = ulp.feed(k, TS, DEC), ulp.recon(k, TS)
        if f > r:
            arriba += 1
        elif f < r:
            abajo += 1
    assert abajo > 0, "si no difieren, toda esta familia de bugs no existiria"
    assert arriba == 0, ("el feed debe quedar SIEMPRE por debajo; si esto cambia, "
                         "la direccion de los diffs de paridad se invierte")


# --------------------------------------------------------------------------- #
# 2) Kernels inmunes por construcción — el borde vive a medio tick
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kernel", [
    "BigTrap2",
    "VolTicksPOC2 (price_mark_ticks=1, default)",
    "aVolCellPOI2",
])
def test_borde_a_medio_tick_no_puede_empatar(kernel):
    for name, off, op, thr in ulp.KERNELS[kernel]:
        assert off is None, (
            "%s / %s dejo de estar a medio tick: ahora un precio negociable puede "
            "caer exactamente en el umbral y la comparacion queda expuesta" % (kernel, name))


# --------------------------------------------------------------------------- #
# 3) Gaps2 — la referencia. Debe seguir en CERO.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("thr", ["bottom < price", "price >= top",
                                 "bottom - 2*ts", "top + 2*ts"])
def test_gaps2_sin_exposicion(thr):
    pct, flips = _exp("Gaps2", thr)
    assert flips == 0, (
        "Gaps2 es la referencia que dio paridad 1316/1316 con el camino 'inverse' "
        "ejercitado en el 47,4%% de las zonas. Si aparece exposicion (%.2f%%), esa "
        "referencia deja de estar ganada." % pct)


# --------------------------------------------------------------------------- #
# 4) HFTZones2 — exposición conocida, calibrada contra el oráculo real
# --------------------------------------------------------------------------- #
V21 = "HFTZones2 (v2.1, ANTES del fix"
V22 = "HFTZones2 (v2.2, grilla entera)"


def test_v21_queda_como_referencia_historica_calibrada():
    """Los numeros que motivaron el fix, conservados. El de abajo es la
    CALIBRACION del modelo: el oraculo real dio 9,0% (188 de 2.078 zonas)."""
    pct, _ = _exp(V21, "lower - pen")
    assert 9.0 <= pct <= 11.0, "calibracion perdida: %.2f%%" % pct
    pct, flips = _exp(V21, "upper + pen")
    assert flips > 0 and 45.0 <= pct <= 52.0, "exposicion inesperada: %.2f%%" % pct


def test_v22_lleva_TODOS_los_umbrales_a_cero():
    """Condicion 3 de la autorizacion de Nico. Cero por CONSTRUCCION: las dos
    representaciones colapsan al mismo indice de tick antes de comparar."""
    for thr in ("priceTick >= lowerTick", "priceTick <= upperTick",
                "lowerTick - pen", "upperTick + pen"):
        pct, flips = _exp(V22, thr)
        assert flips == 0, "%s quedo en %.2f%%: el fix no cerro la exposicion" % (thr, pct)


def test_el_fix_v22_reduce_la_exposicion_no_la_mueve_de_lugar():
    """Compara las dos versiones del MISMO umbral: de expuesto a cero."""
    antes, _ = _exp(V21, "upper + pen")
    despues, _ = _exp(V22, "upperTick + pen")
    assert antes > 45.0 and despues == 0.0


# --------------------------------------------------------------------------- #
# 5) La lección: el paso intermedio es lo que expone
# --------------------------------------------------------------------------- #
def test_una_resta_de_2ts_y_dos_restas_de_1ts_NO_son_equivalentes():
    """Misma distancia matemática, distinta secuencia, distinta exposición.

    Es el hallazgo que justifica medir por expresión en vez de razonar por
    offset neto.
    """
    una, _, _ = ulp.exposure(-2, "le", lambda e, ts: e - 2 * ts, TS, LO, HI, DEC)
    dos, _, _ = ulp.exposure(-2, "le", lambda e, ts: (e - 1 * ts) - 1 * ts,
                             TS, LO, HI, DEC)
    assert una == 0.0, "la resta unica debe ser exacta (patron de Gaps2)"
    assert dos > 5.0, "la resta en dos pasos debe exponer (patron de HFTZones2)"
