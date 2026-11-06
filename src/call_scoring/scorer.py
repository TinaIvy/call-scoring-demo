"""Rule-based scoring of appointment-setter calls.

Every call is scored from 0 to 2 in four categories using simple keyword rules:

    0 = missed, 1 = partly done, 2 = done well

The rules are deliberately transparent, so any score can be explained in one
sentence. They are also deliberately limited: they look for words, not meaning.
The evaluation script (evaluate.py) shows where that falls short.
"""

import re

CATEGORIES = ("greeting", "discovery", "objection_handling", "booking")
MAX_SCORE_PER_CATEGORY = 2

# Everything below is lowercase, because we compare against lowercased text.
COMPANY_NAME = "happy paws"
INTRO_PHRASES = ("this is", "speaking", "my name is")

# Discovery: each topic the setter asks about counts once.
DISCOVERY_TOPICS = {
    "age": ("how old",),
    "breed": ("breed",),
    "duration": ("how long",),
    "history": ("tried", "training before"),
    "trigger": ("happen", "every visitor", "when does"),
}

# Objections: phrases a lead might use to hesitate.
OBJECTION_PHRASES = (
    "worried",
    "expensive",
    "budget",
    "price is",
    "concern",
    "can't afford",
    "too much",
    "more than i expected",
    "think about it",
    "not sure",
    "don't have time",
)
# Responses: a concrete offer is worth more than a polite acknowledgement.
SPECIFIC_RESPONSES = ("free", "payment plan", "flexible", "evening", "online", "discount")
GENERIC_RESPONSES = ("option", "understand", "fair", "price point")

# Booking: asking for the appointment, proposing a specific time, confirming it.
ASK_PHRASES = ("consultation", "appointment", "book", "schedule", "come in", "session")
CONFIRM_PHRASES = ("booked", "confirmed", "you're all set", "i've scheduled")
TIME_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    r"[^.?!]*?\b\d{1,2}(:\d{2})?\s*(am|pm)\b"
)


def _setter_texts(call):
    """Return everything the setter said, lowercased, in order."""
    return [turn["text"].lower() for turn in call["turns"] if turn["speaker"] == "setter"]


def _contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def score_greeting(call):
    """One point for naming the company, one for the setter introducing themselves.

    Only the first thing the setter says counts. If the setter never speaks,
    the score is 0.
    """
    setter_texts = _setter_texts(call)
    if not setter_texts:
        return 0
    first = setter_texts[0]
    points = 0
    if COMPANY_NAME in first:
        points += 1
    if _contains_any(first, INTRO_PHRASES):
        points += 1
    return points


def score_discovery(call):
    """Count how many different topics the setter asked about.

    Two or more topics = 2, one topic = 1, none = 0.
    """
    setter_text = " ".join(_setter_texts(call))
    topics_asked = sum(
        1 for phrases in DISCOVERY_TOPICS.values() if _contains_any(setter_text, phrases)
    )
    return min(topics_asked, MAX_SCORE_PER_CATEGORY)


def _score_response(response_text):
    """Score how well one setter reply deals with an objection."""
    if _contains_any(response_text, SPECIFIC_RESPONSES):
        return 2
    if _contains_any(response_text, GENERIC_RESPONSES):
        return 1
    return 0


def score_objection_handling(call):
    """Score the setter's reply to each objection the lead raised.

    If the lead never objects, there is nothing to mishandle, so the score is 2.
    If there are several objections, the weakest reply decides the score.
    """
    turns = call["turns"]
    reply_scores = []
    for index, turn in enumerate(turns):
        if turn["speaker"] != "lead":
            continue
        if not _contains_any(turn["text"].lower(), OBJECTION_PHRASES):
            continue
        next_setter_turn = next(
            (later for later in turns[index + 1 :] if later["speaker"] == "setter"),
            None,
        )
        if next_setter_turn is None:
            reply_scores.append(0)
        else:
            reply_scores.append(_score_response(next_setter_turn["text"].lower()))
    return min(reply_scores) if reply_scores else MAX_SCORE_PER_CATEGORY


def score_booking(call):
    """2 = asked, proposed a specific day and time, and confirmed it.

    1 = asked for the appointment but did not get as far as a confirmed time.
    0 = never asked.
    """
    setter_texts = _setter_texts(call)
    asked = any(_contains_any(text, ASK_PHRASES) for text in setter_texts)
    proposed_time = any(TIME_PATTERN.search(text) for text in setter_texts)
    confirmed = any(_contains_any(text, CONFIRM_PHRASES) for text in setter_texts)
    if asked and proposed_time and confirmed:
        return 2
    if asked:
        return 1
    return 0


def score_call(call):
    """Score one call and return a dictionary like {"greeting": 2, "discovery": 1, ...}."""
    return {
        "greeting": score_greeting(call),
        "discovery": score_discovery(call),
        "objection_handling": score_objection_handling(call),
        "booking": score_booking(call),
    }


def total_score(scores):
    """Add up the category scores. The maximum is 8."""
    return sum(scores[category] for category in CATEGORIES)
