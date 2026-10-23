"""Generación de candidatas. Cada candidata nace de PISTAS (evidencia propia + literatura) mediante reglas explícitas, lleva su procedencia (a favor Y en contra) y una puntuación
de valor esperado de información. Salida = BORRADORES (pre-registro + RunSpec): un humano (o un revisor) los committea y recién entonces pasan a `candidates.json`.
La literatura solo ajusta priors con peso reducido y nunca cuenta como evidencia propia. Una candidata no puede reutilizar una muestra que ya consumió la pista que la originó."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
FEAS_FLOOR = 0.25                                    # un umbral alto baja la prioridad como mucho a la cuarta parte; no excluye
PRIOR = (1.0, 4.0)                                     # prior Beta del acierto de una candidata nueva


@dataclass
class Candidate:
    cid: str
    title: str
    rule: str                                           # regla del generador que la originó
    gap_kind: str                                       # NO_PRIOR_EVIDENCE | CONFLICTING_EVIDENCE | DATA_DEFINITION | NEW_MECHANISM (vocabulario de Research Ops)
    evidence: list                                      # ids de entradas de evidencia propias
    pro: list = field(default_factory=list)             # ids de literatura a favor
    contra: list = field(default_factory=list)          # ids de literatura en contra
    template: str | None = None                         # estudio parametrizado listo, o None (= NEEDS_SCRIPT)
    cfg: dict = field(default_factory=dict)
    n_trials: int = 1
    power: float = 0.5                                  # chance estimada de detectar el efecto de la pista si existe (supuesto declarado)
    est_seconds: int = 1800
    internet: bool = False
    group: str = ""
    family: str = ""
    owner: str = "autopilot"
    required_rho: float | None = None                   # correlación mínima que la señal debe tener para que la mejor cuenta deje EV ≥ 0 (universo guiado por umbrales)
    utility_class: str = "bridgeable"                  # tradeable | bridgeable | info (ver config/autopilot/mandate.json): ¿puede acabar en una estrategia útil para challenges?
    consumes: dict = field(default_factory=dict)        # {evidence_id: muestra independiente que esta candidata gasta}
    lead_tests: dict = field(default_factory=dict)      # {evidence_id: [prefijos de las pruebas que miden ESA pista]}
    why: str = ""
    score: float = 0.0
    score_parts: dict = field(default_factory=dict)


def load_json(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def lit_adjust(c: Candidate, lits: dict) -> tuple:
    """Pseudo-conteos de literatura: cada afirmación a favor suma weight aciertos y weight observaciones; cada contraria suma weight observaciones."""
    w = lits.get("literature_weight", 0.5); h = w * len(c.pro); n = w * (len(c.pro) + len(c.contra)); return h, n


def score(c: Candidate, outcomes: list, lits: dict) -> Candidate:
    hit = sum(1 for f, g, ok in outcomes if f == c.family and g == c.group and ok); tot = sum(1 for f, g, _ in outcomes if f == c.family and g == c.group)
    lh, ln = lit_adjust(c, lits)
    p0 = (PRIOR[0] + hit + lh) / (PRIOR[0] + PRIOR[1] + tot + ln)
    from .mandate import load as _mandate, utility_weight
    from .universe import RHO_PLAUSIBLE
    cost = np.sqrt(max(c.est_seconds, 60) / 600.0); u = utility_weight(c.utility_class, _mandate()); feas = 1.0 if not c.required_rho or c.required_rho <= 0 else max(FEAS_FLOOR, min(1.0, RHO_PLAUSIBLE / c.required_rho)); voi = p0 * c.power * u * feas / cost      # el umbral PRIORIZA, nunca descarta: piso de factibilidad
    if c.owner == "human-decision": voi = 0.0                       # bloqueada: no compite por cómputo, queda visible para decisión humana
    c.score = float(voi); c.score_parts = dict(p0=round(p0, 4), power=c.power, utility=f"{c.utility_class}={u}", rho_required=None if not c.required_rho else round(c.required_rho, 3), feasibility=round(feas, 3), cost_factor=round(float(cost), 3), prior_hits=f"{hit}/{tot}", literature_pro=len(c.pro), literature_contra=len(c.contra))
    return c


# --- reglas -----------------------------------------------------------------------------------------------------------------------------
def rules(ev: dict, lits: dict) -> list:
    E = {e["id"]: e for e in ev["entries"]}; out = []
    def lit(eid, kind): return [l["id"] for l in lits["leads"] if eid in l["supports"] and l["direction"] in kind]
    e = E.get("GC_0430_REV15")
    if e and e["status"] == "WEAK_LEAD" and "other_assets_same_slot" in e["unused_samples"]:
        out.append(Candidate("SLOT-1", "Reversión de 15 min a las 04:30 CT en otros activos (generalización del hallazgo débil de GC)", "R1_REPLICATE_WEAK_LEAD_IN_UNUSED_SAMPLE", "NO_PRIOR_EVIDENCE",
                             ["GC_0430_REV15", "OU_OTHER"], pro=lit("GC_0430_REV15", ("pro",)), contra=lit("GC_0430_REV15", ("contra",)), template="slot_corr",
                             cfg=dict(mode="slot_corr", sources=["ES", "NQ", "YM", "6E", "6J", "ZB", "ES_spot"], slots=["04:30"], horizon_min=15, spot_ranges={"ES_spot": ["ES", "2018-01-01", "2025-06-30"]}, n_planned=7),
                             n_trials=7, power=0.35, est_seconds=900, group="MULTI", family="SLOT_REVERSAL", consumes={"GC_0430_REV15": "other_assets_same_slot"}, lead_tests={"GC_0430_REV15": ["slot/"]},
                             why="GC 04:30 tiene el mismo signo en dos muestras pero no pasa Holm; GC ya consumió sus datos, así que la prueba limpia es otros activos con el mismo horario."))
    e = E.get("GEX_I2D_ROD_LH")
    if e and e["status"] == "WEAK_LEAD" and "30min_window" in e["unused_samples"]:
        out.append(Candidate("IDM-1", "Momentum intradía «resto del día → última media hora» y su modulación por gamma bajo", "R2_BRIDGE_INFO_LEAD_TO_PUBLISHED_MECHANISM", "NEW_MECHANISM",
                             ["GEX_I2D_ROD_LH", "GEX_AMPLITUDE"], pro=lit("GEX_I2D_ROD_LH", ("pro",)), contra=lit("GEX_I2D_ROD_LH", ("contra",)), template="idm",
                             cfg=dict(mode="idm", sources=["ES", "NQ", "YM", "GC", "ZB", "6E", "6J", "ES_spot", "GC_spot"], gamma_source="ES_spot",
                                      spot_ranges={"ES_spot": ["ES", "2018-01-01", "2025-06-30"], "GC_spot": ["GC", "2022-07-01", "2025-06-30"]}, n_planned=10),
                             n_trials=10, power=0.55, est_seconds=1500, internet=True, group="MULTI", family="IDM", consumes={"GEX_I2D_ROD_LH": "30min_window"}, lead_tests={"GEX_I2D_ROD_LH": ["idm/ES_spot", "idm_gamma_diff/ES_spot"]},
                             why="GEX-1 midió la interacción en una ventana de 90 min (p Holm 0,43, signo esperado); la literatura define 30 min en muchas clases de activos. La ventana nueva y el cruce con gamma son pruebas nuevas, no repeticiones."))
    e = E.get("ZB_REV_5_15")
    if e and e["status"] == "ARTIFACT_SUSPECT" and "mid_price_version" in e["unused_samples"]:
        out.append(Candidate("OU-2", "Reversión de ZB a 5-15 min con precio medio bid/ask (descarta rebote bid-ask)", "R3_ARTIFACT_CHECK", "DATA_DEFINITION", ["ZB_REV_5_15"], pro=[], contra=lit("ZB_REV_5_15", ("contra_signal",)),
                             template="ou2", cfg=dict(mode="ou2", inst="ZB", desde="2025-07-01", hasta="2026-09-30", cells=[[5, 60], [5, 240], [15, 240], [60, 240]], nperm=5000, seed=20261019, n_planned=4), lead_tests={"ZB_REV_5_15": ["ou2/"]}, n_trials=4, power=0.6, utility_class="info", est_seconds=3600, group="ZB", family="OU_MID", consumes={"ZB_REV_5_15": "mid_price_version"},
                             why="Si la reversión sobrevive con precio medio es de otra naturaleza; si desaparece, queda cerrado. Requiere un script que reconstruya mid desde bid_ticks/ask_ticks (no existe aún)."))
    e = E.get("GEX_AMPLITUDE")
    if e and e["status"] == "LEAD_INFO" and "nq_ym_spot" in e["unused_samples"]:
        out.append(Candidate("GEX-2", "Amplitud intradía con gamma bajo en NQ y YM spot (réplica con instrumentos distintos)", "R4_EXTEND_POWER", "NO_PRIOR_EVIDENCE", ["GEX_AMPLITUDE"], template=None, n_trials=12, power=0.6, utility_class="info", consumes={"GEX_AMPLITUDE": "nq_ym_spot"},
                             est_seconds=1500, internet=True, group="NQ_YM", family="GEX", why="El efecto existe en USA500 spot y MES no tiene potencia (9 sesiones). Instrumentos correlacionados: réplica parcialmente independiente. Necesita adaptar gex1b_run a otros spots."))
    e = E.get("AVCL_RANGE")
    if e and e["status"] == "LEAD_INFO" and "direction" in e["unused_samples"]:
        out.append(Candidate("AVCL-2", "Dirección tras la creación de un cluster de volumen (etapa 2 de AVCL-VOL-1)", "R5_INFO_TO_DIRECTION", "NEW_MECHANISM", ["AVCL_RANGE"], template=None, n_trials=12, power=0.5,
                             est_seconds=14400, group="MNQ", family="AVCL", owner="local-session",
                             why="El rango adelante sube tras el cluster (Holm 0,0006); falta la dirección. Es campaña de la sesión local (necesita su manifiesto)."))
    e = E.get("GC_LH_MOMENTUM")
    if e and e["status"] in ("WEAK_LEAD", "REPLICATED_ONCE"):
        if "older_spot_jump_decomposition" in e["unused_samples"]:
            out.append(Candidate("IDM-2", "Momentum de la última media hora en GC: ¿lo explican los saltos del día? Prueba en spot 2022-2025 (muestra no usada para esta versión) y en otros activos", "R7_MECHANISM_COMPLEMENT_OF_LEAD", "NEW_MECHANISM",
                                 ["GC_LH_MOMENTUM"], pro=lit("GC_LH_MOMENTUM", ("pro",)), contra=lit("GC_LH_MOMENTUM", ("contra",)), template="idm_jump",
                                 cfg=dict(mode="idm_jump", sources=["GC_spot_old", "ES_spot", "ES", "NQ", "YM", "ZB", "6E", "6J"], reference_sources=["GC"],
                                          spot_ranges={"GC_spot_old": ["GC", "2022-07-01", "2025-06-30"], "ES_spot": ["ES", "2018-01-01", "2025-06-30"]}, n_planned=8),
                                 n_trials=8, power=0.35, est_seconds=1200, group="GC_MULTI", family="IDM_JUMP", consumes={"GC_LH_MOMENTUM": "older_spot_jump_decomposition"},
                                 lead_tests={"GC_LH_MOMENTUM": ["idmj/GC_spot_old"]},
                                 why="La literatura asocia el efecto a los saltos del día (cobertura de gamma tras grandes movimientos). En GC 2025-26 la correlación se concentra en movimientos grandes (+0,376 contra −0,051) y en 2026Q1. Esta prueba separa saltos y movimiento continuo y la corre sobre spot 2022-2025 de GC, donde esta descomposición no se miró (la versión «tercil grande» sí se miró y dio +0,026, por eso no se pre-registra)."))
        if "metals_basket" in e["unused_samples"]:
            out.append(Candidate("DATA-METALS", "Datos nuevos: plata, platino, paladio y petróleo spot (Dukascopy) 2022-07 → 2026-09 para replicar el momentum de la última media hora en activos hermanos", "R8_REQUEST_INDEPENDENT_ASSETS", "NO_PRIOR_EVIDENCE",
                                 ["GC_LH_MOMENTUM"], pro=lit("GC_LH_MOMENTUM", ("pro",)), contra=lit("GC_LH_MOMENTUM", ("contra",)), template=None, n_trials=0, power=0.6, est_seconds=600, group="DATA", family="DATA", owner="local-session",
                                 why="Es la única fuente de activos independientes en el MISMO período del hallazgo (el período no se puede repetir y el holdout está cerrado). Pide a la sesión local extraer con JForex XAGUSD, XPTUSD, XPDUSD y WTI/Brent (M1) y subirlos como un dataset con calidad.json; luego se corre IDM-2 sobre ellos."))
        if "new_data_after_holdout" in e["unused_samples"]:
            out.append(Candidate("WAIT-GC_LH_MOMENTUM", "Confirmación prospectiva de GC (último 30 min) con datos posteriores al 2026-09-30", "R6_NEW_LEAD_NEEDS_UNSEEN_DATA", "NO_PRIOR_EVIDENCE", ["GC_LH_MOMENTUM"], template=None, n_trials=1, power=0.5,
                                 est_seconds=600, group="BLOCKED", family="WAIT", owner="human-decision",
                                 why="La única muestra realmente independiente en el tiempo es posterior a 2026-09-30 (holdout cerrado). Requiere una decisión humana: pre-registro específico y apertura controlada, o esperar a que haya sesiones nuevas fuera del holdout formal."))
    e = E.get("VIO_ZONES_MGC")
    if e and "vio_1" in e["unused_samples"]:       # R11: hipótesis del usuario (inspección visual) convertida en prueba pre-registrada
        out.append(Candidate("VIO-1", "Zonas violeta (lógica de aVolClusterPOI) sobre las zonas de aVolZonePOI2 en MGC 25 ticks: ¿el precio que vuelve a una distancia D de la zona llega más a la zona que a D más lejos? ¿hay un TP/SL con esperanza neta positiva?",
                             "R11_USER_HYPOTHESIS", "NEW_MECHANISM", ["VIO_ZONES_MGC"], template="vio1",
                             cfg=dict(mode="vio1", inst="MGC", bar_ticks=25, tick_usd=1.0, cost_ticks=6.8, D=[10, 16, 20, 30, 40, 60], split=0.6, nperm=10000, seed=20261018, n_planned=4, desde="2025-07-01", hasta="2026-09-30",
                                      zone_params={"ob_away_heights": 6.0, "ob_max_inside_pct": 4.0, "racimo_min": 6, "racimo_bars": 500, "racimo_altura_ticks": 30}, violet_params={}),
                             n_trials=36 + 3, power=0.35, est_seconds=2400, group="MGC", family="VIO_ZONES", utility_class="tradeable", consumes={"VIO_ZONES_MGC": "vio_1"}, lead_tests={"VIO_ZONES_MGC": ["vio/"]},
                             why="Nico observó en el gráfico de MGC 12-26 (25 ticks) patrones del precio respecto de las zonas violeta de aVolClusterPOI. Esa lógica (alejarse rápido y lejos con poco volumen operado adentro) no tiene paridad verificada; se porta aquí y se aplica a las zonas de aVolZonePOI2, cuya paridad NT8 sí está verificada (25 ticks, MNQ). Se mide, a nivel de tick, la probabilidad de llegar a la zona frente a alejarse cuando el precio, ya alejado, vuelve a una distancia D, para 36 configuraciones de TP/SL."))
    e = E.get("PNL_EVAL_1")
    if e and "pnl_1" in e["unused_samples"]:       # R10: pistas en reserva → reglas operables con P&L neto (mandato: lo que importa es el neto, estable y combinable)
        out.append(Candidate("PNL-1", "P&L neto de reglas operables de las pistas en reserva: GC último 30 min (2 variantes) y celdas de SCAN-1 en GC y ES", "R10_RESERVE_LEADS_TO_NET_PNL", "NEW_MECHANISM", ["GC_LH_MOMENTUM", "UNIVERSE_SCAN_1", "PNL_EVAL_1"],
                             pro=lit("GC_LH_MOMENTUM", ("pro",)), contra=lit("GC_LH_MOMENTUM", ("contra",)), template="strategy_pnl",
                             cfg=dict(mode="strategy_pnl", nperm=20000, seed=20261017, n_planned=2,
                                      spot_ranges={"GC_spot_old": ["GC", "2022-07-01", "2025-06-30"], "GC_spot_new": ["GC", "2025-07-01", "2026-09-30"], "ES_spot": ["ES", "2018-01-01", "2025-06-30"]},
                                      rules=[dict(name="GC_ROD_LH_ALL", inst="GC", entry="14:30", hold_min=30, pred="rod", dir="momentum", filter="none", discovery=["GC"], oos=["GC_spot_old"], descriptive=["GC_spot_new"]),
                                             dict(name="GC_ROD_LH_BIG", inst="GC", entry="14:30", hold_min=30, pred="rod", dir="momentum", filter="bigmove_q67", discovery=["GC"], oos=["GC_spot_old"], descriptive=["GC_spot_new"]),
                                             dict(name="GC_PREV15_1330_MOM", inst="GC", entry="13:30", hold_min=15, pred="prev_15", dir="momentum", filter="none", discovery=["GC_spot_old"], descriptive=["GC", "GC_spot_new"]),
                                             dict(name="ES_PREV60_0730_REV", inst="ES", entry="07:30", hold_min=60, pred="prev_60", dir="reversion", filter="none", discovery=["ES_spot"], descriptive=["ES"]),
                                             dict(name="ES_PREV30_1230_MOM", inst="ES", entry="12:30", hold_min=30, pred="prev_30", dir="momentum", filter="none", discovery=["ES_spot"], descriptive=["ES"])]),
                             n_trials=5, power=0.3, est_seconds=900, group="GC_ES", family="PNL_EVAL", utility_class="tradeable", consumes={"PNL_EVAL_1": "pnl_1"}, lead_tests={"PNL_EVAL_1": ["pnl/"]},
                             why="Convierte las pistas en reserva en reglas operables y mide el P&L neto de costos por muestra, estabilidad (trimestres, 5 mejores días), resistencia a costos × 1,5 y frecuencia; la prueba confirmatoria es solo la de GC último 30 min (2 variantes) en el spot 2022-25, que no se usó para esta prueba. Las celdas de SCAN-1 se reportan de forma descriptiva (su muestra ya se consumió en la réplica)."))
    e = E.get("UNIVERSE_SCAN_1")
    uni = REPO / "docs/research/propfirm_thresholds/UNIVERSO.json"
    if e and "scan_1" in e["unused_samples"] and uni.exists():       # R9: barrido en los instrumentos de menor umbral de cuenta (UNIVERSO.json), con réplica en otra muestra
        cells = json.loads(uni.read_text())["cells"]; best = {}
        for c in cells: best.setdefault(c["inst"], c["rho_required"])
        rho = float(np.median([best[i] for i in ("GC", "NQ", "ES", "YM", "6E") if i in best])) if best else None
        out.append(Candidate("SCAN-1", "Barrido de franjas (07:00-14:30 CT) en GC, NQ, ES, YM y 6E: momentum y reversión, descubrimiento → réplica", "R9_UNIVERSE_BY_ACCOUNT_THRESHOLD", "NO_PRIOR_EVIDENCE", ["UNIVERSE_SCAN_1"],
                             template="slot_scan",
                             cfg=dict(mode="slot_scan", nperm=10000, seed=20261016, n_planned=20, spot_ranges={"ES_spot": ["ES", "2018-01-01", "2025-06-30"], "GC_spot_old": ["GC", "2022-07-01", "2025-06-30"]},
                                      scans=[dict(name="ES", disc="ES_spot", rep="ES"), dict(name="GC", disc="GC_spot_old", rep="GC"), dict(name="NQ", disc="NQ", rep="NQ", split=0.6), dict(name="YM", disc="YM", rep="YM", split=0.6), dict(name="6E", disc="6E", rep="6E", split=0.6)]),
                             n_trials=5 * 96 + 15, power=0.3, est_seconds=2400, group="MULTI", family="SLOT_SCAN", utility_class="tradeable", required_rho=rho, consumes={"UNIVERSE_SCAN_1": "scan_1"}, lead_tests={"UNIVERSE_SCAN_1": ["scan/"]},
                             why="El universo guiado por umbrales ubica los umbrales más bajos de cuenta en la apertura de EE. UU. (08:00-10:00 CT) de GC, NQ, ES y YM. Se barren 96 celdas por instrumento (franja × horizonte × predictor), con nulo de máximo en el descubrimiento (spot largo para ES y GC, 60 % inicial de los futuros para NQ, YM y 6E) y réplica de las 3 mejores celdas en la otra muestra. 495 celdas/pruebas al contador global; 20 pruebas reportadas para Holm."))
    for e in ev["entries"]:                       # pistas nuevas nacidas de resultados del propio autopilot
        if e["status"] == "WEAK_LEAD" and e.get("unused_samples") == ["new_data_after_holdout"]:
            out.append(Candidate("WAIT-" + __import__("re").sub(r"[^A-Za-z0-9_-]", "_", e["id"]), f"Réplica pendiente de datos nuevos: {e['asset']} ({e['indicator']})", "R6_NEW_LEAD_NEEDS_UNSEEN_DATA", "NO_PRIOR_EVIDENCE", [e["id"]], template=None, n_trials=1, power=0.5,
                                 est_seconds=600, group="BLOCKED", family="WAIT", owner="human-decision",
                                 why="Hallazgo exploratorio del autopilot sin muestra independiente disponible: solo datos posteriores al 2026-09-30 (holdout cerrado) o de otra fuente. No se lanza: requiere decisión humana sobre el holdout o una fuente nueva."))
    return out


CAMPANAS_GRILLA = "config/autopilot/grillas/campanas"
CAMPO_CAMPANA = ("cid", "titulo", "experimento", "kernel", "fuente", "modo", "desde", "hasta", "needs", "n_trials", "family", "spec",
                 "justificacion_economica", "como_podria_refutarse")


def campanas_grilla(carpeta: str | Path = CAMPANAS_GRILLA) -> list:
    """Campañas de grilla como DATOS (2026-10-23): el programador del agente (o una persona) deja un JSON por campaña en
    `config/autopilot/grillas/campanas/` y acá se vuelve candidata con RunSpec (kernel genérico, decisión escalera_v1). Antes un
    experimento nuevo quedaba aplicado pero nada lo lanzaba: las candidatas salían sólo de reglas escritas a mano en `rules`.
    Una campaña con `activa: false` no compite. Le falta un campo obligatorio -> se reporta y no se genera."""
    out = []
    for f in sorted((REPO / carpeta).glob("*.json")) if (REPO / carpeta).exists() else []:
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("activa", True): continue
        from edgelab.research.preflight import verificar_campana
        if (err := verificar_campana(d, REPO)): raise ValueError(f"campaña {f.name}: {err}")
        out.append(Candidate(d["cid"], d["titulo"], "R12_GRILLA_CAMPANA", d.get("gap_kind", "NEW_MECHANISM"), d.get("evidencia", []), template="grilla", cfg=d,
                             n_trials=int(d["n_trials"]), power=float(d.get("potencia", 0.5)), est_seconds=int(d.get("est_seconds", 7200)), group=d["fuente"],
                             family=d["family"], utility_class=d.get("utility_class", "bridgeable"),
                             why=f"Campaña de grilla {f.name}: {d['justificacion_economica']} Refutación: {d['como_podria_refutarse']}"))
    return out


def generate(outcomes: list, seed_evidence: str = "config/autopilot/evidence_seed.json", leads: str = "config/autopilot/literature_leads.json", seen_ids: set = frozenset(), runtime: Path | None = None) -> list:
    from .evidence import apply_runtime
    ev, lits = load_json(seed_evidence), load_json(leads)
    if runtime: ev = apply_runtime(ev, runtime)
    cands = [score(c, outcomes, lits) for c in rules(ev, lits) + campanas_grilla() if c.cid not in seen_ids]
    return sorted(cands, key=lambda c: -c.score)


# --- borrador de pre-registro ------------------------------------------------------------------------------------------------------------------
MODE_DEFS = {
 "idm_jump": '''Definiciones congeladas (script `tools/study_slot_effect.py`, modo `idm_jump`, por fecha local CT):
- Precio = apertura del minuto en una rejilla de 5 min (primer valor de cada bloque). Retornos r = log-diferencias sucesivas entre puntos de rejilla disponibles desde el 15:00 CT de la sesión anterior hasta el 14:30 CT (una brecha de mantenimiento/fin de semana cuenta como un retorno).
- σ = 1,4826 · mediana(|r|) de las 20 sesiones previas (causal; se exige ≥ 5 sesiones previas). Salto = |r| > 4σ. ROD = Σ r; ROD_salto = Σ r de los saltos; ROD_cont = ROD − ROD_salto. LH = log(P 15:00 / P 14:30).
- Modelo: OLS LH ~ 1 + ROD_salto + ROD_cont. Estadístico = coeficiente de ROD_salto. H1: > 0 (unilateral). Nulo: signo aleatorio independiente sobre LH, 20.000 sorteos, semilla 20261013.
- `reference_sources` (GC futuro 2025-26) se informan pero NO entran en Holm: es la muestra que originó la pista. La prueba de la pista es `idmj/GC_spot_old` (spot 2022-07-01 → 2025-06-30).
- Descriptivo (no es prueba): participación de sesiones con salto, coeficiente de ROD_cont, rango del coeficiente de salto al excluir cada trimestre.''',
 "slot_scan": '''Definiciones congeladas (script `tools/study_slot_effect.py`, modo `slot_scan`):
- Celdas por instrumento (96): franja de inicio t ∈ {07:00, 07:30, …, 14:30} CT × horizonte h ∈ {15, 30, 60} min (solo si t+h ≤ 15:30) × predictor ∈ {«prev»: log(P_t / P_{t−h}); «rod»: log(P_t / P_cierre previo 15:00 CT)}. Retorno siguiente Y = log(P_{t+h} / P_t). P = apertura del minuto, último precio conocido del día (ffill); se descartan fechas con datos faltantes.
- Estadístico por celda: correlación de Pearson corr(X, Y), BILATERAL (momentum +, reversión −).
- Descubrimiento (por instrumento): z_c = corr·√n; máximo |z| sobre las 96 celdas; nulo de MÁXIMO con 10.000 permutaciones de las sesiones de Y (la misma permutación en todas las celdas); p = (1 + #{máx_nulo ≥ máx_obs}) / (1 + B).
- Réplica (por instrumento): las 3 celdas con mayor |z| del descubrimiento; en la muestra de réplica, con el signo del descubrimiento FIJADO, corr unilateral, nulo de signo aleatorio sobre Y (10.000 sorteos).
- Muestras: ES: descubrimiento en spot ES 2018-01-01 → 2025-06-30 y réplica en el futuro ES 2025-07 → 2026-09; GC: spot 2022-07-01 → 2025-06-30 y futuro 2025-07 → 2026-09; NQ, YM, 6E: futuros 2025-07 → 2026-09 con el primer 60 % de las sesiones para descubrir y el 40 % final para replicar. Semilla 20261016.
- Pruebas reportadas para Holm: 4 por instrumento (1 máximo + 3 réplicas) = 20; el contador global recibe 495 (480 celdas + 15 réplicas).
- Descriptivo (no es prueba): top-10 de celdas del descubrimiento con su correlación en la réplica.''',
 "strategy_pnl": '''Definiciones congeladas (script `tools/study_slot_effect.py`, modo `strategy_pnl`):
- Una operación por día y regla: entrada a la apertura del minuto `entry` (CT) y salida a la apertura `entry + hold_min`; dirección = signo del predictor × (+1 momentum, −1 reversión). Predictor: `prev_h` = log(P_entrada / P_{entrada−h min}); `rod` = log(P_entrada / P cierre previo 15:00 CT). Filtro `bigmove_q67`: solo si |predictor| ≥ cuantil 2/3 expansivo de las sesiones previas (causal, mínimo 60).
- P&L en USD por contrato = signo × (P_salida − P_entrada) × multiplicador (GC 100 oz, ES 50 USD/pt) − costo de ida y vuelta (GC 24,80; ES 30,00; supuestos de `edgelab/autopilot/universe.py`). Precio spot = punto medio bid/ask de la apertura del minuto.
- Reglas, muestras y roles (cfg abajo): `discovery` = muestra donde se halló la pista (descriptiva); `oos` = muestra confirmatoria; `descriptive` = otras fuentes.
- Prueba confirmatoria (solo `oos`): estadístico = media neta por operación; nulo = dirección aleatoria independiente por operación (20.000 sorteos); p unilateral; **p = 1 si la media neta ≤ 0**. Holm sobre 2 pruebas (GC_ROD_LH_ALL y GC_ROD_LH_BIG en el spot 2022-07 → 2025-06). Semilla 20261017.
- Descriptivo (no es prueba): media neta, desvío, aciertos, P&L por trimestre, parte de los 5 mejores días, P&L total con costos × 1,5, drawdown, operaciones por mes, y el P&L diario (para simular challenges y el control sin ventaja fuera del kernel).''',
 "vio1": '''Definiciones congeladas (script `tools/vio1_zones.py`; lógica violeta en `edgelab/research/violet_zones.py`, portada de `nt8/aVolClusterPOI_violet_v05.cs`):
- Datos: MGC, sesiones aprobadas 2025-07-01 → 2026-09-30 (líder por sesión del resolver), sin la pausa CME 16:00-17:00 CT; barras de 25 ticks (trades); footprint total NT8 (`build_total_footprint_csr_nt8`).
- Zonas: `edgelab.bridge.indicators.avolzonepoi2.run` con la configuración 25T de paridad verificada (detección por defecto 10/×2/gap 1/mín. 2/Suma/15 min/p95/20 sesiones/mín. 20; OB 6 alturas, 8 ticks, 4 %; racimo 6/500/30). Se usan TODAS las zonas detectadas.
- Violeta (parámetros por defecto del .cs): dirección = signo del cierre de la barra de creación respecto de la zona (0 = adentro: no aplica); se alejó = separación máxima ≥ max(40 ticks, ⌈2 × ancho⌉) dentro de 30 barras; poco volumen = volumen operado dentro de la zona hasta ese momento / score ≤ umbral adaptativo causal (cuantil q = 20 % / proporción de zonas que se alejan; 0,35 mientras haya menos de 20 alejadas o 20 resueltas); invalidación por cierre de barra del lado equivocado; la decisión se fija una vez.
- Evento (a nivel de TICK): tras la barra de decisión, el precio se aleja a más de D ticks de la zona y luego vuelve a D (entrada con orden límite en D). Ventana: hasta la invalidación de la zona o el fin de la sesión CME (16:00 CT). D ∈ {10, 16, 20, 30, 40, 60} ticks (MGC: 1 tick = 0,10 = USD 1).
- Resultado por configuración (a, b) con a ∈ {D/2, D} ticks hacia la zona (TP; a = D llega al borde de la zona) y b ∈ {D/2, D, 2D} alejándose (SL): 36 configuraciones; sin barrera al fin de la ventana se sale a mercado. P&L en ticks; costo de ida y vuelta supuesto 6,8 ticks (USD 6,8 por contrato: comisión 4,80 + 2 ticks de deslizamiento; supuesto conservador).
- Descubrimiento (60 % inicial de las sesiones): esperanza bruta por evento de cada configuración; nulo de MÁXIMO por cambio de signo por sesión (conjunto en las 36 configuraciones, 10.000 sorteos; H0 = esperanza bruta 0). Réplica (40 % final): las 3 mejores configuraciones del descubrimiento, con media neta (bruta − 6,8) > 0 exigida (p = 1 si ≤ 0), nulo de signo por sesión. Holm sobre 4 pruebas (1 máximo + 3 réplicas); el contador global recibe 39 (36 configuraciones + 3 réplicas). Semilla 20261018.
- Descriptivo (no es prueba): para cada configuración, P(TP), P(SL), P(sin barrera), P(TP) de equilibrio b/(a+b), esperanza bruta en cada mitad, eventos por sesión; y el MISMO análisis para las zonas que se alejaron pero NO son violeta (control).''',
 "ou2": '''Definiciones congeladas (script `tools/ou2_mid.py`):
- Datos: ZB, sesiones aprobadas 2025-07-01 → 2026-09-30 (líder por sesión del resolver; fecha de sesión CME del catálogo). Mismas sesiones y celdas que OU-1 Parte A para ZB (misma muestra que originó la pista: es la prueba de DEFINICIÓN del precio, no de muestra nueva).
- Por (sesión, minuto): «last» = último trade del minuto; «mid» = (bid+ask)/2 del último tick del minuto con libro válido (0 < bid ≤ ask). Los minutos sin libro válido se excluyen del análisis de «mid».
- Estadístico (idéntico a OU-1): X_t = ln P_t − SMA_N(ln P_t) dentro de sesión sobre barras de s minutos (último valor de cada barra); b = pendiente agrupada de (X_{t+1} − X_t) sobre X_t; primera barra de sesión con retorno 0. Nulo: signo aleatorio independiente por retorno de barra (5.000 sorteos, semilla 20261019); z = (b − media_nulo)/sd_nulo, bilateral.
- Pruebas (4, Holm 4) con «mid»: (barra, ventana) = (5,60), (5,240), (15,240), (60,240) minutos. «La reversión sobrevive» = z < 0 y p_Holm < 0,05 en la celda con «mid»; si «last» da reversión y «mid» no, el hallazgo de OU-1 era rebote bid-ask.
- Descriptivo (no es prueba): «last» y «mid» sobre los mismos minutos, y por mitades de sesiones (cada mitad: z de «last» y «mid» en 3 celdas); cobertura de «mid».''',
 "idm": "Ver docstring del script (modo `idm`): corr(resto del día, última media hora), unilateral positiva; diferencia por gamma bajo con permutación por bloques de 20.",
 "slot_corr": "Ver docstring del script (modo `slot_corr`): corr(retorno previo, siguiente) de `horizon_min` minutos en cada franja; unilateral negativa.",
}
TRANSPARENCY = {
 "VIO-1": '''## Transparencia sobre lo ya mirado (antes de este pre-registro)
- La hipótesis nace de la inspección visual de Nico del gráfico MGC 12-26 (25 ticks) con aVolClusterPOI (captura del 2026-10-12, que incluye fechas posteriores al 2026-09-30 que este estudio NO lee). Esas impresiones visuales pueden coincidir con períodos de la muestra: por eso se separa descubrimiento (60 % inicial) y réplica (40 % final); la muestra no es virgen.
- La lógica violeta no tiene paridad verificada (solo el .cs); su portado a Python se prueba con casos sintéticos (`tests/test_violet_zones.py`) y se verificó que corre de punta a punta sobre un tramo de ES (sin resultados de MGC). Las zonas de aVolZonePOI2 sí tienen paridad NT8 verificada (MNQ 25T); su paridad en MGC no se verificó.
- No se miró ningún resultado de MGC antes de este pre-registro.''',
 "OU-2": '''## Transparencia sobre lo ya mirado (antes de este pre-registro)
- OU-1 ya midió ZB con precio de transacción (último trade del minuto): b y z en las 4 celdas (z = −14,05 / −7,68 / −3,28 / +0,06; Holm 36 = 0,0072 / 0,0072 / 0,0204 / 1). Esta corrida usa la MISMA muestra de sesiones con otra definición de precio.
- El pipeline se probó solo en datos sintéticos (con y sin rebote bid-ask inyectado); no se miró ningún resultado de «mid» en ZB real.
- Esto es información sobre el mecanismo, no una estrategia: aunque «mid» sobreviva, que sea operable es otra pregunta (spread, costos).''',
 "PNL-1": '''## Transparencia sobre lo ya mirado (antes de este pre-registro)
- `GC_ROD_LH_ALL` y `GC_ROD_LH_BIG`: la pista nació en el futuro de GC 2025-26 (`discovery`). En el spot 2022-2025 (`oos`) ya se miró antes la correlación del tercil de |ROD| alto (+0,026) y el P&L bruto medio de seguir el signo (+0,66 pb, por debajo del costo): se espera que no pasen; la prueba sirve para cerrar la pista en su forma operable.
- Celdas de SCAN-1 (`GC_PREV15_1330_MOM`, `ES_PREV60_0730_REV`, `ES_PREV30_1230_MOM`): su muestra de réplica (futuros 2025-26) ya se consumió en SCAN-1 sin éxito: aquí son DESCRIPTIVAS, no confirmatorias.''',
 "IDM-2": '''## Transparencia sobre lo ya mirado (antes de este pre-registro)
- En GC 2025-26 (futuro y spot, misma muestra que originó la pista) se miraron: correlación por trimestre, sin 2026Q1, sin los 10 días más influyentes, terciles de |ROD|, economía bruta de seguir el signo. Son descriptivos y no cuentan como pruebas.
- En el spot 2022-2025 se miró **una** cosa antes de pre-registrar: el tercil de |ROD| alto (causal expansivo) dio corr +0,026 (n = 309). Por eso esa versión del refinamiento no se pre-registra ni se usa; la descomposición en saltos NO se calculó en ese tramo.
- El pipeline de saltos se verificó en sintético y en spot 2025-26 (misma muestra de la pista, no la de la prueba primaria).''',
}


def draft_prereg(c: Candidate, lits: dict) -> str:
    cfg = json.dumps(c.cfg, sort_keys=True); mode_block = (MODE_DEFS.get(c.cfg.get("mode"), "") + "\n\n" if c.cfg else "") + (TRANSPARENCY.get(c.cid, "") + "\n\n" if c.cid in TRANSPARENCY else "")
    lit = {l["id"]: l for l in lits["leads"]}
    def fmt(ids): return "\n".join(f"- {i}: {lit[i]['claim']} ({'; '.join(lit[i]['refs'])})" for i in ids) or "- (ninguna)"
    return f"""# {c.cid} — {c.title}
