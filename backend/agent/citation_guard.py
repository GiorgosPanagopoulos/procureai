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
    # The article may sit outside emphasis: "το **Άρθρο 999**".
    r"(?:(?P<det>\bσ?τ(?:ου|ων|ο|α)\s+)(?P<emph>\*{1,3}|_{1,3})?)?"
    rf"(?P<kw>\b{_KEYWORD})\s*(?P<nums>{_NUMBERS})(?![\d/])"
    rf"(?P<par>\s*παρ\.\s*\d+(?:{_LIST_SEP}\d+)*)?",
    re.IGNORECASE,
)

# Neuter adjective agreeing with each form of "άρθρο", so that "του άρθρου 72"
# becomes "του σχετικού άρθρου" and the sentence keeps its grammar.
_ADJECTIVE = {"ου": "σχετικού", "ων": "σχετικών", "ο": "σχετικό", "α": "σχετικά"}

# Ranges wider than this are checked by their endpoints only.
_MAX_RANGE = 500

# A markdown emphasis run ("*", "**", "***", "_"...) directly touching a removed
# citation. Flanking as in CommonMark: an opener is preceded by whitespace, the start
# of the text or an opening bracket/quote; a closer is followed by whitespace, the end
# or punctuation. So "**a** Άρθρο 999 **b**" is not an empty pair, and a "* " list
# bullet is not an opener.
_EMPHASIS_BEFORE = re.compile(r"(?:^|(?<=[\s(\[«\"']))(?P<m>\*{1,3}|_{1,3})$")
_EMPHASIS_AFTER = re.compile(r"^(?P<m>\*{1,3}|_{1,3})(?=$|[\s.,;:!?)\]»\"'])")
# A list item marker with nothing after it yet: "- ", "* ", "1. ".
_LIST_ITEM = re.compile(r"(?:^|\n)[ \t]*(?:[-*+]|\d+[.)])[ \t]*$")
# Separators left dangling inside the emphasis once the citation next to them is gone.
_LEADING_JOINER = re.compile(r"^(?:[,.;:]|και\b|&)[ \t]*")
_TRAILING_JOINER = re.compile(r"[ \t]*(?:[,;:]|(?<!\S)(?:και|&))$")


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
    opening = re.search(r"\s*\(\s*(?:\*{1,3}|_{1,3})?\s*$", text[:start])
    if not opening:
        return None
    close = text.find(")", end)
    if close == -1 or re.search(r"[()\n]", text[end:close]) or close - end > 80:
        return None
    return opening.start(), close + 1


def _join(left: str, right: str) -> str:
    """Glue the text around a removed citation without stray spaces or commas."""
    if _LIST_ITEM.search(left):
        # "* Άρθρο 999: text" -> "* text", not "*: text".
        left = left.rstrip(" \t")
        right = re.sub(r"^[ \t]*[,.;:]?[ \t]*", "", right, count=1)
        return f"{left} {right}" if right and right[0] != "\n" else left + right
    left, right = left.rstrip(" \t"), right.lstrip(" \t")
    if left.endswith(",") and right[:1] in tuple(",.;:!?)"):
        left = left[:-1]
    elif right[:1] in tuple(",.;:") and (not left or left[-1] in "\n(.;:!?"):
        right = right[1:].lstrip(" \t")
    if not left or not right or left[-1] in "\n(" or right[0] in ",.;:!?)\n":
        return left + right
    return f"{left} {right}"


def _cut(left: str, right: str) -> str:
    """Join around a removed citation without leaving empty or broken emphasis."""
    before = _EMPHASIS_BEFORE.search(left)
    after = _EMPHASIS_AFTER.match(right)
    if before and after and before["m"] == after["m"]:
        # "**Άρθρο 999**": the citation was all of the emphasis, drop the pair.
        return _join(left[: before.start()], right[after.end() :])
    if before:
        # "**Άρθρο 999 του Ν. 4412/2016**": keep the opener glued to what remains.
        inner = _LEADING_JOINER.sub("", right.lstrip(" \t"), count=1).lstrip(" \t")
        return _join(left[: before.start()], before["m"] + inner)
    if after:
        # "**ο κανόνας, Άρθρο 999**": keep the closer glued to what precedes it.
        inner = _TRAILING_JOINER.sub("", left.rstrip(" \t"), count=1)
        return _join(inner + after["m"], right[after.end() :])
    return _join(left, right)


def strip_unsupported_citations(answer: str, context: str) -> str:
    """Remove article citations whose numbers are not all cited in the context."""
    supported = _context_articles(context)
    # (start, end, replacement, opener); a replacement of None removes the span but
    # keeps an emphasis opener it swallowed ("το **Άρθρο 999**" -> "**"), so that
    # _cut sees the marker and drops the emphasis pair as a whole.
    edits: List[Tuple[int, int, Optional[str], str]] = []
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
            edits.append((span[0], span[1], None, ""))
        elif m["det"] and not m["prefix"] and ending in _ADJECTIVE:
            edits.append((m.start("kw"), m.end(), f"{_ADJECTIVE[ending]} {m['kw']}", ""))
        else:
            edits.append((m.start(), m.end(), None, m["emph"] or ""))

    for start, end, replacement, opener in reversed(edits):
        if replacement is None:
            answer = _cut(answer[:start] + opener, answer[end:])
        else:
            answer = answer[:start] + replacement + answer[end:]
    return answer
