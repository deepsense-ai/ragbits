import re
from difflib import SequenceMatcher
from itertools import combinations


def get_closest_substring(long, short):
    a, b = max(
        combinations(re.finditer("|".join(short.split()), long), 2),
        key=lambda c: SequenceMatcher(None, long[c[0].start() : c[1].end()], short).ratio(),
    )
    return long[a.start() : b.end()]


def get_passages_list(raw_passages: str) -> list[str]:
    passages = raw_passages.split("[")[1]
    passages = passages.split("]")[0]
    return eval("[" + passages + "]")
