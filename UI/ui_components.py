from __future__ import annotations
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

def benchmark_label(bench_mode: str, bench_quantile: str | None, manual_days_per_unit: float | None) -> str:
    if bench_mode == "manual":
        return f"Manual retention = {float(manual_days_per_unit):.0f} days/unit"
    return f"Benchmark = {bench_quantile} days/unit (per product group)"

def plot_urgency_stacked_counts(metrics: pd.DataFrame) -> None:
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=metrics["product_group"],
            y=metrics["ok_customers"],
            name="OK",
            text=(metrics["ok_rate_pct"].round(1)).astype(str) + "%",
            textposition="inside",
            hovertemplate="OK: %{y:,} (%{text})<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=metrics["product_group"],
            y=metrics["due_soon_customers"],
            name="Due soon",
            text=(metrics["due_soon_rate_pct"].round(1)).astype(str) + "%",
            textposition="inside",
            hovertemplate="Due soon: %{y:,} (%{text})<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=metrics["product_group"],
            y=metrics["overdue_customers"],
            name="Overdue",
            text=(metrics["overdue_rate_pct"].round(1)).astype(str) + "%",
            textposition="inside",
            hovertemplate="Overdue: %{y:,} (%{text})<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="stack",
        height=480,
        margin=dict(l=30, r=20, t=40, b=40),
        yaxis_title="Customers (count)",
        xaxis_title="Product group",
        legend_title_text="Status",
    )

    st.plotly_chart(fig, use_container_width=True)
