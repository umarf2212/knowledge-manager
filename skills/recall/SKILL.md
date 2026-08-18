---
name: recall
description: Retrieve an exact current or historical personal fact from the local AI Memory Engine. Use when the user writes /recall followed by a question about remembered personal information, preferences, relationships, possessions, dates, or changes over time.
---

# Recall

Interpret the text after `/recall` as a deterministic memory query. Resolve the named entity and use the narrowest matching command. Return only relevant structured facts, phrased naturally; include source and dates when requested. Never scan or inject the whole database.

Use the shared runtime:

```sh
DB="$HOME/.hermes/memory/personal-memory.db"
MEMORY="python3 $HOME/.hermes/skills/ai-memory-engine/scripts/memory.py --db $DB"
```

Use `lookup` for a current fact, `history` when the user asks about previous/current changes, `at` for a date in the past, and `changes` for a time range. Examples:

```sh
$MEMORY lookup --subject Tommy --predicate eats
$MEMORY history --subject me --predicate employed_by
$MEMORY at --subject me --predicate address --time 2026-01-15T00:00:00+00:00
```

If the question cannot be mapped to a clear entity and predicate, ask one concise clarification; do not guess or use semantic retrieval.
