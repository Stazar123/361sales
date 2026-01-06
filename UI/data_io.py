from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

DATA_DIR = Path("data/interim")

FILES = {
    "live_customer_product_state": DATA_DIR / "live_customer_product_state.parquet",
    "purchase_intervals": DATA_DIR / "purchase_intervals.parquet",
    "retention_benchmarks": DATA_DIR / "retention_benchmarks.parquet",
    "product_group_retention": DATA_DIR / "product_group_retention.parquet",
}

@st.cache_data(show_spinner=True)
def load_parquets() -> dict[str, pd.DataFrame]:
    dfs: dict[str, pd.DataFrame] = {}
    for key, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path.as_posix()}")
        dfs[key] = pd.read_parquet(path)
    return dfs

def require_cols(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {missing}")

def standardize_columns(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    dfs2 = dict(dfs)
    for key in dfs2:
        if "MATRIX GRUPA PRODUKTOWA" in dfs2[key].columns:
            dfs2[key] = dfs2[key].rename(columns={"MATRIX GRUPA PRODUKTOWA": "product_group"})
    return dfs2
