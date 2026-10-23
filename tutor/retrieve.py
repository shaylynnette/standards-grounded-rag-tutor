"""Retrieval: BM25 over the standards (SQLite FTS5) plus a simple 'can I answer this?' check."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .store import connect

THRESHOLDS = Path(__file__).with_name("thresholds.json")

STOP = set("""a an and are as at be but by can could do does did for from has have how i if in into is it its
me my no not of on or our should so than that the their them then there these they this those to us was we
were what when where which who whom why will with would you your about any also kid kids learn learns learned
learning teach teaches taught teaching cover covers covered covering standard standards teks student students
expected expect grade grades class classroom lesson lessons topic topics tell show give find need needs want
looking using use used get gets make makes made one two three four five first second third fourth fifth
kindergarten kindergartener kindergarteners kindergartners graders grader""".split())

GRADE_WORDS = {"kindergarten": "K", "kindergartener": "K", "kindergarteners": "K", "kindergartners": "K",
               "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5"}


def detect_grade(question: str) -> str | None:
    q = question.lower()
    m = re.search(r"\bgrade\s*([1-5])\b", q) or re.search(r"\b([1-5])(?:st|nd|rd|th)\s+grade", q)
    if m:
        return m.group(1)
    m = re.search(r"\b(first|second|third|fourth|fifth)[\s-]*(?:grade|graders?)\b", q)
    if m:
        return GRADE_WORDS[m.group(1)]
    if re.search(r"\bkindergart", q):
        return "K"
    return None


def tokens(question: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+", question.lower())
    return [t for t in toks if t not in STOP and len(t) > 1 or t.isdigit()]


def stem(tok: str) -> str:
    """Deliberately simple suffix stripping, used only to measure query coverage."""
    for suf in ("ing", "ed", "es", "s"):
        if len(tok) > len(suf) + 2 and tok.endswith(suf):
            return tok[: -len(suf)]
    return tok


@dataclass
class Hit:
    id: str
    teks_code: str
    citation: str
    grade: str
    strand: str
    text: str
    strand_text: str
    source: str
    score: float      # higher is better (negated BM25)
    coverage: float   # share of query content words found in the passage
    vocab: float = 1.0  # share of query content words found anywhere in the standards


_VOCAB: set[str] | None = None


def corpus_vocab(con) -> set[str]:
    global _VOCAB
    if _VOCAB is None:
        _VOCAB = set()
        for r in con.execute("SELECT text, strand_text FROM standards"):
            _VOCAB |= {stem(w) for w in re.findall(r"[a-z0-9]+", (r[0] + " " + r[1]).lower())}
    return _VOCAB


def load_thresholds() -> dict:
    if THRESHOLDS.exists():
        return json.loads(THRESHOLDS.read_text())
    return {"min_coverage": 0.0, "min_score": 0.0, "min_vocab": 0.0}


def search(question: str, k: int = 5, db=None) -> tuple[list[Hit], dict]:
    con = db or connect()
    grade = detect_grade(question)
    toks = tokens(question)
    info = {"grade_filter": grade, "query_terms": toks}
    if not toks:
        return [], info
    match = " OR ".join(f'"{t}"' for t in dict.fromkeys(toks))
    sql = ("SELECT s.*, bm25(standards_fts, 4.0, 1.0) AS rank FROM standards_fts "
           "JOIN standards s ON s.rowid = standards_fts.rowid WHERE standards_fts MATCH ?")
    args: list = [match]
    if grade:
        sql += " AND s.grade = ?"
        args.append(grade)
    sql += " ORDER BY rank LIMIT ?"
    args.append(k)
    qstems = {stem(t) for t in toks}
    vocab = len(qstems & corpus_vocab(con)) / len(qstems)
    hits = []
    for r in con.execute(sql, args):
        words = {stem(w) for w in re.findall(r"[a-z0-9]+", (r["text"] + " " + r["strand_text"]).lower())}
        cov = len(qstems & words) / len(qstems)
        hits.append(Hit(r["id"], r["teks_code"], r["citation"], r["grade"], r["strand"], r["text"],
                        r["strand_text"], r["source"], -r["rank"], cov, vocab))
    return hits, info


def can_answer(hits: list[Hit], thresholds: dict | None = None) -> bool:
    t = thresholds or load_thresholds()
    return bool(hits) and (hits[0].coverage >= t["min_coverage"] and hits[0].score >= t["min_score"]
                              and hits[0].vocab >= t.get("min_vocab", 0.0))
