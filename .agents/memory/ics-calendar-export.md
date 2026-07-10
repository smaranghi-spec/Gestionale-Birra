---
name: ICS calendar export
description: How the calendario ICS feed is generated and how to sync with Google/Apple/Outlook
---

The `/calendario/export.ics` route builds a VCALENDAR document from all `EventoCalendario` rows and returns it with `media_type="text/calendar; charset=utf-8"`.

**Why:** users wanted their brewery calendar (cotte, imbottigliamenti, eventi) visible in their normal calendar app rather than only in-app.

**How to apply:**
- All-day events (no `ora` set) use `DTSTART;VALUE=DATE:YYYYMMDD`; timed events use `DTSTART:YYYYMMDDTHHMMSS`.
- To subscribe live (auto-refreshing) in Google/Apple/Outlook, users should add the feed via "From URL" using `webcal://<domain>/calendario/export.ics` instead of downloading the file once.
- `STATUS:CANCELLED` is used for eventi marked `completato` (there's no dedicated "done" ICS status, this is a pragmatic choice — revisit if it causes confusion in calendar clients).
