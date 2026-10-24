"""Orquestador del embudo de grilla (2026-10-23): una campaña = un JSON; el resto es automático, de punta a punta.

Pedido de Nico: «que este análisis de millones de variantes con promociones siga siempre un embudo, sea fácil en cualquier activo
con cualquier lógica que proponga el agente, sin errores, sin armarlo cada vez; y que lo humano deje de serlo». Lo único que
se escribe por campaña es el módulo del experimento (la lógica) y la campaña (activo, períodos, justificación, refutación).

Etapas (una por ciclo de `avanzar`; idempotente; estado en <raiz>/<cid>/estado.json; bitácora MEDIDO.md):
  PREFLIGHT  local      preflight estático + dinámico del experimento                       falla -> BLOQUEADA
  DESC       kaggle     registro 2·n_celdas; tamiz + Romano-Wolf + pistas + nulo             sin elegibles -> SIN_CANDIDATAS
                        (2026-10-24: sólo pistas NOMINADAS por el FDR q 0,10 del canal, también con el linaje cobrado; RW es diagnóstico)
  INDAGA     kaggle     marginales alrededor de cada candidata (información, no compuerta)
  INTEGRIDAD kaggle     alineación (si señal ≠ ejecución), placebo, latencia                  ninguna pasa -> INTEGRIDAD_FALLA
  OOS        kaggle     réplica en período no usado; un paso de LORD++ de la familia (libro)  todas refutadas -> REFUTADA_OOS
                        (2026-10-24: mata sólo con potencia declarada, en contra significativo y en el MISMO régimen declarado ex ante;
                        sin potencia = NO_CONCLUYENTE; en contra en otro régimen = EN_CONTRA_OTRO_REGIMEN, sigue viva)
  TOPES      kaggle     tope de stop por regla declarada (sólo datos ya usados)              ninguna elegible -> SIN_REGLA_OPERABLE
  ACTA       local      acta de holdout con la regla congelada, N fijo y α RESERVADO en el libro (antes de mirar)
  CONTEO     local      sesiones del holdout: sólo cuenta operaciones (sin P&L) hasta llegar a N
  HOLDOUT    local      primeras N operaciones: un paso de LORD++ -> CONFIRMADA / REFUTADA / SIN_POTENCIA
Las reglas de cada compuerta vienen de la campaña (`seleccion`, `integridad`, `topes`, `holdout`) con valores por defecto
documentados acá; quedan escritas en el estado ANTES de la etapa que las usa.
Las cuatro decisiones de validación del 2026-10-24 (aprobadas por Nico): docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT

ORDEN = ["PREFLIGHT", "DESC", "INDAGA", "INTEGRIDAD", "OOS", "TOPES", "ACTA", "CONTEO", "HOLDOUT", "FIN"]
FINALES = ("BLOQUEADA", "SIN_CANDIDATAS", "INTEGRIDAD_FALLA", "REFUTADA_OOS", "SIN_REGLA_OPERABLE", "CONFIRMADA", "REFUTADA", "SIN_POTENCIA")
Q_FDR_DESC = 0.10                       # decisión 1 (2026-10-24): gate duro, no se configura por campaña
DECISIONES_20261024 = "docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md"
DEFECTOS = dict(seleccion=dict(max_candidatas=3, min_sesiones=20, ratio_mov_friccion=3.0, exigir_meseta=True, min_dif=2),
                integridad=dict(placebo_max_frac=0.25, latencia_1_positiva=False),
                topes=dict(lista=None, min_frac_sin_tope=0.5),
                holdout=dict(desde=HOLDOUT_PRIMERA_SESION_INT, n_fijo=150, conteo_cada_s=86400),
                # decisión 2 (2026-10-24, con el matiz de Nico: «algunas estrategias funcionan por régimen»): `actual_desde` = primer día
                # (YYYYMMDD, anterior al holdout) del régimen vigente y `definicion` = cómo se lo define, ambos ANTES del OOS. Sin
                # declaración el OOS cuenta como del régimen actual (no hay excepción a posteriori).
                regimen=dict(definicion=None, actual_desde=None, fraccion_efecto=0.5, potencia_min=0.8))
CAMPOS = ("cid", "familia", "experimento", "sensor", "desc", "justificacion_economica", "como_podria_refutarse")
# Lo que define la campaña: si cambia después del PREFLIGHT ya no es la misma campaña (se crea otra, con su registro).
INMUTABLES = ("familia", "experimento", "sensor", "ejecucion", "desc", "oos", "n_celdas_por_canal")
CONDUCTORES = ("debian", "local")                          # quién conduce cada campaña: uno solo (auditoría 2026-10-24)
A3_FIN_DESCUBRIMIENTO, A3_INSTRUMENTOS = 20260331, ("ES", "NQ")   # HOLDOUT-A3/A4: ES y NQ descubren hasta acá; abr–sep es réplica
MAX_HORAS_KAGGLE = 14                                       # Kaggle corta a las 12 h: pasado esto, la etapa se da por caída
N_BOOT_REPLICA, N_BOOT_HOLDOUT = 2000, 5000                 # bootstrap de `grilla_generica.evaluar` y de `_fin_holdout`


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


def nominada(p: dict, n_heredado: int = 0) -> tuple:
    """Decisión 1 + 4: la pista pasa DESC sólo si el FDR del canal la nomina (q <= 0,10) y sigue nominada con las pruebas del linaje
    en el mismo tamiz. Una pista sin la marca (DESC anterior al 2026-10-24) cuenta como no nominada."""
    from edgelab.research.linaje import q_con_linaje
    if not p.get("nominada_fdr") or p.get("q_fdr") is None: return False, None
    ql = q_con_linaje(p["q_fdr"], p.get("pi0_fdr", 1.0), int(p["m_fdr"]), int(n_heredado))
    return bool(p["q_fdr"] <= Q_FDR_DESC and ql <= Q_FDR_DESC), ql


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
        if d0 is not None and (d1 is None or int(d1) < int(d0)): c.append("holdout.desde hacia atrás")   # adelantarlo protege más
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
        if e == "OOS" and not spec.get("oos"): return self._siguiente(spec, st, "TOPES", nota="sin período OOS declarado")
        params, periodo, runner = self._params(spec, st, e)
        if e == "CONTEO" and st.get("ultimo_conteo") and self.ahora() - st["ultimo_conteo"] < _reglas(spec, st, "holdout")["conteo_cada_s"]: return st
        if st["fase"] == "PENDIENTE":
            self._registrar(spec, e, params)
            st["handle"] = self.runners[runner].lanzar(spec, "HOLDOUT_CONTEO" if e == "CONTEO" else ("REP" if e in ("OOS", "HOLDOUT") else e), params, periodo)
            st.update(fase="CORRIENDO", params=params, periodo=periodo, lanzada=self.ahora()); self._guardar(spec, st); return st
        est = self.runners[runner].estado(st["handle"])
        if est in ("running", "queued"):
            if runner == "kaggle" and st.get("lanzada") and self.ahora() - st["lanzada"] > MAX_HORAS_KAGGLE * 3600:
                return self._fallo(spec, st, f"sin terminar después de {MAX_HORAS_KAGGLE} h")          # antes esperaba para siempre
            return st
        if est != "complete": return self._fallo(spec, st, est)
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
        if e == "OOS": return dict(base, celdas=st["candidatas"]), spec["oos"], "kaggle"
        h = _reglas(spec, st, "holdout"); hasta = int(time.strftime("%Y%m%d", time.gmtime(self.ahora() - 86400)))
        regla = st["regla"]
        return dict(base, celdas=[regla["celda"]], tope=regla["tope"], acta=st.get("acta")), [h["desde"], hasta], ("sellado" if "sellado" in self.runners else "local")

    def _registrar(self, spec, e, params):
        """Pruebas con desenlace al contador global ANTES de lanzar. DESC: todas las celdas en los dos canales (total y reciente);
        antes, una campaña sin `n_celdas_por_canal` registraba 2 pruebas para una grilla de millones. TOPES: las variantes con
        tope que se corren de verdad (antes 6 fijas aunque la campaña declarara otra lista)."""
        n = None
        if e == "DESC":
            n = spec.get("n_celdas_por_canal")
            if not n: raise ValueError("DESC sin n_celdas_por_canal: el contador global no puede quedar corto (lo fija el PREFLIGHT)")
            n = int(n) * 2
        elif e == "OOS": n = len(params.get("celdas", []))
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
        reglas = {k: _cfg(spec, k) for k in DEFECTOS}
        if (malos := _problemas_regimen(reglas["regimen"]) + self._problemas_linaje(spec)):
            return self._cerrar(spec, st, "BLOQUEADA", "; ".join(malos))
        st["reglas"] = dict(reglas, linaje=self._multiplicidad(spec))                  # quedan escritas antes de usarse
        st["spec"] = spec                                                              # la campaña que se congela
        st["decisiones_20261024"] = dict(ts=self.ahora(), desde="PREFLIGHT")
        self._medido(spec, f"- Linaje: hereda {st['reglas']['linaje']['n_heredado']} pruebas de {st['reglas']['linaje'].get('padres')}; "
                           f"régimen actual desde {reglas['regimen']['actual_desde'] or 'sin declarar (el OOS cuenta como régimen actual)'}")
        return self._siguiente(spec, st, "DESC")

    # --- decisiones del 2026-10-24 ----------------------------------------------------------------------------------------
    def _problemas_linaje(self, spec):
        from edgelab.research import linaje as LN
        return LN.problemas(spec["familia"], Path(self.linajes) if self.linajes else LN.LIBRO, Path(self.ventanas) if self.ventanas else None,
                            Path(self.registro_pruebas) if self.registro_pruebas else LN.REGISTRO)

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
            vivas = [c for c in st["candidatas"] if any(p["celda"] == c and nominada(p, nh)[0] for p in pistas)]
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
        nh = ((st.get("reglas") or {}).get("linaje") or {}).get("n_heredado", 0); no_nom = 0
        pistas = sorted([p for c in (res.get("canales") or {}).values() for p in c.get("pistas", [])], key=lambda p: -p["ic90"][0])
        for p in pistas:
            ok_fdr, p["q_linaje"] = nominada(p, nh)
            if not ok_fdr: no_nom += 1; continue                                     # decisión 1 + 4 (2026-10-24): gate duro
            if p["sesiones"] < sel["min_sesiones"] or p["ratio_mov_friccion"] < sel["ratio_mov_friccion"] or p["ic90"][0] <= 0: continue
            if sel["exigir_meseta"] and not p["meseta"]: continue
            if any(sum(a != b for a, b in zip(p["celda"], v)) < sel["min_dif"] for v in vistos): continue
            vistos.append(p["celda"]); cand.append(p["celda"])
            if len(cand) >= sel["max_candidatas"]: break
        tot = (res.get("canales") or {}).get("total", {})
        self._medido(spec, f"- DESC {spec['desc']}: evaluables {tot.get('evaluables')}, FDR {tot.get('nominadas_fdr')}, RW umbral "
                           f"{(tot.get('romano_wolf') or {}).get('umbral')} (diagnóstico), pistas sin nominación FDR/linaje {no_nom}, candidatas {len(cand)}")
        if not cand: return self._cerrar(spec, st, "SIN_CANDIDATAS", f"ninguna pista nominada por FDR q {Q_FDR_DESC} (linaje {nh}) cumple la selección; "
                                                                      f"nulo publicado ({tot.get('nulo', {}).get('t', {})})")
        st["candidatas"] = cand; st["desc"] = dict(pistas=[p for p in pistas if p["celda"] in cand])
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
        if dec and (aviso := sin_resolucion(dec["nivel"], N_BOOT_REPLICA)): st["oos"]["sin_resolucion"] = aviso; self._medido(spec, f"- OOS: {aviso}")
        self._medido(spec, f"- OOS {spec['oos']} ({'régimen actual' if mismo else 'otro régimen: antes de ' + str(reg['actual_desde'])}): "
                           f"medias {[round(r.get('media_neta', float('nan')), 2) for r in res['replica']]}; "
                           f"veredictos {[v['veredicto'] for v in veredictos]}; potencias {[round(v.get('potencia', float('nan')), 2) for v in veredictos]}; LORD++ "
                           f"{'confirma ' + str([c['test'] for c in dec['confirmadas']]) if dec and dec['rechazo'] else 'sin rechazo'}")
        if not vivas: return self._cerrar(spec, st, "REFUTADA_OOS", f"todas las candidatas refutadas en un OOS con potencia y del régimen actual ({DECISIONES_20261024})")
        st["candidatas"] = vivas
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
        if (malos := HV.problemas(spec["familia"], h["desde"], spec["cid"], libro_v)):
            return self._cerrar(spec, st, "BLOQUEADA", "; ".join(malos))
        # decisión 3 (2026-10-24): el acta RESERVA su paso de LORD++ (consume α ahora, con el nivel fijo) antes de mirar
        reserva = self.libro.reservar(spec["familia"], f"{spec['cid']}/holdout", f"acta {spec['cid']}") if self.libro else None
        alfa = reserva["nivel"] if reserva else 0.05
        acta = dict(cid=spec["cid"], familia=spec["familia"], experimento=spec["experimento"], sensor=spec["sensor"], ejecucion=spec.get("ejecucion"),
                    regla=st["regla"], cortes=st["cortes"], holdout_desde=h["desde"], n_fijo=h["n_fijo"], alfa=alfa, registrada=self.ahora(),
                    reserva_lord=reserva, multiplicidad=self._acta_multiplicidad(spec, st, h["n_fijo"]),
                    regimen=(st.get("reglas") or {}).get("regimen"), oos=[v["veredicto"] for v in (st.get("oos") or {}).get("veredictos", [])],
                    decision=f"primeras {h['n_fijo']} operaciones desde {h['desde']}: el paso RESERVADO de LORD++ de la familia (α={alfa:.5f}); "
                             "CONFIRMADA si rechaza y media > 0; REFUTADA si media ≤ 0; si no, SIN_POTENCIA")
        (self._dir(spec) / "ACTA_HOLDOUT.json").write_text(json.dumps(acta, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        self._medido(spec, f"- ACTA registrada antes de mirar: {acta['decision']}; regla {st['regla']['celda']} tope {st['regla']['tope']}")
        HV.registrar_apertura(spec["familia"], spec["cid"], h["desde"], h["n_fijo"], libro_v)
        if self.registro: self.registro.ensure(f"embudo/{spec['cid']}/holdout", spec["familia"], 1, "apertura de holdout por acta")
        st["acta"] = acta; return self._siguiente(spec, st, "CONTEO")

    def _acta_multiplicidad(self, spec, st, n_fijo):
        """Decisión 4: multiplicidad total (familia + linaje) y lo que se espera ver de la regla fuera de muestra con ese cobro
        (recorte de Harvey-Liu) y la potencia del holdout a N fijo. Se anota, no decide: la decisión es el paso de LORD++."""
        from edgelab.funnel.escalera import _N, potencia, recorte_t
        lin = ((st.get("reglas") or {}).get("linaje")) or self._multiplicidad(spec)
        total = int(lin.get("total", lin.get("propias", 0) + lin.get("n_heredado", 0)))
        p = next((x for x in (st.get("desc") or {}).get("pistas", []) if x["celda"] == st["regla"]["celda"]), None)
        if not p: return dict(linaje=lin, total=total)
        t = _N.inv_cdf(1 - min(max(p["p_sesiones"], 1e-12), 1 - 1e-12)); rc = recorte_t(t, max(total, 1))
        se = (p["ic90"][1] - p["ic90"][0]) / (2 * 1.6448536); esp = rc["conservado"] * p["media_neta"]
        se_h = se * (p["n"] / max(n_fijo, 1)) ** 0.5
        return dict(linaje=lin, total=total, recorte=rc, efecto_esperado=esp, potencia_holdout=potencia(esp, se_h) if esp > 0 else 0.0)

    def _fin_conteo(self, spec, st, res):
        n = int(res["conteo"][0]); st["ultimo_conteo"] = self.ahora(); st["n_holdout"] = n
        if n < st["acta"]["n_fijo"]:
            st["fase"] = "PENDIENTE"; self._guardar(spec, st); return st                  # espera más sesiones (sin mirar P&L)
        return self._siguiente(spec, st, "HOLDOUT", n=n)

    def _fin_holdout(self, spec, st, res):
        from edgelab.funnel.escalera import resumen_sesiones
        ops = res["operaciones"]; N = st["acta"]["n_fijo"]
        if len(ops.get("t") or []) < N:                                              # CONTEO dijo que había N: no decide con menos
            return self._cerrar(spec, st, "BLOQUEADA", f"HOLDOUT trajo {len(ops.get('t') or [])} operaciones, menos que N={N} del acta")
        orden = np.argsort(np.asarray(ops["t"]), kind="stable")[:N]
        x = np.asarray(ops["neto"], float)[orden]; ses = np.asarray(ops["ses"])[orden]
        rs = resumen_sesiones(x, ses, n_boot=5000)
        if self.libro and st["acta"].get("reserva_lord"):                             # decisión 3: al nivel reservado por el acta
            dec = self.libro.resolver(spec["familia"], f"{spec['cid']}/holdout", [("regla", rs["p_unilateral"])])
        elif self.libro:                                                               # actas anteriores al 2026-10-24
            dec = self.libro.probar(spec["familia"], f"{spec['cid']}/holdout", [("regla", rs["p_unilateral"])])
        else: dec = dict(rechazo=rs["p_unilateral"] <= st["acta"]["alfa"])
        st["holdout"] = dict(n=len(x), media=float(x.mean()), ic90=rs["ic"], p=rs["p_unilateral"], lord=dec)
        if (aviso := sin_resolucion(dec.get("nivel", st["acta"]["alfa"]), N_BOOT_HOLDOUT)): st["holdout"]["sin_resolucion"] = aviso; self._medido(spec, f"- HOLDOUT: {aviso}")
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
    for k in ("desc", "oos"):
        per = spec.get(k)
        if per is None: continue
        if len(per) != 2 or int(per[0]) > int(per[1]): e.append(f"{k} {per}: período mal formado")
        elif int(per[1]) >= HOLDOUT_PRIMERA_SESION_INT: e.append(f"{k} {per} toca el holdout (desde {HOLDOUT_PRIMERA_SESION_INT})")
    if int(_cfg(spec, "holdout")["desde"]) < HOLDOUT_PRIMERA_SESION_INT: e.append(f"holdout.desde antes de la frontera {HOLDOUT_PRIMERA_SESION_INT}")
    inst = {spec.get("sensor"), spec.get("ejecucion") or spec.get("sensor")}
    if (a3 := sorted(inst & set(A3_INSTRUMENTOS))) and spec.get("desc") and int(spec["desc"][1]) > A3_FIN_DESCUBRIMIENTO:
        e.append(f"desc {spec['desc']} usa la réplica abr–sep de {a3} (HOLDOUT-A3: descubrimiento hasta {A3_FIN_DESCUBRIMIENTO})")
    try: n = GG.n_celdas(importlib.import_module(spec["experimento"]))
    except Exception as ex: return e + [f"no se pudo contar las celdas del experimento: {ex!r}"[:200]]
    if not spec.get("n_celdas_por_canal"): e.append(f"falta n_celdas_por_canal (el experimento corre {n} celdas por canal)")
    elif int(spec["n_celdas_por_canal"]) != n: e.append(f"n_celdas_por_canal {spec['n_celdas_por_canal']} != {n} celdas que corre el experimento")
    return e


def sin_resolucion(nivel: float, n_boot: int):
    """El p del bootstrap no baja de 1/(n_boot+1): si el nivel de LORD++ queda por debajo, rechazar es imposible por construcción
    y un «sin rechazo» no dice nada del dato. Se avisa (no cambia la decisión: el nivel y n_boot son reglas de validación)."""
    piso = 1 / (n_boot + 1)
    return f"sin resolución: nivel LORD++ {nivel:.2e} < p mínimo del bootstrap {piso:.2e} (n_boot {n_boot}); un rechazo era imposible" if nivel < piso else None


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
