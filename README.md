# Call Scoring Demo

![Tests](https://github.com/TinaIvy/call-scoring-demo/actions/workflows/tests.yml/badge.svg)

A small Python project that scores appointment-setter phone calls and then measures **how well those scores match a human coach**.

It uses made-up transcripts (a fictional company, "Happy Paws Training") and has no real customer data, keys or company information in it.

The point of the project is the second half. Scoring a call is easy to demonstrate. Knowing whether a scorer is *right* is the harder problem, and that is what the evaluation script does.

## What it does

1. **Scores calls** in four categories, each from 0 (missed) to 2 (done well):

   | Category | What is checked |
   | --- | --- |
   | Greeting | The setter names the company and introduces themselves |
   | Discovery | The setter asks about the dog and the problem (age, breed, duration, history, triggers) |
   | Objection handling | When the lead hesitates, the setter responds with something useful |
   | Booking | The setter asks for the appointment, proposes a day and time, and confirms it |

2. **Evaluates the scorer** by replaying every saved call and comparing the scorer's result to a human rating, reporting exact-match accuracy and average error per category.

3. **Supports a second scorer.** `LLMScorer` asks a Claude model to score the same calls with the same rubric. It plugs into the same evaluation, so the rule-based and AI-based scorers can be compared on equal terms.

## Example result

The rule-based scorer on the 10 sample calls:

```
Calls evaluated: 10

Category               Exact match   Avg error
----------------------------------------------
greeting                     100%        0.00
discovery                     90%        0.20
objection_handling            90%        0.20
booking                       80%        0.20
----------------------------------------------
All categories                90%
Average error in total score (0-8 scale): 0.60

Disagreements with the human scores:
  call-07  discovery           human 2  scorer 0
  call-07  objection_handling  human 2  scorer 0
  call-07  booking             human 2  scorer 1
  call-09  booking             human 1  scorer 2
```

## What the evaluation shows

Both failing calls show a limit of keyword rules:

- **call-07** is a good call in different words than the rules look for ("Tell me about Rocky..." instead of "How old is..."; "tomorrow at noon" instead of a weekday). A person sees a strong call. The rules see almost nothing.
- **call-09** gets booked, but only by pushing past the lead's hesitation. A person scores that lower. The rules only see that a time was confirmed.

These are the cases where a language model should help, and the evaluation is how to check whether it really does. The tests list these four disagreements explicitly, so a change to the rules that fixes or breaks one of them is noticed.

With only 10 calls the percentages are rough. A real evaluation would use a much larger set, written by several people.

## Run it

You need Python 3.10 or newer.

```bash
git clone https://github.com/TinaIvy/call-scoring-demo.git
cd call-scoring-demo

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest                                  # run the tests
python -m call_scoring.evaluate         # evaluate the rule-based scorer
```

### Try the AI-based scorer (optional)

```bash
pip install -e ".[llm]"
export ANTHROPIC_API_KEY="your key here"
python -m call_scoring.evaluate --scorer llm
```

The optional `CALL_SCORING_MODEL` environment variable chooses the model. The code that calls the API (`anthropic_complete`) is not covered by the automated tests, because the tests must run without a key or network access. The prompt building, the reply parsing and the evaluation are all tested using a fake model.

## Project layout

```
data/calls.json              Made-up calls with human scores (the answer key)
src/call_scoring/
    loader.py                Reads the calls file
    scorer.py                Rule-based scorer, one function per category
    llm_scorer.py            Claude-based scorer behind the same interface
    evaluate.py              Compares a scorer with the human scores
tests/                       Automated tests (pytest)
```

## Design choices

- **Plain rules first.** The rule-based scorer gives the same answer every time, which makes it easy to test and to explain. It is the baseline any smarter scorer has to beat.
- **A scorer is just a function.** Anything that takes a call and returns category scores can be evaluated. That is why the rules and the AI model share one evaluation.
- **The model is passed in.** `LLMScorer` receives a function instead of calling the API directly, so tests never need a key.
- **Known weaknesses are tested.** The disagreements above are written down in the tests, not hidden.

## Limitations

- Ten calls, one fictional company, one rater. The numbers show the method, not a benchmark.
- The rubric is simplified. Real call coaching uses more categories and a finer scale.
- The keyword rules are tuned to this data and will not generalise to other call scripts without changes.

## Next steps

- Run the AI-based scorer on the sample calls and compare it with the rules.
- Add calls from more than one rater and report how often the humans agree with each other.
- Report disagreements by call type, not only by category.

## License

MIT
