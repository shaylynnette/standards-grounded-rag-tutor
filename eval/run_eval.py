"""Evaluate retrieval and the answer/decline decision against the golden set.

Usage:
  python -m eval.run_eval                 # report using the saved thresholds
  python -m eval.run_eval --calibrate     # tune decline thresholds on the DEV split only, then report

Honesty rule: thresholds are tuned on 'dev' questions and judged on the held-out 'test' questions.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from tutor.retrieve import THRESHOLDS, can_answer, search
from tutor.store import connect

GOLDEN = Path(__file__).with_name("golden.jsonl")
RESULTS = Path(__file__).with_name("results.md")


def load() -> list[dict]:
    return [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]


def run(rows: list[dict], thresholds: dict, k: int = 5):
    con = connect()
    out = []
    for r in rows:
        hits, _ = search(r["question"], k=k, db=con)
        codes = [h.teks_code for h in hits]
        answered = can_answer(hits, thresholds)
        rank = None
        if r["expected"]:
            for i, c in enumerate(codes, 1):
                if c in r["expected"]:
                    rank = i
                    break
        out.append({**r, "codes": codes, "answered": answered, "rank": rank,
                    "top_score": hits[0].score if hits else 0.0,
                    "top_cov": hits[0].coverage if hits else 0.0,
                    "top_vocab": hits[0].vocab if hits else 0.0})
    return out


def metrics(res: list[dict]) -> dict:
    ans = [r for r in res if r["expected"]]
    no = [r for r in res if not r["expected"]]
    n = len(ans) or 1
    return {
        "answerable": len(ans), "unanswerable": len(no),
        "hit@1": sum(1 for r in ans if r["rank"] == 1) / n,
        "hit@3": sum(1 for r in ans if r["rank"] and r["rank"] <= 3) / n,
        "hit@5": sum(1 for r in ans if r["rank"] and r["rank"] <= 5) / n,
        "mrr": sum(1 / r["rank"] for r in ans if r["rank"]) / n,
        "correct_answer_rate": sum(1 for r in ans if r["answered"] and r["rank"] == 1) / n,
        "false_decline_rate": sum(1 for r in ans if not r["answered"]) / n,
        "correct_decline_rate": (sum(1 for r in no if not r["answered"]) / len(no)) if no else float("nan"),
    }


def calibrate(dev: list[dict]) -> dict:
    """Pick the thresholds that maximise dev 'correct answer' + 'correct decline'; tie-break toward lower cutoffs."""
    base = run(dev, {"min_coverage": 0.0, "min_score": 0.0, "min_vocab": 0.0})
    best = None
    covs = [round(x * 0.05, 2) for x in range(0, 21)]
    scores = sorted({round(r["top_score"], 3) for r in base} | {0.0})
    vocs = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    for c, s, v in itertools.product(covs, scores, vocs):
        ok = 0
        for r in base:
            ans = r["top_cov"] >= c and r["top_score"] >= s and r["top_vocab"] >= v
            if r["expected"]:
                ok += 1 if (ans and r["rank"] == 1) else 0
            else:
                ok += 1 if not ans else 0
        key = (ok, -c, -s, -v)
        if best is None or key > best[0]:
            best = (key, {"min_coverage": c, "min_score": s, "min_vocab": v})
    return best[1]


def fmt(m: dict) -> str:
    return (f"hit@1 {m['hit@1']:.0%} | hit@3 {m['hit@3']:.0%} | hit@5 {m['hit@5']:.0%} | MRR {m['mrr']:.2f} | "
            f"correct answer {m['correct_answer_rate']:.0%} | false decline {m['false_decline_rate']:.0%} | "
            f"correct decline {m['correct_decline_rate']:.0%}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    args = ap.parse_args()
    rows = load()
    dev = [r for r in rows if r["split"] == "dev"]
    test = [r for r in rows if r["split"] == "test"]
    if args.calibrate:
        th = calibrate(dev)
        THRESHOLDS.write_text(json.dumps(th, indent=2) + "\n")
    th = json.loads(THRESHOLDS.read_text()) if THRESHOLDS.exists() else {"min_coverage": 0.0, "min_score": 0.0, "min_vocab": 0.0}
    rd, rt = run(dev, th), run(test, th)
    md, mt = metrics(rd), metrics(rt)
    lines = [
        "# Evaluation results", "",
        "Retrieval baseline: BM25 (SQLite FTS5) over 288 K-5 Texas math standards. Extractive answers.",
        f"Decline thresholds (tuned on dev only): `{json.dumps(th)}`", "",
        f"**Dev** ({md['answerable']} answerable, {md['unanswerable']} unanswerable): {fmt(md)}", "",
        f"**Held-out test** ({mt['answerable']} answerable, {mt['unanswerable']} unanswerable): {fmt(mt)}", "",
        "## Test-set misses", "",
    ]
    miss = [r for r in rt if (r["expected"] and not (r["answered"] and r["rank"] == 1)) or (not r["expected"] and r["answered"])]
    if not miss:
        lines.append("None.")
    for r in miss:
        kind = "should decline" if not r["expected"] else f"expected {r['expected']}"
        lines.append(f"- {r['id']} \"{r['question']}\" -> top {r['codes'][:3]}, answered={r['answered']} ({kind})")
    lines += ["", "## Caveats", "",
              "- 52 questions written by one author from the standards text; expected answers need a teacher's review.",
              "- Small sample: treat percentages as directional, not precise.",
              "- Keyword retrieval cannot match meaning when no words overlap; that is what embeddings are for."]
    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
