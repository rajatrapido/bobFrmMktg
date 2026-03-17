import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from app.services.ads_service import AdsService
from app.services.ai_service import AIService
from app.services.firebase_service import FirestoreService
from app.services.report_service import ReportService


class ReportEngine:
    def __init__(self):
        self.ads_service = AdsService()
        self.report_service = ReportService()
        self.ai_service = AIService()
        self.db_service = FirestoreService()

        self.storage_root = Path(os.getenv("LOCAL_STORAGE_DIR", "/Users/E2005/projects/bobfrmmktg/backend/storage"))
        self.raw_reports_dir = self.storage_root / "raw_reports"
        self.agg_weeks_dir = self.storage_root / "aggregates" / "weeks"
        self.threshold_dir = self.storage_root / "aggregates" / "thresholds"
        self.raw_reports_dir.mkdir(parents=True, exist_ok=True)
        self.agg_weeks_dir.mkdir(parents=True, exist_ok=True)
        self.threshold_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _env_bool(name, default=False):
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    def _last_full_week_end(self):
        today = datetime.now()
        return today - timedelta(days=today.weekday() + 1)

    def latest_completed_week_id(self):
        return self._last_full_week_end().strftime("%G-W%V")

    @staticmethod
    def _is_valid_report(report):
        if not isinstance(report, dict):
            return False
        required = ["week", "pan_summary", "network_summary", "significant_changes", "auto_todos", "created_at"]
        return all(k in report for k in required)

    def _week_start_from_iso(self, week_str):
        year, week = week_str.split("-W")
        return datetime.fromisocalendar(int(year), int(week), 1)

    def _week_manifest_path(self, week_str):
        return self.agg_weeks_dir / week_str / "manifest.json"

    def _week_data_path(self, week_str):
        return self.agg_weeks_dir / week_str / "weekly_adgroup.json"

    def _week_exists(self, week_str):
        return self._week_data_path(week_str).exists()

    def _required_weeks(self, target_week_offset):
        target_end = self._last_full_week_end() - timedelta(weeks=max(1, int(target_week_offset)) - 1)
        weeks = []
        for i in range(4):
            wk_end = target_end - timedelta(weeks=i)
            weeks.append(wk_end.strftime("%G-W%V"))
        return target_end, sorted(weeks)

    def _load_weekly_aggregate(self, week_str):
        week_path = self._week_data_path(week_str)
        if not week_path.exists():
            return pd.DataFrame()
        with open(week_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        return pd.DataFrame(records)

    def _persist_weekly_aggregates(self, weekly_df):
        if weekly_df.empty:
            return
        for week, wk_df in weekly_df.groupby("Week"):
            week_dir = self.agg_weeks_dir / week
            week_dir.mkdir(parents=True, exist_ok=True)
            week_data_path = week_dir / "weekly_adgroup.json"
            week_manifest_path = week_dir / "manifest.json"

            records = wk_df.to_dict(orient="records")
            with open(week_data_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=True)

            city_df = wk_df.groupby(["Week", "City"])[ReportService.BASE_METRICS].sum().reset_index()
            city_network_df = wk_df.groupby(["Week", "City", "Ad Network Type"])[ReportService.BASE_METRICS].sum().reset_index()
            campaign_df = wk_df.groupby(["Week", "City", "Campaign_Name"])[ReportService.BASE_METRICS].sum().reset_index()
            pan_df = wk_df.groupby(["Week"])[ReportService.BASE_METRICS].sum().reset_index()

            (week_dir / "weekly_city_metrics.json").write_text(
                json.dumps(city_df.to_dict(orient="records"), ensure_ascii=True),
                encoding="utf-8",
            )
            (week_dir / "weekly_city_network_metrics.json").write_text(
                json.dumps(city_network_df.to_dict(orient="records"), ensure_ascii=True),
                encoding="utf-8",
            )
            (week_dir / "weekly_city_campaign_metrics.json").write_text(
                json.dumps(campaign_df.to_dict(orient="records"), ensure_ascii=True),
                encoding="utf-8",
            )
            (week_dir / "weekly_pan_metrics.json").write_text(
                json.dumps(pan_df.to_dict(orient="records"), ensure_ascii=True),
                encoding="utf-8",
            )

            manifest = {
                "week": week,
                "created_at": datetime.now().isoformat(),
                "rows": int(len(wk_df)),
                "schema": "weekly_adgroup_v1",
            }
            with open(week_manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=True, indent=2)

    def _save_raw_fetch_snapshot(self, start_date_str, end_date_str, raw_df):
        if raw_df.empty:
            return
        snapshot_path = self.raw_reports_dir / f"fetch_{start_date_str}_to_{end_date_str}.json"
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(raw_df.to_dict(orient="records"), f, ensure_ascii=True)

    def _compute_fetch_thresholds(self, target_week_str):
        history_dfs = []
        for week_dir in sorted(self.agg_weeks_dir.glob("*")):
            if not week_dir.is_dir():
                continue
            week = week_dir.name
            if week >= target_week_str:
                continue
            df = self._load_weekly_aggregate(week)
            if not df.empty:
                history_dfs.append(df)

        if history_dfs:
            hist = pd.concat(history_dfs, ignore_index=True)
            imp_med = float(hist["Impressions"].median()) if "Impressions" in hist else 1.0
            imp_mean = float(hist["Impressions"].mean()) if "Impressions" in hist else 1.0
            click_med = float(hist["Clicks"].median()) if "Clicks" in hist else 1.0
            install_med = float(hist["Installs"].median()) if "Installs" in hist else 1.0
            min_impressions = int(max(1.0, imp_med, 0.5 * imp_mean))
            min_clicks = int(max(1.0, click_med * 0.25))
            min_installs = int(max(1.0, install_med * 0.2))
        else:
            min_impressions = int(os.getenv("MIN_IMPRESSIONS_FLOOR", "1"))
            min_clicks = int(os.getenv("MIN_CLICKS_FLOOR", "1"))
            min_installs = int(os.getenv("MIN_INSTALLS_FLOOR", "1"))

        threshold_config = {
            "min_impressions": min_impressions,
            "min_clicks": min_clicks,
            "min_installs": min_installs,
            "impact_floor_ratio": float(os.getenv("IMPACT_FLOOR_RATIO", "0.015")),
            "pct_change_floor": float(os.getenv("PCT_CHANGE_FLOOR", "12")),
            "zscore_floor": float(os.getenv("ZSCORE_FLOOR", "1.5")),
            "city_coverage_target": float(os.getenv("CITY_COVERAGE_TARGET", "0.4")),
            "city_contrib_floor": float(os.getenv("CITY_CONTRIB_FLOOR", "0.05")),
        }
        threshold_path = self.threshold_dir / f"{target_week_str}.json"
        with open(threshold_path, "w", encoding="utf-8") as f:
            json.dump(threshold_config, f, ensure_ascii=True, indent=2)
        return threshold_config

    def _hydrate_required_weeks(self, target_week_offset, use_cached_raw, cache_only):
        target_end_date, required_weeks = self._required_weeks(target_week_offset)
        missing_weeks = [w for w in required_weeks if not self._week_exists(w)]
        target_week_str = target_end_date.strftime("%G-W%V")
        thresholds = self._compute_fetch_thresholds(target_week_str)

        if missing_weeks:
            if cache_only:
                raise RuntimeError(f"Cache-only mode enabled but missing aggregate weeks: {', '.join(missing_weeks)}")

            missing_start = self._week_start_from_iso(min(missing_weeks))
            missing_end = self._week_start_from_iso(max(missing_weeks)) + timedelta(days=6)
            start_date_str = missing_start.strftime("%Y-%m-%d")
            end_date_str = missing_end.strftime("%Y-%m-%d")
            min_impressions = 1
            print(f"[{datetime.now()}] Fetching missing weeks from Ads API: {start_date_str} to {end_date_str} (min_impressions={min_impressions})...")

            df_raw = self.ads_service.fetch_performance_data(
                start_date_str,
                end_date_str,
                min_impressions=min_impressions,
            )
            if df_raw.empty:
                raise RuntimeError("No performance data found for missing weekly windows.")
            self._save_raw_fetch_snapshot(start_date_str, end_date_str, df_raw)

            prepared = self.report_service.prepare_data(df_raw)
            weekly = self.report_service.aggregate_weekly(prepared)
            self._persist_weekly_aggregates(weekly)

        required_frames = [self._load_weekly_aggregate(w) for w in required_weeks]
        available_frames = [df for df in required_frames if not df.empty]
        if not available_frames:
            raise RuntimeError("No aggregate data available for required weeks.")
        return target_week_str, pd.concat(available_frames, ignore_index=True), required_weeks, thresholds

    def _build_report_payload(self, target_week_offset=1, use_cached_raw=None, cache_only=None):
        use_cached_raw = self._env_bool("REPORT_USE_CACHED_RAW", True) if use_cached_raw is None else bool(use_cached_raw)
        cache_only = self._env_bool("REPORT_CACHE_ONLY", False) if cache_only is None else bool(cache_only)
        target_week_str, weekly_df, required_weeks, threshold_config = self._hydrate_required_weeks(
            target_week_offset=target_week_offset,
            use_cached_raw=use_cached_raw,
            cache_only=cache_only,
        )

        report_data = self.report_service.generate_weekly_report_from_aggregates(
            weekly_df=weekly_df,
            target_week_str=target_week_str,
            threshold_config=threshold_config,
        )
        if not report_data:
            return None

        ai_summary = self.ai_service.get_summary(report_data, f"Week {target_week_str}")
        report_data["summary"] = ai_summary
        report_data["created_at"] = datetime.now().isoformat()
        report_data["run_meta"] = {
            "target_week": target_week_str,
            "required_weeks": required_weeks,
            "rows_used": int(len(weekly_df)),
            "storage_mode": "processed_report_only_with_local_aggregates",
            "raw_source": "local_aggregates_cache_first",
            "thresholds": threshold_config,
            "aggregate_dir": str(self.agg_weeks_dir.resolve()),
        }
        return report_data

    def generate_and_save_weekly_report(self, target_week_offset=1, use_cached_raw=None, cache_only=None):
        print(f"[{datetime.now()}] Starting report generation...")
        report_data = self._build_report_payload(
            target_week_offset=target_week_offset,
            use_cached_raw=use_cached_raw,
            cache_only=cache_only,
        )
        target_end_date = self._last_full_week_end() - timedelta(weeks=max(1, int(target_week_offset)) - 1)
        target_week_str = target_end_date.strftime("%G-W%V")

        if not report_data:
            print(f"[{datetime.now()}] Failed to generate report data for {target_week_str}.")
            return None
        self.db_service.save_report(target_week_str, report_data)
        self.db_service.sync_auto_todos(target_week_str, report_data.get("auto_todos", []))
        print(f"[{datetime.now()}] Report saved successfully for {target_week_str}.")
        return self.db_service.get_report(target_week_str) or report_data

    def get_live_report(self, weeks_back=1, use_cached_raw=None, cache_only=None):
        print(f"[{datetime.now()}] Fetching live report (weeks_back={weeks_back})...")
        target_end_date = self._last_full_week_end() - timedelta(weeks=max(1, int(weeks_back)) - 1)
        target_week_str = target_end_date.strftime("%G-W%V")

        # Storage-first: if final report exists on disk, serve it directly.
        existing = self.db_service.get_report(target_week_str)
        if existing:
            return existing

        report_data = self._build_report_payload(
            target_week_offset=weeks_back,
            use_cached_raw=use_cached_raw,
            cache_only=cache_only,
        )
        if report_data:
            self.db_service.save_report(target_week_str, report_data)
            self.db_service.sync_auto_todos(target_week_str, report_data.get("auto_todos", []))
            return self.db_service.get_report(target_week_str) or report_data

        return {"error": "Failed to generate report", "target_week": target_week_str}

    def refresh_latest_week(self, use_cached_raw=True, cache_only=False):
        week_id = self.latest_completed_week_id()
        existing = self.db_service.get_report(week_id)
        if self._is_valid_report(existing):
            return {
                "status": "skipped",
                "reason": "latest_in_storage",
                "source": "storage",
                "week_id": week_id,
                "message": "Latest week report already available in storage.",
                "report_created_at": existing.get("created_at"),
            }

        try:
            generated = self.generate_and_save_weekly_report(
                target_week_offset=1,
                use_cached_raw=use_cached_raw,
                cache_only=cache_only,
            )
            if not generated:
                return {
                    "status": "error",
                    "source": "generated",
                    "week_id": week_id,
                    "message": "Failed to generate latest week report.",
                    "detail": "Generation returned empty payload.",
                }
            return {
                "status": "generated",
                "source": "generated",
                "week_id": week_id,
                "message": "Latest week report generated and saved.",
                "generated_at": datetime.now().isoformat(),
                "report_created_at": generated.get("created_at"),
            }
        except Exception as ex:
            return {
                "status": "error",
                "source": "generated",
                "week_id": week_id,
                "message": "Failed to generate latest week report.",
                "detail": str(ex),
            }
