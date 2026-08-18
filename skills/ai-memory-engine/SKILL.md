---
name: ai-memory-engine
description: Store, update, and retrieve durable structured personal facts using a local SQLite memory database. Use when an agent needs to remember a user's entities, preferences, relationships, possessions, employment, addresses, dates, or historical changes across sessions; answer factual questions from that memory; or inspect/repair deterministic personal-memory records. Do not use for note taking, document search, or broad semantic/RAG retrieval.
---

# AI Memory Engine

Use the bundled `scripts/memory.py` runtime. Keep the database local, defaulting to `~/.hermes/memory/personal-memory.db` for Hermes. Treat memory writes as user-data changes: only write facts the user stated, confirmed, or explicitly asked to save. Never infer sensitive facts or silently resolve an ambiguous entity.

## Workflow

1. Resolve or create the entity before storing a fact. Give people, pets, organizations, places, and things stable entities; add aliases such as `my dog` only when unambiguous.
2. Use a stable, snake_case predicate and a narrow logical `--context`. For attributes that evolve, reuse the same subject/predicate/context so an update supersedes the prior current fact while retaining history.
3. Retrieve with `lookup` for current facts, `history` for prior/current timelines, `at` for a point in time, and `changes` for a date range. Return only the facts that answer the request.
4. Show uncertainty or ambiguity instead of guessing. Explain a result with its source, dates, confidence, and status when the user asks why.

## Commands

Set a database path once per session:

```sh
DB="$HOME/.hermes/memory/personal-memory.db"
MEMORY="python3 /path/to/ai-memory-engine/scripts/memory.py --db $DB"
```

Create or find entities:

```sh
$MEMORY entity create --name "Me" --type person --alias me --alias i
$MEMORY entity create --name "Tommy" --type pet --alias "my dog"
$MEMORY entity resolve --name "Tommy"
```

Write current facts. A repeated identical fact becomes another observation; a changed value atomically supersedes the old current fact.

```sh
$MEMORY remember --subject Tommy --predicate eats --value "Hill's Science Diet"
$MEMORY remember --subject me --predicate employed_by --value "Company B" --source user
```

Read memory:

```sh
$MEMORY lookup --subject Tommy --predicate eats
$MEMORY history --subject me --predicate employed_by
$MEMORY at --subject me --predicate address --time 2026-01-15T00:00:00+00:00
$MEMORY changes --from 2026-01-01T00:00:00+00:00 --to 2026-07-01T00:00:00+00:00
```

The output is JSON. Do not pass the whole database or unrelated history into model context. Use a precise query and formulate the answer from its returned records.

## Rules

- On a conflicting name, stop and ask the user which entity they mean; specify `--type` only when the user made that type clear.
- Do not store credentials, API keys, financial account numbers, government-ID numbers, health details, or other sensitive data without an explicit user request.
- Prefer source `user`; retain a source and confidence for all writes.
- Correct facts by writing the corrected value into the same slot. Do not delete historical facts to make an answer look cleaner.
- To understand data layout, lifecycle, indexes, and error behavior, read [references/model.md](references/model.md).
