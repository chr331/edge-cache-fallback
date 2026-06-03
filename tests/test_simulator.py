from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edge_cache_sim import (  # noqa: E402
    MEMO_LOCAL_ES_AVAILABILITY,
    MEMO_NEIGHBOR_ES_AVAILABILITIES,
    MEMO_ORIGIN_DELAYS,
    SimulationConfig,
    aggregate_trial_rows,
    formal_scenarios,
    memo_sweep_configs,
    neighbor_cache_probability,
    neighbor_recovery_probability,
    run_policy,
    run_repeated_trials,
    run_scenario,
    should_try_neighbor,
    zipf_rank_probabilities,
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
            neighbor_cache_hot_prob=1.0,
            neighbor_cache_cold_prob=1.0,
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
            neighbor_cache_hot_prob=1.0,
            neighbor_cache_cold_prob=1.0,
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
            neighbor_cache_hot_prob=1.0,
            neighbor_cache_cold_prob=1.0,
        )

        local_rows = run_policy("B0", config)
        neighbor_config = SimulationConfig(
            num_requests=20,
            local_es_count=0,
            neighbor_group_size=3,
            k=1,
            es_availability=1.0,
            neighbor_es_availability=0.0,
            neighbor_cache_hot_prob=1.0,
            neighbor_cache_cold_prob=1.0,
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
            neighbor_cache_hot_prob=1.0,
            neighbor_cache_cold_prob=1.0,
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

    def test_zipf_probabilities_become_more_head_heavy(self) -> None:
        low_skew = zipf_rank_probabilities(num_contents=100, zipf_alpha=0.6)
        high_skew = zipf_rank_probabilities(num_contents=100, zipf_alpha=1.5)

        self.assertGreater(high_skew[0], low_skew[0])
        self.assertLess(high_skew[-1], low_skew[-1])
        self.assertAlmostEqual(1.0, float(high_skew.sum()))

    def test_neighbor_cache_probability_declines_by_rank(self) -> None:
        config = SimulationConfig(
            num_contents=500,
            zipf_alpha=1.1,
            neighbor_cache_hot_prob=0.9,
            neighbor_cache_cold_prob=0.15,
            neighbor_cache_rank_gamma=1.0,
        )

        self.assertGreater(
            neighbor_cache_probability(1, config),
            neighbor_cache_probability(500, config),
        )
        self.assertAlmostEqual(0.9, neighbor_cache_probability(1, config))

    def test_neighbor_recovery_uses_missing_chunks(self) -> None:
        config = SimulationConfig(
            neighbor_group_size=1,
            neighbor_es_availability=1.0,
            neighbor_cache_hot_prob=1.0,
            neighbor_cache_cold_prob=1.0,
        )

        self.assertEqual(
            1.0,
            neighbor_recovery_probability(config, missing_chunks=1, content_rank=1),
        )
        self.assertEqual(
            0.0,
            neighbor_recovery_probability(config, missing_chunks=3, content_rank=1),
        )

    def test_b2_can_choose_neighbor_for_hot_content_and_origin_for_cold_content(self) -> None:
        config = SimulationConfig(
            num_contents=500,
            neighbor_group_size=5,
            neighbor_es_availability=1.0,
            origin_delay=180.0,
            neighbor_cache_hot_prob=0.95,
            neighbor_cache_cold_prob=0.03,
            neighbor_cache_rank_gamma=1.0,
        )

        self.assertTrue(should_try_neighbor(config, missing_chunks=3, content_rank=1))
        self.assertFalse(should_try_neighbor(config, missing_chunks=3, content_rank=500))

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
            self.assertIn("neighbor_attempt_rate_mean", row)
            self.assertIn("neighbor_skip_rate_mean", row)
            self.assertIn("fallback_mean_response_time_mean", row)
            self.assertIn("b2_neighbor_choice_rate_mean", row)

    def test_b2_advantage_uses_b1_minus_b2_mean_response_time(self) -> None:
        rows = []
        for trial_index, (b1_mean, b2_mean) in enumerate([(10.0, 7.0), (14.0, 9.0)]):
            rows.append(_trial_row("B1", trial_index, b1_mean))
            rows.append(_trial_row("B2", trial_index, b2_mean))

        aggregated = aggregate_trial_rows(rows)
        b2_row = next(row for row in aggregated if row["policy"] == "B2")

        self.assertEqual(4.0, b2_row["b2_advantage_vs_b1_mean"])
        self.assertEqual(4.0, b2_row["b2_fallback_advantage_vs_b1_mean"])

    def test_repeated_trials_are_reproducible_with_fixed_seed(self) -> None:
        config = SimulationConfig(num_requests=20, seed=456)

        first_rows, _ = run_repeated_trials(config, trials=2, sweep_name="baseline")
        second_rows, _ = run_repeated_trials(config, trials=2, sweep_name="baseline")

        self.assertEqual(first_rows, second_rows)

    def test_formal_scenarios_include_all_policies_with_valid_ci(self) -> None:
        base = SimulationConfig(num_requests=20, seed=789)
        scenario_names = [config.scenario for config in formal_scenarios(base)]

        self.assertIn("decision_boundary_neighbor", scenario_names)

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

    def test_fallback_metrics_focus_on_local_failures(self) -> None:
        config = SimulationConfig(
            num_requests=20,
            local_es_count=0,
            neighbor_group_size=0,
            k=1,
            es_availability=1.0,
        )

        summary_rows, _ = run_scenario(config)
        b0_row = next(row for row in summary_rows if row["policy"] == "B0")

        self.assertEqual(1.0, b0_row["local_failure_rate"])
        self.assertEqual(b0_row["mean_response_time"], b0_row["fallback_mean_response_time"])
        self.assertEqual(b0_row["p95_response_time"], b0_row["fallback_p95_response_time"])
        self.assertEqual(1.0, b0_row["neighbor_skip_rate"])

    def test_memo_sweep_covers_formal_scenario_parameters(self) -> None:
        base = SimulationConfig(num_requests=20, seed=789)

        configs = memo_sweep_configs(base)
        points = {
            (config.effective_neighbor_es_availability, config.origin_delay)
            for config in configs
        }

        self.assertIn(0.25, MEMO_NEIGHBOR_ES_AVAILABILITIES)
        self.assertIn(0.82, MEMO_NEIGHBOR_ES_AVAILABILITIES)
        self.assertIn(180.0, MEMO_ORIGIN_DELAYS)
        self.assertIn(320.0, MEMO_ORIGIN_DELAYS)
        self.assertIn((0.25, 180.0), points)
        self.assertIn((0.82, 180.0), points)
        self.assertIn((0.82, 320.0), points)
        self.assertTrue(
            all(
                config.local_es_availability == MEMO_LOCAL_ES_AVAILABILITY
                for config in configs
            )
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
        "fallback_mean_response_time": mean_response_time,
        "fallback_p95_response_time": mean_response_time + 1.0,
        "origin_free_rate": 0.5,
        "local_failure_rate": 0.5,
        "neighbor_attempt_rate": 0.5,
        "neighbor_skip_rate": 0.0,
        "neighbor_failure_rate": 0.1,
        "b2_neighbor_choice_rate": 0.5,
        "zipf_alpha": 1.1,
        "es_availability": 0.82,
        "local_es_availability": 0.82,
        "neighbor_es_availability": 0.82,
        "origin_delay": 180.0,
        "local_es_count": 3,
        "neighbor_group_size": 5,
        "k": 3,
        "neighbor_cache_hot_prob": 0.9,
        "neighbor_cache_cold_prob": 0.15,
        "neighbor_cache_rank_gamma": 1.0,
    }


if __name__ == "__main__":
    unittest.main()
