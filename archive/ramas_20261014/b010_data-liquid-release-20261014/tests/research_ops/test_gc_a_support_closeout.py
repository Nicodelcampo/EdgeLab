import copy
import unittest

from tools.research_ops.audits.summarize_gc_a_support import normalized_states


class SparseStateSerializationTests(unittest.TestCase):
    def test_missing_zero_states_are_semantically_equal(self):
        sparse = {"A_ONLY": 1, "E_ONLY": 239, "NEITHER": 4837, "UNKNOWN": 6529}
        dense = dict(sparse, BOTH=0)
        self.assertNotEqual(sparse, dense)
        self.assertEqual(normalized_states(sparse), normalized_states(dense))

    def test_missing_nonzero_state_is_not_equal(self):
        self.assertNotEqual(normalized_states({"A_ONLY": 2}),
                            normalized_states({}))

    def test_invalid_values_and_undeclared_states_are_rejected(self):
        for bad in ({"NEW_STATE": 0}, {"BOTH": -1}, {"BOTH": True}, {"BOTH": None}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                normalized_states(bad)

    def test_receipt_input_is_not_mutated(self):
        sparse = {"E_ONLY": 3}
        saved = copy.deepcopy(sparse)
        self.assertEqual(sum(normalized_states(sparse).values()), 3)
        self.assertEqual(sparse, saved)


if __name__ == "__main__":
    unittest.main()