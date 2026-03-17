import json
import os
import time
from pathlib import Path

import pandas as pd

from app.services.report_service import ReportService


STORAGE_ROOT = Path(os.getenv("LOCAL_STORAGE_DIR", "/Users/E2005/projects/bobfrmmktg/backend/storage"))
AGG_WEEKS_DIR = STORAGE_ROOT / "aggregates" / "weeks"
THRESHOLD_DIR = STORAGE_ROOT / "aggregates" / "thresholds"
BACKTEST_DIR = STORAGE_ROOT / "backtests"
BACKTEST_DIR.mkdir(parents=True, exist_ok=True)


def load_week_df(week):
    path = AGG_WEEKS_DIR / week / "weekly_adgroup.json"
    if not path.exists():
        return pd.DataFrame()
    with open(path, "r", encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))


def load_threshold(week):
    path = THRESHOLD_DIR / f"{week}.json"
    if not path.exists():
        return {
            "min_impressions": 1,
            "min_clicks": 1,
            "min_installs": 1,
            "impact_floor_ratio": 0.015,
            "pct_change_floor": 12.0,
            "zscore_floor": 1.5,
            "city_coverage_target": 0.4,
            "city_contrib_floor": 0.05,
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    weeks = sorted([p.name for p in AGG_WEEKS_DIR.iterdir() if p.is_dir()]) if AGG_WEEKS_DIR.exists() else []
    if len(weeks) < 4:
        print("Need at least 4 aggregate weeks for backtest.")
        return 1

    service = ReportService()
    rows = []
    for i in range(3, len(weeks)):
        target_week = weeks[i]
        use_weeks = weeks[i - 3 : i + 1]
        frames = [load_week_df(w) for w in use_weeks]
        if any(df.empty for df in frames):
            continue
        weekly_df = pd.concat(frames, ignore_index=True)
        threshold = load_threshold(target_week)

        t0 = time.time()
        report = service.generate_weekly_report_from_aggregates(weekly_df, target_week, threshold)
        runtime_ms = (time.time() - t0) * 1000
        if not report:
            continue
        payload_size = len(json.dumps(report))
        rows.append(
            {
                "week": target_week,
                "city_insights": len(report.get("city_insights", [])),
                "campaign_insights": len(report.get("campaign_insights", [])),
                "adgroup_insights": len(report.get("adgroup_insights", [])),
                "auto_todos": len(report.get("auto_todos", [])),
                "runtime_ms": round(runtime_ms, 2),
                "payload_bytes": payload_size,
                "wow_growth": report.get("wow_growth", 0),
            }
        )

    if not rows:
        print("No backtest rows generated.")
        return 1

    df = pd.DataFrame(rows)
    csv_path = BACKTEST_DIR / "timeDiff_wow_backtest.csv"
    md_path = BACKTEST_DIR / "timeDiff_wow_backtest.md"
    df.to_csv(csv_path, index=False)

    noise_ok = (df["auto_todos"] <= 20).all()
    median_runtime = float(df["runtime_ms"].median())
    median_payload_kb = float(df["payload_bytes"].median()) / 1024.0

    md_lines = [
        "# TimeDiff+WoW Backtest Report",
        "",
        f"- Weeks tested: {len(df)}",
        f"- Noise gate (auto_todos <= 20): {'PASS' if noise_ok else 'FAIL'}",
        f"- Median runtime: {median_runtime:.2f} ms",
        f"- Median payload size: {median_payload_kb:.2f} KB",
        "",
        "## Per-week Summary",
        "",
        df.to_markdown(index=False),
        "",
        "## Suggested Threshold Tuning",
        "",
    ]

    if not noise_ok:
        md_lines.append("- Consider increasing `pct_change_floor` by 2-4 points and/or `city_contrib_floor` by 0.01.")
    else:
        md_lines.append("- Current thresholds produce bounded todo counts. Keep as baseline and monitor.")
    if median_payload_kb > 250:
        md_lines.append("- Payload is heavy; cap campaign/adgroup insight lengths further.")
    else:
        md_lines.append("- Payload size is within practical limits for frontend rendering.")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
