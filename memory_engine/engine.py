from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from typing import Any
from .models import Entity, FactInput, RetrievedFact
from .resolution import EntityResolver, normalize
from .storage import SQLiteStore
from .ontology import Ontology

def _now() -> datetime: return datetime.now(timezone.utc)
def _iso(value: datetime | None) -> str: return (value or _now()).astimezone(timezone.utc).isoformat()
def _parse(value: str | None) -> datetime | None: return datetime.fromisoformat(value) if value else None
def _value_key(value: Any) -> str: return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

class MemoryEngine:
    """Facade joining storage, resolution, ingestion and deterministic query planning."""
    def __init__(self, path: str = ":memory:"):
        self.store = SQLiteStore(path)
        self.entities = EntityResolver(self.store)
        self.ontology = Ontology()

    def create_entity(self, name: str, entity_type: str, aliases: list[str] | tuple[str, ...] = ()) -> Entity:
        now, eid = _iso(None), str(uuid.uuid4())
        key = normalize(name)
        with self.store.transaction() as db:
            row = db.execute("SELECT * FROM entities WHERE normalized_name=? AND type=? AND merged_into IS NULL", (key, entity_type)).fetchone()
            if row: entity = Entity(row["id"], row["canonical_name"], row["type"])
            else:
                db.execute("INSERT INTO entities VALUES(?,?,?,?,?,NULL)", (eid, name, key, entity_type, now))
                entity = Entity(eid, name, entity_type)
            for alias in set((*aliases, name)):
                db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?,?)", (normalize(alias), entity.id, "user"))
        return entity

    def add_alias(self, entity: str, alias: str, source: str = "user") -> None:
        target = self.entities.resolve(entity)
        # Alias collisions are ambiguity rather than a hidden winner.
        existing = self.store.connection.execute("SELECT entity_id FROM aliases WHERE normalized_alias=?", (normalize(alias),)).fetchall()
        if existing and any(r["entity_id"] != target.id for r in existing):
            raise ValueError(f"alias {alias!r} already belongs to another entity")
        with self.store.transaction() as db:
            db.execute("INSERT OR IGNORE INTO aliases VALUES(?,?,?)", (normalize(alias), target.id, source))

    def remember(self, subject: str | Entity, predicate: str, value: Any, *, object_entity: str | Entity | None = None,
                 context: str = "default", confidence: float = 1.0, source: str = "user",
                 observed_at: datetime | None = None, valid_from: datetime | None = None,
                 tags: tuple[str, ...] = (), raw_text: str | None = None) -> RetrievedFact:
        """Insert a current fact, superseding the current fact in the same logical slot."""
        subject_entity = subject if isinstance(subject, Entity) else self.entities.resolve(subject)
        obj = object_entity if isinstance(object_entity, Entity) else (self.entities.resolve(object_entity) if object_entity else None)
        if not predicate or not predicate.replace("_", "").strip(): raise ValueError("predicate is required")
        now, fact_id = _iso(None), str(uuid.uuid4())
        observed, start = _iso(observed_at), _iso(valid_from or observed_at)
        value_json = _value_key(value)
        with self.store.transaction() as db:
            previous = db.execute("""SELECT id FROM facts WHERE subject_id=? AND predicate=? AND context_key=? AND status='current'
                                   ORDER BY valid_from DESC""", (subject_entity.id, predicate, context)).fetchall()
            # Identical assertion is recorded as another observation, not another fact.
            for prior in previous:
                row = db.execute("SELECT value_json, object_entity_id FROM facts WHERE id=?", (prior["id"],)).fetchone()
                if row["value_json"] == value_json and row["object_entity_id"] == (obj.id if obj else None):
                    db.execute("INSERT INTO observations VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), prior["id"], source, observed, raw_text, confidence))
                    return self._fetch(prior["id"], "exact duplicate observation")
            for prior in previous:
                db.execute("UPDATE facts SET status='superseded', valid_to=? WHERE id=?", (start, prior["id"]))
            supersedes = previous[0]["id"] if previous else None
            db.execute("""INSERT INTO facts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fact_id, subject_entity.id, predicate, value_json, normalize(str(value)), obj.id if obj else None, context,
                 "current", confidence, source, observed, start, None, supersedes, json.dumps(tags)))
            db.execute("INSERT INTO observations VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), fact_id, source, observed, raw_text, confidence))
        return self._fetch(fact_id, "new current assertion")

    def ingest(self, fact: FactInput) -> RetrievedFact:
        return self.remember(fact.subject, fact.predicate, fact.value, object_entity=fact.object_entity, context=fact.context,
            confidence=fact.confidence, source=fact.source, observed_at=fact.observed_at, valid_from=fact.valid_from, tags=fact.tags)

    def set_lifecycle(self, fact_id: str, status: str) -> RetrievedFact:
        """Explicit review workflow for observed → validated → current or archived facts."""
        if status not in {"observed", "validated", "current", "superseded", "archived"}:
            raise ValueError("invalid lifecycle status")
        with self.store.transaction() as db:
            exists = db.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()
            if not exists: raise ValueError(f"unknown fact {fact_id}")
            if status == "current":
                db.execute("""UPDATE facts SET status='superseded', valid_to=?
                    WHERE subject_id=? AND predicate=? AND context_key=? AND status='current' AND id<>?""",
                    (_iso(None), exists["subject_id"], exists["predicate"], exists["context_key"], fact_id))
            db.execute("UPDATE facts SET status=? WHERE id=?", (status, fact_id))
        return self._fetch(fact_id, f"lifecycle changed to {status}")

    def archive(self, fact_id: str, *, archived_at: datetime | None = None) -> RetrievedFact:
        """Hide a fact from normal retrieval while preserving it as historical evidence."""
        stamp = _iso(archived_at)
        with self.store.transaction() as db:
            row = db.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()
            if not row: raise ValueError(f"unknown fact {fact_id}")
            db.execute("UPDATE facts SET status='archived', valid_to=COALESCE(valid_to, ?) WHERE id=?", (stamp, fact_id))
        return self._fetch(fact_id, "explicitly archived")

    def forget(self, fact_id: str) -> None:
        """Permanently remove one fact and its observations. The caller must obtain user confirmation."""
        with self.store.transaction() as db:
            row = db.execute("SELECT id FROM facts WHERE id=?", (fact_id,)).fetchone()
            if not row: raise ValueError(f"unknown fact {fact_id}")
            # Keep later historical records valid if their predecessor is removed.
            db.execute("UPDATE facts SET supersedes_id=NULL WHERE supersedes_id=?", (fact_id,))
            db.execute("DELETE FROM observations WHERE fact_id=?", (fact_id,))
            db.execute("DELETE FROM facts WHERE id=?", (fact_id,))

    def correct(self, subject: str | Entity, predicate: str, value: Any, **kwargs) -> RetrievedFact:
        """Semantic alias for remember: replace the current fact in the same logical slot."""
        return self.remember(subject, predicate, value, **kwargs)

    def lookup(self, subject: str | Entity, predicate: str, *, current: bool = True, at: datetime | None = None) -> list[RetrievedFact]:
        entity = subject if isinstance(subject, Entity) else self.entities.resolve(subject)
        if at:
            stamp = _iso(at)
            rows = self.store.connection.execute("""SELECT id FROM facts WHERE subject_id=? AND predicate=? AND valid_from<=?
                AND (valid_to IS NULL OR valid_to>?) AND status IN ('current','superseded') ORDER BY valid_from""", (entity.id, predicate, stamp, stamp)).fetchall()
            why = f"temporal index at {stamp}"
        else:
            status = "current" if current else "superseded"
            rows = self.store.connection.execute("SELECT id FROM facts WHERE subject_id=? AND predicate=? AND status=? ORDER BY valid_from", (entity.id, predicate, status)).fetchall()
            why = "current-slot index" if current else "history index"
        return [self._fetch(r["id"], why) for r in rows]

    def history(self, subject: str | Entity, predicate: str | None = None) -> list[RetrievedFact]:
        entity = subject if isinstance(subject, Entity) else self.entities.resolve(subject)
        sql, args = "SELECT id FROM facts WHERE subject_id=?", [entity.id]
        if predicate: sql += " AND predicate=?"; args.append(predicate)
        sql += " ORDER BY valid_from"
        return [self._fetch(r["id"], "entity history index") for r in self.store.connection.execute(sql, args)]

    def changed_between(self, start: datetime, end: datetime) -> list[RetrievedFact]:
        rows = self.store.connection.execute("SELECT id FROM facts WHERE observed_at>=? AND observed_at<? ORDER BY observed_at", (_iso(start), _iso(end))).fetchall()
        return [self._fetch(r["id"], "observation time index") for r in rows]

    def related_to(self, object_entity: str | Entity, predicate: str | None = None) -> list[RetrievedFact]:
        entity = object_entity if isinstance(object_entity, Entity) else self.entities.resolve(object_entity)
        sql, args = "SELECT id FROM facts WHERE object_entity_id=? AND status='current'", [entity.id]
        if predicate: sql += " AND predicate=?"; args.append(predicate)
        return [self._fetch(r["id"], "relationship-object index") for r in self.store.connection.execute(sql, args)]

    def answer(self, question: str) -> list[RetrievedFact]:
        """Small rule planner for common personal-memory questions; callers can use lookup for a fully explicit plan."""
        q = normalize(question).rstrip("?")
        # e.g. 'what food does tommy eat' → alias resolution + exact predicate lookup
        import re
        match = re.fullmatch(r"(?:what (?:food|does)|what) (?:does )?(.+?) (?:eat|eats)", q)
        if match: return self.lookup(match.group(1), "eats")
        match = re.fullmatch(r"where do i currently work", q)
        if match: return self.lookup("me", "employed_by")
        match = re.fullmatch(r"where have i worked(?: previously)?", q)
        if match: return self.history("me", "employed_by")
        match = re.fullmatch(r"what is (.+?)'s name", q)
        if match: return self.lookup(match.group(1), "name")
        raise ValueError("No deterministic query plan; supply entity and predicate explicitly (semantic search is intentionally not implicit).")

    def _fetch(self, fact_id: str, why: str) -> RetrievedFact:
        row = self.store.connection.execute("""SELECT f.*, s.canonical_name sn, s.type st, o.id oid, o.canonical_name oname, o.type ot
            FROM facts f JOIN entities s ON s.id=f.subject_id LEFT JOIN entities o ON o.id=f.object_entity_id WHERE f.id=?""", (fact_id,)).fetchone()
        return RetrievedFact(row["id"], Entity(row["subject_id"], row["sn"], row["st"]), row["predicate"], json.loads(row["value_json"]),
            Entity(row["oid"], row["oname"], row["ot"]) if row["oid"] else None, row["status"], _parse(row["observed_at"]), _parse(row["valid_from"]), _parse(row["valid_to"]), row["confidence"], row["source"], why)
