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

    # ENMENDADO 2026-08-18 por P-45 (c). Antes de la decision de Nico este test fijaba
    # 2 near-miss: la serie vuelve a d_min=2 y se separa, y eso se leia como un segundo
    # ciclo. Bajo (c) ese segundo acercamiento es el RETORNO del episodio que abrio el
    # primero -- es A2, no un near-miss nuevo. El valor correcto pasa a ser 1, y el
    # cambio es la decision del estimand, no un arreglo de conteo.
    a1c, nmc, a2c = _contar(censo, BASE + COLAS["nunca_vuelve"])[clave]
    assert (nmc, a2c) == (1, 1), (
        "bajo (c) la cola que se aleja deja 1 near-miss + 1 A2, dio %d y %d"
        % (nmc, a2c))


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
    """Documenta la consecuencia que la decision de P-45 (c) NO resuelve.

    El auditor prefirio (b) justamente porque comparar celdas entre delta solo tiene
    sentido si miden la misma poblacion filtrada. Nico eligio (c). Medido: bajo (c)
    la no-anidacion PERSISTE --y aumenta-- porque la segmentacion en episodios sigue
    dependiendo de delta: con delta grande el retorno se absorbe antes y el corredor
    se consume distinto.

        con (a) golosa : 21 pares no monotonos sobre 19.200
        con (c) episodio: 49

    Numeros en `diag/tasa_senales/barrido_anidacion.py`, deterministico.

    Consecuencia vigente: el anillo marginal de la entrada 014 NO se lee como anidado
    y `n_near_miss_marginal` puede ser negativo. No reabre la decision --el estimand
    lo eligio Nico-- pero tiene que estar fijado y no descubrirse leyendo una tabla.

    El testigo se BUSCA con semilla fija en vez de cablear una serie: una serie
    cableada deja de exhibir el fenomeno en cuanto cambia el estimand, y entonces el
    test miente diciendo que el fenomeno desaparecio."""
    rng = np.random.default_rng(20260818)
    violaciones = 0
    for _ in range(120):
        d = (np.abs(np.cumsum(rng.integers(-4, 5, 120))) % 90).astype(np.int64)
        toca = d == 0
        c = censo.censar_zona(d, toca, toca.copy())
        for D in censo.D_FAR:
            for R in censo.R_MIN:
                s = [c[(D, dl, R, "trade")][1] for dl in censo.DELTA_NM]
                violaciones += sum(1 for x, y in zip(s, s[1:]) if y < x)
    assert violaciones > 0, (
        "no se encontro ninguna violacion de anidacion: si la segmentacion dejo de "
        "depender de delta, esto es una BUENA noticia pero cambia lo que P-45 dice y "
        "hay que releerla, no borrar el test")


# ---------------------------------------------------------------------------
# Parte 4 -- P-45 (c): EPISODIO. Decision de Nico, 2026-08-18.
#
# «Una vez que se cumplio el near miss, el 2do [acercamiento] ... se consideraria
# simplemente parte del retorno a la zona, y si luego se dieran las condiciones para
# considerarlo como otro near miss, entonces ahi si se lo consideraria.»
#   -- docs/research/INTAKE_NICO_HZ2A_EXPLORATORIO_2026-08-18.md
#
# Sin este test la implementacion de (c) seria otra propiedad declarada y no derivada.
# ---------------------------------------------------------------------------

# Tres bajadas identicas a d=2 con separacion a d=8. D=10, delta=2, R=5.
#   bajada 1 -> near-miss                    (abre el episodio)
#   bajada 2 -> A2, el RETORNO               (NO es un segundo near-miss)
#   bajada 3 -> near-miss, episodio nuevo    (el anterior ya cerro)
TRES_BAJADAS = [12, 8, 5, 2, 4, 6, 8, 5, 2, 4, 6, 8, 5, 2, 4, 6, 8, 11]


def test_el_retorno_NO_se_cuenta_como_segundo_near_miss(censo):
    """EL test que pidio el auditor.

    La version anterior reanudaba con `i = r + 1`, o sea DENTRO de la aproximacion de
    vuelta: esa misma vuelta bajaba a d_min, se separaba, y se contaba como near-miss
    nuevo. Bajo (c) el retorno pertenece al episodio abierto.

    Con 3 bajadas iguales: 2 near-miss (la 1ra y la 3ra) y 1 A2 (la 2da). Si diera 3
    near-miss, el retorno se esta contando dos veces."""
    a1, nm, a2 = _contar(censo, TRES_BAJADAS)[(10, 2, 5, "trade")]
    assert nm == 2, (
        "3 bajadas bajo (c) son 2 near-miss (1ra y 3ra) -- dio %d. Si dio 3, el "
        "retorno se esta contando como near-miss nuevo, que es justo lo que (c) "
        "prohibe" % nm)
    assert a2 == 1, "la 2da bajada es el retorno del 1er episodio: 1 A2, dio %d" % a2
    assert a1 == 1, "un solo corredor, dio %d entradas" % a1


def test_el_episodio_se_cierra_recien_al_salir_de_la_banda(censo):
    """Detalle de implementacion que ya fallo una vez: no alcanza con saltar UN indice
    despues del retorno. Si el escaneo se reanuda dentro de la banda delta, vuelve a
    descender por la MISMA aproximacion de vuelta y la cuenta.

    Retorno largo --el precio se queda varias barras dentro de delta antes de salir--
    y una sola bajada posterior. Sigue siendo 2 near-miss, no 3."""
    serie = [12, 8, 5, 2, 4, 6, 8, 5, 2, 2, 1, 2, 2, 4, 6, 8, 5, 2, 4, 6, 8, 11]
    nm = _contar(censo, serie)[(10, 2, 5, "trade")][1]
    assert nm == 2, (
        "un retorno que se queda dentro de delta no puede generar near-miss extra; "
        "dio %d" % nm)


def test_un_near_miss_sin_retorno_sigue_siendo_near_miss(censo):
    """(c) cambia cuando se cuenta el SEGUNDO, no invalida el primero. Si el precio se
    va y no vuelve, el near-miss existe y el A2 no."""
    serie = [12, 8, 5, 2, 4, 6, 8, 9, 8, 9, 8, 9, 11]
    a1, nm, a2 = _contar(censo, serie)[(10, 2, 5, "trade")]
    assert (nm, a2) == (1, 0), "esperado 1 near-miss y 0 A2, dio %d y %d" % (nm, a2)
