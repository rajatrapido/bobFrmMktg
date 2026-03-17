import json
import os
from pathlib import Path


STORAGE_ROOT = Path(os.getenv("LOCAL_STORAGE_DIR", "/Users/E2005/projects/bobfrmmktg/backend/storage"))
AGG_WEEKS_DIR = STORAGE_ROOT / "aggregates" / "weeks"
THRESHOLD_DIR = STORAGE_ROOT / "aggregates" / "thresholds"

REQUIRED_WEEK_FILES = [
    "weekly_adgroup.json",
    "weekly_city_metrics.json",
    "weekly_city_network_metrics.json",
    "weekly_city_campaign_metrics.json",
    "weekly_pan_metrics.json",
    "manifest.json",
]

REQUIRED_ADGROUP_COLS = {
    "Week", "City", "Campaign ID", "Campaign_Name", "Ad Group ID", "Ad Group Name",
    "Ad Network Type", "Installs", "Cost", "Impressions", "Clicks",
}

REQUIRED_THRESHOLD_KEYS = {
    "min_impressions", "min_clicks", "min_installs", "impact_floor_ratio",
    "pct_change_floor", "zscore_floor", "city_coverage_target", "city_contrib_floor",
}


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_week_dir(week_dir):
    issues = []
    for filename in REQUIRED_WEEK_FILES:
        if not (week_dir / filename).exists():
            issues.append(f"missing file: {filename}")
    adgroup_path = week_dir / "weekly_adgroup.json"
    if adgroup_path.exists():
        rows = _load_json(adgroup_path)
        if rows:
            cols = set(rows[0].keys())
            missing_cols = REQUIRED_ADGROUP_COLS - cols
            if missing_cols:
                issues.append(f"missing columns in weekly_adgroup.json: {sorted(missing_cols)}")
            neg_metrics = []
            for r in rows[:2000]:
                for metric in ("Installs", "Cost", "Impressions", "Clicks"):
                    if float(r.get(metric, 0)) < 0:
                        neg_metrics.append(metric)
            if neg_metrics:
                issues.append(f"negative metric values found: {sorted(set(neg_metrics))}")
    return issues


def run():
    print("=== verify_timeDiff_wow ===")
    if not AGG_WEEKS_DIR.exists():
        print(f"[FAIL] Missing aggregate weeks directory: {AGG_WEEKS_DIR}")
        return 1

    week_dirs = sorted([p for p in AGG_WEEKS_DIR.iterdir() if p.is_dir()])
    if not week_dirs:
        print("[FAIL] No week aggregates found.")
        return 1

    all_ok = True
    print(f"[INFO] Found {len(week_dirs)} week directories.")
    for week_dir in week_dirs:
        issues = check_week_dir(week_dir)
        if issues:
            all_ok = False
            print(f"[FAIL] {week_dir.name}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"[OK] {week_dir.name}")

    if not THRESHOLD_DIR.exists():
        all_ok = False
        print(f"[FAIL] Missing threshold directory: {THRESHOLD_DIR}")
    else:
        t_files = sorted(THRESHOLD_DIR.glob("*.json"))
        if not t_files:
            all_ok = False
            print("[FAIL] No threshold snapshots found.")
        else:
            latest = t_files[-1]
            payload = _load_json(latest)
            missing = REQUIRED_THRESHOLD_KEYS - set(payload.keys())
            if missing:
                all_ok = False
                print(f"[FAIL] Threshold snapshot {latest.name} missing keys: {sorted(missing)}")
            else:
                print(f"[OK] Threshold snapshot {latest.name}")

    # Basic trend-window readiness: at least 4 weeks available
    if len(week_dirs) < 4:
        all_ok = False
        print(f"[FAIL] Need at least 4 completed weeks for LW/LLW/3W. Found: {len(week_dirs)}")
    else:
        print("[OK] LW/LLW/3W trend window requirement satisfied.")

    # Basic duplicate check by manifest week key
    seen_weeks = set()
    for week_dir in week_dirs:
        manifest_path = week_dir / "manifest.json"
        if manifest_path.exists():
            manifest = _load_json(manifest_path)
            week = manifest.get("week", week_dir.name)
            if week in seen_weeks:
                all_ok = False
                print(f"[FAIL] Duplicate week manifest key detected: {week}")
            seen_weeks.add(week)

    if all_ok:
        print("[PASS] All checks passed.")
        return 0
    print("[FAIL] One or more checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(run())
