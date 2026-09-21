r"""Invariantes del visor unificado (`viewer/nt8_bridge/index.html`).

Estos tests existen porque la unificación de tres variantes divergentes del visor
(PR #48, el árbol local de `EdgeLab-multiasset` y el checkout principal) destapó cuatro
defectos que ningún test previo podía ver, todos del mismo tipo: **dos piezas correctas
por separado que juntas se anulan**.

1. Una función declarada dos veces en el mismo alcance. En JS la segunda declaración pisa
   a la primera, así que la variante simplificada (sin `quality`) dejaba la insignia
   "EXPLORATORY" como código inalcanzable, y el test de disponibilidad no lo notaba porque
   evalúa solo la primera definición.
2. Un `return` de abstención por `bar_key` distinto que precedía al bloque de flechas de
   señal causal, dejando ese bloque como código muerto.
3. Zonas científicas que caían a `t0` cuando faltaba `available_ts`.
4. El visor no puede tener dos implementadores del mismo objeto (ver
   `tools/visor_server.py`): la densidad y los corredores salen de un solo módulo.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEWER = ROOT / "viewer" / "nt8_bridge"
HTML = (VIEWER / "index.html").read_text(encoding="utf-8")


def _script_inline():
    partes = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", HTML, re.S)
    assert partes, "index.html no tiene script inline"
    return "\n".join(partes)


def test_no_hay_funciones_declaradas_dos_veces_en_el_mismo_alcance():
    """La segunda declaración pisa a la primera y el código de la primera queda muerto."""
    js = _script_inline()
    nombres = re.findall(r"^  function ([A-Za-z_0-9]+)\(", js, re.M)   # alcance del IIFE principal
    repetidas = sorted({n for n in nombres if nombres.count(n) > 1})
    assert repetidas == [], f"funciones declaradas mas de una vez: {repetidas}"


def test_disponibilidad_tiene_una_sola_definicion_y_sale_del_modulo_canonico():
    """`quality` alimenta la insignia EXPLORATORY. La resolución de claves/escalas NO se reimplementa
    en el HTML: se pide a EdgeLabDensityField (verificado contra Python)."""
    assert HTML.count("function zoneAvailabilityInfo(") == 1
    assert "function densityTsSec(" not in HTML
    assert "window.EdgeLabDensityField.extractZoneAvailableNs(z)" in HTML
    assert 'quality: isExplicit ? "EXPLICIT"' in HTML
    assert '"ORIGIN_FALLBACK_UNVERIFIED"' in HTML


def test_el_visor_no_calcula_densidad_ni_corredores_por_su_cuenta():
    """UNA sola definición (HP-007): index.html llama a EdgeLabDensityField y nada más. Antes había
    cinco implementaciones. Ningún kernel gaussiano ni agrupamiento de murallas dentro del HTML."""
    js = _script_inline()
    assert "DF.computeField(" in js and "DF.detectDensityIntervals(" in js and "DF.characterizeCorridors(" in js
    # sin kernel propio: el unico exp(-x*x/...) permitido en el HTML seria el de un dibujo, no de densidad
    assert "Math.exp(-(" not in js
    assert "clusterTol" not in js and "livingWalls" not in js
    assert "EdgeLabCorridorEngine" not in js and "EdgeLabCrosshairDensity" not in js


def test_la_clasificacion_direccional_se_declara_no_certificada():
    assert "CHARACTERIZATION_UNCERTIFIED" in (VIEWER / "density_field.js").read_text(encoding="utf-8")
    assert "characterization" in HTML


def test_el_consumo_por_volumen_esta_permitido_pero_rotulado_no_certificado():
    """Decisión de Nico (2026-09-21): el modo de consumo NO se retira; se rotula."""
    assert "UNCERTIFIED_CANDLE_VOLUME" in HTML
    assert "Consumo por volumen de vela: NO certificado" in HTML


def test_la_abstencion_por_bar_key_suprime_cajas_pero_no_mata_las_flechas():
    """Antes había un `return` que volvía inalcanzable el bloque 1b de flechas causales."""
    i_abstain = HTML.index("ABSTAIN_BAR_KEY_MISMATCH")
    i_flechas = HTML.index("1b. Dibujar FLECHAS DE SEÑAL")
    tramo = HTML[i_abstain:i_flechas]
    assert "boxesSuppressed" in HTML
    assert "(boxesSuppressed ? [] : state.run.zones).forEach" in HTML
    # entre la abstención y las flechas no debe haber ningún corte de la función
    assert not re.search(r"^\s*return;\s*$", tramo, re.M), "un return mata el bloque de flechas"


def test_el_ayudante_estricto_no_cae_a_t0_salvo_luxalgo():
    """`zoneAvailableSec` es el inicio causal ESTRICTO (gate del repo). Migrado de
    test_viewer_causal_zone_start.py sin debilitarlo."""
    helper = HTML[HTML.index("function zoneAvailableSec"):HTML.index("function drawZones")]
    assert 'z.source === "luxalgo"' in helper
    assert "return null;" in helper
    limpio = helper.replace('z.source === "luxalgo" && Number.isFinite(Number(z.t0))) return Number(z.t0);', "")
    assert "z.t0" not in limpio


def test_zonas_exploratorias_visibles_por_defecto_pero_marcadas():
    """Decisión de Nico (2026-09-21): visibles por defecto, con insignia persistente. El
    modo exploratorio nunca alimenta la densidad salvo que se lo pida (opt-in aparte)."""
    assert "show_exploratory_zones: true," in HTML
    assert 'id="chk-show-exploratory" checked' in HTML
    assert "EXPLORATORY — t0 USED AS UNVERIFIED AVAILABILITY" in HTML
    assert "include_exploratory_density: false," in HTML
    assert "hiddenNoAvailability" in HTML       # y si se desactiva, se avisa lo oculto


def test_la_insignia_exploratoria_depende_solo_del_modo_exploratorio():
    i = HTML.index("var zoneStartTs = zoneAvailableSec(z);")
    bloque = HTML[i:i + 600]
    assert "activeProps.show_exploratory_zones === true" in bloque
    assert "hasRenderedExploratory = true" in bloque


def test_las_cajas_nacen_en_la_barra_de_origen_y_la_disponibilidad_solo_decide_si_existen():
    """Decision de Nico 2026-09-21: la caja empieza donde se creo la zona (barra de origen de la racha).
    La disponibilidad causal sigue decidiendo si la zona existe, pero ya no ancla el dibujo. El origen se
    resuelve por indice de barra: los segundos reales no sirven en bundles con eje sintetico (una barra por
    segundo), donde la caja arrancaba minutos antes de su origen."""
    assert "ABSTAIN_BAR_KEY_MISMATCH" in HTML
    assert "var zoneStartTs = zoneAvailableSec(z);" in HTML          # gating causal intacto
    assert "var x0 = timeToX(z.t0, i0);" not in HTML                 # nunca t0 crudo en segundos reales
    assert HTML.count("var x0 = timeToX(zoneStartTs, i0);") == 2
    assert "function zoneOriginBarIndex" in HTML
    assert "var i0 = zoneOriginBarIndex(z, candles, activeKey);" in HTML
    # el indice de barra del bundle no se pisa con un cache del visor (era valido solo para su serie)
    assert "z.start_bar_idx = i0" not in HTML


def test_solo_se_dibujan_los_bordes_exteriores_de_la_zona():
    """Migrado de test_viewer_zone_outer_borders_only.py."""
    assert "ctx.strokeRect(drawX0 + 0.5, yMin_s + 0.5, rw_s, h_s);" not in HTML
    assert "isBottomOuterSlice" in HTML
    assert "isTopOuterSlice" in HTML


def test_capa_l2_existe_y_no_usa_logical_fraccionario():
    """El mapa de calor L2 se dibuja por foto del libro. `logicalToCoordinate` solo resuelve enteros (con fracciones
    devuelve 0): toda posicion entre barras pasa por `logicalToX`, que interpola entre enteros."""
    assert "function drawL2Depth" in HTML and "drawL2Depth(ctx, vr, w, hCanvas);" in HTML
    assert "function logicalToX" in HTML and "var cInterp = logicalToX(targetLogical);" in HTML
    assert "tsc.logicalToCoordinate(targetLogical)" not in HTML
    assert 'id="chk-show-l2"' in HTML and "show_l2_depth" in HTML
    assert "__l2" not in HTML and "__dbg" not in HTML and "sync=1" not in HTML      # sin instrumentacion de depuracion
