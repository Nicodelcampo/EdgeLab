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

import bisect
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

    def reservar(self, etiqueta: str = "") -> dict:
        """Consume el paso t AHORA con su nivel fijo, sin p todavía (decisión del 2026-10-24: el acta reserva su α antes de mirar).
        Mientras está pendiente cuenta como no rechazo para los pasos que siguen: sólo puede dejarles menos nivel, nunca más
        (LORD++ asincrónico, Zrnic, Ramdas y Jordan 2021), así que el FDR sigue controlado."""
        a = self.nivel(); self.t += 1
        r = dict(t=self.t, etiqueta=etiqueta, p=None, nivel=a, rechazo=None, reservada=True); self.historia.append(r); return r

    def resolver(self, t: int, p: float) -> dict:
        """Decide el paso reservado t al nivel que se fijó al reservarlo."""
        if not 0 <= p <= 1: raise ValueError("p fuera de [0,1]")
        h = next((x for x in self.historia if x["t"] == t), None)
        if h is None or not h.get("reservada"): raise ValueError(f"el paso {t} no es una reserva")
        if h["rechazo"] is not None: return h                                          # ya resuelta: idempotente
        h.update(p=p, rechazo=bool(p <= h["nivel"]))
        if h["rechazo"]: bisect.insort(self.rechazos, t)
        return h

    def to_dict(self) -> dict:
        return dict(alfa=self.alfa, w0=self.w0, t=self.t, rechazos=list(self.rechazos), historia=list(self.historia), gamma=self.gamma, metodo="LORD++")

    @staticmethod
    def from_dict(d: dict) -> "LordPP":
        return LordPP(d["alfa"], d["w0"], d["t"], list(d["rechazos"]), list(d.get("historia", [])), d.get("gamma", "finita"))



def decidir_lote(nivel: float, pruebas: list) -> dict:
    """La decisión de un lote a un nivel YA asignado (Simes para la familia, BH adentro). La usa `probar_lote` y el libro cuando
    resuelve un paso reservado por un acta (el nivel quedó fijo al escribirla). pruebas: [(nombre, p)]."""
    if not pruebas: return dict(nivel=nivel, p_simes=None, rechazo=False, confirmadas=[], m=0)
    ps = np.array([float(p) for _, p in pruebas]); m = len(ps); o = np.argsort(ps, kind="stable")
    if np.any((ps < 0) | (ps > 1)): raise ValueError("p fuera de [0,1]")
    p_simes = float(min(1.0, np.min(ps[o] * m / np.arange(1, m + 1)))); rech = bool(p_simes <= nivel); conf = []
    if rech:
        ok = np.flatnonzero(ps[o] <= nivel * np.arange(1, m + 1) / m)
        conf = [dict(test=pruebas[i][0], p=float(ps[i]), nivel=nivel) for i in o[:ok.max() + 1]] if len(ok) else []
    return dict(nivel=nivel, p_simes=p_simes, rechazo=rech, confirmadas=conf, m=m)


