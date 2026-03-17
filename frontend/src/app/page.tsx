"use client";
import { useEffect, useState } from 'react';
import ReportCard from "@/components/ReportCard";
import { api, Report } from '@/lib/api';

export default function Home() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedWeek, setSelectedWeek] = useState<string>("ALL");
  const [toast, setToast] = useState<{ type: "info" | "success" | "error"; message: string } | null>(null);

  const showToast = (type: "info" | "success" | "error", message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  };

  useEffect(() => {
    api.getReports()
      .then((historical) => setReports(historical))
      .catch(() => {
        setReports([]);
        showToast("error", "Could not load reports from storage.");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      {toast && (
        <div
          style={{
            marginBottom: "1rem",
            padding: "0.75rem 1rem",
            borderRadius: "0.5rem",
            border: "1px solid var(--border)",
            background:
              toast.type === "success"
                ? "rgba(16,185,129,0.15)"
                : toast.type === "error"
                  ? "rgba(239,68,68,0.15)"
                  : "rgba(59,130,246,0.15)",
            color:
              toast.type === "success"
                ? "var(--success)"
                : toast.type === "error"
                  ? "var(--danger)"
                  : "var(--primary)",
            fontWeight: 600,
          }}
        >
          {toast.message}
        </div>
      )}
      <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: '700' }}>Marketing Performance</h1>
          <p style={{ color: 'var(--text-dim)', marginTop: '0.5rem' }}>
            Live performance tracking and AI-synthesized insights.
          </p>
        </div>
        <button
          disabled={refreshing}
          onClick={() => {
            setRefreshing(true);
            api.refreshLatestReport()
              .then((result) => {
                if (result.status === "skipped") {
                  showToast("info", "Latest week report already available in storage.");
                } else {
                  showToast("success", "Latest week report generated and saved.");
                }
                setSelectedWeek(result.week_id);
                return api.getReports();
              })
              .then((historical) => setReports(historical))
              .catch(() => showToast("error", "Could not refresh latest week report."))
              .finally(() => setRefreshing(false));
          }}
          className="action-btn"
          style={{
            background: refreshing ? 'var(--secondary)' : 'var(--primary)',
            color: 'white',
            padding: '0.5rem 1rem',
            borderRadius: '0.5rem',
            cursor: refreshing ? 'not-allowed' : 'pointer'
          }}
        >
          {refreshing ? "Refreshing..." : "Refresh All"}
        </button>
      </header>

      {loading ? (
        <div style={{ color: 'var(--text-dim)' }}>Loading data...</div>
      ) : (
        <>
          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '600' }}>Historical Reports</h2>
              <select
                value={selectedWeek}
                onChange={(e) => setSelectedWeek(e.target.value)}
                style={{ background: 'var(--bg-card)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: '0.4rem', padding: '0.4rem 0.6rem' }}
              >
                <option value="ALL">All Weeks</option>
                {reports
                  .map((r) => r.week)
                  .sort()
                  .reverse()
                  .map((week) => (
                    <option key={week} value={week}>
                      {week}
                    </option>
                  ))}
              </select>
            </div>
            <div className="report-grid">
              {reports.length === 0 ? (
                <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '4rem', background: 'var(--bg-card)', borderRadius: '1rem' }}>
                  No historical reports found.
                </div>
              ) : (
                reports
                  .filter((report) => selectedWeek === "ALL" || report.week === selectedWeek)
                  .sort((a, b) => b.week.localeCompare(a.week))
                  .map((report) => (
                  <ReportCard
                    key={report.week}
                    week={report.week}
                    summary={report.summary}
                    autoTodos={report.auto_todos || []}
                    panSummary={report.pan_summary}
                    networkSummary={report.network_summary}
                    significantChanges={report.significant_changes || []}
                    topWastedSpendCandidates={report.top_wasted_spend_candidates || []}
                    metrics={{
                      installs: report.installs,
                      cost: report.cost,
                      clicks: report.clicks
                    }}
                    wowGrowth={report.wow_growth}
                  />
                ))
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
