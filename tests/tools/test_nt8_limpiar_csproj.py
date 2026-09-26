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


# --- apartar los .resources.cs generados ---

def test_aparta_los_generados_bajo_obj(tmp_path):
    """No alcanza con sacarlos del proyecto: si el archivo sigue ahi, NT8 lo vuelve
    a barrer la proxima vez que rehace la lista de fuentes."""
    from tools.nt8_limpiar_csproj import apartar_generados
    obj = tmp_path / "obj" / "Debug"
    for idioma in ("de-DE", "es-ES"):
        d = obj / idioma
        d.mkdir(parents=True)
        (d / "NinjaTrader.Custom.resources.cs").write_text("[assembly: X]", encoding="utf-8")
    (tmp_path / "Indicators").mkdir()
    real = tmp_path / "Indicators" / "Foo.cs"
    real.write_text("class Foo {}", encoding="utf-8")

    apartados, bloqueados = apartar_generados(tmp_path)
    assert len(apartados) == 2 and bloqueados == []
    assert list((tmp_path / "obj").rglob("*.resources.cs")) == []
    assert len(list((tmp_path / "obj").rglob("*.apartado"))) == 2
    # no toca ninguna fuente real
    assert real.exists() and real.read_text(encoding="utf-8") == "class Foo {}"


def test_apartar_es_idempotente_y_tolera_que_no_exista_obj(tmp_path):
    from tools.nt8_limpiar_csproj import apartar_generados
    assert apartar_generados(tmp_path) == ([], [])
    d = tmp_path / "obj" / "Debug" / "ru-RU"
    d.mkdir(parents=True)
    (d / "NinjaTrader.Custom.resources.cs").write_text("x", encoding="utf-8")
    assert len(apartar_generados(tmp_path)[0]) == 1
    assert apartar_generados(tmp_path) == ([], [])