def probar_lote(L: "LordPP", pruebas: list, etiqueta: str = "") -> dict:
    """Un LOTE de réplicas simultáneas (las de una misma corrida) ocupa UN paso de LORD++ (Benjamini y Bogomolov 2014: primero
    se selecciona la familia, después se decide adentro). p de la familia = Simes (min_k p_(k)·m/k); si la familia rechaza al
    nivel alfa_t de LORD++, BH dentro del lote a ese mismo nivel. Con una sola prueba es idéntico a `L.probar`.
    Error que corrige (2026-10-23): pasar 80 réplicas de una corrida de a una por LORD++ gastaba el nivel en las primeras
    (0,011 la 1.ª, ~0 desde la 20.ª) y la decisión dependía del orden alfabético. pruebas: [(nombre, p)]."""
    if not pruebas: return dict(nivel=L.nivel(), p_simes=None, rechazo=False, confirmadas=[])
    d = decidir_lote(L.nivel(), pruebas)
    r = L.probar(d["p_simes"], etiqueta or f"lote de {d['m']}")
    return dict(d, t=r["t"])

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
    if n_boot * k <= _BLOQUE_BOOT:
        pick = rng.integers(0, k, (n_boot, k)); T = tot[pick].sum(1); C = cnt[pick].sum(1); mb = T / C
    else:                                                              # B grande (resolución, 2026-10-24): por bloques, memoria acotada
        mb = np.empty(n_boot); paso = max(1, _BLOQUE_BOOT // k)
        for a in range(0, n_boot, paso):
            pick = rng.integers(0, k, (min(paso, n_boot - a), k)); mb[a:a + len(pick)] = tot[pick].sum(1) / cnt[pick].sum(1)
    cen = mb - obs                                                     # distribución nula centrada
    a = (1 - confianza) / 2
    sd_ses = float(np.std(tot - obs * cnt, ddof=1)) if k > 1 else float("nan")   # dispersión del aporte por sesión (influencia)
    se = float(np.std(mb, ddof=1))
    return dict(n_ops=int(len(x)), n_sesiones=int(k), ops_por_sesion=float(len(x) / k), media=obs, se=se,
                ic=[float(np.quantile(mb, a)), float(np.quantile(mb, 1 - a))], confianza=confianza,
                p_unilateral=float((1 + np.sum(cen >= obs)) / (n_boot + 1)), sd_por_op=float(np.std(x, ddof=1)) if len(x) > 1 else float("nan"),
                sd_aporte_sesion=sd_ses, ic_orientativo=bool(k < 160), metodo="bootstrap por sesiones (iid de sesiones)")


# ----------------------------------------------------------------------------- 3b. resolución del p (falsos negativos, 2026-10-24)
# El p del bootstrap no baja de 1/(B+1). Con B = 2000 el piso es 5e-4, y el nivel de LORD++ de una familia con historia baja a
# 1e-5: rechazar era imposible por construcción y el «sin rechazo» se leía como evidencia (U1: 80 réplicas a 2e-5 con p ≥ 5e-4).
# Regla: B >= POR_NIVEL / umbral (umbral = nivel / m, el más exigente de Simes/BH en un lote de m), hasta N_BOOT_MAX; si no
# alcanza, p analítico agrupado por sesión (t de Student con k-1 g.l. sobre los aportes por sesión). Nunca un «no rechaza» por
# resolución.
_BLOQUE_BOOT = 8_000_000                   # elementos de la matriz de sorteo por bloque (~64 MB en int64)
N_BOOT_BASE, N_BOOT_MAX, POR_NIVEL = 2000, 200_000, 10


def n_boot_para(nivel: float | None, m: int = 1, base: int = N_BOOT_BASE, tope: int = N_BOOT_MAX) -> int:
    """B necesario para resolver el umbral más exigente de un lote de m pruebas a `nivel` (>= POR_NIVEL réplicas por umbral)."""
    if nivel is None or not nivel > 0: return int(base)
    return int(min(tope, max(base, math.ceil(POR_NIVEL * max(int(m), 1) / nivel))))


def _betacf(a: float, b: float, x: float) -> float:
    """Fracción continua de la beta incompleta (Lentz modificado, Numerical Recipes). Sin scipy: el núcleo no suma dependencias."""
    tiny = 1e-300
    def _no_cero(v): return v if abs(v) > tiny else tiny
    c, d = 1.0, 1.0 / _no_cero(1.0 - (a + b) * x / (a + 1.0)); h = d
    for m in range(1, 500):
        m2 = 2 * m
        aa = m * (b - m) * x / ((a - 1 + m2) * (a + m2))
        d = 1.0 / _no_cero(1.0 + aa * d); c = _no_cero(1.0 + aa / c); h *= d * c
        aa = -(a + m) * (a + b + m) * x / ((a + m2) * (a + 1 + m2))
        d = 1.0 / _no_cero(1.0 + aa * d); c = _no_cero(1.0 + aa / c); de = d * c; h *= de
        if abs(de - 1.0) < 1e-15: break
    return h


def t_cola_superior(t: float, gl: float) -> float:
    """P(T > t) para una t de Student con `gl` grados de libertad (beta incompleta regularizada)."""
    if not math.isfinite(t): return 0.0 if t > 0 else 1.0
    x = gl / (gl + t * t); a, b = gl / 2.0, 0.5
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x) if 0 < x < 1 else None
    if lbt is None: ib = 0.0 if x <= 0 else 1.0
    elif x < (a + 1) / (a + b + 2): ib = math.exp(lbt) * _betacf(a, b, x) / a
    else: ib = 1.0 - math.exp(lbt) * _betacf(b, a, 1 - x) / b
    cola = 0.5 * ib                                                    # = P(|T| > |t|) / 2
    return float(cola if t > 0 else 1.0 - cola)


