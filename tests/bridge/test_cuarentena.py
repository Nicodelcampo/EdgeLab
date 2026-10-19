# -*- coding: utf-8 -*-
"""Cuarentena estructural por versión (Decisión B de Nico, 2026-07-26).

La versión débil de esta decisión sería "acordarse de no usar los datos viejos".
Falla de tres maneras previsibles: alguien nuevo no lo sabe, el que lo sabe se
olvida, o un script lo lee solo. Y el defecto es **silencioso** — un CSV
contaminado se parsea igual de bien que uno limpio, sólo que le faltan el 47 %
de los gaps de 1 tick.

Estos tests fijan que el filtro viva en el CAMINO DE INGESTA, no en la memoria.
"""
import os

import pytest

from edgelab.bridge import oracle, quarantine
from edgelab.bridge.quarantine import DatosEnCuarentena

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

META_SUCIO = ("# meta indicator=AACloseOpenDiffs,version=1.0,subseries=minute_1_always,"
              "instrument=6E 09-26,tick_size=5E-05,min_diff_ticks=1")
META_LIMPIO = META_SUCIO.replace("version=1.0", "version=1.2")
FILAS = ("event_seq,event_type,ts,unix_ms,zone_id,start_ms,end_ms,upper,lower,"
         "diff_ticks,direction,overlap_at_birth,m1_bar\n"
         "1,ZONE_CREATED,2026-07-13 22:01:00.000,1784073660000,D000002,"
         "1784073660000,1784076660000,1.16,1.15995,1,-1,1,100\n")


def _csv(tmp_path, meta, nombre="x.csv"):
    p = tmp_path / nombre
    p.write_text(meta + "\n" + FILAS, encoding="utf-8")
    return str(p)


# ------------------------------------------------------- el filtro estructural
def test_el_camino_de_ingesta_rechaza_los_datos_sucios(tmp_path):
    with pytest.raises(DatosEnCuarentena) as e:
        oracle.parse_nt8_log(_csv(tmp_path, META_SUCIO), chart_tz="UTC", tick_size=5e-05)
    msg = str(e.value)
    assert "version=1.0" in msg and "limpio desde v1.1" in msg
    # El mensaje tiene que explicar el SESGO, no sólo decir que está prohibido:
    # quien lo lea tiene que poder decidir si su análisis quedó contaminado.
    assert "SISTEMÁTICO" in msg and "CORRELACIONADO" in msg


def test_los_datos_limpios_pasan(tmp_path):
    o = oracle.parse_nt8_log(_csv(tmp_path, META_LIMPIO), chart_tz="UTC", tick_size=5e-05)
    assert o["indicator"] == "AACloseOpenDiffs"
    assert len(o["zones"]) == 1


def test_el_escape_forense_es_explicito_y_deja_rastro(tmp_path):
    """Leer los datos sucios para MEDIR el defecto es legítimo; usarlos, no."""
    o = oracle.parse_nt8_log(_csv(tmp_path, META_SUCIO), chart_tz="UTC",
                             tick_size=5e-05, allow_quarantined=True)
    assert len(o["zones"]) == 1


def test_sin_version_legible_NO_es_limpio(tmp_path):
    """Fail-closed: un archivo del indicador sin versión no se afirma limpio."""
    meta = "# meta indicator=AACloseOpenDiffs,subseries=minute_1_always"
    with pytest.raises(DatosEnCuarentena) as e:
        oracle.parse_nt8_log(_csv(tmp_path, meta), chart_tz="UTC", tick_size=5e-05)
    assert "fail-closed" in str(e.value)


def test_los_otros_indicadores_no_se_ven_afectados(tmp_path):
    """La cuarentena es por indicador: no puede volverse un bloqueo global."""
    for ind in ("Gaps2", "HFTZones2", "VolTicksPOC2", "aVolCellPOI2", "BigTrap2"):
        r = quarantine.evaluar_meta("# meta indicator=%s,version=1.0" % ind)
        assert r["estado"] == "limpio", ind


def test_la_comparacion_de_version_es_numerica_no_lexicografica():
    """"1.10" < "1.9" como texto: sería un bug silencioso con diez versiones."""
    assert quarantine.evaluar_meta(
        "indicator=AACloseOpenDiffs,version=1.10")["estado"] == "limpio"
    assert quarantine.evaluar_meta(
        "indicator=AACloseOpenDiffs,version=1.0")["estado"] == "cuarentena"
    assert quarantine.evaluar_meta(
        "indicator=AACloseOpenDiffs,version=0.9")["estado"] == "cuarentena"
    assert quarantine.evaluar_meta(
        "indicator=AACloseOpenDiffs,version=2.0")["estado"] == "limpio"


# ------------------------------------------------- el .cs sostiene el contrato
def test_el_cs_escribe_su_version_en_CADA_FILA_del_logger():
    """El logger MERGEA corridas: una versión a nivel de archivo sería falsa.

    Éste es el hueco que dejó pasar el defecto de v1.0 durante todo su
    histórico: el logger de research no registraba con qué versión se generó
    cada fila, así que no había forma de filtrarlo retroactivamente.
    """
    src = open(os.path.join(REPO, "nt8", "AACloseOpenDiffs.cs"),
               encoding="utf-8-sig").read()
    assert 'private const string IND_VERSION = "1.2";' in src
    assert "overlap_at_birth,m1_bar,ind_version" in src      # header
    assert "z.M1Bar, IND_VERSION);" in src                    # cada fila
    # Una sola fuente de verdad: el meta de paridad usa la misma constante.
    assert 'indicator=AACloseOpenDiffs,version=" + IND_VERSION' in src


def test_la_version_del_cs_esta_por_encima_del_umbral_de_cuarentena():
    """Si alguien bajara la versión del `.cs`, sus propios datos entrarían en
    cuarentena — y este test lo diría antes de gastar un export."""
    src = open(os.path.join(REPO, "nt8", "AACloseOpenDiffs.cs"),
               encoding="utf-8-sig").read()
    import re
    v = re.search(r'IND_VERSION\s*=\s*"([\d.]+)"', src).group(1)
    r = quarantine.evaluar_meta("indicator=AACloseOpenDiffs,version=%s" % v)
    assert r["estado"] == "limpio", (v, r)


# --------------------------------------------------------------- el material
def test_el_material_en_cuarentena_se_conserva_crudo():
    """No se borra: es la evidencia de la magnitud del defecto (43,5 %)."""
    d = os.path.join(REPO, "archive", "cuarentena", "aacloseopendiffs_pre_v1.1")
    assert os.path.isdir(d), "falta el directorio de cuarentena"
    hay = [f for f in os.listdir(d) if f.endswith(".csv")]
    assert hay, "la cuarentena está vacía: el material forense se perdió"


def test_la_cuarentena_declara_su_procedencia():
    reg = quarantine.CUARENTENA["AACloseOpenDiffs"]
    assert reg["min_version_limpia"] == "1.1"
    assert reg["fecha"] == "2026-07-26"
    assert "Nico" in reg["decision"]
    assert "AUDIT-003" in reg["ref"]
