# KT Codex Notes (2026-03-01)

## Project Snapshot
- Purpose: Automate weekly Google Ads performance reporting with AI summaries and deliver via API + UI.
- Current state: Backend has a FastAPI service + scheduled weekly report generation; frontend is a Next.js dashboard that pulls live + historical reports and shows comments/tasks per report.

## Key Files I Read
- `/Users/E2005/projects/bobfrmmktg/kt.md`
- `/Users/E2005/projects/bobfrmmktg/progress_update.md`
- `/Users/E2005/projects/bobfrmmktg/backend/app/main.py`
- `/Users/E2005/projects/bobfrmmktg/backend/app/services/report_engine.py`
- `/Users/E2005/projects/bobfrmmktg/backend/app/services/report_service.py`
- `/Users/E2005/projects/bobfrmmktg/backend/app/services/ads_service.py`
- `/Users/E2005/projects/bobfrmmktg/backend/app/services/ai_service.py`
- `/Users/E2005/projects/bobfrmmktg/backend/app/services/firebase_service.py`
- `/Users/E2005/projects/bobfrmmktg/backend/app/services/auth_service.py`
- `/Users/E2005/projects/bobfrmmktg/frontend/src/app/layout.tsx`
- `/Users/E2005/projects/bobfrmmktg/frontend/src/app/page.tsx`
- `/Users/E2005/projects/bobfrmmktg/frontend/src/components/ReportCard.tsx`
- `/Users/E2005/projects/bobfrmmktg/frontend/src/components/Sidebar.tsx`
- `/Users/E2005/projects/bobfrmmktg/frontend/src/components/AuthProvider.tsx`
- `/Users/E2005/projects/bobfrmmktg/frontend/src/lib/api.ts`
- `/Users/E2005/projects/bobfrmmktg/frontend/src/lib/firebase.ts`

## Architecture (High-Level)
- **Backend (FastAPI)**: Generates reports from Google Ads data, enriches with AI summaries, persists to Firestore (currently mocked).
- **Scheduler (APScheduler)**: Runs weekly generation every Monday at 9:00 AM.
- **Frontend (Next.js)**: Displays live report + historical reports, and supports comments/tasks per report.

## Key Flows
1. **Weekly scheduled report**
   - `main.py` schedules `ReportEngine.generate_and_save_weekly_report()` weekly.
   - `ReportEngine` fetches 4+ weeks of data for WoW comparisons, calls report + AI services, then saves to Firestore.
2. **Live report**
   - `/reports/live` uses `ReportEngine.get_live_report()` without persistence.
3. **User interaction**
   - Frontend loads live + historical reports, supports comments and tasks with API endpoints.

## Report Logic (What’s Interesting)
- **Campaign parsing**: City and Service are derived by splitting campaign names on `-`, pulling index 2 for City and index 4 for Service. This implies naming conventions are critical for correct reporting.
- **WoW logic**: `report_service.generate_weekly_report()` computes WoW based on prior week in `Week` series; if no prior data, WoW defaults to `0`.
- **Movers logic**: For each city, it pulls top 2 positive and top 2 negative ad groups by install delta and includes only those with non-zero change.
- **Recent changes**: Pulls up to 10 change events and attaches as structured entries for AI interpretation.

## AI Summary Generation (Notable)
- `AIService` uses Gemini 2.5 Flash and provides a structured prompt that expects Markdown only (no HTML tables), with executive summary, movers, change impact, and recommendations.
- When no `GEMINI_API_KEY`, it returns a mock HTML snippet.

## Auth + Persistence State
- **Backend auth**: `verify_token()` currently bypasses real Firebase Auth and returns a mock user.
- **Frontend auth**: `AuthProvider` always returns a mock user; `firebase.ts` is stubbed.
- **Firestore**: `FirestoreService` is hard-coded to mock-only mode.

## Notes From `progress_update.md`
- Backend logic migrated from standalone script (`performace_report_updated.py`) into a structured FastAPI service.
- Services segregated as AdsService, ReportService, AIService, FirestoreService, orchestrated by ReportEngine.
- Scheduler job runs Mondays at 9:00 AM.

## Suggested Next Investigations (If You Want)
1. Validate campaign naming conventions and ensure consistent parsing for City/Service fields.
2. Re-enable real Firebase Auth and Firestore once ready (multiple components are still mock-only).
3. Check `performace_report_updated.py` for any unmatched edge-case logic not migrated to `ReportService`.
