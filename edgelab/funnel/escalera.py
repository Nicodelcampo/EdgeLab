"""Escalera de promoción para estudios de evento y reglas con P&L por operación (auditoría del embudo, 2026-10-22).

Por qué existe. El runner del embudo sólo cubre matrices señal x (SL, TP); todo lo que se investigó en la práctica (impulsos,
ORB, escalonadas, reglas vistas en el visor) se midió con scripts sueltos, sin contador global ni una regla de decisión común.
Y el ciclo autónomo decide con Holm (error familiar) al nivel que le deja el alpha-investing, que tras 8 campañas quedó en
riqueza 0,0025: ya no puede descubrir nada aunque exista. Las dos cosas fallan en sentidos opuestos: los scripts sueltos no
cuentan lo probado (sobreajuste) y el autopilot exige tanto que descarta lo que podría funcionar (error de tipo II).

Diseño, en dos niveles, como el descubrimiento + réplica de la genómica (y Harvey-Liu-Zhu para finanzas):
  1. TAMIZ masivo sobre la muestra de descubrimiento: FDR (Benjamini-Hochberg o Storey adaptativo) a q = 0,10 dentro de la
     campaña. Controla la FRACCIÓN de nominaciones falsas, no la chance de una sola, así que escala a miles de pruebas sin
     matar la potencia. Nominar no afirma nada: sólo da derecho a gastar una réplica. Todo lo probado va al contador global.
  2. CONFIRMACIÓN en muestra no mirada: pocas pruebas (<= 3 por campaña), cada una con nivel asignado por LORD++ (FDR en línea,
     Javanmard-Montanari 2018; Ramdas et al. 2017), que no se muere como el alpha-investing cuando hay rachas sin hallazgos.
     La réplica, el holdout y el paper se siguen con e-procesos (`secuencial.py`), válidos aunque se mire cada semana.
  3. Tres salidas posibles por candidata, no dos: CONFIRMADA, REFUTADA (con evidencia: la cota optimista no llega a lo útil) y
     SIN_POTENCIA (viva: el informe dice cuántas operaciones más hacen falta). Un nulo sin potencia no mata (ATJ-18, Harris 2016).
  4. Realismo económico antes de abrir el holdout: costos canónicos (`edgelab/costos.py`), estrés adverso, concentración, y el
     efecto ESPERADO fuera de muestra con recorte por selección (DSR de Bailey-López de Prado con N_eff; recorte de Sharpe de
     Harvey-Liu). Abrir el holdout sólo si con el n que va a dar hay potencia para ver el efecto recortado.

Nada de este módulo otorga estados G (contrato G0-G5): produce el nivel del embudo y la evidencia que G2-G4 piden.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import NormalDist

import numpy as np

_N = NormalDist()
Q_TAMIZ = 0.10
ALFA_CONFIRMACION = 0.05
ESTADOS = ("DESCARTADA_INTEGRIDAD", "REFUTADA", "SIN_POTENCIA", "NOMINADA", "CONFIRMADA_REPLICA", "LISTA_PARA_HOLDOUT")


# ----------------------------------------------------------------------------- 1. tamiz masivo (FDR dentro de la campaña)
def tamiz_fdr(pvals, q: float = Q_TAMIZ, metodo: str = "storey", lam: float = 0.5) -> dict:
    """Benjamini-Hochberg (o Storey: BH con pi0 estimado, más potente cuando hay muchos efectos reales). Válido con independencia
    o dependencia positiva (PRDS); 'by' (Benjamini-Yekutieli) para dependencia arbitraria. Devuelve índices nominados y q-valores."""
    p = np.asarray(pvals, float)
    if p.ndim != 1 or not len(p) or np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("p-valores finitos en [0,1]; las pruebas no evaluables se cuentan con p=1, no se omiten")
    m = len(p); pi0 = 1.0
    if metodo == "storey":
        pi0 = min(1.0, (np.sum(p > lam) + 1) / ((1 - lam) * m))
    elif metodo == "by":
        pi0 = sum(1.0 / i for i in range(1, m + 1))
    elif metodo != "bh":
        raise ValueError("metodo: bh | storey | by")
    o = np.argsort(p, kind="stable"); ps = p[o] * m * pi0 / np.arange(1, m + 1)
    qv = np.minimum.accumulate(ps[::-1])[::-1].clip(max=1.0)
    qvals = np.empty(m); qvals[o] = qv
    return dict(nominadas=sorted(int(i) for i in np.flatnonzero(qvals <= q)), q_valores=qvals.tolist(), pi0=float(pi0), q=q, metodo=metodo, m=m)


# ----------------------------------------------------------------------------- 2. confirmación: FDR en línea (LORD++)
def _gamma_jm(j: int) -> float:
    """Secuencia de Javanmard-Montanari (suma exactamente 1 con la constante 0,07720838): pensada para miles de pruebas."""
    return 0.07720838 * math.log(max(j, 2)) / (j * math.exp(math.sqrt(math.log(j)))) if j >= 1 else 0.0


_ZETA_16 = 2.2857491                       # zeta(1,6)


def _gamma_finita(j: int) -> float:
    """j^-1,6 / zeta(1,6): suma 1, más peso en las primeras pruebas. Para un proyecto con decenas o cientos de confirmaciones."""
    return j ** -1.6 / _ZETA_16 if j >= 1 else 0.0


GAMMAS = {"finita": _gamma_finita, "javanmard_montanari": _gamma_jm}


@dataclass
class LordPP:
    """LORD++ (Ramdas et al. 2017, sobre Javanmard-Montanari 2018): controla el FDR a nivel `alfa` sobre la secuencia de TODAS las
    confirmaciones (réplicas) de la historia del proyecto. El nivel de la prueba t depende de cuándo hubo descubrimientos previos;
    tras una racha sin hallazgos decae lento (gamma ~ log j / j·e^sqrt(log j)) en vez de agotarse. Estado serializable (to_dict)."""
    alfa: float = ALFA_CONFIRMACION
    w0: float = ALFA_CONFIRMACION / 2
    t: int = 0
    rechazos: list = field(default_factory=list)       # índices t (1-based) de los descubrimientos
    historia: list = field(default_factory=list)
    gamma: str = "finita"                               # cualquier secuencia no negativa que sume <= 1 es válida; se fija ANTES de la primera prueba

    def nivel(self) -> float:
        t = self.t + 1; g = GAMMAS[self.gamma]
        a = g(t) * self.w0
        if self.rechazos:
            a += (self.alfa - self.w0) * g(t - self.rechazos[0]) + self.alfa * sum(g(t - r) for r in self.rechazos[1:])
        return a

    def probar(self, p: float, etiqueta: str = "") -> dict:
        if not 0 <= p <= 1: raise ValueError("p fuera de [0,1]")
        a = self.nivel(); self.t += 1; ok = p <= a
        if ok: self.rechazos.append(self.t)
        r = dict(t=self.t, etiqueta=etiqueta, p=p, nivel=a, rechazo=ok); self.historia.append(r); return r

    def to_dict(self) -> dict:
        return dict(alfa=self.alfa, w0=self.w0, t=self.t, rechazos=list(self.rechazos), historia=list(self.historia), gamma=self.gamma, metodo="LORD++")

    @staticmethod
    def from_dict(d: dict) -> "LordPP":
        return LordPP(d["alfa"], d["w0"], d["t"], list(d["rechazos"]), list(d.get("historia", [])), d.get("gamma", "finita"))


# ----------------------------------------------------------------------------- 3. inferencia por operación, agrupada por sesión
def resumen_sesiones(netos, sesiones, n_boot: int = 4000, seed: int = 20261022, confianza: float = 0.90) -> dict:
    """Media neta por operación con IC bootstrap remuestreando SESIONES enteras (miles de operaciones en pocas sesiones no son
    miles de apuestas independientes: ATJ-11). p unilateral de H0: media <= 0 por bootstrap centrado. Con < 160 sesiones el IC es
    orientativo (el PrimaryCI estudentizado del contrato G2 exige 160)."""
    x = np.asarray(netos, float); s = np.asarray(sesiones)
    if x.ndim != 1 or len(x) != len(s) or not len(x) or not np.isfinite(x).all():
        raise ValueError("netos y sesiones alineados, finitos y no vacíos")
    u, inv = np.unique(s, return_inverse=True); tot = np.bincount(inv, weights=x); cnt = np.bincount(inv).astype(float)
    k = len(u); obs = float(x.mean()); rng = np.random.default_rng(seed)
    pick = rng.integers(0, k, (n_boot, k)); T = tot[pick].sum(1); C = cnt[pick].sum(1); mb = T / C
    cen = mb - obs                                                     # distribución nula centrada
    a = (1 - confianza) / 2
    sd_ses = float(np.std(tot - obs * cnt, ddof=1)) if k > 1 else float("nan")   # dispersión del aporte por sesión (influencia)
    se = float(np.std(mb, ddof=1))
    return dict(n_ops=int(len(x)), n_sesiones=int(k), ops_por_sesion=float(len(x) / k), media=obs, se=se,
                ic=[float(np.quantile(mb, a)), float(np.quantile(mb, 1 - a))], confianza=confianza,
                p_unilateral=float((1 + np.sum(cen >= obs)) / (n_boot + 1)), sd_por_op=float(np.std(x, ddof=1)) if len(x) > 1 else float("nan"),
                sd_aporte_sesion=sd_ses, ic_orientativo=bool(k < 160), metodo="bootstrap por sesiones (iid de sesiones)")


def mde(se: float, alfa: float = ALFA_CONFIRMACION, potencia: float = 0.8) -> float:
    """Efecto mínimo detectable (unilateral) con este error estándar."""
    return (_N.inv_cdf(1 - alfa) + _N.inv_cdf(potencia)) * se


def ops_necesarias(efecto: float, se_actual: float, n_actual: int, alfa: float = ALFA_CONFIRMACION, potencia: float = 0.8) -> int | None:
    """Operaciones para detectar `efecto` con la dispersión observada (se ~ 1/sqrt(n), conservando la agrupación por sesión)."""
    if efecto <= 0 or not math.isfinite(se_actual) or se_actual <= 0: return None
    z = _N.inv_cdf(1 - alfa) + _N.inv_cdf(potencia)
    return int(math.ceil(n_actual * (z * se_actual / efecto) ** 2))


def potencia(efecto: float, se: float, alfa: float = ALFA_CONFIRMACION) -> float:
    if not math.isfinite(se) or se <= 0: return float("nan")
    return float(1 - _N.cdf(_N.inv_cdf(1 - alfa) - efecto / se))


# ----------------------------------------------------------------------------- 4. recorte por selección
def n_efectivo(matriz) -> float:
    """Número efectivo de pruebas a partir de la correlación de sus P&L (Li y Ji 2005, sobre autovalores): variantes casi iguales
    no cuentan como pruebas independientes. matriz: observaciones (p. ej. días) x pruebas."""
    M = np.asarray(matriz, float)
    if M.ndim != 2 or M.shape[1] < 2: return float(M.shape[1] if M.ndim == 2 else 1)
    M = M[:, np.nanstd(M, 0) > 0]
    if M.shape[1] < 2: return float(M.shape[1])
    ev = np.clip(np.linalg.eigvalsh(np.corrcoef(np.nan_to_num(M), rowvar=False)), 0, None)
    return float(sum((e >= 1) + (e - math.floor(e)) for e in ev))


def recorte_t(t: float, n_pruebas: float) -> dict:
    """Recorte de Harvey-Liu (2015) con Bonferroni sobre N_eff: el t observado (agrupado por sesión) se lleva al t que tendría la
    misma p ajustada. No lineal: castiga mucho a los marginales y poco a los muy fuertes. `conservado` = fracción del efecto que
    se espera ver fuera de muestra por sesgo de selección (no incluye decaimiento del mercado: McLean-Pontiff ~26 % adicional)."""
    if not t > 0: return dict(t=t, t_ajustado=0.0, conservado=0.0, p_ajustada=1.0, metodo="Harvey-Liu, Bonferroni sobre N_eff")
    p = 1 - _N.cdf(t); pa = min(1.0, p * max(n_pruebas, 1.0))
    ta = max(_N.inv_cdf(1 - pa), 0.0) if pa < 1 else 0.0
    return dict(t=t, t_ajustado=ta, p_ajustada=pa, conservado=ta / t, metodo="Harvey-Liu, Bonferroni sobre N_eff")


def dsr(sr_por_op: float, n_ops: int, n_pruebas: float, skew: float = 0.0, kurt: float = 3.0) -> float:
    from edgelab.research.g2 import deflated_sharpe
    return float(deflated_sharpe(sr_por_op, n_ops, max(n_pruebas, 1.0), skew, kurt))


# ----------------------------------------------------------------------------- 5. realismo económico
def economia(netos_base, netos_adverso=None, sesiones=None, periodos=None) -> dict:
    """G1/G3 sobre P&L NETO por operación (costos canónicos ya aplicados). Duros: neto base > 0; sin las 5 mejores > 0; ningún
    período > 80 % del total; adverso > -0,5 x base. Blando: margen < 1 tick (la decisión depende del modelo de costos)."""
    x = np.asarray(netos_base, float); tot = float(x.sum()); r = dict(neto_base_por_op=float(x.mean()), neto_total=tot)
    r["sin_top5_por_op"] = float(np.sort(x)[:-5].mean()) if len(x) > 5 else float("nan")
    duros = dict(neto_base_positivo=bool(x.mean() > 0), sin_top5_positivo=bool(len(x) > 5 and np.sort(x)[:-5].sum() > 0))
    if periodos is not None:
        per = {}
        for k, v in zip(periodos, x): per[k] = per.get(k, 0.0) + float(v)
        r["por_periodo"] = per; r["periodos_positivos"] = f"{sum(v > 0 for v in per.values())}/{len(per)}"
        duros["ningun_periodo_80pct"] = bool(tot > 0 and max(per.values()) <= 0.8 * tot)
    if netos_adverso is not None:
        a = float(np.mean(netos_adverso)); r["neto_adverso_por_op"] = a
        duros["sin_colapso_adverso"] = bool(a > -0.5 * x.mean()) if x.mean() > 0 else False
    r["duros"] = duros; r["pasa"] = all(duros.values())
    return r


# ----------------------------------------------------------------------------- 6. veredicto
@dataclass
class Veredicto:
    estado: str
    motivos: list
    siguiente_paso: str
    numeros: dict

    def to_dict(self) -> dict:
        return dict(estado=self.estado, motivos=self.motivos, siguiente_paso=self.siguiente_paso, numeros=self.numeros,
                    asserts_edge=False, otorga_estado_G=False)


def evaluar(*, descubrimiento: dict, nominada: bool, n_pruebas_familia: float, efecto_util: float = 0.0,
            replica: dict | None = None, alfa_replica: float | None = None, economico: dict | None = None,
            n_esperado_holdout: int | None = None, integridad: list | None = None) -> Veredicto:
    """descubrimiento/replica: salidas de `resumen_sesiones` sobre P&L NETO por operación. nominada: si pasó `tamiz_fdr` en su
    campaña. n_pruebas_familia: N_eff cobrado (contador de la familia). efecto_util: neto mínimo por operación que la vuelve útil
    (0 = cualquier positivo). alfa_replica: nivel asignado por LORD++. n_esperado_holdout: operaciones que dará el holdout."""
    if integridad:
        return Veredicto("DESCARTADA_INTEGRIDAD", list(integridad), "corregir integridad (costos, entrada, look-ahead) y volver a medir: no hay lectura estadística posible", {})
    d = descubrimiento; sr = d["media"] / d["sd_por_op"] if d["sd_por_op"] and d["sd_por_op"] > 0 else 0.0
    rc = recorte_t(d["media"] / d["se"] if d["se"] > 0 else 0.0, n_pruebas_familia); esperado = max(0.0, rc["conservado"] * d["media"])
    num = dict(descubrimiento=d, recorte=rc, efecto_esperado_fuera_de_muestra=esperado, dsr=dsr(sr, d["n_ops"], n_pruebas_familia),
               n_pruebas_familia=n_pruebas_familia, mde_descubrimiento=mde(d["se"]))
    if economico is not None: num["economico"] = economico            # se informa siempre, aunque el estado se decida antes
    umbral = max(efecto_util, 0.0)
    if d["ic"][1] < umbral:
        return Veredicto("REFUTADA", [f"la cota optimista del IC ({d['ic'][1]:.4g}) no llega al efecto útil ({umbral:.4g})"],
                         "archivar con su alcance exacto (regla, población, costos); no reintentar la misma hipótesis sin campaña nueva", num)
    if replica is None:
        if not nominada:
            faltan = ops_necesarias(max(d["media"], mde(d["se"]) / 2), d["se"], d["n_ops"])
            return Veredicto("SIN_POTENCIA", [f"no pasa el tamiz FDR de su campaña, pero el IC [{d['ic'][0]:.4g}, {d['ic'][1]:.4g}] no excluye lo útil",
                                              f"MDE actual {num['mde_descubrimiento']:.4g} por operación"],
                             f"queda viva en reserva; con ~{faltan} operaciones se distinguiría el efecto observado del cero" if faltan else "queda viva en reserva", num)
        return Veredicto("NOMINADA", ["pasó el tamiz FDR de su campaña (nominación, no evidencia)"],
                         f"pre-registrar la regla exacta y replicar en muestra no mirada; para ver el efecto recortado ({esperado:.4g}) hacen falta "
                         f"~{ops_necesarias(esperado, d['se'], d['n_ops']) or 'inf'} operaciones con la dispersión actual", num)
    r = replica; num["replica"] = r; a = alfa_replica if alfa_replica is not None else ALFA_CONFIRMACION; num["alfa_replica"] = a
    if r["p_unilateral"] <= a and r["media"] > 0:
        est, mot = "CONFIRMADA_REPLICA", [f"réplica p = {r['p_unilateral']:.4g} <= nivel LORD++ {a:.4g}"]
    elif r["ic"][1] < umbral:
        return Veredicto("REFUTADA", [f"en la réplica la cota optimista ({r['ic'][1]:.4g}) no llega a lo útil ({umbral:.4g})"],
                         "archivar: la réplica limpia la refuta", num)
    else:
        faltan = ops_necesarias(esperado or r["media"], r["se"], r["n_ops"], a)
        return Veredicto("SIN_POTENCIA", [f"réplica no concluyente (p = {r['p_unilateral']:.4g}, potencia para el efecto esperado "
                                          f"{potencia(esperado, r['se'], a):.2f})"],
                         f"seguir la réplica con el monitor secuencial (secuencial.MonitorCandidato) hasta ~{faltan} operaciones; no abrir el holdout todavía", num)
    if economico is None:
        return Veredicto(est, mot + ["falta el chequeo económico (G1/G3)"], "correr `economia` con costos canónicos y escenario adverso", num)
    num["economico"] = economico
    if not economico["pasa"]:
        return Veredicto(est, mot + ["no pasa lo económico: " + ", ".join(k for k, v in economico["duros"].items() if not v)],
                         "nivel B: replica pero no es operable así; corregir forma (costos, frecuencia, salidas) o usarla como filtro", num)
    if n_esperado_holdout is not None:
        se_h = r["se"] * math.sqrt(r["n_ops"] / max(n_esperado_holdout, 1)); pot = potencia(esperado, se_h, ALFA_CONFIRMACION)
        num["potencia_holdout"] = pot
        if not pot >= 0.8:
            return Veredicto(est, mot + [f"con {n_esperado_holdout} operaciones el holdout tiene potencia {pot:.2f} para el efecto recortado"],
                             "esperar más datos sellados antes de la única apertura, o seguirlo como paper con el monitor secuencial", num)
    return Veredicto("LISTA_PARA_HOLDOUT", mot + ["económico OK", "potencia de holdout suficiente"],
                     "apertura única por protocolo (holdout_apertura) con la regla congelada; seguimiento secuencial", num)


# ----------------------------------------------------------------------------- 7. puente con el ciclo autónomo
def para_autopilot(pruebas: list) -> dict:
    """Formato `results_flat` que `edgelab.autopilot.analyze.records` ya entiende (no hay que tocar el autopilot para leerlo).
    pruebas: [{test, p, evaluable, effect}]; las de réplica deben llevar '/rep/' en el nombre (analyze exige rechazo en réplica)."""
    return dict(results_flat=[dict(test=t["test"], p=float(t["p"]) if t.get("p") is not None else None, evaluable=bool(t.get("evaluable", True)),
                                   diff=t.get("effect")) for t in pruebas], schema="escalera_embudo_v1")
