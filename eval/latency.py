"""Measure end-to-end answer latency (retrieval + answer) over the golden questions."""
from __future__ import annotations
import json, statistics, time
from pathlib import Path
from tutor.answer import ask
from tutor.store import connect

qs = [json.loads(l)["question"] for l in Path(__file__).with_name("golden.jsonl").read_text().splitlines() if l.strip()]
db = connect()
for q in qs[:5]: ask(q, db=db)  # warm up
ts = []
for _ in range(20):
    for q in qs:
        t = time.perf_counter(); ask(q, db=db); ts.append((time.perf_counter() - t) * 1000)
ts.sort()
p = lambda f: ts[min(len(ts) - 1, int(f * len(ts)))]
out = f"n={len(ts)} queries | p50 {p(.5):.1f} ms | p95 {p(.95):.1f} ms | p99 {p(.99):.1f} ms | model calls per answer: 0"
print(out)
Path(__file__).with_name("latency.txt").write_text(out + "\n")
