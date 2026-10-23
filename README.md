# Standards-grounded RAG tutor (K-5 Texas standards, 10 subjects)

**Live demo:** [meshayla.com/ai](https://meshayla.com/ai/) (type a question in the box). Zero runtime dependencies: Python standard library for the reference build, TypeScript for the deployed function.

**Outcome:** on 45 held-out questions, the right standard is the top result for 88% and in the top five for 95%; 4 of 5 off-topic questions are declined; no adversarial input was obeyed. Limits are listed below, including two classes of miss I have not fixed.

**License:** [PolyForm Noncommercial 1.0.0](LICENSE). Free to read, run and learn from; commercial use needs a license from me (meshayla@kempadvisory.com).

## Quick start (clean clone)
```
git clone <this repo> && cd <this repo>
python -m tutor.cli "fifth grade rounding decimals"     # builds the SQLite index on first run
python -m unittest discover -s tests -t .
```
Python 3.10+ with SQLite FTS5 (standard in most builds). Node 22+ only for the `ts/` port.

Ask a question in plain language; get the matching TEKS standard with its 19 TAC citation, or an honest "I can't find that." Covers 2,259 student expectations: ELAR, math, science, social studies, health, PE, art, music, theatre and technology applications, kindergarten to grade 5.

**Source:** the six TEA grade-level TEKS compilations for K-5 (revised June 2024). Math is the 2012 edition, ELAR 2017, science 2021, social studies 2022, health and PE 2020, fine arts 2013, technology applications 2022. TEA publishes these "for information only"; the Texas Register / TAC is the legal text. Languages Other Than English is not included.

## How it works
1. `tutor/parse_all.py` parses each subject's "Knowledge and skills" into records (id, subject, TEKS code, citation, grade, strand, text). A regression test pins the counts; the math records match an earlier independent parse (287 of 288 identical; the other differs only by a double period in TEA's own PDF).
2. `tutor/store.py` loads them into SQLite with an FTS5 index (porter stemming).
3. `tutor/retrieve.py` ranks with BM25, filters by grade when the question names one, and decides **answer vs decline** from three signals: BM25 score, passage coverage, and vocabulary coverage (share of question words that exist anywhere in the standards).
4. `tutor/normalize.py` (and `ts/normalize.ts`) understand how teachers type before retrieval: "fifth grade", "5th grade", "grade 5", "Gr. 5", "G5", "grade five" and "kinder" are one grade; "TEKS 5.3A", "5.3(A)" and "5 3 a" look up that exact standard; a bare decimal like 5.3 is not mistaken for a code; and a word that is not in the standards is fixed only when exactly one standards word is one typing slip away, with the fix reported in the answer (`understood.corrected`). `eval/phrasing.jsonl` pins 38 phrasings, and the Python and TypeScript versions are tested against each other.
4. `tutor/answer.py` is extractive: it quotes the retrieved standard and cites it, so nothing is invented. A `Generator` protocol lets an LLM be plugged in later; it must only see retrieved passages.

```
python -m tutor.cli "fifth grade rounding decimals"
python -m eval.run_eval --calibrate   # tune on dev, report held-out test
python -m tutor.api                    # JSON API: GET /ask?q=...
python -m unittest discover -s tests -t .
```

## Results (see `eval/results.md`)
92 hand-written questions (81 answerable, 11 off-topic), split dev/test. Decline thresholds are tuned on dev only; test is held out.

| | hit@1 | hit@3 | correct decline | false decline |
|---|---|---|---|---|
| Held-out test (40 answerable, 5 off-topic) | 88% | 95% | 80% | 2% |

Per-subject numbers are in the results file. Most non-math subjects have only 3 to 7 questions, so read those as a smoke test, not a measurement. One author wrote the questions; expected answers should be reviewed by a teacher.

**Loading more subjects made decline harder.** With math only, 100% of off-topic questions were declined; with ten subjects, trivia such as "What is the capital of Texas?" shares words with a standard (SS 2.4B mentions "state capital") and is answered with it. That is a known failure, recorded as an expected-failure test, and the reason a relevance check is on the roadmap.

## TypeScript port (what runs on meshayla.com)
`ts/` is a dependency-free TypeScript port (BM25 + Porter stemmer + the same decline rule). It is deployed as a Netlify Function, `/api/ask`.
Parity with this Python reference: same top result, same top five and same answer/decline decision on all 92 golden questions (`node ts/parity.ts`, enforced by `tests/test_parity.py`); unit tests: `node --test ts/*.test.ts`.
If you change `data/standards.jsonl`, regenerate `ts/standards.json` and copy `ts/porter.ts`, `ts/retrieve.ts`, `ts/standards.json` into the site's `netlify/functions/lib/`.

## Known limits
- Keyword retrieval only. Paraphrases with no shared words will miss; embeddings are the next step.
- K-5 only, ten subjects. Grade 6 and above, and Languages Other Than English, decline.
- Trivia that shares words with a standard is answered with it (see above).
- `sql/schema_pgvector_PLANNED.sql` is a design, not tested.

## Roadmap
- **Teacher features** (planned): unpacked standards, vertical alignment across grades, and role-based explanations written by a language model that sees only the retrieved standard.
- 
- Embeddings + pgvector hybrid search, an LLM generator behind the grounding contract, an MCP server, and a crosswalk agent. Each must pass the same evaluation and adversarial suites before it ships.

## Data
`data/standards.jsonl` is parsed from the TEA grade-level TEKS PDFs (`pdftotext -layout`, then `python -m tutor.parse_all data/standards.jsonl <six .txt files>`). The PDFs are not redistributed here; obtain them from TEA to regenerate. `data/standards.db` is built on first run.

## Failure modes, latency and cost

- `python -m eval.adversarial` runs 16 hostile, malformed and misspelled inputs (results in `eval/adversarial_results.md`). No attacker text was obeyed or echoed; 2 legitimate questions were wrongly declined and 2 out-of-scope inputs were answered with a loosely related standard (see file).
- `python -m eval.latency` measures retrieval plus answer on the 92 golden questions: p50 0.4 ms, p95 0.7 ms (local, in-process SQLite). Deployed latency also includes network and function cold start, which is not measured here.
- Cost per answer is effectively zero: no model calls. Hosting is a static site plus one serverless function.

## Build versus buy: why keyword retrieval first

I started with BM25 because the corpus is small (2,259 standards), exact wording and citations matter more than paraphrase, and a deterministic baseline makes the evaluation honest: every later change is compared against it. It also keeps children's questions off third-party services. I would move to embeddings plus a hosted model when users ask in loose language the standards do not use (the misspelling and padded-question misses above show where keyword search breaks), accepting a per-query cost, added latency and a new hallucination risk that the same evaluation and adversarial suites must then clear.
