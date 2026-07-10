---
name: Bulk fermentation log entry
description: Pattern used for multi-row bulk form submission (dettaglio_cotta diario)
---

For the bulk fermentation-log entry feature, the form uses dynamically-numbered field names (`data_0`, `temp_0`, `densita_0`, `note_0`, `data_1`, ...) added client-side via a "+ Aggiungi riga" button (JS clones a row template with an incrementing counter).

**Why:** FastAPI `Form(...)` params can't express a variable-length list of rows cleanly without a JS-driven index convention, so the backend reads the raw form dict directly.

**How to apply:** Backend route takes `request: Request` and does `form = await request.form()`, then loops `i = 0, 1, 2, ...` checking `f"data_{i}" in form` until missing — this avoids needing a fixed max row count. Reuse this same convention for any other bulk/multi-row form in this app to stay consistent.
