r"""Semántica de disponibilidad de las zonas que alimentan corredores y perfil de densidad.

Valida (Gate B):
1. clasificación EXPLICIT vs ORIGIN_FALLBACK_UNVERIFIED;
2. controles de UI de zonas exploratorias y su insignia persistente;
3. estados del perfil de densidad;
4. el adaptador `toFieldZones` (zona del visor -> zona canónica): las exploratorias entran a la
   densidad SOLO si se lo pide, y las explícitas siempre.

Reescrito el 2026-09-21 al unificar la definición de densidad: antes extraía `densityTsSec` y
`buildCrosshairDensityRanges` del HTML (una implementación propia del kernel); ahora esas funciones no
existen y la disponibilidad sale del módulo canónico (`density_field.js`), que se carga real en Node.
Los tres escenarios A/B/C son los mismos de antes.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEWER = ROOT / "viewer" / "nt8_bridge"
VIEWER_HTML = VIEWER / "index.html"
DF_JS = VIEWER / "density_field.js"


def test_viewer_html_contains_required_controls():
    content = VIEWER_HTML.read_text(encoding="utf-8")
    assert 'id="chk-show-exploratory"' in content
    assert 'id="chk-include-exploratory-density"' in content
    assert "EXPLORATORY — t0 USED AS UNVERIFIED AVAILABILITY" in content
    assert "zoneAvailabilityInfo" in content
    assert "PASS_CAUSAL_DENSITY_PROFILE" in content
    assert "PASS_EXPLORATORY_DENSITY_PROFILE" in content
    assert "ABSTAIN_NO_ZONES" in content          # sin zonas elegibles el campo se abstiene


def test_no_queda_un_kernel_de_densidad_propio_en_el_html():
    content = VIEWER_HTML.read_text(encoding="utf-8")
    for muerto in ("buildCrosshairDensityRanges", "EdgeLabCrosshairDensity", "densityTsSec(", "livingWalls"):
        assert muerto not in content, muerto
    assert 'src="density_field.js"' in content
    assert "window.EdgeLabDensityField.extractZoneAvailableNs" in content


def test_js_availability_and_adapter_semantics_in_node():
    script = r"""
    const fs = require('fs');
    const html = fs.readFileSync(process.argv[1], 'utf8');
    global.window = { EdgeLabDensityField: require(process.argv[2]) };

    // Extrae una funcion del IIFE principal contando llaves (sin depender de su indentacion).
    function extract(name) {
      const i = html.indexOf('function ' + name + '(');
      if (i < 0) throw new Error('no se encontro ' + name);
      let d = 0, j = html.indexOf('{', i);
      for (let k = j; k < html.length; k++) {
        if (html[k] === '{') d++;
        else if (html[k] === '}') { d--; if (d === 0) return html.slice(i, k + 1); }
      }
      throw new Error('llaves desbalanceadas en ' + name);
    }
    for (const n of ['zoneAvailabilityInfo', 'zoneAvailableSec', 'toFieldZones']) eval(extract(n).replace(/^function (\w+)/, 'global.$1 = function'));

    // 1. Zona explicita
    const zExp = { id: 'E', top: 100, bottom: 98, available_ts: 1700000000, t0: 1699990000, vol: 10 };
    const iE = zoneAvailabilityInfo(zExp);
    if (iE.quality !== 'EXPLICIT' || !iE.isExplicit || iE.sec !== 1700000000) throw new Error('explicita: ' + JSON.stringify(iE));

    // 2. Zona exploratoria (cae a t0)
    const zEx = { id: 'X', top: 100, bottom: 98, t0: 1700000000, vol: 10 };
    const iX = zoneAvailabilityInfo(zEx);
    if (iX.quality !== 'ORIGIN_FALLBACK_UNVERIFIED' || iX.isExplicit || iX.sec !== 1700000000) throw new Error('exploratoria: ' + JSON.stringify(iX));

    // 3. Sin nada: ni disponibilidad ni origen
    const zN = { id: 'N', top: 100, bottom: 98, vol: 10 };
    if (zoneAvailabilityInfo(zN).quality !== 'NONE' || zoneAvailabilityInfo(zN).sec !== null) throw new Error('none');

    // 4. El ayudante ESTRICTO no cae a t0 (salvo luxalgo)
    if (zoneAvailableSec(zEx) !== null) throw new Error('el estricto cayo a t0');
    if (zoneAvailableSec(Object.assign({ source: 'luxalgo' }, zEx)) !== 1700000000) throw new Error('luxalgo');
    if (zoneAvailableSec(zExp) !== 1700000000) throw new Error('estricto explicito');

    // 5. Adaptador. Escenario A: solo exploratoria, sin pedirla -> queda afuera
    global.visible = () => true;
    global.state = { data: { meta: { tick_size: 0.25 } } };
    global.activeProps = { consumption_mode: 'fixed' };
    let r = toFieldZones([zEx], false);
    if (r.zones.length !== 0 || r.excluded.exploratoryExcluded !== 1) throw new Error('A: ' + JSON.stringify(r));
    // B: pidiendola -> entra, marcada
    r = toFieldZones([zEx], true);
    if (r.zones.length !== 1 || r.excluded.exploratoryIncluded !== 1) throw new Error('B: ' + JSON.stringify(r));
    // C: explicita, sin pedir exploratorias -> entra como explicita
    r = toFieldZones([zExp], false);
    if (r.zones.length !== 1 || r.excluded.exploratoryIncluded !== 0 || r.excluded.exploratoryExcluded !== 0) throw new Error('C: ' + JSON.stringify(r));

    // 6. `touches` (conteo FINAL) NO se pasa: seria look-ahead en el desgaste
    r = toFieldZones([Object.assign({ touches: 9 }, zExp)], false);
    if ('touches' in r.zones[0]) throw new Error('touches se filtro al campo');

    // 7. `t1` solo es muerte si la zona trae state != ACTIVE
    r = toFieldZones([Object.assign({ t1: 1700000500 }, zExp)], false);
    if ('ended_ts' in r.zones[0]) throw new Error('t1 sin state se tomo como muerte');
    r = toFieldZones([Object.assign({ t1: 1700000500, state: 'INVALIDATED' }, zExp)], false);
    if (r.zones[0].ended_ts !== 1700000500) throw new Error('t1 con state INVALIDATED debia ser muerte');

    console.log('PASS_AVAILABILITY_SEMANTICS_JS');
    """
    res = subprocess.run(["node", "-e", script, str(VIEWER_HTML), str(DF_JS)],
                         capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, res.stderr
    assert "PASS_AVAILABILITY_SEMANTICS_JS" in res.stdout
