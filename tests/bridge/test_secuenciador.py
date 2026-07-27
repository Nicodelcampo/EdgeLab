# -*- coding: utf-8 -*-
"""Secuenciador causal — P4, P5, P7, P8, P9, P10 de PRED-003.

No se puede ejecutar C# desde acá. Lo que sí se puede, y es lo que exige el
pre-registro antes de gastar un oráculo, son dos cosas:

1. **Implementación de referencia** del mismo algoritmo en Python, con tests que
   fijan cada invariante. Si la referencia no puede sostenerlos, el `.cs` tampoco.
2. **Verificación estructural** de que `BigTrap2.cs` contiene las piezas del
   patrón y no quedó ninguna del anterior. Es el mismo estándar que ya se usó
   para el espejado bit a bit del filtro de mecha.
"""
import io
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CS = os.path.join(REPO, "nt8", "BigTrap2.cs")


# ---------------------------------------------------------------------------
# Implementación de REFERENCIA: el mismo algoritmo que el .cs
# ---------------------------------------------------------------------------
class Secuenciador:
    """Snapshots y bloques por separado; se unen por identidad, no por llegada."""

    def __init__(self, k):
        self.k = k
        self.no_confiable = False
        self.suprimidas = 0
        self.snaps = []          # cola de snapshots (barras cerradas)
        self.blocks = []         # cola de bloques completos
        self.cur = []            # bloque en construcción
        self.sess = None
        self.procesados = []     # (bar, bloque) en el orden en que se procesaron
        self.residuales = 0
        self.mismatch = []

    # -- BIP1: llega un evento de la subserie
    def evento(self, tick, sesion):
        if self.sess is None or sesion != self.sess:
            if self.cur:                       # bloque RESIDUAL (1..K-1)
                self.blocks.append(self.cur)
                self.residuales += 1
                self.cur = []
            self.no_confiable = False          # la frontera resincroniza
            self.sess = sesion
        self.cur.append((tick, sesion))
        if len(self.cur) >= self.k:
            self.blocks.append(self.cur)
            self.cur = []

    # -- BIP0: cierra una barra primaria
    def cierre(self, bar, o, h, lo, c):
        self.snaps.append(dict(bar=bar, o=o, h=h, lo=lo, c=c))
        self.drenar()

    def drenar(self):
        # Sólo avanza con LAS DOS piezas. Tomar de menos desalinea hacia adelante.
        while self.snaps and self.blocks:
            s = self.snaps.pop(0)
            b = self.blocks.pop(0)
            if not self.verificar(s, b):
                continue
            # POLITICA DE ROTURA: con la sesion marcada el ciclo de vida corre
            # (depende del OHLC) pero NO se crean zonas. Una zona nacida de un
            # footprint que no se pudo verificar es peor que ninguna: entra al
            # store con la misma apariencia que una buena.
            if self.no_confiable:
                self.suprimidas += 1
                continue
            self.procesados.append((s["bar"], b))

    def verificar(self, s, b):
        px = [t for t, _ in b]
        ok = (px[0] == s["o"] and px[-1] == s["c"]
              and min(px) == s["lo"] and max(px) == s["h"])
        if not ok:
            residual = len(b) < self.k
            self.mismatch.append(dict(bar=s["bar"], n=len(b), residual=residual))
            if not residual:
                self.no_confiable = True
        return ok


def _serie(sec, ticks, sesion, bar_ini, k):
    """Alimenta `ticks` eventos y cierra las barras que correspondan."""
    bloques = [ticks[i:i + k] for i in range(0, len(ticks), k)]
    for e in ticks:
        sec.evento(e, sesion)
    for j, blk in enumerate(bloques):
        sec.cierre(bar_ini + j, blk[0], max(blk), min(blk), blk[-1])
    return bar_ini + len(bloques)


# --------------------------------------------------------------- invariantes
def test_P4_orden_total_entre_barras():
    """Ninguna barra se procesa antes que su anterior."""
    s = Secuenciador(5)
    _serie(s, list(range(100, 125)), 1, 0, 5)
    bars = [b for b, _ in s.procesados]
    assert bars == sorted(bars) == list(range(5)), bars


