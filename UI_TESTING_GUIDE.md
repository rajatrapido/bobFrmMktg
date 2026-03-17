# UI Testing Guide (Storage-First Reports)

## Purpose
This guide explains how to run and validate the project using the UI only (no extra validation scripts required), with **fetch/seed testing deferred for later**.

## Prerequisites
- Backend virtualenv already exists at `/Users/E2005/projects/bobfrmmktg/backend/.venv`
- Frontend dependencies already installed in `/Users/E2005/projects/bobfrmmktg/frontend`

## 1) Start Backend
Open Terminal 1:

```bash
cd /Users/E2005/projects/bobfrmmktg/backend
GEMINI_API_KEY='' .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 2) Start Frontend
Open Terminal 2:

```bash
cd /Users/E2005/projects/bobfrmmktg/frontend
npm run dev -- --port 3000
```

## 3) Open UI
In browser:

```text
http://localhost:3000
```

## 4) UI-Only Test Steps

1. Wait for page to load.
   - Expect:
     - `Live Performance (Current Week)` card
     - `Historical Reports` section

2. Do **not** trigger fetch/seed flows for now.
   - Skip `Refresh All` if it may trigger generation in your environment.
   - Use already stored reports only.

3. Validate historical reports.
   - Confirm one or more historical report cards are shown.
   - Use week dropdown to filter by a single week.
   - Switch back to `All Weeks`.

4. Validate storage-first behavior from UI.
   - Refresh browser page.
   - Reports should still load without requiring another manual trigger.

5. Validate report content.
   - In any report card, check:
     - Summary text visible
     - Installs / Cost / Clicks visible
     - WoW shown near title

6. Validate To-do panel.
   - Click `To-do List`.
   - Confirm auto-generated todos appear with:
     - severity label
     - issue text
     - recommendation

7. Validate deep links.
   - In To-do panel click `Jump to related insight`.
   - Confirm page jumps to city/campaign insight block in the card.

8. Validate comments/tasks interaction.
   - Add a comment in `Comment` panel.
   - Toggle a task checkbox in `To-do List`.
   - Confirm UI updates immediately.

## 5) How to Update Latest Week Report

### Preferred (UI)
1. Open `http://localhost:3000`.
2. Click `Refresh All` in the page header.
3. Wait for loading to complete.
4. The newest week report is regenerated and saved, then shown in `Historical Reports`.

### Optional (API trigger from terminal)
Run this if you want to trigger latest-week generation manually:

```bash
curl -X POST -H 'Authorization: Bearer mock_token' 'http://localhost:8000/reports/generate?target_week_offset=1&use_cached_raw=true&cache_only=false'
```

Then refresh the browser page to see updated data.

## 6) Fetch Testing (Deferred)
Fetch/seed validation is intentionally deferred.

When you decide to test fetching later, use:

```bash
curl -X POST -H 'Authorization: Bearer mock_token' 'http://localhost:8000/reports/generate?target_week_offset=1&use_cached_raw=true&cache_only=false'
```

## 7) Optional Direct API Sanity (storage-only)
Run in Terminal 3:

```bash
curl -H 'Authorization: Bearer mock_token' 'http://localhost:8000/reports/live?weeks_back=1&cache_only=true&use_cached_raw=true'
```

This confirms storage-first live read path.

## 8) Stop Services
In Terminal 1 and 2:
- Press `Ctrl + C`
