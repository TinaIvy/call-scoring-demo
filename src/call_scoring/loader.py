"""Load call transcripts from a JSON file."""

import json
from pathlib import Path


def load_calls(path):
    """Read a JSON file of calls and return them as a list of dictionaries."""
    with open(Path(path), encoding="utf-8") as file:
        return json.load(file)
