"""Public value objects. Values are JSON-compatible primitives or objects."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class Entity:
    id: str
    name: str
    type: str

@dataclass(frozen=True)
class FactInput:
    subject: str
    predicate: str
    value: Any
    object_entity: str | None = None
    context: str = "default"
    confidence: float = 1.0
    source: str = "user"
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    tags: tuple[str, ...] = ()

@dataclass(frozen=True)
class RetrievedFact:
    id: str
    subject: Entity
    predicate: str
    value: Any
    object_entity: Entity | None
    status: str
    observed_at: datetime
    valid_from: datetime
    valid_to: datetime | None
    confidence: float
    source: str
    why_matched: str
