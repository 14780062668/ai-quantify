"""生成演示用日线行情（无外网依赖）"""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_ohlcv(
    symbol: str = "DEMO",
    days: int = 504,
    seed: int = 42,
    start_price: float = 50.0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + hash(symbol) % 10000)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)

    # 几何布朗 + 少量均值回归，贴近真实波动
    rets = rng.normal(0.0004, 0.018, size=days)
    price = start_price * np.cumprod(1 + rets)
    close = price
    open_ = np.r_[start_price, close[:-1]] * (1 + rng.normal(0, 0.002, days))
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.012, days))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.012, days))
    volume = rng.integers(5_000_000, 30_000_000, size=days).astype(float)

    return pd.DataFrame(
        {
            "symbol": symbol,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


def make_universe(symbols: list[str] | None = None, days: int = 504) -> pd.DataFrame:
    symbols = symbols or [f"S{i:03d}" for i in range(1, 21)]
    frames = [make_ohlcv(s, days=days, seed=100 + i) for i, s in enumerate(symbols)]
    return pd.concat(frames).sort_index()
