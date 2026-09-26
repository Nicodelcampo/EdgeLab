#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T6 — gate REAL de compilación de un NinjaScript. Sin abrir NinjaTrader.

## Por qué existe

`BigTrap2.cs` **v2.3 no compilaba**: tenía `if (!ok) { }` con `ok` sin declarar
(CS0103). Sobrevivió al pin, a la suite y a tres capas de auditoría por una razón
sola: **el pin compara `sha256`, y un archivo que no compila tiene un hash
perfectamente válido.** Ninguna verificación del repo ejercitaba el compilador.

Y el sucesor —v2.4, con las reparaciones de H1 y H2— **tampoco lo compiló
nadie**. Se verificó por regex, que es un precheck, no un veredicto.

> `test_H1_el_cs_no_tiene_identificadores_sin_declarar` busca el token `ok`.
> Detecta el defecto **conocido**. No detectaría otro `CS0103`, una API
> incompatible, una referencia faltante ni un error de sintaxis.

## Qué hace, y qué NO

Compila con **`csc.exe` de .NET Framework** contra los **assemblies reales de la
instalación de NinjaTrader 8**, resueltos desde `NinjaTrader.Custom.csproj` — el
mismo proyecto que NT8 usa para compilar los indicadores del usuario. Escribe
sólo en un directorio temporal: **no toca la instalación, no copia a
`Indicators\`, no abre NT8**.

**Lo que NO demuestra:** que NT8 lo cargue en runtime, que la lógica sea
correcta, ni que la paridad se sostenga. Demuestra **una** cosa —que el código es
válido para el compilador que gobierna NinjaScript— y esa cosa es precondición
de todas las demás.

## Control negativo, obligatorio

Un gate que sólo sabe decir «sí» no sirve. En cada corrida se compila **además**
una copia **mutada** del fuente que debe fallar. Si la copia mutada compila, el
gate está roto y se reporta `INSTRUMENTO_ROTO`, no `COMPILA`.

**La mutación se hace sobre una copia en el temporal.** El `.cs` canónico no se
toca; se verifica su `sha256` antes y después.

## Salida

JSON content-addressed con: versión del compilador, `sha256` del fuente, lista
de referencias resueltas, exit code, stdout y stderr **completos**, y el
veredicto. Se cita en el preflight; no se redacta a mano.

Uso:
    python tools/compilar_nt8_cs.py nt8/BigTrap2.cs [--out runs/pred004/compila.json]

Exit: 0 = COMPILA · 1 = NO_COMPILA · 2 = ABSTAIN (no se pudo evaluar) ·
      3 = INSTRUMENTO_ROTO (el control negativo compiló)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CSC_CANDIDATOS = (
    r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe",
)
NT8_BIN = Path(os.environ.get("NT8_BIN", r"C:\Program Files\NinjaTrader 8\bin"))
#: `Documents` no es universal: con OneDrive y Windows en español la carpeta real
#: es `OneDrive\Documentos`, y ahí vive el csproj. Cableado, el gate ABSTAIN-eaba
#: en esta máquina — correcto, pero inservible. Se sobreescribe con NT8_CUSTOM,
#: simétrico a NT8_BIN, en vez de asumir una convención de carpetas.
NT8_CUSTOM = Path(os.path.expandvars(os.environ.get(
    "NT8_CUSTOM", r"%USERPROFILE%\Documents\NinjaTrader 8\bin\Custom")))
CSPROJ = NT8_CUSTOM / "NinjaTrader.Custom.csproj"
#: Reference assemblies del framework que el csproj declara (`net48`). csc no
#: las encuentra solo: WindowsBase/PresentationCore/PresentationFramework viven
#: aca, no en el directorio del compilador.
def _descubrir_refasm():
    """Directorio de reference assemblies del framework, descubierto.

    `WindowsBase` / `PresentationCore` / `PresentationFramework` no viven en el
    directorio de `csc.exe`: estan en los reference assemblies. Se busca la
    version mas alta que realmente los tenga, en vez de escribir la ruta -que
    ademas ataba el gate a una version puntual de .NET-.
    """
    base = (Path(r"C:\Program Files (x86)\Reference Assemblies\Microsoft"
                 r"\Framework") / ".NETFramework")
    if base.exists():
        for d in sorted((x for x in base.iterdir() if x.is_dir()),
                        key=lambda x: x.name, reverse=True):
            if (d / "WindowsBase.dll").exists():
                return d
    alt = Path(r"C:\Windows\Microsoft.NET\Framework64") / "v4.0.30319" / "WPF"
    return alt if alt.exists() else base


REFASM = Path(os.environ["NT8_REFASM"]) if os.environ.get("NT8_REFASM") \
    else _descubrir_refasm()

#: Errores de ENTORNO, no de codigo. Reportarlos como NO_COMPILA seria decir
#: "tu codigo esta roto" cuando la verdad es "no pude verificarlo", que es
#: justamente el modo de falla que este expediente persigue.
#: CS0006 metadata file no encontrado · CS0009/CS0518 referencia invalida o
#: tipo base ausente · CS1703 assembly duplicado · CS0433 tipo duplicado en DLLs.
ERRORES_DE_ENTORNO = ("CS0006", "CS0009", "CS0433", "CS0518", "CS1703", "CS1704")

#: La mutación del control negativo. Reproduce **el defecto real de v2.3**: un
#: identificador sin declarar. No un error de sintaxis trivial — el gate tiene
#: que atrapar la clase de defecto que ya se le escapó una vez.
MUTACION = ("\n\t\tprivate void __ControlNegativoT6__()\n"
            "\t\t{\n\t\t\tif (!__identificador_inexistente__) { }\n\t\t}\n")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def buscar_csc():
    for c in CSC_CANDIDATOS:
        if Path(c).exists():
            return c
    return None


def referencias():
    """Resuelve las referencias del csproj de NT8 contra los DLL reales.

    Se leen del proyecto que **NT8 usa para compilar los indicadores del
    usuario**: inventar la lista a mano sería compilar contra otro entorno y
    llamarlo equivalencia.
    """
    if not CSPROJ.exists():
        return None, "no existe %s" % CSPROJ
    txt = CSPROJ.read_text(encoding="utf-8", errors="replace")
    nombres = re.findall(r'<Reference Include="([^",]+)"', txt)
    resueltas, faltantes = [], []
    for n in nombres:
        for base in (NT8_CUSTOM, NT8_BIN, REFASM):
            cand = base / (n + ".dll")
            if cand.exists():
                resueltas.append(str(cand))
                break
        else:
            faltantes.append(n)          # del GAC / framework: csc las encuentra
    return dict(resueltas=resueltas, del_framework=faltantes), None


def compilar(fuente, refs, csc, tmp, etiqueta):
    salida = Path(tmp) / ("%s.dll" % etiqueta)
    # /noconfig: sin esto csc auto-referencia los assemblies de SU directorio
    # via csc.rsp, y chocan con los reference assemblies de net48 que declara el
    # csproj -CS1703, misma identidad importada dos veces-. Con /noconfig las
    # referencias son EXACTAMENTE las que el proyecto de NT8 declara, que es lo
    # que hace al gate equivalente y no aproximado.
    # /nostdlib+: csc agrega SU mscorlib pase lo que pase, y el csproj declara el
    # de net48. Sin esto queda un CS1703 residual solo por mscorlib.
    cmd = [csc, "/nologo", "/noconfig", "/nostdlib+", "/target:library", "/nowarn:1701,1702",
           "/out:%s" % salida]
    cmd += ["/reference:%s" % r for r in refs["resueltas"]]
    for n in refs["del_framework"]:
        r = REFASM / (n + ".dll")
        cmd.append("/reference:%s" % (r if r.exists() else (n + ".dll")))
    cmd.append(str(fuente))
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    # el parser buscaba ": error ", pero csc emite `error CS0006: ...` al
    # principio de linea cuando el error no es de un archivo concreto. Se
    # perdian TODOS los errores de entorno: n_errores=0 con exit_code=1.
    errores = [l for l in (p.stdout or "").splitlines() if re.search(r"error CS\d+", l)]
    de_entorno = [l for l in errores if any(c in l for c in ERRORES_DE_ENTORNO)]
    return dict(exit_code=p.returncode, n_errores=len(errores),
                n_errores_de_entorno=len(de_entorno),
                errores=errores[:40],
                stdout=(p.stdout or "")[-8000:], stderr=(p.stderr or "")[-4000:])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fuente")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    fuente = Path(a.fuente)
    if not fuente.is_absolute():
        fuente = REPO / fuente
    res = dict(schema_version="compilacion_nt8_v1", fuente=str(fuente))

    def emitir(estado, motivo=None, code=2, **extra):
        res.update(estado=estado, motivo=motivo, **extra)
        res["resultado_sha256"] = hashlib.sha256(
            json.dumps(res, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        txt = json.dumps(res, indent=1, ensure_ascii=False)
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(txt, encoding="utf-8")
        print(txt if not a.out else txt[:1500])
        print("\n==> %s%s" % (estado, "  (%s)" % motivo if motivo else ""))
        return code

    if not fuente.exists():
        return emitir("ABSTAIN", "el fuente no existe")
    sha_antes = sha256(fuente)
    res["sha256_fuente"] = sha_antes
    m = re.search(r"version=([0-9.]+)", fuente.read_text(encoding="utf-8", errors="replace"))
    res["version_declarada"] = m.group(1) if m else None

    csc = buscar_csc()
    if not csc:
        return emitir("ABSTAIN", "no se encontro csc.exe de .NET Framework")
    res["csc"] = csc
    v = subprocess.run([csc, "/version"], capture_output=True, text=True)
    res["csc_version"] = (v.stdout or v.stderr or "").strip()[:120]

    refs, err = referencias()
    if err:
        return emitir("ABSTAIN", err)
    res["referencias_resueltas"] = len(refs["resueltas"])
    res["referencias_del_framework"] = refs["del_framework"]
    if not refs["resueltas"]:
        return emitir("ABSTAIN", "ninguna referencia de NT8 resuelta: entorno incompleto")

    with tempfile.TemporaryDirectory(prefix="t6_") as tmp:
        copia = Path(tmp) / fuente.name
        shutil.copy2(fuente, copia)
        res["real"] = compilar(copia, refs, csc, tmp, "real")

        # --- CONTROL NEGATIVO: la copia mutada DEBE fallar ---
        mutado = Path(tmp) / ("MUTADO_" + fuente.name)
        src = copia.read_text(encoding="utf-8", errors="replace")
        i = src.rfind("\t}\n}")            # antes de cerrar clase y namespace
        mutado.write_text(src[:i] + MUTACION + src[i:], encoding="utf-8")
        res["control_negativo"] = compilar(mutado, refs, csc, tmp, "mutado")

    if sha256(fuente) != sha_antes:
        return emitir("ABSTAIN", "el fuente canonico CAMBIO durante la corrida",
                      code=2)
    res["fuente_intacto"] = True

    # ENTORNO antes que CODIGO: si no se pudo resolver una referencia, no se
    # esta midiendo el codigo. ABSTAIN, nunca NO_COMPILA.
    if res["real"]["n_errores_de_entorno"]:
        return emitir("ABSTAIN",
                      "errores de ENTORNO, no de codigo (%s): no se pudo evaluar"
                      % ", ".join(sorted({c for c in ERRORES_DE_ENTORNO
                                          for l in res["real"]["errores"] if c in l})),
                      code=2)
    if res["control_negativo"]["exit_code"] == 0:
        return emitir("INSTRUMENTO_ROTO",
                      "la copia mutada COMPILO: el gate no detecta el defecto "
                      "que ya se escapo una vez", code=3)
    if res["real"]["exit_code"] != 0:
        return emitir("NO_COMPILA", "%d error(es)" % res["real"]["n_errores"], code=1)
    return emitir("COMPILA", None, code=0)


if __name__ == "__main__":
    sys.exit(main())
