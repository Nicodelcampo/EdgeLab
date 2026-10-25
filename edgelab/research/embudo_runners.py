"""Runners del embudo (2026-10-23): dónde corre cada etapa.

KaggleRunner  etapas pesadas sobre datos de desarrollo: arma el kernel del experimento (embudo_main + módulos con SHA), resuelve
              datasets (futuros del release por `needs`; spot de Dukascopy por dataset del catálogo) y la fricción canónica del
              instrumento de ejecución (edgelab.costos: si el spread no está medido, NO se lanza), lanza con tools/kaggle_launch.py,
              consulta y trae RESULTADO.json.
LocalRunner   etapas del holdout sobre los datos sellados de la máquina (nunca suben a Kaggle): corre en el momento.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_LANZAR_S = 480       # el servicio del Debian (TimeoutStartSec=900) corta el ciclo entero: un push no puede comérselo solo
BASE_MODULOS = ["edgelab/holdout.py", "edgelab/research/fuentes_ticks.py", "edgelab/research/areas_expansion.py", "edgelab/research/areas_expansion_run.py",
                "edgelab/research/grilla_generica.py", "edgelab/research/controles.py", "edgelab/research/etapas.py"]


def friccion(instrumento: str) -> tuple:
    """(fricción base, extra adverso) en puntos del instrumento de EJECUCIÓN. Un spot no se ejecuta: usa la de su futuro."""
    from edgelab import costos as C
    from edgelab.research.fuentes_ticks import DUKASCOPY
    inst = instrumento
    if inst.startswith("DK:"):
        inst = next((k for k, v in DUKASCOPY.items() if v == inst[3:] and not k.startswith("M")), None)
        if inst is None: raise ValueError(f"{instrumento}: sin futuro de referencia para el costo")
    b = C.friccion_rt_puntos(inst, "base"); a = C.friccion_rt_puntos(inst, "adverso")       # CostoNoMedido -> no se lanza
    return b, a - b


def datasets(nombre: str, desde: int, hasta: int) -> tuple:
    """(needs, extra_datasets) para kaggle_launch."""
    if nombre.startswith("DK:"):
        resolver = json.loads((ROOT / "docs/data_catalog/RESOLVER.json").read_text(encoding="utf-8"))
        from edgelab.research.fuentes_ticks import DUKASCOPY
        fut = next(k for k, v in DUKASCOPY.items() if v == nombre[3:])
        return [], ["nicolasbuttaro/" + resolver["spot_datasets"][fut]]
    f = lambda d: f"{str(d)[:4]}-{str(d)[4:6]}-{str(d)[6:]}"
    return [f"{nombre}:{f(desde)}:{f(hasta)}"], []


def modulo_a_ruta(mod: str) -> str:
    return mod.replace(".", "/") + ".py"


def dependencias(ruta: str, vistos=None) -> list:
    """Módulos del repo que importa `ruta` (recursivo): el kernel los embebe todos. Antes sólo se embebía el experimento y uno
    que importara otro módulo del repo fallaba recién en Kaggle."""
    import ast
    vistos = vistos if vistos is not None else []
    if ruta in vistos or not (ROOT / ruta).exists(): return vistos
    vistos.append(ruta)
    for n in ast.walk(ast.parse((ROOT / ruta).read_text(encoding="utf-8-sig"))):
        mods = [n.module] if isinstance(n, ast.ImportFrom) and n.module else [a.name for a in n.names] if isinstance(n, ast.Import) else []
        if isinstance(n, ast.ImportFrom) and n.module:
            mods += [f"{n.module}.{a.name}" for a in n.names]                      # from edgelab.research import u1_indaga
        for m in mods:
            if m.split(".")[0] in ("edgelab", "tests"):
                r = modulo_a_ruta(m)
                if (ROOT / r).exists(): dependencias(r, vistos)
    return vistos


class KaggleRunner:
    def __init__(self, owner=None, python=sys.executable, carpeta=None, dataset_sellado=None):
        """`dataset_sellado`: si se da, este runner corre las etapas del HOLDOUT en Kaggle leyendo SÓLO ese dataset privado
        (datos desde la sesión del 2026-10-01; nunca se adjunta a etapas de desarrollo)."""
        self.owner = owner or os.environ.get("EDGELAB_KAGGLE_OWNER", "nicolasbuttaro")      # SV1: la cuenta de Kaggle de Gonza
        self.python, self.dataset_sellado = python, dataset_sellado
        self.carpeta = Path(carpeta or tempfile.mkdtemp(prefix="embudo_kernels_"))

    def _construir(self, spec) -> Path:
        sys.path.insert(0, str(ROOT / "tools" / "kaggle_grilla"))
        from construir_kernel import construir
        out = self.carpeta / f"kernel_{spec['cid'].lower()}.py"
        construir("tools/kaggle_grilla/embudo_main.py", str(out), list(dict.fromkeys(BASE_MODULOS + dependencias(modulo_a_ruta(spec["experimento"])))))
        return out

    def argumentos(self, spec, etapa, params, periodo) -> list:
        ejec = spec.get("ejecucion") or spec["sensor"]; fr, ex = friccion(ejec)
        if self.dataset_sellado:                                         # holdout: sólo el dataset sellado, nada del release
            needs, extra = [], [self.dataset_sellado]
        else:
            needs, extra = datasets(spec["sensor"], *periodo)
            if ejec != spec["sensor"]:
                n2, e2 = datasets(ejec, *periodo); needs += n2; extra += e2
            extra += list(spec.get("datasets_extra", []))                 # p. ej. el almacén de zonas de U1-ZONAS (target-free)
        slug = f"{spec.get('cuenta_kaggle') or self.owner}/embudo-{spec['cid'].lower()}-{etapa.lower()}-{periodo[0]}".replace("_", "-")[:100]   # Kaggle no acepta "_" (HOLDOUT_CONTEO)
        env = dict(EXPERIMENTO=spec["experimento"], ETAPA=etapa, SENSOR=spec["sensor"], EJECUCION=ejec, DESDE=str(periodo[0]), HASTA=str(periodo[1]),
                   FRICCION=repr(fr), EXTRA=repr(ex), PARAMS=json.dumps(params, separators=(",", ":"), default=float))
        if self.dataset_sellado:
            if not params.get("acta"): raise ValueError("etapa de holdout sin acta registrada")
            env["SELLADO"] = "1"
        a = ["--slug", slug, "--script", str(self._construir(spec))]
        for n in needs: a += ["--need", n]
        for d in dict.fromkeys(extra): a += ["--extra-dataset", d]
        for k, v in env.items(): a += ["--env", f"{k}={v}"]
        return a

    def lanzar(self, spec, etapa, params, periodo) -> str:
        a = self.argumentos(spec, etapa, params, periodo)
        env = dict(os.environ)                                         # cuenta de Kaggle de la campaña (config/kaggle_cuentas.json); el lanzador
        cuenta = a[1].split("/")[0]                                    # protegido no se toca: la cuenta viaja por el entorno hasta kaggle_kernel
        cuentas = [k for k in json.loads((ROOT / "config/kaggle_cuentas.json").read_text(encoding="utf-8")) if not k.startswith("_")]
        if cuenta in cuentas: env.update(EDGELAB_KAGGLE_OWNER=cuenta, EDGELAB_KAGGLE_DATASET_OWNERS=",".join(cuentas))
        r = subprocess.run([self.python, "-X", "utf8", str(ROOT / "tools/kaggle_launch.py"), *a], cwd=ROOT, capture_output=True, text=True,
                           timeout=TIMEOUT_LANZAR_S, env=env)
        if r.returncode != 0 or '"url"' not in r.stdout: raise RuntimeError(f"no se lanzó: {(r.stdout + r.stderr)[-500:]}")
        return a[1]

    def estado(self, handle) -> str:
        r = subprocess.run([self.python, str(ROOT / "tools/kaggle_kernel.py"), "status", "--slug", handle], cwd=ROOT, capture_output=True, text=True, timeout=120)
        out = r.stdout.lower()
        for s in ("complete", "running", "queued", "error", "cancel"):
            if f'"{s}' in out: return "complete" if s == "complete" else ("running" if s in ("running", "queued") else "error")
        if '"code":404' in out.replace(" ", "") or "no runs found" in out: return "error"     # el push no arrancó (p. ej. tope de sesiones): relanzar, no esperar para siempre
        return "running"

    def traer(self, handle) -> dict:
        out = self.carpeta / f"{handle.split('/')[-1]}_RESULTADO.json"
        subprocess.run([self.python, str(ROOT / "tools/kaggle_kernel.py"), "output", "--slug", handle, "--file", "RESULTADO.json", "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
        return json.loads(out.read_text(encoding="utf-8"))


class LocalRunner:
    """Etapas del holdout en la máquina, con datos sellados: `lectores` = {nombre: f(desde, hasta, spec) -> bloques}.
    `carpeta`: donde se guarda cada resultado. El ciclo del Debian arma un runner NUEVO en cada vuelta; sin carpeta el
    resultado vivía sólo en memoria, la vuelta siguiente veía el handle como desconocido («error») y a la tercera el embudo
    cerraba la campaña como BLOQUEADA: CONTEO y HOLDOUT no podían terminar nunca desde el ciclo."""
    def __init__(self, lectores: dict, ticks: dict, acta_requerida=True, carpeta=None):
        self.lectores, self.ticks, self.acta_requerida, self.res = lectores, ticks, acta_requerida, {}
        self.carpeta = Path(carpeta) if carpeta else None

    def _archivo(self, h): return self.carpeta / f"{h}.json"

    def lanzar(self, spec, etapa, params, periodo) -> str:
        from edgelab.research import etapas as ET, grilla_generica as GG
        exp = importlib.import_module(spec["experimento"]); ejec = spec.get("ejecucion") or spec["sensor"]
        ctx = GG.contexto_m1(self.lectores[spec["sensor"]](*periodo, spec), self.ticks[spec["sensor"]])
        cx_ej = GG.contexto_m1(self.lectores[ejec](*periodo, spec), self.ticks[ejec]) if ejec != spec["sensor"] else None
        fr, ex = friccion(ejec)
        h = f"local-{spec['cid']}-{etapa}-{periodo[0]}-{periodo[1]}-{len(self.res)}"
        if self.carpeta:
            self.carpeta.mkdir(parents=True, exist_ok=True); k = 0
            while self._archivo(h).exists(): k += 1; h = f"local-{spec['cid']}-{etapa}-{periodo[0]}-{periodo[1]}-{k}"
        self.res[h] = json.loads(json.dumps(ET.ejecutar(etapa, exp, ctx, friccion=fr, extra_adverso=ex, cx_ej=cx_ej, params=params, log=lambda s: None), default=float))
        if self.carpeta:
            tmp = self._archivo(h).with_suffix(".tmp"); tmp.write_text(json.dumps(self.res[h], default=float), encoding="utf-8"); tmp.replace(self._archivo(h))
        return h

    def estado(self, h): return "complete" if h in self.res or (self.carpeta and self._archivo(h).exists()) else "error"

    def traer(self, h):
        if h not in self.res and self.carpeta: self.res[h] = json.loads(self._archivo(h).read_text(encoding="utf-8"))
        return self.res[h]


def lectores_sellados(cfg_sellado: dict, raiz_embudo: Path) -> tuple:
    """De la configuración del Debian ({"DK:USATECHIDXUSD": carpeta, "NQ": parquet sellado}) a lectores del LocalRunner. El de NQ
    exige el acta de holdout de la campaña (la escribe la etapa ACTA antes de mirar)."""
    from edgelab.research import fuentes_ticks as F
    lec, ticks = {}, {}
    for nombre, ruta in (cfg_sellado or {}).items():
        if nombre.startswith("DK:"):
            sym = nombre[3:]; lec[nombre] = (lambda d0, d1, spec, s=sym, r=ruta: F.bloques_spot_sellado(s, d0, d1, r)); ticks[nombre] = F.REDONDEO_SPOT[sym]
        else:
            lec[nombre] = (lambda d0, d1, spec, r=ruta: F.bloques_nq_sellado(d0, d1, r, str(Path(raiz_embudo) / spec["cid"] / "ACTA_HOLDOUT.json")))
            ticks[nombre] = F.TICK_FUTURO[nombre]
    return lec, ticks
