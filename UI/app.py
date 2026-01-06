# ui/app.py
from __future__ import annotations

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from UI.data_io import load_parquets, standardize_columns
from UI.live_logic import compute_live_dynamic, compute_live_dynamic_all_groups
from UI.compare_logic import product_group_metrics
from UI.ui_components import benchmark_label, plot_urgency_stacked_counts


# ---------- Page config ----------
st.set_page_config(
    page_title="Retention + Live Status",
    layout="wide",
)

st.title("Retention + Live Status (Internal UI)")

# ---------- Load data ----------
dfs = standardize_columns(load_parquets())

live_std = dfs["live_customer_product_state"]
intervals = dfs["purchase_intervals"]
bench = dfs["retention_benchmarks"]
pg_ret = dfs["product_group_retention"]  # kept (not used here but kept for compatibility)

# ---------- Sidebar ----------
st.sidebar.header("Controls")
customer_mode = st.sidebar.toggle("Customer mode", value=True, help="Hide technical previews")
st.sidebar.divider()

product_groups = sorted(live_std["product_group"].dropna().unique())
selected_pg = st.sidebar.selectbox("Product group", product_groups)

asof_choice = st.sidebar.radio("ASOF date", ["dataset", "today"])

bench_mode = st.sidebar.radio("Benchmark mode", ["quantile", "manual"])
if bench_mode == "quantile":
    bench_quantile = st.sidebar.selectbox("Benchmark quantile", ["p25", "median", "p75"])
    manual_days_per_unit = None
else:
    bench_quantile = None
    manual_days_per_unit = st.sidebar.number_input("Manual days per unit", 1, 3650, 90)

due_soon_days = st.sidebar.slider("Due soon window (days)", 0, 60, 14)

st.sidebar.divider()
st.sidebar.caption("Tip: 'Compare products' and 'Overdue overview' use the same controls above.")

# ---------- Tabs ----------
tab_live, tab_compare, tab_overview = st.tabs(
    ["Live (single product)", "Compare products", "Overdue overview"]
)

