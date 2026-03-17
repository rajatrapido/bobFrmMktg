## [2026-02-28 17:50] - Integrated Reporting Engine & AI Summaries

### 💡 Overview
We've significantly enhanced the backend architecture to automate and improve our marketing performance reporting. The system now automatically fetches live Google Ads data, processes it to identify key trends across different cities and services, and uses Google's AI (Gemini) to generate easy-to-read, professional summaries. We also built a scheduler so these reports are generated automatically every Monday morning!

### 🛠️ Technical Details
- **Architecture Shift**: Migrated core reporting logic from a standalone script (`performace_report_updated.py`) into a structured FastAPI backend.
- **Service Segregation**: 
  - `AdsService`: Handles communication with the Google Ads API for data ingestion (`fetch_performance_data`).
  - `ReportService`: Processes the raw pandas DataFrames, extracts granular features (City, Service from Campaign Names), and calculates Week-over-Week (WoW) deltas.
  - `AIService`: Integrates with the `google-generativeai` SDK (Gemini 2.5 Flash) to generate HTML summaries of the performance metrics.
  - `FirestoreService`: Manages data persistence (Reports, Comments, Tasks) in Firebase.
- **Reporting Engine (`ReportEngine`)**: Orchestrates the workflow between the segregated services. It can generate reports dynamically for live viewing without saving, or run background tasks to generate and save the weekly reports to the database.
- **Automation**: Implemented `BackgroundScheduler` in `main.py` (APScheduler) to run the `scheduled_report_job` every Monday at 9:00 AM.
- **Data Model**: The generated reports now include aggregated metrics (Installs, Cost, Clicks, Impressions, WoW Growth) alongside the AI-generated HTML summary and are stored persistently.

---
