"""The TypeScript port (what is deployed) must give the same top five and the same answer/decline
decision as this Python reference on every golden question. Skipped if Node 22+ is not installed."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from tutor.retrieve import can_answer, search
from tutor.store import connect

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("node"), "node not installed")
class ParityTests(unittest.TestCase):
    def test_same_results_as_python(self):
        out = subprocess.run(["node", "ts/parity.ts"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        ts = {r["id"]: r for r in json.loads(out)}
        con = connect()
        bad = []
        for line in (ROOT / "eval" / "golden.jsonl").read_text().splitlines():
            g = json.loads(line)
            hits, _ = search(g["question"], k=5, db=con)
            py = ([h.teks_code for h in hits], can_answer(hits))
            t = ts[g["id"]]
            if (t["codes"], t["answered"]) != py:
                bad.append((g["id"], py, (t["codes"], t["answered"])))
        self.assertEqual(bad, [], f"{len(bad)} mismatches")
