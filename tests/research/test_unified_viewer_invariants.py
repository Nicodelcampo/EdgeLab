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


def test_disponibilidad_tiene_una_sola_definicion_y_expone_calidad():
    """`quality` alimenta la insignia EXPLORATORY; si falta, la insignia no puede mostrarse."""
    assert HTML.count("function zoneAvailabilityInfo(") == 1
    assert HTML.count("function densityTsSec(") == 1
    assert 'quality: isExplicit ? "EXPLICIT"' in HTML
    assert '"ORIGIN_FALLBACK_UNVERIFIED"' in HTML


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


def test_las_cajas_se_anclan_al_inicio_causal_nunca_a_t0():
    """Migrado de test_viewer_causal_zone_start.py."""
    assert "ABSTAIN_BAR_KEY_MISMATCH" in HTML
    assert "var zoneStartTs = zoneAvailableSec(z);" in HTML
    assert "var x0 = timeToX(z.t0, i0);" not in HTML
    assert HTML.count("var x0 = timeToX(zoneStartTs, i0);") == 2
    assert "candles[z.start_bar_idx].time === zoneStartTs" in HTML
    assert "if (candles[mid].time < zoneStartTs)" in HTML


def test_solo_se_dibujan_los_bordes_exteriores_de_la_zona():
    """Migrado de test_viewer_zone_outer_borders_only.py."""
    assert "ctx.strokeRect(drawX0 + 0.5, yMin_s + 0.5, rw_s, h_s);" not in HTML
    assert "isBottomOuterSlice" in HTML
    assert "isTopOuterSlice" in HTML
