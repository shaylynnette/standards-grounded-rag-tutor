# Evaluation results

Retrieval baseline: BM25 (SQLite FTS5) over 2259 K-5 Texas standards in 10 subjects (TEA TEKS, revised June 2024). Extractive answers.
Decline thresholds (tuned on dev only): `{"min_coverage": 0.0, "min_score": 0.0, "min_vocab": 0.8}`

**Dev** (41 answerable, 6 unanswerable): hit@1 93% | hit@3 98% | hit@5 98% | MRR 0.95 | correct answer 90% | false decline 5% | correct decline 83%

**Held-out test** (40 answerable, 5 unanswerable): hit@1 88% | hit@3 95% | hit@5 95% | MRR 0.91 | correct answer 85% | false decline 2% | correct decline 80%

## By subject (dev and test combined, answerable questions only)

| Subject | Questions | hit@1 | hit@3 |
|---|---|---|---|
| ART | 2 | 100% | 100% |
| ELAR | 7 | 100% | 100% |
| HEALTH | 5 | 100% | 100% |
| MATH | 40 | 82% | 95% |
| MUSIC | 3 | 100% | 100% |
| PE | 4 | 75% | 75% |
| SCI | 7 | 100% | 100% |
| SS | 6 | 100% | 100% |
| TECH | 4 | 100% | 100% |
| THEATRE | 3 | 100% | 100% |

## Test-set misses

- q31 "Solving addition word problems with an unknown number in first grade" -> top ['MATH 1.3B', 'MATH 1.3E', 'MATH 1.5F'], answered=True (expected ['MATH 1.5F', 'MATH 1.5D'])
- q38 "Dividing by a two-digit divisor" -> top ['MATH 4.4F', 'MATH 5.3C', 'MATH 5.3F'], answered=True (expected ['MATH 5.3C', 'MATH 5.3G'])
- q45 "Input-output tables and number patterns" -> top ['MATH 5.8C', 'MATH 4.5B', 'SCI 3.1F'], answered=True (expected ['MATH 4.5B'])
- q46 "Writing a number with the cent symbol" -> top ['ELAR 3.9D'], answered=True (expected ['MATH 1.4B'])
- q58 "Alphabetizing words and using a dictionary in second grade" -> top ['ELAR 2.2D', 'ELAR 2.2C', 'ELAR 2.2B'], answered=False (expected ['ELAR 2.2D'])
- q81 "Kindergarten exercises that promote health-related fitness" -> top ['HEALTH K.4B', 'HEALTH K.5', 'HEALTH K.7B'], answered=True (expected ['PE K.8C'])
- q96 "What does the Texas state test cost per student?" -> top ['SS K.9A', 'SS 4.14D', 'SS 4.3E'], answered=True (should decline)

## Caveats

- 92 questions written by one author from the standards text; expected answers need a teacher's review.
- Several subjects have only 3 to 6 questions: treat their per-subject numbers as a smoke test, not a measurement.
- Small sample: treat percentages as directional, not precise.
- Keyword retrieval cannot match meaning when no words overlap; that is what embeddings are for.
