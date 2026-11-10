#!/usr/bin/env python3
"""HFT-CLUSTERS-INFO: construir y lanzar los kernels (docs/research/hft_clusters_u1_20261110/PREREGISTRO_E0_E_INFORMACION.md).
  python tools/hft_clusters_info.py e0                     # paso sin retornos (4 activos, DESC)
  python tools/hft_clusters_info.py e0b                    # E0-b sin retornos: 40 definiciones (más zonas, ancho mínimo), equilibrio potencia/fricción
  python tools/hft_clusters_info.py e0b_otros              # E0-b sin retornos en RTY, 6E, 6B y MBT (regla mecánica de definición)
  python tools/hft_clusters_info.py ruptura_otros          # tabla de ruptura (generador) en esos activos + YM, SIN mirar desenlaces → banco
  python tools/hft_clusters_info.py ruptura_replica        # tabla de la confirmación de «no defiende» (abr → sep; sin desenlaces en el kernel)
  python tools/hft_clusters_info.py niveles_replica        # REBOTE_NIVEL_SESION: niveles de la sesión con zonas y clusters (abr → sep) → banco
  python tools/hft_clusters_info.py ruptura                # indagación de la ruptura en clusters grandes (DESC, exploratoria)
  python tools/hft_clusters_info.py ruptura_rep            # confirmación en la réplica abr → sep de las reglas que eligió la indagación
  python tools/hft_clusters_info.py contexto               # contexto de otros clusters (6 variables) sobre la definición elegida por regla
  python tools/hft_clusters_info.py rebotes                # 7 definiciones de rebote (D0–D6) con los clusters del E0-b en NQ y ES
  python tools/hft_clusters_info.py info                   # paso de información en DESC con la definición que eligió el E0
  python tools/hft_clusters_info.py rep                    # réplica abr → sep (sólo si el paso info pasó; una vez)
  python tools/hft_clusters_info.py traer e0|info|rep      # baja el resultado a la carpeta de la familia (y escribe RECOMENDACIONES_<modo>.md)
      [modulo=justificación]                               # si el resultado es NO VIGENTE y el diff de ese módulo se revisó y no toca el modo
  python tools/hft_clusters_info.py recomendar rebotes|contexto|info   # rehace las recomendaciones de un resultado ya bajado
Agregar --solo-construir para no lanzar. La definición del paso info sale de HFTC_e0.json (campo `eleccion`), nunca a mano.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools/kaggle_grilla"))
DIR = ROOT / "docs/research/hft_clusters_u1_20261110"
MODULOS = ["edgelab/holdout.py", "edgelab/research/fuentes_ticks.py", "edgelab/bridge/indicators/hftzones_nq.py",
           "edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py",
           "edgelab/research/hft_clusters_info.py", "edgelab/research/hft_rebotes.py", "edgelab/research/hft_contexto.py", "edgelab/research/hft_ruptura.py",
           "edgelab/research/niveles_sesion.py"]
DATASET = "nicolasbuttaro/edgelab-liquid-ticks-20261014"
OTROS = ("RTY", "6E", "6B", "MBT")                                     # activos con costo medido sin E0-b (6J y ZB: spread sin medir)
REPLICA_INST = ("NQ", "ES", "RTY", "YM")                                # confirmación de «el cluster grande no defiende» (CONFIRMACION_NO_DEFIENDE.md)
NIVELES_INST = ("NQ", "ES", "RTY", "YM", "GC")                          # REBOTE_NIVEL_SESION (PREREGISTRO_REBOTE_NIVEL.md)


def construir(modo: str) -> Path:
    from construir_kernel import construir as K
    src = (ROOT / "tools/kaggle_grilla/hft_clusters_info_main.py").read_text(encoding="utf-8").replace('MODO = "e0"', f'MODO = "{modo}"', 1)
    if modo == "contexto":                                             # misma base que rebotes + la definición elegida por regla
        from edgelab.research.hft_contexto import elegir_definicion
        d = elegir_definicion(json.loads((DIR / "HFTC_rebotes.json").read_text(encoding="utf-8")))
        src = src.replace('DEF_CONTEXTO = "D0_BASE"', f'DEF_CONTEXTO = "{d}"', 1); print("definición elegida para el contexto:", d)
    if modo == "ruptura_rep":                                          # reglas congeladas por la selección mecánica de la indagación
        sel = json.loads((DIR / "HFTC_ruptura.json").read_text(encoding="utf-8")).get("seleccion") or []
        if not sel: raise SystemExit("la indagación no seleccionó ninguna regla: no hay nada que confirmar")
        reglas = []
        for m in sel:                                                   # cortes de la indagación (DESC), por activo, sin recalcular en la réplica
            reglas.append(dict(rasgo=m["rasgo"], tercil=m["tercil"], cortes_por_activo=m["cortes_por_activo"]))
        src = src.replace("REGLAS_RUPTURA = []", "REGLAS_RUPTURA = " + json.dumps(reglas), 1); print("reglas congeladas:", reglas)
    if modo == "e0b_otros":                                            # E0-b sin retornos en los activos nuevos con costo medido
        src = src.replace('INSTRUMENTOS = ("NQ", "ES", "YM", "GC")', "INSTRUMENTOS = " + repr(OTROS), 1)
    if modo in ("ruptura_replica", "niveles_replica"):                 # réplica abr → sep: definiciones congeladas de los dos E0-b
        el = {i: ["Z_CERT", v["elegida"]["cluster"]] for f in ("HFTC_e0b.json", "HFTC_e0b_otros.json")
              for i, v in json.loads((DIR / f).read_text(encoding="utf-8"))["equilibrio"].items() if v.get("elegida")}
        inst = REPLICA_INST if modo == "ruptura_replica" else NIVELES_INST
        el = {i: d for i, d in el.items() if i in inst}
        src = src.replace('INSTRUMENTOS = ("NQ", "ES", "YM", "GC")', "INSTRUMENTOS = " + repr(tuple(inst)), 1)
        src = src.replace("DEFS = {}", "DEFS = " + json.dumps(el), 1); print("activos:", inst, "definiciones:", el)
    elif modo == "ruptura_otros":                                      # definición elegida por el E0-b de cada activo (YM: la del E0-b original)
        el = {i: ["Z_CERT", v["elegida"]["cluster"]] for i, v in json.loads((DIR / "HFTC_e0b_otros.json").read_text(encoding="utf-8"))["equilibrio"].items() if v.get("elegida")}
        ym = json.loads((DIR / "HFTC_e0b.json").read_text(encoding="utf-8"))["equilibrio"]["YM"]["elegida"]
        if ym: el["YM"] = ["Z_CERT", ym["cluster"]]
        if not el: raise SystemExit("ningún activo nuevo con definición elegible en el E0-b")
        src = src.replace('INSTRUMENTOS = ("NQ", "ES", "YM", "GC")', "INSTRUMENTOS = " + repr(tuple(sorted(el))), 1)
        src = src.replace("DEFS = {}", "DEFS = " + json.dumps(el), 1); print("definiciones:", el)
    elif modo in ("rebotes", "contexto", "ruptura", "ruptura_rep"):                                              # clusters del E0-b (equilibrio potencia/fricción); YM y GC fuera
        eq = json.loads((DIR / "HFTC_e0b.json").read_text(encoding="utf-8"))["equilibrio"]
        el = {i: ["Z_CERT", eq[i]["elegida"]["cluster"]] for i in ("NQ", "ES") if eq.get(i, {}).get("elegida")}
        src = src.replace("DEFS = {}", "DEFS = " + json.dumps(el), 1)
    elif modo not in ("e0", "e0b", "e0b_otros", "ruptura_replica", "niveles_replica"):
        el = json.loads((DIR / "HFTC_e0.json").read_text(encoding="utf-8"))["eleccion"]
        if not el: raise SystemExit("el E0 no eligió ninguna definición: el paso de información no se corre")
        src = src.replace("DEFS = {}", "DEFS = " + json.dumps({i: [v["zona"], v["cluster"]] for i, v in sorted(el.items())}), 1)
    tmp = ROOT / f"tools/kaggle_grilla/_hft_clusters_info_{modo}_main.py"; tmp.write_text(src, encoding="utf-8")
    out = ROOT / f"tools/kaggle_grilla/kernel_hft_clusters_info_{modo}.py"
    try: K(str(tmp.relative_to(ROOT)), str(out), MODULOS)
    finally: tmp.unlink()
    return out


def _item(nombre, c, sugerencia, por_activo=None, nominada=False, control=None, compuerta=True, monotono=None, signo=1):
    c = c or {}
    return dict(nombre=nombre, diferencia=c.get("diferencia"), ic90=c.get("ic90"), se=c.get("se"), mde80=c.get("mde80"), nominada=nominada,
                n_min=min(c.get("n_real", 0), c.get("n_placebo", 0)), compuerta_ok=compuerta, media_a=c.get("media_real"),
                por_activo=por_activo or {}, control_diferencia=control, monotono=monotono, sugerencia=sugerencia, signo_esperado=signo)


def recomendaciones(modo: str) -> str:
    """Lectura y próximo análisis de un resultado (edgelab/research/recomendador.py) → RECOMENDACIONES_<modo>.md."""
    from edgelab.research import hft_contexto as KX, hft_rebotes as RB, recomendador as RC
    res = json.loads((DIR / f"HFTC_{modo}.json").read_text(encoding="utf-8"))
    if modo == "rebotes":
        nom = set(res.get("nominadas_bh_q010") or [])
        its = [_item(d, v.get("conjunto"), RB.SUGERENCIAS.get(d), {i: dict(diferencia=(c or {}).get("diferencia"), se=(c or {}).get("se")) for i, c in v["por_activo"].items()}, d in nom)
               for d, v in res.get("por_definicion", {}).items()]
    elif modo == "contexto":
        nom = set(res.get("nominadas_bh_q010") or [])
        its = [_item(var, v if v.get("estado") == "PROBADA" else {"n_real": v["conteos"].get(v["estratos"][0], 0), "n_placebo": v["conteos"].get(v["estratos"][1], 0)},
                     KX.SUGERENCIAS.get(var), v.get("por_activo"), var in nom, (v.get("control") or {}).get("diferencia"),
                     v.get("estado") == "PROBADA", v.get("monotono"), v.get("signo_esperado", 0)) for var, v in res.get("variables", {}).items()]
    else:
        its = [_item(p, res[p].get("conjunto"), {"rebote": "Pasar a las 7 definiciones de rebote (HFT-REBOTES) para ver qué condición lo concentra.",
                                                  "iman": "Medir la distancia al cluster como objetivo de reglas que ya tengan entrada."}[p],
                     {i: dict(diferencia=(c or {}).get("diferencia"), se=(c or {}).get("se")) for i, c in res[p]["por_activo"].items()},
                     (res[p].get("stouffer") or {}).get("p", 1) < 0.05) for p in ("rebote", "iman") if p in res]
    rec = RC.recomendar(its); out = DIR / f"RECOMENDACIONES_{modo}.md"
    out.write_text(RC.markdown(f"Recomendaciones — HFT-CLUSTERS {modo}", rec, f"HFTC_{modo}.json"), encoding="utf-8")
    return out.relative_to(ROOT)


USA = {"base": MODULOS[:5], "rebotes": ["edgelab/research/hft_rebotes.py"], "contexto": ["edgelab/research/hft_rebotes.py", "edgelab/research/hft_contexto.py"],
       "ruptura": ["edgelab/research/hft_rebotes.py", "edgelab/research/hft_ruptura.py"],
       "niveles": ["edgelab/research/hft_rebotes.py", "edgelab/research/hft_ruptura.py", "edgelab/research/niveles_sesion.py"]}


def no_vigente(modo: str, res: dict) -> list:
    """Módulos que el modo USA y que cambiaron desde que se construyó el kernel (`preflight.codigo_vigente` restringido al modo:
    un cambio en un módulo que el modo no importa no invalida la corrida)."""
    from edgelab.research.preflight import codigo_vigente
    usa = set(USA["base"] + USA.get(modo.replace("_replica", "").replace("_rep", "").replace("_otros", ""), []))
    return [m for m in codigo_vigente(res, ROOT) if m in usa]


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]; slug = lambda m: f"nicolasbuttaro/hft-clusters-info-{m.replace('_', '-')}-20261110"   # Kaggle no admite «_» en el slug
    k = lambda *x: subprocess.run([sys.executable, str(ROOT / "tools/kaggle_kernel.py"), *x], capture_output=True, text=True).stdout
    if a[0] == "traer":
        for ext in ("json", "csv"): print(k("output", "--slug", slug(a[1]), "--file", f"HFTC_{a[1]}.{ext}", "--out", str(DIR / f"HFTC_{a[1]}.{ext}")).strip())
        js = DIR / f"HFTC_{a[1]}.json"
        if js.exists():                                                  # error 23 de preflight: ¿corrió con el código vigente?
            res = json.loads(js.read_text(encoding="utf-8")); viejo = no_vigente(a[1], res)
            acept = dict(x.split("=", 1) for x in sys.argv if "=" in x and x.split("=", 1)[0] in viejo)   # modulo=justificación (diff revisado)
            if viejo and set(viejo) <= set(acept):                       # cambio revisado y declarado irrelevante: queda escrito en el resultado
                res["cambios_aceptados"] = acept; js.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
                print("cambios de código aceptados con justificación:", acept); viejo = []
            if viejo:
                for ext in ("json", "csv"):
                    f = DIR / f"HFTC_{a[1]}.{ext}"
                    if f.exists(): f.rename(DIR / f"HFTC_{a[1]}.NO_VIGENTE.{ext}")
                raise SystemExit(f"NO VIGENTE: el resultado bajado corrió con otra versión de {viejo} (¿versión anterior del kernel o todavía "
                                 "corriendo?). Se renombró a HFTC_<modo>.NO_VIGENTE.*: no se interpreta. Esperar la versión nueva.")
        if js.exists() and a[1] in ("info", "rebotes", "contexto"): print("escrito", recomendaciones(a[1]))
        return
    if a[0] == "recomendar": print("escrito", recomendaciones(a[1])); return
    out = construir(a[0]); print("construido", out.relative_to(ROOT))
    if "--solo-construir" not in sys.argv:
        r = k("push", "--slug", slug(a[0]), "--title", f"hft clusters info {a[0]} 20261110", "--script", str(out), "--dataset", DATASET)
        print(r[-300:])
        if '"versionNumber"' not in r or '"hasError":true' in r:            # O19: un push fallido no puede pasar en silencio
            raise SystemExit(f"FALLÓ el lanzamiento de {slug(a[0])}: revisar la salida de tools/kaggle_kernel.py push")


if __name__ == "__main__":
    main()
