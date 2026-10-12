"""Ciclo del autopilot. Un `tick()` hace, en orden: kill switch → verificación de protegidos → cierre de corridas terminadas (analizar, liquidar alfa, aprender) → lanzar la mejor
candidata si hay cupo y presupuesto. Modo `propose` (por defecto) solo escribe qué lanzaría; `execute` exige además permiso explícito del humano en la configuración."""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import analyze, guard, evidence
from .fdr import AlphaInvesting
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

    def _paused(self) -> bool:
        return Path(self.cfg.get("kill_switch", self.root / "PAUSE")).exists()

    def tick(self, candidates: list, now: float | None = None) -> dict:
        now = now or time.time(); rep = dict(closed=[], launched=None, proposed=None, blocked=[])
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "heartbeat.json").write_text(json.dumps(dict(ts=now, wealth=self.fdr.wealth, running=[r["run_id"] for r in self.ledger.running()], mode=self.cfg.get("mode", "propose"))))
        if self._paused(): return self._note(event="paused", **rep)
        prot = self.cfg.get("protected")
        if prot and (bad := guard.check_protected(Path(prot), self.repo)):
            return self._note(event="STOP_protected_changed", blocked=bad, **{k: v for k, v in rep.items() if k != "blocked"})
        for r in self.ledger.running():                                              # 1) cerrar terminadas
            st = self.ex.status(r["handle"])
            if st in ("complete", "COMPLETE"):
                spec = RunSpec.from_dict(json.loads(self.ledger.db.execute("SELECT spec FROM runs WHERE run_id=?", (r["run_id"],)).fetchone()[0]))
                res = self.ex.fetch(r["handle"], self.cfg["result_files"].get(spec.family, "RESULTS.json"))
                if spec.kind == "benchmark":                                        # infraestructura: sin hipótesis, sin alfa
                    self.ledger.finish(spec.run_id, "BENCHMARK_DONE", dict(hit=False, benchmark=True)); rep["closed"].append((spec.run_id, "BENCHMARK")); continue
                bid = self.fdr.state["open"][f"{spec.run_id}"]
                d = analyze.decide(res, bid["alpha"], spec.n_trials)
                self.fdr.settle(spec.run_id, d["rejections"]); self.ledger.finish(spec.run_id, "ANALYZED", d); rep["closed"].append((spec.run_id, d["hit"]))
                if self.cfg.get("evidence_runtime"): evidence.record_outcome(Path(self.cfg["evidence_runtime"]), spec, d, evidence.current_states(Path(self.cfg["evidence_runtime"])), result=res)
                if self.brain: self.brain(spec, d)
            elif st in ("error", "ERROR", "cancelAcknowledged"):
                self.ledger.finish(r["run_id"], "FAILED", failure=f"estado {st}"); rep["closed"].append((r["run_id"], "FAILED"))
        running = self.ledger.running()                                              # 2) ¿cupo y presupuesto?
        if len(running) >= self.cfg.get("max_concurrent", 1) or self.ledger.launched_since(now - 86400) >= self.cfg.get("max_per_day", 2):
            return self._note(event="tick_no_capacity", **rep)
        ranked = rank(candidates, self.ledger.outcomes(), self.ledger, seed=int(now) // 3600)
        for score, spec, why in ranked:                                              # 3) la mejor que pase todas las guardas
            errs = guard.all_checks(spec, set(self.cfg.get("allow_internet", [])), self.repo, Path(prot) if prot else None)
            if self.fdr.wealth < 1e-4: errs.append("riqueza de alfa agotada: no se lanzan campañas nuevas hasta que haya replicaciones que la recarguen")
            if errs: rep["blocked"].append((spec.run_id, errs)); continue
            if self.cfg.get("mode", "propose") != "execute":
                rep["proposed"] = (spec.run_id, why); break
            if spec.kind != "benchmark":
                if self.registry: self.registry.ensure(f"autopilot/{spec.run_id}", spec.family, spec.n_trials, spec.notes or "autopilot")   # se cuenta ANTES de lanzar
                self.fdr.bid(spec.run_id, spec.n_trials)
            try:
                handle = self.ex.launch(spec)
            except Exception as e:
                if spec.kind != "benchmark": self.fdr.settle(spec.run_id, 0)
                rep["blocked"].append((spec.run_id, [str(e)[:200]])); continue
            self.ledger.add(spec, handle); rep["launched"] = (spec.run_id, why); break
        return self._note(event="tick", **rep)

    def status(self) -> dict:
        led = self.ledger.db.execute("SELECT status, COUNT(*) FROM runs GROUP BY status").fetchall()
        last = [json.loads(l) for l in self.log.read_text().splitlines()[-5:]] if self.log.exists() else []
        hb = json.loads((self.root / "heartbeat.json").read_text()) if (self.root / "heartbeat.json").exists() else None
        return dict(mode=self.cfg.get("mode", "propose"), paused=self._paused(), alpha_wealth=self.fdr.wealth, open_bids=list(self.fdr.state["open"]), runs=dict(led), running=self.ledger.running(),
                    heartbeat_age_s=None if not hb else round(time.time() - hb["ts"]), last_events=[{k: v for k, v in e.items() if k in ("event", "launched", "closed", "blocked")} for e in last])
