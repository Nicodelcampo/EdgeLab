import unittest
import os
import shutil
import tempfile
from edgelab.edge_factory.orchestrator import (
    ResourceBudget,
    DAGNode,
    ExperimentDAG,
    OrchestratorCheckpoint,
    OrchestratorRunner,
    ALLOWED_STAGES
)

class TestEdgeFactoryOrchestrator(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.ckpt_path = os.path.join(self.test_dir, "test_ckpt.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_budget_constraints(self):
        budget = ResourceBudget(max_memory_mb=1500.0, max_concurrency=1)
        self.assertTrue(budget.check_memory(1200.0))
        self.assertFalse(budget.check_memory(1600.0))
        self.assertEqual(budget.max_concurrency, 1)

    def test_invalid_stage_rejected(self):
        with self.assertRaises(ValueError):
            DAGNode(node_id="n1", hypothesis_id="HP-01", stage="CONFIRMATORY_LIVE")

    def test_dag_topological_order(self):
        dag = ExperimentDAG()
        n1 = DAGNode(node_id="census", hypothesis_id="HP-01", stage="TARGET_FREE_CENSUS")
        n2 = DAGNode(node_id="features", hypothesis_id="HP-01", stage="PROPOSED_TARGET_FREE", dependencies=["census"])
        n3 = DAGNode(node_id="prereg", hypothesis_id="HP-01", stage="READY_FOR_PREREGISTRATION", dependencies=["features"])

        dag.add_node(n3)
        dag.add_node(n1)
        dag.add_node(n2)

        order = dag.get_execution_order()
        self.assertEqual(order, ["census", "features", "prereg"])

    def test_dag_cycle_detection(self):
        dag = ExperimentDAG()
        n1 = DAGNode(node_id="a", hypothesis_id="HP-01", stage="PROPOSED_TARGET_FREE", dependencies=["b"])
        n2 = DAGNode(node_id="b", hypothesis_id="HP-01", stage="PROPOSED_TARGET_FREE", dependencies=["a"])
        dag.add_node(n1)
        dag.add_node(n2)
        with self.assertRaises(ValueError):
            dag.get_execution_order()

    def test_orchestrator_execution_and_resume(self):
        dag = ExperimentDAG()
        n1 = DAGNode(node_id="c1", hypothesis_id="HP-01", stage="TARGET_FREE_CENSUS")
        n2 = DAGNode(node_id="c2", hypothesis_id="HP-01", stage="PROPOSED_TARGET_FREE", dependencies=["c1"])
        dag.add_node(n1)
        dag.add_node(n2)

        ckpt = OrchestratorCheckpoint(self.ckpt_path)
        runner = OrchestratorRunner(dag, ckpt)

        # First run executes all nodes
        res1 = runner.run()
        self.assertEqual(res1["executed"], 2)
        self.assertEqual(res1["resumed"], 0)

        # Second run resumes seamlessly
        res2 = runner.run()
        self.assertEqual(res2["executed"], 0)
        self.assertEqual(res2["resumed"], 2)

if __name__ == "__main__":
    unittest.main()
