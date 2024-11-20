import json
import re
import warnings
from difflib import SequenceMatcher
from itertools import combinations


def get_closest_substring(long: str, short: str) -> str:
    """
    Finds the closest substring to short string in longer one
    Args:
        long: str - longer string
        short: str - shorter string
    Returns:
        closest substring of longer
    """
    a, b = max(
        combinations(re.finditer("|".join(short.split()), long), 2),
        key=lambda c: SequenceMatcher(None, long[c[0].start() : c[1].end()], short).ratio(),
    )
    return long[a.start() : b.end()]


def get_passages_list(raw_passages: str) -> list[str]:
    """
    Formats LLM output to list of passages
    Args:
        raw_passages: string representing raw passages returned by llm
    Returns:
        list of parsed passages
    """
    match = re.search(r"\[(.*?)\]", raw_passages, re.DOTALL)

    if match:
        passages_content = match.group(1)
        try:
            return json.loads("[" + passages_content + "]")
        except (SyntaxError, ValueError):
            warnings.warn("Unable to evaluate the passages content. Check the format.", category=UserWarning)
            return []
    else:
        warnings.warn(message="No brackets found in the input string.", category=UserWarning)
        return []
