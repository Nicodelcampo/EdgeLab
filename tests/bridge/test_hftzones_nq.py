"""HFTZonesNQ: motor de rachas, con detección y aceptación separadas.

Lo que fija esta suite, por encima de la corrección del motor, es la decisión de
arquitectura: **una pasada por tick produce el censo completo, y los diez umbrales se
aplican después**. Si algún test tuviera que volver a llamar a `detect_candidates` para
cambiar un umbral, la separación se rompió.
"""
import pytest

from edgelab.bridge.indicators import hftzones_nq as hz

MS = 1_000_000  # ns por milisegundo


def _stream(precios, ms_entre=1.0, vol=10.0):
    """Tick stream sintético: precios en ticks, cadencia y volumen constantes."""
    ts = [int(i * ms_entre * MS) for i in range(len(precios))]
    return ts, list(precios), [float(vol)] * len(precios)


def _racha_bajista(n=12, desde=1000):
    return list(range(desde, desde - n, -1))


# ------------------------------------------------- la separación es el punto

def test_UNA_pasada_por_tick_alcanza_para_barrer_todos_los_umbrales():
    """El resultado que hace viable la investigación.

    Detectar es caro (recorre ticks); aceptar es aritmética sobre el censo. Este test
    detecta UNA vez y evalúa dos configuraciones distintas.
    """
    ts, px, vol = _stream(_racha_bajista(12))
    cands = hz.detect_candidates(ts, px, vol)

    laxo, _ = hz.accept_all(cands, dict(min_pasos=3, min_volume_rate=0,
                                        min_total_volume=0))
    estricto, _ = hz.accept_all(cands, dict(min_pasos=50))
    assert len(laxo) > len(estricto) == 0


def test_el_censo_incluye_los_candidatos_RECHAZADOS():
    """Sin los rechazados no se puede aflojar un umbral sin re-correr todo."""
    ts, px, vol = _stream(_racha_bajista(4))       # 4 pasos: no llega a min_pasos=8
    cands = hz.detect_candidates(ts, px, vol)
    assert cands, "la racha existe como candidato"
    zonas, motivos = hz.accept_all(cands)
    assert zonas == [] and motivos == {"pasos": len(cands)}


def test_accept_all_dice_POR_QUE_se_cayo_cada_candidato():
    """Un barrido vacío sin motivo es indistinguible de un umbral mal puesto."""
    ts, px, vol = _stream(_racha_bajista(12), ms_entre=100.0, vol=1.0)
    cands = hz.detect_candidates(ts, px, vol, dict(max_pausa_ms=1e9))
    _, motivos = hz.accept_all(cands)
    assert motivos, "tiene que reportar al menos un motivo"
    assert set(motivos) <= set(hz.GATE_ORDER)


# ------------------------------------------------- máquina de estados

def test_una_pausa_larga_corta_la_racha():
    ts, px, vol = _stream(_racha_bajista(10))
    ts[5] += int(500 * MS)                          # silencio de 500 ms
    for k in range(6, len(ts)):
        ts[k] += int(500 * MS)
    cands = hz.detect_candidates(ts, px, vol, dict(max_pausa_ms=100))
    assert len(cands) >= 2, "la pausa parte la racha en dos"


def test_sin_pausa_la_racha_queda_entera():
    """10 precios dan 9 pasos: el primer tick no tiene anterior contra el cual
    comparar dirección ni medir el intervalo, igual que NT8 sale temprano con
    `if (CurrentBars[ds] < 1) return;`."""
    ts, px, vol = _stream(_racha_bajista(10))
    cands = hz.detect_candidates(ts, px, vol, dict(max_pausa_ms=100))
    assert len(cands) == 1
    assert cands[0]["pasos"] == 9


def test_un_retroceso_grande_termina_la_racha_y_abre_otra():
    # baja 10 ticks y despues sube 10 de golpe
    px = _racha_bajista(10) + list(range(991, 1001))
    ts, px, vol = _stream(px)
    cands = hz.detect_candidates(ts, px, vol, dict(max_pausa_ms=1e9))
    assert len(cands) >= 2
    assert cands[0]["direction"] == -1
    assert any(c["direction"] == 1 for c in cands[1:])


