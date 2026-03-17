"use client";
import { useState, useEffect } from "react";
import { api, Comment, Task } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface CompareRow {
  cw: number;
  lw: number;
  baseline_avg?: number;
  cw_vs_lw_pct: number;
  cw_vs_baseline_pct?: number;
}

interface ReportCardProps {
  week: string;
  summary: string;
  metrics: {
    installs: number;
    cost: number;
    clicks: number;
  };
  wowGrowth?: number;
  autoTodos?: Array<{
    level: string;
    entity: string;
    city?: string;
    campaign?: string;
    issue: string;
    impact_score: number;
    severity: string;
    recommendation: string;
  }>;
  panSummary?: {
    metrics?: Record<string, CompareRow>;
    ratios?: Record<string, CompareRow>;
  };
  networkSummary?: {
    rows: Array<{
      network: string;
      metrics: Record<string, CompareRow>;
      ratios: Record<string, CompareRow>;
    }>;
  };
  significantChanges?: Array<{
    level: string;
    entity: string;
    significance?: {
      delta_installs?: number;
      pct_change?: number;
      zscore?: number;
      impact_score?: number;
    };
    campaigns_to_check?: Array<{
      campaign: string;
      contribution?: {
        install_delta?: number;
        share_of_entity_delta_pct?: number;
      };
      adgroups_to_check?: Array<{
        ad_group: string;
        contribution?: {
          install_delta?: number;
          share_of_campaign_delta_pct?: number;
        };
      }>;
    }>;
  }>;
  topWastedSpendCandidates?: Array<{
    entity: string;
    city: string;
    cw_cost: number;
    cw_installs: number;
    cti_delta_pct: number;
    reason: string;
  }>;
}

const slugify = (value: string) =>
  value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

