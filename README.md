# Standards-grounded RAG tutor (K-5 Texas math)

**Live demo:** [meshayla.com/ai](https://meshayla.com/ai/) (type a question in the box). Zero runtime dependencies: Python standard library for the reference build, TypeScript for the deployed function.

**Outcome:** the right standard is the top result for 80% of held-out questions and in the top three for 100%; 100% of off-topic questions are declined; 0 of 16 adversarial inputs were obeyed. Limits are listed below.

**License:** [PolyForm Noncommercial 1.0.0](LICENSE). Free to read, run and learn from; commercial use needs a license from me (meshayla@kempadvisory.com).

## Quick start (clean clone)
```
git clone <this repo> && cd <this repo>
python -m tutor.cli "fifth grade rounding decimals"     # builds the SQLite index on first run
python -m unittest discover -s tests -t .
```
Python 3.10+ with SQLite FTS5 (standard in most builds). Node 22+ only for the `ts/` port.

Ask a question in plain language; get the matching TEKS standard with its 19 TAC citation, or an honest "I can't find that."

**Source:** 19 TAC Chapter 111, Subchapter A (Elementary Math, adopted 2012, K-5), from the official TEA PDF. TEA publishes these rules "for information only"; the Texas Register / TAC is the legal text.

## How it works
1. `tutor/parse.py` parses "Knowledge and skills" into 288 records (id, TEKS code, citation, grade, strand, text).
2. `tutor/store.py` loads them into SQLite with an FTS5 index (porter stemming).
3. `tutor/retrieve.py` ranks with BM25, filters by grade when the question names one, and decides **answer vs decline** from three signals: BM25 score, passage coverage, and vocabulary coverage (share of question words that exist anywhere in the standards).
4. `tutor/answer.py` is extractive: it quotes the retrieved standard and cites it, so nothing is invented. A `Generator` protocol lets an LLM be plugged in later; it must only see retrieved passages.

```
python -m tutor.cli "fifth grade rounding decimals"
python -m eval.run_eval --calibrate   # tune on dev, report held-out test
python -m tutor.api                    # JSON API: GET /ask?q=...
python -m unittest discover -s tests -t .
```

## Results (see `eval/results.md`)
52 hand-written questions (40 answerable, 12 off-topic), split dev/test. Decline thresholds are tuned on dev only; test is held out.

| | hit@1 | hit@3 | correct decline | false decline |
|---|---|---|---|---|
| Held-out test | 80% | 100% | 100% | 5% |

Read these with care: the sample is small, one author wrote the questions, and expected answers should be reviewed by a teacher.

## TypeScript port (what runs on meshayla.com)
`ts/` is a dependency-free TypeScript port (BM25 + Porter stemmer + the same decline rule). It is deployed as a Netlify Function, `/api/ask`.
Parity with this Python reference: same top result, same top five and same answer/decline decision on all 52 golden questions (`node ts/parity.ts`); unit tests: `node --test ts/*.test.ts`.
If you change `data/standards.jsonl`, regenerate `ts/standards.json` and copy `ts/porter.ts`, `ts/retrieve.ts`, `ts/standards.json` into the site's `netlify/functions/lib/`.

## Known limits
- Keyword retrieval only. Paraphrases with no shared words will miss; embeddings are the next step.
- Math K-5 only. Other subjects correctly decline.
- `sql/schema_pgvector_PLANNED.sql` is a design, not tested.

## Roadmap
- **Other subjects and grades:** one official TEA PDF per subject (parser adapted per layout, subject filter, a golden set for each). 
- Embeddings + pgvector hybrid search, an LLM generator behind the grounding contract, an MCP server, and a crosswalk agent. Each must pass the same evaluation and adversarial suites before it ships.

## Data
`data/standards.jsonl` is parsed from the official TEA PDF of 19 TAC Chapter 111, Subchapter A (`pdftotext -layout` then `tutor/parse.py`). The PDF itself is not redistributed here; obtain it from TEA to regenerate. `data/standards.db` is built on first run.

## Failure modes, latency and cost

- `python -m eval.adversarial` runs 16 hostile, malformed and misspelled inputs (results in `eval/adversarial_results.md`). No attacker text was obeyed or echoed; 3 legitimate questions were wrongly declined (see file).
- `python -m eval.latency` measures retrieval plus answer on the 52 golden questions: p50 0.3 ms, p95 0.5 ms (local, in-process SQLite). Deployed latency also includes network and function cold start, which is not measured here.
- Cost per answer is effectively zero: no model calls. Hosting is a static site plus one serverless function.

## Build versus buy: why keyword retrieval first

I started with BM25 because the corpus is small (288 standards), exact wording and citations matter more than paraphrase, and a deterministic baseline makes the evaluation honest: every later change is compared against it. It also keeps children's questions off third-party services. I would move to embeddings plus a hosted model when users ask in loose language the standards do not use (the misspelling and padded-question misses above show where keyword search breaks), accepting a per-query cost, added latency and a new hallucination risk that the same evaluation and adversarial suites must then clear.
