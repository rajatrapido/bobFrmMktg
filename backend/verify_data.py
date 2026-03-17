import asyncio
from app.services.report_engine import ReportEngine

def test_w08():
    # Force mock auth locally
    import os
    os.environ["USE_MOCK_AUTH"] = "true"
    
    engine = ReportEngine()
    # W08 is Feb 16 to Feb 22. W07 is Feb 09 to Feb 15.
    # To get W08 and W07, start_date = 2026-02-09, end_date = 2026-02-22
    
    start_date_str = '2026-02-09'
    end_date_str = '2026-02-22'
    
    print(f"Fetching performance data from {start_date_str} to {end_date_str}...")
    df_raw = engine.ads_service.fetch_performance_data(start_date_str, end_date_str)
    print(f"Total raw rows: {len(df_raw)}")
    
    df_prepared = engine.report_service.prepare_data(df_raw)
    
    target_week_str = '2026-W08'
    
    # We will pass None for changes to isolate numeric accuracy first
    report_data = engine.report_service.generate_weekly_report(df_prepared, None, target_week_str)
    
    if report_data:
        print("\n--- RESULTS FOR W08 ---")
        print(f"Installs: {report_data['installs']} (Expected: 733705)")
        print(f"Cost: {report_data['cost']} (Expected: 19553374.61)")
        print(f"Impressions: {report_data['impressions']} (Expected: 284808896)")
        print(f"Clicks: {report_data['clicks']} (Expected: 4060966)")
    else:
        print("Failed to generate report data.")

if __name__ == "__main__":
    test_w08()