# =========================================================
# TAB 1: Live (single product)
# =========================================================
with tab_live:
    # ---------- Compute dynamic live (single PG) ----------
    live_pg, asof_date_used, days_per_unit_used = compute_live_dynamic(
        live_std,
        bench,
        selected_pg,
        asof_choice,
        bench_mode,
        bench_quantile,
        manual_days_per_unit,
        due_soon_days,
    )

    intervals_pg = intervals[intervals["product_group"] == selected_pg]

    # ---------- Top KPIs ----------
    st.divider()
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    total_customers = int(live_pg["anon"].nunique())

    repeat_customers = int(intervals_pg["anon"].nunique()) if "anon" in intervals_pg.columns else 0
    repeat_rate = (repeat_customers / total_customers * 100) if total_customers else 0.0

    if len(intervals_pg) > 0:
        r = intervals_pg["adj_retention_days"].dropna()
        median_ret = float(r.median()) if len(r) else float("nan")
    else:
        median_ret = float("nan")

    overdue_customers = int(live_pg.loc[live_pg["status"] == "overdue", "anon"].nunique())
    due_soon_customers = int(live_pg.loc[live_pg["status"] == "due_soon", "anon"].nunique())
    overdue_rate = (overdue_customers / total_customers * 100) if total_customers else 0.0
    due_soon_rate = (due_soon_customers / total_customers * 100) if total_customers else 0.0

    k1.metric("Customers", f"{total_customers:,}")
    k2.metric("Repeat customers", f"{repeat_customers:,}")
    k3.metric("Repeat rate", f"{repeat_rate:.1f}%")
    k4.metric("Median retention", f"{median_ret:.1f} days" if median_ret == median_ret else "—")
    k5.metric("Overdue", f"{overdue_customers:,}", f"{overdue_rate:.1f}%")
    k6.metric("Due soon", f"{due_soon_customers:,}", f"{due_soon_rate:.1f}%")

    # ---------- Selection summary ----------
    st.subheader("Current selection")

    c1, c2, c3, c4 = st.columns(4)
    c1.write(f"**Product group:** {selected_pg}")
    c2.write(f"**ASOF:** {asof_choice}")
    c3.write(f"**Benchmark:** {bench_quantile if bench_mode=='quantile' else f'manual={manual_days_per_unit}'}")
    c4.write(f"**Due soon:** {due_soon_days} days")

    st.caption(f"ASOF_DATE = {asof_date_used.date()} | days_per_unit = {days_per_unit_used:.1f}")

    # ---------- Retention distribution ----------
    st.divider()
    st.subheader("Historical retention behaviour")

    left, right = st.columns([2, 1])

    x = (
        pd.to_numeric(intervals_pg.get("adj_retention_days"), errors="coerce")
        if not intervals_pg.empty
        else pd.Series(dtype=float)
    )
    x = x.dropna()
    x = x[np.isfinite(x)]
    x = x[x > 0]

    with left:
        if len(x) == 0:
            st.info("No retention intervals to display for this selection.")
        else:
            view = st.radio(
                "View",
                ["ECDF (recommended)", "Histogram (log-scaled, clipped)"],
                horizontal=True,
                key="retention_view",
            )
            clip_q = st.slider(
                "Clip long tail at quantile",
                min_value=0.90,
                max_value=0.999,
                value=0.99,
                step=0.01,
                key="retention_clip_q",
                help="Improves readability by clipping the extreme tail (stats table still uses full data).",
            )

            p25, p50, p75 = np.percentile(x.values, [25, 50, 75])
            clip_val = float(x.quantile(clip_q))
            x_clip = x.clip(upper=clip_val)

            if view.startswith("ECDF"):
                xs = np.sort(x.values)
                ys = np.arange(1, len(xs) + 1) / len(xs)

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=xs,
                        y=ys,
                        mode="lines",
                        name="ECDF",
                        hovertemplate="Days: %{x:.1f}<br>Share: %{y:.1%}<extra></extra>",
                    )
                )

                for val, name in [(p25, "P25"), (p50, "Median"), (p75, "P75")]:
                    fig.add_vline(
                        x=float(val),
                        line_dash="dot",
                        annotation_text=f"{name}: {val:.0f}d",
                        annotation_position="top right",
                    )

                # Show benchmark as reference
                if days_per_unit_used is not None and np.isfinite(days_per_unit_used) and days_per_unit_used > 0:
                    fig.add_vline(
                        x=float(days_per_unit_used),
                        line_dash="dash",
                        annotation_text=f"benchmark: {days_per_unit_used:.0f}d",
                        annotation_position="top left",
                    )

                fig.update_layout(
                    height=380,
                    margin=dict(l=30, r=20, t=40, b=40),
                    xaxis_title="Adjusted retention (days per unit)",
                    yaxis_title="Share of cycles ≤ X",
                    yaxis_tickformat=".0%",
                    showlegend=False,
                )

                st.plotly_chart(fig, use_container_width=True)
                st.caption("Interpretation: by day X, this curve shows the % of observed repurchase cycles completed within ≤ X days/unit.")

            else:
                xh = np.log1p(x_clip.values)

                fig = px.histogram(
                    x=xh,
                    nbins=40,
                    title=f"Histogram (log-scaled bins; clipped at p{int(clip_q*1000)/10:g} = {clip_val:.0f}d)",
                )

                ticks = np.linspace(xh.min(), xh.max(), 6)
                fig.update_xaxes(
                    tickmode="array",
                    tickvals=ticks,
                    ticktext=[f"{np.expm1(t):.0f}" for t in ticks],
                    title_text="Adjusted retention (days per unit)",
                )
                fig.update_yaxes(title_text="Count of cycles")
                fig.update_layout(height=380, margin=dict(l=30, r=20, t=40, b=40))

                st.plotly_chart(fig, use_container_width=True)
                st.caption("This histogram uses log-scaled binning + tail clipping to stay readable; the summary stats use full data.")

    with right:
        if len(x) > 0:
            st.table(x.describe(percentiles=[0.25, 0.5, 0.75]).to_frame("value").round(1))

    # ---------- Live status ----------
    st.divider()
    st.subheader("Live status")

    status_counts = (
        live_pg["actionable_status"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="customers")
    )
    status_counts["pct"] = (status_counts["customers"] / status_counts["customers"].sum() * 100).round(1)

    left, right = st.columns([1, 2])

    with left:
        st.dataframe(status_counts, hide_index=True)

    with right:
        fig, ax = plt.subplots()
        ax.bar(status_counts["status"], status_counts["customers"])
        for i, pct in enumerate(status_counts["pct"]):
            ax.text(i, status_counts["customers"].iloc[i], f"{pct}%", ha="center")
        st.pyplot(fig)

    # ---------- Action list ----------
    st.divider()
    st.subheader("📋 Action list (customers to contact)")

    status_filter = st.radio(
        "Show customers with status:",
        options=["overdue", "due_soon", "overdue + due_soon"],
        horizontal=True,
    )

    if status_filter == "overdue":
        action_df = live_pg[live_pg["status"] == "overdue"].copy()
    elif status_filter == "due_soon":
        action_df = live_pg[live_pg["status"] == "due_soon"].copy()
    else:
        action_df = live_pg[live_pg["status"].isin(["overdue", "due_soon"])].copy()

    if action_df.empty:
        st.success("No customers match the selected status filter.")
    else:
        st.caption(f"Customers in selection: {action_df['anon'].nunique():,}")

        action_df = action_df.sort_values("days_to_due")

        cols_to_show = [
            "anon",
            "last_purchase_date",
            "due_date",
            "days_to_due",
            "bottles_owned_effective",
            "coverage_days_est",
            "status",
        ]
        cols_to_show = [c for c in cols_to_show if c in action_df.columns]

        st.dataframe(action_df[cols_to_show], use_container_width=True, height=420)

        csv = action_df[cols_to_show].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download action list (CSV)",
            data=csv,
            file_name=f"action_list__{status_filter.replace(' ', '_')}__{selected_pg}.csv",
            mime="text/csv",
        )

        st.info(
            f"{action_df['anon'].nunique():,} customers require action for **{selected_pg}** "
            f"({status_filter.replace('_', ' ')})"
        )

    if not customer_mode:
        with st.expander("Debug: filtered data"):
            st.dataframe(live_pg.head(50))
            st.dataframe(intervals_pg.head(50))


