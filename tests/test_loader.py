from call_scoring.loader import load_calls

CALLS_FILE = "data/calls.json"


def test_load_calls_returns_ten_calls():
    calls = load_calls(CALLS_FILE)
    assert len(calls) == 10


def test_each_call_has_id_turns_and_human_scores():
    calls = load_calls(CALLS_FILE)
    for call in calls:
        assert "id" in call
        assert "turns" in call
        assert "human_scores" in call


def test_call_ids_are_unique():
    ids = [call["id"] for call in load_calls(CALLS_FILE)]
    assert len(ids) == len(set(ids))


def test_human_scores_are_between_zero_and_two():
    for call in load_calls(CALLS_FILE):
        for score in call["human_scores"].values():
            assert 0 <= score <= 2
