"""风控：单票上限、总仓位、止损、最大回撤熔断"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskConfig:
    max_pos: float = 0.25  # 单票最大仓位
    max_gross: float = 1.0  # 总仓位上限
    stop_loss: float = -0.08  # 单票相对成本止损
    max_dd: float = -0.15  # 净值最大回撤熔断
    cool_down: int = 5  # 熔断后空仓交易日


class RiskManager:
    def __init__(self, cfg: RiskConfig | None = None):
        self.cfg = cfg or RiskConfig()
        self._peak = 1.0
        self._cool = 0  # 剩余空仓日

    def clip_weights(self, weights: dict[str, float]) -> dict[str, float]:
        """单票上限 + 总仓位缩放"""
        if self._cool > 0:
            return {}
        clipped = {k: min(v, self.cfg.max_pos) for k, v in weights.items() if v > 0}
        gross = sum(clipped.values())
        if gross > self.cfg.max_gross and gross > 0:
            scale = self.cfg.max_gross / gross
            clipped = {k: v * scale for k, v in clipped.items()}
        return clipped

    def apply_stop(
        self, positions: dict[str, float], cost: dict[str, float], price: dict[str, float]
    ) -> dict[str, float]:
        """持仓相对成本跌破止损线则清仓"""
        kept = {}
        for sym, qty in positions.items():
            if qty <= 0 or sym not in price or sym not in cost or cost[sym] <= 0:
                continue
            pnl = price[sym] / cost[sym] - 1.0
            if pnl <= self.cfg.stop_loss:
                continue
            kept[sym] = qty
        return kept

    def check_drawdown(self, nav: float) -> bool:
        """True=触发熔断，强制空仓 cool_down 天"""
        self._peak = max(self._peak, nav)
        dd = nav / self._peak - 1.0 if self._peak > 0 else 0.0
        if dd <= self.cfg.max_dd:
            self._cool = self.cfg.cool_down
            return True
        return False

    def tick_cool(self) -> None:
        if self._cool > 0:
            self._cool -= 1
