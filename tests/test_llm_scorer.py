import pytest

from call_scoring.evaluate import evaluate
from call_scoring.llm_scorer import LLMScorer, build_prompt, parse_scores

CALL = {
    "id": "x",
    "turns": [
        {"speaker": "setter", "text": "Happy Paws Training, this is Jo."},
        {"speaker": "lead", "text": "Hi."},
    ],
    "human_scores": {"greeting": 2, "discovery": 0, "objection_handling": 2, "booking": 0},
}

GOOD_REPLY = '{"greeting": 2, "discovery": 0, "objection_handling": 2, "booking": 0}'


def test_prompt_contains_the_rubric_and_the_transcript():
    prompt = build_prompt(CALL)
    assert "objection_handling" in prompt
    assert "Setter: Happy Paws Training, this is Jo." in prompt
    assert "Lead: Hi." in prompt


def test_parse_scores_reads_plain_json():
    assert parse_scores(GOOD_REPLY)["greeting"] == 2


def test_parse_scores_ignores_text_and_code_fences_around_the_json():
    reply = f"Here are the scores:\n```json\n{GOOD_REPLY}\n```\nHope that helps!"
    assert parse_scores(reply) == {
        "greeting": 2,
        "discovery": 0,
        "objection_handling": 2,
        "booking": 0,
    }


@pytest.mark.parametrize(
    "bad_reply",
    [
        "I cannot score this call.",
        '{"greeting": 2}',
        '{"greeting": 3, "discovery": 0, "objection_handling": 2, "booking": 0}',
        '{"greeting": "2", "discovery": 0, "objection_handling": 2, "booking": 0}',
        '{"greeting": true, "discovery": 0, "objection_handling": 2, "booking": 0}',
        "{not json}",
    ],
)
def test_parse_scores_rejects_invalid_replies(bad_reply):
    with pytest.raises(ValueError):
        parse_scores(bad_reply)


def test_llm_scorer_sends_the_prompt_and_parses_the_reply():
    seen_prompts = []

    def fake_complete(prompt):
        seen_prompts.append(prompt)
        return GOOD_REPLY

    scorer = LLMScorer(fake_complete)
    assert scorer(CALL) == CALL["human_scores"]
    assert len(seen_prompts) == 1
    assert "Happy Paws Training" in seen_prompts[0]


def test_llm_scorer_plugs_into_the_evaluation():
    scorer = LLMScorer(lambda prompt: GOOD_REPLY)
    results = evaluate([CALL], scorer)
    assert results["overall_exact_match_rate"] == 1.0
