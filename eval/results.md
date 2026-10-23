# Evaluation results

Retrieval baseline: BM25 (SQLite FTS5) over 288 K-5 Texas math standards. Extractive answers.
Decline thresholds (tuned on dev only): `{"min_coverage": 0.0, "min_score": 0.0, "min_vocab": 0.7}`

**Dev** (20 answerable, 6 unanswerable): hit@1 90% | hit@3 95% | hit@5 95% | MRR 0.93 | correct answer 80% | false decline 10% | correct decline 100%

**Held-out test** (20 answerable, 6 unanswerable): hit@1 80% | hit@3 100% | hit@5 100% | MRR 0.89 | correct answer 75% | false decline 5% | correct decline 100%

## Test-set misses

- q30 "What do kindergarteners learn about comparing groups of objects up to twenty?" -> top ['K.2D', 'K.2G', 'K.2I'], answered=True (expected ['K.2G', 'K.2H'])
- q31 "Solving addition word problems with an unknown number in first grade" -> top ['1.3B', '1.3E', '1.5F'], answered=True (expected ['1.5F', '1.5D'])
- q37 "Bar graphs with a scale in third grade" -> top ['3.8A', '3.8B', '3.1D'], answered=False (expected ['3.8A'])
- q38 "Dividing by a two-digit divisor" -> top ['4.4F', '5.3C', '5.3F'], answered=True (expected ['5.3C', '5.3G'])
- q45 "Input-output tables and number patterns" -> top ['5.8C', '4.5B', '5.4D'], answered=True (expected ['4.5B'])

## Caveats

- 52 questions written by one author from the standards text; expected answers need a teacher's review.
- Small sample: treat percentages as directional, not precise.
- Keyword retrieval cannot match meaning when no words overlap; that is what embeddings are for.