# =========================================================
# TAB 2: Compare products
# =========================================================
with tab_compare:
    st.subheader("Compare product groups")

    live_all, asof_all = compute_live_dynamic_all_groups(
        live_std, bench, asof_choice, bench_mode, bench_quantile, manual_days_per_unit, due_soon_days
    )
    metrics = product_group_metrics(live_all, intervals)

    compare_pgs = st.multiselect(
        "Pick product groups to compare",
        options=sorted(metrics["product_group"].dropna().unique()),
        default=[selected_pg] if selected_pg in metrics["product_group"].values else None,
    )
    if compare_pgs:
        metrics = metrics[metrics["product_group"].isin(compare_pgs)]

    st.caption(f"Computed on ASOF_DATE = {asof_all.date()} | due_soon window = {due_soon_days}d")

    st.dataframe(
        metrics[
            [
                "product_group",
                "customers",
                "repeat_customers",
                "repeat_rate_pct",
                "median_retention_days",
                "overdue_rate_pct",
                "due_soon_rate_pct",
            ]
        ].round(
            {
                "repeat_rate_pct": 1,
                "median_retention_days": 1,
                "overdue_rate_pct": 1,
                "due_soon_rate_pct": 1,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader(
        f"Urgency by product group — {benchmark_label(bench_mode, bench_quantile, manual_days_per_unit)}"
    )
    plot_urgency_stacked_counts(metrics)


# =========================================================
# TAB 3: Overdue overview (customer-centric)
# =========================================================
with tab_overview:
    st.subheader("Overdue overview (customer-centric)")

    live_all, asof_all = compute_live_dynamic_all_groups(
        live_std, bench, asof_choice, bench_mode, bench_quantile, manual_days_per_unit, due_soon_days
    )

    actionable = live_all[live_all["status"].isin(["overdue", "due_soon"])].copy()

    st.caption(f"ASOF_DATE = {asof_all.date()} | due_soon window = {due_soon_days}d")

    if actionable.empty:
        st.success("No customers are overdue or due soon (across all product groups).")
    else:
        idx = actionable.groupby("anon")["days_to_due"].idxmin()
        most_urgent = actionable.loc[idx].copy().sort_values("days_to_due")

        st.metric("Customers needing action (any product)", f"{most_urgent['anon'].nunique():,}")

        cols = [
            "anon",
            "product_group",
            "status",
            "days_to_due",
            "last_purchase_date",
            "due_date",
            "bottles_owned_effective",
            "coverage_days_est",
        ]
        cols = [c for c in cols if c in most_urgent.columns]
        st.dataframe(most_urgent[cols], use_container_width=True, height=520)

        csv = most_urgent[cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download most-urgent-per-customer (CSV)",
            data=csv,
            file_name="overdue_overview__most_urgent_per_customer.csv",
            mime="text/csv",
        )

        st.divider()
        st.subheader("Customer drilldown")

        cust_options = most_urgent["anon"].astype(str).unique().tolist()
        selected_customer = st.selectbox("Pick a customer (anon)", cust_options)

        cust_df = live_all[live_all["anon"].astype(str) == str(selected_customer)].copy()
        cust_df = cust_df.sort_values(["status", "days_to_due", "product_group"])

        cust_cols = [
            "product_group",
            "status",
            "days_to_due",
            "last_purchase_date",
            "due_date",
            "bottles_owned_effective",
            "coverage_days_est",
            "days_per_unit",
        ]
        cust_cols = [c for c in cust_cols if c in cust_df.columns]

        st.dataframe(cust_df[cust_cols], use_container_width=True, height=360)

        show_matrix = st.toggle("Show status matrix (customer × product)", value=False)
        if show_matrix:
            st.caption("Matrix shows status per (customer, product_group).")
            mat = live_all.pivot_table(
                index="anon",
                columns="product_group",
                values="status",
                aggfunc="first",
            )
            only_actionable = st.toggle("Show only customers with any action needed", value=True)
            if only_actionable:
                mat = mat.loc[mat.index.isin(most_urgent["anon"].unique())]
            st.dataframe(mat, use_container_width=True, height=520)