def test_P5_el_bloque_de_la_barra_N_es_el_de_la_barra_N():
    """Orden lógico: cada snapshot recibe SU bloque, no el que llegó."""
    s = Secuenciador(5)
    _serie(s, list(range(100, 125)), 1, 0, 5)
    for bar, blk in s.procesados:
        assert [t for t, _ in blk] == list(range(100 + bar * 5, 105 + bar * 5))


def test_los_eventos_pueden_llegar_TARDE_sin_desalinear():
    """El caso que motiva todo: la barra cierra antes de que lleguen sus eventos.

    El secuenciador no procesa hasta tener el bloque; con take/reset la barra se
    habría quedado con lo que hubiera en el balde.
    """
    s = Secuenciador(5)
    s.cierre(0, 100, 104, 100, 104)      # cierra ANTES de recibir nada
    s.cierre(1, 105, 109, 105, 109)
    assert s.procesados == []            # no se procesó nada: falta el bloque
    for e in range(100, 110):
        s.evento(e, 1)
    s.drenar()
    assert [b for b, _ in s.procesados] == [0, 1]
    assert [t for t, _ in s.procesados[0][1]] == [100, 101, 102, 103, 104]


def test_P7_ningun_bloque_mezcla_sesiones():
    s = Secuenciador(5)
    for e in range(100, 107):
        s.evento(e, 1)                   # 7 eventos: 5 + residual de 2
    for e in range(200, 210):
        s.evento(e, 2)
    for blk in s.blocks + ([s.cur] if s.cur else []):
        assert len({ses for _, ses in blk}) == 1, blk


def test_P8_el_residual_es_categoria_explicita():
    s = Secuenciador(5)
    for e in range(100, 107):
        s.evento(e, 1)                   # 5 + 2
    for e in range(200, 205):
        s.evento(e, 2)
    assert s.residuales == 1
    tam = [len(b) for b in s.blocks]
    assert tam == [5, 2, 5], tam         # el residual de 2 va ANTES del de la sesión nueva


def test_P9_sin_piezas_huerfanas_en_el_interior():
    s = Secuenciador(5)
    _serie(s, list(range(100, 120)), 1, 0, 5)
    assert len(s.procesados) == 4
    assert s.snaps == [] and s.blocks == []   # nada colgado


def test_P9_el_borde_derecho_queda_pendiente_y_es_lo_esperado():
    """Una barra que cerró y cuyo bloque aún no llegó NO es un error: es el
    borde derecho del rango (MATURITY_TAIL)."""
    s = Secuenciador(5)
    for e in range(100, 105):
        s.evento(e, 1)
    s.cierre(0, 100, 104, 100, 104)
    s.cierre(1, 105, 109, 105, 109)      # su bloque nunca llega
    assert len(s.procesados) == 1
    assert len(s.snaps) == 1             # queda pendiente, no se fuerza


def test_P10_el_verificador_OHLC_atrapa_un_bloque_equivocado():
    """Si el par no corresponde, el OHLC lo dice. Es el punto del diseño."""
    s = Secuenciador(5)
    for e in [100, 101, 102, 103, 104]:
        s.evento(e, 1)
    s.cierre(0, 200, 204, 200, 204)      # snapshot de OTRA barra
    assert s.procesados == []
    assert len(s.mismatch) == 1
    assert s.mismatch[0]["residual"] is False


def test_el_verificador_acepta_el_residual_corto():
    s = Secuenciador(5)
    for e in [100, 101]:
        s.evento(e, 1)
    for e in [200]:
        s.evento(e, 2)                   # fuerza el cierre del residual
    s.cierre(0, 100, 101, 100, 101)
    assert len(s.procesados) == 1        # el residual de 2 valida contra su barra
    assert s.mismatch == []


