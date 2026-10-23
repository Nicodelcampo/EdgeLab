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

ORDEN = ["PREFLIGHT", "DESC", "INDAGA", "INTEGRIDAD", "OOS", "TOPES", "ACTA", "CONTEO", "HOLDOUT", "FIN"]
FINALES = ("BLOQUEADA", "SIN_CANDIDATAS", "INTEGRIDAD_FALLA", "SIN_REGLA_OPERABLE", "CONFIRMADA", "REFUTADA", "SIN_POTENCIA")
DEFECTOS = dict(seleccion=dict(max_candidatas=3, min_sesiones=20, ratio_mov_friccion=3.0, exigir_meseta=True, min_dif=2),
                integridad=dict(placebo_max_frac=0.25, latencia_1_positiva=False),
                topes=dict(lista=None, min_frac_sin_tope=0.5),
                holdout=dict(desde=20261001, n_fijo=150, conteo_cada_s=86400))
CAMPOS = ("cid", "familia", "experimento", "sensor", "desc", "justificacion_economica", "como_podria_refutarse")


def _cfg(spec, k):
    return {**DEFECTOS[k], **(spec.get(k) or {})}


class Embudo:
    def __init__(self, raiz: Path, runners: dict, registro=None, libro=None, ahora=time.time, log=print):
        """runners: {"kaggle": ..., "local": ...} con lanzar(spec, etapa, params, periodo) -> handle, estado(handle), traer(handle)."""
        self.raiz, self.runners, self.registro, self.libro, self.ahora, self.log = Path(raiz), runners, registro, libro, ahora, log

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
        st.update(etapa=etapa, fase="PENDIENTE", handle=None); self._guardar(spec, st); return st

    # --- un paso --------------------------------------------------------------------------------------------------------
    def avanzar(self, spec: dict) -> dict:
        falta = [k for k in CAMPOS if k not in spec]
        if falta: raise ValueError(f"campaña sin {falta}")
        st = self.estado(spec)
        if st["etapa"] == "FIN": return st
        e = st["etapa"]
        if e == "PREFLIGHT": return self._preflight(spec, st)
        if e == "ACTA": return self._acta(spec, st)
        if e == "OOS" and not spec.get("oos"): return self._siguiente(spec, st, "TOPES", nota="sin período OOS declarado")
        params, periodo, runner = self._params(spec, st, e)
        if e == "CONTEO" and st.get("ultimo_conteo") and self.ahora() - st["ultimo_conteo"] < _cfg(spec, "holdout")["conteo_cada_s"]: return st
        if st["fase"] == "PENDIENTE":
            self._registrar(spec, e, params)
            st["handle"] = self.runners[runner].lanzar(spec, "HOLDOUT_CONTEO" if e == "CONTEO" else ("REP" if e in ("OOS", "HOLDOUT") else e), params, periodo)
            st.update(fase="CORRIENDO", params=params, periodo=periodo, lanzada=self.ahora()); self._guardar(spec, st); return st
        est = self.runners[runner].estado(st["handle"])
        if est in ("running", "queued"): return st
        if est != "complete":
            st["fallas"] = st.get("fallas", 0) + 1; st["fase"] = "PENDIENTE"
            if st["fallas"] >= 3: return self._cerrar(spec, st, "BLOQUEADA", f"la etapa {e} falló 3 veces ({est})")
            self._guardar(spec, st); return st
        return getattr(self, f"_fin_{e.lower()}")(spec, st, self.runners[runner].traer(st["handle"]))

    def _params(self, spec, st, e):
        base = dict(cortes=st.get("cortes"))
        if e == "DESC": return dict(cortes=None), spec["desc"], "kaggle"
        if e == "INDAGA": return dict(base, bases=st["candidatas"]), spec["desc"], "kaggle"
        if e in ("INTEGRIDAD", "TOPES"): return dict(base, celdas=st["candidatas"], topes=_cfg(spec, "topes")["lista"] or None), spec["desc"], "kaggle"
        if e == "OOS": return dict(base, celdas=st["candidatas"]), spec["oos"], "kaggle"
        h = _cfg(spec, "holdout"); hasta = int(time.strftime("%Y%m%d", time.gmtime(self.ahora() - 86400)))
        regla = st["regla"]
        return dict(base, celdas=[regla["celda"]], tope=regla["tope"]), [h["desde"], hasta], "local"

    def _registrar(self, spec, e, params):
        if self.registro is None: return
        n = {"DESC": spec.get("n_celdas_por_canal", 1) * 2, "OOS": len(params.get("celdas", [])), "TOPES": len(params.get("celdas", [])) * 6, "HOLDOUT": 1}.get(e)
        if n: self.registro.ensure(f"embudo/{spec['cid']}/{e.lower()}", spec["familia"], int(n), f"embudo {spec['cid']} etapa {e}")

    # --- compuertas -----------------------------------------------------------------------------------------------------
    def _preflight(self, spec, st):
        from edgelab.research.preflight import verificar_experimento
        r = verificar_experimento(spec["experimento"], dinamico_tambien=spec.get("preflight_dinamico", True))
        self._medido(spec, f"## {spec['cid']} — {spec['experimento']} · señal {spec['sensor']} · ejecución {spec.get('ejecucion') or spec['sensor']}\n"
                           f"- Justificación: {spec['justificacion_economica']}\n- Refutación: {spec['como_podria_refutarse']}\n- PREFLIGHT: {'ok' if r['ok'] else r['errores']}")
        if not r["ok"]: return self._cerrar(spec, st, "BLOQUEADA", f"preflight: {r['errores'][:3]}")
        st["reglas"] = {k: _cfg(spec, k) for k in DEFECTOS}                           # quedan escritas antes de usarse
        return self._siguiente(spec, st, "DESC")

    def _fin_desc(self, spec, st, res):
        sel = _cfg(spec, "seleccion"); st["cortes"] = res["E0"]["cortes"]; cand, vistos = [], []
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
        cfg = _cfg(spec, "integridad"); al = res.get("alineacion")
        if al and al.get("pico_lag_s") is not None and al["pico_lag_s"] > 0:
            return self._cerrar(spec, st, "INTEGRIDAD_FALLA", f"alineación: la señal adelanta a la ejecución ({al['pico_lag_s']} s)")
        quedan = []
        for i, c in enumerate(st["candidatas"]):
            lat = res["latencia"]; r0 = (lat.get(0) or lat.get("0") or [{}])[i].get("media"); r1 = (lat.get(1) or lat.get("1") or [{}])[i].get("media")
            plac = float(np.mean((res["placebo"].get(i) or res["placebo"].get(str(i)))))
            ok = r0 is not None and r0 > 0 and plac <= cfg["placebo_max_frac"] * r0 and (not cfg["latencia_1_positiva"] or (r1 or -1) > 0)
            self._medido(spec, f"- INTEGRIDAD {c}: regla {r0}, placebo {plac:.2f}, latencia 1 vela {r1} -> {'pasa' if ok else 'no pasa'}")
            if ok: quedan.append(c)
        if not quedan: return self._cerrar(spec, st, "INTEGRIDAD_FALLA", "ninguna candidata pasa placebo/latencia")
        st["candidatas"] = quedan; return self._siguiente(spec, st, "OOS")

    def _fin_oos(self, spec, st, res):
        pr = [(f"c{i}", r.get("p_sesiones", 1.0) if r.get("p_sesiones") is not None else 1.0) for i, r in enumerate(res["replica"])]
        dec = self.libro.probar(spec["familia"], f"{spec['cid']}/oos", pr) if self.libro else None
        st["oos"] = dict(replica=res["replica"], lord=dec)
        self._medido(spec, f"- OOS {spec['oos']}: medias {[round(r.get('media_neta', float('nan')), 2) for r in res['replica']]}; LORD++ "
                           f"{'confirma ' + str([c['test'] for c in dec['confirmadas']]) if dec and dec['rechazo'] else 'sin rechazo'} (no mata: edges actuales)")
        return self._siguiente(spec, st, "TOPES")

    def _fin_topes(self, spec, st, res):
        cfg = _cfg(spec, "topes"); mejor = None
        for i, c in enumerate(st["candidatas"]):
            sin = res["por_tope"]["sin tope"][i]["por_mitad"]
            for nombre, filas in res["por_tope"].items():
                if nombre == "sin tope": continue
                f = filas[i]; mit = f["por_mitad"]
                ok = all((m.get("media") or -1) > 0 and (m.get("media") or -1) >= cfg["min_frac_sin_tope"] * (s.get("media") or 0) for m, s in zip(mit, sin))
                if not ok or not f.get("drawdown_max"): continue
                puntaje = f["total"] / abs(f["drawdown_max"])
                tope = [nombre.split(":")[0], float(nombre.split(":")[1])]
                if mejor is None or puntaje > mejor["puntaje"]: mejor = dict(celda=c, tope=tope, puntaje=puntaje, peor=f.get("peor"))
        self._medido(spec, f"- TOPES: {'elegida ' + str(mejor) if mejor else 'ninguna variante con tope conserva el resultado en las dos mitades'}")
        if not mejor: return self._cerrar(spec, st, "SIN_REGLA_OPERABLE", "ningún tope conserva el edge (la pérdida máxima no se puede acotar)")
        st["regla"] = mejor; return self._siguiente(spec, st, "ACTA")

    def _acta(self, spec, st):
        h = _cfg(spec, "holdout"); alfa = self.libro.nivel(spec["familia"]) if self.libro else 0.05
        acta = dict(cid=spec["cid"], familia=spec["familia"], experimento=spec["experimento"], sensor=spec["sensor"], ejecucion=spec.get("ejecucion"),
                    regla=st["regla"], cortes=st["cortes"], holdout_desde=h["desde"], n_fijo=h["n_fijo"], alfa=alfa, registrada=self.ahora(),
                    decision=f"primeras {h['n_fijo']} operaciones desde {h['desde']}: un paso de LORD++ de la familia (α={alfa:.5f}); "
                             "CONFIRMADA si rechaza y media > 0; REFUTADA si media ≤ 0; si no, SIN_POTENCIA")
        (self._dir(spec) / "ACTA_HOLDOUT.json").write_text(json.dumps(acta, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
        self._medido(spec, f"- ACTA registrada antes de mirar: {acta['decision']}; regla {st['regla']['celda']} tope {st['regla']['tope']}")
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
        if dec["rechazo"] and x.mean() > 0: return self._cerrar(spec, st, "CONFIRMADA", f"holdout {len(x)} ops, media {x.mean():.2f}, p {rs['p_unilateral']:.4f}")
        if x.mean() <= 0: return self._cerrar(spec, st, "REFUTADA", f"holdout {len(x)} ops, media {x.mean():.2f}")
        return self._cerrar(spec, st, "SIN_POTENCIA", f"holdout {len(x)} ops, media {x.mean():.2f} > 0 sin alcanzar α (p {rs['p_unilateral']:.4f})")


def avanzar_todas(carpeta_campanas: Path, embudo: Embudo) -> list:
    """Lo que corre el ciclo autónomo: un paso de cada campaña activa (`activa` != false)."""
    out = []
    for f in sorted(Path(carpeta_campanas).glob("*.json")):
        spec = json.loads(f.read_text(encoding="utf-8"))
        if spec.get("activa", True) and spec.get("embudo", False):
            try: out.append(dict(cid=spec["cid"], **{k: v for k, v in embudo.avanzar(spec).items() if k in ("etapa", "fase", "motivo")}))
            except Exception as e: out.append(dict(cid=spec.get("cid"), error=repr(e)[:300]))
    return out