def p_sesiones_analitico(netos, sesiones) -> dict:
    """p unilateral (H0: media <= 0) agrupado por sesión: t = media / se_cluster, se con los aportes por sesión (CR1, k/(k-1)),
    referencia t de Student con k-1 g.l. Es la alternativa cuando el bootstrap no puede resolver el nivel."""
    x = np.asarray(netos, float); s = np.asarray(sesiones)
    u, inv = np.unique(s, return_inverse=True); tot = np.bincount(inv, weights=x); cnt = np.bincount(inv).astype(float)
    k = len(u); N = float(cnt.sum()); mu = float(tot.sum() / N)
    if k < 2: return dict(p=1.0, t=float("nan"), gl=0, metodo="analítico por sesión (sin g.l.)")
    e = tot - mu * cnt; se = math.sqrt(k / (k - 1) * float(np.sum(e * e))) / N
    t = mu / se if se > 0 else (math.inf if mu > 0 else -math.inf)
    return dict(p=t_cola_superior(t, k - 1), t=float(t), gl=k - 1, metodo="analítico por sesión (t de Student, k-1 g.l.)")


def resumen_resuelto(netos, sesiones, nivel: float | None = None, m: int = 1, n_boot: int = N_BOOT_BASE, seed: int = 20261022) -> dict:
    """`resumen_sesiones` con un p que puede resolver el umbral `nivel / m`: sube B (>= 10 por umbral, hasta N_BOOT_MAX) y, si no
    alcanza, usa el p analítico por sesión. Publica `n_boot`, `piso_p` y `metodo_p`. Sin nivel: igual que antes."""
    B = n_boot_para(nivel, m, base=n_boot)
    necesita = nivel is not None and nivel > 0 and POR_NIVEL * max(int(m), 1) / nivel > N_BOOT_MAX
    rs = resumen_sesiones(netos, sesiones, n_boot=B, seed=seed)
    rs.update(n_boot=B, piso_p=1.0 / (B + 1), metodo_p="bootstrap por sesiones")
    if necesita:
        an = p_sesiones_analitico(netos, sesiones)
        rs.update(p_bootstrap=rs["p_unilateral"], p_unilateral=an["p"], metodo_p=an["metodo"], t_sesiones=an["t"], piso_p=0.0)
    return rs


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


