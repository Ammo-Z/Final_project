"""Evaluation Metrics — Cohen's kappa, rubric aggregation, statistical testing."""

from __future__ import annotations
import json
import numpy as np
from typing import Optional
from ..core.schemas import EvalResult


def cohens_kappa(rater1: list[int], rater2: list[int]) -> float:
    """Calculate Cohen's kappa inter-rater reliability.

    Args:
        rater1: Scores from rater 1 (e.g., model judge)
        rater2: Scores from rater 2 (e.g., human)

    Returns:
        Cohen's kappa coefficient (-1 to 1, >0.6 = substantial agreement)
    """
    assert len(rater1) == len(rater2), "Rater lists must be same length"

    n = len(rater1)
    categories = sorted(set(rater1) | set(rater2))
    k = len(categories)

    # Build confusion matrix
    cat_to_idx = {c: i for i, c in enumerate(categories)}
    matrix = np.zeros((k, k), dtype=int)
    for r1, r2 in zip(rater1, rater2):
        matrix[cat_to_idx[r1]][cat_to_idx[r2]] += 1

    # Observed agreement
    po = np.trace(matrix) / n

    # Expected agreement
    row_sums = matrix.sum(axis=1)
    col_sums = matrix.sum(axis=0)
    pe = np.sum(row_sums * col_sums) / (n * n)

    if pe == 1.0:
        return 1.0

    kappa = (po - pe) / (1 - pe)
    return float(kappa)


def aggregate_rubric_scores(results: list[EvalResult]) -> dict:
    """Aggregate rubric scores across all evaluated cases.

    Returns:
        Dict with mean, std, min, max for each dimension, plus overall stats
    """
    dimensions = [
        "translation_accuracy",
        "completeness",
        "citation_faithfulness",
        "action_usefulness",
        "refusal_correctness",
    ]

    stats = {}
    for dim in dimensions:
        scores = []
        for result in results:
            if dim in result.scores:
                scores.append(result.scores[dim].score)

        if scores:
            stats[dim] = {
                "mean": float(np.mean(scores)),
                "std": float(np.std(scores)),
                "min": float(np.min(scores)),
                "max": float(np.max(scores)),
                "count": len(scores),
            }
        else:
            stats[dim] = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "count": 0}

    # Overall scores
    overall_scores = [r.overall_score for r in results if r.overall_score > 0]
    stats["overall"] = {
        "mean": float(np.mean(overall_scores)) if overall_scores else 0.0,
        "std": float(np.std(overall_scores)) if overall_scores else 0.0,
        "min": float(np.min(overall_scores)) if overall_scores else 0.0,
        "max": float(np.max(overall_scores)) if overall_scores else 0.0,
        "count": len(overall_scores),
    }

    # Win rate
    wins = sum(1 for r in results if r.win_vs_gold)
    stats["win_rate"] = wins / len(results) if results else 0.0

    return stats


def paired_bootstrap_test(
    scores_system: list[float],
    scores_baseline: list[float],
    n_bootstrap: int = 10000,
    confidence: float = 0.95,
) -> dict:
    """Paired bootstrap test for statistical significance.

    Tests whether the system scores are significantly different from baseline.

    Args:
        scores_system: System scores per case
        scores_baseline: Baseline scores per case
        n_bootstrap: Number of bootstrap iterations
        confidence: Confidence level

    Returns:
        Dict with mean_diff, ci_lower, ci_upper, p_value, significant
    """
    assert len(scores_system) == len(scores_baseline)
    n = len(scores_system)

    # Observed difference
    observed_diff = np.mean(scores_system) - np.mean(scores_baseline)

    # Bootstrap
    rng = np.random.RandomState(42)
    diffs = []
    for _ in range(n_bootstrap):
        idx = rng.randint(0, n, size=n)
        boot_sys = np.mean([scores_system[i] for i in idx])
        boot_base = np.mean([scores_baseline[i] for i in idx])
        diffs.append(boot_sys - boot_base)

    diffs = np.array(diffs)
    alpha = 1 - confidence
    ci_lower = float(np.percentile(diffs, 100 * alpha / 2))
    ci_upper = float(np.percentile(diffs, 100 * (1 - alpha / 2)))

    # P-value (two-sided)
    p_value = float(np.mean(np.abs(diffs - np.mean(diffs)) >= np.abs(observed_diff)))

    return {
        "mean_diff": float(observed_diff),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": p_value,
        "significant": p_value < alpha,
        "n_bootstrap": n_bootstrap,
        "confidence": confidence,
    }


def compute_evaluation_report(
    results: list[EvalResult],
    baseline_results: Optional[list[EvalResult]] = None,
    human_scores: Optional[dict[str, list[int]]] = None,
) -> dict:
    """Generate a comprehensive evaluation report.

    Args:
        results: System evaluation results
        baseline_results: Optional baseline results for comparison
        human_scores: Optional human spot-check scores {case_id: [dim_scores]}

    Returns:
        Complete evaluation report dict
    """
    report = {
        "system_scores": aggregate_rubric_scores(results),
        "total_cases": len(results),
        "published_cases": sum(1 for r in results if r.overall_score > 0),
        "refusal_cases": sum(1 for r in results if r.overall_score == 0),
    }

    # Baseline comparison
    if baseline_results:
        report["baseline_scores"] = aggregate_rubric_scores(baseline_results)

        # Statistical significance
        sys_overall = [r.overall_score for r in results]
        base_overall = [r.overall_score for r in baseline_results]
        if len(sys_overall) == len(base_overall):
            report["bootstrap_test"] = paired_bootstrap_test(sys_overall, base_overall)

    # Inter-rater reliability
    if human_scores:
        model_scores_flat = []
        human_scores_flat = []
        for result in results:
            case_id = result.case_id
            if case_id in human_scores:
                # Use overall score bucketed to 1-5
                model_bucket = min(5, max(1, round(result.overall_score)))
                model_scores_flat.append(model_bucket)
                human_scores_flat.append(
                    round(np.mean(human_scores[case_id]))
                )

        if len(model_scores_flat) >= 2:
            report["cohens_kappa"] = cohens_kappa(model_scores_flat, human_scores_flat)
        else:
            report["cohens_kappa"] = None

    return report
