import math
import pandas as pd


class ReportService:
    BASE_METRICS = ["Installs", "Cost", "Impressions", "Clicks"]
    REPORT_NETWORK_ROWS = ["SEARCH", "YOUTUBE", "DISPLAY"]

    @staticmethod
    def prepare_data(df_raw):
        if df_raw.empty:
            return df_raw

        df = df_raw.copy()
        df["Campaign ID"] = df["Campaign ID"].astype(str)
        if "Ad Group ID" in df.columns:
            df["Ad Group ID"] = df["Ad Group ID"].astype(str)
        df.rename(columns={"Campaign Name": "Campaign_Name"}, inplace=True, errors="ignore")

        df["Day"] = pd.to_datetime(df["Date"])
        df["Week"] = df["Day"].dt.strftime("%G-W%V")

        if "Campaign_Name" in df.columns:
            campaign_parts = df["Campaign_Name"].str.split("-", expand=True)
            df["City"] = campaign_parts[2] if campaign_parts.shape[1] > 2 else "Unknown"
            df["Service"] = campaign_parts[4] if campaign_parts.shape[1] > 4 else "Unknown"
        else:
            df["City"] = "Unknown"
            df["Service"] = "Unknown"

        return df

    @staticmethod
    def _normalize_network(value):
        net = str(value or "").upper()
        if net in {"SEARCH", "SEARCH_PARTNERS"}:
            return "SEARCH"
        if net == "CONTENT":
            return "DISPLAY"
        if net == "YOUTUBE":
            return "YOUTUBE"
        if net == "DISPLAY":
            return "DISPLAY"
        return "DISPLAY"

    def aggregate_weekly(self, prepared_df):
        if prepared_df.empty:
            return prepared_df
        df = prepared_df.copy()
        df["Ad Network Type"] = df["Ad Network Type"].apply(self._normalize_network)
        group_cols = ["Week", "City", "Campaign ID", "Campaign_Name", "Ad Group ID", "Ad Group Name", "Ad Network Type"]
        agg_df = df.groupby(group_cols, dropna=False)[self.BASE_METRICS].sum().reset_index()
        return agg_df

    @staticmethod
    def _safe_div(numerator, denominator):
        if not denominator:
            return 0.0
        return float(numerator) / float(denominator)

    def _pct_change(self, current, previous):
        if not previous:
            return 0.0
        return round((float(current) - float(previous)) * 100.0 / float(previous), 2)

    def _entity_windows(self, grouped_df, target_week):
        g = grouped_df.sort_values("Week").reset_index(drop=True)
        target_idx_list = g.index[g["Week"] == target_week].tolist()
        if not target_idx_list:
            return None
        target_idx = target_idx_list[-1]
        if target_idx == 0:
            return None
        current = g.iloc[target_idx]
        previous = g.iloc[target_idx - 1]
        baseline_start = max(0, target_idx - 3)
        baseline_df = g.iloc[baseline_start:target_idx]
        return current, previous, baseline_df

    def _significance(self, current, previous, baseline_values, impact_floor, pct_floor, z_floor):
        delta = float(current) - float(previous)
        pct = self._pct_change(current, previous)
        z_score = 0.0
        if baseline_values:
            mean = sum(baseline_values) / len(baseline_values)
            variance = sum((x - mean) ** 2 for x in baseline_values) / len(baseline_values)
            std = math.sqrt(variance)
            if std > 0:
                z_score = (float(current) - mean) / std
        is_sig = abs(delta) >= impact_floor and (abs(pct) >= pct_floor or abs(z_score) >= z_floor)
        return {
            "delta": round(delta, 2),
            "pct_change": round(pct, 2),
            "z_score": round(z_score, 3),
            "significant": bool(is_sig),
        }

    def _calc_ratios(self, metric_row):
        installs = float(metric_row.get("Installs", 0))
        cost = float(metric_row.get("Cost", 0))
        impressions = float(metric_row.get("Impressions", 0))
        clicks = float(metric_row.get("Clicks", 0))
        ctr = self._safe_div(clicks * 100.0, impressions)
        cpc = self._safe_div(cost, clicks)
        cpm = self._safe_div(cost * 1000.0, impressions)
        cti = self._safe_div(installs * 100.0, clicks)
        return {"ctr": ctr, "cpc": cpc, "cpm": cpm, "cti": cti}

    def _metric_block(self, cw_row, lw_row, base_row):
        out = {}
        for m in self.BASE_METRICS:
            cw = float(cw_row.get(m, 0))
            lw = float(lw_row.get(m, 0))
            base = float(base_row.get(m, 0))
            out[m.lower()] = {
                "cw": round(cw, 3) if m == "Cost" else int(round(cw)),
                "lw": round(lw, 3) if m == "Cost" else int(round(lw)),
                "baseline_avg": round(base, 3) if m == "Cost" else int(round(base)),
                "cw_vs_lw_pct": self._pct_change(cw, lw),
                "cw_vs_baseline_pct": self._pct_change(cw, base),
            }
        return out

    def _ratio_block(self, cw_row, lw_row, base_row):
        cw = self._calc_ratios(cw_row)
        lw = self._calc_ratios(lw_row)
        base = self._calc_ratios(base_row)
        out = {}
        for k in ["ctr", "cpc", "cpm", "cti"]:
            out[k] = {
                "cw": round(cw[k], 4),
                "lw": round(lw[k], 4),
                "baseline_avg": round(base[k], 4),
                "cw_vs_lw_pct": self._pct_change(cw[k], lw[k]),
                "cw_vs_baseline_pct": self._pct_change(cw[k], base[k]),
            }
        return out

    def _network_rows(self, df, target_week, last_week, include_baseline=False, baseline_weeks=None):
        baseline_weeks = baseline_weeks or []
        rows = []
        net_week = df.groupby(["Week", "Ad Network Type"])[self.BASE_METRICS].sum().reset_index()
        for network in self.REPORT_NETWORK_ROWS:
            cw_df = net_week[(net_week["Week"] == target_week) & (net_week["Ad Network Type"] == network)]
            lw_df = net_week[(net_week["Week"] == last_week) & (net_week["Ad Network Type"] == network)]
            base_df = net_week[(net_week["Week"].isin(baseline_weeks)) & (net_week["Ad Network Type"] == network)]
            cw = cw_df.iloc[0] if not cw_df.empty else {m: 0 for m in self.BASE_METRICS}
            lw = lw_df.iloc[0] if not lw_df.empty else {m: 0 for m in self.BASE_METRICS}
            base = base_df[self.BASE_METRICS].mean() if not base_df.empty else lw

            metrics = {}
            for m in self.BASE_METRICS:
                metrics[m.lower()] = {
                    "cw": round(float(cw[m]), 3) if m == "Cost" else int(round(float(cw[m]))),
                    "lw": round(float(lw[m]), 3) if m == "Cost" else int(round(float(lw[m]))),
                    "cw_vs_lw_pct": self._pct_change(cw[m], lw[m]),
                }
            if include_baseline:
                for m in self.BASE_METRICS:
                    metrics[m.lower()]["baseline_avg"] = round(float(base[m]), 3) if m == "Cost" else int(round(float(base[m])))
                    metrics[m.lower()]["cw_vs_baseline_pct"] = self._pct_change(cw[m], base[m])

            cw_rat = self._calc_ratios(cw)
            lw_rat = self._calc_ratios(lw)
            base_rat = self._calc_ratios(base)
            ratios = {}
            for k in ["ctr", "cpc", "cpm", "cti"]:
                ratios[k] = {
                    "cw": round(cw_rat[k], 4),
                    "lw": round(lw_rat[k], 4),
                    "cw_vs_lw_pct": self._pct_change(cw_rat[k], lw_rat[k]),
                }
                if include_baseline:
                    ratios[k]["baseline_avg"] = round(base_rat[k], 4)
                    ratios[k]["cw_vs_baseline_pct"] = self._pct_change(cw_rat[k], base_rat[k])

            rows.append({"network": network, "metrics": metrics, "ratios": ratios})
        return rows

    def _advanced_block(self, cw_row, lw_row, base_row, spend_total_cw=0, spend_total_lw=0):
        cw_rat = self._calc_ratios(cw_row)
        lw_rat = self._calc_ratios(lw_row)
        base_rat = self._calc_ratios(base_row)
        install_delta_lw = float(cw_row.get("Installs", 0)) - float(lw_row.get("Installs", 0))
        install_delta_base = float(cw_row.get("Installs", 0)) - float(base_row.get("Installs", 0))
        cpi_lw = self._safe_div(float(cw_row.get("Cost", 0)) - float(lw_row.get("Cost", 0)), install_delta_lw)
        cpi_base = self._safe_div(float(cw_row.get("Cost", 0)) - float(base_row.get("Cost", 0)), install_delta_base)
        spend_share_cw = self._safe_div(float(cw_row.get("Cost", 0)) * 100.0, spend_total_cw) if spend_total_cw else 0.0
        spend_share_lw = self._safe_div(float(lw_row.get("Cost", 0)) * 100.0, spend_total_lw) if spend_total_lw else 0.0

        return {
            "cost_per_incremental_install": {
                "cw_vs_lw": round(cpi_lw, 4),
                "cw_vs_baseline": round(cpi_base, 4),
            },
            "incremental_install_share": {
                "cw": round(self._safe_div(float(cw_row.get("Installs", 0)) * 100.0, max(1.0, float(cw_row.get("Installs", 0)))), 4),
                "lw": round(self._safe_div(float(lw_row.get("Installs", 0)) * 100.0, max(1.0, float(cw_row.get("Installs", 0)))), 4),
                "baseline_avg": round(self._safe_div(float(base_row.get("Installs", 0)) * 100.0, max(1.0, float(cw_row.get("Installs", 0)))), 4),
            },
            "spend_mix_shift_pct": round(spend_share_cw - spend_share_lw, 4),
            "creative_fatigue_signal": bool(cw_rat["ctr"] < lw_rat["ctr"] and float(cw_row.get("Impressions", 0)) >= float(lw_row.get("Impressions", 0))),
            "efficiency_deterioration_signal": bool(cw_rat["cpc"] > lw_rat["cpc"] and cw_rat["cti"] < lw_rat["cti"]),
            "learning_or_volatility_flag": bool(float(cw_row.get("Impressions", 0)) < 5000 or float(cw_row.get("Clicks", 0)) < 100),
        }

    def _entity_summary(self, hist_df, target_week, baseline_weeks):
        windows = self._entity_windows(hist_df, target_week)
        if not windows:
            return None
        cw, lw, baseline_df = windows
        base = baseline_df[self.BASE_METRICS].mean() if not baseline_df.empty else lw
        return cw, lw, base

    def _build_todo(self, level, entity, issue, impact_score, recommendation, city=None, campaign=None):
        return {
            "level": level,
            "entity": entity,
            "city": city,
            "campaign": campaign,
            "issue": issue,
            "impact_score": round(float(impact_score), 4),
            "severity": "high" if impact_score >= 0.2 else "medium" if impact_score >= 0.1 else "low",
            "recommendation": recommendation,
        }

    def _top_wasted_spend(self, weekly_df, target_week, last_week):
        campaign_week = weekly_df.groupby(["Week", "City", "Campaign_Name"])[self.BASE_METRICS].sum().reset_index()
        cw = campaign_week[campaign_week["Week"] == target_week].copy()
        lw = campaign_week[campaign_week["Week"] == last_week].copy()
        if cw.empty:
            return []
        merged = cw.merge(
            lw[["City", "Campaign_Name", "Cost", "Installs", "Clicks"]],
            on=["City", "Campaign_Name"],
            how="left",
            suffixes=("_cw", "_lw"),
        ).fillna(0)
        merged["cti_cw"] = merged.apply(lambda r: self._safe_div(r["Installs_cw"] * 100.0, r["Clicks_cw"]), axis=1)
        merged["cti_lw"] = merged.apply(lambda r: self._safe_div(r["Installs_lw"] * 100.0, r["Clicks_lw"]), axis=1)
        merged["cti_delta_pct"] = merged.apply(lambda r: self._pct_change(r["cti_cw"], r["cti_lw"]), axis=1)
        spend_rank = merged.sort_values("Cost_cw", ascending=False)
        candidates = []
        for _, r in spend_rank.head(20).iterrows():
            if r["cti_delta_pct"] >= 0:
                continue
            candidates.append(
                {
                    "level": "campaign",
                    "entity": r["Campaign_Name"],
                    "city": r["City"],
                    "cw_cost": round(float(r["Cost_cw"]), 4),
                    "cw_installs": int(round(float(r["Installs_cw"]))),
                    "cw_cti": round(float(r["cti_cw"]), 4),
                    "lw_cti": round(float(r["cti_lw"]), 4),
                    "cti_delta_pct": round(float(r["cti_delta_pct"]), 2),
                    "reason": "High spend + weak installs + worsening CTI",
                }
            )
        return candidates[:5]

    def generate_weekly_report_from_aggregates(self, weekly_df, target_week_str, threshold_config):
        if weekly_df.empty:
            return None

        df = weekly_df.copy()
        df["Ad Network Type"] = df["Ad Network Type"].apply(self._normalize_network)
        all_weeks = sorted(df["Week"].unique())
        if target_week_str not in all_weeks:
            return None
        target_idx = all_weeks.index(target_week_str)
        if target_idx == 0:
            return None

        last_week = all_weeks[target_idx - 1]
        baseline_weeks = all_weeks[max(0, target_idx - 3):target_idx]
        pan_week = df.groupby("Week")[self.BASE_METRICS].sum().reset_index()
        cw_pan = pan_week[pan_week["Week"] == target_week_str]
        lw_pan = pan_week[pan_week["Week"] == last_week]
        if cw_pan.empty or lw_pan.empty:
            return None
        cw_pan = cw_pan.iloc[0]
        lw_pan = lw_pan.iloc[0]
        base_pan = pan_week[pan_week["Week"].isin(baseline_weeks)][self.BASE_METRICS].mean()
        if base_pan.isna().any():
            base_pan = lw_pan

        report = {
            "week": target_week_str,
            "report_type": "google_ads_app_campaign_weekly",
            "period_config": {
                "current_week": target_week_str,
                "last_week": last_week,
                "baseline_weeks": baseline_weeks,
                "baseline_label": f"{len(baseline_weeks)}W Avg",
            },
            "network_dimension": {
                "allowed_networks_raw": ["SEARCH", "SEARCH_PARTNERS", "YOUTUBE", "DISPLAY"],
                "raw_to_report_mapping": {
                    "CONTENT": "DISPLAY",
                    "SEARCH": "SEARCH",
                    "SEARCH_PARTNERS": "SEARCH",
                    "YOUTUBE": "YOUTUBE",
                    "DISPLAY": "DISPLAY",
                },
                "final_rows": self.REPORT_NETWORK_ROWS,
            },
            "pan_summary": {
                "metrics": self._metric_block(cw_pan, lw_pan, base_pan),
                "ratios": self._ratio_block(cw_pan, lw_pan, base_pan),
            },
            "network_summary": {"rows": self._network_rows(df, target_week_str, last_week, include_baseline=False)},
            "significant_changes": [],
            "auto_todos": [],
            "top_wasted_spend_candidates": self._top_wasted_spend(df, target_week_str, last_week),
            "recent_changes": [],
        }

        report["pan_summary"]["advanced"] = {
            "cost_per_incremental_install": {
                "cw_vs_lw": round(self._safe_div(float(cw_pan["Cost"]) - float(lw_pan["Cost"]), float(cw_pan["Installs"]) - float(lw_pan["Installs"])), 4),
                "cw_vs_baseline": round(self._safe_div(float(cw_pan["Cost"]) - float(base_pan["Cost"]), float(cw_pan["Installs"]) - float(base_pan["Installs"])), 4),
            },
            "incremental_install_share": {
                "cw": round(100.0, 4),
                "lw": round(self._safe_div(float(lw_pan["Installs"]) * 100.0, max(1.0, float(cw_pan["Installs"]))), 4),
                "baseline_avg": round(self._safe_div(float(base_pan["Installs"]) * 100.0, max(1.0, float(cw_pan["Installs"]))), 4),
            },
            "spend_mix_shift_pct": {
                "search": 0.0,
                "youtube": 0.0,
                "display": 0.0,
            },
        }

        network_rows = report["network_summary"]["rows"]
        total_cost_cw = max(1.0, float(cw_pan["Cost"]))
        total_cost_lw = max(1.0, float(lw_pan["Cost"]))
        spend_map = {}
        for row in network_rows:
            cw_cost = float(row["metrics"]["cost"]["cw"])
            lw_cost = float(row["metrics"]["cost"]["lw"])
            spend_map[row["network"].lower()] = round(self._safe_div(cw_cost * 100.0, total_cost_cw) - self._safe_div(lw_cost * 100.0, total_cost_lw), 4)
            row["advanced"] = {
                "cost_per_incremental_install": round(self._safe_div(
                    float(row["metrics"]["cost"]["cw"]) - float(row["metrics"]["cost"]["lw"]),
                    float(row["metrics"]["installs"]["cw"]) - float(row["metrics"]["installs"]["lw"]),
                ), 4),
                "incremental_install_share": round(self._safe_div(
                    (float(row["metrics"]["installs"]["cw"]) - float(row["metrics"]["installs"]["lw"])) * 100.0,
                    max(1.0, float(cw_pan["Installs"]) - float(lw_pan["Installs"])),
                ), 4),
                "spend_mix_shift_pct": spend_map[row["network"].lower()],
                "creative_fatigue_signal": bool(
                    float(row["ratios"]["ctr"]["cw"]) < float(row["ratios"]["ctr"]["lw"]) and
                    float(row["metrics"]["impressions"]["cw"]) >= float(row["metrics"]["impressions"]["lw"])
                ),
                "efficiency_deterioration_signal": bool(
                    float(row["ratios"]["cpc"]["cw"]) > float(row["ratios"]["cpc"]["lw"]) and
                    float(row["ratios"]["cti"]["cw"]) < float(row["ratios"]["cti"]["lw"])
                ),
            }
        report["pan_summary"]["advanced"]["spend_mix_shift_pct"] = {
            "search": spend_map.get("search", 0.0),
            "youtube": spend_map.get("youtube", 0.0),
            "display": spend_map.get("display", 0.0),
        }

        # Significance and selection.
        min_impressions = int(threshold_config.get("min_impressions", 0))
        min_clicks = int(threshold_config.get("min_clicks", 0))
        min_installs = int(threshold_config.get("min_installs", 0))
        impact_floor_ratio = float(threshold_config.get("impact_floor_ratio", 0.015))
        pct_floor = float(threshold_config.get("pct_change_floor", 12.0))
        z_floor = float(threshold_config.get("zscore_floor", 1.5))
        city_coverage = float(threshold_config.get("city_coverage_target", 0.4))
        city_contrib_floor = float(threshold_config.get("city_contrib_floor", 0.05))
        city_impact_floor = max(10.0, abs(float(cw_pan["Installs"]) - float(lw_pan["Installs"])) * impact_floor_ratio)

        city_week = df.groupby(["Week", "City"])[self.BASE_METRICS].sum().reset_index()
        city_cw = city_week[city_week["Week"] == target_week_str]
        city_lw = city_week[city_week["Week"] == last_week].rename(columns={m: f"{m}_lw" for m in self.BASE_METRICS})
        city_join = city_cw.merge(city_lw[["City"] + [f"{m}_lw" for m in self.BASE_METRICS]], on="City", how="left").fillna(0)
        city_join["install_delta"] = city_join["Installs"] - city_join["Installs_lw"]
        total_abs_delta = max(1.0, float(city_join["install_delta"].abs().sum()))
        city_join["contrib_abs"] = city_join["install_delta"].abs() / total_abs_delta

        city_rank = city_join.sort_values("contrib_abs", ascending=False)
        selected_cities = []
        coverage = 0.0
        for _, row in city_rank.iterrows():
            if row["contrib_abs"] < city_contrib_floor:
                continue
            selected_cities.append(row["City"])
            coverage += float(row["contrib_abs"])
            if coverage >= city_coverage:
                break
        if not selected_cities:
            selected_cities = city_rank.head(6)["City"].tolist()

        city_insights = []
        campaign_insights = []
        adgroup_insights = []
        todos = []

        for city in selected_cities:
            hist = city_week[city_week["City"] == city]
            city_summary = self._entity_summary(hist, target_week_str, baseline_weeks)
            if not city_summary:
                continue
            cw_city, lw_city, base_city = city_summary
            sig = self._significance(
                current=float(cw_city["Installs"]),
                previous=float(lw_city["Installs"]),
                baseline_values=hist[hist["Week"].isin(baseline_weeks)]["Installs"].tolist(),
                impact_floor=city_impact_floor,
                pct_floor=pct_floor,
                z_floor=z_floor,
            )
            if not sig["significant"]:
                continue

            city_metrics = self._metric_block(cw_city, lw_city, base_city)
            city_ratios = self._ratio_block(cw_city, lw_city, base_city)
            city_advanced = self._advanced_block(
                cw_city, lw_city, base_city, spend_total_cw=float(cw_pan["Cost"]), spend_total_lw=float(lw_pan["Cost"])
            )

            city_scope_df = df[df["City"] == city]
            city_network = self._network_rows(city_scope_df, target_week_str, last_week, include_baseline=False)

            city_change = {
                "level": "city",
                "entity": city,
                "significance": {
                    "delta_installs": int(round(sig["delta"])),
                    "pct_change": sig["pct_change"],
                    "zscore": sig["z_score"],
                    "impact_score": round(abs(sig["delta"]) / max(1.0, float(cw_pan["Installs"])), 4),
                    "learning_or_volatility_flag": bool(float(cw_city["Impressions"]) < 5000 or float(cw_city["Clicks"]) < 100),
                },
                "summary_metrics": {"metrics": city_metrics, "ratios": city_ratios, "advanced": city_advanced},
                "network_breakdown": {"rows": city_network},
                "campaigns_to_check": [],
            }

            city_insights.append({
                "city": city,
                "metrics": {m: float(cw_city[m]) for m in self.BASE_METRICS},
                "wow_changes": {m: self._pct_change(float(cw_city[m]), float(lw_city[m])) for m in self.BASE_METRICS},
                "stats": sig,
                "movers": [],
            })

            campaign_week = city_scope_df.groupby(["Week", "Campaign_Name"])[self.BASE_METRICS].sum().reset_index()
            for campaign, camp_hist in campaign_week.groupby("Campaign_Name"):
                camp_summary = self._entity_summary(camp_hist, target_week_str, baseline_weeks)
                if not camp_summary:
                    continue
                cw_cmp, lw_cmp, base_cmp = camp_summary
                cmp_sig = self._significance(
                    current=float(cw_cmp["Installs"]),
                    previous=float(lw_cmp["Installs"]),
                    baseline_values=camp_hist[camp_hist["Week"].isin(baseline_weeks)]["Installs"].tolist(),
                    impact_floor=max(5.0, city_impact_floor * 0.2),
                    pct_floor=pct_floor,
                    z_floor=z_floor,
                )
                if not cmp_sig["significant"]:
                    continue

                cmp_scope = city_scope_df[city_scope_df["Campaign_Name"] == campaign]
                cmp_network = self._network_rows(cmp_scope, target_week_str, last_week, include_baseline=False)
                cmp_metrics = self._metric_block(cw_cmp, lw_cmp, base_cmp)
                cmp_ratios = self._ratio_block(cw_cmp, lw_cmp, base_cmp)
                cmp_advanced = self._advanced_block(
                    cw_cmp, lw_cmp, base_cmp, spend_total_cw=float(cw_city["Cost"]), spend_total_lw=float(lw_city["Cost"])
                )

                # Ad groups to check by contribution.
                adg_week = cmp_scope.groupby(["Week", "Ad Group Name"])[self.BASE_METRICS].sum().reset_index()
                adg_rows = []
                for adg, adg_hist in adg_week.groupby("Ad Group Name"):
                    adg_summary = self._entity_summary(adg_hist, target_week_str, baseline_weeks)
                    if not adg_summary:
                        continue
                    cw_adg, lw_adg, base_adg = adg_summary
                    if (
                        float(cw_adg["Impressions"]) < min_impressions
                        or float(cw_adg["Clicks"]) < min_clicks
                        or float(cw_adg["Installs"]) < min_installs
                    ):
                        continue
                    delta = float(cw_adg["Installs"]) - float(lw_adg["Installs"])
                    adg_rows.append((adg, delta, cw_adg, lw_adg, base_adg))
                total_cmp_abs = sum(abs(x[1]) for x in adg_rows) or 1.0
                adgroups_to_check = []
                for adg, delta, cw_adg, lw_adg, base_adg in sorted(adg_rows, key=lambda x: abs(x[1]), reverse=True):
                    share = abs(delta) * 100.0 / total_cmp_abs
                    if share < 10.0 and len(adgroups_to_check) >= 3:
                        continue
                    adgroups_to_check.append({
                        "ad_group": adg,
                        "contribution": {
                            "install_delta": int(round(delta)),
                            "share_of_campaign_delta_pct": round(share, 2),
                        },
                        "metrics": self._metric_block(cw_adg, lw_adg, base_adg),
                        "ratios": self._ratio_block(cw_adg, lw_adg, base_adg),
                        "advanced": {
                            "creative_fatigue_signal": bool(
                                self._calc_ratios(cw_adg)["ctr"] < self._calc_ratios(lw_adg)["ctr"] and float(cw_adg["Impressions"]) >= float(lw_adg["Impressions"])
                            ),
                            "efficiency_deterioration_signal": bool(
                                self._calc_ratios(cw_adg)["cpc"] > self._calc_ratios(lw_adg)["cpc"] and self._calc_ratios(cw_adg)["cti"] < self._calc_ratios(lw_adg)["cti"]
                            ),
                            "learning_or_volatility_flag": bool(float(cw_adg["Impressions"]) < 3000 or float(cw_adg["Clicks"]) < 60),
                        },
                    })
                    adgroup_insights.append({
                        "city": city,
                        "campaign": campaign,
                        "ad_group": adg,
                        "install_change": int(round(delta)),
                        "stats": {"delta": round(delta, 2)},
                    })
                    if len(adgroups_to_check) >= 8:
                        break

                city_change["campaigns_to_check"].append({
                    "campaign": campaign,
                    "contribution": {
                        "install_delta": int(round(float(cw_cmp["Installs"]) - float(lw_cmp["Installs"]))),
                        "share_of_entity_delta_pct": round(
                            abs(float(cw_cmp["Installs"]) - float(lw_cmp["Installs"])) * 100.0 /
                            max(1.0, abs(float(cw_city["Installs"]) - float(lw_city["Installs"]))), 2
                        ),
                    },
                    "metrics": cmp_metrics,
                    "ratios": cmp_ratios,
                    "advanced": cmp_advanced,
                    "network_breakdown": {"rows": cmp_network},
                    "adgroups_to_check": adgroups_to_check,
                })

                campaign_insights.append({
                    "city": city,
                    "campaign": campaign,
                    "metrics": {m: float(cw_cmp[m]) for m in self.BASE_METRICS},
                    "wow_changes": {m: self._pct_change(float(cw_cmp[m]), float(lw_cmp[m])) for m in self.BASE_METRICS},
                    "stats": cmp_sig,
                })

                todos.append(self._build_todo(
                    level="campaign",
                    entity=campaign,
                    city=city,
                    campaign=campaign,
                    issue="Significant install movement vs LW/3W baseline",
                    impact_score=abs(float(cw_cmp["Installs"]) - float(lw_cmp["Installs"])) / max(1.0, float(cw_pan["Installs"])),
                    recommendation="Review keyword/creative mix and rebalance budget toward strongest ad groups.",
                ))

            # city-level todo
            todos.append(self._build_todo(
                level="city",
                entity=city,
                city=city,
                campaign=None,
                issue="Significant install movement vs LW/3W baseline",
                impact_score=abs(float(cw_city["Installs"]) - float(lw_city["Installs"])) / max(1.0, float(cw_pan["Installs"])),
                recommendation="Check bid/creative mix in this city and scale winning ad groups.",
            ))

            report["significant_changes"].append(city_change)

        # Deduplicate todos.
        todo_map = {}
        for todo in sorted(todos, key=lambda x: x["impact_score"], reverse=True):
            key = f"{todo['level']}::{todo['entity']}"
            if key not in todo_map:
                todo_map[key] = todo
        report["auto_todos"] = list(todo_map.values())[:20]

        # Backward compatible fields for existing frontend.
        report["installs"] = int(round(float(cw_pan["Installs"])))
        report["cost"] = round(float(cw_pan["Cost"]), 3)
        report["clicks"] = int(round(float(cw_pan["Clicks"])))
        report["impressions"] = int(round(float(cw_pan["Impressions"])))
        report["wow_growth"] = self._pct_change(float(cw_pan["Installs"]), float(lw_pan["Installs"]))
        report["trend_windows"] = {
            "current_week": target_week_str,
            "last_week": last_week,
            "baseline_weeks": baseline_weeks,
        }
        report["pan_network"] = [
            {
                "network": row["network"],
                "metrics": {k.capitalize(): row["metrics"][k]["cw"] for k in ["installs", "cost", "impressions", "clicks"]},
                "wow_changes": {k.capitalize(): row["metrics"][k]["cw_vs_lw_pct"] for k in ["installs", "cost", "impressions", "clicks"]},
            }
            for row in report["network_summary"]["rows"]
        ]
        report["city_insights"] = city_insights[:20]
        report["campaign_insights"] = campaign_insights[:30]
        report["adgroup_insights"] = adgroup_insights[:40]

        return report
