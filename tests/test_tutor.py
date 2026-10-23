import json
import re
import unittest
from collections import Counter
from pathlib import Path

from tutor.answer import ask
from tutor.store import DEFAULT_JSONL

ROOT = Path(__file__).resolve().parent.parent
RECS = [json.loads(l) for l in DEFAULT_JSONL.read_text(encoding="utf-8").splitlines()]
CODES = {r["teks_code"] for r in RECS}


class ParseTests(unittest.TestCase):
    def test_counts_regression(self):
        self.assertEqual(len(RECS), 2259)
        c = Counter(r["subject"] for r in RECS)
        self.assertEqual(dict(c), {"ELAR": 369, "MATH": 288, "SCI": 258, "SS": 331, "HEALTH": 297,
                                   "PE": 247, "ART": 75, "MUSIC": 133, "THEATRE": 112, "TECH": 149})
        g = Counter(r["grade"] for r in RECS if r["subject"] == "MATH")
        self.assertEqual(dict(g), {"K": 36, "1": 50, "2": 50, "3": 53, "4": 53, "5": 46})

    def test_every_subject_has_every_grade(self):
        pairs = {(r["subject"], r["grade"]) for r in RECS}
        for subj in {r["subject"] for r in RECS}:
            for gr in ["K", "1", "2", "3", "4", "5"]:
                self.assertIn((subj, gr), pairs)

    def test_no_section_header_leaked_into_text(self):
        for r in RECS:
            self.assertIsNone(re.search(r"§\d{3}\.\d+\.|revised [A-Z][a-z]+ \d{4}|Adopted \d{4}", r["text"]), r["id"])

    def test_ids_unique(self):
        self.assertEqual(len({r["id"] for r in RECS}), len(RECS))

    def test_no_hyphen_join_artifacts(self):
        for r in RECS:
            # "two- and three-dimensional" is real text; "two- dimensional" is a line-break artifact
            self.assertIsNone(re.search(r"\w- (?!and\b|or\b)\w", r["text"]), r["id"])

    def test_citation_shape(self):
        for r in RECS:
            self.assertRegex(r["citation"], r"^19 TAC §1\d\d\.\d+\([a-z]\)\(\d+\)", r["id"])


class GoldenTests(unittest.TestCase):
    def test_expected_codes_exist(self):
        for l in (ROOT / "eval" / "golden.jsonl").read_text().splitlines():
            g = json.loads(l)
            for c in g["expected"] or []:
                self.assertIn(c, CODES, g["id"])


class BehaviourTests(unittest.TestCase):
    def test_answers_with_citation(self):
        r = ask("fifth grade volume of a rectangular prism")
        self.assertTrue(r.answered)
        self.assertTrue(r.citations)

    def test_declines_off_topic(self):
        for q in ["Explain photosynthesis for fifth graders", "How do I bake a chocolate cake?", ""]:
            self.assertFalse(ask(q).answered, q)

    @unittest.expectedFailure
    def test_known_limitation_trivia_sharing_words_with_a_standard(self):
        # Documented weakness: keyword retrieval cannot tell a trivia question from a standards question
        # when the words overlap a standard ("state capital" appears in SS 2.4B). Embeddings plus a
        # relevance check are the planned fix; this test starts failing the day that works.
        self.assertFalse(ask("What is the capital of Texas?").answered)

    def test_grade_filter(self):
        r = ask("third grade equivalent fractions")
        self.assertTrue(all(h.grade == "3" for h in r.hits))


if __name__ == "__main__":
    unittest.main()


class ApiTests(unittest.TestCase):
    def test_respond_shapes(self):
        from tutor.api import respond
        ok = respond("fourth grade rounding whole numbers")
        self.assertTrue(ok["answered"] and ok["citations"] and ok["matches"])
        no = respond("Explain photosynthesis for fifth graders")
        self.assertFalse(no["answered"])
        self.assertEqual(no["matches"], [])
