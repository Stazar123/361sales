from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st

def resolve_asof_date(live_df: pd.DataFrame, asof: str) -> pd.Timestamp:
    return (
        pd.to_datetime(live_df["last_purchase_date"]).max().normalize()
        if asof == "dataset"
        else pd.Timestamp.today().normalize()
    )

def resolve_benchmark_days_per_unit(bench_df, product_group, bench_mode, bench_quantile, manual_days):
    if bench_mode == "manual":
        return float(manual_days)
    row = bench_df.loc[bench_df["product_group"] == product_group]
    return float(row.iloc[0][bench_quantile])

@st.cache_data(show_spinner=False)
def compute_live_dynamic(
    live_df,
    bench_df,
    product_group,
    asof_choice,
    bench_mode,
    bench_quantile,
    manual_days_per_unit,
    due_soon_days,
):
    asof_date = resolve_asof_date(live_df, asof_choice)
    days_per_unit = resolve_benchmark_days_per_unit(
        bench_df, product_group, bench_mode, bench_quantile, manual_days_per_unit
    )

    df = live_df[live_df["product_group"] == product_group].copy()
    df["last_purchase_date"] = pd.to_datetime(df["last_purchase_date"])

    units = df["bottles_owned_effective"].fillna(1).clip(lower=1)
    df["coverage_days_est"] = (days_per_unit * units).round().astype(int)

    df["due_date"] = df["last_purchase_date"] + pd.to_timedelta(df["coverage_days_est"], unit="D")
    df["days_to_due"] = (df["due_date"] - asof_date).dt.days

    df["status"] = "ok"
    df.loc[df["days_to_due"] < 0, "status"] = "overdue"
    df.loc[(df["days_to_due"] >= 0) & (df["days_to_due"] <= due_soon_days), "status"] = "due_soon"
    df["actionable_status"] = df["status"]

    return df, asof_date, days_per_unit

@st.cache_data(show_spinner=False)
def compute_live_dynamic_all_groups(
    live_df: pd.DataFrame,
    bench_df: pd.DataFrame,
    asof_choice: str,
    bench_mode: str,
    bench_quantile: str | None,
    manual_days_per_unit: float | None,
    due_soon_days: int,
) -> tuple[pd.DataFrame, pd.Timestamp]:
    asof_date = resolve_asof_date(live_df, asof_choice)

    base = live_df.copy()
    base["last_purchase_date"] = pd.to_datetime(base["last_purchase_date"])

    if bench_mode == "manual":
        dpu = pd.DataFrame({
            "product_group": base["product_group"].dropna().unique(),
            "days_per_unit": float(manual_days_per_unit),
        })
    else:
        dpu = bench_df[["product_group", bench_quantile]].rename(columns={bench_quantile: "days_per_unit"})

    df = base.merge(dpu, on="product_group", how="left")
    df["days_per_unit"] = pd.to_numeric(df["days_per_unit"], errors="coerce").fillna(90.0)

    units = df["bottles_owned_effective"].fillna(1).clip(lower=1)
    df["coverage_days_est"] = (df["days_per_unit"] * units).round().astype(int)

    df["due_date"] = df["last_purchase_date"] + pd.to_timedelta(df["coverage_days_est"], unit="D")
    df["days_to_due"] = (df["due_date"] - asof_date).dt.days

    df["status"] = "ok"
    df.loc[df["days_to_due"] < 0, "status"] = "overdue"
    df.loc[(df["days_to_due"] >= 0) & (df["days_to_due"] <= due_soon_days), "status"] = "due_soon"
    df["actionable_status"] = df["status"]

    return df, asof_date
