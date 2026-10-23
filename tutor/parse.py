"""Parse the official TEKS mathematics text (19 TAC Chapter 111, Subchapter A, Elementary)
into one record per student expectation, keeping the wording exactly as published.

Input is the text layer of the TEA PDF (pdftotext -layout). Only the "(b) Knowledge and
skills" part of each grade section is parsed; introductions are not standards.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

SECTION_RE = re.compile(r"^§111\.(\d+)\.\s+(Kindergarten|Grade \d),\s+Adopted 2012\.")
STRAND_RE = re.compile(r"^\s*\((\d{1,2})\)\s+(\S.*)$")
ITEM_RE = re.compile(r"^\s*\(([A-Z])\)\s+(\S.*)$")
PAGE_NOISE = (
    re.compile(r"^\s*December 2014 Update\s+Page \d+\s*$"),
    re.compile(r"^\s*Page \d+\s+December 2014 Update\s*$"),
    re.compile(r"^\f?§111\.A\.\s+Elementary\s*$"),
    re.compile(r"^\f?Elementary\s+§111\.A\.\s*$"),
)
STEM_END = "The student is expected to:"
SOURCE_URL = "https://tea.texas.gov/laws-and-rules/texas-administrative-code/19-tac-chapter-111"


@dataclass
class Standard:
    id: str            # e.g. "111.7.b.2.C"
    teks_code: str     # e.g. "5.2C"
    citation: str      # e.g. "19 TAC §111.7(b)(2)(C)"
    grade: str         # "K", "1" ... "5"
    section: str       # "111.7"
    strand_number: int
    strand: str        # e.g. "Number and operations"
    strand_text: str   # full strand sentence(s) before "The student is expected to:"
    text: str          # the student expectation, verbatim
    source: str = SOURCE_URL


def _clean(lines):
    for line in lines:
        line = line.rstrip("\n")
        if any(p.match(line) for p in PAGE_NOISE):
            continue
        if not line.strip():
            continue
        yield line


def _join(parts):
    """Join wrapped lines. A hyphen at a line end followed by a lowercase word that is
    not a conjunction is a broken compound ("two-" + "dimensional"), so no space is added;
    "two-" + "and" stays "two- and" as the published text has it."""
    out = ""
    for part in (p.strip() for p in parts):
        if not part:
            continue
        if out and re.search(r"[A-Za-z]-$", out) and re.match(r"[a-z]", part) \
                and not re.match(r"(and|or)\b", part):
            out += part
        else:
            out += (" " if out else "") + part
    return re.sub(r"\s+", " ", out).strip()


def parse(text: str) -> list[Standard]:
    lines = list(_clean(text.splitlines()))
    out: list[Standard] = []
    section = grade = None
    in_b = False
    strand_no = None
    strand_parts: list[str] = []
    items: list[tuple[str, list[str]]] = []
    cur: list[str] | None = None

    def flush_strand():
        nonlocal strand_no, strand_parts, items, cur
        if strand_no is None:
            return
        full = _join(strand_parts)
        name = full.split(". ", 1)[0].rstrip(".")
        code_grade = "K" if grade == "Kindergarten" else grade.split()[1]
        base = dict(grade=code_grade, section=section, strand_number=strand_no, strand=name)
        if items:
            stem = full.split(STEM_END)[0].strip() + (" " + STEM_END if STEM_END in full else "")
            for letter, parts in items:
                out.append(Standard(
                    id=f"{section}.b.{strand_no}.{letter}",
                    teks_code=f"{code_grade}.{strand_no}{letter}",
                    citation=f"19 TAC §{section}(b)({strand_no})({letter})",
                    strand_text=stem, text=_join(parts), **base))
        else:  # the strand statement itself is the expectation
            out.append(Standard(
                id=f"{section}.b.{strand_no}",
                teks_code=f"{code_grade}.{strand_no}",
                citation=f"19 TAC §{section}(b)({strand_no})",
                strand_text=full, text=full, **base))
        strand_no, strand_parts, items, cur = None, [], [], None

    for line in lines:
        m = SECTION_RE.match(line)
        if m:
            flush_strand()
            section, grade, in_b = f"111.{m.group(1)}", m.group(2), False
            continue
        if line.startswith("Source:"):
            flush_strand()
            in_b = False
            continue
        if re.match(r"^\(b\)\s+Knowledge and skills\.", line):
            in_b = True
            continue
        if not in_b:
            continue
        if re.match(r"^\([a-z]\)\s", line):  # next top-level subsection, e.g. (c)
            flush_strand()
            in_b = False
            continue
        im = ITEM_RE.match(line)
        if im and strand_no is not None:
            cur = [im.group(2)]
            items.append((im.group(1), cur))
            continue
        sm = STRAND_RE.match(line)
        if sm and not ITEM_RE.match(line):
            flush_strand()
            strand_no, strand_parts = int(sm.group(1)), [sm.group(2)]
            cur = None
            continue
        if cur is not None:
            cur.append(line)
        elif strand_no is not None:
            strand_parts.append(line)
    flush_strand()
    return out


def main(src: str, dst: str) -> int:
    standards = parse(Path(src).read_text(encoding="utf-8"))
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        for s in standards:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")
    return len(standards)


if __name__ == "__main__":
    import sys
    n = main(sys.argv[1], sys.argv[2])
    print(f"wrote {n} standards to {sys.argv[2]}")
