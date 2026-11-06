import pytest

from call_scoring.evaluate import evaluate, format_report, main
from call_scoring.scorer import CATEGORIES

CALLS = [
    {"id": "a", "turns": [], "human_scores": {c: 2 for c in CATEGORIES}},
    {"id": "b", "turns": [], "human_scores": {c: 0 for c in CATEGORIES}},
]


def perfect_scorer(call):
    return dict(call["human_scores"])


def always_one_scorer(call):
    return {c: 1 for c in CATEGORIES}


def test_perfect_scorer_has_full_accuracy_and_no_error():
    results = evaluate(CALLS, perfect_scorer)
    assert results["overall_exact_match_rate"] == 1.0
    assert results["total_score_mean_absolute_error"] == 0.0
    assert results["misses"] == []


def test_always_one_scorer_is_never_exactly_right_and_off_by_one():
    results = evaluate(CALLS, always_one_scorer)
    assert results["overall_exact_match_rate"] == 0.0
    for numbers in results["categories"].values():
        assert numbers["mean_absolute_error"] == 1.0
    # Both calls are off by 4 points in total (4 categories x 1 point).
    assert results["total_score_mean_absolute_error"] == 4.0


def test_misses_name_the_call_category_and_both_scores():
    results = evaluate(CALLS, always_one_scorer)
    assert {
        "call_id": "a",
        "category": "greeting",
        "human": 2,
        "scorer": 1,
    } in results["misses"]


def test_evaluate_rejects_an_empty_list_of_calls():
    with pytest.raises(ValueError):
        evaluate([], perfect_scorer)


def test_report_lists_every_category():
    report = format_report(evaluate(CALLS, always_one_scorer))
    for category in CATEGORIES:
        assert category in report


def test_report_says_so_when_there_are_no_disagreements():
    report = format_report(evaluate(CALLS, perfect_scorer))
    assert "agrees with every human score" in report


def test_command_line_runs_on_the_sample_data(capsys):
    assert main(["data/calls.json"]) == 0
    assert "Calls evaluated: 10" in capsys.readouterr().out