def test_los_estadisticos_suficientes_reconstruyen_cada_compuerta():
    """Cada umbral del `.cs` tiene que ser computable desde el censo, sin ticks."""
    ts, px, vol = _stream(_racha_bajista(12))
    c = hz.detect_candidates(ts, px, vol)[0]
    for campo in ("valid_steps", "height_ticks", "avg_ms", "total_ms",
                  "vol_rate", "total_vol", "max_retro_ticks"):
        assert campo in c, campo
    # y la relación entre ellos es la del original
    assert c["avg_ms"] == pytest.approx(c["total_ms"] / c["n_intervals"])
    assert c["vol_rate"] == pytest.approx(
        c["total_vol"] / (max(c["total_ms"], 1.0) / 1000.0))


# ------------------------------------------------- compuertas de aceptación

def test_absorb_usa_un_minimo_de_pasos_DISTINTO():
    ts, px, vol = _stream(_racha_bajista(7))        # altura 6 ticks
    c = hz.detect_candidates(ts, px, vol)[0]
    # con min_sweep alto pasa a ser ABSORB y aplica min_absorb_pasos
    ok, gate = hz.accept(c, dict(min_sweep_ticks=99, min_absorb_pasos=6,
                                 min_pasos=99, min_volume_rate=0,
                                 min_total_volume=0))
    assert ok, gate
    ok, gate = hz.accept(c, dict(min_sweep_ticks=99, detect_absorb=False,
                                 min_pasos=1, min_absorb_pasos=1))
    assert not ok and gate == "sweep_o_absorb"


def test_la_compuerta_de_retroceso_NO_aplica_a_absorb():
    """Regla del original: `limpioOk = isAbsorb || (maxRetro <= permitido)`.

    Es la compuerta que `hftzones2.py` no tiene, y por la que ese módulo no sirve
    como espejo de este motor.
    """
    ts, px, vol = _stream(_racha_bajista(8))
    c = dict(hz.detect_candidates(ts, px, vol)[0])
    c["max_retro_ticks"] = 999.0
    base = dict(min_pasos=1, min_absorb_pasos=1, min_volume_rate=0,
                min_total_volume=0)
    ok, gate = hz.accept(c, dict(base, min_sweep_ticks=1))
    assert not ok and gate == "retroceso"
    ok, _ = hz.accept(c, dict(base, min_sweep_ticks=99))     # ahora es ABSORB
    assert ok, "un ABSORB no se descalifica por retroceso"


def test_el_bucket_no_interviene_en_la_aceptacion():
    ts, px, vol = _stream(_racha_bajista(10), ms_entre=1.0)
    c = hz.detect_candidates(ts, px, vol)[0]
    assert hz.bucket(c) == "Predator", "1 ms entre ticks"
    ok, _ = hz.accept(c, dict(min_pasos=1, min_volume_rate=0, min_total_volume=0))
    assert ok


# ------------------------------------------------- límites declarados

def test_tick_resolution_mayor_a_1_no_esta_soportado():
    """Prefiero fallar a fingir. Con resolución > 1 dos filtros dejan de ser inertes."""
    ts, px, vol = _stream(_racha_bajista(5))
    with pytest.raises(NotImplementedError):
        hz.detect_candidates(ts, px, vol, dict(tick_resolution=25))


def test_los_defaults_son_los_del_cs():
    assert hz.ACCEPT_DEFAULTS["min_pasos"] == 8
    assert hz.ACCEPT_DEFAULTS["min_sweep_ticks"] == 4
    assert hz.ACCEPT_DEFAULTS["max_avg_ms"] == 25.0
    assert hz.ACCEPT_DEFAULTS["max_total_ms"] == 500.0
    assert hz.ACCEPT_DEFAULTS["min_volume_rate"] == 100.0
    assert hz.ACCEPT_DEFAULTS["min_total_volume"] == 50.0
    assert hz.STRUCTURAL_DEFAULTS["max_pausa_ms"] == 100.0


def test_fallos_tolerados_no_existe_como_parametro():
    """Está en la UI del `.cs` y no hace nada: `fails` se escribe y nunca se lee.

    No se replica un parámetro muerto: exponerlo acá sugeriría que se puede barrer.
    """
    assert "fallos_tolerados" not in hz.STRUCTURAL_DEFAULTS
    assert "fallos_tolerados" not in hz.ACCEPT_DEFAULTS