def n_efectivo_o_bruto(n_bruto: float, matriz=None) -> dict:
    """Número de pruebas a cobrar (2026-10-24, falsos negativos): Li-Ji sobre la matriz de P&L (observaciones x pruebas) cuando
    está disponible y cubre TODAS las pruebas contadas; si no, el bruto con aviso (nunca se extrapola Li-Ji de una muestra de
    columnas a un total mayor: el descuento quedaría sin respaldo). Nunca devuelve más que el bruto."""
    n_bruto = float(n_bruto)
    if matriz is None:
        return dict(n=n_bruto, bruto=n_bruto, metodo="bruto", aviso="sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)")
    M = np.asarray(matriz, float)
    if M.ndim != 2 or M.shape[1] != int(n_bruto):
        return dict(n=n_bruto, bruto=n_bruto, metodo="bruto",
                    aviso=f"matriz de P&L con {M.shape[1] if M.ndim == 2 else 0} columnas para {int(n_bruto)} pruebas: se cobra el bruto")
    ne = min(n_efectivo(M), n_bruto)
    return dict(n=float(max(ne, 1.0)), bruto=n_bruto, metodo="Li-Ji (autovalores de la correlación de P&L)", aviso=None)


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
    período VIEJO > 80 % del total; adverso > -0,5 x base. Blando: margen < 1 tick (la decisión depende del modelo de costos).
    Régimen (principio de Nico, 2026-10-22: «queremos edges actuales, aunque en el pasado no hayan funcionado»): si la ganancia
    se concentra en los períodos MÁS RECIENTES (el último cuarto, al menos uno; `periodos` deben ordenar cronológicamente) no
    se mata: se marca `regimen_reciente` y la confirmación tiene que salir de datos posteriores (réplica reciente o forward).
    Concentrada en un período viejo sigue siendo dura: un edge que sólo funcionó antes no es actual."""
    x = np.asarray(netos_base, float); tot = float(x.sum()); r = dict(neto_base_por_op=float(x.mean()), neto_total=tot)
    r["sin_top5_por_op"] = float(np.sort(x)[:-5].mean()) if len(x) > 5 else float("nan")
    duros = dict(neto_base_positivo=bool(x.mean() > 0), sin_top5_positivo=bool(len(x) > 5 and np.sort(x)[:-5].sum() > 0))
    if periodos is not None:
        per = {}
        for k, v in zip(periodos, x): per[k] = per.get(k, 0.0) + float(v)
        r["por_periodo"] = per; r["periodos_positivos"] = f"{sum(v > 0 for v in per.values())}/{len(per)}"
        orden = sorted(per); recientes = set(orden[-max(1, round(len(orden) / 4)):]); top = max(per, key=per.get)
        concentrado = bool(tot > 0 and per[top] > 0.8 * tot)
        r["regimen_reciente"] = bool(concentrado and top in recientes)
        duros["ningun_periodo_80pct"] = bool(tot > 0 and (not concentrado or r["regimen_reciente"]))
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
            n_esperado_holdout: int | None = None, integridad: list | None = None, pista_replicada: bool = False) -> Veredicto:
    """descubrimiento/replica: salidas de `resumen_sesiones` sobre P&L NETO por operación. nominada: si pasó `tamiz_fdr` en su
    campaña. n_pruebas_familia: N_eff cobrado (contador de la familia). efecto_util: neto mínimo por operación que la vuelve útil
    (0 = cualquier positivo). alfa_replica: nivel asignado por LORD++. n_esperado_holdout: operaciones que dará el holdout.
    pista_replicada: la celda NO fue nominada pero entró por «pistas a réplica» (ATJ-25): congelada entre las top-k de su campaña
    ANTES de la réplica, registrada en el contador y probada en lote con UN paso de LORD++ (`elegir_pistas_replica` +
    `probar_lote`). Esa réplica en datos no mirados es una confirmación válida a su nivel (2026-10-24, falsos negativos)."""
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
            sig = ("queda viva en reserva: entra a «pistas a réplica» (top-k de la campaña por cota inferior, congeladas, un paso de "
                   "LORD++ por lote en una ventana reciente no usada)")
            return Veredicto("SIN_POTENCIA", [f"no pasa el tamiz FDR de su campaña, pero el IC [{d['ic'][0]:.4g}, {d['ic'][1]:.4g}] no excluye lo útil",
                                              f"MDE actual {num['mde_descubrimiento']:.4g} por operación"],
                             sig + (f"; con ~{faltan} operaciones se distinguiría el efecto observado del cero" if faltan else ""), num)
        return Veredicto("NOMINADA", ["pasó el tamiz FDR de su campaña (nominación, no evidencia)"],
                         f"pre-registrar la regla exacta y replicar en muestra no mirada; para ver el efecto recortado ({esperado:.4g}) hacen falta "
                         f"~{ops_necesarias(esperado, d['se'], d['n_ops']) or 'inf'} operaciones con la dispersión actual", num)
    r = replica; num["replica"] = r; a = alfa_replica if alfa_replica is not None else ALFA_CONFIRMACION; num["alfa_replica"] = a
    num["via"] = "nominada_fdr" if nominada else ("pista_replicada" if pista_replicada else None)
    if not nominada and not pista_replicada:            # decisión del 2026-10-24: sin nominación FDR ni pista congelada, no hay confirmación
        return Veredicto("SIN_POTENCIA", ["no pasó el tamiz FDR (q 0,10) de su campaña ni entró como pista congelada a réplica: la réplica "
                                          "no puede confirmarla (docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md)"],
                         "queda viva en reserva: congelarla entre las top-k de su campaña y replicarla en lote (pistas a réplica, ATJ-25)", num)
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


# ----------------------------------------------------------------------------- 6b. pistas a réplica (ATJ-25, restaurada 2026-10-24)
K_PISTAS_REPLICA = 20


def elegir_pistas_replica(pistas: list, k: int = K_PISTAS_REPLICA, *, min_dif: int = 2, min_sesiones: int = 0,
                          ratio_mov_friccion: float = 0.0) -> list:
    """Las top-k pistas de una campaña que no nominó nada por FDR, para congelarlas y replicarlas en lote. Orden: cota inferior del
    IC90 por sesiones (desc), desempate por t de Romano-Wolf; NUNCA por P&L máximo. Distintas entre sí (difieren en >= `min_dif`
    perillas, también entre canales). Los filtros de relevancia son los de la selección pre-registrada. Sólo entran pistas con cota
    inferior del IC90 > 0 (2026-10-25): con Simes cada pista de más divide el nivel del lote, y una que ya cruza cero en el
    descubrimiento casi no puede confirmar; dejarla entrar le quita potencia a las buenas (EXPZ: 17 pistas con cota negativa)."""
    ok = [p for p in pistas if p.get("ic90") and float(p["ic90"][0]) > 0 and (p.get("media_neta") or 0) > 0 and (p.get("sesiones") or 0) >= min_sesiones
          and (p.get("ratio_mov_friccion") if p.get("ratio_mov_friccion") is not None else float("inf")) >= ratio_mov_friccion]
    ok = sorted(ok, key=lambda p: (-float(p["ic90"][0]), -float(p.get("t_rw") or 0.0)))
    out = []
    for p in ok:
        if any(sum(a != b for a, b in zip(p["celda"], q["celda"])) < min_dif for q in out): continue
        out.append(p)
        if len(out) >= k: break
    return out


def decidir_pistas(dec_lote: dict, replica: list, nombres: list) -> list:
    """Qué pistas pasan a nominadas tras el paso de LORD++ del lote: confirmadas por BH dentro del lote (al nivel del paso) Y con
    media neta > 0 en la réplica. Devuelve los índices (en el orden de `replica`)."""
    conf = {c["test"] for c in (dec_lote or {}).get("confirmadas", [])} if (dec_lote or {}).get("rechazo") else set()
    return [i for i, (n, r) in enumerate(zip(nombres, replica)) if n in conf and (r.get("media_neta") or 0) > 0]


def canasta_pistas(operaciones: dict, k: int, n_boot: int = 4000) -> dict:
    """Prueba AGREGADA de un lote de pistas (decisión de Nico, 2026-10-26, auditoría del filtro): la canasta igual-ponderada de las k
    pistas, P&L neto medio por pista y sesión, como UNA serie (bootstrap por sesiones). Detecta un edge repartido en muchas celdas vecinas
    débiles que la prueba pista por pista (umbral / k) no puede ver. `operaciones`: dict de listas con celda, ses, neto (REP)."""
    import pandas as pd
    o = pd.DataFrame(operaciones or {})
    if not len(o): return dict(n_sesiones=0)
    g = o.groupby(["ses", "celda"]).neto.sum().unstack().reindex(columns=range(k)).fillna(0.0).mean(axis=1)
    rs = resumen_sesiones(g.to_numpy(float), g.index.to_numpy(), n_boot=n_boot)
    return dict(n_sesiones=int(len(g)), media=float(g.mean()), ic90=rs["ic"], p=rs["p_unilateral"], n_boot=n_boot)


def veredicto_pistas(confirmadas: list, canasta: dict, dec_canasta: dict | None, media_desc: float, fraccion_efecto: float = 0.5,
                     potencia_min: float = 0.8) -> dict:
    """Veredicto del lote de pistas (2026-10-26). Antes: 0 confirmadas una por una = SIN_CANDIDATAS, aunque la potencia fuera del 1–2 %.
    Ahora, con la misma semántica que el OOS (decisión 2 del 2026-10-24: un nulo sin potencia no mata):
      CANASTA_CONFIRMADA   el paso de LORD++ de la canasta rechaza y su media > 0
      PISTAS_CONFIRMADAS   alguna pista individual confirmada (como antes)
      REFUTADA             la canasta tiene potencia >= potencia_min para fraccion_efecto x media del DESC y su IC90 entero es < 0
      SIN_RECHAZO          con potencia, sin confirmar ni estar en contra: viva (un efecto menor que el del DESC sigue posible)
      SIN_POTENCIA         sin potencia: viva. En los dos casos el próximo paso es el holdout de la canasta congelada."""
    if dec_canasta and dec_canasta.get("rechazo") and (canasta.get("media") or 0) > 0: return dict(veredicto="CANASTA_CONFIRMADA")
    if confirmadas: return dict(veredicto="PISTAS_CONFIRMADAS")
    ic = canasta.get("ic90")
    if not ic: return dict(veredicto="SIN_POTENCIA", motivo="canasta sin operaciones evaluables")
    se = (ic[1] - ic[0]) / (2 * 1.6448536); ef = fraccion_efecto * max(media_desc, 0.0)
    nivel = (dec_canasta or {}).get("nivel", ALFA_CONFIRMACION)
    pot = potencia(ef, se, nivel) if ef > 0 else 0.0
    if pot == pot and pot >= potencia_min and ic[1] < 0:
        return dict(veredicto="REFUTADA", potencia=pot, efecto=ef, motivo="canasta en contra con potencia")
    if pot == pot and pot >= potencia_min:
        return dict(veredicto="SIN_RECHAZO", potencia=pot, efecto=ef,
                    motivo=(f"con potencia para {fraccion_efecto:g} x el efecto del DESC: la canasta no lo alcanza (IC90 {ic}) pero no está en contra; "
                            "un efecto menor sigue posible: la familia sigue viva"))
    return dict(veredicto="SIN_POTENCIA", potencia=pot, efecto=ef,
                motivo="ni pistas ni canasta confirman y no hay potencia para decidir: la familia sigue viva")


# ----------------------------------------------------------------------------- 7. puente con el ciclo autónomo
def para_autopilot(pruebas: list) -> dict:
    """Formato `results_flat` que `edgelab.autopilot.analyze.records` ya entiende (no hay que tocar el autopilot para leerlo).
    pruebas: [{test, p, evaluable, effect}]; las de réplica deben llevar '/rep/' en el nombre (analyze exige rechazo en réplica)."""
    return dict(results_flat=[dict(test=t["test"], p=float(t["p"]) if t.get("p") is not None else None, evaluable=bool(t.get("evaluable", True)),
                                   diff=t.get("effect")) for t in pruebas], schema="escalera_embudo_v1")
