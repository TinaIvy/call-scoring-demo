"""Compare a scorer's results with human scores and report accuracy by category.

Run it from the project folder:

    python -m call_scoring.evaluate                # rule-based scorer
    python -m call_scoring.evaluate --scorer llm   # Claude-based scorer (needs an API key)
"""

import argparse

from .loader import load_calls
from .scorer import CATEGORIES, score_call, total_score


def evaluate(calls, scorer):
    """Run `scorer` on every call and compare its scores with the human scores.

    `scorer` is any function that takes a call and returns a dictionary of
    category scores. That is what lets us test the rule-based scorer and an
    AI-based scorer with exactly the same code.
    """
    if not calls:
        raise ValueError("There are no calls to evaluate.")

    exact_matches = {category: 0 for category in CATEGORIES}
    absolute_errors = {category: 0 for category in CATEGORIES}
    total_score_error = 0
    misses = []

    for call in calls:
        predicted = scorer(call)
        human = call["human_scores"]
        for category in CATEGORIES:
            difference = abs(predicted[category] - human[category])
            absolute_errors[category] += difference
            if difference == 0:
                exact_matches[category] += 1
            else:
                misses.append(
                    {
                        "call_id": call["id"],
                        "category": category,
                        "human": human[category],
                        "scorer": predicted[category],
                    }
                )
        total_score_error += abs(total_score(predicted) - total_score(human))

    call_count = len(calls)
    categories = {
        category: {
            "exact_match_rate": exact_matches[category] / call_count,
            "mean_absolute_error": absolute_errors[category] / call_count,
        }
        for category in CATEGORIES
    }
    overall_matches = sum(exact_matches.values())
    return {
        "call_count": call_count,
        "categories": categories,
        "overall_exact_match_rate": overall_matches / (call_count * len(CATEGORIES)),
        "total_score_mean_absolute_error": total_score_error / call_count,
        "misses": misses,
    }


def format_report(results):
    """Turn the results of `evaluate` into a readable text report."""
    lines = [
        f"Calls evaluated: {results['call_count']}",
        "",
        f"{'Category':<22}{'Exact match':>12}{'Avg error':>12}",
        "-" * 46,
    ]
    for category, numbers in results["categories"].items():
        lines.append(
            f"{category:<22}"
            f"{numbers['exact_match_rate']:>11.0%} "
            f"{numbers['mean_absolute_error']:>11.2f}"
        )
    lines += [
        "-" * 46,
        f"{'All categories':<22}{results['overall_exact_match_rate']:>11.0%}",
        f"Average error in total score (0-8 scale): "
        f"{results['total_score_mean_absolute_error']:.2f}",
        "",
    ]
    if results["misses"]:
        lines.append("Disagreements with the human scores:")
        for miss in results["misses"]:
            lines.append(
                f"  {miss['call_id']}  {miss['category']:<20}"
                f"human {miss['human']}  scorer {miss['scorer']}"
            )
    else:
        lines.append("The scorer agrees with every human score.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate a call scorer against human scores.")
    parser.add_argument("path", nargs="?", default="data/calls.json", help="JSON file of calls")
    parser.add_argument(
        "--scorer",
        choices=("rules", "llm"),
        default="rules",
        help="which scorer to evaluate (default: rules)",
    )
    args = parser.parse_args(argv)

    if args.scorer == "llm":
        # Imported here so the rule-based path never needs the anthropic package.
        from .llm_scorer import LLMScorer, anthropic_complete

        scorer = LLMScorer(anthropic_complete)
    else:
        scorer = score_call

    print(format_report(evaluate(load_calls(args.path), scorer)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
