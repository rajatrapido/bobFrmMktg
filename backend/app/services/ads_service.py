import os
import json
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from google.cloud import storage
from google.oauth2 import service_account
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv
from google.cloud import firestore

# Force REST transport at the module level for all clients
os.environ["GOOGLE_ADS_TRANSPORT"] = "rest"

load_dotenv()

class AdsService:
    def __init__(self):
        self.customer_id = os.getenv("CUSTOMER_ID") or os.getenv("GOOGLE_LOGIN_CUSTOMER_ID")
        self.ads_client = None
        self.use_mock = False
        self.db = firestore.Client() if os.getenv("USE_MOCK_AUTH", "False").lower() != "true" else None
        
        try:
            config = self._load_credentials()
            
            # Explicitly disabling proto-plus for stability in this environment
            config["use_proto_plus"] = False
            
            self.ads_client = GoogleAdsClient.load_from_dict(config)
            print("Google Ads client initialized (Transport: REST forced via ENV).")
        except Exception as e:
            print(f"Ads client initialization failed: {e}. Using mock data fallback.")
            self.use_mock = True

    @staticmethod
    def _normalize_network_type(value):
        """
        Normalize ad network type values to human-readable names.
        API sometimes returns enums or numeric codes depending on transport.
        """
        enum_map = {
            2: "SEARCH",
            3: "SEARCH_PARTNERS",
            4: "CONTENT",
            5: "SHOPPING",
            8: "YOUTUBE",
            9: "MIXED",
            10: "HOTEL",
            11: "SMART",
        }
        if value is None:
            return "UNKNOWN"
        try:
            # Enum with .name
            if hasattr(value, "name"):
                return value.name
            # Numeric code as int/str
            if isinstance(value, (int, float)):
                return enum_map.get(int(value), str(int(value)))
            if isinstance(value, str) and value.isdigit():
                return enum_map.get(int(value), value)
            return str(value)
        except Exception:
            return str(value)

    def _get_conversion_action_map(self, ga_service, customer_id):
        """
        Map conversion action resource names to unified labels used in reports.
        Uses conversion action names (not IDs) to avoid drift when IDs change.
        """
        target_action_names = {
            "Rapido - Best Bike Taxi App (Android) First open": "Installs",
            "(AppsFlyer) Registration": "Registrations",
            "platform_ride_completed-firebase_android": "FTUs",
        }
        quoted_action_names = ", ".join(f"'{name}'" for name in target_action_names.keys())
        query = f"""
            SELECT conversion_action.resource_name, conversion_action.name
            FROM conversion_action
            WHERE conversion_action.name IN ({quoted_action_names})
        """
        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            mapping = {}
            for r in response:
                action_name = r.conversion_action.name
                label = target_action_names.get(action_name)
                if label:
                    mapping[r.conversion_action.resource_name] = label
            return mapping
        except Exception as e:
            print(f"[Error] Failed to fetch conversion action mapping by name: {e}")
            return {}

    def _load_credentials(self):
        # Try loading from Firestore dynamic config first
        if self.db:
            try:
                doc_ref = self.db.collection('system_config').document('adwords_auth')
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    refresh_token = data.get('refresh_token')
                    if refresh_token:
                        print("Loaded Adwords credentials from Firestore")
                        return {
                            "developer_token": os.getenv("GOOGLE_DEVELOPER_TOKEN", ""),
                            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                            "refresh_token": refresh_token,
                            "login_customer_id": os.getenv("GOOGLE_LOGIN_CUSTOMER_ID", ""),
                        }
            except Exception as e:
                print(f"Firestore credential lookup failed: {e}. Falling back to yaml.")
                    
        # Fallback to yaml
        print("Falling back to local yaml configuration")
        yaml_path = "/Users/E2005/projects/bobfrmmktg/backend/app/google-ads.yaml"
        with open(yaml_path, "r") as f:
            return yaml.safe_load(f)

    def fetch_live_summary(self, start_date_str, end_date_str):
        """
        Optimized campaign-level fetch for the 'Live' view.
        """
        if self.use_mock:
            print("Using mock data fallback for live summary.")
            return self._fetch_mock_data(start_date_str, end_date_str)

        print(f"--- FETCHING LIVE SUMMARY (CAMPAIGN LEVEL) FROM {start_date_str} to {end_date_str} ---")
        ga_service = self.ads_client.get_service("GoogleAdsService")
        conversion_map = self._get_conversion_action_map(ga_service, self.customer_id)

        # 1. Fetch Performance
        query_perf = f"""
            SELECT campaign.id, campaign.name, campaign.status, metrics.impressions, 
                   metrics.clicks, metrics.cost_micros, segments.date
            FROM campaign
            WHERE campaign.status IN ('ENABLED', 'PAUSED') AND metrics.impressions > 0
                  AND segments.date BETWEEN '{start_date_str}' AND '{end_date_str}'
        """
        
        try:
            response = ga_service.search(customer_id=self.customer_id, query=query_perf)
            data = []
            for r in response:
                data.append({
                    "Date": r.segments.date,
                    "Campaign ID": str(r.campaign.id),
                    "Campaign Name": r.campaign.name,
                    "Campaign Status": str(r.campaign.status),
                    "Impressions": r.metrics.impressions,
                    "Clicks": r.metrics.clicks,
                    "Cost": max(0, r.metrics.cost_micros / 1_000_000)
                })
            df = pd.DataFrame(data)
            
            if df.empty:
                print("[Live] No rows returned from campaign query.")
                return df

            # 2. Fetch Conversions (Fast campaign-level fetch)
            query_conv = f"""
                SELECT segments.date, campaign.id, segments.conversion_action, metrics.all_conversions
                FROM campaign
                WHERE metrics.all_conversions > 0
                      AND segments.date BETWEEN '{start_date_str}' AND '{end_date_str}'
            """
            response_conv = ga_service.search(customer_id=self.customer_id, query=query_conv)
            conv_data = []
            for r in response_conv:
                conv_data.append({
                    "Date": r.segments.date,
                    "Campaign ID": str(r.campaign.id),
                    "Conversion Action Resource Name": r.segments.conversion_action,
                    "Value": r.metrics.all_conversions
                })
            
            if conv_data:
                df_conv = pd.DataFrame(conv_data)
                print(f"[Live] Found {len(df_conv)} raw conversion rows.")
                print(f"[Live] Unique conversion actions in data: {df_conv['Conversion Action Resource Name'].unique().tolist()}")

                # Map by conversion action name (stable) instead of hardcoded IDs
                df_conv['ActionType'] = df_conv['Conversion Action Resource Name'].map(conversion_map)
                mapped_count = df_conv['ActionType'].notna().sum()
                print(f"[Live] Mapped {mapped_count} conversion rows.")
                # Only keep rows we mapped
                df_conv = df_conv.dropna(subset=['ActionType'])
                
                if not df_conv.empty:
                    df_pivoted = df_conv.pivot_table(index=['Date', 'Campaign ID'], 
                                                     columns='ActionType', 
                                                     values='Value', 
                                                     aggfunc='sum').reset_index()
                    
                    df = pd.merge(df, df_pivoted, on=['Date', 'Campaign ID'], how='left').fillna(0)
                    
                    for col in ['Installs', 'Registrations', 'FTUs']:
                        if col in df.columns:
                            df[col] = df[col].astype(int)
                        else:
                            df[col] = 0

            print(f"[Live] Success: Processed {len(df)} rows with metrics.")
            return df
        except Exception as e:
            print(f"[Error] Failed to fetch live summary: {e}")
            return pd.DataFrame()

    def fetch_performance_data(self, start_date_str, end_date_str, min_impressions=1):
        """
        Fetches granular ad-group level data for actionable insights representation.
        We request segments.ad_network_type, campaign name, ad group name, and metrics.
        """
        if self.use_mock:
            return self._fetch_mock_data(start_date_str, end_date_str)

        min_impressions = max(1, int(min_impressions))
        print(f"--- FETCHING GRANULAR PERFORMANCE FROM {start_date_str} to {end_date_str} (min_impressions={min_impressions}) ---")
        ga_service = self.ads_client.get_service("GoogleAdsService")
        conversion_map = self._get_conversion_action_map(ga_service, self.customer_id)

        # 1. Fetch Performance (Ad Group Level)
        query_perf = f"""
            SELECT campaign.id, campaign.name, campaign.status, 
                   ad_group.id, ad_group.name, segments.ad_network_type,
                   metrics.impressions, metrics.clicks, metrics.cost_micros, segments.date
            FROM ad_group
            WHERE campaign.status IN ('ENABLED', 'PAUSED') AND metrics.impressions >= {min_impressions}
                  AND segments.date BETWEEN '{start_date_str}' AND '{end_date_str}'
        """
        
        try:
            response = ga_service.search_stream(customer_id=self.customer_id, query=query_perf)
            data = []
            for batch in response:
                for r in batch.results:
                    data.append({
                        "Date": r.segments.date,
                        "Campaign ID": str(r.campaign.id),
                        "Campaign Name": r.campaign.name,
                        "Campaign Status": r.campaign.status.name if hasattr(r.campaign.status, 'name') else str(r.campaign.status),
                        "Ad Group ID": str(r.ad_group.id),
                        "Ad Group Name": r.ad_group.name,
                        "Ad Network Type": self._normalize_network_type(r.segments.ad_network_type),
                        "Impressions": r.metrics.impressions,
                        "Clicks": r.metrics.clicks,
                        "Cost": max(0, r.metrics.cost_micros / 1_000_000)
                    })
            df = pd.DataFrame(data)
            
            if df.empty:
                print("[Insights] No rows returned from ad_group query.")
                return df

            # 2. Fetch Conversions (Ad Group Level)
            query_conv = f"""
                SELECT segments.date, campaign.id, ad_group.id, segments.ad_network_type,
                       segments.conversion_action, metrics.all_conversions
                FROM ad_group
                WHERE metrics.all_conversions > 0
                      AND segments.date BETWEEN '{start_date_str}' AND '{end_date_str}'
            """
            response_conv = ga_service.search_stream(customer_id=self.customer_id, query=query_conv)
            conv_data = []
            for batch in response_conv:
                for r in batch.results:
                    conv_data.append({
                        "Date": r.segments.date,
                        "Campaign ID": str(r.campaign.id),
                        "Ad Group ID": str(r.ad_group.id),
                        "Ad Network Type": self._normalize_network_type(r.segments.ad_network_type),
                        "Conversion Action Resource Name": r.segments.conversion_action,
                        "Value": r.metrics.all_conversions
                    })
            
            if conv_data:
                df_conv = pd.DataFrame(conv_data)

                # Conversion Mapping by action name
                df_conv['ActionType'] = df_conv['Conversion Action Resource Name'].map(conversion_map)
                df_conv = df_conv.dropna(subset=['ActionType'])
                
                if not df_conv.empty:
                    df_pivoted = df_conv.pivot_table(index=['Date', 'Campaign ID', 'Ad Group ID', 'Ad Network Type'], 
                                                     columns='ActionType', 
                                                     values='Value', 
                                                     aggfunc='sum').reset_index()
                    
                    df = pd.merge(df, df_pivoted, on=['Date', 'Campaign ID', 'Ad Group ID', 'Ad Network Type'], how='left').fillna(0)
                    
                    for col in ['Installs', 'Registrations', 'FTUs']:
                        if col in df.columns:
                            df[col] = df[col].astype(int)
                        else:
                            df[col] = 0

            print(f"[Insights] Success: Processed {len(df)} rows with granular metrics.")
            return df
        except Exception as e:
            print(f"[Error] Failed to fetch granular metrics: {e}")
            return pd.DataFrame()

    def fetch_change_history(self, start_date_str, end_date_str, limit=500):
        """
        Extracted directly from performace_report_updated.py via Google Ads API.
        """
        if self.use_mock:
            return pd.DataFrame()

        print(f"--- FETCHING CHANGE HISTORY FROM {start_date_str} to {end_date_str} ---")
        ga_service = self.ads_client.get_service("GoogleAdsService")
        
        # We need a pb json serialization helper locally
        from google.protobuf.json_format import MessageToDict
        
        query = f"""
            SELECT change_event.change_date_time, change_event.user_email, change_event.client_type,
                   change_event.change_resource_type, change_event.old_resource, change_event.new_resource,
                   change_event.campaign, change_event.ad_group
            FROM change_event
            WHERE change_event.change_date_time >= '{start_date_str} 00:00:00'
                  AND change_event.change_date_time <= '{end_date_str} 23:59:59'
            ORDER BY change_event.change_date_time DESC
            LIMIT {int(limit)}
        """

        def get_pretty_diff(d1, d2, path=""):
            diffs = []
            for k in sorted(list(set(d1.keys()) | set(d2.keys()))):
                new_path, v1, v2 = f"{path}.{k}" if path else k, d1.get(k), d2.get(k)
                if v1 is None and v2 is not None:
                    str_v2 = str(v2)
                    diffs.append(f"[+] Added **{new_path}**" if isinstance(v2, dict) or len(str_v2) > 100 else f"[+] Added **{new_path}**: '{str_v2}'")
                elif v1 is not None and v2 is None:
                    diffs.append(f"[-] Removed **{new_path}**")
                elif isinstance(v1, dict) and isinstance(v2, dict):
                    diffs.extend(get_pretty_diff(v1, v2, path=new_path))
                elif v1 != v2:
                    str_v1, str_v2 = str(v1), str(v2)
                    diffs.append(f"[~] Changed **{new_path}**" if len(str_v1) > 100 or len(str_v2) > 100 else f"[~] Changed **{new_path}**: '{str_v1}' -> '{str_v2}'")
            return diffs

        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)
            results = []
            for r in response:
                campaign_res = getattr(r.change_event, 'campaign', '')
                ad_group_res = getattr(r.change_event, 'ad_group', '')
                
                # We need to extract just the campaign/ad_group names if possible, but the API may just return the resource path.
                # In the original script, it attempts to map these or uses them as string paths.
                
                try:
                    old_dict = MessageToDict(r.change_event.old_resource._pb) if hasattr(r.change_event.old_resource, '_pb') else {}
                    new_dict = MessageToDict(r.change_event.new_resource._pb) if hasattr(r.change_event.new_resource, '_pb') else {}
                    changes = "\\n".join(get_pretty_diff(old_dict, new_dict)) or "—"
                except Exception as ex:
                    changes = "Could not parse change diff."

                results.append({
                    "Date": r.change_event.change_date_time[:10],
                    "User": r.change_event.user_email,
                    "Resource": r.change_event.change_resource_type.name if hasattr(r.change_event.change_resource_type, 'name') else str(r.change_event.change_resource_type),
                    "Campaign Resource": campaign_res,
                    "Ad Group Resource": ad_group_res,
                    "Changes": changes
                })
            df = pd.DataFrame(results)
            print(f"[Data] Fetched {len(df)} change event rows.")
            return df
        except Exception as e:
            print(f"[Error] Failed to fetch change history: {e}")
            return pd.DataFrame()

    def _fetch_mock_data(self, start_date_str, end_date_str):
        print("Using mock data.")
        dates = pd.date_range(start=start_date_str, end=end_date_str)
        data = []
        for d in dates:
            data.append({
                "Date": d.strftime('%Y-%m-%d'),
                "Campaign ID": "123",
                "Campaign Name": "Mock Campaign",
                "Campaign Status": "ENABLED",
                "Impressions": 1000,
                "Clicks": 50,
                "Cost": 25.0,
                "Installs": 5,
                "Registrations": 3,
                "FTUs": 1
            })
        return pd.DataFrame(data)
