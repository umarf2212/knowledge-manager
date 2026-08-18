---
name: mms-forget
description: Permanently delete one exact personal-memory fact and its observations after explicit confirmation. Use when the user writes /mms-forget to remove incorrect, private, or no-longer-wanted personal information.
---

# MMS Forget

Treat `/mms-forget` as a destructive privacy operation. First retrieve the exact matching fact and show its ID, subject, predicate, and value. Explain that deletion is permanent in the local database and removes its observations. Ask the user to reply `DELETE <fact-id>`; execute only when the confirmation exactly matches the displayed ID. Never infer a confirmation from prose and never delete multiple facts in one confirmation.

```sh
DB="$HOME/.hermes/memory/personal-memory.db"
MEMORY="python3 $HOME/.hermes/skills/mms-memory-engine/scripts/memory.py --db $DB"
$MEMORY forget --fact-id "<fact-id>" --confirm DELETE
```

Do not claim deletion removes copies from backups, exports, prior Git history, or other devices. Advise the user to delete those copies separately when applicable.
