-- Standards store (SQLite, used today). Full-text search with BM25 ranking via FTS5.
CREATE TABLE IF NOT EXISTS standards (
  id            TEXT PRIMARY KEY,      -- e.g. 111.7.b.2.C
  subject       TEXT NOT NULL,         -- ELAR, MATH, SCI, SS, HEALTH, PE, ART, MUSIC, THEATRE, TECH
  subject_name  TEXT NOT NULL,
  adopted       TEXT NOT NULL,         -- year the TEKS were adopted
  teks_code     TEXT NOT NULL,         -- e.g. MATH 5.2C
  citation      TEXT NOT NULL,         -- e.g. 19 TAC §111.7(b)(2)(C)
  grade         TEXT NOT NULL,         -- K, 1 ... 5
  section       TEXT NOT NULL,
  strand_number INTEGER NOT NULL,
  strand        TEXT NOT NULL,
  strand_text   TEXT NOT NULL,
  text          TEXT NOT NULL,         -- verbatim student expectation
  source        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_standards_grade ON standards(grade);
CREATE INDEX IF NOT EXISTS idx_standards_subject ON standards(subject);

-- Search index: the expectation text is weighted above the strand description at query time.
CREATE VIRTUAL TABLE IF NOT EXISTS standards_fts USING fts5(
  text, strand_text,
  tokenize = 'porter unicode61'
);
