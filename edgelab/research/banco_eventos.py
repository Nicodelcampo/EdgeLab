"""BANCO DE EVENTOS (2026-11-10, pedido de Nico): probar muchísimas cosas distintas sobre una misma tabla de eventos sin diseñarlas una
por una y sin gastar multiplicidad por cada cosa mirada. Documento rector: `docs/research/BANCO_DE_EVENTOS.md`.

Idea: un GENERADOR (kernel) produce una tabla de eventos (una fila por evento: identificadores, rasgos causales, desenlaces, y filas de
control con placebo = 1). Un EXPERIMENTO es una especificación JSON de pocas líneas sobre esa tabla. El banco hace siempre lo mismo:

  1. Valida el contrato de la tabla (columnas, holdout, sesiones excluidas, rasgos que no sean desenlaces).
  2. Parte las sesiones en dos mitades fijadas sólo por la fecha (semanas alternas, desfase por familia): A y B.
  3. En A explora TODO sin costo inferencial: cada rasgo × estrato, cada par de rasgos × estratos, y un modelo aditivo con todos los
     rasgos. Los cortes de los estratos salen de A.
  4. Congela en un archivo, ANTES de mirar B, las k mejores celdas (rasgos distintos, umbral económico, n mínimo) y el modelo.
  5. Prueba en B sólo esas k + 1 hipótesis (bootstrap por sesión, BH q 0,10). La multiplicidad que se gasta es k + 1, no las miles de
     celdas exploradas. B se usa UNA vez por familia y ventana (libro `USOS.jsonl`).
  6. Traduce la salida a RECOMENDACIONES con `recomendador.py`. Lo que se nomina va a la réplica congelada de la familia; nada se
     promueve desde acá.
Calibración (`calibrar`): el mismo proceso con el desenlace permutado dentro de (activo, mes) da la tasa de falsos del método; el
preflight la exige baja antes de correr con datos reales.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "docs/research/banco_eventos"
IDS = ("inst", "fecha", "placebo")
OBLIGATORIOS = ("nombre", "familia", "tabla", "desenlace", "columnas_desenlace", "ventana", "justificacion_economica", "como_refutar")
DEFECTOS = dict(direccion=1, nulo=0.0, umbral_economico=0.08, k=3, q=0.10, min_n=100, min_n_b=60, pares=True, cortes_fijos={},
                rasgos="todos", max_rasgos=60, habilitada=True, etapa="EF2", linaje=None, n_boot=2000, encogimiento=200)
Z = NormalDist()

# Generadores conocidos: quién produce tablas con el contrato del banco. Un generador nuevo se agrega acá con su test de causalidad.
GENERADORES = {
    "hft_ruptura": dict(funcion="edgelab.research.hft_ruptura.ruptura_del_dia", kernel="tools/hft_clusters_info.py ruptura",
                        tabla="docs/research/hft_clusters_u1_20261110/HFTC_ruptura.csv",
                        eventos="primer regreso (D0) a un cluster HFT grande de NQ/ES tras alejarse X/2; control = pseudo-clusters desplazados",
                        desenlaces=["rompe", "rompe_media", "rompe_doble", "t_res_s", "avance15_x"]),
    "hft_contexto": dict(funcion="edgelab.research.hft_contexto.contexto_del_dia", kernel="tools/hft_clusters_info.py contexto",
                         tabla="docs/research/hft_clusters_u1_20261110/HFTC_contexto.csv",
                         eventos="toques de la definición de rebote elegida, con el contexto de otros clusters vivos",
                         desenlaces=["resultado"]),
}


# ---------------------------------------------------------------- especificación y contrato
def especificacion(fuente) -> dict:
    d = json.loads(Path(fuente).read_text(encoding="utf-8")) if isinstance(fuente, (str, Path)) else dict(fuente)
    return {**DEFECTOS, **d}


def leer_tabla(spec: dict, root: Path = ROOT) -> pd.DataFrame:
    p = Path(spec["tabla"]); p = p if p.is_absolute() else root / p
    return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)


def rasgos_de(spec: dict, T: pd.DataFrame) -> list:
    fuera = set(IDS) | set(spec["columnas_desenlace"]) | {spec["desenlace"]} | set(spec.get("excluir", []))
    if spec["rasgos"] != "todos": return list(spec["rasgos"])
    return [c for c in T.columns if c not in fuera and pd.api.types.is_numeric_dtype(T[c])]


def validar(spec: dict, T: pd.DataFrame | None = None) -> list:
    """Errores que impiden correr (lista vacía = válido)."""
    from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT, sesion_excluida
    err = [f"falta `{c}` en la especificación" for c in OBLIGATORIOS if not spec.get(c)]
    if err: return err
    d0, d1 = spec["ventana"]
    if d1 >= HOLDOUT_PRIMERA_SESION_INT: err.append(f"la ventana termina en {d1}: toca el holdout ({HOLDOUT_PRIMERA_SESION_INT})")
    if spec["desenlace"] not in spec["columnas_desenlace"]: err.append("el desenlace tiene que estar en `columnas_desenlace`")
    if spec["direccion"] not in (-1, 0, 1): err.append("`direccion` es +1, −1 o 0")
    if not spec.get("habilitada", True): err.append("especificación no habilitada (`habilitada: false`)")
    if T is None: return err
    falt = [c for c in IDS + (spec["desenlace"],) if c not in T]
    if falt: return err + [f"la tabla no tiene {falt}"]
    if not set(T.placebo.unique()) <= {0, 1}: err.append("`placebo` sólo 0 o 1")
    f = T.fecha.astype(int)
    if f.max() >= HOLDOUT_PRIMERA_SESION_INT: err.append(f"la tabla tiene sesiones del holdout (máx {f.max()})")
    if f.min() < d0 or f.max() > d1: err.append(f"la tabla ({f.min()}–{f.max()}) se sale de la ventana declarada {spec['ventana']}")
    exc = [(i, x) for i, x in T[["inst", "fecha"]].drop_duplicates().itertuples(index=False) if sesion_excluida(str(i), int(x))]
    if exc: err.append(f"sesiones excluidas del holdout en la tabla: {exc[:3]}")
    R = rasgos_de(spec, T)
    if not R: err.append("sin rasgos numéricos")
    if len(R) > spec["max_rasgos"]: err.append(f"{len(R)} rasgos > max_rasgos {spec['max_rasgos']}: la biblioteca se declara, no se vuelca")
    fuga = [r for r in R if r in spec["columnas_desenlace"]]
    if fuga: err.append(f"rasgos que son desenlaces (fuga): {fuga}")
    no_num = [r for r in R if r not in T or not pd.api.types.is_numeric_dtype(T[r])]
    if no_num: err.append(f"rasgos inexistentes o no numéricos: {no_num}")
    y = T.loc[T.placebo == 0, spec["desenlace"]]
    if not np.isfinite(y.to_numpy(float)).all(): err.append("el desenlace de los eventos reales tiene NaN o infinitos")
    return err


# ---------------------------------------------------------------- partición honesta
def mitad(fechas, familia: str) -> np.ndarray:
    """0 = A (explorar), 1 = B (probar). Sólo depende de la fecha y de la familia: semana (lunes a domingo) alterna, con un desfase
    fijado por el hash de la familia. Ninguna información del resultado entra en la partición."""
    off = int(hashlib.sha256(familia.encode()).hexdigest(), 16) % 2
    lunes0 = date(2000, 1, 3).toordinal()
    sem = np.array([(date(x // 10000, x // 100 % 100, x % 100).toordinal() - lunes0) // 7 for x in np.asarray(fechas, int)])
    return ((sem + off) % 2).astype(int)


# ---------------------------------------------------------------- estratos (cortes SIEMPRE de A)
def cortes(A: pd.DataFrame, r: str, fijos: dict) -> dict:
    """{inst: (c1, c2)} con estrato = (v > c1) + (v > c2). Fijos si se declararon; si no, terciles de A por activo."""
    if r in fijos: return {i: tuple(fijos[r]) for i in A.inst.unique()}
    out = {}
    for i, h in A.groupby("inst"):
        v = h[r].to_numpy(float); v = v[np.isfinite(v)]
        if v.size: out[i] = tuple(float(x) for x in np.quantile(v, [1 / 3, 2 / 3]))
    return out


def estrato(T: pd.DataFrame, r: str, c: dict) -> np.ndarray:
    out = np.full(len(T), -1); v = T[r].to_numpy(float); ins = T.inst.to_numpy()
    for i, (c1, c2) in c.items():
        m = (ins == i) & np.isfinite(v); out[m] = (v[m] > c1).astype(int) + (v[m] > c2).astype(int)
    return out


# ---------------------------------------------------------------- inferencia por sesión
def _sesiones(T):
    return pd.factorize(T.inst.astype(str) + "|" + T.fecha.astype(str))[0]


def media_sesion(y, ses, n_boot=2000, seed=7):
    """Media y error estándar por bootstrap de sesiones (los eventos de una sesión no son independientes)."""
    y = np.asarray(y, float); s = np.asarray(ses)
    if y.size == 0: return np.nan, np.nan
    u, k = np.unique(s, return_inverse=True); su = np.bincount(k, y); nu = np.bincount(k).astype(float)
    mu = float(su.sum() / nu.sum())
    if len(u) < 5: return mu, np.nan
    idx = np.random.default_rng(seed).integers(0, len(u), (n_boot, len(u)))
    return mu, float((su[idx].sum(1) / nu[idx].sum(1)).std(ddof=1))


def dif_sesion(y, ses, g, n_boot=2000, seed=7):
    """Diferencia de medias (g = 1) − (g = 0) con bootstrap de sesiones."""
    y = np.asarray(y, float); g = np.asarray(g, int); s = np.asarray(ses)
    u, k = np.unique(s, return_inverse=True)
    s1, n1 = np.bincount(k, y * (g == 1), len(u)), np.bincount(k, (g == 1).astype(float), len(u))
    s0, n0 = np.bincount(k, y * (g == 0), len(u)), np.bincount(k, (g == 0).astype(float), len(u))
    if n1.sum() == 0 or n0.sum() == 0: return np.nan, np.nan
    d = float(s1.sum() / n1.sum() - s0.sum() / n0.sum())
    if len(u) < 5: return d, np.nan
    idx = np.random.default_rng(seed).integers(0, len(u), (n_boot, len(u)))
    with np.errstate(invalid="ignore", divide="ignore"):
        b = s1[idx].sum(1) / n1[idx].sum(1) - s0[idx].sum(1) / n0[idx].sum(1)
    b = b[np.isfinite(b)]
    return d, float(b.std(ddof=1)) if b.size > 10 else np.nan


def bh(ps, q):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); m = len(ps)
    k = max([j + 1 for j, i in enumerate(o) if ps[i] <= q * (j + 1) / max(m, 1)] or [0])
    nom = [False] * m
    for i in o[:k]: nom[i] = True
    return nom


# ---------------------------------------------------------------- mitad A: explorar todo
def explorar(A: pd.DataFrame, spec: dict, rasgos: list) -> dict:
    """Todas las celdas de 1 y 2 rasgos y el modelo aditivo, sólo con A. Devuelve el landscape y las hipótesis a congelar."""
    y = A[spec["desenlace"]].to_numpy(float); n_all = len(y); mu_all = float(y.mean()) if n_all else 0.0
    sgn = spec["direccion"]; C = {r: cortes(A, r, spec["cortes_fijos"]) for r in rasgos}
    E = np.column_stack([estrato(A, r, C[r]) for r in rasgos]) if rasgos else np.zeros((n_all, 0), int)
    celdas = []

    def celda(rs, ss, m):
        n = int(m.sum())
        if n < 2: return
        v = y[m]; mu = float(v.mean()); sd = float(v.std(ddof=1)) if n > 1 else np.nan
        t = (mu - spec["nulo"]) / (sd / np.sqrt(n)) if sd and sd > 0 else 0.0
        celdas.append(dict(rasgos=list(rs), estratos=list(ss), n=n, media=mu, t=float(t)))

    for a, r in enumerate(rasgos):
        for s in (0, 1, 2): celda([r], [s], E[:, a] == s)
    if spec["pares"]:
        for a in range(len(rasgos)):
            for b in range(a + 1, len(rasgos)):
                ca = E[:, a] * 3 + E[:, b]; ok = (E[:, a] >= 0) & (E[:, b] >= 0)
                for s1 in (0, 1, 2):
                    for s2 in (0, 1, 2): celda([rasgos[a], rasgos[b]], [s1, s2], ok & (ca == s1 * 3 + s2))
    # elegibles: n mínimo, más allá del umbral económico en la dirección declarada (o en cualquiera si direccion = 0)
    def orient(c): return sgn if sgn else (1 if c["media"] >= spec["nulo"] else -1)
    eleg = [dict(c, signo=orient(c)) for c in celdas if c["n"] >= spec["min_n"]
            and orient(c) * (c["media"] - spec["nulo"]) >= spec["umbral_economico"] and orient(c) * c["t"] > 0]
    hip, usados = [], set()
    for c in sorted(eleg, key=lambda c: -abs(c["t"])):
        if usados & set(c["rasgos"]): continue                                   # rasgos distintos: k hipótesis no redundantes
        hip.append(dict(tipo="celda", rasgos=c["rasgos"], estratos=c["estratos"], signo=c["signo"], a=dict(n=c["n"], media=c["media"], t=c["t"])))
        usados |= set(c["rasgos"])
        if len(hip) == spec["k"]: break
    # modelo aditivo encogido: efecto de cada estrato respecto de la media de A, con peso n/(n + n0)
    ef = {}
    for a, r in enumerate(rasgos):
        ef[r] = [float((y[E[:, a] == s].mean() - mu_all) * (E[:, a] == s).sum() / ((E[:, a] == s).sum() + spec["encogimiento"]))
                 if (E[:, a] == s).any() else 0.0 for s in (0, 1, 2)]
    sc = puntaje(A, rasgos, C, ef)
    cs = {i: tuple(float(x) for x in np.quantile(sc[A.inst.to_numpy() == i], [1 / 3, 2 / 3])) for i in A.inst.unique()} if n_all else {}
    g = _tercil_puntaje(A, sc, cs); d_a = float(y[g == 2].mean() - y[g == 0].mean()) if (g == 2).any() and (g == 0).any() else 0.0
    modelo = dict(tipo="modelo", rasgos=list(rasgos), efectos=ef, cortes_puntaje=cs, signo=sgn if sgn else (1 if d_a >= 0 else -1),
                  a=dict(dif_alto_bajo=d_a, n=n_all))
    return dict(cortes=C, n_celdas=len(celdas), celdas=celdas, hipotesis=hip + [modelo], media_a=mu_all, n_a=n_all)


def puntaje(T, rasgos, C, ef):
    s = np.zeros(len(T))
    for r in rasgos:
        e = estrato(T, r, C[r]); w = np.array(ef[r] + [0.0])                  # índice −1 (sin dato) → 0
        s += w[e]
    return s


def _tercil_puntaje(T, sc, cs):
    g = np.full(len(T), -1); ins = T.inst.to_numpy()
    for i, (c1, c2) in cs.items():
        m = ins == i; g[m] = (sc[m] > c1).astype(int) + (sc[m] > c2).astype(int)
    return g


def _mascara(T, h, C):
    m = np.ones(len(T), bool)
    for r, s in zip(h["rasgos"], h["estratos"]): m &= estrato(T, r, C[r]) == s
    return m


# ---------------------------------------------------------------- mitad B: probar sólo lo congelado
def evaluar(B: pd.DataFrame, ctrl: pd.DataFrame, congelado: dict, spec: dict) -> list:
    y = B[spec["desenlace"]].to_numpy(float); ses = _sesiones(B) if len(B) else np.array([], int); C = congelado["cortes"]; out = []
    for h in congelado["hipotesis"]:
        sg = h["signo"]
        if h["tipo"] == "celda":
            m = _mascara(B, h, C); mu, se = media_sesion(sg * y[m], ses[m], spec["n_boot"]); n = int(m.sum())
            est = mu - sg * spec["nulo"] if np.isfinite(mu) else np.nan
            ctl = None
            if len(ctrl):
                mc = _mascara(ctrl, h, C)
                if mc.sum() >= 30: ctl = float(sg * ctrl[spec["desenlace"]].to_numpy(float)[mc].mean())
            nombre = " ∧ ".join(f"{r}={s}" for r, s in zip(h["rasgos"], h["estratos"]))
        else:
            sc = puntaje(B, h["rasgos"], C, h["efectos"]); g = _tercil_puntaje(B, sc, h["cortes_puntaje"]); m = np.isin(g, (0, 2))
            est, se = dif_sesion(sg * y[m], ses[m], (g[m] == 2).astype(int), spec["n_boot"]); n = int(min((g == 2).sum(), (g == 0).sum()))
            mu = float(sg * y[g == 2].mean()) if (g == 2).any() else np.nan; ctl = None; nombre = "modelo aditivo: tercil alto − tercil bajo"
        p = float(1 - Z.cdf(est / se)) if se and np.isfinite(se) and se > 0 and np.isfinite(est) else 1.0
        out.append(dict(nombre=nombre, tipo=h["tipo"], signo=sg, n_b=n, estimacion=None if not np.isfinite(est) else float(est),
                        media_b=None if not np.isfinite(mu) else float(mu), se=None if not np.isfinite(se) else float(se),
                        ic90=None if not (se and np.isfinite(se) and np.isfinite(est)) else [float(est - 1.645 * se), float(est + 1.645 * se)],
                        p=p, control=ctl, a=h["a"], compuerta_ok=n >= spec["min_n_b"]))
    for r, nom in zip(out, bh([r["p"] if r["compuerta_ok"] else 1.0 for r in out], spec["q"])): r["nominada"] = nom
    return out


# ---------------------------------------------------------------- orquestación
def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def partir(spec, T):
    R = T[T.placebo == 0].reset_index(drop=True); K = T[T.placebo == 1].reset_index(drop=True)
    mr, mk = mitad(R.fecha, spec["familia"]), mitad(K.fecha, spec["familia"]) if len(K) else np.array([], int)
    return R[mr == 0].reset_index(drop=True), R[mr == 1].reset_index(drop=True), K[mk == 1].reset_index(drop=True) if len(K) else K


def usos_previos(spec, raiz: Path = DIR) -> list:
    f = raiz / "USOS.jsonl"
    if not f.exists(): return []
    d0, d1 = spec["ventana"]; out = []
    for l in f.read_text(encoding="utf-8").splitlines():
        u = json.loads(l)
        if u["familia"] == spec["familia"] and not (u["ventana"][1] < d0 or u["ventana"][0] > d1): out.append(u)
    return out


def correr(spec: dict, T: pd.DataFrame, raiz: Path = DIR, registro: Path | None = ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl",
           ensayo: bool = False) -> dict:
    """Corre el experimento completo. `ensayo=True` (calibración, tests) no escribe nada ni consume B."""
    spec = especificacion(spec); err = validar(spec, T)
    if err: raise ValueError("especificación o tabla inválidas: " + "; ".join(err))
    if not ensayo and usos_previos(spec, raiz):
        raise ValueError(f"la mitad B de la familia {spec['familia']} en esta ventana ya se usó ({usos_previos(spec, raiz)[0]['nombre']}): "
                         "una sola prueba por familia y ventana; nuevas ideas esperan datos nuevos o van a la réplica")
    rasgos = rasgos_de(spec, T); A, B, K = partir(spec, T)
    ex = explorar(A, spec, rasgos)
    congelado = dict(nombre=spec["nombre"], cortes=ex["cortes"], hipotesis=ex["hipotesis"], rasgos=rasgos, tabla_sha=hashlib.sha256(pd.util.hash_pandas_object(T, index=False).to_numpy().tobytes()).hexdigest())
    congelado["sha"] = _sha(congelado); carpeta = raiz / spec["nombre"]
    if not ensayo:                                                           # se escribe ANTES de mirar B
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "HIPOTESIS_CONGELADAS.json").write_text(json.dumps(congelado, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        if registro is not None:
            from edgelab.funnel.multiplicity import TrialRegistry
            g = TrialRegistry(registro)
            g.ensure(f"banco/{spec['nombre']}/A", spec["familia"], ex["n_celdas"] + 1, "banco de eventos, mitad A: exploración, no confirmatoria")
            g.ensure(f"banco/{spec['nombre']}/B", spec["familia"], len(ex["hipotesis"]), "banco de eventos, mitad B: pruebas congeladas, BH q 0,10")
    res = evaluar(B, K, congelado, spec)
    out = dict(experimento=spec["nombre"], familia=spec["familia"], etapa=spec["etapa"], ventana=spec["ventana"], desenlace=spec["desenlace"],
               direccion=spec["direccion"], umbral_economico=spec["umbral_economico"], rasgos=rasgos, n_a=len(A), n_b=len(B), n_control_b=len(K),
               sesiones_a=int(A[["inst", "fecha"]].drop_duplicates().shape[0]), sesiones_b=int(B[["inst", "fecha"]].drop_duplicates().shape[0]),
               celdas_exploradas=ex["n_celdas"], pruebas_en_b=len(res), hipotesis_sha=congelado["sha"], resultados=res,
               nominadas=[r["nombre"] for r in res if r["nominada"]],
               mejores_a=sorted(ex["celdas"], key=lambda c: -abs(c["t"]))[:20])
    if not ensayo:
        (carpeta / "RESULTADO.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        (carpeta / "RECOMENDACIONES.md").write_text(recomendaciones(out, spec), encoding="utf-8")
        with open(raiz / "USOS.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(nombre=spec["nombre"], familia=spec["familia"], ventana=spec["ventana"], hipotesis_sha=congelado["sha"],
                                    pruebas=len(res), nominadas=out["nominadas"]), ensure_ascii=False) + "\n")
    return out


def recomendaciones(out: dict, spec: dict) -> str:
    from edgelab.research import recomendador as RC
    items = []
    for r in out["resultados"]:
        se = r["se"]
        items.append(dict(nombre=r["nombre"], diferencia=r["estimacion"], ic90=r["ic90"], se=se, mde80=2.49 * se if se else None,
                          nominada=r["nominada"], n_min=r["n_b"], compuerta_ok=r["compuerta_ok"], media_a=r["media_b"], signo_esperado=1,
                          control_diferencia=None if r["control"] is None or r["media_b"] is None else r["media_b"] - r["control"],
                          sugerencia=("Réplica congelada de esta celda (mismos cortes de A) en la ventana de réplica de la familia; si "
                                      "sobrevive, P&L con ejecución fija." if r["tipo"] == "celda" else
                                      "El conjunto de rasgos ordena el desenlace: mirar qué rasgos pesan en el modelo y replicar el puntaje congelado.")))
    return RC.markdown(f"Recomendaciones — banco de eventos: {out['experimento']}", RC.recomendar(items),
                       f"docs/research/banco_eventos/{out['experimento']}/RESULTADO.json")


def calibrar(spec: dict, T: pd.DataFrame, n: int = 20, seed: int = 0) -> dict:
    """Tasa de falsos del MÉTODO sobre esta tabla: permuta el desenlace dentro de (activo, mes) entre eventos reales (rompe toda
    relación con los rasgos y conserva la estructura), lo centra en el nulo y cuenta corridas con al menos una nominada (error de
    familia). Con BH bajo el nulo completo debe quedar cerca de q; el preflight bloquea por encima de 2q."""
    spec = especificacion(spec); spec["n_boot"] = min(spec["n_boot"], 500); rng = np.random.default_rng(seed); falsas = 0
    R = T[T.placebo == 0].copy(); K = T[T.placebo == 1]; grupo = R.inst.astype(str) + (R.fecha // 100).astype(str)
    for _ in range(n):
        y = R[spec["desenlace"]].to_numpy(float).copy()
        for idx in R.groupby(grupo).indices.values(): y[idx] = y[rng.permutation(idx)]
        y = y - y.mean() + spec["nulo"]                                       # el nulo exacto: mide el error del método, no la media del evento
        P = pd.concat([R.assign(**{spec["desenlace"]: y}), K], ignore_index=True)
        falsas += bool(correr(spec, P, ensayo=True)["nominadas"])
    from math import comb
    lim = 2 * spec["q"]; p_exceso = sum(comb(n, j) * lim ** j * (1 - lim) ** (n - j) for j in range(falsas, n + 1))
    # bloquea sólo con evidencia de que la tasa supera 2q (binomial, 5 %): con 20–40 permutaciones la proporción sola es muy ruidosa
    return dict(corridas=n, con_alguna_nominada=falsas, tasa=falsas / n, p_tasa_mayor_2q=float(p_exceso), ok=p_exceso >= 0.05)


def preflight(spec: dict, T: pd.DataFrame, n_calibracion: int = 40) -> dict:
    """Todo lo que se chequea antes de correr con datos reales: contrato, partición con muestra en las dos mitades, estratos no
    degenerados (aviso) y calibración contra permutaciones (bloquea si la tasa de falsos supera 2q)."""
    spec = especificacion(spec); err = validar(spec, T)
    if err: return dict(ok=False, errores=err)
    A, B, _ = partir(spec, T); avisos = []
    sa, sb = A[["inst", "fecha"]].drop_duplicates().shape[0], B[["inst", "fecha"]].drop_duplicates().shape[0]
    if min(sa, sb) < 20: err.append(f"pocas sesiones por mitad (A {sa}, B {sb} < 20)")
    for r in rasgos_de(spec, T):
        c = cortes(A, r, spec["cortes_fijos"]); e = estrato(A, r, c); e = e[e >= 0]
        if e.size and min((e == k).mean() for k in (0, 1, 2)) < 0.10: avisos.append(f"{r}: algún estrato con < 10 % de A")
    cal = calibrar(spec, T, n_calibracion) if not err else None
    if cal and not cal["ok"]: err.append(f"calibración: {cal['con_alguna_nominada']}/{cal['corridas']} permutaciones con nominadas (tasa > 2q, p {cal['p_tasa_mayor_2q']:.3f})")
    return dict(ok=not err, errores=err, avisos=avisos, sesiones_a=sa, sesiones_b=sb, calibracion=cal)


PLANTILLA = dict(nombre="FAMILIA_idea_20261110", familia="FAMILIA", linaje="FAMILIA_MADRE", etapa="EF2", generador="hft_ruptura",
                 tabla="docs/research/.../tabla.csv", ventana=[20250701, 20260331], desenlace="rompe",
                 columnas_desenlace=["rompe", "rompe_media", "rompe_doble", "t_res_s", "avance15_x"], direccion=1, nulo=0.0,
                 umbral_economico=0.08, k=3, q=0.10, min_n=100, min_n_b=60, pares=True, rasgos="todos", cortes_fijos={},
                 justificacion_economica="por qué el mercado pagaría esto", como_refutar="qué resultado lo mataría", habilitada=True)
