"""Answer step. The default generator is extractive: it quotes the retrieved standard and cites it,
so every sentence is grounded by construction. A language-model generator can be plugged in
through the Generator interface; it must receive only the retrieved passages."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from .retrieve import Hit, can_answer, search

DECLINE = ("I can't find that in the Texas elementary standards (kindergarten to grade 5) that I have. "
           "Try naming a grade and a topic, for example: \"fifth grade rounding decimals\" or \"third grade science energy\".")


class Generator(Protocol):
    def generate(self, question: str, passages: list[Hit]) -> str: ...


class ExtractiveGenerator:
    def generate(self, question: str, passages: list[Hit]) -> str:
        top = passages[0]
        grade = "Kindergarten" if top.grade == "K" else f"Grade {top.grade}"
        body = re.sub(r"[;,]?\s+(and|or)$", "", top.text.rstrip(";.")).rstrip(";.") if top.text != top.strand_text else top.text
        lines = [f"{grade} {top.subject_name}, {top.teks_code} ({top.citation}): the student is expected to {body}."
                 if top.text != top.strand_text else f"{grade} {top.subject_name}, {top.teks_code} ({top.citation}): {body}"]
        for h in [p for p in passages[1:] if p.subject == top.subject][:2]:
            lines.append(f"Related: {h.teks_code} ({h.citation})")
        return "\n".join(lines)


@dataclass
class Result:
    question: str
    answered: bool
    answer: str
    citations: list[str] = field(default_factory=list)
    hits: list[Hit] = field(default_factory=list)
    info: dict = field(default_factory=dict)


def ask(question: str, generator: Generator | None = None, k: int = 5, db=None) -> Result:
    hits, info = search(question, k=k, db=db)
    if not can_answer(hits):
        return Result(question, False, DECLINE, [], hits, info)
    gen = generator or ExtractiveGenerator()
    return Result(question, True, gen.generate(question, hits), [h.citation for h in hits[:3]], hits, info)
