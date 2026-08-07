# -*- coding: utf-8 -*-
"""Pruebas de FALLA INTENCIONAL del gate de identidad de la sonda.

## Por qué existen

El gate de procedencia de `sonda_alejamiento_cero.py` falló **tres veces al
primer uso real y ninguna a la lectura**:

1. miraba `diag/` entera y **se bloqueaba con su propia salida**;
2. quedó leyendo un campo que ya no existía → `KeyError` antes de medir;
3. comparaba conjuntos de dependencias de punta a punta y **abortaba siempre**,
   porque `sys.modules` crece durante la corrida.

Las tres las atrapó ejecutar el código. Un gate que nadie prueba fallando es un
gate del que sólo se sabe que no molesta.

Estas pruebas fijan las cinco condiciones en la dirección que importa: que el
gate **diga que no** cuando corresponde, y que **no moleste** cuando no.
"""
from __future__ import annotations

import io
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

S = pytest.importorskip("diag.tasa_senales.sonda_alejamiento_cero",
                        reason="la sonda necesita el entorno del bridge")
C = pytest.importorskip("diag.tasa_senales.comparar_sondas")


# ------------------------------------------------------------------ 1
def test_dependencia_congelada_MODIFICADA_se_detecta(tmp_path):
    """Es el caso que motiva todo: los bytes cambiaron entre el prehash y el
    cierre, o sea que el hash publicado no cubre lo que se ejecutó."""
    f = tmp_path / "dep.py"
    f.write_text("x = 1\n", encoding="utf-8")
    ident = "otro:" + f.as_posix()

    antes, faltan = S.prehashear({"dependencias": [ident]})
    assert not faltan and ident in antes

    f.write_text("x = 2\n", encoding="utf-8")          # cambia durante la corrida
    despues, _ = S.prehashear({"dependencias": [ident]})

    movidos = S.hashes_que_cambiaron(antes, despues)
    assert [m[0] for m in movidos] == [ident], \
        "una dependencia congelada cambio y el gate no lo vio"


# ------------------------------------------------------------------ 2
def test_dependencia_NUEVA_invalida_la_corrida(tmp_path):
    """`new_unfrozen_dependency_files == []` es la regla canónica: todo archivo
    usado tiene que haber estado identificado y hasheado ANTES de medir."""
    congeladas = ["repo:diag/tasa_senales/sonda_alejamiento_cero.py",
                  "venv:Lib/site-packages/numpy/__init__.py"]
    observadas = congeladas + ["stdlib:Lib/statistics.py"]

    nuevas = S.dependencias_no_congeladas(observadas, congeladas)
    assert nuevas == ["stdlib:Lib/statistics.py"]

    # y el caso que NO debe disparar: importar tarde algo YA congelado
    assert S.dependencias_no_congeladas(congeladas, congeladas) == [], \
        "un modulo prehasheado importado mas tarde NO invalida la corrida"


# ------------------------------------------------------------------ 3
def test_un_OUTPUT_modificado_NO_bloquea():
    """La contracara. Un artefacto generado sin commitear no puede cambiar un
    número — y el gate que miraba `diag/` entera se bloqueaba con su propia
    salida, que es cómo se descubrió."""
    salidas = S.salidas_generadas()
    if not salidas:
        pytest.skip("no hay artefactos de la sonda en disco todavia")
    dep_repo, _inputs, _ent, _mods = S.conjunto_de_dependencias(
        "6E_09-26_ticks.parquet")
    assert not (salidas & set(
        r.replace("repo:", "") for r in dep_repo)), \
        "una salida de la sonda entro al conjunto de dependencias"

    est = S.estado_del_worktree(dep_repo)
    for r in est["ignored_generated_outputs"]:
        assert r not in est["dependency_set_dirty_start"], \
            "una salida generada esta bloqueando el gate"


# ------------------------------------------------------------------ 4
def test_ruta_del_manifiesto_INEXISTENTE_aborta():
    """El conjunto congelado dejó de ser alcanzable: la corrida no sería la
    misma, así que no se publica."""
    hashes, faltan = S.prehashear(
        {"dependencias": ["repo:no/existe/este/archivo.py"]})
    assert faltan == ["repo:no/existe/este/archivo.py"]
    assert hashes == {}


