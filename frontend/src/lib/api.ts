import { auth } from './firebase';

const BASE_URL = 'http://localhost:8000';

const getHeaders = async () => {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json'
    };
    if (auth.currentUser) {
        const token = await auth.currentUser.getIdToken();
        headers['Authorization'] = `Bearer ${token}`;
    } else if (process.env.NEXT_PUBLIC_USE_MOCK_AUTH === 'true') {
        headers['Authorization'] = `Bearer mock_token`;
    }
    return headers;
};

export interface Report {
    week: string;
    summary: string;
    installs: number;
    cost: number;
    clicks: number;
    impressions: number;
    wow_growth?: number;
    trend_windows?: {
        current_week: string;
        last_week: string;
        baseline_weeks: string[];
    };
    auto_todos?: Array<{
        level: string;
        entity: string;
        city?: string;
        campaign?: string;
        issue: string;
        impact_score: number;
        severity: string;
        recommendation: string;
    }>;
    city_insights?: Array<{
        city: string;
        stats?: {
            delta: number;
            pct_change: number;
            z_score: number;
            significant: boolean;
        };
    }>;
    campaign_insights?: Array<{
        city: string;
        campaign: string;
        stats?: {
            delta: number;
            pct_change: number;
            z_score: number;
            significant: boolean;
        };
    }>;
    pan_summary?: {
        metrics?: Record<string, {
            cw: number;
            lw: number;
            baseline_avg: number;
            cw_vs_lw_pct: number;
            cw_vs_baseline_pct: number;
        }>;
        ratios?: Record<string, {
            cw: number;
            lw: number;
            baseline_avg: number;
            cw_vs_lw_pct: number;
            cw_vs_baseline_pct: number;
        }>;
    };
    network_summary?: {
        rows: Array<{
            network: string;
            metrics: Record<string, {
                cw: number;
                lw: number;
                cw_vs_lw_pct: number;
            }>;
            ratios: Record<string, {
                cw: number;
                lw: number;
                cw_vs_lw_pct: number;
            }>;
        }>;
    };
    significant_changes?: Array<{
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
    top_wasted_spend_candidates?: Array<{
        entity: string;
        city: string;
        cw_cost: number;
        cw_installs: number;
        cti_delta_pct: number;
        reason: string;
    }>;
}

export interface Comment {
    report_id: string;
    user_id: string;
    text: string;
    timestamp: string;
}

export interface Task {
    id?: string;
    report_id: string;
    description: string;
    is_completed: boolean;
    due_date?: string;
    is_auto_generated?: boolean;
    meta?: Record<string, unknown>;
}

export interface RefreshLatestResponse {
    status: "skipped" | "generated" | "error";
    source: "storage" | "generated";
    week_id: string;
    message: string;
    reason?: string;
    generated_at?: string;
    report_created_at?: string;
    detail?: string;
}

export const api = {
    getReports: async (): Promise<Report[]> => {
        const res = await fetch(`${BASE_URL}/reports`, { headers: await getHeaders() });
        return res.json();
    },

    getLiveReport: async (): Promise<Report> => {
        const res = await fetch(`${BASE_URL}/reports/live`, { headers: await getHeaders() });
        return res.json();
    },

    getComments: async (weekId: string): Promise<Comment[]> => {
        const res = await fetch(`${BASE_URL}/reports/${weekId}/comments`, { headers: await getHeaders() });
        return res.json();
    },

    addComment: async (comment: Comment) => {
        const res = await fetch(`${BASE_URL}/comments`, {
            method: 'POST',
            headers: await getHeaders(),
            body: JSON.stringify(comment),
        });
        return res.json();
    },

    getTasks: async (weekId: string): Promise<Task[]> => {
        const res = await fetch(`${BASE_URL}/reports/${weekId}/tasks`, { headers: await getHeaders() });
        return res.json();
    },

    addTask: async (task: Task) => {
        const res = await fetch(`${BASE_URL}/tasks`, {
            method: 'POST',
            headers: await getHeaders(),
            body: JSON.stringify(task),
        });
        return res.json();
    },

    updateTaskStatus: async (taskId: string, isCompleted: boolean) => {
        const res = await fetch(`${BASE_URL}/tasks/${taskId}`, {
            method: 'PATCH',
            headers: await getHeaders(),
            body: JSON.stringify({ is_completed: isCompleted }),
        });
        return res.json();
    },

    refreshLatestReport: async (): Promise<RefreshLatestResponse> => {
        const res = await fetch(`${BASE_URL}/reports/refresh-latest?use_cached_raw=true&cache_only=false`, {
            method: "POST",
            headers: await getHeaders(),
        });
        const payload = await res.json();
        if (!res.ok) {
            const detail = payload?.detail || payload;
            throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        }
        return payload;
    },
};
