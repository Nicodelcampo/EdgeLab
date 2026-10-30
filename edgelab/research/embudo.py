"""Orquestador del embudo de grilla (2026-10-23): una campaña = un JSON; el resto es automático, de punta a punta.

Pedido de Nico: «que este análisis de millones de variantes con promociones siga siempre un embudo, sea fácil en cualquier activo
con cualquier lógica que proponga el agente, sin errores, sin armarlo cada vez; y que lo humano deje de serlo». Lo único que
se escribe por campaña es el módulo del experimento (la lógica) y la campaña (activo, períodos, justificación, refutación).

Etapas (una por ciclo de `avanzar`; idempotente; estado en <raiz>/<cid>/estado.json; bitácora MEDIDO.md):
  PREFLIGHT  local      preflight estático + dinámico del experimento                       falla -> BLOQUEADA
  DESC       kaggle     registro 2·n_celdas; tamiz + Romano-Wolf + pistas + nulo             0 nominadas -> PISTAS (o SIN_CANDIDATAS
                        (2026-10-24: sólo pistas NOMINADAS por el FDR q 0,10 del canal; RW es     si no hay ventana para replicarlas)
                        diagnóstico; el linaje es información salvo `linaje_como: "compuerta"`; la meseta ordena, no mata)
  PISTAS     kaggle     pistas a réplica (ATJ-25): top-k congeladas, réplica en la ventana       0 confirmadas -> SIN_CANDIDATAS
                        reciente no usada, UN paso de LORD++ por lote (Simes + BH); las confirmadas
                        quedan nominadas y siguen a INDAGA (docs/research/revision_20261024/FALSOS_NEGATIVOS_EMBUDO_20261024.md)
  INDAGA     kaggle     marginales alrededor de cada candidata (información, no compuerta)
  INTEGRIDAD kaggle     alineación (si señal ≠ ejecución), placebo, latencia                  ninguna pasa -> INTEGRIDAD_FALLA
  OOS        kaggle     réplica en período no usado; un paso de LORD++ de la familia (libro)  todas refutadas -> REFUTADA_OOS
                        (2026-10-24: mata sólo con potencia declarada, en contra significativo y en el MISMO régimen declarado ex ante;
                        sin potencia = NO_CONCLUYENTE; en contra en otro régimen = EN_CONTRA_OTRO_REGIMEN, sigue viva)
  ATRAS      kaggle     (2026-10-26, informativa) las candidatas congeladas sobre años ANTERIORES al DESC que la familia no usó
                        (`atras` de la campaña). NUNCA mata: el pasado no refuta lo que funciona en el régimen actual (ATJ-24,
                        Nico 2026-10-26); se publica A_FAVOR / EN_CONTRA_PASADO / NO_CONCLUYENTE con potencia y va al acta
  TOPES      kaggle     tope de stop por regla declarada (sólo datos ya usados)              ninguna elegible -> SIN_REGLA_OPERABLE
  ACTA       local      acta de holdout con la regla congelada, N fijo y α RESERVADO en el libro (antes de mirar)
  CONTEO     local      sesiones del holdout: sólo cuenta operaciones (sin P&L) hasta llegar a N
  HOLDOUT    local      primeras N operaciones: un paso de LORD++ -> CONFIRMADA / REFUTADA / SIN_POTENCIA
Las reglas de cada compuerta vienen de la campaña (`seleccion`, `integridad`, `topes`, `holdout`) con valores por defecto
documentados acá; quedan escritas en el estado ANTES de la etapa que las usa.
Las cuatro decisiones de validación del 2026-10-24 (aprobadas por Nico): docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md.
Correcciones de falsos negativos del mismo día (pedido de Nico: que el embudo no descarte candidatas reales sin perder el control
del error): docs/research/revision_20261024/FALSOS_NEGATIVOS_EMBUDO_20261024.md.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT

ORDEN = ["PREFLIGHT", "DESC", "PISTAS", "INDAGA", "INTEGRIDAD", "OOS", "ATRAS", "TOPES", "ACTA", "CONTEO", "HOLDOUT", "FIN"]
FINALES = ("BLOQUEADA", "SIN_CANDIDATAS", "PISTAS_VIVAS", "SIN_POTENCIA_HOLDOUT", "INTEGRIDAD_FALLA", "REFUTADA_OOS", "SIN_REGLA_OPERABLE", "CONFIRMADA", "REFUTADA", "SIN_POTENCIA")
Q_FDR_DESC = 0.10                       # decisión 1 (2026-10-24): gate duro, no se configura por campaña
DECISIONES_20261024 = "docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md"
FALSOS_NEGATIVOS_20261024 = "docs/research/revision_20261024/FALSOS_NEGATIVOS_EMBUDO_20261024.md"
LINAJE_COMO = ("informacion", "compuerta")                # cómo pesa el linaje en DESC (falsos negativos, 2026-10-24)
A3_REPLICA = (20260401, 20260930)                          # HOLDOUT-A3: ventana de réplica de ES/NQ (una vez por familia)
# `exigir_meseta` (nombre histórico): desde el 2026-10-24 la meseta ORDENA las candidatas (primero las que la tienen), no las mata.
DEFECTOS = dict(seleccion=dict(max_candidatas=3, min_sesiones=20, ratio_mov_friccion=3.0, exigir_meseta=True, min_dif=2, min_ops_oos=30),
                # pistas a réplica (ATJ-25): k declarado por campaña; `ventana` = período reciente no usado. Sin declarar: el OOS si
                # es posterior al DESC, o la réplica de HOLDOUT-A3 para ES/NQ; si no hay ninguna, la etapa no corre.
                pistas_replica=dict(activa=True, k=20, ventana=None),
                integridad=dict(placebo_max_frac=0.25, latencia_1_positiva=False),
                topes=dict(lista=None, min_frac_sin_tope=0.5),
                holdout=dict(desde=HOLDOUT_PRIMERA_SESION_INT, n_fijo=150, conteo_cada_s=86400, n_max=500, potencia_min=0.8),
                # decisión 2 (2026-10-24, con el matiz de Nico: «algunas estrategias funcionan por régimen»): `actual_desde` = primer día
                # (YYYYMMDD, anterior al holdout) del régimen vigente y `definicion` = cómo se lo define, ambos ANTES del OOS. Sin
                # declaración el OOS cuenta como del régimen actual (no hay excepción a posteriori).
                regimen=dict(definicion=None, actual_desde=None, fraccion_efecto=0.5, potencia_min=0.8))
CAMPOS = ("cid", "familia", "experimento", "sensor", "desc", "justificacion_economica", "como_podria_refutarse")
# Lo que define la campaña: si cambia después del PREFLIGHT ya no es la misma campaña (se crea otra, con su registro).
INMUTABLES = ("familia", "experimento", "sensor", "ejecucion", "desc", "oos", "n_celdas_por_canal", "pistas_replica", "linaje_como")
CONDUCTORES = ("debian", "local")                          # quién conduce cada campaña: uno solo (auditoría 2026-10-24)
A3_FIN_DESCUBRIMIENTO, A3_INSTRUMENTOS = 20260331, ("ES", "NQ")   # HOLDOUT-A3/A4: ES y NQ descubren hasta acá; abr–sep es réplica
GRACIA_NO_ENCONTRADO_S = 3600                              # 404 tolerado tras lanzar (2026-10-30, BLOQUEADAS del 26-10)
MAX_HORAS_KAGGLE = 14                                       # Kaggle corta a las 12 h: pasado esto, la etapa se da por caída
GG_MIN_OPS = 30                                              # = grilla_generica.MIN_OPS (test)
N_BOOT_REPLICA, N_BOOT_HOLDOUT = 2000, 5000                 # bootstrap de `grilla_generica.evaluar` y de `_fin_holdout`
# D5 (2026-10-24): holdout.estadistico = "e_proceso" exige cotas ESTRUCTURALES declaradas en la campaña antes de mirar (puntos de
# la ejecución): pérdida y ganancia máximas por construcción, margen de hueco y efecto útil. Una regla sin tope de pérdida (U1 sin
# tope) no puede usarlo: una cola más ancha que la declarada detiene con LIMITE_VIOLADO (U1-B, 2026-10-23) y queda N fijo.
COTAS_E_PROCESO = ("perdida_max_pts", "ganancia_max_pts", "margen_hueco_pts", "mu_util")


def _cfg(spec, k):
    return {**DEFECTOS[k], **(spec.get(k) or {})}


def _reglas(spec, st, k):
    """Las reglas de cada compuerta quedan congeladas en el PREFLIGHT (antes de ver resultados); después se usan ésas aunque
    alguien edite el JSON de la campaña. Antes se releían del JSON en cada etapa: aflojar `seleccion` o `topes` después de ver
    el DESC cambiaba la compuerta en silencio."""
    return {**DEFECTOS[k], **(st.get("reglas") or {}).get(k, {})} if st.get("reglas") else _cfg(spec, k)


def _de(lista, i) -> dict:
    return lista[i] if isinstance(lista, list) and i < len(lista) and isinstance(lista[i], dict) else {}


def _por_lat(lat, r):
    return lat.get(r) if r in lat else lat.get(str(r), [])


def _problemas_regimen(r) -> list:
    if r.get("actual_desde") is None: return []
    e = []
    if not r.get("definicion"): e.append("regimen.actual_desde sin regimen.definicion (el régimen se define por escrito antes del OOS)")
    if int(r["actual_desde"]) >= HOLDOUT_PRIMERA_SESION_INT: e.append("regimen.actual_desde cae en el holdout: el régimen se define con desarrollo")
    return e


def nominada(p: dict, n_heredado: int = 0, como: str = "compuerta") -> tuple:
    """Decisión 1 + 4: la pista pasa DESC sólo si el FDR del canal la nomina (q <= 0,10). El linaje (q con las pruebas heredadas en
    el mismo tamiz) es compuerta sólo con `como="compuerta"`; con "informacion" (por defecto en campañas nuevas desde el
    2026-10-24) se calcula y se publica pero no decide: la confirmación es en datos nuevos y la controla LORD++. Una pista que
    entró por «pistas a réplica» y el paso de LORD++ del lote la confirmó (`nominada_replica`) cuenta como nominada. Una pista
    sin marca (DESC anterior al 2026-10-24) cuenta como no nominada."""
    from edgelab.research.linaje import q_con_linaje
    if como not in LINAJE_COMO: raise ValueError(f"linaje_como: {LINAJE_COMO}")
    if p.get("nominada_replica"): return True, None
    if not p.get("nominada_fdr") or p.get("q_fdr") is None: return False, None
    ql = q_con_linaje(p["q_fdr"], p.get("pi0_fdr", 1.0), int(p["m_fdr"]), int(n_heredado))
    return bool(p["q_fdr"] <= Q_FDR_DESC and (como == "informacion" or ql <= Q_FDR_DESC)), ql


def _como_linaje(st) -> str:
    """Lo congelado en el PREFLIGHT. Un estado congelado antes del 2026-10-24 (sin `como`) conserva la compuerta: aflojarla con
    resultados ya vistos sería relajar un gate después de mirar."""
    return (((st.get("reglas") or {}).get("linaje")) or {}).get("como", "compuerta")


def oos_comprometido(spec: dict) -> bool:
    """La campaña declara que su OOS ya se miró (`periodos_consumidos.oos` empieza con «COMPROMETIDO»; LUXG: la regla del visor se
    diseñó mirando abr–sep). Ese período puede refutar en la etapa OOS, pero nunca confirmar pistas (2026-10-25, revisión externa)."""
    return str(((spec.get("periodos_consumidos") or {}).get("oos")) or "").strip().upper().startswith("COMPROMETIDO")


def _meses(periodo) -> int:
    """Meses calendario que toca un período [YYYYMMDD, YYYYMMDD]."""
    if not periodo: return 0
    a, b = int(periodo[0]), int(periodo[1])
    return (b // 10000 - a // 10000) * 12 + (b // 100 % 100 - a // 100 % 100) + 1


def _solapa(a, b) -> bool:
    return bool(a and b and int(a[0]) <= int(b[1]) and int(b[0]) <= int(a[1]))


def ventana_pistas(spec: dict, cfg: dict | None = None):
    """Ventana de la réplica de pistas: la declarada; si no, el OOS de la campaña cuando es posterior al DESC (reciente y no usado:
    entonces el OOS no se reusa para las pistas replicadas); si no, la réplica de HOLDOUT-A3 para ES/NQ. None = no hay dónde.
    Ninguna ventana que solape un OOS declarado comprometido sirve para confirmar (`oos_comprometido`)."""
    cfg = cfg if cfg is not None else _cfg(spec, "pistas_replica")
    malo = spec.get("oos") if oos_comprometido(spec) else None
    if cfg.get("ventana"): return [int(cfg["ventana"][0]), int(cfg["ventana"][1])]
    if spec.get("oos") and spec.get("desc") and int(spec["oos"][0]) > int(spec["desc"][1]) and not malo: return [int(spec["oos"][0]), int(spec["oos"][1])]
    inst = {spec.get("sensor"), spec.get("ejecucion") or spec.get("sensor")}
    if inst & set(A3_INSTRUMENTOS) and spec.get("desc") and int(spec["desc"][1]) <= A3_FIN_DESCUBRIMIENTO and not _solapa(A3_REPLICA, malo): return list(A3_REPLICA)
    return None


class Embudo:
    def __init__(self, raiz: Path, runners: dict, registro=None, libro=None, ahora=time.time, log=print, ventanas=None, linajes=None,
                 registro_pruebas=None):
        """runners: {"kaggle": ..., "local": ...} con lanzar(spec, etapa, params, periodo) -> handle, estado(handle), traer(handle)."""
        self.raiz, self.runners, self.registro, self.libro, self.ahora, self.log = Path(raiz), runners, registro, libro, ahora, log
        self.ventanas = ventanas                                                   # libro de ventanas del holdout (None = el del repo)
        self.linajes, self.registro_pruebas = linajes, registro_pruebas            # LINAJES.jsonl y TRIAL_REGISTRY (None = los del repo)

    # --- estado -------------------------------------------------------------------------------------------------------
    def _dir(self, spec): d = self.raiz / spec["cid"]; d.mkdir(parents=True, exist_ok=True); return d

    def estado(self, spec) -> dict:
        f = self._dir(spec) / "estado.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else dict(etapa="PREFLIGHT", fase="PENDIENTE", historial=[], spec=spec)

    def _guardar(self, spec, st):
        f = self._dir(spec) / "estado.json"; tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False, default=float), encoding="utf-8"); tmp.replace(f)

    def _medido(self, spec, linea):
        with (self._dir(spec) / "MEDIDO.md").open("a", encoding="utf-8", newline="\n") as f: f.write(linea + "\n")

    def _cerrar(self, spec, st, final, motivo):
        # Guarda (2026-10-26, auditoría del filtro): «refutada» exige una prueba que PODÍA rechazar. Si la réplica de pistas no tenía
        # resolución (umbral < p mínimo posible) o su veredicto no es REFUTADA, la familia no se cierra como SIN_CANDIDATAS.
        pr_ = st.get("pistas_replica") or {}
        if final == "SIN_CANDIDATAS" and pr_.get("lord") is not None and (pr_.get("veredicto") or {}).get("veredicto") != "REFUTADA":
            motivo = f"{motivo} | guarda: sin una refutación con potencia no se cierra como SIN_CANDIDATAS"; final = "PISTAS_VIVAS"
        st.update(etapa="FIN", fase=final, motivo=motivo); st["historial"].append(dict(ts=self.ahora(), final=final, motivo=motivo))
        self._medido(spec, f"- **{final}** — {motivo}"); self._guardar(spec, st); return st

    def _siguiente(self, spec, st, etapa, **datos):
        st["historial"].append(dict(ts=self.ahora(), etapa=st["etapa"], fin=True, **{k: v for k, v in datos.items() if k != "resultado"}))
        st.update(etapa=etapa, fase="PENDIENTE", handle=None, fallas=0); self._guardar(spec, st); return st   # fallas: por etapa

    def _fallo(self, spec, st, motivo):
        st["fallas"] = st.get("fallas", 0) + 1; st["fase"] = "PENDIENTE"
        st["historial"].append(dict(ts=self.ahora(), etapa=st["etapa"], falla=motivo[:300]))
        if st["fallas"] >= 3: return self._cerrar(spec, st, "BLOQUEADA", f"la etapa {st['etapa']} falló 3 veces ({motivo[:200]})")
        self._guardar(spec, st); return st

    def _cambios(self, spec, st) -> list:
        if st["etapa"] == "PREFLIGHT" or "spec" not in st: return []
        viejo = st["spec"]; c = [k for k in INMUTABLES if viejo.get(k) != spec.get(k)]
        d0, d1 = (viejo.get("holdout") or {}).get("desde"), (spec.get("holdout") or {}).get("desde")
        if d0 is not None and (d1 is None or int(d1) < int(d0)):
            if int(d1 or 0) != HOLDOUT_PRIMERA_SESION_INT: c.append("holdout.desde hacia atrás")   # 2026-10-27 (Nico): alinear a la frontera 20261001 está permitido
        return c

    # --- un paso --------------------------------------------------------------------------------------------------------
    def avanzar(self, spec: dict) -> dict:
        falta = [k for k in CAMPOS if k not in spec]
        if falta: raise ValueError(f"campaña sin {falta}")
        st = self.estado(spec)
        if st["etapa"] == "FIN": return st
        if (cambios := self._cambios(spec, st)):
            return self._cerrar(spec, st, "BLOQUEADA", f"la campaña cambió después del PREFLIGHT ({cambios}): es otra campaña, con cid y registro propios")
        e = st["etapa"]
        if e != "PREFLIGHT" and not st.get("decisiones_20261024"):
            st = self._revalidar_20261024(spec, st)
            if st["etapa"] == "FIN": return st
        if e == "PREFLIGHT": return self._preflight(spec, st)
        if e == "ACTA": return self._acta(spec, st)
        if e == "OOS" and not spec.get("oos"): return self._siguiente(spec, st, "ATRAS", nota="sin período OOS declarado")
        if e == "OOS" and st.get("oos_cubierto_por_pistas"):                       # la réplica de pistas ya usó ese período
            return self._siguiente(spec, st, "ATRAS", nota="el OOS es la ventana donde se replicaron las pistas: no se reusa")
        if e == "ATRAS" and not spec.get("atras"): return self._siguiente(spec, st, "TOPES", nota="sin período hacia atrás declarado")
        params, periodo, runner = self._params(spec, st, e)
        if e == "CONTEO" and st.get("ultimo_conteo") and self.ahora() - st["ultimo_conteo"] < _reglas(spec, st, "holdout")["conteo_cada_s"]: return st
        if st["fase"] == "PENDIENTE":
            self._registrar(spec, e, params)
            st["handle"] = self.runners[runner].lanzar(spec, "HOLDOUT_CONTEO" if e == "CONTEO" else ("REP" if e in ("OOS", "HOLDOUT", "PISTAS", "ATRAS") else e), params, periodo)
            st.update(fase="CORRIENDO", params=params, periodo=periodo, lanzada=self.ahora()); self._guardar(spec, st); return st
        est = self.runners[runner].estado(st["handle"])
        if est in ("running", "queued"):
            if runner == "kaggle" and st.get("lanzada") and self.ahora() - st["lanzada"] > MAX_HORAS_KAGGLE * 3600:
                return self._fallo(spec, st, f"sin terminar después de {MAX_HORAS_KAGGLE} h")          # antes esperaba para siempre
            return st
        if est == "no_encontrado":                  # 2026-10-30: Kaggle da 404 unos minutos después del push; antes contaba como falla y relanzaba
            if self.ahora() - (st.get("lanzada") or 0) < GRACIA_NO_ENCONTRADO_S: return st          # el mismo slug 3 veces en 30 min -> BLOQUEADA con el kernel completo
            est = "error (Kaggle no encuentra el kernel después de la gracia)"
        if est != "complete": return self._fallo(spec, st, f"{est}: {getattr(self.runners[runner], 'ultimo_detalle', '')}".strip(": "))
        try: res = self.runners[runner].traer(st["handle"])
        except Exception as ex: return self._fallo(spec, st, f"no se pudo traer el resultado: {ex!r}")
        from edgelab.research.preflight import codigo_vigente                     # error 23: código que cambió después de lanzar
        if (cambio := codigo_vigente(res)):
            st.setdefault("codigo_cambiado", []).append(dict(etapa=e, modulos=cambio))
            self._medido(spec, f"- AVISO {e}: el resultado se calculó con módulos que cambiaron después ({cambio}); revisar si el cambio toca la medición")
        return getattr(self, f"_fin_{e.lower()}")(spec, st, res)

    def _params(self, spec, st, e):
        base = dict(cortes=st.get("cortes"))
        if e == "DESC": return dict(cortes=None), spec["desc"], "kaggle"
        if e == "INDAGA": return dict(base, bases=st["candidatas"]), spec["desc"], "kaggle"
        if e in ("INTEGRIDAD", "TOPES"): return dict(base, celdas=st["candidatas"], topes=_reglas(spec, st, "topes")["lista"] or None), spec["desc"], "kaggle"
        if e == "OOS": return dict(base, celdas=st["candidatas"], resolucion=self._resolucion(spec, len(st["candidatas"]))), spec["oos"], "kaggle"
        if e == "ATRAS": return dict(base, celdas=st["candidatas"], resolucion=None), [int(x) for x in spec["atras"]], "kaggle"
        if e == "PISTAS":
            pr = st["pistas_replica"]
            return dict(base, celdas=pr["celdas"], resolucion=self._resolucion(spec, len(pr["celdas"]))), pr["ventana"], "kaggle"
        h = _reglas(spec, st, "holdout"); hasta = int(time.strftime("%Y%m%d", time.gmtime(self.ahora() - 86400)))
        regla = st["regla"]
        return dict(base, celdas=[regla["celda"]], tope=regla["tope"], acta=st.get("acta")), [h["desde"], hasta], ("sellado" if "sellado" in self.runners else "local")

    def _resolucion(self, spec, m):
        """Nivel de LORD++ que va a tener el lote y su tamaño: el kernel ajusta B (o usa el p analítico) para poder resolver nivel/m."""
        return dict(nivel=float(self.libro.nivel(spec["familia"])), m=int(m)) if self.libro else None

    def _registrar(self, spec, e, params):
        """Pruebas con desenlace al contador global ANTES de lanzar. DESC: todas las celdas en los dos canales (total y reciente);
        antes, una campaña sin `n_celdas_por_canal` registraba 2 pruebas para una grilla de millones. TOPES: las variantes con
        tope que se corren de verdad (antes 6 fijas aunque la campaña declarara otra lista)."""
        n = None
        if e == "DESC":
            n = spec.get("n_celdas_por_canal")
            if not n: raise ValueError("DESC sin n_celdas_por_canal: el contador global no puede quedar corto (lo fija el PREFLIGHT)")
            n = int(n) * 2
        elif e in ("OOS", "PISTAS", "ATRAS"): n = len(params.get("celdas", []))           # PISTAS: las k congeladas, antes de correr
        elif e == "TOPES":
            from edgelab.research.etapas import TOPES_ESTANDAR
            n = len(params.get("celdas", [])) * sum(t is not None for t in (params.get("topes") or TOPES_ESTANDAR))
        elif e == "HOLDOUT": n = 1
        if n and self.registro is None: raise RuntimeError(f"etapa {e} con desenlaces sin registro de pruebas: no se lanza")   # auditoría 2026-10-24
        if n: self.registro.ensure(f"embudo/{spec['cid']}/{e.lower()}", spec["familia"], int(n), f"embudo {spec['cid']} etapa {e}")

    # --- compuertas -----------------------------------------------------------------------------------------------------
    def _preflight(self, spec, st):
        from edgelab.research.preflight import verificar_experimento
        r = verificar_experimento(spec["experimento"], dinamico_tambien=spec.get("preflight_dinamico", True))
        self._medido(spec, f"## {spec['cid']} — {spec['experimento']} · señal {spec['sensor']} · ejecución {spec.get('ejecucion') or spec['sensor']}\n"
                           f"- Justificación: {spec['justificacion_economica']}\n- Refutación: {spec['como_podria_refutarse']}\n- PREFLIGHT: {'ok' if r['ok'] else r['errores']}")
        if not r["ok"]: return self._cerrar(spec, st, "BLOQUEADA", f"preflight: {r['errores'][:3]}")
        if (malos := problemas_campana(spec)):
            self._medido(spec, f"- PREFLIGHT de la campaña: {malos}"); return self._cerrar(spec, st, "BLOQUEADA", f"campaña: {malos[:3]}")
        from edgelab.research.potencia_previa import informe_previo              # 2026-10-26: informativo, no bloquea
        if (pp := informe_previo(spec, _meses)):
            st["potencia_previa"] = pp
            self._medido(spec, f"- Potencia previa declarada: MDE DESC {pp['desc']['mde']:.3g}, OOS {pp.get('oos', {}).get('mde', float('nan')):.3g}, "
                               f"holdout {pp['holdout']['mde']:.3g}; meses para el efecto útil {pp.get('meses_necesarios')}")
        reglas = {k: _cfg(spec, k) for k in DEFECTOS}
        if (malos := _problemas_regimen(reglas["regimen"]) + self._problemas_linaje(spec)):
            return self._cerrar(spec, st, "BLOQUEADA", "; ".join(malos))
        reglas["pistas_replica"] = dict(reglas["pistas_replica"], ventana=ventana_pistas(spec, reglas["pistas_replica"]))
        st["reglas"] = dict(reglas, linaje=dict(self._multiplicidad(spec), como=spec.get("linaje_como", "informacion")))   # antes de usarse
        st["spec"] = spec                                                              # la campaña que se congela
        st["decisiones_20261024"] = dict(ts=self.ahora(), desde="PREFLIGHT")
        lin = st["reglas"]["linaje"]
        self._medido(spec, f"- Linaje ({lin['como']}; {lin.get('metodo_n', 'bruto')}{'; ' + lin['aviso'] if lin.get('aviso') else ''}); pistas a réplica "
                           f"k {reglas['pistas_replica']['k']} en {reglas['pistas_replica']['ventana']}")
        self._medido(spec, f"- Linaje: hereda {st['reglas']['linaje']['n_heredado']} pruebas de {st['reglas']['linaje'].get('padres')}; "
                           f"régimen actual desde {reglas['regimen']['actual_desde'] or 'sin declarar (el OOS cuenta como régimen actual)'}")
        return self._siguiente(spec, st, "DESC")

    # --- decisiones del 2026-10-24 ----------------------------------------------------------------------------------------
    def _problemas_linaje(self, spec):
        from edgelab.research import linaje as LN
        return LN.problemas(spec["familia"], Path(self.linajes) if self.linajes else LN.LIBRO, Path(self.ventanas) if self.ventanas else None,
                            Path(self.registro_pruebas) if self.registro_pruebas else LN.REGISTRO)

    def _evaluables(self, spec, res):
        """Decisión 2026-10-25: cuántas de las 2·n_celdas registradas fueron evaluables (>= MIN_OPS operaciones) en los dos canales.
        Sólo eso hereda multiplicidad por linaje; el registro previo queda como cota (`linaje.registrar_evaluables`)."""
        from edgelab.research import linaje as LN
        can = res.get("canales") or {}; n_ev = sum(int((can.get(c) or {}).get("evaluables") or 0) for c in ("total", "reciente"))
        n_reg = 2 * int(spec.get("n_celdas_por_canal") or 0)
        if not self.registro or not n_reg or not can: return None
        libro = Path(self.registro_pruebas).with_name("EVALUABLES.jsonl") if self.registro_pruebas else LN.EVALUABLES
        row = LN.registrar_evaluables(f"embudo/{spec['cid']}/desc", spec["familia"], n_reg, min(n_ev, n_reg), f"DESC {spec['cid']} (canales total+reciente)", libro)
        self._medido(spec, f"- Evaluables: {row['n_evaluables']} de {n_reg} celdas registradas heredan multiplicidad (el resto no llegó a {GG_MIN_OPS} operaciones)")
        return row

    def _multiplicidad(self, spec):
        from edgelab.research import linaje as LN
        return LN.multiplicidad(spec["familia"], Path(self.linajes) if self.linajes else LN.LIBRO,
                                Path(self.registro_pruebas) if self.registro_pruebas else LN.REGISTRO)

    def _revalidar_20261024(self, spec, st):
        """Campañas que pasaron DESC antes del 2026-10-24: se les aplican las decisiones nuevas antes de seguir (sólo endurecen).
        Congela régimen y linaje si faltan, y vuelve a filtrar las candidatas por la nominación FDR con el linaje cobrado."""
        reglas = st.setdefault("reglas", {})
        reglas.setdefault("regimen", _cfg(spec, "regimen"))
        if (malos := _problemas_regimen(reglas["regimen"]) + self._problemas_linaje(spec)):
            return self._cerrar(spec, st, "BLOQUEADA", "decisiones 2026-10-24: " + "; ".join(malos))
        reglas.setdefault("linaje", self._multiplicidad(spec))
        st["decisiones_20261024"] = dict(ts=self.ahora(), desde=st["etapa"])
        if st["etapa"] in ("INDAGA", "INTEGRIDAD", "OOS", "TOPES", "ACTA") and st.get("candidatas"):
            pistas = (st.get("desc") or {}).get("pistas", [])
            nh = reglas["linaje"]["n_heredado"]
            vivas = [c for c in st["candidatas"] if any(p["celda"] == c and nominada(p, nh, _como_linaje(st))[0] for p in pistas)]
            if st.get("regla") and st["regla"]["celda"] not in vivas: vivas = []        # en ACTA la regla ya está elegida
            if not vivas:
                return self._cerrar(spec, st, "SIN_CANDIDATAS", f"decisión 2026-10-24 (FDR q {Q_FDR_DESC} gate duro en DESC, con linaje de {nh} "
                                                                 f"pruebas): ninguna de las {len(st['candidatas'])} candidatas está nominada ({DECISIONES_20261024})")
            st["candidatas"] = vivas
        self._medido(spec, f"- Decisiones 2026-10-24 aplicadas en {st['etapa']} (después de DESC: sólo endurecen); linaje {reglas['linaje']['n_heredado']}")
        self._guardar(spec, st); return st

    def _fin_desc(self, spec, st, res):
        n_reg = spec.get("n_celdas_por_canal")
        if n_reg and res.get("celdas") is not None and int(res["celdas"]) != int(n_reg):
            return self._cerrar(spec, st, "BLOQUEADA", f"el contador global registró {n_reg} celdas por canal y se corrieron {res['celdas']}: "
                                                       "la multiplicidad quedó mal contada (corregir y relanzar como campaña nueva)")
        sel = _reglas(spec, st, "seleccion"); st["cortes"] = res["E0"]["cortes"]; cand, vistos = [], []
        nh = ((st.get("reglas") or {}).get("linaje") or {}).get("n_heredado", 0); no_nom = 0; como = _como_linaje(st)
        pistas = [p for c in (res.get("canales") or {}).values() for p in c.get("pistas", [])]
        # 2026-10-25: una candidata tiene que poder confirmarse. Las 3 de U1-ES-GRILLA tenían 30-37 operaciones en 26 meses y dieron
        # 6, 1 y 0 en el OOS de 6 meses (NO_CONCLUYENTE sin potencia, y un holdout de 150 operaciones imposible). La frecuencia es un
        # dato target-free: se exige que la del DESC prometa >= min_ops_oos operaciones en la ventana OOS. Sólo endurece la selección.
        meses_can = {id(p): max(1, len(c.get("meses") or []) or _meses(spec.get("desc"))) for c in (res.get("canales") or {}).values() for p in c.get("pistas", [])}
        m_oos = _meses(spec.get("oos")) if spec.get("oos") else 0
        try:                                                      # escala causal mensual (u1_oro y derivados): el 1.er mes del OOS no dispara
            import importlib
            if m_oos and hasattr(importlib.import_module(spec["experimento"]), "escala_por_mes"): m_oos -= 1
        except ImportError:
            pass
        # 2026-10-24 (falsos negativos): la meseta ORDENA (primero las que la tienen), no mata; 4 de las 5 celdas de U1 no la tenían
        orden = (lambda p: (not p.get("meseta", False), -p["ic90"][0])) if sel["exigir_meseta"] else (lambda p: -p["ic90"][0])
        for p in sorted(pistas, key=orden):
            ok_fdr, p["q_linaje"] = nominada(p, nh, como)
            if not ok_fdr: no_nom += 1; continue                                     # decisión 1 (2026-10-24): gate duro
            if p["sesiones"] < sel["min_sesiones"] or p["ratio_mov_friccion"] < sel["ratio_mov_friccion"] or p["ic90"][0] <= 0: continue
            if m_oos and sel.get("min_ops_oos") and p["n"] / meses_can[id(p)] * m_oos < sel["min_ops_oos"]: continue
            if any(sum(a != b for a, b in zip(p["celda"], v)) < sel["min_dif"] for v in vistos): continue
            vistos.append(p["celda"]); cand.append(p["celda"])
            if len(cand) >= sel["max_candidatas"]: break
        tot = (res.get("canales") or {}).get("total", {})
        self._evaluables(spec, res)
        self._medido(spec, f"- DESC {spec['desc']}: evaluables {tot.get('evaluables')} (m del FDR {tot.get('m_fdr', tot.get('evaluables'))} de "
                           f"{tot.get('celdas', '?')} celdas), FDR {tot.get('nominadas_fdr')}, RW umbral {(tot.get('romano_wolf') or {}).get('umbral')} "
                           f"(diagnóstico), linaje {nh} como {como}, pistas sin nominación {no_nom}, candidatas {len(cand)}")
        if not cand: return self._a_pistas(spec, st, pistas, tot)
        st["candidatas"] = cand; st["desc"] = dict(pistas=[p for p in pistas if p["celda"] in cand])
        from edgelab.research.potencia_previa import por_candidata                 # 2026-10-26: informativo, no mata
        pp = [por_candidata(p, meses_can[id(p)], m_oos, int(_reglas(spec, st, "holdout")["n_fijo"]), _reglas(spec, st, "regimen")["fraccion_efecto"])
              for p in pistas if p["celda"] in cand]
        st["potencia_prevista"] = pp
        self._medido(spec, "- Potencia prevista (informativa): " + "; ".join(
            f"{x['celda']}: OOS n {x.get('oos', {}).get('n')} potencia {x.get('oos', {}).get('potencia', 0):.2f}, holdout n {x['holdout']['n']} "
            f"potencia {x['holdout']['potencia']:.2f}" for x in pp))
        return self._siguiente(spec, st, "INDAGA", candidatas=cand)

    def _a_pistas(self, spec, st, pistas, tot):
        """ATJ-25 restaurada (2026-10-24): cero nominadas no cierra la familia. Las top-k pistas (por cota inferior del IC, nunca por
        P&L máximo) se congelan acá —antes de registrarlas y de lanzar— y se replican en lote en la ventana reciente no usada."""
        from edgelab.funnel.escalera import elegir_pistas_replica
        cfg = _reglas(spec, st, "pistas_replica"); sel = _reglas(spec, st, "seleccion")
        ventana = cfg.get("ventana") or ventana_pistas(spec, cfg)
        cierre = f"ninguna pista nominada por FDR q {Q_FDR_DESC} cumple la selección; nulo publicado ({tot.get('nulo', {}).get('t', {})})"
        if not cfg.get("activa", True) or not ventana or int(cfg.get("k") or 0) <= 0:
            if cfg.get("activa", True) and cfg.get("k"):                        # sin dónde replicar no hubo prueba: no es una refutación
                return self._cerrar(spec, st, "PISTAS_VIVAS", cierre + "; pistas a réplica: sin ventana reciente no usada declarada (no se pudo probar)")
            return self._cerrar(spec, st, "SIN_CANDIDATAS", cierre + "; pistas a réplica: apagada por la campaña")
        elegidas = elegir_pistas_replica(pistas, int(cfg["k"]), min_dif=sel["min_dif"], min_sesiones=sel["min_sesiones"],
                                         ratio_mov_friccion=sel["ratio_mov_friccion"])
        if not elegidas: return self._cerrar(spec, st, "SIN_CANDIDATAS", cierre + "; pistas a réplica: ninguna pista relevante con media > 0")
        st["pistas_replica"] = dict(k=int(cfg["k"]), ventana=list(ventana), orden="cota inferior IC90 por sesiones (desc), desempate t Romano-Wolf",
                                    congeladas=self.ahora(), celdas=[p["celda"] for p in elegidas])
        st["desc"] = dict(pistas=elegidas)
        self._medido(spec, f"- PISTAS a réplica (ATJ-25): {len(elegidas)} congeladas de {len(pistas)} (k {cfg['k']}), ventana {ventana}, "
                           f"un paso de LORD++ por lote; celdas {st['pistas_replica']['celdas']}")
        return self._siguiente(spec, st, "PISTAS", pistas=len(elegidas))

    def _fin_pistas(self, spec, st, res):
        """Un paso de LORD++ de la familia para el lote entero (`probar_lote`: Simes para la familia, BH adentro, al nivel del paso).
        Las confirmadas con media > 0 quedan nominadas (`nominada_replica`) y siguen a INDAGA; el resto queda registrado."""
        from edgelab.funnel.escalera import canasta_pistas, decidir_pistas, veredicto_pistas
        pr_ = st["pistas_replica"]; filas = res.get("replica") or []
        if len(filas) != len(pr_["celdas"]): return self._fallo(spec, st, f"réplica de pistas con {len(filas)} filas para {len(pr_['celdas'])} celdas")
        # 2026-10-26 (Nico, auditoría del filtro): primero la CANASTA de las k pistas como una sola prueba, con su propio paso de LORD++
        can = canasta_pistas(res.get("operaciones"), len(filas))
        dec_can = (self.libro.probar(spec["familia"], f"{spec['cid']}/pistas_canasta", [("canasta", can["p"])], f"canasta de pistas {spec['cid']}")
                   if self.libro and can.get("p") is not None else None)
        pr_["canasta"] = dict(can, lord=dec_can)
        self._medido(spec, f"- PISTAS canasta (una prueba): media {can.get('media')} IC90 {can.get('ic90')} p {can.get('p')} sesiones "
                           f"{can.get('n_sesiones')}; LORD++ {'rechaza' if (dec_can or {}).get('rechazo') else 'sin rechazo'} (nivel {(dec_can or {}).get('nivel')})")
        nombres = [f"p{i}" for i in range(len(filas))]
        pruebas = [(n, r.get("p_sesiones") if r.get("p_sesiones") is not None else 1.0) for n, r in zip(nombres, filas)]
        dec = self.libro.probar(spec["familia"], f"{spec['cid']}/pistas", pruebas, f"pistas a réplica {spec['cid']} (lote de {len(pruebas)})") if self.libro else None
        ok = decidir_pistas(dec, filas, nombres)
        for i, (p, r) in enumerate(zip(st["desc"]["pistas"], filas)):
            p["replica_pistas"] = dict(n=r.get("n"), media=r.get("media_neta"), ic90=r.get("ic90"), p=r.get("p_sesiones"), metodo_p=r.get("metodo_p"),
                                       nivel=(dec or {}).get("nivel"), t_lord=(dec or {}).get("t"), confirmada=i in ok)
            if i in ok: p["nominada_replica"] = True
        pr_.update(lord=dec, confirmadas=[pr_["celdas"][i] for i in ok])
        if (aviso := _aviso_resolucion(dec, filas, len(filas))): pr_["sin_resolucion"] = aviso; self._medido(spec, f"- PISTAS: {aviso}")
        self._medido(spec, f"- PISTAS réplica {pr_['ventana']}: LORD++ t={(dec or {}).get('t')} nivel {(dec or {}).get('nivel')} p Simes "
                           f"{(dec or {}).get('p_simes')}; confirmadas {len(ok)} de {len(filas)} {pr_['confirmadas']}")
        reg = _reglas(spec, st, "regimen")
        media_desc = float(np.mean([p["media_neta"] for p in st["desc"]["pistas"]])) if st["desc"]["pistas"] else 0.0
        ver = veredicto_pistas(ok, can, dec_can, media_desc, reg["fraccion_efecto"], reg["potencia_min"]); pr_["veredicto"] = ver
        if ver["veredicto"] == "CANASTA_CONFIRMADA" and not ok:                 # la canasta confirma: siguen sus pistas con media > 0
            ok = [i for i, r in enumerate(filas) if (r.get("media_neta") or 0) > 0]
            for i in ok: st["desc"]["pistas"][i]["nominada_replica"] = True
        if not ok:
            texto = (f"pistas a réplica: 0 de {len(filas)} confirmadas una por una (nivel {(dec or {}).get('nivel')}, p Simes {(dec or {}).get('p_simes')}); "
                     f"canasta media {can.get('media')} IC90 {can.get('ic90')}; {ver.get('motivo', '')}; potencia de la canasta {ver.get('potencia')}")
            return self._cerrar(spec, st, "SIN_CANDIDATAS" if ver["veredicto"] == "REFUTADA" else "PISTAS_VIVAS", texto)
        sel = _reglas(spec, st, "seleccion")
        orden = sorted(ok, key=lambda i: (filas[i].get("p_sesiones") or 1.0, -(filas[i].get("ic90") or [0])[0]))
        cand = [pr_["celdas"][i] for i in orden[:sel["max_candidatas"]]]
        if len(orden) > sel["max_candidatas"]: pr_["confirmadas_fuera_de_cupo"] = [pr_["celdas"][i] for i in orden[sel["max_candidatas"]:]]
        st["oos_cubierto_por_pistas"] = bool(spec.get("oos") and [int(x) for x in spec["oos"]] == [int(x) for x in pr_["ventana"]])
        st["candidatas"] = cand
        return self._siguiente(spec, st, "INDAGA", candidatas=cand)

    def _fin_indaga(self, spec, st, res):
        st["indagacion"] = res.get("por_base"); self._medido(spec, f"- INDAGA: marginales de {len(res.get('por_base') or [])} candidatas guardadas")
        return self._siguiente(spec, st, "INTEGRIDAD")

    def _fin_integridad(self, spec, st, res):
        cfg = _reglas(spec, st, "integridad"); al = res.get("alineacion"); n = len(st["candidatas"])
        if any(len(_por_lat(res["latencia"], r)) not in (0, n) for r in (0, 1, 2, 5) if _por_lat(res["latencia"], r)):
            return self._fallo(spec, st, "latencia con una lista por celda desalineada (kernel anterior al fix por_celda): se relanza")
        if al and al.get("pico_lag_s") is not None and al["pico_lag_s"] > 0:
            return self._cerrar(spec, st, "INTEGRIDAD_FALLA", f"alineación: la señal adelanta a la ejecución ({al['pico_lag_s']} s)")
        quedan = []
        for i, c in enumerate(st["candidatas"]):
            lat = res["latencia"]; r0 = _de(_por_lat(lat, 0), i).get("media"); r1 = _de(_por_lat(lat, 1), i).get("media")
            pl = res["placebo"].get(i, res["placebo"].get(str(i))) or []
            plac = float(np.nanmean(pl)) if np.isfinite(np.asarray(pl, float)).any() else float("nan")       # sin placebo: no pasa
            ok = r0 is not None and r0 > 0 and np.isfinite(plac) and plac <= cfg["placebo_max_frac"] * r0 and (not cfg["latencia_1_positiva"] or (r1 or -1) > 0)
            self._medido(spec, f"- INTEGRIDAD {c}: regla {r0}, placebo {plac:.2f}, latencia 1 vela {r1} -> {'pasa' if ok else 'no pasa'}")
            if ok: quedan.append(c)
        if not quedan: return self._cerrar(spec, st, "INTEGRIDAD_FALLA", "ninguna candidata pasa placebo/latencia")
        st["candidatas"] = quedan; return self._siguiente(spec, st, "OOS")

    def _fin_oos(self, spec, st, res):
        """Decisión 2 (2026-10-24, con el matiz de régimen de Nico): por candidata,
          REFUTADA_OOS           potencia >= potencia_min para fraccion_efecto x media de DESC, IC90 entero < 0 y OOS en el régimen actual;
          EN_CONTRA_OTRO_REGIMEN igual, pero el OOS cae entero antes de `regimen.actual_desde` (declarado antes): no mata;
          NO_CONCLUYENTE         sin potencia declarada (o no evaluable): no mata, no suma;
          A_FAVOR / SIN_RECHAZO  según el paso de LORD++ de la familia.
        La confirmación de una candidata viva sigue saliendo del holdout (régimen actual), nunca del OOS."""
        from edgelab.funnel.escalera import ALFA_CONFIRMACION, potencia
        pr = [(f"c{i}", r.get("p_sesiones", 1.0) if r.get("p_sesiones") is not None else 1.0) for i, r in enumerate(res["replica"])]
        dec = self.libro.probar(spec["familia"], f"{spec['cid']}/oos", pr) if self.libro else None
        reg = _reglas(spec, st, "regimen"); a_oos, b_oos = int(spec["oos"][0]), int(spec["oos"][1])
        mismo = reg.get("actual_desde") is None or b_oos >= int(reg["actual_desde"])
        conf = {c["test"] for c in (dec or {}).get("confirmadas", [])}
        pistas = (st.get("desc") or {}).get("pistas", []); veredictos, vivas = [], []
        for i, (c, r) in enumerate(zip(st["candidatas"], res["replica"])):
            md = next((p["media_neta"] for p in pistas if p["celda"] == c), None); ic = r.get("ic90")
            if not ic or r.get("media_neta") is None or md is None or md <= 0:
                v = dict(celda=c, veredicto="NO_CONCLUYENTE", motivo="no evaluable en el OOS"); veredictos.append(v); vivas.append(c); continue
            se = (ic[1] - ic[0]) / (2 * 1.6448536); ef = reg["fraccion_efecto"] * md; pot = potencia(ef, se, ALFA_CONFIRMACION)
            en_contra = ic[1] < 0
            if not pot == pot: ver = "NO_CONCLUYENTE"                                  # se no finito: sin potencia medible
            elif en_contra and pot >= reg["potencia_min"]: ver = "REFUTADA_OOS" if mismo else "EN_CONTRA_OTRO_REGIMEN"
            elif pot < reg["potencia_min"]: ver = "NO_CONCLUYENTE"
            else: ver = "A_FAVOR" if f"c{i}" in conf else "SIN_RECHAZO"
            veredictos.append(dict(celda=c, veredicto=ver, media=r["media_neta"], ic90=ic, efecto_para_potencia=ef, potencia=pot, mismo_regimen=mismo))
            if ver != "REFUTADA_OOS": vivas.append(c)
        st["oos"] = dict(replica=res["replica"], lord=dec, regimen=reg, mismo_regimen=mismo, veredictos=veredictos)
        if (aviso := _aviso_resolucion(dec, res["replica"], len(res["replica"]))): st["oos"]["sin_resolucion"] = aviso; self._medido(spec, f"- OOS: {aviso}")
        self._medido(spec, f"- OOS {spec['oos']} ({'régimen actual' if mismo else 'otro régimen: antes de ' + str(reg['actual_desde'])}): "
                           f"medias {[round(r.get('media_neta', float('nan')), 2) for r in res['replica']]}; "
                           f"veredictos {[v['veredicto'] for v in veredictos]}; potencias {[round(v.get('potencia', float('nan')), 2) for v in veredictos]}; LORD++ "
                           f"{'confirma ' + str([c['test'] for c in dec['confirmadas']]) if dec and dec['rechazo'] else 'sin rechazo'}")
        if not vivas: return self._cerrar(spec, st, "REFUTADA_OOS", f"todas las candidatas refutadas en un OOS con potencia y del régimen actual ({DECISIONES_20261024})")
        st["candidatas"] = vivas
        return self._siguiente(spec, st, "ATRAS")

    def _fin_atras(self, spec, st, res):
        """Informativa (2026-10-26): no cambia `candidatas`. Con potencia y en contra = EN_CONTRA_PASADO (el edge, si existe, es del
        régimen actual: lo decide el holdout); sin potencia = NO_CONCLUYENTE; IC90 entero > 0 = A_FAVOR; si no, SIN_RECHAZO."""
        from edgelab.funnel.escalera import ALFA_CONFIRMACION, potencia
        reg = _reglas(spec, st, "regimen"); pistas = (st.get("desc") or {}).get("pistas", []); ver = []
        for c, r in zip(st["candidatas"], res.get("replica") or []):
            md = next((p["media_neta"] for p in pistas if p["celda"] == c), None); ic = r.get("ic90")
            if not ic or r.get("media_neta") is None or md is None or md <= 0: ver.append(dict(celda=c, veredicto="NO_CONCLUYENTE", n=r.get("n"))); continue
            se = (ic[1] - ic[0]) / (2 * 1.6448536); pot = potencia(reg["fraccion_efecto"] * md, se, ALFA_CONFIRMACION)
            v = ("NO_CONCLUYENTE" if not pot == pot or pot < reg["potencia_min"] else "EN_CONTRA_PASADO" if ic[1] < 0
                 else "A_FAVOR" if ic[0] > 0 else "SIN_RECHAZO")
            ver.append(dict(celda=c, veredicto=v, n=r.get("n"), media=r["media_neta"], ic90=ic, media_desc=md, potencia=pot))
        st["atras"] = dict(periodo=spec["atras"], veredictos=ver, nota="informativa: no mata (ATJ-24)")
        self._medido(spec, f"- ATRAS {spec['atras']} (informativa, no mata): {[(v['veredicto'], round(v.get('media', float('nan')), 2), v.get('n')) for v in ver]}")
        return self._siguiente(spec, st, "TOPES")

    def _fin_topes(self, spec, st, res):
        cfg = _reglas(spec, st, "topes"); mejor = None; n = len(st["candidatas"])
        if any(len(filas) not in (0, n) for filas in res["por_tope"].values()):
            return self._fallo(spec, st, "topes con una lista por celda desalineada (kernel anterior al fix por_celda): se relanza")
        for i, c in enumerate(st["candidatas"]):
            sin = _de(res["por_tope"].get("sin tope"), i).get("por_mitad")
            if not sin: continue                                                           # la celda no operó sin tope
            for nombre, filas in res["por_tope"].items():
                if nombre == "sin tope": continue
                f = _de(filas, i); mit = f.get("por_mitad")
                if not mit: continue
                ok = all((m.get("media") or -1) > 0 and (m.get("media") or -1) >= cfg["min_frac_sin_tope"] * (s.get("media") or 0) for m, s in zip(mit, sin))
                if not ok or f.get("drawdown_max") is None: continue
                puntaje = f["total"] / abs(f["drawdown_max"]) if f["drawdown_max"] else float("inf")   # sin drawdown: la mejor, no excluida
                tope = [nombre.split(":")[0], float(nombre.split(":")[1])]
                if mejor is None or puntaje > mejor["puntaje"]: mejor = dict(celda=c, tope=tope, puntaje=puntaje, peor=f.get("peor"))
        self._medido(spec, f"- TOPES: {'elegida ' + str(mejor) if mejor else 'ninguna variante con tope conserva el resultado en las dos mitades'}")
        if not mejor: return self._cerrar(spec, st, "SIN_REGLA_OPERABLE", "ningún tope conserva el edge (la pérdida máxima no se puede acotar)")
        st["regla"] = mejor; return self._siguiente(spec, st, "ACTA")

    def _acta(self, spec, st):
        h = _reglas(spec, st, "holdout")
        from edgelab.research import holdout_ventanas as HV                      # ventanas consumidas y una apertura por familia
        libro_v = Path(self.ventanas) if getattr(self, "ventanas", None) else HV.LIBRO
        est = h.get("estadistico", "n_fijo")                                       # D5 (2026-10-24): e_proceso permite el reuso autorizado
        if est not in ("n_fijo", "e_proceso", "canasta_regimen"): return self._cerrar(spec, st, "BLOQUEADA", f"holdout.estadistico {est!r}: n_fijo | e_proceso | canasta_regimen")
        cotas = {k: h.get(k) for k in COTAS_E_PROCESO}
        if est == "e_proceso" and (faltan := [k for k, v in cotas.items() if not isinstance(v, (int, float)) or v <= 0]):
            return self._cerrar(spec, st, "BLOQUEADA", f"e-proceso sin cotas estructurales declaradas antes de mirar: {faltan}")
        if (malos := HV.problemas(spec["familia"], h["desde"], spec["cid"], libro_v, estadistico=est)):
            return self._cerrar(spec, st, "BLOQUEADA", "; ".join(malos))
        # Compuerta de potencia (2026-10-26, decisión de Nico; error E8): la única apertura de la familia no se gasta sin poder decidir.
        # 2026-10-27 (Nico): en `canasta_regimen` el riesgo se diversifica en la canasta y se evalúa si el rendimiento en el período
        # reducido de holdout está dentro de la desviación esperada (sin exigir esperar años a un n_fijo de alta potencia individual).
        plan = self._plan_holdout(spec, st, h)
        st["plan_holdout"] = plan
        if est != "canasta_regimen" and plan.get("n_fijo") is None:
            return self._cerrar(spec, st, "SIN_POTENCIA_HOLDOUT", f"potencia del holdout < {h['potencia_min']} aun con N máximo {h['n_max']} "
                                                                  f"({plan}); la familia sigue viva, sin gastar su apertura")
        n_acta = int(h.get("n_min_canasta", 1)) if est == "canasta_regimen" else int(plan["n_fijo"])
        h = dict(h, n_fijo=n_acta)
        # decisión 3 (2026-10-24): el acta RESERVA su paso de LORD++ (consume α ahora, con el nivel fijo) antes de mirar
        reserva = self.libro.reservar(spec["familia"], f"{spec['cid']}/holdout", f"acta {spec['cid']}") if self.libro else None
        alfa = reserva["nivel"] if reserva else 0.05
        acta = dict(cid=spec["cid"], familia=spec["familia"], experimento=spec["experimento"], sensor=spec["sensor"], ejecucion=spec.get("ejecucion"),
                    regla=st["regla"], cortes=st["cortes"], holdout_desde=h["desde"], n_fijo=h["n_fijo"], alfa=alfa, registrada=self.ahora(),
                    reserva_lord=reserva, multiplicidad=self._acta_multiplicidad(spec, st, h["n_fijo"]),
                    regimen=(st.get("reglas") or {}).get("regimen"), oos=[v["veredicto"] for v in (st.get("oos") or {}).get("veredictos", [])],
                    atras=[v["veredicto"] for v in (st.get("atras") or {}).get("veredictos", [])],
                    decision=f"primeras {h['n_fijo']} operaciones desde {h['desde']}: el paso RESERVADO de LORD++ de la familia (α={alfa:.5f}); "
                             "CONFIRMADA si rechaza y media > 0; REFUTADA si media ≤ 0; si no, SIN_POTENCIA")
        if est == "canasta_regimen":
            acta.update(estadistico=est,
                        decision=f"canasta de régimen desde {h['desde']} (n >= {h['n_fijo']}): CONFIRMADA para la canasta si la media observada "
                                 f"en el período reducido de holdout está dentro de la desviación esperada (media esperada={plan.get('efecto')}, "
                                 f"sd_op={plan.get('sd_op')}); REFUTADA si cae por debajo de la banda inferior esperada.")
        if est == "e_proceso":
            acta.update(estadistico=est, cotas=cotas, vistas_hasta=HV.ultima_consumida(spec["familia"], libro_v),
                        decision=f"e-proceso (Ville) sobre las operaciones netas desde {h['desde']}, en cada conteo, hasta {h['n_fijo']}: "
                                 f"CONFIRMADA si e ≥ 1/α (α={alfa:.5f}, el paso RESERVADO de LORD++) y media > 0; REFUTADA si la futilidad "
                                 f"(E[x] < {cotas['mu_util']}) llega a e ≥ 10; SIN_POTENCIA si llega a N sin decidir. Se informa también "
                                 "sin las sesiones ya miradas (D5).")
        (self._dir(spec) / "ACTA_HOLDOUT.json").write_text(json.dumps(acta, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        acta["plan_holdout"] = st.get("plan_holdout")
        (self._dir(spec) / "ACTA_HOLDOUT.json").write_text(json.dumps(acta, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        self._medido(spec, f"- ACTA registrada antes de mirar: {acta['decision']}; regla {st['regla']['celda']} tope {st['regla']['tope']}; "
                           f"plan {st.get('plan_holdout')}")
        pot_h = (acta.get("multiplicidad") or {}).get("potencia_holdout")
        if pot_h is not None and pot_h < 0.5:
            self._medido(spec, f"- AVISO ACTA: potencia del holdout {pot_h:.2f} < 0,5 con N {h['n_fijo']}: lo más probable es SIN_POTENCIA "
                               "(docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md, E8)")
        HV.registrar_apertura(spec["familia"], spec["cid"], h["desde"], h["n_fijo"], libro_v)
        if self.registro: self.registro.ensure(f"embudo/{spec['cid']}/holdout", spec["familia"], 1, "apertura de holdout por acta")
        st["acta"] = acta; return self._siguiente(spec, st, "CONTEO")

    def _plan_holdout(self, spec, st, h) -> dict:
        from edgelab.funnel.escalera import _N, potencia
        c = st["regla"]["celda"]
        p = next((x for x in (st.get("desc") or {}).get("pistas", []) if x["celda"] == c), None)
        if not p or not p.get("ic90") or not p.get("n"): return dict(n_fijo=h["n_fijo"], nota="sin estadísticas de la regla: N declarado")
        se_d = (p["ic90"][1] - p["ic90"][0]) / (2 * 1.6448536); n_d = int(p["n"]); sd_op = float(se_d * (n_d ** 0.5))
        oos = next((v for v in (st.get("oos") or {}).get("veredictos", []) if v.get("celda") == c and v.get("media") is not None), None)
        rep = (p.get("replica_pistas") or {})
        if oos and oos["media"] > 0: ef, fuente = float(oos["media"]), "OOS"
        elif rep.get("media") is not None and rep["media"] > 0: ef, fuente = float(rep["media"]), "réplica de pistas"
        else: ef, fuente = _reglas(spec, st, "regimen")["fraccion_efecto"] * float(p["media_neta"]), "fracción del DESC"
        nivel = float(self.libro.nivel(spec["familia"])) if self.libro else 0.05
        if ef <= 0: return dict(n_fijo=None, efecto=ef, sd_op=sd_op, fuente=fuente, nivel=nivel)
        z = _N.inv_cdf(1 - nivel) + _N.inv_cdf(h["potencia_min"])
        n80 = int(np.ceil(n_d * (z * se_d / ef) ** 2))
        n = max(int(h["n_fijo"]), n80)
        pot = potencia(ef, se_d * (n_d / n) ** 0.5, nivel)
        return dict(n_fijo=n if n <= int(h["n_max"]) else None, n_necesario=n80, potencia=pot, efecto=ef, sd_op=sd_op, fuente=fuente, nivel=nivel)

    def _acta_multiplicidad(self, spec, st, n_fijo):
        """Decisión 4: multiplicidad total (familia + linaje) y lo que se espera ver de la regla fuera de muestra con ese cobro
        (recorte de Harvey-Liu) y la potencia del holdout a N fijo. Se anota, no decide: la decisión es el paso de LORD++."""
        from edgelab.funnel.escalera import _N, potencia, recorte_t
        lin = ((st.get("reglas") or {}).get("linaje")) or self._multiplicidad(spec)
        total = int(lin.get("total", lin.get("propias", 0) + lin.get("n_heredado", 0)))
        p = next((x for x in (st.get("desc") or {}).get("pistas", []) if x["celda"] == st["regla"]["celda"]), None)
        info = dict(linaje=lin, total=total, linaje_como=lin.get("como", "compuerta"), metodo_n=lin.get("metodo_n", "bruto"), aviso_n=lin.get("aviso"),
                    nota="información (Harvey-Liu, efecto esperado, potencia): la decisión es el paso de LORD++ en datos nuevos")
        if not p: return info
        t = _N.inv_cdf(1 - min(max(p["p_sesiones"], 1e-12), 1 - 1e-12)); rc = recorte_t(t, max(total, 1))
        se = (p["ic90"][1] - p["ic90"][0]) / (2 * 1.6448536); esp = rc["conservado"] * p["media_neta"]
        se_h = se * (p["n"] / max(n_fijo, 1)) ** 0.5
        return dict(info, via="pista_replicada" if p.get("nominada_replica") else "nominada_fdr", q_linaje=p.get("q_linaje"),
                    recorte=rc, efecto_esperado=esp, potencia_holdout=potencia(esp, se_h) if esp > 0 else 0.0)

    def _fin_conteo(self, spec, st, res):
        n = int(res["conteo"][0]); st["ultimo_conteo"] = self.ahora(); st["n_holdout"] = n
        if st["acta"].get("estadistico") == "e_proceso" and n > st.get("n_holdout_decidido", 0):
            return self._siguiente(spec, st, "HOLDOUT", n=n)                          # e-proceso: se mira en cada conteo con datos nuevos
        if n < st["acta"]["n_fijo"]:
            st["fase"] = "PENDIENTE"; self._guardar(spec, st); return st                  # espera más sesiones (sin mirar P&L)
        return self._siguiente(spec, st, "HOLDOUT", n=n)

    def _fin_holdout_e(self, spec, st, ops, N):
        """D5: e-proceso (Ville) sobre las netas en orden temporal, válido mirando en cada conteo. Decide con TODO lo que hay desde
        `holdout.desde` (incluidas las sesiones ya miradas, reuso autorizado) y además informa el mismo monitor sin esas sesiones."""
        from edgelab.funnel.secuencial import MonitorCandidato
        from edgelab.research.embudo_runners import friccion
        a = st["acta"]; c = a["cotas"]; nivel = (a.get("reserva_lord") or {}).get("nivel", a["alfa"])
        fr = friccion(spec.get("ejecucion") or spec["sensor"])[0]
        orden = np.argsort(np.asarray(ops.get("t") or []), kind="stable")[:N]
        x = np.asarray(ops.get("neto") or [], float)[orden]; ses = np.asarray(ops.get("ses") or [], np.int64)[orden]
        def monitor(xx):
            m = MonitorCandidato.desde_regla(perdida_max_pts=c["perdida_max_pts"], ganancia_max_pts=c["ganancia_max_pts"], friccion_pts=fr,
                                             margen_hueco_pts=c["margen_hueco_pts"], mu_util=c["mu_util"], alfa=nivel)
            try: return m.agregar([float(v) for v in xx]) if len(xx) else m.estado()
            except ValueError as e: return dict(estado="LIMITE_VIOLADO", n=len(xx), error=str(e))
        todo = monitor(x); vh = a.get("vistas_hasta")
        sin = monitor(x[ses > int(vh)]) if vh else None
        st["holdout"] = dict(estadistico="e_proceso", n=int(len(x)), media=float(x.mean()) if len(x) else None, nivel=nivel, e_proceso=todo,
                             sin_sesiones_vistas=sin, vistas_hasta=vh)
        st["n_holdout_decidido"] = int(len(x))
        self._medido(spec, f"- HOLDOUT (e-proceso): n {len(x)}, {todo['estado']}" + (f"; sin las sesiones vistas: {sin['estado']} (n {sin['n']})" if sin else ""))
        if todo["estado"] == "LIMITE_VIOLADO": return self._cerrar(spec, st, "BLOQUEADA", f"e-proceso: {todo['error']} (la cota declarada no era estructural)")
        if todo["estado"] == "EDGE_CONFIRMADO" and x.mean() > 0:
            return self._cerrar(spec, st, "CONFIRMADA", f"e-proceso {todo['e_edge']:.1f} ≥ {todo['umbral_edge']:.1f} con {len(x)} ops; sin las vistas: {sin['estado'] if sin else 'n/a'}")
        if todo["estado"] == "REFUTADO_FUTILIDAD": return self._cerrar(spec, st, "REFUTADA", f"futilidad con {len(x)} ops (E[x] < {c['mu_util']})")
        if len(x) >= N: return self._cerrar(spec, st, "SIN_POTENCIA", f"{len(x)} ops sin decidir (e {todo['e_edge']:.2f})")
        st["ultimo_conteo"] = self.ahora(); return self._siguiente(spec, st, "CONTEO", n=int(len(x)))     # sigue mirando: es válido

    def _fin_holdout(self, spec, st, res):
        from edgelab.funnel.escalera import confirmar_en_canasta_regimen, resumen_resuelto
        ops = res["operaciones"]; N = st["acta"]["n_fijo"]
        if st["acta"].get("estadistico") == "e_proceso": return self._fin_holdout_e(spec, st, ops, N)
        if st["acta"].get("estadistico") == "canasta_regimen":
            orden = np.argsort(np.asarray(ops.get("t") or []), kind="stable")
            x = np.asarray(ops.get("neto") or [], float)[orden]
            plan = (st["acta"].get("plan_holdout") or st.get("plan_holdout") or {})
            ev = confirmar_en_canasta_regimen(x, mu_esperada=float(plan.get("efecto") or 0.0), sd_op_ref=float(plan.get("sd_op") or 0.0))
            st["holdout"] = dict(estadistico="canasta_regimen", **ev)
            self._medido(spec, f"- HOLDOUT (canasta_regimen): n {ev['n']}, media {ev['media_obs']}, banda esperada {ev['banda_esperada']}, z {ev['z_desvio']} -> {ev['estado']}")
            if ev["confirmada_canasta"]:
                return self._cerrar(spec, st, "CONFIRMADA", f"canasta_regimen: {ev['n']} ops, media {ev['media_obs']:.2f} dentro de banda esperada [{ev['banda_esperada'][0]:.2f}, {ev['banda_esperada'][1]:.2f}] (z={ev['z_desvio']:+.2f})")
            if ev["estado"] == "FUERA_DE_BANDA_INFERIOR":
                return self._cerrar(spec, st, "REFUTADA", f"canasta_regimen: {ev['n']} ops, media {ev['media_obs']:.2f} debajo de cota inferior {ev['banda_esperada'][0]:.2f} (z={ev['z_desvio']:+.2f})")
            return self._cerrar(spec, st, "SIN_POTENCIA", f"canasta_regimen: {ev['estado']}")
        if len(ops.get("t") or []) < N:                                             # CONTEO dijo que había N: no decide con menos
            return self._cerrar(spec, st, "BLOQUEADA", f"HOLDOUT trajo {len(ops.get('t') or [])} operaciones, menos que N={N} del acta")
        orden = np.argsort(np.asarray(ops["t"]), kind="stable")[:N]
        x = np.asarray(ops["neto"], float)[orden]; ses = np.asarray(ops["ses"])[orden]
        nivel = (st["acta"].get("reserva_lord") or {}).get("nivel", st["acta"]["alfa"])
        rs = resumen_resuelto(x, ses, nivel=nivel, m=1, n_boot=N_BOOT_HOLDOUT)                 # 2026-10-24: el p resuelve el nivel reservado
        if self.libro and st["acta"].get("reserva_lord"):                             # decisión 3: al nivel reservado por el acta
            dec = self.libro.resolver(spec["familia"], f"{spec['cid']}/holdout", [("regla", rs["p_unilateral"])])
        elif self.libro:                                                               # actas anteriores al 2026-10-24
            dec = self.libro.probar(spec["familia"], f"{spec['cid']}/holdout", [("regla", rs["p_unilateral"])])
        else: dec = dict(rechazo=rs["p_unilateral"] <= st["acta"]["alfa"])
        st["holdout"] = dict(n=len(x), media=float(x.mean()), ic90=rs["ic"], p=rs["p_unilateral"], lord=dec, n_boot=rs["n_boot"], metodo_p=rs["metodo_p"])
        if (aviso := sin_resolucion(dec.get("nivel", st["acta"]["alfa"]), rs["n_boot"], 1, rs["metodo_p"])): st["holdout"]["sin_resolucion"] = aviso; self._medido(spec, f"- HOLDOUT: {aviso}")
        if dec["rechazo"] and x.mean() > 0: return self._cerrar(spec, st, "CONFIRMADA", f"holdout {len(x)} ops, media {x.mean():.2f}, p {rs['p_unilateral']:.4f}")
        if x.mean() <= 0: return self._cerrar(spec, st, "REFUTADA", f"holdout {len(x)} ops, media {x.mean():.2f}")
        return self._cerrar(spec, st, "SIN_POTENCIA", f"holdout {len(x)} ops, media {x.mean():.2f} > 0 sin alcanzar α (p {rs['p_unilateral']:.4f})")


def problemas_campana(spec: dict) -> list:
    """Chequeos de la campaña que no dependen de datos (corren en el PREFLIGHT, antes de gastar una corrida):
    - ningún período de desarrollo (DESC, OOS) toca el holdout y el holdout empieza en la frontera única o después;
    - `n_celdas_por_canal` declarado y igual a las celdas que el experimento corre de verdad (el contador global depende de esto).
    Las lecturas de `fuentes_ticks` ya cortan en la frontera; esto lo frena antes y con un motivo legible."""
    import importlib
    from edgelab.research import grilla_generica as GG
    e = []
    for k in ("desc", "oos", "atras"):
        per = spec.get(k)
        if per is None: continue
        if len(per) != 2 or int(per[0]) > int(per[1]): e.append(f"{k} {per}: período mal formado")
        elif int(per[1]) >= HOLDOUT_PRIMERA_SESION_INT: e.append(f"{k} {per} toca el holdout (desde {HOLDOUT_PRIMERA_SESION_INT})")
    if int(_cfg(spec, "holdout")["desde"]) < HOLDOUT_PRIMERA_SESION_INT: e.append(f"holdout.desde antes de la frontera {HOLDOUT_PRIMERA_SESION_INT}")
    inst = {spec.get("sensor"), spec.get("ejecucion") or spec.get("sensor")}
    if (a3 := sorted(inst & set(A3_INSTRUMENTOS))) and spec.get("desc") and int(spec["desc"][1]) > A3_FIN_DESCUBRIMIENTO:
        e.append(f"desc {spec['desc']} usa la réplica abr–sep de {a3} (HOLDOUT-A3: descubrimiento hasta {A3_FIN_DESCUBRIMIENTO})")
    if spec.get("atras") and spec.get("desc") and int(spec["atras"][1]) >= int(spec["desc"][0]):
        e.append(f"atras {spec['atras']} no es anterior al DESC {spec['desc']} (tiene que ser historia que la familia no usó)")
    if spec.get("linaje_como", "informacion") not in LINAJE_COMO: e.append(f"linaje_como {spec.get('linaje_como')!r}: debe ser uno de {LINAJE_COMO}")
    e += _problemas_pistas(spec)
    try: n = GG.n_celdas(importlib.import_module(spec["experimento"]))
    except Exception as ex: return e + [f"no se pudo contar las celdas del experimento: {ex!r}"[:200]]
    if not spec.get("n_celdas_por_canal"): e.append(f"falta n_celdas_por_canal (el experimento corre {n} celdas por canal)")
    elif int(spec["n_celdas_por_canal"]) != n: e.append(f"n_celdas_por_canal {spec['n_celdas_por_canal']} != {n} celdas que corre el experimento")
    return e


def sin_resolucion(nivel: float, n_boot: int, m: int = 1, metodo_p: str | None = None):
    """El p del bootstrap no baja de 1/(n_boot+1): si el umbral más exigente del lote (nivel/m: Simes y BH sobre m pruebas) queda
    por debajo, rechazar es imposible por construcción y un «sin rechazo» no dice nada del dato. Desde el 2026-10-24 el kernel
    sube B o usa el p analítico (`escalera.resumen_resuelto`), así que este aviso sólo aparece con resultados viejos o si el nivel
    bajó entre el lanzamiento y la decisión. Con p analítico no hay piso."""
    if metodo_p and "analítico" in metodo_p: return None
    piso = 1 / (n_boot + 1); umbral = nivel / max(int(m), 1)
    return (f"sin resolución: umbral LORD++ {umbral:.2e} (nivel {nivel:.2e} / {m}) < p mínimo del bootstrap {piso:.2e} (n_boot {n_boot}); "
            "un rechazo era imposible") if umbral < piso else None


def _aviso_resolucion(dec, filas, m):
    """Aviso de resolución de un lote: el B más chico entre las filas con p bootstrap (las viejas, sin `n_boot`, valen N_BOOT_REPLICA)."""
    if not dec: return None
    boot = [r for r in filas if r.get("p_sesiones") is not None and "analítico" not in (r.get("metodo_p") or "")]
    if not boot: return None
    return sin_resolucion(dec["nivel"], min(int(r.get("n_boot") or N_BOOT_REPLICA) for r in boot), m)


def _problemas_pistas(spec: dict) -> list:
    """La ventana de pistas a réplica: bien formada, antes del holdout, después del DESC (no usada), dentro de la réplica A3 para
    ES/NQ, y si toca el OOS tiene que ser exactamente el OOS (entonces el OOS no se reusa para esas pistas)."""
    cfg = _cfg(spec, "pistas_replica"); e = []
    if not isinstance(cfg.get("k", 0), int) or cfg.get("k", 0) < 0: e.append("pistas_replica.k debe ser un entero >= 0")
    v = ventana_pistas(spec, cfg)
    if not v or not cfg.get("activa", True): return e
    a, b = v
    if a > b: e.append(f"pistas_replica.ventana {v}: mal formada")
    if b >= HOLDOUT_PRIMERA_SESION_INT: e.append(f"pistas_replica.ventana {v} toca el holdout (desde {HOLDOUT_PRIMERA_SESION_INT})")
    if spec.get("desc") and a <= int(spec["desc"][1]): e.append(f"pistas_replica.ventana {v} no es posterior al DESC {spec['desc']} (tiene que ser no usada)")
    if oos_comprometido(spec) and _solapa(v, spec.get("oos")): e.append(f"pistas_replica.ventana {v} solapa el OOS {spec['oos']} declarado comprometido: no confirma")
    inst = {spec.get("sensor"), spec.get("ejecucion") or spec.get("sensor")}
    if inst & set(A3_INSTRUMENTOS) and (a < A3_REPLICA[0] or b > A3_REPLICA[1]):
        e.append(f"pistas_replica.ventana {v} fuera de la réplica HOLDOUT-A3 {list(A3_REPLICA)} para {sorted(inst & set(A3_INSTRUMENTOS))}")
    if spec.get("oos"):
        o = [int(x) for x in spec["oos"]]
        if not (b < o[0] or a > o[1]) and o != [a, b]: e.append(f"pistas_replica.ventana {v} se superpone con el OOS {o} sin ser el OOS")
    return e


def avanzar_todas(carpeta_campanas: Path, embudo: Embudo, conductor: str | None = None) -> list:
    """Lo que corre el ciclo autónomo: un paso de cada campaña activa (`activa` != false). Con `conductor`, sólo las campañas que
    lo declaran: dos conductores sobre una campaña lanzan el mismo slug de Kaggle dos veces, con estados, libros de LORD++ y de
    ventanas distintos (auditoría 2026-10-24). Una campaña sin conductor declarado se informa como omitida."""
    out = []
    for f in sorted(Path(carpeta_campanas).glob("*.json")):
        spec = json.loads(f.read_text(encoding="utf-8"))
        if not (spec.get("activa", True) and spec.get("embudo", False)): continue
        if conductor is not None and spec.get("conductor") != conductor:
            out.append(dict(cid=spec.get("cid"), omitida=f"conductor {spec.get('conductor')!r}, no {conductor!r}")); continue
        try: out.append(dict(cid=spec["cid"], **{k: v for k, v in embudo.avanzar(spec).items() if k in ("etapa", "fase", "motivo")}))
        except Exception as e: out.append(dict(cid=spec.get("cid"), error=repr(e)[:300]))
    return out
