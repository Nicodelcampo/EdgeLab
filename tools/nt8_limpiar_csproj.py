#!/usr/bin/env python3
r"""Saca del proyecto de NinjaTrader los artefactos de build que compila como fuente.

## El sintoma

Al compilar, NT8 tira decenas de `CS0579 Duplicate
'System.Reflection.AssemblyCompanyAttribute' attribute` sobre
`NinjaTrader\Custom\resources.cs`, con las lineas 13 a 20 repetidas en bloques.

## La causa

`NinjaTrader.Custom.csproj` arma su lista de fuentes por glob y se lleva puestos los
`obj\Debug\<idioma>\NinjaTrader.Custom.resources.cs` que genera MSBuild para las
assemblies satelite. Son ocho, uno por idioma, y **cada uno declara los mismos atributos
de assembly**. El proyecto ya excluia `obj\**` de `None` y de `Page`, pero no de
`Compile`: faltaba una linea.

No es codigo del usuario. Ningun indicador puede causarlo ni arreglarlo.

## Lo que hace

1. Borra todo `<Compile Include="obj\...">`.
2. Agrega `<Compile Remove="obj\**" />` junto a los otros dos `Remove`, para que no
   vuelvan si NT8 regenera el proyecto.
3. Renombra a `.apartado` los `.resources.cs` que quedaron bajo `obj\`, para que un
   rescaneo de NT8 no los pueda encontrar. Los dos pasos hacen falta: el `Remove` se
   pierde si NT8 reescribe el proyecto, y los archivos vuelven si MSBuild los
   regenera. Renombra en vez de borrar: es reversible y son artefactos regenerables.

Es idempotente: correrlo dos veces no cambia nada la segunda. Deja respaldo la primera
vez. Si NT8 reescribe el `.csproj` y el error vuelve, se corre de nuevo.
"""
from __future__ import annotations

import argparse
import pathlib
import re

BS = chr(92)
GLOB = "obj" + BS + "**"
DEFECTO = pathlib.Path.home() / "Documents" / "NinjaTrader 8" / "bin" / "Custom"


def limpiar(texto):
    """Devuelve (texto nuevo, includes sacados, si agrego el Remove)."""
    nl = "\r\n" if "\r\n" in texto else "\n"
    patron = (r'[ \t]*<Compile Include="obj' + re.escape(BS)
              + r'[^"]*"[ ]*/>[ \t]*\r?\n')
    nuevo, sacados = re.subn(patron, "", texto)

    remove = '<Compile Remove="' + GLOB + '" />'
    agrego = False
    if remove not in nuevo:
        ancla = '    <None Remove="' + GLOB + '" />'
        if ancla in nuevo:
            nuevo = nuevo.replace(ancla, "    " + remove + nl + ancla, 1)
            agrego = True
        elif "</Project>" in nuevo:
            bloque = ("  <ItemGroup>" + nl + "    " + remove + nl
                      + "  </ItemGroup>" + nl + "</Project>")
            nuevo = nuevo.replace("</Project>", bloque, 1)
            agrego = True
    return nuevo, sacados, agrego


def apartar_generados(custom):
    """Renombra los `.resources.cs` generados bajo `obj/` para que el escaneo no los vea.

    La carpeta `obj/` suele estar tomada por NinjaTrader mientras corre, pero los
    archivos de adentro se renombran igual.
    """
    obj = pathlib.Path(custom) / "obj"
    apartados, bloqueados = [], []
    if not obj.exists():
        return apartados, bloqueados
    for f in sorted(obj.rglob("*.resources.cs")):
        try:
            f.rename(f.with_suffix(f.suffix + ".apartado"))
            apartados.append(f)
        except OSError as e:
            bloqueados.append((f, e))
    return apartados, bloqueados


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--custom", default=str(DEFECTO),
                    help="carpeta bin/Custom de NinjaTrader 8")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    proj = pathlib.Path(a.custom) / "NinjaTrader.Custom.csproj"
    if not proj.exists():
        print("no existe:", proj)
        return 1

    crudo = proj.read_bytes()
    enc = "utf-8-sig" if crudo.startswith(b"\xef\xbb\xbf") else "utf-8"
    texto = crudo.decode(enc)
    nuevo, sacados, agrego = limpiar(texto)

    obj = pathlib.Path(a.custom) / "obj"
    pendientes = sorted(obj.rglob("*.resources.cs")) if obj.exists() else []

    if nuevo == texto and not pendientes:
        print("ya estaba limpio:", proj)
        return 0

    if nuevo != texto:
        print("includes de obj sacados: %d | Compile Remove agregado: %s"
              % (sacados, "si" if agrego else "ya estaba"))
    if pendientes:
        print("generados bajo obj/ a apartar: %d" % len(pendientes))

    if a.dry_run:
        print("(dry-run, no se escribio)")
        return 0

    if nuevo != texto:
        resp = proj.with_suffix(proj.suffix + ".bak")
        if not resp.exists():
            resp.write_bytes(crudo)
            print("respaldo:", resp)
        proj.write_bytes(nuevo.encode(enc))
        print("escrito:", proj)

    apartados, bloqueados = apartar_generados(a.custom)
    if apartados:
        print("apartados: %d generados bajo obj/" % len(apartados))
    for f, e in bloqueados:
        print("BLOQUEADO (cerrar NinjaTrader y reintentar): %s -- %s" % (f.name, e))
    if bloqueados:
        return 1

    print("Ahora compilar en NT8 (F5).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
