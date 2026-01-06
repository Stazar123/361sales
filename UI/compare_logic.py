from __future__ import annotations
import pandas as pd
import numpy as np

def product_group_metrics(live_all: pd.DataFrame, intervals_all: pd.DataFrame) -> pd.DataFrame:
    total = live_all.groupby("product_group")["anon"].nunique().rename("customers")

    overdue = (
        live_all[live_all["status"] == "overdue"]
        .groupby("product_group")["anon"].nunique()
        .rename("overdue_customers")
    )
    due_soon = (
        live_all[live_all["status"] == "due_soon"]
        .groupby("product_group")["anon"].nunique()
        .rename("due_soon_customers")
    )

    repeat = intervals_all.groupby("product_group")["anon"].nunique().rename("repeat_customers")
    median_ret = (
        intervals_all.groupby("product_group")["adj_retention_days"]
        .median()
        .rename("median_retention_days")
    )

    out = pd.concat([total, repeat, median_ret, overdue, due_soon], axis=1).fillna(0)

    out["ok_customers"] = (out["customers"] - out["overdue_customers"] - out["due_soon_customers"]).clip(lower=0)

    out["repeat_rate_pct"] = np.where(out["customers"] > 0, out["repeat_customers"] / out["customers"] * 100, 0)
    out["overdue_rate_pct"] = np.where(out["customers"] > 0, out["overdue_customers"] / out["customers"] * 100, 0)
    out["due_soon_rate_pct"] = np.where(out["customers"] > 0, out["due_soon_customers"] / out["customers"] * 100, 0)
    out["ok_rate_pct"] = np.where(out["customers"] > 0, out["ok_customers"] / out["customers"] * 100, 0)

    return out.reset_index().sort_values("customers", ascending=False)