# ------------------------------------------------------------------ 5
def test_sidecar_AUSENTE_invalida_el_artefacto(tmp_path):
    """Un JSON cuyo sidecar falte o no coincida es inválido como evidencia, sin
    ambigüedad: si el proceso cae entre los dos `os.replace`, el consumidor no
    puede distinguir un artefacto completo de uno a medias."""
    import hashlib
    p = tmp_path / "art.json"
    cuerpo = {"schema_version": "x", "por_indicador": {}}
    cuerpo["payload_sha256"] = hashlib.sha256(
        json.dumps(cuerpo, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    p.write_text(json.dumps(cuerpo), encoding="utf-8")

    fallos = C.verificar_integridad(str(p), cuerpo, "A")
    assert any("sidecar" in f for f in fallos), "sin sidecar deberia ser invalido"

    # con sidecar CORRECTO, no hay queja
    side = tmp_path / "art.json.sha256"
    side.write_text("%s  %s\n" % (hashlib.sha256(p.read_bytes()).hexdigest(),
                                  p.name), encoding="utf-8")
    assert C.verificar_integridad(str(p), cuerpo, "A") == []

    # con sidecar QUE NO COINCIDE, tambien invalido
    side.write_text("%s  %s\n" % ("0" * 64, p.name), encoding="utf-8")
    assert any("sidecar" in f for f in C.verificar_integridad(str(p), cuerpo, "A"))


# ------------------------------------------------------------------ extras
def test_los_ambitos_son_relativos_y_reversibles():
    """Un manifiesto con rutas absolutas no sirve en otra máquina y convierte
    una diferencia de entorno en un falso positivo de código."""
    import numpy
    import pathlib
    for f in (S.__file__, numpy.__file__):
        ambito, ident = S._ident(f)
        assert ambito in ("repo", "venv", "stdlib", "otro")
        assert ":" in ident
        if ambito != "otro":
            assert not ident.split(":", 1)[1].startswith(("/", "\\")), ident
            assert ":" not in ident.split(":", 1)[1], "quedo una unidad de Windows"
        assert pathlib.Path(S._resolver(ident)).resolve() == pathlib.Path(f).resolve()


def test_venv_tiene_precedencia_sobre_repo():
    """`.venv` vive DENTRO del repo: sin precedencia determinista, site-packages
    se clasificaria como codigo del proyecto y un cambio de pandas se leeria
    como un cambio de codigo."""
    import numpy
    ambito, ident = S._ident(numpy.__file__)
    assert ambito == "venv" and ident.startswith("venv:"), ident


#: Las limitaciones que la implementación **de esta versión** declara no cubrir.
#: Se fija la lista, no su no-vacuidad: si una versión futura captura alguna
#: —por ejemplo, enumerando las `.dll` transitivas con una herramienta del
#: sistema— el test debe **obligar a actualizar esta constante**, no a conservar
#: la limitación artificialmente. «Nunca esté vacía» sería un invariante
#: universal que no se sostiene y que premiaría no mejorar el método.
SUPERFICIE_ESPERADA_V1 = {
    "librerias nativas transitivas", "modulos built-in y frozen",
    "el binario del interprete", "variables de entorno", "configuracion externa",
}


def test_la_superficie_no_cubierta_declara_su_alcance():
    """Presencia, tipo y **la lista de esta versión** — no la no-vacuidad."""
    sup = getattr(S, "SUPERFICIE_NO_CUBIERTA", None)
    assert sup is not None, "el campo tiene que existir aunque quede vacio"
    assert isinstance(sup, list) and all(isinstance(x, str) for x in sup)

    faltan = [e for e in SUPERFICIE_ESPERADA_V1
              if not any(e in x for x in sup)]
    sobran = [x for x in sup
              if not any(e in x for e in SUPERFICIE_ESPERADA_V1)]
    assert not faltan and not sobran, (
        "la superficie declarada dejo de coincidir con la de esta version.\n"
        "  sin declarar: %s\n  no esperadas: %s\n"
        "Si el metodo mejoro y ahora cubre alguna, ACTUALIZAR "
        "SUPERFICIE_ESPERADA_V1; no conservar la limitacion para que pase."
        % (faltan, sobran))


#: El subproceso instala un audit hook ANTES de importar la sonda. Esa es la
#: parte que un listado de directorio no puede dar: ve cada `open` con su modo,
#: los borrados y los renombres, aunque el archivo se cree y se borre dentro del
#: mismo import.
#:
#: `__pycache__` se excluye a propósito: escribir un `.pyc` es un efecto
#: LEGÍTIMO del import machinery, y contarlo como mutación de outputs sería un
#: falso positivo que enseñaría a ignorar el test.
_SONDA_IMPORT_PROBE = r'''
import json, sys
REPO = %r
sys.path.insert(0, REPO)
viol = []

def _norm(p):
    return str(p).replace("\\", "/").lower()

def hook(event, args):
    try:
        if event == "open":
            p, modo = _norm(args[0]), (args[1] or "")
            if "__pycache__" in p:
                return
            if "/data/nt8/" in p or "manifiesto_universo" in p:
                viol.append(["LEE INPUT DE MEDICION", str(args[0]), modo])
            elif ("/diag/tasa_senales/" in p
                  and any(c in modo for c in "wax+")):
                viol.append(["ESCRIBE OUTPUT", str(args[0]), modo])
        elif event in ("os.remove", "os.unlink", "os.rename", "os.replace",
                       "shutil.move", "shutil.copyfile"):
            for a in args:
                p = _norm(a)
                if "__pycache__" in p:
                    continue
                if "/diag/tasa_senales/" in p or "/data/nt8/" in p:
                    viol.append([event.upper(), str(a), ""])
    except Exception:
        pass

sys.addaudithook(hook)
import diag.tasa_senales.sonda_alejamiento_cero as s
import inspect
guard = "if __name__ ==" in inspect.getsource(s)
print("__RESULTADO__" + json.dumps(
    {"viol": viol, "guard": guard, "tiene_main": hasattr(s, "main")}))
'''


def _hashes_del_directorio(d):
    """Contenido, no nombres ni mtimes. Un archivo reescrito con los mismos
    bytes es inocuo; uno reescrito con otros no, y el listado no los distingue."""
    import hashlib
    out = {}
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if not os.path.isfile(p) or "__pycache__" in p:
            continue
        with open(p, "rb") as fh:
            out[f] = hashlib.sha256(fh.read()).hexdigest()
    return out


def test_importar_la_sonda_no_toca_inputs_ni_muta_outputs():
    """`congelar_dependencias.py` **importa** la sonda para observar qué carga.

    Si ese import midiera algo, abriera el parquet o reescribiera un artefacto,
    el congelado estaría produciendo evidencia como efecto colateral —y peor,
    con un conjunto de dependencias que todavía no está congelado—.

    ## Qué se afirma exactamente, y qué NO

    **No** se afirma «importar no hace I/O»: el import legítimamente lee `.py`,
    `.pyc` y extensiones binarias, y eso es lo que se está inventariando. La
    condición correcta es más estrecha y más fuerte:

        sin acceso a inputs de medición
        y sin crear, modificar ni eliminar outputs

    ## Por qué no alcanza con listar el directorio

    Una versión anterior de esta prueba comparaba el listado y los `mtime` antes
    y después. **Ese listado queda igual** si el import lee el parquet, si
    modifica un JSON existente, si crea un archivo y lo borra, o si reescribe un
    sidecar con el mismo nombre. Se cambió por dos comprobaciones que sí lo ven:
    **hashes de contenido** y un **audit hook** que registra cada `open` con su
    modo, más borrados y renombres.
    """
    import subprocess
    salida = os.path.join(REPO, "diag", "tasa_senales")
    antes = _hashes_del_directorio(salida)

    r = subprocess.run([sys.executable, "-c", _SONDA_IMPORT_PROBE % REPO],
                       capture_output=True, text=True, timeout=600, cwd=REPO)
    assert r.returncode == 0, "importar la sonda fallo:\n%s" % r.stderr[-2000:]
    marca = "__RESULTADO__"
    assert marca in r.stdout, r.stdout[-2000:]
    res = json.loads(r.stdout.split(marca, 1)[1].splitlines()[0])

    assert not res["viol"], (
        "importar la sonda accedio a inputs de medicion o muto outputs:\n  %s"
        % "\n  ".join(" | ".join(v) for v in res["viol"]))
    assert res["guard"], "la sonda no tiene `if __name__ == ...`"
    assert res["tiene_main"], "la sonda no expone `main`"

    despues = _hashes_del_directorio(salida)
    nuevos = sorted(set(despues) - set(antes))
    faltantes = sorted(set(antes) - set(despues))
    mutados = sorted(f for f in set(antes) & set(despues)
                     if antes[f] != despues[f])
    assert not (nuevos or faltantes or mutados), (
        "el contenido del directorio de salida cambio: nuevos=%s faltantes=%s "
        "mutados=%s" % (nuevos, faltantes, mutados))
