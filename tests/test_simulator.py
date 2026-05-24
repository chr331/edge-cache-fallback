from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import SimulationConfig, run_policy, run_scenario  # noqa: E402


class SimulatorTests(unittest.TestCase):
    def test_local_success_avoids_origin(self) -> None:
        config = SimulationConfig(
            num_requests=20,
            local_es_count=3,
            neighbor_group_size=0,
            k=1,
            es_availability=1.0,
        )

        rows = run_policy("B0", config)

        self.assertTrue(all(not row["origin_used"] for row in rows))
        self.assertTrue(all(row["completion"] == "local" for row in rows))

    def test_b0_falls_back_to_origin_after_local_failure(self) -> None:
        config = SimulationConfig(
            num_requests=20,
            local_es_count=0,
            neighbor_group_size=3,
            k=1,
            es_availability=1.0,
        )

        rows = run_policy("B0", config)

        self.assertTrue(all(row["origin_used"] for row in rows))
        self.assertTrue(all(not row["neighbor_attempted"] for row in rows))

    def test_b1_uses_neighbor_when_neighbor_can_recover(self) -> None:
        config = SimulationConfig(
            num_requests=20,
            local_es_count=0,
            neighbor_group_size=3,
            k=1,
            es_availability=1.0,
        )

        rows = run_policy("B1", config)

        self.assertTrue(all(not row["origin_used"] for row in rows))
        self.assertTrue(all(row["neighbor_attempted"] for row in rows))
        self.assertTrue(all(row["completion"] == "neighbor" for row in rows))

    def test_b2_chooses_origin_when_neighbor_expected_delay_is_worse(self) -> None:
        config = SimulationConfig(
            num_requests=20,
            local_es_count=0,
            neighbor_group_size=3,
            k=1,
            es_availability=1.0,
            origin_delay=20.0,
            neighbor_recovery_delay=100.0,
        )

        rows = run_policy("B2", config)

        self.assertTrue(all(row["origin_used"] for row in rows))
        self.assertTrue(all(not row["neighbor_attempted"] for row in rows))

    def test_scenario_summary_contains_all_policies(self) -> None:
        config = SimulationConfig(num_requests=20)

        summary_rows, raw_rows = run_scenario(config)

        self.assertEqual(["B0", "B1", "B2"], [row["policy"] for row in summary_rows])
        self.assertEqual(60, len(raw_rows))


if __name__ == "__main__":
    unittest.main()
