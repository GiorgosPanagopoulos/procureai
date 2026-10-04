"""Deterministic guard against article citations missing from the retrieved context.

Two rounds of prompt rules (doc_qa v1.1, v1.2) did not stop the model from citing
articles from its own knowledge, e.g. "(π.χ. άρθρα 360-366 περί ΑΕΠΠ)" when no
chunk contains them. This guard runs on the model's answer before it is returned:
a citation stays only if every article number in it is cited as an article in the
context. Contract articles ("Άρθρο 4 της Σύμβασης") pass the same way, because the
contract chunks carry their own "Άρθρο N" headings.
"""

import re
from typing import List, Optional, Set, Tuple

import structlog

log = structlog.get_logger()

# άρθρο, άρθρου, άρθρα, άρθρων, άρθρ., in any case, with or without the accent.
_KEYWORD = r"[άα]ρθρ(?:ου|ων|ο|α|\.)"
# An article number, with an optional ordinal suffix ("4ο").
_NUM = r"\d+(?:ου|ο)?"
_RANGE_SEP = r"\s*[-–—]\s*"
_LIST_SEP = r"\s*(?:,|και|&)\s*"
_ITEM = rf"{_NUM}(?:{_RANGE_SEP}{_NUM})?"
_NUMBERS = rf"{_ITEM}(?:{_LIST_SEP}{_ITEM})*"

_CITATION = re.compile(
    r"(?P<prefix>(?:π\.\s?χ\.|βλ\.)\s*)?"
    r"(?P<det>\bσ?τ(?:ου|ων|ο|α)\s+)?"
    rf"(?P<kw>\b{_KEYWORD})\s*(?P<nums>{_NUMBERS})(?![\d/])"
    rf"(?P<par>\s*παρ\.\s*\d+(?:{_LIST_SEP}\d+)*)?",
    re.IGNORECASE,
)

# Neuter adjective agreeing with each form of "άρθρο", so that "του άρθρου 72"
# becomes "του σχετικού άρθρου" and the sentence keeps its grammar.
_ADJECTIVE = {"ου": "σχετικού", "ων": "σχετικών", "ο": "σχετικό", "α": "σχετικά"}

# Ranges wider than this are checked by their endpoints only.
_MAX_RANGE = 500


def _article_numbers(nums: str) -> List[int]:
    """Every article number in a citation's number list, ranges expanded."""
    numbers: List[int] = []
    for item in re.split(_LIST_SEP, nums.strip()):
        bounds = [int(n) for n in re.findall(r"\d+", item)]
        if len(bounds) == 2 and 0 <= bounds[1] - bounds[0] <= _MAX_RANGE:
            numbers.extend(range(bounds[0], bounds[1] + 1))
        else:
            numbers.extend(bounds)
    return numbers


def _context_articles(context: str) -> Set[int]:
    return {n for m in _CITATION.finditer(context) for n in _article_numbers(m["nums"])}


def _enclosing_parenthetical(text: str, start: int, end: int) -> Optional[Tuple[int, int]]:
    """Span of "(...)" when the citation opens it, e.g. "(π.χ. άρθρα 360-366 περί ΑΕΠΠ)"."""
    opening = re.search(r"\s*\(\s*$", text[:start])
    if not opening:
        return None
    close = text.find(")", end)
    if close == -1 or re.search(r"[()\n]", text[end:close]) or close - end > 80:
        return None
    return opening.start(), close + 1


def _join(left: str, right: str) -> str:
    """Glue the text around a removed citation without stray spaces or commas."""
    left, right = left.rstrip(" \t"), right.lstrip(" \t")
    if left.endswith(",") and right[:1] in tuple(",.;:!?)"):
        left = left[:-1]
    elif right[:1] in tuple(",.;:") and (not left or left[-1] in "\n(.;:!?"):
        right = right[1:].lstrip(" \t")
    if not left or not right or left[-1] in "\n(" or right[0] in ",.;:!?)\n":
        return left + right
    return f"{left} {right}"


def strip_unsupported_citations(answer: str, context: str) -> str:
    """Remove article citations whose numbers are not all cited in the context."""
    supported = _context_articles(context)
    # (start, end, replacement); a replacement of None removes the span.
    edits: List[Tuple[int, int, Optional[str]]] = []
    for m in _CITATION.finditer(answer):
        numbers = _article_numbers(m["nums"])
        missing = sorted(set(numbers) - supported)
        if not missing:
            continue
        log.info(
            "unsupported_article_citation_removed",
            citation=m.group(0).strip(),
            articles=sorted(set(numbers)),
            missing=missing,
        )
        if edits and m.start() < edits[-1][1]:
            continue  # already inside a removed parenthetical
        span = _enclosing_parenthetical(answer, m.start(), m.end())
        ending = next((e for e in _ADJECTIVE if m["kw"].lower().endswith(e)), None)
        if span:
            edits.append((span[0], span[1], None))
        elif m["det"] and not m["prefix"] and ending in _ADJECTIVE:
            edits.append((m.start("kw"), m.end(), f"{_ADJECTIVE[ending]} {m['kw']}"))
        else:
            edits.append((m.start(), m.end(), None))

    for start, end, replacement in reversed(edits):
        if replacement is None:
            answer = _join(answer[:start], answer[end:])
        else:
            answer = answer[:start] + replacement + answer[end:]
    return answer
