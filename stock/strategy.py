"""因子选股策略：每日按 score 选多头，权重等权或分数加权"""
from __future__ import annotations

import pandas as pd


class FactorStrategy:
    def __init__(self, top_n: int = 5, weight_mode: str = "equal"):
        self.top_n = top_n
        self.weight_mode = weight_mode  # equal | score

    def generate_weights(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """返回 MultiIndex(date, symbol) 的目标权重 target_w"""
        rows = []
        for dt, day in factor_df.groupby(level=0):
            day = day.dropna(subset=["score"])
            if day.empty:
                continue
            pick = day.nlargest(self.top_n, "score")
            if self.weight_mode == "score":
                s = pick["score"].clip(lower=0)
                if s.sum() <= 0:
                    w = pd.Series(1.0 / len(pick), index=pick["symbol"].values)
                else:
                    w = s / s.sum()
                    w.index = pick["symbol"].values
            else:
                w = pd.Series(1.0 / len(pick), index=pick["symbol"].values)
            for sym, weight in w.items():
                rows.append({"date": dt, "symbol": sym, "target_w": float(weight)})

        if not rows:
            return pd.DataFrame(columns=["date", "symbol", "target_w"]).set_index(
                ["date", "symbol"]
            )
        return pd.DataFrame(rows).set_index(["date", "symbol"])
