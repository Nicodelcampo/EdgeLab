"""Ciclo del autopilot. Un `tick()` hace, en orden: kill switch → verificación de protegidos → cierre de corridas terminadas (analizar, liquidar alfa, aprender) → lanzar la mejor
candidata si hay cupo y presupuesto. Modo `propose` (por defecto) solo escribe qué lanzaría; `execute` exige además permiso explícito del humano en la configuración."""
from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path

from . import account, analyze, guard, evidence
from .fdr import AlphaInvesting
from .executor import LaunchRejected
from .ledger import RunLedger
from .selector import rank
from .spec import RunSpec


class Autopilot:
    def __init__(self, root: Path, executor, cfg: dict, repo: Path = guard.REPO, registry=None, brain=None):
        self.root, self.ex, self.cfg, self.repo, self.registry, self.brain = Path(root), executor, cfg, repo, registry, brain
        self.ledger = RunLedger(self.root / "runs.sqlite"); self.fdr = AlphaInvesting(self.root / "alpha.json", **cfg.get("alpha", {}))
        self.log = self.root / "autopilot.log.jsonl"

    def _note(self, **k):
        k["ts"] = time.time(); self.log.parent.mkdir(parents=True, exist_ok=True)
        with self.log.open("a") as f: f.write(json.dumps(k, default=str) + "\n")
        return k

    def pause_files(self) -> tuple:
        """Dos interruptores: el de consola (sólo un humano en la máquina lo crea y lo borra) y el de la sala (Chaski).
        La sala nunca puede levantar una pausa de consola; el ciclo se detiene si existe cualquiera de los dos."""
        return (Path(self.cfg.get("kill_switch", self.root / "PAUSE")), Path(self.cfg.get("kill_switch_sala", self.root / "PAUSE_SALA")))

    def _paused(self) -> bool:
        return any(p.exists() for p in self.pause_files())

    def tick(self, candidates: list, now: float | None = None) -> dict:
        """Un solo controlador por directorio de estado: bloqueo exclusivo no bloqueante (cubre CLI, timer y generador que apunten al mismo estado)."""
        self.root.mkdir(parents=True, exist_ok=True)
        with open(self.root / ".lock", "a") as lk:
            try: fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError: return self._note(event="locked_by_other_controller")
            return self._tick(candidates, now)

    def _reconcile(self, rep: dict) -> None:
        """Cierra apuestas de alfa que quedaron abiertas tras una caída entre pasos: corrida ya ANALYZED → se liquida con su resultado guardado; FAILED → se devuelve."""
        for rid in list(self.fdr.state["open"]):
            row = self.ledger.db.execute("SELECT status,result FROM runs WHERE run_id=?", (rid,)).fetchone()
            if row and row[0] == "ANALYZED": self.fdr.settle(rid, int(json.loads(row[1]).get("rejections", 0))); rep.setdefault("reconciled", []).append((rid, "settled"))
            elif row and row[0] == "FAILED": self.fdr.release(rid, "corrida fallida"); rep.setdefault("reconciled", []).append((rid, "released"))

    def _tick(self, candidates: list, now: float | None = None) -> dict:
        now = now or time.time(); rep = dict(closed=[], launched=None, proposed=None, blocked=[]); self.fdr.state = self.fdr._load(); self._reconcile(rep)
        (self.root / "heartbeat.json").write_text(json.dumps(dict(ts=now, wealth=self.fdr.wealth, running=[r["run_id"] for r in self.ledger.running()], send_uncertain=self.ledger.uncertain(), mode=self.cfg.get("mode", "propose"))))
        if self._paused(): return self._note(event="paused", **rep)
        prot = self.cfg.get("protected")
        if prot and (bad := guard.check_protected(Path(prot), self.repo)):
            return self._note(event="STOP_protected_changed", blocked=bad, **{k: v for k, v in rep.items() if k != "blocked"})
        for r in self.ledger.running():                                              # 1) cerrar terminadas
            st = self.ex.status(r["handle"])
            if st in ("complete", "COMPLETE"):
                spec = RunSpec.from_dict(json.loads(self.ledger.db.execute("SELECT spec FROM runs WHERE run_id=?", (r["run_id"],)).fetchone()[0]))
                if spec.kind == "benchmark":                                        # infraestructura: sin hipótesis, sin alfa, sin traer resultado
                    self.ledger.finish(spec.run_id, "BENCHMARK_DONE", dict(hit=False, benchmark=True)); rep["closed"].append((spec.run_id, "BENCHMARK")); continue
                try:
                    res = self.ex.fetch(r["handle"], self.cfg["result_files"][spec.family])
                except Exception as e:                                                 # error de configuración o de red: no tumba el ciclo, queda registrado y se reintenta
                    self.ledger.event(spec.run_id, "fetch_failed", repr(e)[:200]); rep["blocked"].append((spec.run_id, [f"no se pudo traer el resultado: {e!r}"[:200]])); continue
                bid = self.fdr.open_bid(spec.run_id)
                if bid is None: rep["blocked"].append((spec.run_id, ["sin apuesta de alfa abierta: no se liquida"])); continue
                d = analyze.decide(res, bid["alpha"], spec.n_tests_holm or spec.n_trials)
                self.ledger.finish(spec.run_id, "ANALYZED", d); self.fdr.settle(spec.run_id, d["rejections"]); rep["closed"].append((spec.run_id, d["hit"]))     # primero el libro, luego la riqueza: si cae entre ambos, _reconcile liquida al reiniciar
                if self.cfg.get("evidence_runtime"): evidence.record_outcome(Path(self.cfg["evidence_runtime"]), spec, d, evidence.current_states(Path(self.cfg["evidence_runtime"])), result=res)
                if self.brain: self.brain(spec, d)
            elif st in ("error", "ERROR", "cancelAcknowledged"):
                self.ledger.finish(r["run_id"], "FAILED", failure=f"estado {st}"); self.fdr.release(r["run_id"], f"estado {st}"); rep["closed"].append((r["run_id"], "FAILED"))
        running = self.ledger.running()                                              # 2) ¿cupo y presupuesto?
        if len(running) >= self.cfg.get("max_concurrent", 1):
            return self._note(event="tick_no_capacity", **rep)
        hyp_full = self.ledger.launched_since(now - 86400) >= self.cfg.get("max_per_day", 2); bm_full = self.ledger.launched_since(now - 86400, benchmark=True) >= self.cfg.get("max_benchmarks_per_day", 4)
        if hyp_full and bm_full: return self._note(event="tick_no_capacity", **rep)
        if (cap := self.cfg.get("account_max_per_day")) and account.count_since(now - 86400, self.cfg.get("account_log")) >= cap:
            return self._note(event="tick_account_cap", reason=f"la cuenta ya lanzó {cap} kernels en 24 h (autopilot + manuales + otros agentes)", **rep)
        ranked = rank(candidates, self.ledger.outcomes(), self.ledger, seed=int(now) // 3600)
        for score, spec, why in ranked:                                              # 3) la mejor que pase todas las guardas
            if (spec.kind == "benchmark" and bm_full) or (spec.kind != "benchmark" and hyp_full): continue      # los topes diarios son por tipo: hipótesis y benchmarks
            errs = guard.all_checks(spec, set(self.cfg.get("allow_internet", [])), self.repo, Path(prot) if prot else None)
            if self.fdr.wealth < 1e-4: errs.append("riqueza de alfa agotada: no se lanzan campañas nuevas hasta que haya replicaciones que la recarguen")
            if errs: rep["blocked"].append((spec.run_id, errs)); continue
            if self.cfg.get("mode", "propose") != "execute":
                rep["proposed"] = (spec.run_id, why); break
            if spec.kind != "benchmark":
                if self.registry: self.registry.ensure(f"autopilot/{spec.run_id}", spec.family, spec.n_trials, spec.notes or "autopilot")   # se cuenta ANTES de lanzar
                self.fdr.bid(spec.run_id, spec.n_trials)
            self.ledger.add_intent(spec)                                              # escribe-antes-de-enviar: una caída durante el envío deja SEND_UNCERTAIN y nunca se reenvía sola
            try:
                handle = self.ex.launch(spec)
            except LaunchRejected as e:                                               # rechazo explícito: no hay corrida; se devuelve la apuesta y puede reintentarse
                self.ledger.cancel_intent(spec.run_id)
                if spec.kind != "benchmark": self.fdr.release(spec.run_id, "lanzamiento rechazado")
                rep["blocked"].append((spec.run_id, [str(e)[:200]])); continue
            except Exception as e:                                                    # tiempo agotado o error ambiguo: puede haber corrida remota → SEND_UNCERTAIN, apuesta abierta, sin reenvío; requiere conciliar a mano
                rep["blocked"].append((spec.run_id, [f"envío incierto (se reconcilia a mano con el handle exacto, no se reenvía): {str(e)[:150]}"])); break
            self.ledger.confirm_send(spec.run_id, handle); rep["launched"] = (spec.run_id, why); break
        return self._note(event="tick", **rep)

    def status(self) -> dict:
        led = self.ledger.db.execute("SELECT status, COUNT(*) FROM runs GROUP BY status").fetchall()
        last = [json.loads(l) for l in self.log.read_text().splitlines()[-5:]] if self.log.exists() else []
        hb = json.loads((self.root / "heartbeat.json").read_text()) if (self.root / "heartbeat.json").exists() else None
        return dict(mode=self.cfg.get("mode", "propose"), paused=self._paused(), pausas=[str(p) for p in self.pause_files() if p.exists()], pedidos_abiertos=[p['id'] for p in __import__('edgelab.autopilot.pedidos', fromlist=['x']).abiertos(self.root)], alpha_wealth=self.fdr.wealth, open_bids=list(self.fdr.state["open"]), runs=dict(led), running=self.ledger.running(), send_uncertain=self.ledger.uncertain(),
                    heartbeat_age_s=None if not hb else round(time.time() - hb["ts"]), last_events=[{k: v for k, v in e.items() if k in ("event", "launched", "closed", "blocked")} for e in last])
