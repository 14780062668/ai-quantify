"""日频回测引擎（收盘调仓）"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .risk import RiskConfig, RiskManager


def run_backtest(
    price_df: pd.DataFrame,
    weight_df: pd.DataFrame,
    init_cash: float = 1_000_000.0,
    fee_rate: float = 0.0003,
    risk_cfg: RiskConfig | None = None,
) -> dict:
    """
    price_df: index=date, columns含 symbol/close
    weight_df: MultiIndex(date, symbol) -> target_w
    """
    risk = RiskManager(risk_cfg)
    closes = price_df.pivot_table(index=price_df.index, columns="symbol", values="close")
    dates = closes.index.sort_values()

    cash = init_cash
    pos: dict[str, float] = {}  # 股数
    cost: dict[str, float] = {}  # 成本价
    records = []
    trades = []

    for i, dt in enumerate(dates):
        px = closes.loc[dt].dropna().to_dict()
        # 止损
        pos = risk.apply_stop(pos, cost, px)

        # 市值
        mkt = sum(pos.get(s, 0) * px[s] for s in pos if s in px)
        nav = cash + mkt

        if risk.check_drawdown(nav):
            # 熔断：清仓
            for s, q in list(pos.items()):
                if s in px and q > 0:
                    proceeds = q * px[s] * (1 - fee_rate)
                    cash += proceeds
                    trades.append({"date": dt, "symbol": s, "side": "熔断卖", "qty": q, "price": px[s]})
            pos, cost = {}, {}
            mkt = 0.0
            nav = cash

        # 目标权重
        if dt in weight_df.index.get_level_values(0):
            day_w = weight_df.xs(dt, level=0)["target_w"].to_dict()
        else:
            day_w = {}
        day_w = risk.clip_weights(day_w)

        target_val = {s: nav * w for s, w in day_w.items() if s in px}
        # 不在目标里的持仓清掉
        for s in list(pos.keys()):
            if s not in target_val and s in px:
                q = pos.pop(s)
                cash += q * px[s] * (1 - fee_rate)
                cost.pop(s, None)
                trades.append({"date": dt, "symbol": s, "side": "卖", "qty": q, "price": px[s]})

        for s, tv in target_val.items():
            cur_val = pos.get(s, 0) * px[s]
            diff = tv - cur_val
            if abs(diff) < nav * 0.001:
                continue
            qty = diff / px[s]
            if qty > 0:
                cost_amt = qty * px[s] * (1 + fee_rate)
                if cost_amt > cash:
                    qty = cash / (px[s] * (1 + fee_rate))
                    cost_amt = qty * px[s] * (1 + fee_rate)
                if qty <= 0:
                    continue
                # 更新成本价
                old_q = pos.get(s, 0)
                old_c = cost.get(s, px[s])
                new_q = old_q + qty
                cost[s] = (old_q * old_c + qty * px[s]) / new_q if new_q > 0 else px[s]
                pos[s] = new_q
                cash -= cost_amt
                trades.append({"date": dt, "symbol": s, "side": "买", "qty": qty, "price": px[s]})
            else:
                sell_q = min(-qty, pos.get(s, 0))
                if sell_q <= 0:
                    continue
                cash += sell_q * px[s] * (1 - fee_rate)
                pos[s] = pos.get(s, 0) - sell_q
                if pos[s] <= 1e-8:
                    pos.pop(s, None)
                    cost.pop(s, None)
                trades.append({"date": dt, "symbol": s, "side": "卖", "qty": sell_q, "price": px[s]})

        mkt = sum(pos.get(s, 0) * px[s] for s in pos if s in px)
        nav = cash + mkt
        records.append({"date": dt, "nav": nav, "cash": cash, "mkt": mkt, "n_pos": len(pos)})
        risk.tick_cool()

    nav_df = pd.DataFrame(records).set_index("date")
    ret = nav_df["nav"].pct_change().fillna(0)
    total_ret = nav_df["nav"].iloc[-1] / init_cash - 1
    ann = (1 + total_ret) ** (252 / max(len(nav_df), 1)) - 1
    vol = ret.std() * np.sqrt(252)
    sharpe = ann / vol if vol > 1e-12 else 0.0
    dd = (nav_df["nav"] / nav_df["nav"].cummax() - 1).min()

    return {
        "nav": nav_df,
        "trades": pd.DataFrame(trades),
        "metrics": {
            "总收益": round(float(total_ret), 4),
            "年化": round(float(ann), 4),
            "波动": round(float(vol), 4),
            "夏普": round(float(sharpe), 4),
            "最大回撤": round(float(dd), 4),
            "交易次数": int(len(trades)),
        },
    }
