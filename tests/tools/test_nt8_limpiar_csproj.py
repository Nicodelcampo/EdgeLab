r"""El .csproj de NT8 no puede compilar sus propios artefactos de build.

NT8 arma la lista de fuentes por glob y se lleva los `obj\Debug\<idioma>\*.resources.cs`
que genera MSBuild. Son ocho y cada uno declara los mismos atributos de assembly, asi
que el compilador tira CS0579 y no compila NADA -- ningun indicador puede arreglarlo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.nt8_limpiar_csproj import limpiar  # noqa: E402

BS = chr(92)


def _proj(includes_obj=1, con_remove=False):
    ls = ["<Project>", "  <ItemGroup>",
          '    <Compile Include="Indicators' + BS + 'Foo.cs" />']
    for idioma in ["de-DE", "es-ES", "fr-FR"][:includes_obj]:
        ls.append('    <Compile Include="obj' + BS + 'Debug' + BS + idioma
                  + BS + 'NinjaTrader.Custom.resources.cs" />')
    ls += ["  </ItemGroup>", "  <ItemGroup>"]
    if con_remove:
        ls.append('    <Compile Remove="obj' + BS + '**" />')
    ls += ['    <None Remove="obj' + BS + '**" />',
           '    <Page Remove="obj' + BS + '**" />',
           "  </ItemGroup>", "</Project>", ""]
    return "\n".join(ls)


def test_saca_los_includes_de_obj_y_no_toca_las_fuentes_reales():
    nuevo, sacados, agrego = limpiar(_proj(includes_obj=3))
    assert sacados == 3
    assert agrego is True
    assert 'Include="obj' not in nuevo
    assert 'Include="Indicators' + BS + 'Foo.cs"' in nuevo


def test_agrega_el_Compile_Remove_que_faltaba():
    nuevo, _, _ = limpiar(_proj())
    assert nuevo.count('<Compile Remove="obj' + BS + '**" />') == 1
    # los otros dos Remove ya existian y siguen ahi
    assert '<None Remove="obj' + BS + '**" />' in nuevo
    assert '<Page Remove="obj' + BS + '**" />' in nuevo


def test_es_idempotente():
    """NT8 regenera el proyecto: la herramienta se corre muchas veces."""
    una, _, _ = limpiar(_proj(includes_obj=3))
    dos, sacados, agrego = limpiar(una)
    assert dos == una
    assert sacados == 0 and agrego is False


def test_un_proyecto_sano_no_se_toca():
    sano = _proj(includes_obj=0, con_remove=True)
    nuevo, sacados, agrego = limpiar(sano)
    assert nuevo == sano and sacados == 0 and agrego is False


def test_sin_ancla_lo_agrega_igual_antes_del_cierre():
    """Si NT8 saca tambien los Remove de None/Page, no hay donde anclar."""
    crudo = ("<Project>\n  <ItemGroup>\n"
             '    <Compile Include="obj' + BS + 'Debug' + BS + 'x.resources.cs" />\n'
             "  </ItemGroup>\n</Project>\n")
    nuevo, sacados, agrego = limpiar(crudo)
    assert sacados == 1 and agrego is True
    assert nuevo.count('<Compile Remove="obj' + BS + '**" />') == 1
    assert nuevo.rstrip().endswith("</Project>")


def test_preserva_fin_de_linea_windows():
    nuevo, _, _ = limpiar(_proj(includes_obj=2).replace("\n", "\r\n"))
    assert "\r\n" in nuevo
    assert "\n\n" not in nuevo.replace("\r\n", "\n\n").replace("\n\n", "\r\n")
