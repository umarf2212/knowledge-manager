"""SQLite persistence and indexes. No ORM: schema and query costs stay visible."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS entities (
 id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, normalized_name TEXT NOT NULL,
 type TEXT NOT NULL, created_at TEXT NOT NULL, merged_into TEXT REFERENCES entities(id),
 UNIQUE(normalized_name, type)
);
CREATE TABLE IF NOT EXISTS aliases (
 normalized_alias TEXT NOT NULL, entity_id TEXT NOT NULL REFERENCES entities(id),
 source TEXT NOT NULL, PRIMARY KEY(normalized_alias, entity_id)
);
CREATE TABLE IF NOT EXISTS facts (
 id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES entities(id), predicate TEXT NOT NULL,
 value_json TEXT NOT NULL, value_normalized TEXT NOT NULL, object_entity_id TEXT REFERENCES entities(id),
 context_key TEXT NOT NULL DEFAULT 'default', status TEXT NOT NULL CHECK(status IN ('observed','validated','current','superseded','archived')),
 confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1), source TEXT NOT NULL,
 observed_at TEXT NOT NULL, valid_from TEXT NOT NULL, valid_to TEXT, supersedes_id TEXT REFERENCES facts(id),
 tags_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS observations (
 id TEXT PRIMARY KEY, fact_id TEXT NOT NULL REFERENCES facts(id), source TEXT NOT NULL,
 observed_at TEXT NOT NULL, raw_text TEXT, confidence REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_alias_lookup ON aliases(normalized_alias);
CREATE INDEX IF NOT EXISTS ix_entity_name ON entities(normalized_name, type);
CREATE INDEX IF NOT EXISTS ix_fact_current ON facts(subject_id, predicate, context_key, status);
CREATE INDEX IF NOT EXISTS ix_fact_object ON facts(object_entity_id, predicate, status);
CREATE INDEX IF NOT EXISTS ix_fact_time ON facts(valid_from, valid_to, status);
CREATE INDEX IF NOT EXISTS ix_fact_predicate ON facts(predicate, status);
"""

class SQLiteStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.executescript(SCHEMA)

    @contextmanager
    def transaction(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

    def rebuild_indexes(self) -> None:
        # SQLite indexes are declarative; REINDEX validates/rebuilds their B-trees.
        self.connection.execute("REINDEX")
