"""因子选股策略：按 score 选多头，周频调仓，权重等权或分数加权"""
from __future__ import annotations

import pandas as pd


class FactorStrategy:
    def __init__(self, top_n: int = 5, weight_mode: str = "equal", rebalance: str = "W"):
        self.top_n = top_n
        self.weight_mode = weight_mode  # equal | score
        self.rebalance = rebalance  # W=每周首个交易日调仓 | D=每日

    def generate_weights(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """返回 MultiIndex(date, symbol) 的目标权重 target_w，仅含调仓日"""
        df = factor_df.dropna(subset=["score"])[["symbol", "score"]].copy()
        if df.empty:
            idx = pd.MultiIndex.from_tuples([], names=["date", "symbol"])
            return pd.DataFrame(columns=["target_w"], index=idx)

        # 索引可能含重复日期（多票同日），先降成普通列
        df = df.reset_index().rename(columns={factor_df.index.name or "index": "date"})
        df = df.rename(columns={df.columns[0]: "date"})
        df["date"] = pd.to_datetime(df["date"])

        # 只保留每周（或每日）的第一个交易日作为调仓日
        if self.rebalance == "W":
            period = df["date"].dt.to_period("W")
            first_days = df.groupby(period)["date"].transform("min")
            df = df[df["date"] == first_days]

        # 截面排名向量化选 top_n
        df["rk"] = df.groupby("date")["score"].rank(ascending=False, method="first")
        df = df[df["rk"] <= self.top_n]
        if df.empty:
            idx = pd.MultiIndex.from_tuples([], names=["date", "symbol"])
            return pd.DataFrame(columns=["target_w"], index=idx)

        if self.weight_mode == "score":
            s = df["score"].clip(lower=0)
            tot = s.groupby(df["date"]).transform("sum")
            # 当天分数全负则回退等权
            df["target_w"] = (s / tot.where(tot > 0)).fillna(1.0 / df.groupby("date")["symbol"].transform("count"))
        else:
            df["target_w"] = 1.0 / df.groupby("date")["symbol"].transform("count")

        return df.set_index(["date", "symbol"])[["target_w"]].sort_index()
