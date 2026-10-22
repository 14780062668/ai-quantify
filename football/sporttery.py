"""体彩竞彩足球官方赛程/胜平负赔率拉取"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Any

from .models import Match

# 体彩按北京时间销售日（businessDate）开售
_CN_TZ = timezone(timedelta(hours=8))


def _today_cn() -> str:
    return datetime.now(_CN_TZ).strftime("%Y-%m-%d")

API_URL = (
    "https://webapi.sporttery.cn/gateway/jc/football/"
    "getMatchCalculatorV1.qry?poolCode=hhad,had,crs&channel=c"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.sporttery.cn/",
    "Origin": "https://www.sporttery.cn",
    "Accept": "application/json, text/plain, */*",
}

# 简易内存缓存（按销售日隔离）
_CACHE: dict[str, Any] = {"ts": 0.0, "day": "", "matches": [], "updated_at": "", "error": ""}
_CACHE_TTL = 60.0  # 秒


def _f(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if v > 0 else default
    except (TypeError, ValueError):
        return default


def odds_to_prob(h: float, d: float, a: float) -> tuple[float, float, float]:
    """赔率去水分 → 隐含概率"""
    ih, id_, ia = 1.0 / h, 1.0 / d, 1.0 / a
    s = ih + id_ + ia
    return ih / s, id_ / s, ia / s


def crs_to_prob(crs: dict) -> tuple[float, float, float]:
    """波胆赔率聚合 → 胜/平/负概率

    键格式为 "s{主队进球}s{客队进球}"（如 "s01s00"=1-0），带 f 后缀的
    为标志位需跳过；"胜其他"等非标准键被忽略，归一化后三向比例仍有效；
    波胆定价已包含伤停/近况信息，可作为胜平负概率的校准源。
    """
    ph = pd = pa = 0.0
    for code, odds in (crs or {}).items():
        if not (isinstance(code, str) and len(code) == 6 and code.startswith("s")):
            continue
        parts = code[1:].split("s")
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            continue
        o = _f(odds)
        if o <= 1:
            continue
        gh, ga = int(parts[0]), int(parts[1])
        inv = 1.0 / o
        if gh > ga:
            ph += inv
        elif gh == ga:
            pd += inv
        else:
            pa += inv
    s = ph + pd + pa
    if s <= 0:
        return 0.0, 0.0, 0.0
    return ph / s, pd / s, pa / s


def _parse_matches(payload: dict) -> tuple[list[Match], str]:
    """只保留体彩「当天销售日」可买场次（businessDate == 北京时间今天）"""
    value = payload.get("value") or {}
    updated = str(value.get("lastUpdateTime") or "")
    today = _today_cn()
    out: list[Match] = []
    for day in value.get("matchInfoList") or []:
        day_biz = str(day.get("businessDate") or "")
        for m in day.get("subMatchList") or []:
            if m.get("isHide"):
                continue
            # 销售日：场次归属日，非开赛日（如罗马-热那亚开赛18号、销售日17号）
            biz = str(m.get("businessDate") or day_biz or "")
            if biz != today:
                continue
            had = m.get("had") or {}
            oh, od, oa = _f(had.get("h")), _f(had.get("d")), _f(had.get("a"))
            if oh <= 1 or od <= 1 or oa <= 1:
                continue
            status = str(m.get("matchStatus") or "")
            if status and status.lower() not in ("selling", "1"):
                if int(m.get("sellStatus") or 0) != 1:
                    continue
            ph, pd, pa = odds_to_prob(oh, od, oa)
            pch, pcd, pca = crs_to_prob(m.get("crs") or {})
            mid = str(m.get("matchId") or m.get("matchNumStr") or len(out))
            num = str(m.get("matchNumStr") or "")
            league = str(m.get("leagueAbbName") or m.get("leagueAllName") or "")
            home = str(m.get("homeTeamAbbName") or m.get("homeTeamAllName") or "")
            away = str(m.get("awayTeamAbbName") or m.get("awayTeamAllName") or "")
            date = str(m.get("matchDate") or biz or "")
            tm = str(m.get("matchTime") or "")
            out.append(
                Match(
                    match_id=mid,
                    league=league,
                    home=home,
                    away=away,
                    odds_h=oh,
                    odds_d=od,
                    odds_a=oa,
                    p_h=ph,
                    p_d=pd,
                    p_a=pa,
                    match_num=num,
                    match_date=date,
                    match_time=tm,
                    extra={"p_h_crs": pch, "p_d_crs": pcd, "p_a_crs": pca},
                )
            )
    return out, updated


def fetch_jczq_matches(force: bool = False) -> dict[str, Any]:
    """
    拉取竞彩足球在售胜平负赛事。
    返回 {matches, updated_at, source, error}
    """
    now = time.time()
    today = _today_cn()
    if (
        not force
        and _CACHE["matches"]
        and _CACHE.get("day") == today
        and now - float(_CACHE["ts"]) < _CACHE_TTL
    ):
        return {
            "matches": _CACHE["matches"],
            "updated_at": _CACHE["updated_at"],
            "source": "sporttery.cn",
            "sell_date": today,
            "error": "",
            "cached": True,
        }

    try:
        req = urllib.request.Request(API_URL, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload.get("success"):
            raise RuntimeError(payload.get("errorMessage") or "接口返回失败")
        matches, updated = _parse_matches(payload)
        if not matches:
            raise RuntimeError(f"今日（{today}）暂无体彩可买足球场次")
        _CACHE["ts"] = now
        _CACHE["day"] = today
        _CACHE["matches"] = matches
        _CACHE["updated_at"] = updated
        _CACHE["error"] = ""
        return {
            "matches": matches,
            "updated_at": updated,
            "source": "sporttery.cn",
            "sell_date": today,
            "error": "",
            "cached": False,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, RuntimeError, json.JSONDecodeError) as e:
        if _CACHE["matches"] and _CACHE.get("day") == today:
            return {
                "matches": _CACHE["matches"],
                "updated_at": _CACHE["updated_at"],
                "source": "sporttery.cn(缓存)",
                "sell_date": today,
                "error": str(e),
                "cached": True,
            }
        return {
            "matches": [],
            "updated_at": "",
            "source": "sporttery.cn",
            "sell_date": today,
            "error": str(e),
            "cached": False,
        }
