---
name: mms-archive
description: Hide a remembered fact from ordinary retrieval while retaining its historical record. Use when the user writes /mms-archive to retire a fact without permanently deleting it.
---

# MMS Archive

Interpret `/mms-archive` as a request to retire one exact fact. First retrieve the matching fact and show its ID, subject, predicate, and value. Ask the user to reply `ARCHIVE <fact-id>`; only then execute the archive command. Do not archive multiple facts without explicit confirmation for each.

```sh
DB="$HOME/.hermes/memory/personal-memory.db"
MEMORY="python3 $HOME/.hermes/skills/mms-memory-engine/scripts/memory.py --db $DB"
$MEMORY archive --fact-id "<fact-id>" --confirm ARCHIVE
```

Archived facts are omitted from ordinary current lookup but remain in history. Recommend `/mms-forget` only when the user truly wants permanent removal.
