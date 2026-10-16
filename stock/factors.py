"""多因子计算：动量 / 波动 / 成交量 / 均值回归"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _zscore(s: pd.Series) -> pd.Series:
    std = s.std()
    if std == 0 or np.isnan(std):
        return s * 0.0
    return (s - s.mean()) / std


def calc_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入需含 close/volume，按 symbol 分组。
    输出附加因子列，并给出综合 score（越大越偏多）。
    """
    out = df.copy()
    g = out.groupby("symbol", group_keys=False)

    # 动量：20日 / 60日收益
    out["mom_20"] = g["close"].pct_change(20)
    out["mom_60"] = g["close"].pct_change(60)

    # 波动：20日收益率标准差（低波加分）
    ret = g["close"].pct_change()
    out["vol_20"] = ret.groupby(out["symbol"]).transform(lambda x: x.rolling(20).std())

    # 成交量异动：量 / 20日均量
    out["vol_ratio"] = g["volume"].transform(lambda x: x / x.rolling(20).mean())

    # 均值回归：收盘相对 20日均线偏离
    ma20 = g["close"].transform(lambda x: x.rolling(20).mean())
    out["mr_20"] = (out["close"] - ma20) / ma20

    # 截面标准化后加权打分
    def _score_one_day(day: pd.DataFrame) -> pd.Series:
        m20 = _zscore(day["mom_20"])
        m60 = _zscore(day["mom_60"])
        # 低波动更好：取负
        v20 = -_zscore(day["vol_20"])
        vr = _zscore(day["vol_ratio"])
        # 过度上涨惩罚（均值回归）
        mr = -_zscore(day["mr_20"])
        return 0.30 * m20 + 0.25 * m60 + 0.20 * v20 + 0.15 * vr + 0.10 * mr

    out["score"] = out.groupby(out.index, group_keys=False).apply(_score_one_day)
    return out
