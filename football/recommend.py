"""竞彩足球推荐：数据来自体彩官方在售赛程"""
from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np

from .models import Match
from .sporttery import fetch_jczq_matches


class MatchPool:
    def __init__(self, matches: list[Match] | None = None):
        self.matches = matches or []


def _edge(p: float, odds: float) -> float:
    return p * odds - 1.0


def _pick_outcome(m: Match) -> tuple[str, float, float, float]:
    cands = [
        ("主胜", m.p_h, m.odds_h),
        ("平局", m.p_d, m.odds_d),
        ("客胜", m.p_a, m.odds_a),
    ]
    best = max(cands, key=lambda x: _edge(x[1], x[2]))
    name, p, o = best
    return name, p, o, _edge(p, o)


def _combo_prob(probs: list[float]) -> float:
    p = 1.0
    for x in probs:
        p *= x
    return p


def _combo_odds(odds: list[float]) -> float:
    o = 1.0
    for x in odds:
        o *= x
    return o


def _round_bet(amount: float, unit: float = 2.0) -> float:
    """竞彩按 2 元整倍取整，至少 1 倍"""
    if amount <= 0:
        return 0.0
    n = max(1, int(round(amount / unit)))
    return n * unit


def _pick_reason(p: dict[str, Any]) -> str:
    """单场买入理由"""
    ev = p["ev"]
    if ev >= 0.05:
        ev_txt = f"期望价值偏正(+{ev:.0%})"
    elif ev >= 0:
        ev_txt = f"期望接近打平(+{ev:.0%})"
    else:
        ev_txt = f"期望略亏({ev:.0%})，靠概率优势压风险"
    num = p.get("编号") or ""
    num_txt = f"「{num}」" if num else ""
    return (
        f"体彩{num_txt}胜平负「{p['推荐']}」：官方赔率 {p['odds']}，"
        f"去水分概率约 {p['prob']:.0%}，{ev_txt}；三项里该项 EV 最高，故选它。"
    )


def _ticket_why(tag: str, picks: list[dict], cp: float, co: float, ev: float) -> str:
    """整单买入理由"""
    n = len(picks)
    names = "、".join(f"{x['对阵']}→{x['推荐']}" for x in picks)
    if tag == "稳单保本":
        return (
            f"只串 {n} 场（{names}），综合命中率约 {cp:.0%}、赔率 {co:.2f}。"
            f"逻辑是用高概率少场次换本金安全，优先保本/小赚；"
            f"整单 EV={ev:+.1%}，适合压大部分预算。"
        )
    return (
        f"串 {n} 场（{names}），综合赔率 {co:.2f}（目标 4~10 倍），命中率约 {cp:.0%}。"
        f"逻辑是用 2~4 场控赔率区间搏超额收益；"
        f"整单 EV={ev:+.1%}，适合小仓位博弹性。"
    )


def allocate_budget(
    total: float,
    p_stable: float,
    p_high: float,
    ev_stable: float,
    ev_high: float,
) -> tuple[float, float, str]:
    """
    按成本分仓：命中率优先、EV 微调；稳单占大头。
    预算≥20 时高收益至少 20%；金额取 2 元整倍。
    """
    # 仅允许 2~1000 正偶数
    total = int(max(2, min(1000, float(total))))
    if total % 2 != 0:
        total -= 1
    total = float(max(4, total))  # 至少两单各 2 元
    w_s = (max(p_stable, 1e-6) ** 1.2) * max(ev_stable + 1.0, 0.35)
    w_h = (max(p_high, 1e-6) ** 1.2) * max(ev_high + 1.0, 0.35)
    w_s *= 1.35
    ratio_s = w_s / (w_s + w_h)
    # 夹紧：稳单 55%~80%，高收益留足仓位
    ratio_s = float(np.clip(ratio_s, 0.55, 0.80))
    min_high = 2.0 if total < 20 else _round_bet(total * 0.20)
    stake_s = _round_bet(total * ratio_s)
    stake_h = _round_bet(total - stake_s)
    if stake_h < min_high:
        stake_h = min_high
        stake_s = _round_bet(total - stake_h)
    if stake_s < 2:
        stake_s = 2.0
        stake_h = _round_bet(total - stake_s)
    # 校正总和不超过预算
    if stake_s + stake_h > total:
        stake_h = max(2.0, _round_bet(total - stake_s))
        stake_s = _round_bet(total - stake_h)
    reason = (
        f"总成本 {total:.0f} 元，按「命中率优先 + EV 微调」分配："
        f"稳单约 {ratio_s:.0%}→{stake_s:.0f} 元，高收益→{stake_h:.0f} 元"
        f"（2 元整倍，高收益保底约 20%）。"
    )
    return stake_s, stake_h, reason


