-- PLANNED, NOT YET RUN OR TESTED. Target schema for the embeddings upgrade (Postgres + pgvector).
-- The working baseline uses SQLite FTS5 (see schema_sqlite.sql). This file records the design only.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE standards (
  id            text PRIMARY KEY,
  teks_code     text NOT NULL,
  citation      text NOT NULL,
  grade         text NOT NULL,
  strand        text NOT NULL,
  strand_text   text NOT NULL,
  text          text NOT NULL,
  source        text NOT NULL,
  embedding     vector(384)            -- dimension depends on the embedding model chosen
);

CREATE INDEX standards_embedding_idx ON standards USING hnsw (embedding vector_cosine_ops);
CREATE INDEX standards_fts_idx ON standards USING gin (to_tsvector('english', text || ' ' || strand_text));

-- Hybrid retrieval idea: reciprocal-rank fusion of keyword rank and vector rank, then threshold to decline.
