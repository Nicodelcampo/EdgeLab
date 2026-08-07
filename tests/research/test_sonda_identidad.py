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


def test_las_claves_de_identidad_coinciden_con_lo_que_el_comparador_declara():
    """El defecto que se repitio CUATRO veces en este archivo: renombrar un
    campo y dejar una referencia al nombre viejo. Las cuatro reventaron al
    primer uso real -KeyError despues de minutos de computo- y ninguna a la
    lectura, porque un `replace` de string que no matchea no avisa.

    Esto lo caza sin correr la sonda: se compara el conjunto de claves que
    `identidad_de_corrida` produce contra el que el comparador declara. Si
    alguien renombra en un lado y no en el otro, falla en 2 segundos.
    """
    ident = S.identidad_de_corrida("6E_09-26_ticks.parquet", ["2026-06-12"])
    declaradas = set(C.IDENTIDAD_DEBE_COINCIDIR) | set(C.IDENTIDAD_PUEDE_DIFERIR)

    # las que solo existen en modo canonico se agregan al terminar de medir
    solo_canonico = {"dependency_manifest_sha256", "frozen_dependencies_n",
                     "new_unfrozen_dependency_files", "modo",
                     "entorno_importado_durante_la_corrida",
                     "dependency_set_entorno_n_fin",
                     "dependency_set_entorno_sha256_fin"}
    producidas = set(ident) | solo_canonico

    sin_declarar = sorted(producidas - declaradas)
    declaradas_de_mas = sorted(declaradas - producidas)
    assert not sin_declarar and not declaradas_de_mas, (
        "el comparador y la sonda no hablan del mismo esquema.\n"
        "  produce y nadie declara: %s\n"
        "  declarado y no se produce: %s" % (sin_declarar, declaradas_de_mas))


def test_la_reverificacion_de_cierre_usa_una_constante_no_parsing_textual():
    """El test anterior era VACUO y por eso pasaba.

    Extraia el bloque con `src.split("movidos = [")[1].split("]")[0]`, y el
    primer `]` del fuente es el de `ident[k]` — no el cierre de la tupla. Asi
    que `campos` quedaba en `[]` y el assert no validaba nada. Un test vacuo es
    peor que ninguno: ocupa el lugar del que faltaba.

    Ahora la lista vive en una constante y se compara contra las claves reales.
    """
    ident = S.identidad_de_corrida("6E_09-26_ticks.parquet", ["2026-06-12"])
    assert S.CAMPOS_REVERIFICADOS, "la constante no puede estar vacia"
    faltan = [c for c in S.CAMPOS_REVERIFICADOS if c not in ident]
    assert not faltan, "la re-verificacion mira campos inexistentes: %s" % faltan

    import inspect
    src = inspect.getsource(S.main)
    assert "CAMPOS_REVERIFICADOS" in src, "main() dejo de usar la constante"
    assert 'for k in ("code_commit_start"' not in src, \
        "volvio la lista escrita a mano adentro de main()"


def test_una_dependencia_versionada_sucia_BLOQUEA(monkeypatch):
    """El defecto mas grave que encontro la auditoria: `git status` emite rutas
    DESNUDAS y el conjunto de dependencias usa `repo:`. Sin normalizar, la
    interseccion era SIEMPRE VACIA y `dependency_set_dirty_start` **nunca podia
    dispararse**. El gate estaba fail-open mientras el commit afirmaba
    "commit declarado = codigo que produjo el artefacto".

    Un gate que no puede fallar y un gate que pasa se ven identicos desde
    afuera. Por eso esto ensucia una dependencia REAL y exige que bloquee.
    """
    sucia = "diag/tasa_senales/sonda_alejamiento_cero.py"
    monkeypatch.setattr(S.subprocess, "run",
                        lambda *a, **k: type("R", (), {"stdout": " M %s\n" % sucia})())
    dep = {"repo:" + sucia: "abc", "repo:otro.py": "def"}
    est = S.estado_del_worktree(dep)
    assert est["dependency_set_dirty_start"] == [sucia], \
        "una dependencia versionada modificada NO bloqueo: %s" % est
    assert est["sin_clasificar"] == [], \
        "quedo clasificada como 'sin clasificar' en vez de bloquear"


