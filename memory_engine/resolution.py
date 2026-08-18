"""Deterministic entity resolution; ambiguity is always surfaced, never guessed."""
from __future__ import annotations
import re
import unicodedata
from .models import Entity

class AmbiguousEntityError(ValueError): pass
class UnknownEntityError(ValueError): pass

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold().strip())

class EntityResolver:
    def __init__(self, store): self.store = store

    def resolve(self, reference: str, entity_type: str | None = None) -> Entity:
        key = normalize(reference)
        sql = """SELECT DISTINCT e.* FROM entities e LEFT JOIN aliases a ON a.entity_id=e.id
                 WHERE (e.normalized_name=? OR a.normalized_alias=?) AND e.merged_into IS NULL"""
        args: list[str] = [key, key]
        if entity_type:
            sql += " AND e.type=?"; args.append(entity_type)
        rows = self.store.connection.execute(sql, args).fetchall()
        if not rows: raise UnknownEntityError(reference)
        if len(rows) > 1: raise AmbiguousEntityError(f"{reference!r} matches {[r['canonical_name'] for r in rows]}")
        row = rows[0]; return Entity(row["id"], row["canonical_name"], row["type"])
