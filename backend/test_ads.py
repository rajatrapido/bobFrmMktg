import os
os.environ["GOOGLE_ADS_TRANSPORT"] = "rest"
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__name__)))

from app.services.ads_service import AdsService

def test_ads():
    print("Initializing AdsService...")
    service = AdsService()
    print("AdsService initialized.")
    
    today = datetime.now()
    end_date = today - timedelta(days=today.weekday() + 1)
    start_date = end_date - timedelta(days=6*4) # 4 weeks
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    print(f"Fetching performance data from {start_date_str} to {end_date_str}...")
    df = service.fetch_performance_data(start_date_str, end_date_str)
    
    print(f"Fetch completed. Rows: {len(df)}")
    if not df.empty:
        print(df.head())
    else:
        print("DataFrame is empty.")

if __name__ == "__main__":
    test_ads()
