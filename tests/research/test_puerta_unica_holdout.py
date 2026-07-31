# -*- coding: utf-8 -*-
"""El holdout no se puede leer por accidente. Test ESTRUCTURAL, no de ejemplo.

## Qué se está probando y por qué así

El 2026-07-27 el atlas nulo consumió 10 días del holdout. El guard
`check_holdout` existía y estaba bien escrito; el filtro del atlas vivía en un
**docstring**. Ninguna capa era responsable, así que ninguna filtró.

Un test que sólo verifique "el atlas filtra bien" no habría impedido nada: el
atlas *tenía* la regla escrita, en prosa. Y no impediría que el estudio número
once nazca sin el filtro.

Por eso el test es **estructural**: falla si existe *cualquier* camino que lea
el manifiesto de días sin pasar por la puerta única. Es el equivalente, del lado
del proceso, de lo que el censo hace con los datos — buscar la firma del defecto
en todas partes, no confirmar el caso conocido.
"""
from __future__ import annotations

import io
import json
import os
import re

import pytest

from edgelab.research import universo_estudio as U

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Único productor legítimo del manifiesto (lo ESCRIBE, no lo consume para un
# estudio) y la propia puerta. Cualquier otro archivo que lo lea es un camino
# alternativo y el test lo denuncia.
EXENTOS = {
    os.path.join("tools", "censo_integridad.py"),        # lo genera
    os.path.join("tools", "censo_es_nq.py"),             # genera el suyo
    os.path.join("edgelab", "research", "universo_estudio.py"),   # la puerta
}


# ALCANCE DEL ENFORCEMENT — leer antes de tocar.
#
# Esta tupla NO es "dónde suele haber consumidores del manifiesto": es la
# superficie que este test vigila. **Lo que queda afuera es invisible**, y un
# punto ciego de alcance es indistinguible de un test que pasa.
#
# `sidecar` se agregó el 2026-07-31. Estuvo fuera desde el principio porque
# corre en un venv aislado (`sidecar/kronos_env`), y ese aislamiento se leyó
# como si también aislara del firewall. No aisla: `sidecar/kronos_paso2.py`
# venía leyendo el manifiesto con `json.load(open(...))` y **sin ningún filtro
# de fecha** — exactamente el patrón de INC-002, en la carpeta que este test no
# miraba. No causó daño por casualidad, no por diseño.
#
# REGLA: toda carpeta nueva con código que se ejecuta se agrega acá **en el
# mismo commit** que la crea. Si el enforcement no la cubre, no existe.
CARPETAS_VIGILADAS = ("tools", "edgelab", "sidecar")

# Subcarpetas de terceros: venv aislado, pesos del modelo y repo vendorizado.
# Están en `.gitignore`, no las escribimos nosotros, y recorrerlas haría que el
# test crawlee miles de archivos ajenos.
_NO_ES_CODIGO_NUESTRO = ("kronos_env", "Kronos", "pesos", "__pycache__",
                         ".venv", "node_modules")


def _fuentes():
    for base in CARPETAS_VIGILADAS:
        raiz = os.path.join(REPO, base)
        if not os.path.isdir(raiz):
            continue
        for root, dirs, files in os.walk(raiz):
            dirs[:] = [d for d in dirs if d not in _NO_ES_CODIGO_NUESTRO]
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(root, f)
                    yield os.path.relpath(p, REPO), io.open(p, encoding="utf-8").read()


def test_nadie_lee_el_manifiesto_por_fuera_de_la_puerta():
    """Si aparece un consumidor nuevo del manifiesto, este test lo caza.

    No alcanza con que el archivo nuevo filtre bien: tiene que usar la puerta.
    Un filtro propio es exactamente el patrón que fallo -- cada estudio con su
    copia de la regla, y el que se olvida no se entera.
    """
    infractores = []
    for rel, src in _fuentes():
        if rel.replace("/", os.sep) in EXENTOS:
            continue
        if "manifiesto_universo" not in src and "manifiesto" not in src:
            continue
        # lee el manifiesto: tiene que ser a traves de la puerta
        lee = re.search(r"json\.load\s*\(\s*open\s*\([^)]*manifiesto", src) or \
            re.search(r"manifiesto_universo\.json", src)
        if lee and "cargar_dias_de_estudio" not in src:
            infractores.append(rel)
    assert not infractores, (
        "estos archivos leen el manifiesto de dias sin pasar por "
        "`universo_estudio.cargar_dias_de_estudio`: %s. Filtrar por su cuenta "
        "es el patron que dejo entrar 10 dias del holdout el 2026-07-27."
        % infractores)


def _manifiesto_falso():
    return dict(dias=[
        dict(archivo="x.parquet", fecha="2026-06-30", tipo_de_dia="COMPLETO", n_ticks=1),
        dict(archivo="x.parquet", fecha="2026-07-01", tipo_de_dia="COMPLETO", n_ticks=1),
        dict(archivo="x.parquet", fecha="2026-07-15", tipo_de_dia="COMPLETO", n_ticks=1),
        dict(archivo="x.parquet", fecha="2026-06-19", tipo_de_dia="APERTURA_SEMANAL", n_ticks=1),
    ])


def test_por_defecto_el_holdout_no_sale_nunca():
    dias, info = U.cargar_dias_de_estudio(_manifiesto_falso())
    assert all(d["fecha"] < "2026-07-01" for d in dias)
    assert info["descartados_holdout"] == 2
    assert info["fechas_holdout"] == ["2026-07-01", "2026-07-15"]


def test_el_primer_dia_del_holdout_esta_ADENTRO_del_sello():
    """Borde: 2026-07-01 pertenece al holdout, no es el ultimo dia libre."""
    dias, _ = U.cargar_dias_de_estudio(_manifiesto_falso())
    assert "2026-07-01" not in {d["fecha"] for d in dias}


def test_incluir_holdout_sin_purpose_levanta():
    with pytest.raises(U.UniversoError) as e:
        U.cargar_dias_de_estudio(_manifiesto_falso(), incluir_holdout=True)
    assert "purpose" in str(e.value)


def test_alcance_por_tipo_de_dia_se_respeta():
    dias, _ = U.cargar_dias_de_estudio(_manifiesto_falso(),
                                       tipos_de_dia=["COMPLETO"])
    assert {d["tipo_de_dia"] for d in dias} == {"COMPLETO"}


def test_manifiesto_viejo_sin_tipo_de_dia_es_fail_closed():
    """Sin `tipo_de_dia` no se puede acotar el alcance; correr igual seria
    meter domingos en un nulo que no los declara."""
    m = dict(dias=[dict(archivo="x", fecha="2026-06-30", n_ticks=1)])
    with pytest.raises(U.UniversoError):
        U.cargar_dias_de_estudio(m, tipos_de_dia=["COMPLETO"])


def test_los_atlas_reales_no_devuelven_holdout():
    """Contra el manifiesto REAL del repo, no uno sintetico."""
    p = os.path.join(REPO, "runs", "censo", "manifiesto_universo.json")
    if not os.path.exists(p):
        pytest.skip("sin censo generado en este entorno")
    dias, info = U.cargar_dias_de_estudio(p, tipos_de_dia=["COMPLETO", "CIERRE_SEMANAL"])
    assert dias, "el manifiesto real quedo vacio tras filtrar: revisar"
    assert all(d["fecha"] < "2026-07-01" for d in dias)
    assert info["descartados_holdout"] >= 1, (
        "el manifiesto real deberia contener dias de holdout que la puerta "
        "descarta; si no los tiene, este test dejo de probar lo que dice")
