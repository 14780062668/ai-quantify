"""足球数据模型"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Match:
    match_id: str
    league: str
    home: str
    away: str
    odds_h: float  # 胜
    odds_d: float  # 平
    odds_a: float  # 负
    p_h: float
    p_d: float
    p_a: float
    match_num: str = ""  # 体彩编号，如 周五002
    match_date: str = ""
    match_time: str = ""
    extra: dict = field(default_factory=dict)
