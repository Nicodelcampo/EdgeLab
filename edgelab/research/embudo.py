"""Orquestador del embudo de grilla (2026-10-23): una campaña = un JSON; el resto es automático, de punta a punta.

Pedido de Nico: «que este análisis de millones de variantes con promociones siga siempre un embudo, sea fácil en cualquier activo
con cualquier lógica que proponga el agente, sin errores, sin armarlo cada vez; y que lo humano deje de serlo». Lo único que
se escribe por campaña es el módulo del experimento (la lógica) y la campaña (activo, períodos, justificación, refutación).

Etapas (una por ciclo de `avanzar`; idempotente; estado en <raiz>/<cid>/estado.json; bitácora MEDIDO.md):
  PREFLIGHT  local      preflight estático + dinámico del experimento                       falla -> BLOQUEADA
  DESC       kaggle     registro 2·n_celdas; tamiz + Romano-Wolf + pistas + nulo             sin elegibles -> SIN_CANDIDATAS
  INDAGA     kaggle     marginales alrededor de cada candidata (información, no compuerta)
  INTEGRIDAD kaggle     alineación (si señal ≠ ejecución), placebo, latencia                  ninguna pasa -> INTEGRIDAD_FALLA
  OOS        kaggle     réplica en período no usado; un paso de LORD++ de la familia (libro)  (no mata: principio de edges actuales)
  TOPES      kaggle     tope de stop por regla declarada (sólo datos ya usados)              ninguna elegible -> SIN_REGLA_OPERABLE
  ACTA       local      acta de holdout con la regla congelada, N fijo y α del libro (antes de mirar)
  CONTEO     local      sesiones del holdout: sólo cuenta operaciones (sin P&L) hasta llegar a N
  HOLDOUT    local      primeras N operaciones: un paso de LORD++ -> CONFIRMADA / REFUTADA / SIN_POTENCIA
Las reglas de cada compuerta vienen de la campaña (`seleccion`, `integridad`, `topes`, `holdout`) con valores por defecto
documentados acá; quedan escritas en el estado ANTES de la etapa que las usa.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT

ORDEN = ["PREFLIGHT", "DESC", "INDAGA", "INTEGRIDAD", "OOS", "TOPES", "ACTA", "CONTEO", "HOLDOUT", "FIN"]
FINALES = ("BLOQUEADA", "SIN_CANDIDATAS", "INTEGRIDAD_FALLA", "SIN_REGLA_OPERABLE", "CONFIRMADA", "REFUTADA", "SIN_POTENCIA")
DEFECTOS = dict(seleccion=dict(max_candidatas=3, min_sesiones=20, ratio_mov_friccion=3.0, exigir_meseta=True, min_dif=2),
                integridad=dict(placebo_max_frac=0.25, latencia_1_positiva=False),
                topes=dict(lista=None, min_frac_sin_tope=0.5),
                holdout=dict(desde=HOLDOUT_PRIMERA_SESION_INT, n_fijo=150, conteo_cada_s=86400))
CAMPOS = ("cid", "familia", "experimento", "sensor", "desc", "justificacion_economica", "como_podria_refutarse")
# Lo que define la campaña: si cambia después del PREFLIGHT ya no es la misma campaña (se crea otra, con su registro).
INMUTABLES = ("familia", "experimento", "sensor", "ejecucion", "desc", "oos", "n_celdas_por_canal")
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


class Embudo:
    def __init__(self, raiz: Path, runners: dict, registro=None, libro=None, ahora=time.time, log=print, ventanas=None):
        """runners: {"kaggle": ..., "local": ...} con lanzar(spec, etapa, params, periodo) -> handle, estado(handle), traer(handle)."""
        self.raiz, self.runners, self.registro, self.libro, self.ahora, self.log = Path(raiz), runners, registro, libro, ahora, log
        self.ventanas = ventanas                                                   # libro de ventanas del holdout (None = el del repo)

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
        if self.registro is None: return
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
        st["reglas"] = {k: _cfg(spec, k) for k in DEFECTOS}                           # quedan escritas antes de usarse
        st["spec"] = spec                                                              # la campaña que se congela
        return self._siguiente(spec, st, "DESC")

    def _fin_desc(self, spec, st, res):
        n_reg = spec.get("n_celdas_por_canal")
        if n_reg and res.get("celdas") is not None and int(res["celdas"]) != int(n_reg):
            return self._cerrar(spec, st, "BLOQUEADA", f"el contador global registró {n_reg} celdas por canal y se corrieron {res['celdas']}: "
                                                       "la multiplicidad quedó mal contada (corregir y relanzar como campaña nueva)")
        sel = _reglas(spec, st, "seleccion"); st["cortes"] = res["E0"]["cortes"]; cand, vistos = [], []
        pistas = sorted([p for c in (res.get("canales") or {}).values() for p in c.get("pistas", [])], key=lambda p: -p["ic90"][0])
        for p in pistas:
            if p["sesiones"] < sel["min_sesiones"] or p["ratio_mov_friccion"] < sel["ratio_mov_friccion"] or p["ic90"][0] <= 0: continue
            if sel["exigir_meseta"] and not p["meseta"]: continue
            if any(sum(a != b for a, b in zip(p["celda"], v)) < sel["min_dif"] for v in vistos): continue
            vistos.append(p["celda"]); cand.append(p["celda"])
            if len(cand) >= sel["max_candidatas"]: break
        tot = (res.get("canales") or {}).get("total", {})
        self._medido(spec, f"- DESC {spec['desc']}: evaluables {tot.get('evaluables')}, FDR {tot.get('nominadas_fdr')}, RW umbral "
                           f"{(tot.get('romano_wolf') or {}).get('umbral')}, candidatas {len(cand)}")
        if not cand: return self._cerrar(spec, st, "SIN_CANDIDATAS", f"ninguna pista cumple la selección; nulo publicado ({tot.get('nulo', {}).get('t', {})})")
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
        pr = [(f"c{i}", r.get("p_sesiones", 1.0) if r.get("p_sesiones") is not None else 1.0) for i, r in enumerate(res["replica"])]
        dec = self.libro.probar(spec["familia"], f"{spec['cid']}/oos", pr) if self.libro else None
        st["oos"] = dict(replica=res["replica"], lord=dec)
        if dec and (aviso := sin_resolucion(dec["nivel"], N_BOOT_REPLICA)): st["oos"]["sin_resolucion"] = aviso; self._medido(spec, f"- OOS: {aviso}")
        self._medido(spec, f"- OOS {spec['oos']}: medias {[round(r.get('media_neta', float('nan')), 2) for r in res['replica']]}; LORD++ "
                           f"{'confirma ' + str([c['test'] for c in dec['confirmadas']]) if dec and dec['rechazo'] else 'sin rechazo'} (no mata: edges actuales)")
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
        alfa = self.libro.nivel(spec["familia"]) if self.libro else 0.05
        acta = dict(cid=spec["cid"], familia=spec["familia"], experimento=spec["experimento"], sensor=spec["sensor"], ejecucion=spec.get("ejecucion"),
                    regla=st["regla"], cortes=st["cortes"], holdout_desde=h["desde"], n_fijo=h["n_fijo"], alfa=alfa, registrada=self.ahora(),
                    decision=f"primeras {h['n_fijo']} operaciones desde {h['desde']}: un paso de LORD++ de la familia (α={alfa:.5f}); "
                             "CONFIRMADA si rechaza y media > 0; REFUTADA si media ≤ 0; si no, SIN_POTENCIA")
        (self._dir(spec) / "ACTA_HOLDOUT.json").write_text(json.dumps(acta, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        self._medido(spec, f"- ACTA registrada antes de mirar: {acta['decision']}; regla {st['regla']['celda']} tope {st['regla']['tope']}")
        HV.registrar_apertura(spec["familia"], spec["cid"], h["desde"], h["n_fijo"], libro_v)
        if self.registro: self.registro.ensure(f"embudo/{spec['cid']}/holdout", spec["familia"], 1, "apertura de holdout por acta")
        st["acta"] = acta; return self._siguiente(spec, st, "CONTEO")

    def _fin_conteo(self, spec, st, res):
        n = int(res["conteo"][0]); st["ultimo_conteo"] = self.ahora(); st["n_holdout"] = n
        if n < st["acta"]["n_fijo"]:
            st["fase"] = "PENDIENTE"; self._guardar(spec, st); return st                  # espera más sesiones (sin mirar P&L)
        return self._siguiente(spec, st, "HOLDOUT", n=n)

    def _fin_holdout(self, spec, st, res):
        from edgelab.funnel.escalera import resumen_sesiones
        ops = res["operaciones"]; N = st["acta"]["n_fijo"]
        orden = np.argsort(np.asarray(ops["t"]), kind="stable")[:N]
        x = np.asarray(ops["neto"], float)[orden]; ses = np.asarray(ops["ses"])[orden]
        rs = resumen_sesiones(x, ses, n_boot=5000)
        dec = self.libro.probar(spec["familia"], f"{spec['cid']}/holdout", [("regla", rs["p_unilateral"])]) if self.libro else dict(rechazo=rs["p_unilateral"] <= st["acta"]["alfa"])
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


def avanzar_todas(carpeta_campanas: Path, embudo: Embudo) -> list:
    """Lo que corre el ciclo autónomo: un paso de cada campaña activa (`activa` != false)."""
    out = []
    for f in sorted(Path(carpeta_campanas).glob("*.json")):
        spec = json.loads(f.read_text(encoding="utf-8"))
        if spec.get("activa", True) and spec.get("embudo", False):
            try: out.append(dict(cid=spec["cid"], **{k: v for k, v in embudo.avanzar(spec).items() if k in ("etapa", "fase", "motivo")}))
            except Exception as e: out.append(dict(cid=spec.get("cid"), error=repr(e)[:300]))
    return out
