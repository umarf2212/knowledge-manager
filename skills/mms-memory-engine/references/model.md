# Memory model

The runtime uses SQLite with four tables: `entities`, `aliases`, `facts`, and `observations`. Entity aliases and canonical names are case-insensitive Unicode-normalized keys. A reference that maps to zero entities is unknown; one is deterministic; more than one is an error. Types are optional disambiguators and are open vocabulary.

A fact has a subject, predicate, JSON value, context key, lifecycle status, confidence, source, observation time, validity interval, and optional superseded-fact ID. The current logical slot is `(subject, predicate, context)`. Writing a different value to that slot marks the old fact `superseded`, closes its validity interval, and writes a new `current` fact in the same transaction. Writing the same value only adds an observation.

Use `lookup` for the current state, `history` for all states, `at` for a historical point, and `changes` for facts observed in an interval. `correct` writes a new current fact and supersedes the old value. `archive` retains the record but hides it from ordinary retrieval. `forget` permanently removes one fact and its observations, and must only execute after an exact user confirmation. All command results include enough provenance to explain the match.

The runtime has indexed aliases, current fact slots, and time ranges. It is designed for personal-scale 1,000–10,000 active facts, local backup as a single SQLite file, and deterministic retrieval—not semantic search.