def _build_ticket(
    picks: list[dict[str, Any]],
    tag: str,
    note: str,
    stake: float,
) -> dict[str, Any]:
    probs = [x["prob"] for x in picks]
    odds = [x["odds"] for x in picks]
    cp = _combo_prob(probs)
    co = _combo_odds(odds)
    ev = cp * co - 1.0
    stake = float(stake)
    payout = round(stake * co, 2) if stake > 0 else 0.0
    net = round(payout - stake, 2)
    expect_net = round(stake * ev, 2)
    why = _ticket_why(tag, picks, cp, co, ev)
    for p in picks:
        p["理由"] = _pick_reason(p)
    return {
        "tag": tag,
        "note": note,
        "why": why,
        "picks": picks,
        "串关场次": len(picks),
        "综合概率": round(cp, 4),
        "综合赔率": round(co, 2),
        "投注金额": round(stake, 2),
        "理论返还": payout,
        "中奖净利": net,
        "期望净利": expect_net,
        "期望收益EV": round(ev, 4),
    }


def compare_tickets(stable: dict, high: dict, alloc_reason: str) -> dict[str, Any]:
    """两单对比结论"""
    rows = [
        {
            "维度": "定位",
            "稳单保本": "保本/控回撤",
            "高收益": "博弹性/冲赔率",
        },
        {
            "维度": "场次",
            "稳单保本": stable["串关场次"],
            "高收益": high["串关场次"],
        },
        {
            "维度": "综合概率",
            "稳单保本": f"{stable['综合概率']:.1%}",
            "高收益": f"{high['综合概率']:.1%}",
        },
        {
            "维度": "综合赔率",
            "稳单保本": stable["综合赔率"],
            "高收益": high["综合赔率"],
        },
        {
            "维度": "建议投入",
            "稳单保本": f"{stable['投注金额']:.0f}元",
            "高收益": f"{high['投注金额']:.0f}元",
        },
        {
            "维度": "中奖返还",
            "稳单保本": f"{stable['理论返还']:.2f}元",
            "高收益": f"{high['理论返还']:.2f}元",
        },
        {
            "维度": "中奖净利",
            "稳单保本": f"{stable['中奖净利']:+.2f}元",
            "高收益": f"{high['中奖净利']:+.2f}元",
        },
        {
            "维度": "期望净利",
            "稳单保本": f"{stable['期望净利']:+.2f}元",
            "高收益": f"{high['期望净利']:+.2f}元",
        },
        {
            "维度": "EV",
            "稳单保本": f"{stable['期望收益EV']:+.1%}",
            "高收益": f"{high['期望收益EV']:+.1%}",
        },
    ]
    # 结论
    if stable["综合概率"] >= high["综合概率"] * 1.5:
        verdict = "稳单命中率明显更高，预算应以稳单为主，高收益作小仓冲刺。"
    elif high["理论返还"] > stable["理论返还"] * 2:
        verdict = "高收益返还弹性大，但概率偏低；适合小仓，勿反客为主。"
    else:
        verdict = "两单风险收益差不极端，按分仓金额执行即可。"
    both_hit = round(stable["理论返还"] + high["理论返还"], 2)
    both_cost = round(stable["投注金额"] + high["投注金额"], 2)
    return {
        "rows": rows,
        "分仓说明": alloc_reason,
        "结论": verdict,
        "两单全中返还": both_hit,
        "两单总成本": both_cost,
        "两单全中净利": round(both_hit - both_cost, 2),
    }


def _pick_high_combo(
    scored: list[dict],
    rng: np.random.Generator,
    exclude_ids: set[str] | None = None,
    odds_lo: float = 4.0,
    odds_hi: float = 10.0,
    n_min: int = 2,
    n_max: int = 4,
) -> list[dict]:
    """高收益：2~4 场，综合赔率落在 [4, 10]"""
    exclude_ids = exclude_ids or set()
    pool = [x for x in scored if x["match_id"] not in exclude_ids]
    if len(pool) < n_min:
        pool = list(scored)
    # 候选按单场赔率适中优先，便于乘积进区间
    pool = sorted(pool, key=lambda x: (-x["ev"], abs(x["odds"] - 2.2)))
    cand = pool[:10]
    hits: list[tuple[float, list[dict]]] = []

    for n in range(n_min, min(n_max, len(cand)) + 1):
        for combo in combinations(cand, n):
            co = _combo_odds([x["odds"] for x in combo])
            if odds_lo <= co <= odds_hi:
                # 越贴近区间中位、EV 越好越优先
                mid = (odds_lo + odds_hi) / 2
                score = -abs(co - mid) + 0.15 * sum(x["ev"] for x in combo)
                hits.append((score, list(combo)))

    if hits:
        hits.sort(key=lambda x: -x[0])
        # 在头部若干方案中按种子随机，避免每次固定
        top = hits[: min(6, len(hits))]
        chosen = top[int(rng.integers(0, len(top)))][1]
        return sorted(chosen, key=lambda x: -x["odds"])

    # 回退：贪心凑到区间内
    rng.shuffle(cand)
    picked: list[dict] = []
    co = 1.0
    for x in cand:
        if len(picked) >= n_max:
            break
        nxt = co * x["odds"]
        if nxt > odds_hi and len(picked) >= n_min:
            continue
        if len(picked) < n_min or nxt <= odds_hi:
            picked.append(x)
            co = nxt
            if len(picked) >= n_min and odds_lo <= co <= odds_hi:
                break
    if len(picked) < n_min:
        picked = cand[:n_min]
    # 仍超区间则砍场次
    while len(picked) > n_min and _combo_odds([x["odds"] for x in picked]) > odds_hi:
        picked.pop()
    # 仍不足 4 倍则尽量再加一场
    if _combo_odds([x["odds"] for x in picked]) < odds_lo:
        used = {x["match_id"] for x in picked}
        for x in cand:
            if x["match_id"] in used or len(picked) >= n_max:
                continue
            nxt = _combo_odds([p["odds"] for p in picked] + [x["odds"]])
            if nxt <= odds_hi:
                picked.append(x)
                if nxt >= odds_lo:
                    break
    return sorted(picked, key=lambda x: -x["odds"])


