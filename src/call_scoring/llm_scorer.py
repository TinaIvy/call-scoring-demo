"""Score calls with a language model instead of keyword rules.

`LLMScorer` has the same shape as the rule-based `score_call`: it takes a call
and returns a dictionary of category scores. That means `evaluate.py` can
measure both in exactly the same way.

The model itself is passed in as a plain function (`complete`) that takes a
prompt and returns text. The tests use a fake function, so they run without an
API key or internet access. `anthropic_complete` is the real one.
"""

import json
import os

from .scorer import CATEGORIES, MAX_SCORE_PER_CATEGORY

RUBRIC = """You are a call coach reviewing an appointment setter's phone call with a lead.
Score the SETTER in four categories. Use 0 = missed, 1 = partly done, 2 = done well.

- greeting: the setter names the company and introduces themselves.
- discovery: the setter asks about the dog and the problem (age, breed, how long, what was tried, when it happens).
- objection_handling: when the lead hesitates (price, time, uncertainty), the setter responds with something useful. If the lead never hesitates, score 2.
- booking: the setter asks for the appointment, proposes a specific day and time, and confirms it.

Reply with JSON only, for example:
{"greeting": 2, "discovery": 1, "objection_handling": 2, "booking": 0}
"""


def build_prompt(call):
    """Combine the rubric and the transcript into one prompt."""
    transcript = "\n".join(
        f"{turn['speaker'].capitalize()}: {turn['text']}" for turn in call["turns"]
    )
    return f"{RUBRIC}\nTranscript:\n{transcript}\n"


def parse_scores(reply):
    """Pull the JSON scores out of a model reply and check they are valid.

    Models sometimes wrap JSON in extra text or a code fence, so we take
    everything from the first "{" to the last "}".
    """
    start, end = reply.find("{"), reply.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in model reply: {reply!r}")
    try:
        data = json.loads(reply[start : end + 1])
    except json.JSONDecodeError as error:
        raise ValueError(f"Model reply was not valid JSON: {reply!r}") from error

    scores = {}
    for category in CATEGORIES:
        if category not in data:
            raise ValueError(f"Model reply is missing the category {category!r}")
        value = data[category]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Score for {category!r} must be a whole number, got {value!r}")
        if not 0 <= value <= MAX_SCORE_PER_CATEGORY:
            raise ValueError(f"Score for {category!r} must be 0 to {MAX_SCORE_PER_CATEGORY}")
        scores[category] = value
    return scores


class LLMScorer:
    """A scorer that asks a language model. Call it like a function: scorer(call)."""

    def __init__(self, complete):
        self._complete = complete

    def __call__(self, call):
        return parse_scores(self._complete(build_prompt(call)))


def anthropic_complete(prompt):
    """Send a prompt to Claude and return the text of the reply.

    Needs `pip install -e ".[llm]"` and an ANTHROPIC_API_KEY environment
    variable. This function is not covered by the automated tests, because the
    tests must not need a key or network access.
    """
    try:
        import anthropic
    except ImportError as error:
        raise RuntimeError('Install the anthropic package: pip install -e ".[llm]"') from error

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    model = os.environ.get("CALL_SCORING_MODEL", "claude-sonnet-5-5")
    message = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
