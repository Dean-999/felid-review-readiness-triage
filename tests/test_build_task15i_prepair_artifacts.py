from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task15i_prepair", ROOT / "scripts/build_task15i_prepair_artifacts.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def edge(left: str, right: str, strict: bool = True) -> object:
    return MODULE.Edge(left, right, 4, 1, strict, 1, 1 if strict else None, 1, 1 if strict else None)


class Task15IPrepairArtifactTests(unittest.TestCase):
    def test_grow_components_forms_disjoint_four_edge_trees(self) -> None:
        pool = []
        for component in range(4):
            center = f"c{component}"
            for leaf in range(4):
                pool.append(edge(center, f"{center}l{leaf}"))
        selected = MODULE.grow_components(pool, set(), 4, 0)
        self.assertEqual(len(selected), 4)
        self.assertTrue(all(len(component) == 4 for component in selected))
        self.assertEqual(len({node for component in selected for item in component for node in (item.left, item.right)}), 20)

    def test_rank_band(self) -> None:
        self.assertEqual(MODULE.rank_band(MODULE.Edge("a", "b", 20, 5, True, 5, 5, 5, 5)), "top_5")
        self.assertEqual(MODULE.rank_band(MODULE.Edge("a", "b", 30, 10, True, 10, 10, 5, 5)), "top_10")
        self.assertEqual(MODULE.rank_band(MODULE.Edge("a", "b", 40, 20, False, 20, None, 20, None)), "top_20")


if __name__ == "__main__":
    unittest.main()