def generate_tips(
    seed: int | None = None,
    pool: MatchPool | None = None,
    total_budget: float = 20.0,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """
    稳单保本：1-2场，高概率
    高收益：2-4场，综合赔率 4~10 倍
    赛程/赔率：体彩竞彩官方在售数据
    """
    tb = int(max(2, min(1000, float(total_budget))))
    if tb % 2 != 0:
        tb -= 1
    total_budget = float(max(2, tb))
    rng = np.random.default_rng(seed)

    meta = {"source": "", "updated_at": "", "error": "", "match_count": 0}
    if pool is not None and pool.matches:
        matches = list(pool.matches)
        meta["source"] = "自定义"
        meta["match_count"] = len(matches)
    else:
        raw = fetch_jczq_matches(force=force_refresh)
        matches = list(raw.get("matches") or [])
        meta = {
            "source": raw.get("source") or "sporttery.cn",
            "updated_at": raw.get("updated_at") or "",
            "sell_date": raw.get("sell_date") or "",
            "error": raw.get("error") or "",
            "match_count": len(matches),
            "cached": bool(raw.get("cached")),
        }
        if not matches:
            return {
                "seed": int(seed) if seed is not None else None,
                "总成本": float(total_budget),
                "稳单保本": None,
                "高收益": None,
                "对比": None,
                "meta": meta,
                "error": meta["error"] or "暂无体彩在售足球场次",
            }

    rng.shuffle(matches)

    scored = []
    for m in matches:
        outcome, p, o, ev = _pick_outcome(m)
        kick = " ".join(x for x in (m.match_date, m.match_time) if x).strip()
        scored.append(
            {
                "match_id": m.match_id,
                "league": m.league,
                "编号": m.match_num,
                "开赛": kick,
                "对阵": f"{m.home} vs {m.away}",
                "推荐": outcome,
                "prob": p,
                "odds": o,
                "ev": ev,
            }
        )

    stable_pool = [x for x in scored if x["prob"] >= 0.45 and x["ev"] > -0.05]
    stable_pool = sorted(stable_pool, key=lambda x: (-x["prob"], -x["ev"]))
    if not stable_pool:
        stable_pool = sorted(scored, key=lambda x: -x["prob"])[:4]
    n_stable = int(rng.choice([1, 2]))
    n_stable = min(n_stable, len(stable_pool))
    head = stable_pool[: max(n_stable + 2, n_stable)]
    stable_picks = list(rng.choice(head, size=n_stable, replace=False))
    stable_picks = sorted(stable_picks, key=lambda x: -x["prob"])

    high_picks = _pick_high_combo(
        scored,
        rng,
        exclude_ids={x["match_id"] for x in stable_picks},
        odds_lo=4.0,
        odds_hi=10.0,
        n_min=2,
        n_max=4,
    )

    def _fmt(picks: list[dict]) -> list[dict]:
        return [
            {
                "编号": x.get("编号") or "",
                "开赛": x.get("开赛") or "",
                "联赛": x["league"],
                "对阵": x["对阵"],
                "推荐": x["推荐"],
                "prob": x["prob"],
                "odds": x["odds"],
                "ev": x["ev"],
                "概率": f"{x['prob']:.0%}",
                "赔率": x["odds"],
                "EV": round(x["ev"], 3),
            }
            for x in picks
        ]

    fmt_s = _fmt(stable_picks)
    fmt_h = _fmt(high_picks)
    cp_s = _combo_prob([x["prob"] for x in fmt_s])
    cp_h = _combo_prob([x["prob"] for x in fmt_h])
    co_s = _combo_odds([x["odds"] for x in fmt_s])
    co_h = _combo_odds([x["odds"] for x in fmt_h])
    ev_s = cp_s * co_s - 1.0
    ev_h = cp_h * co_h - 1.0

    stake_s, stake_h, alloc_reason = allocate_budget(
        total_budget, cp_s, cp_h, ev_s, ev_h
    )

    stable = _build_ticket(
        fmt_s, "稳单保本", "少场次、高概率，体彩胜平负", stake_s
    )
    high = _build_ticket(
        fmt_h, "高收益", "2~4场串关，综合赔率约4~10倍，体彩胜平负", stake_h
    )

    return {
        "seed": int(seed) if seed is not None else None,
        "总成本": float(total_budget),
        "稳单保本": stable,
        "高收益": high,
        "对比": compare_tickets(stable, high, alloc_reason),
        "meta": meta,
        "error": "",
    }
