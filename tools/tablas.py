#!/usr/bin/env python3
"""Tablas de eventos de punta a punta con UNA herramienta (edgelab/research/tablas.py; AUTOMATIZACION_PROCESOS_20261111).

  python tools/tablas.py preflight <modulo>                                   # contrato, causalidad, motor calibrado, kernel SINT
  python tools/tablas.py lanzar <modulo> FUENTE:DESDE:HASTA [...]              # preflight + kernel + Kaggle; una o varias ventanas
  python tools/tablas.py traer [<modulo>]                                     # trae todo lo terminado (verifica código vigente)
  python tools/tablas.py estado                                               # kernels lanzados y su estado
  python tools/tablas.py explorar <modulo>                                    # análisis de desarrollo → EXPLORACION.md/json
  python tools/tablas.py congelar <modulo> <hipotesis.json> --familia F FUENTE:DESDE:HASTA [...]   # congela y lanza la confirmación
  python tools/tablas.py confirmar <modulo> <CONGELADAS_*.json>               # UNA vez → RESULTADO_CONFIRMACION_<hash>.md/json
  python tools/tablas.py curva <modulo> <definición|-> <ejecución> [filtro]   # curva de capital IS / OOS / confirmación / holdout (SVG)
  python tools/tablas.py holdout <modulo> <CONGELADAS_*.json> FUENTE:DESDE:HASTA --acta <md committeado> --p <p1,p2,...>
                                                                               # apertura exploratoria de la familia (una sola): registra y lanza
  python tools/tablas.py confirmar_holdout <modulo> <CONGELADAS_*.json>       # UNA vez: veredicto + Fisher con las p de desarrollo

FUENTE: NQ, ES, YM, GC, ... (futuros del release) o DK:USATECHIDXUSD, DK:USA500IDXUSD, ... (spot de Dukascopy). El holdout se rechaza
en los lectores de desarrollo; la apertura (`holdout`) exige congeladas con hash, acta committeada, p de desarrollo declaradas y que
la familia no haya usado su apertura (edgelab/research/holdout_ventanas.py); la registra ANTES de lanzar.
Carpeta de cada módulo: `CARPETA` del módulo o docs/research/tablas/<NOMBRE>/ (tablas/ = desarrollo, confirmacion/ = confirmación).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.research import tablas as TB  # noqa: E402

LANZADAS = ROOT / "docs/research/tablas/LANZADAS.jsonl"


def carpeta(mod) -> Path:
    m = TB.cargar(mod); return ROOT / (getattr(m, "CARPETA", None) or f"docs/research/tablas/{m.NOMBRE}")


def slug(mod, fuente, d0, d1, owner) -> str:
    """Único por módulo: nombre corto + 6 caracteres del sha del NOMBRE completo (2026-11-11: cortar el nombre a 14 caracteres hizo
    que LUXIMB-AMARILLA, -R y -R2 compartieran slug y cada lanzamiento pisara al anterior)."""
    import hashlib
    nom = TB.cargar(mod).NOMBRE; h = hashlib.sha256(nom.encode()).hexdigest()[:6]
    f = fuente.replace("DK:", "").replace("IDXUSD", "").lower()[:4]
    s = f"t-{nom.lower()[:5].rstrip('-')}-{h}-{f}-{str(d0)[2:]}-{str(d1)[2:]}".replace("_", "-")
    if len(s) > 49 - len(owner) - 1: raise ValueError(f"slug demasiado largo: {s}")
    return f"{owner}/{s}"


def _ventanas(args):
    out = []
    for v in args:
        f, d0, d1 = v.rsplit(":", 2); out.append((f, int(d0), int(d1)))
    return out


def _leer():
    return [json.loads(l) for l in LANZADAS.read_text(encoding="utf-8").splitlines() if l.strip()] if LANZADAS.exists() else []


def preflight(modulo):
    e = TB.preflight(modulo)
    print("PREFLIGHT OK" if not e else "PREFLIGHT FALLA:\n- " + "\n- ".join(e)); return e


DATASET_SELLADO = "nicolasbuttaro/edgelab-holdout-sellado"


def lanzar(modulo, ventanas, uso="desarrollo", congeladas=None, env_extra=None):
    if preflight(modulo): raise SystemExit("no se lanza: el preflight falla")
    from edgelab.research.embudo_runners import datasets
    k = TB.construir_kernel(modulo); owner = os.environ.get("EDGELAB_KAGGLE_OWNER", "nicolasbuttaro"); LANZADAS.parent.mkdir(parents=True, exist_ok=True)
    for f, d0, d1 in ventanas:
        needs, extra = ([], [DATASET_SELLADO]) if uso == "holdout" else datasets(f, d0, d1); sl = slug(modulo, f, d0, d1, owner) + ("-h" if uso == "holdout" else "")
        a = [sys.executable, str(ROOT / "tools/kaggle_launch.py"), "--slug", sl, "--script", str(k), "--title", sl.split("/")[1],
             "--env", f"MODULO={modulo}", "--env", f"FUENTE={f}", "--env", f"DESDE={d0}", "--env", f"HASTA={d1}"]
        for n in needs: a += ["--need", n]
        for x in extra: a += ["--extra-dataset", x]
        for kv in (env_extra or {}).items(): a += ["--env", "=".join(kv)]
        r = subprocess.run(a, capture_output=True, text=True); sal = r.stdout + r.stderr
        fila = dict(ts=time.time(), modulo=modulo, fuente=f, desde=d0, hasta=d1, slug=sl, uso=uso, congeladas=congeladas, env_extra=env_extra)
        if "Maximum batch CPU session count" in sal:                     # tope de kernels simultáneos de Kaggle: a la cola, no a mano
            with LANZADAS.open("a", encoding="utf-8") as fh: fh.write(json.dumps(dict(fila, estado="en_cola"), ensure_ascii=False) + "\n")
            print("en cola (tope de Kaggle)", sl); continue
        if r.returncode or '"versionNumber"' not in sal or '"hasError":true' in sal:   # O19: un push fallido no pasa en silencio
            raise SystemExit(f"FALLÓ el lanzamiento de {sl}:\n{sal[-800:]}")
        with LANZADAS.open("a", encoding="utf-8") as fh: fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
        print("lanzada", sl)


def _env_cuenta(sl):
    """La credencial de la cuenta dueña del kernel (cada cuenta tiene su host en config/kaggle_cuentas.json)."""
    return dict(os.environ, EDGELAB_KAGGLE_OWNER=sl.split("/")[0])


def _estado(sl):
    r = subprocess.run([sys.executable, str(ROOT / "tools/kaggle_kernel.py"), "status", "--slug", sl], capture_output=True, text=True, env=_env_cuenta(sl))
    try: return json.loads(r.stdout.strip().splitlines()[-1]).get("status")
    except (ValueError, IndexError): return "?"


def reintentar_cola():
    """Relanza lo que quedó en cola por el tope de Kaggle (lo llama `traer`, así el ciclo del Debian lo hace solo)."""
    L = _leer(); lanzados = {x["slug"] for x in L if x.get("estado") != "en_cola"}
    for x in L:
        if x.get("estado") == "en_cola" and x["slug"] not in lanzados:
            try: lanzar(x["modulo"], [(x["fuente"], x["desde"], x["hasta"])], uso=x["uso"], congeladas=x.get("congeladas"), env_extra=x.get("env_extra"))
            except SystemExit as ex: print("sigue sin lanzarse", x["slug"], str(ex)[:200])
            lanzados.add(x["slug"])


def traer(modulo=None):
    from edgelab.research.preflight import codigo_vigente
    reintentar_cola(); pend = []; todas = _leer()
    anuladas = {(x.get("modulo"), x["slug"]) for x in todas if x.get("estado") == "anulada"}   # kernel pisado por otro módulo
    for L in [x for x in todas if x.get("estado") not in ("en_cola", "movida", "anulada") and (x.get("modulo"), x["slug"]) not in anuladas]:
        if modulo and L["modulo"] != modulo: continue
        nom = f"TABLA_{TB.cargar(L['modulo']).NOMBRE}_{L['fuente'].replace('DK:', '')}_{L['desde']}_{L['hasta']}"
        dest = carpeta(L["modulo"]) / {"confirmacion": "confirmacion", "holdout": "holdout"}.get(L["uso"], "tablas"); dest.mkdir(parents=True, exist_ok=True)
        if (dest / f"{nom}.json").exists(): continue
        st = _estado(L["slug"])
        if st != "complete": pend.append((L["slug"], st)); continue
        for ext in ("json", "csv.gz"):
            subprocess.run([sys.executable, str(ROOT / "tools/kaggle_kernel.py"), "output", "--slug", L["slug"], "--file", f"{nom}.{ext}", "--out", str(dest / f"{nom}.{ext}")],
                           capture_output=True, text=True, env=_env_cuenta(L["slug"]))
        js = dest / f"{nom}.json"
        if not js.exists(): pend.append((L["slug"], "sin salida (¿ERROR_KERNEL.txt?)")); continue
        viejo = codigo_vigente(json.loads(js.read_text(encoding="utf-8")), ROOT)
        if viejo:
            for ext in ("json", "csv.gz"): (dest / f"{nom}.{ext}").rename(dest / f"{nom}.NO_VIGENTE.{ext}")
            pend.append((L["slug"], f"NO VIGENTE ({viejo[:3]}): no se interpreta; relanzar")); continue
        print("traída", nom)
    for p in pend: print("pendiente", *p)
    return pend


def _tablas(modulo, sub):
    import pandas as pd
    fs = sorted((carpeta(modulo) / sub).glob("TABLA_*.csv.gz"))
    if not fs: raise SystemExit(f"sin tablas en {carpeta(modulo) / sub}")
    partes = []
    for f in fs:
        T = pd.read_csv(f); T["fuente"] = json.loads(f.with_name(f.name.replace(".csv.gz", ".json")).read_text())["fuente"].replace("DK:", ""); partes.append(T)
    return pd.concat(partes, ignore_index=True)


def explorar(modulo):
    from edgelab.research import analizar_tabla as AT
    res = AT.explorar(modulo, _tablas(modulo, "tablas")); d = carpeta(modulo)
    for c in res["cortes"].values(): c.pop("todas", None)
    (d / "EXPLORACION.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    (d / "EXPLORACION.md").write_text(AT.informe_exploracion(res), encoding="utf-8"); print("escrito", (d / "EXPLORACION.md").relative_to(ROOT))


def congelar(modulo, hip, familia, ventanas):
    from edgelab.funnel.multiplicity import TrialRegistry
    from edgelab.research import analizar_tabla as AT
    p = AT.congelar(modulo, json.loads(Path(hip).read_text(encoding="utf-8")), familia, carpeta(modulo),
                    [dict(fuente=f, desde=d0, hasta=d1) for f, d0, d1 in ventanas], TrialRegistry(ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl"))
    print("congeladas", p.relative_to(ROOT), "— commitealas ANTES de mirar la confirmación"); lanzar(modulo, ventanas, uso="confirmacion", congeladas=str(p.relative_to(ROOT)))


def confirmar(modulo, cong):
    from edgelab.research import analizar_tabla as AT
    C = AT.verificar_congeladas(Path(cong)); out = carpeta(modulo) / f"RESULTADO_CONFIRMACION_{C['sha256'][:8]}.json"
    if out.exists(): raise SystemExit(f"ya confirmado: {out.relative_to(ROOT)} (una sola vez)")
    ven = {(v["fuente"].replace("DK:", ""), v["desde"], v["hasta"]) for v in C["ventana_confirmacion"]}
    T = _tablas(modulo, "confirmacion")
    T = T[T.apply(lambda r: any(r.fuente == f and d0 <= r.ses <= d1 for f, d0, d1 in ven), axis=1)]
    res = AT.confirmar(modulo, T.reset_index(drop=True), Path(cong))
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    out.with_suffix(".md").write_text(AT.informe_confirmacion(res), encoding="utf-8"); print("escrito", out.with_suffix(".md").relative_to(ROOT))


def holdout(modulo, cong, ventana, acta, ps):
    """Apertura exploratoria (modo 2026-11-08): congeladas con hash, acta committeada, una p de desarrollo por hipótesis, y la familia
    sin apertura previa. Registra la apertura en HOLDOUT_VENTANAS.jsonl ANTES de lanzar."""
    from edgelab.research import analizar_tabla as AT, holdout_ventanas as HV
    C = AT.verificar_congeladas(Path(cong)); fam = C["familia"]; cid = f"{fam}::holdout_{C['sha256'][:8]}"
    if len(ps) != len(C["hipotesis"]): raise SystemExit("una p de desarrollo por hipótesis congelada (--p p1,p2,...)")
    commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", acta], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not commit: raise SystemExit(f"el acta {acta} no está committeada: no se abre")
    (f, d0, d1), = ventana
    if (pr := HV.problemas(fam, d0, cid)): raise SystemExit("no se abre: " + "; ".join(pr))
    reg = carpeta(modulo) / f"HOLDOUT_{C['sha256'][:8]}.json"
    reg.write_text(json.dumps(dict(cid=cid, congeladas=str(cong), acta=acta, commit=commit, p_desarrollo=ps, ventana=[f, d0, d1]), indent=1), encoding="utf-8")
    HV.registrar_apertura(fam, cid, d0, n_fijo=0); print("apertura registrada", cid)
    lanzar(modulo, ventana, uso="holdout", congeladas=str(cong), env_extra=dict(SELLADO="1", ACTA_JSON=json.dumps(dict(acta=acta, commit=commit, familia=fam, cid=cid))))


def confirmar_holdout(modulo, cong):
    from edgelab.research import analizar_tabla as AT
    C = AT.verificar_congeladas(Path(cong)); reg = json.loads((carpeta(modulo) / f"HOLDOUT_{C['sha256'][:8]}.json").read_text(encoding="utf-8"))
    out = carpeta(modulo) / f"RESULTADO_HOLDOUT_{C['sha256'][:8]}.json"
    if out.exists(): raise SystemExit(f"ya analizado: {out.relative_to(ROOT)} (una sola vez)")
    res = AT.confirmar(modulo, _tablas(modulo, "holdout"), Path(cong))
    for h, pd_ in zip(res["hipotesis"], reg["p_desarrollo"]): h["p_desarrollo"] = pd_; h["p_fisher"] = AT.fisher([pd_, h["p"]])
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    out.with_suffix(".md").write_text(AT.informe_confirmacion(res) + "\nFisher con desarrollo: " + "; ".join(
        f"{h['ejec']}: {h['p_fisher']:.4f}" for h in res["hipotesis"]) + "\n", encoding="utf-8"); print("escrito", out.with_suffix(".md").relative_to(ROOT))


def curva(modulo, dfn, ej, fn="todos"):
    """R neto por operación, en orden, por tramo: DESC = IS, REP = OOS, la confirmación y el holdout (si existen sus tablas)."""
    import numpy as np
    from edgelab.research import analizar_tabla as AT, curva as CV
    tramos = []
    for sub, nom in (("tablas", None), ("confirmacion", "CONFIRMACION"), ("holdout", "HOLDOUT")):
        try: T = _tablas(modulo, sub)
        except SystemExit: continue
        T = T.sort_values(["t", "k"], kind="mergesort").reset_index(drop=True); y = AT.serie(TB.cargar(modulo), T, None if dfn == "-" else dfn, ej, fn)
        grupos = [(("IS" if p == "DESC" else "OOS" if p == "REP" else p), g) for p, g in T.groupby(TB.periodo(TB.cargar(modulo), T.ses))] if nom is None else [(nom, T)]
        for n, g in grupos:
            yy = y[g.index]; yy = yy[np.isfinite(yy)]
            if len(yy): tramos.append((n, f"{int(g.ses.min())}–{int(g.ses.max())}", yy))
    orden = {"IS": 0, "OOS": 1, "CONFIRMACION": 2, "HOLDOUT": 3}; tramos.sort(key=lambda x: orden.get(x[0], 9))
    s, res = CV.svg(tramos, f"{TB.cargar(modulo).NOMBRE} — {ej}", f"definición {dfn}, filtro {fn}; R neto acumulado con costos de edgelab/costos.py")
    out = carpeta(modulo) / f"CURVA_{ej}_{dfn}_{fn}.svg".replace("/", "-"); out.write_text(s, encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print("escrito", out)


def estado():
    for L in _leer(): print(L["slug"], L.get("uso", L.get("estado")), L.get("estado") or _estado(L["slug"]))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]; op = a[0]
    if op == "preflight": sys.exit(1 if preflight(a[1]) else 0)
    elif op == "lanzar": lanzar(a[1], _ventanas(a[2:]))
    elif op == "traer": traer(a[1] if len(a) > 1 else None)
    elif op == "estado": estado()
    elif op == "explorar": explorar(a[1])
    elif op == "congelar":
        fam = sys.argv[sys.argv.index("--familia") + 1]; congelar(a[1], a[2], fam, _ventanas([x for x in a[3:] if x != fam]))
    elif op == "confirmar": confirmar(a[1], a[2])
    elif op == "curva": curva(*a[1:5])
    elif op == "holdout":
        acta = sys.argv[sys.argv.index("--acta") + 1]; ps = [float(x) for x in sys.argv[sys.argv.index("--p") + 1].split(",")]
        holdout(a[1], a[2], _ventanas([x for x in a[3:] if ":" in x]), acta, ps)
    elif op == "confirmar_holdout": confirmar_holdout(a[1], a[2])
    else: raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