const pctText = (value: number) => `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
const valueText = (key: string, value: number) =>
  key.includes("cost") || key.includes("cpc") || key.includes("cpm")
    ? value.toLocaleString(undefined, { maximumFractionDigits: 3 })
    : value.toLocaleString(undefined, { maximumFractionDigits: 2 });

const labelize = (key: string) => key.toUpperCase();

const ReportCard = ({
  week,
  summary,
  metrics,
  wowGrowth,
  autoTodos = [],
  panSummary,
  networkSummary,
  significantChanges = [],
  topWastedSpendCandidates = [],
}: ReportCardProps) => {
  const [showComments, setShowComments] = useState(false);
  const [showTodo, setShowTodo] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newComment, setNewComment] = useState("");
  const [openSections, setOpenSections] = useState({
    pan: true,
    network: true,
    significant: true,
    wasted: true,
  });

  useEffect(() => {
    if (showComments) {
      api.getComments(week).then(setComments);
    }
  }, [showComments, week]);

  useEffect(() => {
    if (showTodo) {
      api.getTasks(week).then(setTasks);
    }
  }, [showTodo, week]);

  const handleAddComment = async (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && newComment.trim()) {
      const comment: Comment = {
        report_id: week,
        user_id: "current_user",
        text: newComment,
        timestamp: new Date().toISOString(),
      };
      await api.addComment(comment);
      setComments([...comments, comment]);
      setNewComment("");
    }
  };

  const handleToggleTask = async (taskId: string, isCompleted: boolean) => {
    await api.updateTaskStatus(taskId, isCompleted);
    setTasks(tasks.map((t) => (t.id === taskId ? { ...t, is_completed: isCompleted } : t)));
  };

  const toggleSection = (key: keyof typeof openSections) =>
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));

  const autoFromTasks = tasks
    .filter((t) => t.is_auto_generated)
    .map((t) => (t.meta as unknown as ReportCardProps["autoTodos"][number]));
  const generatedTodos = autoTodos.length > 0 ? autoTodos : autoFromTasks;
  const manualTasks = tasks.filter((t) => !t.is_auto_generated);
  const todoCount = generatedTodos.length + manualTasks.length;

  const summaryText = summary?.replace(/<b>/g, "**").replace(/<\/b>/g, "**") || "";
  const panMetricRows = panSummary?.metrics ? Object.entries(panSummary.metrics) : [];
  const panRatioRows = panSummary?.ratios ? Object.entries(panSummary.ratios) : [];

  return (
    <div className="card fade-in">
      <div className="card-header">
        <h3 className="card-title">Week {week}</h3>
        {wowGrowth !== undefined && (
          <div style={{ color: wowGrowth >= 0 ? "var(--success)" : "var(--danger)", fontWeight: "bold" }}>
            {wowGrowth >= 0 ? "+" : ""}
            {wowGrowth}% WoW
          </div>
        )}
      </div>

      <div
        className="ai-summary markdown-body"
        style={{
          color: "var(--text-dim)",
          fontSize: "0.95rem",
          lineHeight: "1.6",
          marginBottom: "1.25rem",
          wordBreak: "break-word",
        }}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{summaryText}</ReactMarkdown>
      </div>

      {panMetricRows.length > 0 && (
        <div style={{ marginTop: "1rem", background: "rgba(0,0,0,0.2)", borderRadius: "0.5rem", padding: "0.9rem" }}>
          <button className="action-btn" onClick={() => toggleSection("pan")} style={{ marginBottom: "0.6rem" }}>
            {openSections.pan ? "▼" : "▶"} Pan Metrics & Ratios (CW vs LW vs Avg)
          </button>
          {openSections.pan && (
            <>
              <div style={{ overflowX: "auto", marginBottom: "0.8rem" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left", paddingBottom: "0.35rem" }}>Metric</th>
                      <th>CW</th>
                      <th>LW</th>
                      <th>3W Avg</th>
                      <th>CW vs LW</th>
                      <th>CW vs Avg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {panMetricRows.map(([k, v]) => (
                      <tr key={`metric-${k}`}>
                        <td>{labelize(k)}</td>
                        <td>{valueText(k, v.cw)}</td>
                        <td>{valueText(k, v.lw)}</td>
                        <td>{valueText(k, v.baseline_avg || 0)}</td>
                        <td style={{ color: v.cw_vs_lw_pct >= 0 ? "var(--success)" : "var(--danger)" }}>{pctText(v.cw_vs_lw_pct)}</td>
                        <td style={{ color: (v.cw_vs_baseline_pct || 0) >= 0 ? "var(--success)" : "var(--danger)" }}>{pctText(v.cw_vs_baseline_pct || 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {panRatioRows.length > 0 && (
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left", paddingBottom: "0.35rem" }}>Ratio</th>
                        <th>CW</th>
                        <th>LW</th>
                        <th>3W Avg</th>
                        <th>CW vs LW</th>
                        <th>CW vs Avg</th>
                      </tr>
                    </thead>
                    <tbody>
                      {panRatioRows.map(([k, v]) => (
                        <tr key={`ratio-${k}`}>
                          <td>{labelize(k)}</td>
                          <td>{valueText(k, v.cw)}</td>
                          <td>{valueText(k, v.lw)}</td>
                          <td>{valueText(k, v.baseline_avg || 0)}</td>
                          <td style={{ color: v.cw_vs_lw_pct >= 0 ? "var(--success)" : "var(--danger)" }}>{pctText(v.cw_vs_lw_pct)}</td>
                          <td style={{ color: (v.cw_vs_baseline_pct || 0) >= 0 ? "var(--success)" : "var(--danger)" }}>{pctText(v.cw_vs_baseline_pct || 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {networkSummary?.rows?.length ? (
        <div style={{ marginTop: "1rem", background: "rgba(0,0,0,0.2)", borderRadius: "0.5rem", padding: "0.9rem" }}>
          <button className="action-btn" onClick={() => toggleSection("network")} style={{ marginBottom: "0.6rem" }}>
            {openSections.network ? "▼" : "▶"} Network Comparison (SEARCH + YOUTUBE + DISPLAY)
          </button>
          {openSections.network && (
            <div style={{ display: "grid", gap: "0.6rem" }}>
              {networkSummary.rows.map((row) => (
                <div key={row.network} style={{ border: "1px solid var(--border)", borderRadius: "0.5rem", padding: "0.6rem" }}>
                  <div style={{ fontWeight: 600, marginBottom: "0.35rem" }}>{row.network}</div>
                  <div style={{ fontSize: "0.82rem", color: "var(--text-dim)" }}>
                    Installs {valueText("installs", row.metrics.installs?.cw || 0)} vs {valueText("installs", row.metrics.installs?.lw || 0)} ({pctText(row.metrics.installs?.cw_vs_lw_pct || 0)}) | CTR {valueText("ctr", row.ratios.ctr?.cw || 0)} vs {valueText("ctr", row.ratios.ctr?.lw || 0)} ({pctText(row.ratios.ctr?.cw_vs_lw_pct || 0)})
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {significantChanges.length > 0 && (
        <div style={{ marginTop: "1rem", background: "rgba(0,0,0,0.2)", borderRadius: "0.5rem", padding: "0.9rem" }}>
          <button className="action-btn" onClick={() => toggleSection("significant")} style={{ marginBottom: "0.6rem" }}>
            {openSections.significant ? "▼" : "▶"} Significant Changes (City → Campaign → Ad Group)
          </button>
          {openSections.significant && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
              {significantChanges.slice(0, 10).map((sc, idx) => (
                <div id={`insight-city-${slugify(week)}-${slugify(sc.entity)}`} key={`sig-${idx}`} style={{ border: "1px solid var(--border)", borderRadius: "0.5rem", padding: "0.6rem" }}>
                  <div style={{ fontWeight: 600 }}>{sc.entity}</div>
                  <div style={{ color: "var(--text-dim)", fontSize: "0.82rem", marginBottom: "0.4rem" }}>
                    ΔInstalls {sc.significance?.delta_installs ?? 0} | {pctText(sc.significance?.pct_change ?? 0)} | z={sc.significance?.zscore ?? 0}
                  </div>
                  {(sc.campaigns_to_check || []).slice(0, 4).map((cmp, ci) => (
                    <div id={`insight-campaign-${slugify(week)}-${slugify(cmp.campaign)}`} key={`cmp-${ci}`} style={{ marginTop: "0.35rem", paddingLeft: "0.35rem", borderLeft: "2px solid var(--border)" }}>
                      <div style={{ fontSize: "0.85rem", fontWeight: 600 }}>{cmp.campaign}</div>
                      <div style={{ fontSize: "0.8rem", color: "var(--text-dim)" }}>
                        Campaign contribution: {cmp.contribution?.install_delta ?? 0} installs ({cmp.contribution?.share_of_entity_delta_pct ?? 0}%)
                      </div>
                      <div style={{ fontSize: "0.8rem", marginTop: "0.2rem" }}>
                        Check adgroups: {(cmp.adgroups_to_check || []).slice(0, 3).map((a) => `${a.ad_group} (${a.contribution?.share_of_campaign_delta_pct ?? 0}%)`).join(" | ")}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {topWastedSpendCandidates.length > 0 && (
        <div style={{ marginTop: "1rem", background: "rgba(0,0,0,0.2)", borderRadius: "0.5rem", padding: "0.9rem" }}>
          <button className="action-btn" onClick={() => toggleSection("wasted")} style={{ marginBottom: "0.6rem" }}>
            {openSections.wasted ? "▼" : "▶"} Top Wasted Spend Candidates
          </button>
          {openSections.wasted && (
            <div style={{ display: "grid", gap: "0.4rem" }}>
              {topWastedSpendCandidates.map((w, i) => (
                <div key={`w-${i}`} style={{ border: "1px solid var(--border)", borderRadius: "0.4rem", padding: "0.5rem", fontSize: "0.82rem" }}>
                  <b>{w.entity}</b> ({w.city}) | Cost {valueText("cost", w.cw_cost)} | Installs {w.cw_installs} | CTI Δ {pctText(w.cti_delta_pct)} | {w.reason}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="card-actions">
        <button className="action-btn" onClick={() => setShowComments(!showComments)}>
          <span style={{ fontSize: "1.2rem" }}>💬</span> Comment ({comments.length})
        </button>
        <button className="action-btn" onClick={() => setShowTodo(!showTodo)}>
          <span style={{ fontSize: "1.2rem" }}>📝</span> To-do List ({todoCount})
        </button>
      </div>

      {showComments && (
        <div style={{ marginTop: "1rem", padding: "1rem", background: "rgba(0,0,0,0.2)", borderRadius: "0.5rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1rem" }}>
            {comments.map((c, i) => (
              <div key={i} style={{ fontSize: "0.9rem" }}>
                <span style={{ color: "var(--primary)", fontWeight: "500" }}>{c.user_id}: </span>
                {c.text}
              </div>
            ))}
          </div>
          <input
            type="text"
            placeholder="Add a comment..."
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            onKeyDown={handleAddComment}
            style={{
              width: "100%",
              padding: "0.5rem",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid var(--border)",
              borderRadius: "0.25rem",
              color: "white",
            }}
          />
        </div>
      )}

      {showTodo && (
        <div style={{ marginTop: "1rem", padding: "1rem", background: "rgba(0,0,0,0.2)", borderRadius: "0.5rem" }}>
          {generatedTodos.length > 0 && (
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "0.5rem" }}>Auto To-dos (Significant Changes)</div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {generatedTodos.map((t, i) => {
                  const targetId =
                    t.level === "campaign"
                      ? `insight-campaign-${slugify(week)}-${slugify(t.entity)}`
                      : t.level === "city"
                        ? `insight-city-${slugify(week)}-${slugify(t.entity)}`
                        : "";
                  return (
                    <div key={`auto-${i}`} style={{ fontSize: "0.85rem", border: "1px solid var(--border)", borderRadius: "0.4rem", padding: "0.5rem" }}>
                      <div style={{ fontWeight: 600 }}>
                        [{t.severity.toUpperCase()}] {t.level}: {t.entity}
                      </div>
                      <div style={{ color: "var(--text-dim)" }}>{t.issue}</div>
                      <div style={{ marginTop: "0.2rem" }}>{t.recommendation}</div>
                      {targetId && (
                        <a href={`#${targetId}`} style={{ color: "var(--primary)", fontSize: "0.8rem" }}>
                          Jump to related insight
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {manualTasks.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {manualTasks.map((t) => (
                <div key={t.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.9rem" }}>
                  <input
                    type="checkbox"
                    checked={t.is_completed}
                    onChange={(e) => t.id && handleToggleTask(t.id, e.target.checked)}
                  />
                  <span style={{ textDecoration: t.is_completed ? "line-through" : "none", color: t.is_completed ? "var(--text-dim)" : "inherit" }}>
                    {t.description}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ReportCard;
