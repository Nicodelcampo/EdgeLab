import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Set

ALLOWED_STAGES = {
    "TARGET_FREE_CENSUS",
    "PROPOSED_TARGET_FREE",
    "BLOCKED_MISSING_FEATURES",
    "READY_FOR_PREREGISTRATION",
    "ABSTAIN_INSUFFICIENT_EVIDENCE"
}

class ResourceBudget:
    def __init__(self, max_memory_mb: float = 1500.0, max_concurrency: int = 1, timeout_sec: float = 3600.0):
        self.max_memory_mb = max_memory_mb
        self.max_concurrency = max_concurrency
        self.timeout_sec = timeout_sec

    def check_memory(self, current_mb: float) -> bool:
        return current_mb <= self.max_memory_mb

class DAGNode:
    def __init__(self, node_id: str, hypothesis_id: str, stage: str, dependencies: Optional[List[str]] = None, config: Optional[dict] = None):
        if stage not in ALLOWED_STAGES:
            raise ValueError(f"Stage '{stage}' not in allowed target-free stages: {ALLOWED_STAGES}")
        self.node_id = node_id
        self.hypothesis_id = hypothesis_id
        self.stage = stage
        self.dependencies = dependencies or []
        self.config = config or {}
        self.config_id = self._compute_config_id(self.config)
        self.experiment_id = f"EXP-{self.config_id[:8]}-{node_id}"
        self.status = "PENDING"
        self.failure_reason = None
        self.output_artifacts = {}

    @staticmethod
    def _compute_config_id(cfg: dict) -> str:
        s = json.dumps(cfg, sort_keys=True)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

class ExperimentDAG:
    def __init__(self, budget: Optional[ResourceBudget] = None):
        self.budget = budget or ResourceBudget()
        self.nodes: Dict[str, DAGNode] = {}

    def add_node(self, node: DAGNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"Duplicate node_id: {node.node_id}")
        self.nodes[node.node_id] = node

    def get_execution_order(self) -> List[str]:
        # Topological sort
        visited = set()
        temp_mark = set()
        order = []

        def visit(n_id: str):
            if n_id in temp_mark:
                raise ValueError(f"Cyclic dependency detected at node {n_id}")
            if n_id not in visited:
                temp_mark.add(n_id)
                node = self.nodes.get(n_id)
                if not node:
                    raise KeyError(f"Dependency node {n_id} not found in DAG")
                for dep in node.dependencies:
                    if dep in self.nodes:
                        visit(dep)
                temp_mark.remove(n_id)
                visited.add(n_id)
                order.append(n_id)

        for n_id in self.nodes:
            if n_id not in visited:
                visit(n_id)
        return order

class OrchestratorCheckpoint:
    def __init__(self, checkpoint_path: str):
        self.checkpoint_path = checkpoint_path

    def load(self) -> dict:
        if os.path.exists(self.checkpoint_path):
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"completed_nodes": {}, "failed_nodes": {}}

    def save(self, data: dict) -> None:
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        tmp = self.checkpoint_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.checkpoint_path)

class OrchestratorRunner:
    def __init__(self, dag: ExperimentDAG, checkpoint_manager: OrchestratorCheckpoint):
        self.dag = dag
        self.ckpt_mgr = checkpoint_manager

    def run(self, dry_run: bool = True) -> dict:
        order = self.dag.get_execution_order()
        state = self.ckpt_mgr.load()

        results = {
            "total_nodes": len(order),
            "executed": 0,
            "resumed": 0,
            "failed": 0,
            "completed": []
        }

        for n_id in order:
            node = self.dag.nodes[n_id]
            if n_id in state.get("completed_nodes", {}):
                node.status = "COMPLETED"
                results["resumed"] += 1
                continue

            # Check dependencies
            missing_deps = [d for d in node.dependencies if d not in state.get("completed_nodes", {})]
            if missing_deps:
                node.status = "BLOCKED_MISSING_FEATURES"
                node.failure_reason = f"Unresolved dependencies: {missing_deps}"
                state["failed_nodes"][n_id] = {
                    "stage": node.stage,
                    "reason": node.failure_reason,
                    "timestamp": time.time()
                }
                results["failed"] += 1
                continue

            # Simulate execution in target-free scaffold
            node.status = "COMPLETED"
            state["completed_nodes"][n_id] = {
                "experiment_id": node.experiment_id,
                "hypothesis_id": node.hypothesis_id,
                "stage": node.stage,
                "config_id": node.config_id,
                "completed_at": time.time()
            }
            results["executed"] += 1
            results["completed"].append(node.experiment_id)

        self.ckpt_mgr.save(state)
        return results