**Estado: BORRADOR generado por el autopilot (regla {c.rule}). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
{c.why}
Evidencia propia de origen: {', '.join(c.evidence)}. Tipo de vacío: {c.gap_kind}.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
{fmt(c.pro)}
Literatura en contra / límites:
{fmt(c.contra)}

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{cfg}
```
Pruebas planeadas: {c.n_trials} (se cuentan en el registro global antes de lanzar). Potencia supuesta: {c.power} (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

{mode_block}{_decision_bloque(c)}

## Puntuación de valor esperado de información
{json.dumps(c.score_parts, ensure_ascii=False)} → {c.score:.4f}
"""


def _decision_bloque(c: Candidate) -> str:
    if c.template == "grilla":
        extra = "".join(f"\n{k} congelado (bloque exacto que recibe el kernel):\n```\n{json.dumps(c.cfg[k.lower()])}\n```\n"
                        for k in ("CORTES", "CELDAS") if c.cfg.get(k.lower()))
        return f"""## Grilla y decisión
Experimento `{c.cfg['experimento']}` (spec `{c.cfg['spec']}`), kernel `{c.cfg['kernel']}`, fuente {c.cfg['fuente']}, modo {c.cfg['modo']}, {c.cfg['desde']} → {c.cfg['hasta']}.
Justificación económica: {c.cfg['justificacion_economica']}
Cómo podría refutarse: {c.cfg['como_podria_refutarse']}
Celdas registradas: {c.n_trials} (todas cuentan). DESC: tamiz FDR q = 0,10 + Romano-Wolf por sesiones en canales total/reciente, pistas
y marginales; nada de DESC es acierto. REP: celdas y cortes congelados, un lote = un paso de LORD++ (Simes + BH). Una variante buena se
indaga antes de su P&L básico (ATJ-26).{extra}"""
    return f"""## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre {c.n_trials} pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio."""


TEMPLATES = {"vio1": dict(script="tools/vio1_zones.py", env="VIO_CFG", extra=["nicolasbuttaro/edgelab-code-zones"]),
             "ou2": dict(script="tools/ou2_mid.py", env="OU2_CFG", extra=[])}


def to_runspec(c: Candidate) -> dict | None:
    if not c.template: return None
    if c.template == "grilla":
        g = c.cfg; env = dict(EXPERIMENTO=g["experimento"], FUENTE=g["fuente"], MODO=g["modo"], DESDE=str(g["desde"]), HASTA=str(g["hasta"]))
        for k in ("cortes", "celdas"):
            if g.get(k): env[k.upper()] = json.dumps(g[k])
        return dict(run_id=c.cid.lower(), kind="replication" if g["modo"] == "REP" else "scan", family=g["family"], group=g["fuente"], script=g["kernel"],
                    prereg=f"docs/research/autopilot/drafts/{c.cid}.md", n_trials=c.n_trials, needs=list(g["needs"]), extra_datasets=list(g.get("extra_datasets", [])),
                    internet=False, env=env, est_seconds=c.est_seconds, decision_rule="escalera_v1", notes=c.title)
    tm = TEMPLATES.get(c.template, dict(script="tools/study_slot_effect.py", env="STUDY_CFG", extra=None))
    names = (c.cfg.get("sources") or sorted({x[k] for x in c.cfg.get("scans", []) for k in ("disc", "rep")} | {n for r in c.cfg.get("rules", []) for k in ("discovery", "oos", "descriptive") for n in r.get(k, [])})) + c.cfg.get("reference_sources", [])
    needs = [f"{s}:2025-07-01:2026-09-30" for s in names if s not in c.cfg.get("spot_ranges", {})] if "inst" not in c.cfg else [f"{c.cfg['inst']}:{c.cfg.get('desde', '2025-07-01')}:{c.cfg.get('hasta', '2026-09-30')}"]
    extra = tm["extra"] if tm["extra"] is not None else ["nicolasbuttaro/edgelab-dukascopy-es-usa500"] + (["nicolasbuttaro/edgelab-dukascopy-xauusd-ticks-m1"] if any(k.startswith("GC_spot") for k in c.cfg.get("spot_ranges", {})) else [])
    return dict(run_id=c.cid.lower(), kind="study", family=c.family, group=c.group, script=tm["script"], prereg=f"docs/research/autopilot/drafts/{c.cid}.md", n_trials=c.n_trials, n_tests_holm=c.cfg.get("n_planned"),
                needs=needs, extra_datasets=extra, internet=c.internet, env={tm["env"]: json.dumps(c.cfg, sort_keys=True)}, est_seconds=c.est_seconds, decision_rule="holm", notes=c.title, origin={k: dict(sample=v, tests=c.lead_tests.get(k)) for k, v in c.consumes.items()})


def research_gaps(c: Candidate) -> dict:
    """Directiva para el planificador knowledge-first de Research Ops (formato de plan_research): pregunta pública neutral, sin contexto privado, con su contraria.
    `public_query_reviewed` queda en False: la revisión es humana."""
    topic = {"SLOT-1": "intraday return reversal at fixed time of day across futures markets", "IDM-1": "intraday momentum last half-hour return predicted by rest-of-day return gamma hedging",
             "OU-2": "short-horizon negative autocorrelation futures bid-ask bounce mid-quote versus transaction prices", "GEX-2": "dealer gamma exposure and intraday volatility index futures",
             "AVCL-2": "volume clusters order flow direction after high volume nodes futures", "SCAN-1": "intraday return predictability time of day futures momentum reversal US open", "IDM-2": "jumps rest-of-day return last half-hour return commodity futures gold intraday momentum", "DATA-METALS": "intraday momentum metals silver platinum palladium crude oil futures"}.get(c.cid, c.title)
    return dict(candidate=c.cid, gap_kind=c.gap_kind, missing_evidence=c.why[:2048], public_query=topic, contrary_query=f"evidence against or limitations: {topic}", public_query_reviewed=False)
