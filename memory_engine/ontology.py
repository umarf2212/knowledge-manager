"""Lightweight vocabulary registry; it guides callers but never constrains storage."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PredicateDefinition:
    name: str
    subject_types: tuple[str, ...] = ()
    object_types: tuple[str, ...] = ()
    description: str = ""

class Ontology:
    def __init__(self):
        self.entity_types = {"person", "pet", "organization", "place", "thing"}
        self.predicates: dict[str, PredicateDefinition] = {}

    def register_entity_type(self, name: str) -> None: self.entity_types.add(name)
    def register_predicate(self, definition: PredicateDefinition) -> None: self.predicates[definition.name] = definition
    def describe(self, predicate: str) -> PredicateDefinition | None: return self.predicates.get(predicate)