def test_el_gate_cubre_los_INPUTS_versionados(monkeypatch):
    """El manifiesto de universo esta trackeado y DEFINE LA MUESTRA: modificarlo
    sin commitear cambia el numero igual que modificar codigo. La version
    anterior pasaba solo `dep_repo` al gate."""
    inp = "runs/censo/manifiesto_universo.json"
    monkeypatch.setattr(S.subprocess, "run",
                        lambda *a, **k: type("R", (), {"stdout": " M %s\n" % inp})())
    est = S.estado_del_worktree({"repo:" + inp: "abc"})
    assert est["dependency_set_dirty_start"] == [inp]


def test_una_dependencia_BORRADA_al_cierre_aborta():
    """`hashes_que_cambiaron` sólo mira `k in despues`: un archivo borrado
    durante la corrida quedaba fuera de las dos comprobaciones."""
    antes = {"repo:a.py": "h1", "repo:b.py": "h2"}
    despues = {"repo:a.py": "h1"}
    assert S.dependencias_desaparecidas(antes, despues) == ["repo:b.py"]
    assert S.hashes_que_cambiaron(antes, despues) == [], \
        "la desaparicion NO debe reportarse como cambio de hash: son dos cosas"
    assert S.dependencias_desaparecidas(antes, antes) == []


def test_la_publicacion_es_realmente_atomica(tmp_path):
    """El commit afirmaba promocion atomica y el codigo hacia `write_text`
    directo; `tempfile` estaba importado y no se usaba. Que un texto afirme una
    propiedad no se la da al codigo."""
    import inspect, hashlib
    src = inspect.getsource(S.publicar_atomico)
    assert "os.replace" in src and "NamedTemporaryFile" in src
    assert "dir=str(salida.parent)" in src, "el temporal tiene que ir al destino"

    main_src = inspect.getsource(S.main)
    assert "publicar_atomico" in main_src
    assert "salida.write_text" not in main_src, "volvio la escritura directa"

    j = tmp_path / "a.json"
    sc = tmp_path / "a.json.sha256"
    prev = "{\"viejo\": 1}\n"
    j.write_text(prev, encoding="utf-8")
    S.publicar_atomico(j, sc, "{\"nuevo\": 2}\n")
    assert j.read_text(encoding="utf-8") == "{\"nuevo\": 2}\n"
    assert sc.read_text(encoding="utf-8").split()[0] == \
        hashlib.sha256(j.read_bytes()).hexdigest()
    assert not list(tmp_path.glob("*.tmp*")), "quedaron temporales sin limpiar"


def test_el_comparador_EXIGE_canonico_y_cero_no_congeladas(tmp_path):
    """El comparador pedia que `modo` COINCIDIERA, no que fuera 'canonico': dos
    corridas de descubrimiento daban exit 0. Y `new_unfrozen_dependency_files`
    estaba en «pueden diferir», sin exigirse nunca vacio. O sea que su exit 0 NO
    probaba ninguna de las dos propiedades que el commit afirmaba."""
    base = {"identidad": {"modo": "canonico",
                          "new_unfrozen_dependency_files": [],
                          "dependency_manifest_sha256": "x"},
            "outcomes_accessed": False, "umbrales": [], "por_indicador": {}}
    assert not [f for f in C.validar_estructura(base, "A")
                if "modo" in f or "unfrozen" in f]

    d = json.loads(json.dumps(base)); d["identidad"]["modo"] = "descubrimiento"
    assert any("canonico" in f for f in C.validar_estructura(d, "A"))

    d = json.loads(json.dumps(base))
    d["identidad"]["new_unfrozen_dependency_files"] = ["stdlib:Lib/x.py"]
    assert any("unfrozen" in f for f in C.validar_estructura(d, "A"))

    d = json.loads(json.dumps(base))
    d["identidad"]["new_unfrozen_dependency_files"] = None
    assert any("unfrozen" in f for f in C.validar_estructura(d, "A"))
