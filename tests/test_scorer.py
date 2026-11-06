import pytest

from call_scoring.loader import load_calls
from call_scoring.scorer import (
    CATEGORIES,
    score_booking,
    score_call,
    score_discovery,
    score_greeting,
    score_objection_handling,
    total_score,
)

CALLS_FILE = "data/calls.json"


def make_call(*turns):
    """Build a small call from (speaker, text) pairs, so tests stay short."""
    return {"id": "test", "turns": [{"speaker": s, "text": t} for s, t in turns]}


# --- greeting -------------------------------------------------------------


def test_greeting_with_company_and_name_scores_two():
    call = make_call(("setter", "Thanks for calling Happy Paws Training, this is Jamie."))
    assert score_greeting(call) == 2


def test_greeting_with_company_only_scores_one():
    call = make_call(("setter", "Happy Paws Training, how can I help?"))
    assert score_greeting(call) == 1


def test_greeting_without_either_scores_zero():
    call = make_call(("lead", "Hi, do you train dogs?"), ("setter", "Yes."))
    assert score_greeting(call) == 0


def test_greeting_is_judged_on_the_first_setter_turn_even_if_the_lead_speaks_first():
    call = make_call(
        ("lead", "Hello?"),
        ("setter", "Hi, this is Pat from Happy Paws Training."),
    )
    assert score_greeting(call) == 2


def test_greeting_is_zero_when_the_setter_never_speaks():
    assert score_greeting(make_call(("lead", "Hello?"))) == 0


# --- discovery ------------------------------------------------------------


def test_discovery_two_topics_scores_two():
    call = make_call(("setter", "How old is Bella and what breed is she?"))
    assert score_discovery(call) == 2


def test_discovery_one_topic_scores_one():
    call = make_call(("setter", "How old is your puppy?"))
    assert score_discovery(call) == 1


def test_discovery_no_questions_scores_zero():
    call = make_call(("setter", "We offer many programs."))
    assert score_discovery(call) == 0


def test_discovery_caps_at_two_even_with_many_topics():
    call = make_call(
        ("setter", "How old is he, what breed, how long has it gone on, and have you tried training before?")
    )
    assert score_discovery(call) == 2


# --- objection handling ---------------------------------------------------


def test_no_objection_scores_two():
    call = make_call(("lead", "Sounds great."), ("setter", "Wonderful."))
    assert score_objection_handling(call) == 2


def test_objection_answered_with_a_concrete_offer_scores_two():
    call = make_call(
        ("lead", "I'm worried about the price."),
        ("setter", "The first consultation is free."),
    )
    assert score_objection_handling(call) == 2


def test_objection_answered_generically_scores_one():
    call = make_call(
        ("lead", "That's expensive."),
        ("setter", "We have a few options."),
    )
    assert score_objection_handling(call) == 1


def test_objection_ignored_scores_zero():
    call = make_call(
        ("lead", "I don't have time for weekly classes."),
        ("setter", "Okay, bye."),
    )
    assert score_objection_handling(call) == 0


def test_objection_with_no_setter_reply_scores_zero():
    call = make_call(("lead", "I'm not sure about this."))
    assert score_objection_handling(call) == 0


def test_weakest_reply_decides_when_there_are_several_objections():
    call = make_call(
        ("lead", "I'm worried about the price."),
        ("setter", "It is free to start."),
        ("lead", "I also don't have time."),
        ("setter", "Okay."),
    )
    assert score_objection_handling(call) == 0


# --- booking --------------------------------------------------------------


def test_booking_with_time_and_confirmation_scores_two():
    call = make_call(
        ("setter", "Would Thursday at 4 PM work for a consultation?"),
        ("lead", "Yes."),
        ("setter", "Great, I've booked you."),
    )
    assert score_booking(call) == 2


def test_booking_ask_without_a_time_scores_one():
    call = make_call(("setter", "Do you want to come in for a consultation sometime?"))
    assert score_booking(call) == 1


def test_booking_never_asked_scores_zero():
    call = make_call(("setter", "Have a great day!"))
    assert score_booking(call) == 0


# --- whole calls ----------------------------------------------------------


def test_score_call_returns_every_category():
    call = make_call(("setter", "Hello."))
    assert set(score_call(call)) == set(CATEGORIES)


def test_total_score_adds_the_categories():
    scores = {"greeting": 2, "discovery": 1, "objection_handling": 0, "booking": 2}
    assert total_score(scores) == 5


# Where the keyword rules are known to disagree with the human raters.
# Each entry is (call id, category). If you improve the rules, update this set.
KNOWN_MISSES = {
    ("call-07", "discovery"),  # asked open questions without our keywords
    ("call-07", "objection_handling"),  # good reply, but it uses words we do not look for
    ("call-07", "booking"),  # "tomorrow at noon" is not a weekday plus a clock time
    ("call-09", "booking"),  # booked, but only by pushing past the lead's hesitation
}


def test_rules_disagree_with_humans_only_where_we_expect():
    misses = set()
    for call in load_calls(CALLS_FILE):
        predicted = score_call(call)
        for category in CATEGORIES:
            if predicted[category] != call["human_scores"][category]:
                misses.add((call["id"], category))
    assert misses == KNOWN_MISSES


@pytest.mark.parametrize("call_id", ["call-01", "call-02", "call-05", "call-08", "call-10"])
def test_rules_match_the_humans_exactly_on_clear_calls(call_id):
    call = next(c for c in load_calls(CALLS_FILE) if c["id"] == call_id)
    assert score_call(call) == call["human_scores"]
