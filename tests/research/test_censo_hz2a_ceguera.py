"""C-A · Gate de ceguera del censo H-Z2A (entrada 021 §5).

El auditor verificó por **lectura de código** que el runner es ciego a outcomes, y
señaló lo que falta: *«hoy es construcción + declaración, no gate»*. Es la misma
familia que P-34 / P-35 / P-39 / P-41 — una propiedad afirmada en vez de derivada.

Este archivo la convierte en gate. La parte fuerte NO es mirar imports: es
**invarianza metamórfica**.

    Si el censo deja de medir en A2, entonces todo lo que pase DESPUES de A2
    no puede cambiar ni un conteo.

Un test de imports se puede satisfacer sin ser ciego (basta calcular el outcome
inline). La invarianza no: si el censo mirara acceso, penetración o cualquier
resultado posterior, reemplazar la cola por su opuesto cambiaria la salida.

Los casos son de geometria conocida y construidos a mano, no muestreados.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

import numpy as np
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
RUNNER = REPO / "diag" / "tasa_senales" / "censo_hz2a_superficie.py"


def _cargar():
    """El nombre del archivo no es importable como modulo (tiene guiones bajos pero
    vive fuera de un paquete), asi que se carga por path."""
    spec = importlib.util.spec_from_file_location("censo_hz2a", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def censo():
    return _cargar()


# ---------------------------------------------------------------------------
# Parte 1 -- estatica. Necesaria pero NO suficiente: se puede pasar y no ser ciego.
# ---------------------------------------------------------------------------

# Simbolos que sólo existen para medir qué pasó DESPUES del landmark.
PROHIBIDOS = (
    "mfe", "mae", "pnl", "profit", "first_passage", "tick_first_touch_race",
    "run_first_passage_race", "outcome", "hazard", "kaplan", "survival",
)


def test_el_runner_no_nombra_simbolos_de_outcome(censo):
    """Un `grep` no prueba ceguera, pero su violacion sí prueba lo contrario."""
    fuente = RUNNER.read_text(encoding="utf-8")
    # Se elimina TODA la prosa antes de buscar. El docstring del modulo explica que NO
    # se miden outcomes, y nombrarlos ahi es correcto: buscar sobre el archivo crudo
    # confundiria la explicacion con el pecado.
    sin_doc = re.sub(r'"""'r'.*?'r'"""', "", fuente, flags=re.S)
    codigo = "\n".join(l.split("#")[0] for l in sin_doc.splitlines()).lower()
    hallados = [s for s in PROHIBIDOS if re.search(r"\b%s\b" % re.escape(s), codigo)]
    assert not hallados, (
        "el runner del censo nombra simbolos de outcome en codigo (no en prosa): %s"
        % hallados)


def test_no_importa_el_camino_de_carreras_del_portador(censo):
    """`avolcluster_tick_formal` corre carreras de primer pasaje. Importarlo traeria
    outcomes al proceso aunque no se llamaran."""
    fuente = RUNNER.read_text(encoding="utf-8")
    # Se busca un IMPORT, no una mencion: el runner se cita en comentarios a proposito,
    # para explicar por que NO se lo importa. Confundir las dos cosas haria fallar al
    # gate por documentar bien.
    imports = re.findall(r"^\s*(?:from|import)\s+.*avolcluster_tick_formal.*$",
                         fuente, flags=re.M)
    assert not imports, (
        "el censo IMPORTA el runner del portador, que corre carreras de primer "
        "pasaje: %s" % imports)


def test_declara_las_dos_banderas_del_firewall(censo):
    fuente = RUNNER.read_text(encoding="utf-8")
    assert "outcomes_accessed=False" in fuente
    assert "pnl_accessed=False" in fuente


# ---------------------------------------------------------------------------
# Parte 2 -- INVARIANZA. Este es el gate.
# ---------------------------------------------------------------------------

def _serie(patron):
    """Construye (d, toca_trade, toca_quote) desde una lista de distancias en ticks.
    `d == 0` significa dentro de la zona, o sea toque."""
    d = np.array(patron, dtype=np.int64)
    toca = d == 0
    return d, toca, toca.copy()


# A1 desde d>=10, giro en d_min=2, separacion de +6 (>=R=5), y vuelve a d<=2 => A2.
BASE = [12, 10, 6, 3, 2, 4, 6, 8, 8, 6, 3, 2, 3, 5]

# Cuatro colas mutuamente excluyentes en terminos de OUTCOME, pegadas DESPUES del A2.
COLAS = {
    "acceso_profundo": [1, 0, 0, 0, 0, 0, 0, 0],      # entra y se queda dentro
    "nunca_vuelve": [9, 14, 20, 28, 35, 40, 48, 60],  # se va para siempre
    "roza_y_rebota": [1, 3, 1, 4, 1, 5, 1, 6],        # coquetea sin entrar
    "ruido_violento": [0, 40, 0, 40, 0, 40, 0, 40],   # alterna dentro/lejos
}


def _contar(censo, patron):
    d, tt, tq = _serie(patron)
    return censo.censar_zona(d, tt, tq)


def test_apendear_datos_NUNCA_baja_un_conteo(censo):
    """EL gate, en su forma correcta.

    La primera version de este test pedia invarianza total de los conteos al cambiar
    la cola. Estaba MAL formulada: apendear datos extiende el corredor y por lo tanto
    puede contener legitimamente MAS eventos. Pedir invarianza total habria obligado a
    romper el censo para que pase.

    La propiedad correcta de una medicion forward-only es **monotonia**: apendear
    datos puede sumar eventos nuevos, pero JAMAS puede borrar uno ya completado. Si el
    censo mirara hacia atras desde un outcome --por ejemplo contando solo los
    near-miss que despues accedieron-- una cola sin acceso BAJARIA un conteo.

    Y es exactamente lo que pasaba: el `argmin` sobre el corredor entero hacia que un
    acceso posterior se volviera el `d_min` y matara un near-miss anterior (1 -> 0).
    Este test lo caza."""
    base = _contar(censo, BASE)
    for nombre, cola in COLAS.items():
        conteos = _contar(censo, BASE + cola)
        bajaron = {k: (base[k], conteos[k]) for k in base
                   if any(n < b for b, n in zip(base[k], conteos[k]))}
        assert not bajaron, (
            "la cola '%s' HACE BAJAR conteos ya completados -- el censo mira hacia "
            "atras desde el futuro. Celdas (antes, despues): %s"
            % (nombre, dict(list(bajaron.items())[:5])))


def test_truncar_nunca_sube_un_conteo(censo):
    """Simetrico del anterior. Cortar la serie no puede INVENTAR eventos."""
    for nombre, cola in COLAS.items():
        completo = _contar(censo, BASE + cola)
        truncado = _contar(censo, BASE)
        subieron = {k: (completo[k], truncado[k]) for k in completo
                    if any(tr > co for co, tr in zip(completo[k], truncado[k]))}
        assert not subieron, (
            "truncar la cola '%s' SUBE conteos: el censo inventa eventos al perder "
            "datos. %s" % (nombre, dict(list(subieron.items())[:5])))


def test_el_gate_SI_detecta_un_censo_que_mira_el_futuro(censo):
    """Control negativo del gate. Un test de invarianza que nunca puede fallar no es
    un gate. Se construye a mano un contador que SI mira la cola (cuenta accesos
    posteriores) y se verifica que las cuatro colas lo distinguen."""
    def censar_retrospectivo(d, tt, tq):
        """Censo prohibido: solo cuenta el near-miss si DESPUES hubo acceso. Es
        exactamente la clase de defecto que el gate tiene que atrapar."""
        base = censo.censar_zona(d, tt, tq)
        hubo_acceso = bool((d[len(BASE):] == 0).any())
        return {k: (v[0], v[1] if hubo_acceso else 0, v[2]) for k, v in base.items()}

    base = censo.censar_zona(*_serie(BASE))
    detectado = False
    for nombre, cola in COLAS.items():
        d, tt, tq = _serie(BASE + cola)
        esp = censar_retrospectivo(d, tt, tq)
        if any(any(n < b for b, n in zip(base[k], esp[k])) for k in base):
            detectado = True
    assert detectado, (
        "el control negativo no fue atrapado por la regla de monotonia: el gate no "
        "probaria nada")


def test_la_geometria_base_produce_el_evento_esperado(censo):
    """Si BASE no generara near-miss ni A2, los tests de invarianza serian vacuos:
    comparar ceros contra ceros. Se fija que el caso es informativo."""
    clave = (10, 2, 5, "trade")     # D_far=10, delta=2, R_min=5, predicado primario
    a1, nm, a2 = _contar(censo, BASE)[clave]
    assert a1 == 1, "BASE deberia ser UNA entrada al corredor, dio %d" % a1
    assert nm == 1, "BASE deberia producir exactamente 1 near-miss, dio %d" % nm
    assert a2 == 1, "BASE deberia producir exactamente 1 A2, dio %d" % a2

    # Y con la cola que se aleja aparece un SEGUNDO ciclo: la serie vuelve a d_min=2 y
    # se separa de nuevo. Dos near-miss es la lectura correcta de v4 --dos
    # aproximaciones, cada una con su rechazo-- no un doble conteo. Se fija para que
    # nadie lo "arregle" al valor viejo.
    nm_con_cola = _contar(censo, BASE + COLAS["nunca_vuelve"])[clave][1]
    assert nm_con_cola == 2, (
        "la cola que se aleja deberia habilitar un 2do ciclo (2 near-miss), dio %d"
        % nm_con_cola)


def test_un_toque_antes_del_giro_mata_el_near_miss(censo):
    """El predicado exige 'ningun trade dentro de [L,U] ANTES del giro'. Se fija por
    construccion: la misma geometria con un 0 antes del minimo no es near-miss."""
    con_toque = [12, 10, 6, 0, 2, 4, 6, 8, 8, 6, 3, 2, 3, 5]
    clave = (10, 2, 5, "trade")
    assert _contar(censo, con_toque)[clave][1] == 0, (
        "un toque antes del giro deberia invalidar el near-miss y no lo hace")


# ---------------------------------------------------------------------------
# Parte 3 -- geometria de la grilla. Agregado 2026-08-18 tras la entrada 025.
#
# El auditor pidio "declarar que las celdas ya no anidan en delta". No se declara:
# se computa, y al computarlo aparecieron DOS causas distintas, una de las cuales
# era un bug mio.
# ---------------------------------------------------------------------------

def test_un_ciclo_que_no_separa_no_mata_a_los_que_siguen(censo):
    """EL segundo bug, de la misma familia que el `argmin`.

    El escaneo por ciclos tenia un `break` cuando un minimo no alcanzaba a separarse
    R ticks: abandonaba el corredor ENTERO. Pero un minimo posterior mas profundo
    tiene un umbral mas bajo (`d_min' + R`) y puede alcanzarlo de sobra.

    Caso: D_far=10, R=5. Un minimo d=5 es INOBSERVABLE --exige llegar a d>=10, y
    d>=10 cierra el corredor por definicion-- seguido de un minimo d=2 que separa
    sin problema. Con el `break`, delta=5 y delta=8 daban 0 mientras delta=3 daba 1:
    ampliar la ventana PERDIA el evento."""
    serie = [12, 8, 6, 5, 6, 7, 8, 6, 4, 2, 4, 6, 8, 9, 7, 5, 6, 11]
    for dl in (3, 5, 8):
        nm = _contar(censo, serie)[(10, dl, 5, "trade")][1]
        assert nm == 1, (
            "con delta=%d el minimo profundo d=2 deberia contar 1 near-miss, dio %d "
            "-- un ciclo que no separa esta abandonando el corredor" % (dl, nm))


def test_la_degeneracion_de_la_grilla_es_aritmetica_no_empirica(censo):
    """17 de las 60 celdas de la grilla congelada no pueden producir un near-miss por
    aritmetica pura: si `delta + R >= D_far`, la separacion exigida cae fuera del
    corredor. No hace falta un tick para saberlo, y por eso tiene que estar computado
    en el artefacto y no razonado por el lector."""
    degeneradas = [(D, dl, R) for D in censo.D_FAR for dl in censo.DELTA_NM
                   for R in censo.R_MIN if dl + R >= D]
    assert len(degeneradas) == 17, (
        "la grilla congelada deberia tener 17 celdas degeneradas, tiene %d -- si la "
        "grilla cambio, esta cuenta cambia con ella" % len(degeneradas))

    # Las estructuralmente nulas: ni el minimo mas profundo posible (d_min=1) separa.
    nulas = [(D, dl, R) for (D, dl, R) in degeneradas if D - R - 1 < 1]
    assert len(nulas) == 15


def test_los_anillos_NO_anidan_y_el_censo_lo_dice(censo):
    """Documenta la segunda causa, que NO es un bug sino una decision de estimand sin
    tomar (P-45): la segmentacion es golosa y depende de delta. Con delta grande un
    minimo poco profundo califica primero, consume el corredor hasta su rechazo y
    saltea minimos mas profundos que un delta chico si habria contado aparte.

    El conjunto de EVENTOS anida --un near-miss de d_min=2 califica para todo
    delta>=2-- pero el CONTEO no. Este test fija que el fenomeno existe, para que
    nadie lea el anillo marginal de la entrada 014 como si anidara."""
    serie = ([25] + [16, 17, 15, 12, 9, 13, 16, 18, 15, 19, 12, 10, 13, 17, 13,
                     15, 12, 8, 12, 9, 6, 3, 5, 4, 8, 4, 8, 11, 9, 11, 14, 17,
                     13, 10, 15, 19] + [25])
    d = np.array(serie, dtype=np.int64)
    toca = d == 0
    c = censo.censar_zona(d, toca, toca.copy())
    por_delta = [c[(20, dl, 5, "trade")][1] for dl in censo.DELTA_NM]
    assert any(y < x for x, y in zip(por_delta, por_delta[1:])), (
        "esta serie deberia exhibir el conteo NO monotono en delta; dio %s. Si dejo "
        "de pasar, la segmentacion cambio y P-45 hay que releerla" % por_delta)
