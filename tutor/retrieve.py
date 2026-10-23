"""Retrieval: BM25 over the standards (SQLite FTS5) plus a simple 'can I answer this?' check."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .normalize import correct_spelling, extract_code, normalize_grades
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


SUBJECT_WORDS = [
    ("MATH", r"\bmath(?:ematics)?\b"),
    ("ELAR", r"\b(?:ela|elar|reading|writing|english language arts|phonics|spelling|literacy)\b"),
    ("SCI", r"\bscience\b"),
    ("SS", r"\bsocial studies\b"),
    ("HEALTH", r"\bhealth\b"),
    ("PE", r"\b(?:physical education|p\.?e\.?)\b"),
    ("ART", r"\bart\b"),
    ("MUSIC", r"\bmusic\b"),
    ("THEATRE", r"\b(?:theatre|theater|drama)\b"),
    ("TECH", r"\b(?:technology applications|computer science|coding|programming)\b"),
]


def detect_subject(question: str) -> tuple[str | None, str]:
    """Return (subject, question with the matched subject words removed). One subject only: if the
    question names several, no filter is applied."""
    q = question.lower()
    found = [(code, re.search(rx, q)) for code, rx in SUBJECT_WORDS]
    found = [(c, m) for c, m in found if m]
    if len(found) != 1:
        return None, question
    code, m = found[0]
    return code, (q[:m.start()] + " " + q[m.end():])


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
    subject: str
    subject_name: str
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
_WORDS: set[str] | None = None


def corpus_vocab(con) -> set[str]:
    global _VOCAB, _WORDS
    if _VOCAB is None:
        _VOCAB, _WORDS = set(), set()
        for r in con.execute("SELECT text, strand_text FROM standards"):
            ws = re.findall(r"[a-z0-9]+", (r[0] + " " + r[1]).lower())
            _WORDS |= set(ws)
            _VOCAB |= {stem(w) for w in ws}
    return _VOCAB


def corpus_words(con) -> set[str]:
    corpus_vocab(con)
    return _WORDS or set()


def load_thresholds() -> dict:
    if THRESHOLDS.exists():
        return json.loads(THRESHOLDS.read_text())
    return {"min_coverage": 0.0, "min_score": 0.0, "min_vocab": 0.0}


def _code_hits(con, code, subject, k) -> list[Hit]:
    grade, strand, letter = code
    sql = "SELECT * FROM standards WHERE grade = ? AND strand_number = ?"
    args: list = [grade, strand]
    if subject:
        sql += " AND subject = ?"
        args.append(subject)
    out = []
    for r in con.execute(sql + " ORDER BY rowid", args):
        m = re.search(r"\s[K1-5]\.(\d+)([A-Z]?)$", r["teks_code"])
        if m and (letter is None or m.group(2) == letter):
            out.append(Hit(r["id"], r["subject"], r["subject_name"], r["teks_code"], r["citation"], r["grade"], r["strand"],
                           r["text"], r["strand_text"], r["source"], 100.0, 1.0, 1.0))
    return out[:k]


def search(question: str, k: int = 5, db=None) -> tuple[list[Hit], dict]:
    con = db or connect()
    q = normalize_grades(question.lower())
    info: dict = {"grade_filter": None, "subject_filter": None, "query_terms": [], "code": None, "corrected": []}
    other = sum(1 for t in tokens(q) if t.isalpha())
    code, q_nocode = extract_code(q, other)
    if code:
        subj, _ = detect_subject(q_nocode)
        hits = _code_hits(con, code, subj, k)
        if hits:
            info.update(grade_filter=code[0], subject_filter=subj, code=f"{code[0]}.{code[1]}{code[2] or ''}")
            return hits, info
        q = q_nocode
    grade = detect_grade(q)
    subject, rest = detect_subject(q)
    toks = tokens(rest)
    vocab_stems = corpus_vocab(con)
    toks, fixed = correct_spelling(toks, corpus_words(con), lambda t: stem(t) in vocab_stems)
    info.update(grade_filter=grade, subject_filter=subject, query_terms=toks, corrected=fixed)
    if not toks:
        return [], info
    match = " OR ".join(f'"{t}"' for t in dict.fromkeys(toks))
    sql = ("SELECT s.*, bm25(standards_fts, 4.0, 1.0) AS rank FROM standards_fts "
           "JOIN standards s ON s.rowid = standards_fts.rowid WHERE standards_fts MATCH ?")
    args: list = [match]
    if grade:
        sql += " AND s.grade = ?"
        args.append(grade)
    if subject:
        sql += " AND s.subject = ?"
        args.append(subject)
    sql += " ORDER BY rank LIMIT ?"
    args.append(k)
    qstems = {stem(t) for t in toks}
    vocab = len(qstems & vocab_stems) / len(qstems)
    hits = []
    for r in con.execute(sql, args):
        words = {stem(w) for w in re.findall(r"[a-z0-9]+", (r["text"] + " " + r["strand_text"]).lower())}
        cov = len(qstems & words) / len(qstems)
        hits.append(Hit(r["id"], r["subject"], r["subject_name"], r["teks_code"], r["citation"], r["grade"], r["strand"], r["text"],
                        r["strand_text"], r["source"], -r["rank"], cov, vocab))
    return hits, info


def can_answer(hits: list[Hit], thresholds: dict | None = None) -> bool:
    t = thresholds or load_thresholds()
    return bool(hits) and (hits[0].coverage >= t["min_coverage"] and hits[0].score >= t["min_score"]
                              and hits[0].vocab >= t.get("min_vocab", 0.0))
