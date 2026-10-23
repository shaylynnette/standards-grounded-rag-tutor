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
    def test_per_grade_counts_regression(self):
        c = Counter(r["grade"] for r in RECS)
        self.assertEqual(dict(c), {"K": 36, "1": 50, "2": 50, "3": 53, "4": 53, "5": 46})

    def test_ids_unique(self):
        self.assertEqual(len({r["id"] for r in RECS}), len(RECS))

    def test_no_hyphen_join_artifacts(self):
        for r in RECS:
            # "two- and three-dimensional" is real text; "two- dimensional" is a line-break artifact
            self.assertIsNone(re.search(r"\w- (?!and\b|or\b)\w", r["text"]), r["id"])

    def test_citation_shape(self):
        for r in RECS:
            self.assertTrue(r["citation"].startswith("19 TAC §111."), r["id"])


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
        for q in ["What is the capital of Texas?", "Explain photosynthesis for fifth graders", ""]:
            self.assertFalse(ask(q).answered, q)

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
        no = respond("What is the capital of Texas?")
        self.assertFalse(no["answered"])
        self.assertEqual(no["matches"], [])
