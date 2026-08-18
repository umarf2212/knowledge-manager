---
name: mms-correct
description: Correct a remembered personal fact by replacing its current value while preserving the prior value as history. Use when the user writes /mms-correct to fix an incorrect or outdated memory.
---

# MMS Correct

Interpret the text after `/mms-correct` as a correction of an existing fact. Identify the entity, predicate, replacement value, and context. Resolve the entity and execute `correct`; it atomically supersedes the old current fact rather than deleting history. If the existing fact or intended predicate is unclear, show the matching fact and ask one clarification.

```sh
DB="$HOME/.hermes/memory/personal-memory.db"
MEMORY="python3 $HOME/.hermes/skills/mms-memory-engine/scripts/memory.py --db $DB"
$MEMORY correct --subject me --predicate employed_by --value "Company B" --source user
```

Confirm the new current value and mention that the old value remains available in history.