# ------------------------------------------------- la politica de rotura ACTUA
def test_una_rotura_suprime_las_zonas_del_RESTO_de_la_sesion():
    """La marca de sesión no confiable tiene que tener EFECTO.

    En la primera versión el flag se escribía y nunca se leía — lógica muerta.
    La política dice "marcar el resto de la sesión como no confiable", y eso
    sólo significa algo si deja de crear zonas.
    """
    s = Secuenciador(5)
    for e in [100, 101, 102, 103, 104]:
        s.evento(e, 1)
    s.cierre(0, 200, 204, 200, 204)      # snapshot de OTRA barra -> rotura
    assert s.no_confiable is True
    # los pares siguientes de la MISMA sesión ya no producen zonas
    for e in [110, 111, 112, 113, 114]:
        s.evento(e, 1)
    s.cierre(1, 110, 114, 110, 114)
    assert s.procesados == []
    assert s.suprimidas == 1


def test_la_frontera_de_sesion_resincroniza():
    """Y sólo la frontera: no se reacomoda el buffer para salir antes."""
    s = Secuenciador(5)
    for e in [100, 101, 102, 103, 104]:
        s.evento(e, 1)
    s.cierre(0, 200, 204, 200, 204)      # rotura
    assert s.no_confiable is True
    for e in [300, 301, 302, 303, 304]:
        s.evento(e, 2)                   # sesión NUEVA
    assert s.no_confiable is False
    s.cierre(1, 300, 304, 300, 304)
    assert len(s.procesados) == 1        # vuelve a producir


def test_el_cs_suprime_zonas_con_la_sesion_marcada():
    s = _cs_codigo()
    i = s.index("private void DrainReadyBars()")
    j = s.index("private bool VerificarOHLC")
    cuerpo = s[i:j]
    assert "if (sesionNoConfiable)" in cuerpo
    assert cuerpo.index("if (sesionNoConfiable)") < cuerpo.index("ProcessBar(s,")
    assert "nSuprimidas++" in cuerpo


# --------------------------------------------------- el .cs espeja el patrón
def _cs():
    return io.open(CS, encoding="utf-8-sig").read()


def _cs_codigo():
    """El `.cs` SIN comentarios.

    Los nombres del patrón viejo aparecen en los comentarios que explican por qué
    ya no están — buscarlos sobre el texto completo da falsos positivos y hace
    que el test castigue justo la documentación que uno quiere que exista.
    """
    out = []
    for ln in _cs().splitlines():
        i = ln.find("//")
        out.append(ln[:i] if i >= 0 else ln)
    return chr(10).join(out)


@pytest.mark.parametrize("pieza", [
    "private struct BarSnap",
    "private readonly Queue<BarSnap>",
    "private readonly Queue<List<FpTick>>",
    "private void DrainReadyBars()",
    "private bool VerificarOHLC(BarSnap s, List<FpTick> blk)",
    "while (snapQ.Count > 0 && blockQ.Count > 0)",
    "_sessIter.GetNextSession(tEv, true)",
    "UpdateZones(s);",
    "ProcessBar(s, askMap, bidMap",
])
def test_el_cs_tiene_la_pieza(pieza):
    assert pieza in _cs(), pieza


@pytest.mark.parametrize("resto", [
    "pendingAsk", "pendingBid", "pendingVolume",
    "Take + reset",
    "Bars.IsFirstBarOfSession",
])
def test_el_cs_no_conserva_nada_del_patron_viejo(resto):
    assert resto not in _cs_codigo(), resto


def test_el_cs_llama_UpdateZones_ANTES_de_ProcessBar():
    """P5 en el código: el orden de las dos llamadas dentro del drenaje."""
    s = _cs()
    i = s.index("private void DrainReadyBars()")
    j = s.index("private bool VerificarOHLC")
    cuerpo = s[i:j]
    assert cuerpo.index("UpdateZones(s);") < cuerpo.index("ProcessBar(s,")


def test_el_cs_no_toma_de_menos():
    """No debe existir un camino que procese con menos de K cuando K > 0."""
    s = _cs_codigo()
    assert "Math.Min(fpTicksPerBar" not in s
    assert "blockQ.Count >= 1 ? " not in s
