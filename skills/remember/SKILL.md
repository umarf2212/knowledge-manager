---
name: remember
description: Save a user-stated personal fact into the local AI Memory Engine. Use when the user writes /remember followed by a fact such as a preference, relationship, possession, date, address, employer, or other durable personal information.
---

# Remember

Interpret the text after `/remember` as a request to store a structured fact, not a note. Extract a subject, stable snake_case predicate, value, and optional current/historical context. If the entity does not exist, create it with a clear type and useful aliases. If two entities match, ask which they mean. Confirm the stored fact briefly with its current value.

Use the shared runtime:

```sh
DB="$HOME/.hermes/memory/personal-memory.db"
MEMORY="python3 $HOME/.hermes/skills/ai-memory-engine/scripts/memory.py --db $DB"
```

For example, `/remember My dog Tommy eats Hill's Science Diet` becomes:

```sh
$MEMORY entity create --name "Tommy" --type pet --alias "my dog"
$MEMORY remember --subject Tommy --predicate eats --value "Hill's Science Diet" --source user
```

Only store information the user explicitly supplied or confirmed. Do not store passwords, API keys, government IDs, financial account numbers, health data, or other sensitive data unless the user expressly asks. Use the same subject/predicate/context for changes so history remains intact.
