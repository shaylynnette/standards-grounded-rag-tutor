"""Parse the TEA grade-level TEKS compilations (K-5, all subjects, revised June 2024) into one record
per student expectation, keeping the wording exactly as published.

Input: text layer of each TEA PDF (pdftotext -layout). Only the "Knowledge and skills" subsection of
each subject section is parsed; introductions are not standards. Languages Other Than English (a
single shared section, not a K-5 grade standard) is skipped.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ANY_SECTION_RE = re.compile(r"^\s*§\d{3}\.\d+\.\s+.+,\s+Adopted \d{4}\.")
SECTION_RE = re.compile(r"^\s*§(\d{3})\.(\d+)\.\s+(.+?),\s+(Kindergarten|Grade \d),\s+Adopted (\d{4})\.")
KS_RE = re.compile(r"^\s*\(([a-z])\)\s+Knowledge and skills\.")
TOP_RE = re.compile(r"^\s*\(([a-z])\)\s")
STRAND_RE = re.compile(r"^\s*\((\d{1,2})\)\s+(\S.*)$")
ITEM_RE = re.compile(r"^\s*\(([A-Z])\)\s+(\S.*)$")
SUB_RE = re.compile(r"^\s*\((i{1,3}|iv|v|vi{0,3}|ix|x)\)\s+(\S.*)$")
NOISE = (re.compile(r"^\f?\s*revised [A-Z][a-z]+ \d{4}\s*$"), re.compile(r"^\f?\s*\d{1,3}\s*$"))
STEM_END = "The student is expected to:"
CHAPTER_SUBJECT = {"110": ("ELAR", "English Language Arts and Reading"), "111": ("MATH", "Mathematics"),
                   "112": ("SCI", "Science"), "113": ("SS", "Social Studies"), "115": ("HEALTH", "Health Education"),
                   "116": ("PE", "Physical Education"), "126": ("TECH", "Technology Applications")}
ARTS = {"Art": "ART", "Music": "MUSIC", "Theatre": "THEATRE"}
SOURCE_URL = "https://tea.texas.gov/academics/curriculum-standards/teks-review/texas-essential-knowledge-and-skills"


@dataclass
class Standard:
    id: str
    subject: str       # ELAR, MATH, SCI, SS, HEALTH, PE, ART, MUSIC, THEATRE, TECH
    subject_name: str
    teks_code: str     # e.g. "SCI 3.2B"
    citation: str      # e.g. "19 TAC §112.5(b)(2)(B)"
    grade: str
    section: str
    adopted: str
    strand_number: int
    strand: str
    strand_text: str
    text: str
    source: str = SOURCE_URL


def _join(parts):
    out = ""
    for part in (p.strip() for p in parts):
        if not part:
            continue
        if out and re.search(r"[A-Za-z]-$", out) and re.match(r"[a-z]", part) and not re.match(r"(and|or)\b", part):
            out += part
        else:
            out += (" " if out else "") + part
    return re.sub(r"\s+", " ", out).strip()


def parse(text: str, issues: list[str] | None = None) -> list[Standard]:
    issues = issues if issues is not None else []
    out: list[Standard] = []
    sec = None            # (chapter, num, subject_key, subject_name, grade, adopted)
    ks_letter = None
    in_ks = False
    strand_no = None
    strand_parts: list[str] = []
    items: list[list] = []          # [letter, [parts]]
    mode = None                      # "strand" | "item"

    def flush():
        nonlocal strand_no, strand_parts, items, mode
        if strand_no is None or sec is None:
            strand_no, strand_parts, items, mode = None, [], [], None
            return
        chapter, num, subj, sname, grade, adopted = sec
        section = f"{chapter}.{num}"
        full = _join(strand_parts)
        name = full.split(". ", 1)[0].rstrip(".")
        base = dict(subject=subj, subject_name=sname, grade=grade, section=section, adopted=adopted,
                    strand_number=strand_no, strand=name)
        if items:
            letters = [l for l, _ in items]
            expect = [chr(ord("A") + i) for i in range(len(items))]
            if letters != expect:
                issues.append(f"{section} strand {strand_no}: item letters {letters}")
            stem = full.split(STEM_END)[0].strip() + (" " + STEM_END if STEM_END in full else "")
            for letter, parts in items:
                out.append(Standard(id=f"{section}.{ks_letter}.{strand_no}.{letter}",
                                    teks_code=f"{subj} {grade}.{strand_no}{letter}",
                                    citation=f"19 TAC §{section}({ks_letter})({strand_no})({letter})",
                                    strand_text=stem, text=_join(parts), **base))
        else:
            out.append(Standard(id=f"{section}.{ks_letter}.{strand_no}", teks_code=f"{subj} {grade}.{strand_no}",
                                citation=f"19 TAC §{section}({ks_letter})({strand_no})",
                                strand_text=full, text=full, **base))
        strand_no, strand_parts, items, mode = None, [], [], None

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip() or any(p.match(line) for p in NOISE):
            continue
        if ANY_SECTION_RE.match(line) and not SECTION_RE.match(line):   # e.g. Languages Other Than English
            flush()
            sec, in_ks = None, False
            continue
        m = SECTION_RE.match(line)
        if m:
            flush()
            chapter, num, sname, gtxt, adopted = m.groups()
            grade = "K" if gtxt == "Kindergarten" else gtxt.split()[1]
            if chapter == "117":
                subj = ARTS.get(sname)
            else:
                subj = CHAPTER_SUBJECT.get(chapter, (None,))[0]
            if subj is None:
                sec, in_ks = None, False
                continue
            sec = (chapter, num, subj, sname if chapter == "117" else CHAPTER_SUBJECT[chapter][1], grade, adopted)
            in_ks = False
            continue
        if sec is None:
            continue
        if line.lstrip().startswith("Source:"):
            flush()
            in_ks = False
            continue
        k = KS_RE.match(line)
        if k:
            ks_letter, in_ks = k.group(1), True
            continue
        if not in_ks:
            continue
        sm = STRAND_RE.match(line)
        im = ITEM_RE.match(line)
        bm = SUB_RE.match(line)
        if TOP_RE.match(line) and not im and not bm and not sm:   # next lettered subsection, e.g. (c)
            flush()
            in_ks = False
            continue
        if sm and (strand_no is None or int(sm.group(1)) == strand_no + 1):
            flush()
            strand_no = int(sm.group(1))
            strand_parts, items, mode = [sm.group(2)], [], "strand"
        elif im and strand_no is not None and (
                (not items and im.group(1) == "A") or (items and ord(im.group(1)) == ord(items[-1][0]) + 1)):
            items.append([im.group(1), [im.group(2)]])
            mode = "item"
        elif bm and mode == "item":
            items[-1][1].append(f"({bm.group(1)}) {bm.group(2)}")
        elif mode == "strand":
            strand_parts.append(line)
        elif mode == "item":
            items[-1][1].append(line)
    flush()
    return out


def main(paths: list[str], out: str) -> None:
    allr, issues = [], []
    for p in paths:
        allr += parse(Path(p).read_text(encoding="utf-8"), issues)
    Path(out).write_text("\n".join(json.dumps(asdict(r), ensure_ascii=False) for r in allr) + "\n", encoding="utf-8")
    print(f"{len(allr)} standards written to {out}; {len(issues)} structure issues")
    for i in issues:
        print("  ", i)


if __name__ == "__main__":
    main(sys.argv[2:], sys.argv[1])
