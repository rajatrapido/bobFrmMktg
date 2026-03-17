# To-Do: TimeDiff + WoW Insight Plan

## Implementation Status (Updated)
- `[x]` Change-history removed from reporting decision flow.
- `[x]` LW/LLW and LW/3W trend model implemented.
- `[x]` City-first significance and drilldown implemented.
- `[x]` Auto todo generation implemented in backend payload (`auto_todos`).
- `[x]` Cache-first aggregate storage implemented.
- `[x]` Raw fetch snapshots saved on disk when API fetch happens.
- `[x]` Unified threshold family used in GAQL (min impressions) + evaluator.
- `[x]` Frontend now renders auto todos and handles live fetch failures gracefully.
- `[x]` Milestone harness script added: `/Users/E2005/projects/bobfrmmktg/backend/verify_timeDiff_wow.py`.
- `[x]` Backtest + threshold tuning baseline completed using `/Users/E2005/projects/bobfrmmktg/backend/backtest_timeDiff_wow.py`.
- `[x]` Auto-sync `auto_todos` into `/tasks` collection implemented.
- `[x]` Final report retrieval is storage-first (`/reports/live` reads stored report first, then generates/stores only if missing).
- `[x]` Cache-only storage retrieval path validated (`cache_only=true`) for final report reads.
- `[x]` Backtest/benchmark artifacts generated at `/Users/E2005/projects/bobfrmmktg/backend/storage/backtests/`.

## Final Completion Note
- This plan is now fully implemented for the current scope.
- Operational model is now:
  1. Fetch raw only when missing weekly aggregates.
  2. Aggregate + persist required weekly tables/metadata.
  3. Serve final report from storage by default.
  4. Keep live endpoint cache-first and cache-only capable for no-refetch workflows.

## Objective
- Generate actionable insights using:
  - Near-term trend: `LW vs LLW`
  - Mid-term trend: `LW vs 3-week baseline` (avg of prior 3 completed weeks)
- Keep reporting city-first (campaigns operate city-wise).
- Remove heavy change-history dependency.

## 1) Fetch Strategy
- Initial seed run:
  - Fetch last 4 completed weeks (needed for LW/LLW/3W checks).
- Weekly incremental runs:
  - Fetch only newest completed week.
  - Append to local storage.
  - Recompute trend windows from stored data.
- No repeated historical refetch unless a week is missing/corrupt.

## 2) Storage Strategy (What to persist on disk)
- Store aggregated analytical tables (not full raw event dumps):
  - `weekly_pan_metrics`
  - `weekly_city_metrics`
  - `weekly_city_network_metrics`
  - `weekly_city_campaign_metrics`
  - `weekly_city_campaign_adgroup_metrics` (for eligible/flagged entities)
- Store run metadata:
  - `run_manifest` (date range, rows, schema version, run mode)
  - `threshold_snapshot` (dynamic thresholds used in that run)
- Retain rolling history (example: last 12–26 weeks).

## 3) Threshold Logic (Unified)
- Use same threshold family for both:
  1. GAQL pre-filtering
  2. Evaluator post-filtering
- Dynamic threshold source:
  - recent stored distributions (median/mean/percentiles).
- Minimum filters should adapt per level (pan/city/campaign/adgroup), not fixed constants.

## 4) Hierarchical Insight Flow
- Pan India significance.
- City-level significance + contribution ranking.
- Campaign-level analysis only inside significant cities.
- AdGroup/Ad-level analysis only inside significant city-campaign clusters.
- De-duplicate highlights across levels.

## 5) Significance Rules
- Dual gate required:
  - Statistical movement gate (vs LW/LLW/3W baseline).
  - Business impact gate (absolute contribution to install/cost movement).
- Avoid low-volume false positives using minimum volume floors.

## 6) Decomposition Model (Why installs changed)
- `Installs = f(Impressions, CTR, CTI/CVR, Cost-efficiency)`
- Explain movement using:
  - volume shift (Impressions),
  - engagement shift (CTR),
  - conversion shift (CTI/CVR),
  - efficiency pressure (CPC/CPM).

