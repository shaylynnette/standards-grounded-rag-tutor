"""SQLite store for the standards, with FTS5 (BM25) full-text search."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "sql" / "schema_sqlite.sql"
DEFAULT_DB = ROOT / "data" / "standards.db"
DEFAULT_JSONL = ROOT / "data" / "standards.jsonl"


def build(db_path: Path = DEFAULT_DB, jsonl: Path = DEFAULT_JSONL) -> int:
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    n = 0
    for line in Path(jsonl).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        cur = con.execute(
            "INSERT INTO standards (id, subject, subject_name, adopted, teks_code, citation, grade, section,"
            " strand_number, strand, strand_text, text, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["id"], r["subject"], r["subject_name"], r["adopted"], r["teks_code"], r["citation"], r["grade"],
             r["section"], r["strand_number"], r["strand"], r["strand_text"], r["text"], r["source"]))
        con.execute("INSERT INTO standards_fts (rowid, text, strand_text) VALUES (?,?,?)",
                    (cur.lastrowid, r["text"], r["strand_text"]))
        n += 1
    con.commit()
    con.close()
    return n


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path = Path(db_path)
    if not db_path.exists():
        build(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


if __name__ == "__main__":
    print(f"built {build()} standards into {DEFAULT_DB}")
