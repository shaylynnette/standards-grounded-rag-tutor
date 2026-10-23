"""Query normalization: understand how teachers actually type.

Grades ("fifth grade", "5th grade", "grade 5", "gr 5", "G5", "grade five", "kinder"), TEKS codes
("TEKS 5.3A", "5.3(A)", "5.3a") and small typing slips are turned into one canonical form before
retrieval. Grade phrases are rewritten into the exact form the retriever already handled, so the
set of query terms for old phrasings does not change. Nothing here calls a model.
"""
from __future__ import annotations

import re

NUM_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5"}
ORD_WORDS = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5"}

# "grade five", "gr. 5", "grd k", "grade kindergarten"
_GRADE_LABEL = re.compile(r"\b(?:grade|gr|grd)\.?\s*(k|kinder\w*|kindergart\w*|[1-5]|one|two|three|four|five)\b")
_G_SHORT = re.compile(r"\bg([1-5k])\b")
_ORD_DIGIT = re.compile(r"\b([1-5])(?:st|nd|rd|th)(?:[\s-]*(?:grade|graders?)\b)?")
_KINDER = re.compile(r"\bkinder\b")

# TEKS code: 5.3A  5.3(A)  5.3 (a)  k.2b  or, after the word TEKS, "5 3 a"
_CODE_DOT = re.compile(r"(?<![\w.])(?:teks\s*)?([k1-5])\.(\d{1,2})(?:\s*\(\s*([a-z])\s*\)|([a-z])\b)?(?![\w.]*\d)")
_CODE_TEKS_SPACED = re.compile(r"\bteks\s*:?\s*([k1-5])[\s\-]+(\d{1,2})(?:\s*\(\s*([a-z])\s*\)|\s+([a-z])\s*$)?")


def _grade_text(g: str) -> str:
    g = g.lower()
    if g.startswith("kinder") or g == "k":
        return "kindergarten"
    return "grade " + NUM_WORDS.get(g, g)


def normalize_grades(q: str) -> str:
    q = _GRADE_LABEL.sub(lambda m: _grade_text(m.group(1)), q)
    q = _G_SHORT.sub(lambda m: _grade_text(m.group(1)), q)
    q = _ORD_DIGIT.sub(lambda m: f"grade {m.group(1)}", q)
    q = _KINDER.sub("kindergarten", q)
    return q


def extract_code(q: str, other_words: int) -> tuple[tuple[str, int, str | None] | None, str]:
    """Find a TEKS code. A bare '5.3' is also a decimal, so a code needs a letter, the word TEKS, or
    to be the whole question. Returns ((grade, strand, letter|None), question with the code removed)."""
    m = _CODE_TEKS_SPACED.search(q)
    explicit = bool(m)
    if not m:
        m = _CODE_DOT.search(q)
    if not m:
        return None, q
    grade, strand, l1, l2 = m.group(1), int(m.group(2)), m.group(3), m.group(4)
    letter = (l1 or l2 or "").upper() or None
    has_prefix = explicit or m.group(0).startswith("teks")
    if not (letter or has_prefix or other_words == 0):
        return None, q
    return (grade.upper(), strand, letter), (q[:m.start()] + " " + q[m.end():])


def _edits1(a: str, b: str) -> bool:
    """True if a and b differ by exactly one insertion, deletion, substitution or adjacent swap."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])
    s, l = (a, b) if len(a) < len(b) else (b, a)
    i = 0
    while i < len(s) and s[i] == l[i]:
        i += 1
    return s[i:] == l[i + 1:]


def correct_spelling(tokens: list[str], words: set[str], stems_known) -> tuple[list[str], list[tuple[str, str]]]:
    """Fix a word that is not in the standards only when exactly one standards word is one edit away."""
    out, fixed = [], []
    for t in tokens:
        if len(t) >= 6 and t.isalpha() and not stems_known(t):
            cands = sorted(w for w in words if abs(len(w) - len(t)) <= 1 and w[0] == t[0] and _edits1(t, w))
            if len(cands) == 1:
                fixed.append((t, cands[0]))
                out.append(cands[0])
                continue
        out.append(t)
    return out, fixed