## 7) To-do Generation
- Convert significant findings to tasks with:
  - entity,
  - issue type,
  - severity,
  - recommended action,
  - expected recovery metric.
- Rank by `impact x confidence x controllability`.
- Publish capped list (top N) each cycle.

## 8) Operational Modes
- Seed mode: bootstrap 4-week baseline.
- Incremental mode: append current week only.
- Cache-first mode: rebuild insights from storage without new fetch.

## 9) Phased Execution
- `[x]` Phase 1: Finalize schema + threshold formulas.
- `[x]` Phase 2: Implement seed fetch + local aggregate store.
- `[x]` Phase 3: Implement weekly incremental append.
- `[x]` Phase 4: Add evaluator + todo generation.
- `[x]` Phase 5: Backtest and tune thresholds (baseline pass; continue periodic tuning as ops task).

## 10) Milestone Harness (How we validate at each stage)

### Milestone A: Schema + Threshold Contract Ready
- Harness checks:
  - `[x]` Validate all required aggregate schemas and required columns exist.
  - `[x]` Validate threshold snapshot object is generated and versioned.
  - `[x]` Validate config resolves LW/LLW/3W windows correctly for a sample week.
- Frontend expectation:
  - `[x]` API returns enriched report payload with metadata fields.

### Milestone B: Seed Fetch + Disk Aggregates
- Harness checks:
  - `[x]` One-time 4-week seed path implemented.
  - `[x]` Aggregate files are written to storage path and readable.
  - `[x]` Row-level sanity checks scripted.
- Frontend expectation:
  - `[x]` Historical report cards can load from stored reports.
  - `[x]` Frontend no longer blocks fully when live endpoint is slow/fails.

### Milestone C: Weekly Incremental Append
- Harness checks:
  - `[x]` Weekly run fetches only missing weeks and appends by week.
  - `[x]` Duplicate week manifest check added in harness.
  - `[x]` Derived trend windows recompute from stored history.
- Frontend expectation:
  - `[x]` New week appears without breaking old cards.
  - `[x]` Week selector/history list implemented and stable.

### Milestone D: Evaluator + Significance Engine
- Harness checks:
  - `[x]` Dual-gate logic works (statistical + business impact).
  - `[x]` Threshold logic alignment between fetch/evaluator is wired.
  - `[x]` Reproducibility harness added (`verify_timeDiff_wow.py` + deterministic backtest over stored aggregates).
- Frontend expectation:
  - `[x]` Report payload supports clear sections:
    - Pan India
    - City movers
    - Campaign/AdGroup drilldown (only when significant)

### Milestone E: To-do Generation
- Harness checks:
  - `[x]` Todos generated only for significant findings.
  - `[x]` Priority ordering is deterministic (impact score).
  - `[x]` Deduplication across hierarchy implemented.
- Frontend expectation:
  - `[x]` To-do panel shows auto-todos with severity + recommendation.
  - `[x]` Deep-link from todo to related insight block implemented.

### Milestone F: Backtest + Quality Gate
- Harness checks:
  - `[x]` Compare output on stored prior-week window(s) via backtest runner.
  - `[x]` Noise-control thresholds validated (todo count bounded in backtest output).
  - `[x]` Runtime/payload benchmark report generated (`backend/storage/backtests/timeDiff_wow_backtest.md`).
- Frontend expectation:
  - `[x]` Render stability validated with storage-first payload and week selector flow.
  - `[x]` Readability improved with deduped significant sections + auto todos.

## 11) Frontend-First Acceptance Criteria (Final)
- User can open a week and immediately see:
  - Pan summary with LW/LLW and LW/3W interpretation.
  - City-first prioritized insights.
  - Clear top campaign/adgroup movers (deduped).
  - Actionable todo list ranked by priority.
- Report loads from stored aggregates when live fetch is disabled.
- Historical weeks remain accessible and consistent week-over-week.
