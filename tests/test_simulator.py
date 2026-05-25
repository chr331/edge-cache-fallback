from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import (  # noqa: E402
    SimulationConfig,
    aggregate_trial_rows,
    formal_scenarios,
    run_policy,
    run_repeated_trials,
    run_scenario,
)


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

    def test_neighbor_availability_can_differ_from_local_availability(self) -> None:
        config = SimulationConfig(
            num_requests=20,
            local_es_count=1,
            neighbor_group_size=3,
            k=1,
            es_availability=1.0,
            neighbor_es_availability=0.0,
        )

        local_rows = run_policy("B0", config)
        neighbor_config = SimulationConfig(
            num_requests=20,
            local_es_count=0,
            neighbor_group_size=3,
            k=1,
            es_availability=1.0,
            neighbor_es_availability=0.0,
        )
        neighbor_rows = run_policy("B1", neighbor_config)

        self.assertTrue(all(row["completion"] == "local" for row in local_rows))
        self.assertTrue(all(row["completion"] == "origin_after_neighbor" for row in neighbor_rows))
        self.assertEqual(1.0, neighbor_rows[0]["local_es_availability"])
        self.assertEqual(0.0, neighbor_rows[0]["neighbor_es_availability"])

    def test_b2_expected_delay_uses_neighbor_availability(self) -> None:
        config = SimulationConfig(
            num_requests=20,
            local_es_count=0,
            neighbor_group_size=3,
            k=1,
            es_availability=1.0,
            neighbor_es_availability=0.0,
            origin_delay=180.0,
        )

        rows = run_policy("B2", config)

        self.assertTrue(all(row["completion"] == "b2_origin_choice" for row in rows))
        self.assertTrue(all(not row["neighbor_attempted"] for row in rows))

    def test_b2_reduces_invalid_neighbor_search_when_neighbor_is_unreliable(self) -> None:
        config = SimulationConfig(
            num_requests=20,
            local_es_count=0,
            neighbor_group_size=5,
            k=3,
            es_availability=0.82,
            neighbor_es_availability=0.25,
            origin_delay=180.0,
        )

        b1_rows = run_policy("B1", config)
        b2_rows = run_policy("B2", config)

        self.assertGreater(
            sum(1 for row in b1_rows if row["neighbor_attempted"]),
            sum(1 for row in b2_rows if row["neighbor_attempted"]),
        )

    def test_scenario_summary_contains_all_policies(self) -> None:
        config = SimulationConfig(num_requests=20)

        summary_rows, raw_rows = run_scenario(config)

        self.assertEqual(["B0", "B1", "B2"], [row["policy"] for row in summary_rows])
        self.assertEqual(60, len(raw_rows))

    def test_repeated_trials_report_trial_count_and_ci(self) -> None:
        config = SimulationConfig(num_requests=20, seed=123)

        rows, _ = run_repeated_trials(config, trials=3, sweep_name="baseline")

        self.assertEqual({3}, {row["trial_count"] for row in rows})
        for row in rows:
            self.assertLessEqual(
                row["mean_response_time_ci95_low"],
                row["mean_response_time_mean"],
            )
            self.assertGreaterEqual(
                row["mean_response_time_ci95_high"],
                row["mean_response_time_mean"],
            )

    def test_b2_advantage_uses_b1_minus_b2_mean_response_time(self) -> None:
        rows = []
        for trial_index, (b1_mean, b2_mean) in enumerate([(10.0, 7.0), (14.0, 9.0)]):
            rows.append(_trial_row("B1", trial_index, b1_mean))
            rows.append(_trial_row("B2", trial_index, b2_mean))

        aggregated = aggregate_trial_rows(rows)
        b2_row = next(row for row in aggregated if row["policy"] == "B2")

        self.assertEqual(4.0, b2_row["b2_advantage_vs_b1_mean"])

    def test_repeated_trials_are_reproducible_with_fixed_seed(self) -> None:
        config = SimulationConfig(num_requests=20, seed=456)

        first_rows, _ = run_repeated_trials(config, trials=2, sweep_name="baseline")
        second_rows, _ = run_repeated_trials(config, trials=2, sweep_name="baseline")

        self.assertEqual(first_rows, second_rows)

    def test_formal_scenarios_include_all_policies_with_valid_ci(self) -> None:
        base = SimulationConfig(num_requests=20, seed=789)

        for config in formal_scenarios(base):
            rows, _ = run_repeated_trials(
                config,
                trials=2,
                sweep_name="formal_scenario",
                sweep_value=config.scenario,
            )

            self.assertEqual(["B0", "B1", "B2"], [row["policy"] for row in rows])
            for row in rows:
                self.assertLessEqual(
                    row["mean_response_time_ci95_low"],
                    row["mean_response_time_mean"],
                )
                self.assertGreaterEqual(
                    row["mean_response_time_ci95_high"],
                    row["mean_response_time_mean"],
                )


def _trial_row(policy: str, trial_index: int, mean_response_time: float) -> dict:
    return {
        "scenario": "unit",
        "policy": policy,
        "trial_index": trial_index,
        "sweep_name": "baseline",
        "sweep_value": "",
        "mean_response_time": mean_response_time,
        "p95_response_time": mean_response_time + 1.0,
        "origin_free_rate": 0.5,
        "neighbor_failure_rate": 0.1,
        "zipf_alpha": 1.1,
        "es_availability": 0.82,
        "local_es_availability": 0.82,
        "neighbor_es_availability": 0.82,
        "origin_delay": 180.0,
        "local_es_count": 3,
        "neighbor_group_size": 5,
        "k": 3,
    }


if __name__ == "__main__":
    unittest.main()
