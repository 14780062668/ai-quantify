"""双功能入口：足球推荐 | 股票量化（手机优先）"""
from __future__ import annotations

import time

import plotly.express as px
import streamlit as st

from football.recommend import generate_tips
from stock.backtest import run_backtest
from stock.data import make_universe
from stock.factors import calc_factors
from stock.risk import RiskConfig
from stock.strategy import FactorStrategy

st.set_page_config(
    page_title="AI Quantify",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&family=Space+Grotesk:wght@500;700&display=swap');

:root {
  --ink: #121814;
  --muted: #5B675F;
  --line: #D7DED8;
  --bg: #EEF2EF;
  --card: #FFFFFF;
  --green: #146C4B;
  --green-soft: #E5F2EB;
  --amber: #B45309;
  --amber-soft: #FFF4E8;
  --radius: 16px;
}

html, body, [data-testid="stAppViewContainer"] {
  max-width: 100vw;
  overflow-x: hidden;
  font-family: "DM Sans", sans-serif !important;
}
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(900px 420px at 10% -10%, rgba(20,108,75,0.14), transparent 55%),
    radial-gradient(700px 380px at 100% 0%, rgba(180,83,9,0.08), transparent 50%),
    var(--bg);
}
[data-testid="stHeader"] { display: none; }
#MainMenu, footer { visibility: hidden; }
.block-container {
  padding: 0.7rem 1rem 3.5rem !important;
  max-width: 720px;
}

.brand {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.75rem; margin-bottom: 0.6rem;
}
.brand-mark {
  font-family: "Space Grotesk", sans-serif;
  font-weight: 700; font-size: 1.5rem; letter-spacing: -0.03em;
  color: var(--ink); line-height: 1.1;
}
.brand-mark span { color: var(--green); }
.brand-sub { color: var(--muted); font-size: 0.74rem; margin-top: 0.2rem; }
.brand-chip {
  flex-shrink: 0; font-size: 0.68rem; font-weight: 600;
  color: var(--green); background: var(--green-soft);
  border-radius: 999px; padding: 0.28rem 0.6rem;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 0.35rem; background: transparent; border-bottom: 1px solid var(--line);
  padding-bottom: 0.15rem; overflow-x: auto; flex-wrap: nowrap !important;
}
[data-testid="stTabs"] button {
  min-height: 44px; padding: 0.45rem 0.9rem !important;
  font-family: "Space Grotesk", sans-serif !important;
  font-weight: 600 !important; color: var(--muted) !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--ink) !important;
  border-bottom: 2px solid var(--green) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }

div.stButton > button {
  width: 100%; min-height: 48px; border-radius: 12px;
  font-weight: 700; font-family: "Space Grotesk", sans-serif !important;
  letter-spacing: 0.01em;
  padding: 0 0.5rem; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
div.stButton > button,
div.stButton > button p {
  color: var(--ink) !important;
}
div.stButton > button[kind="primary"] {
  background: var(--green) !important; border-color: var(--green) !important;
  color: #FFFFFF !important;
}
div.stButton > button[kind="primary"] p,
div.stButton > button[kind="primary"] span {
  color: #FFFFFF !important;
}
/* 输入框标签可见性保险 */
[data-testid="stNumberInput"] label,
[data-testid="stNumberInput"] label p {
  color: var(--ink) !important; font-size: 0.85rem !important;
  visibility: visible !important; display: block !important;
}
[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 0.7rem 0.85rem;
}
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: var(--muted) !important; }
[data-testid="stMetricValue"] {
  font-family: "Space Grotesk", sans-serif !important; font-size: 1.2rem !important;
}

.toolbar {
  display: grid; grid-template-columns: 1fr; gap: 0.35rem;
  margin-bottom: 0.35rem;
}
p.hint {
  color: #3D4A42 !important; font-size: 0.78rem !important; line-height: 1.4;
  margin: 0.15rem 0 0.75rem; display: block !important; visibility: visible !important;
}
.seed-line {
  display: flex; justify-content: space-between; align-items: center;
  color: var(--muted); font-size: 0.75rem; margin: 0.55rem 0 0.75rem;
}

.ticket-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 1rem 1rem 1.05rem;
  margin-bottom: 0.9rem;
}
.ticket-card.stable { box-shadow: inset 3px 0 0 var(--green); }
.ticket-card.high { box-shadow: inset 3px 0 0 var(--amber); }
.ticket-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 0.6rem; margin-bottom: 0.85rem;
}
.ticket-head .tag {
  font-family: "Space Grotesk", sans-serif;
  font-weight: 700; font-size: 1.08rem; color: var(--ink);
}
.ticket-head .note { color: var(--muted); font-size: 0.78rem; margin-top: 0.2rem; }
.badge {
  flex-shrink: 0; font-size: 0.78rem; font-weight: 700;
  border-radius: 10px; padding: 0.35rem 0.6rem; white-space: nowrap;
}
.badge.g { background: var(--green-soft); color: var(--green); }
.badge.a { background: var(--amber-soft); color: var(--amber); }

.pick-row {
  display: grid; grid-template-columns: 1fr auto;
  gap: 0.55rem; padding: 0.7rem 0;
  border-top: 1px solid #EEF1EE;
}
.pick-main .league {
  color: var(--muted); font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: 0.04em;
}
.pick-main .vs {
  font-weight: 700; font-size: 0.95rem; margin-top: 0.12rem;
  word-break: break-word;
}
.pick-why {
  margin-top: 0.35rem; color: var(--muted); font-size: 0.74rem; line-height: 1.4;
}
.pick-side { text-align: right; }
.pick-side .rec {
  font-family: "Space Grotesk", sans-serif;
  font-weight: 700; font-size: 1rem; color: var(--green);
}
.pick-side .od { color: var(--muted); font-size: 0.78rem; margin-top: 0.15rem; }

.meta-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.45rem; margin-top: 0.85rem;
}
.meta-cell {
  background: #F4F7F5; border-radius: 12px; padding: 0.55rem 0.65rem;
}
.meta-cell .k { font-size: 0.68rem; color: var(--muted); }
.meta-cell .v {
  font-family: "Space Grotesk", sans-serif;
  font-size: 1.02rem; font-weight: 700; margin-top: 0.1rem;
}
.why-box {
  margin-top: 0.8rem; padding: 0.75rem 0.8rem;
  background: var(--green-soft); border-radius: 12px;
  font-size: 0.82rem; line-height: 1.5; color: #1E3328;
}
.ticket-card.high .why-box { background: var(--amber-soft); color: #3A2A16; }
.why-box .label {
  font-family: "Space Grotesk", sans-serif;
  font-weight: 700; font-size: 0.78rem; margin-bottom: 0.25rem;
  letter-spacing: 0.02em;
}

.compare-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 1rem; margin-bottom: 0.5rem;
}
.compare-card .title {
  font-family: "Space Grotesk", sans-serif;
  font-weight: 700; font-size: 1.05rem; margin-bottom: 0.65rem;
}
.compare-row {
  display: grid; grid-template-columns: 0.85fr 1fr 1fr; gap: 0.3rem;
  padding: 0.45rem 0; border-bottom: 1px solid #EEF1EE; font-size: 0.8rem;
}
.compare-row.head {
  color: var(--muted); font-size: 0.7rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.03em;
}
.compare-row .dim { color: var(--muted); }
.verdict {
  margin-top: 0.75rem; padding: 0.75rem 0.8rem;
  background: #F4F7F5; border-radius: 12px;
  font-size: 0.84rem; line-height: 1.45;
}
.verdict b { font-family: "Space Grotesk", sans-serif; }
.summary-bar {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.4rem;
  margin-top: 0.7rem;
}
.summary-bar .cell {
  background: #F4F7F5; border-radius: 10px; padding: 0.5rem 0.45rem; text-align: center;
}
.summary-bar .k { font-size: 0.65rem; color: var(--muted); }
.summary-bar .v {
  font-family: "Space Grotesk", sans-serif;
  font-weight: 700; font-size: 0.92rem; margin-top: 0.1rem;
}

@media (max-width: 640px) {
  .block-container { padding: 0.55rem 0.6rem 4rem !important; }
  .brand { margin-bottom: 0.45rem; }
  .brand-mark { font-size: 1.3rem; }
  /* 按钮/指标保持并排，不再强制单列堆叠；列可收缩避免按钮被裁 */
  [data-testid="stHorizontalBlock"] { gap: 0.4rem !important; flex-wrap: nowrap !important; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: 0 !important; }
  .ticket-card { padding: 0.85rem 0.8rem 0.9rem; margin-bottom: 0.7rem; }
  .ticket-head .tag { font-size: 1rem; }
  .meta-grid { gap: 0.3rem; }
  .meta-cell { padding: 0.42rem 0.5rem; border-radius: 10px; }
  .meta-cell .k { font-size: 0.62rem; }
  .meta-cell .v { font-size: 0.9rem; }
  .pick-row { padding: 0.55rem 0; }
  .pick-main .vs { font-size: 0.88rem; }
  .pick-side .rec { font-size: 0.92rem; }
  /* 对比表：小字号 + 横向可滚动，避免三列挤压换行 */
  .compare-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .compare-row { min-width: 300px; font-size: 0.74rem; padding: 0.38rem 0; }
  .summary-bar .v { font-size: 0.85rem; }
  .why-box { font-size: 0.78rem; }
  p.hint { font-size: 0.72rem !important; }
  .seed-line { font-size: 0.68rem; flex-wrap: wrap; gap: 0.2rem; }
  div.stButton > button { min-height: 46px; font-size: 0.85rem; padding: 0 0.3rem; }
  [data-testid="stMetric"] { padding: 0.5rem 0.6rem; }
  [data-testid="stMetricValue"] { font-size: 1.05rem !important; }
}

/* 推荐理由：手机/桌面统一可折叠，默认收起 */
details.pick-why { margin-top: 0.35rem; }
details.pick-why summary {
  color: var(--green); font-size: 0.72rem; font-weight: 600;
  cursor: pointer; list-style: none; user-select: none;
}
details.pick-why summary::before { content: "▸ "; }
details.pick-why[open] summary::before { content: "▾ "; }
details.pick-why .why-text {
  margin-top: 0.25rem; color: var(--muted); font-size: 0.74rem; line-height: 1.45;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="brand">
  <div>
    <div class="brand-mark">AI <span>Quantify</span></div>
    <div class="brand-sub">足球推荐 · 股票量化</div>
  </div>
  <div class="brand-chip">演示版</div>
</div>
""",
    unsafe_allow_html=True,
)

tab_fb, tab_stock = st.tabs(["足球", "股票"])


def _ticket_html(ticket: dict, kind: str) -> str:
    cls = "stable" if kind == "stable" else "high"
    badge_cls = "g" if kind == "stable" else "a"
    rows = []
    for p in ticket["picks"]:
        why = p.get("理由", "")
        num = p.get("编号") or ""
        kick = p.get("开赛") or ""
        league = p.get("联赛") or ""
        meta_line = " · ".join(x for x in (num, league, kick) if x)
        rows.append(
            f"""<div class="pick-row">
              <div class="pick-main">
                <div class="league">{meta_line}</div>
                <div class="vs">{p['对阵']}</div>
                <details class="pick-why"><summary>买入理由</summary><div class="why-text">{why}</div></details>
              </div>
              <div class="pick-side">
                <div class="rec">{p['推荐']}</div>
                <div class="od">{p['概率']} · 赔 {p['赔率']}</div>
              </div>
            </div>"""
        )
    return f"""
    <div class="ticket-card {cls}">
      <div class="ticket-head">
        <div>
          <div class="tag">{ticket['tag']}</div>
          <div class="note">{ticket['note']}</div>
        </div>
        <div class="badge {badge_cls}">{ticket['投注金额']:.0f} 元</div>
      </div>
      {''.join(rows)}
      <div class="meta-grid">
        <div class="meta-cell"><div class="k">综合赔率</div><div class="v">{ticket['综合赔率']}</div></div>
        <div class="meta-cell"><div class="k">综合概率</div><div class="v">{ticket['综合概率']:.1%}</div></div>
        <div class="meta-cell"><div class="k">中奖返还</div><div class="v">{ticket['理论返还']:.2f}</div></div>
        <div class="meta-cell"><div class="k">中奖净利</div><div class="v">{ticket['中奖净利']:+.2f}</div></div>
        <div class="meta-cell"><div class="k">期望净利</div><div class="v">{ticket['期望净利']:+.2f}</div></div>
        <div class="meta-cell"><div class="k">期望 EV</div><div class="v">{ticket['期望收益EV']:+.1%}</div></div>
      </div>
      <div class="why-box">
        <div class="label">为什么这样买</div>
        {ticket['why']}
      </div>
    </div>
    """


def _compare_html(cmp: dict) -> str:
    rows = [
        '<div class="compare-row head"><div>维度</div><div>稳单</div><div>高收益</div></div>'
    ]
    for r in cmp["rows"]:
        rows.append(
            f'<div class="compare-row"><div class="dim">{r["维度"]}</div>'
            f'<div>{r["稳单保本"]}</div><div>{r["高收益"]}</div></div>'
        )
    return f"""
    <div class="compare-card">
      <div class="title">两单对比</div>
      <div class="compare-scroll">{''.join(rows)}</div>
      <div class="why-box" style="margin-top:0.75rem;background:#F4F7F5;color:#1E3328">
        <div class="label">分仓逻辑</div>
        {cmp['分仓说明']}
      </div>
      <div class="verdict">
        <b>结论</b><br/>{cmp['结论']}
      </div>
      <div class="summary-bar">
        <div class="cell"><div class="k">总成本</div><div class="v">{cmp['两单总成本']:.0f}</div></div>
        <div class="cell"><div class="k">全中返还</div><div class="v">{cmp['两单全中返还']:.2f}</div></div>
        <div class="cell"><div class="k">全中净利</div><div class="v">{cmp['两单全中净利']:+.2f}</div></div>
      </div>
    </div>
    """


with tab_fb:
    st.markdown(
        '<p class="hint">仅推荐体彩「当天销售日」可买场次（按 businessDate）；'
        "赔率来自 sporttery.cn 胜平负。编号可在体彩 App / 网点核对。</p>",
        unsafe_allow_html=True,
    )
    if "fb_seed" not in st.session_state:
        st.session_state.fb_seed = int(time.time()) % 10_000_000
    if "fb_force" not in st.session_state:
        st.session_state.fb_force = False

    budget_raw = st.number_input(
        "总成本（元）",
        min_value=2,
        max_value=1000,
        value=20,
        step=2,
        label_visibility="visible",
    )
    budget = int(budget_raw)
    if budget % 2 != 0:
        budget -= 1
    budget = max(2, min(1000, budget))
    if budget != int(budget_raw):
        st.caption(f"已校正为偶数：{budget} 元")

    c1, c2 = st.columns(2)
    with c1:
        regen = st.button("重新生成", type="primary", use_container_width=True, key="fb_regen")
    with c2:
        refresh = st.button("刷新赛程", use_container_width=True, key="fb_refresh")
    if regen:
        st.session_state.fb_seed = int(time.time() * 1000) % 10_000_000
        st.rerun()
    if refresh:
        st.session_state.fb_force = True
        st.rerun()

    tips = generate_tips(
        seed=st.session_state.fb_seed,
        total_budget=float(budget),
        force_refresh=bool(st.session_state.fb_force),
    )
    st.session_state.fb_force = False

    meta = tips.get("meta") or {}
    src = meta.get("source") or "sporttery.cn"
    upd = meta.get("updated_at") or "-"
    cnt = meta.get("match_count") or 0
    sell = meta.get("sell_date") or "-"
    st.markdown(
        f'<div class="seed-line"><span>销售日 {sell} · {cnt} 场 · {src} · {upd}</span>'
        f'<span>成本 {tips["总成本"]:.0f} 元</span></div>',
        unsafe_allow_html=True,
    )

    if tips.get("error") or not tips.get("稳单保本"):
        st.error(tips.get("error") or "暂无体彩在售足球数据")
    else:
        st.markdown(_ticket_html(tips["稳单保本"], "stable"), unsafe_allow_html=True)
        st.markdown(_ticket_html(tips["高收益"], "high"), unsafe_allow_html=True)
        st.markdown(_compare_html(tips["对比"]), unsafe_allow_html=True)


with tab_stock:
    with st.expander("策略参数", expanded=True):
        top_n = st.slider("持股数", 3, 10, 5)
        max_pos = st.slider("单票上限", 0.10, 0.40, 0.25, 0.05)
        stop_loss = st.slider("止损", -0.20, -0.03, -0.08, 0.01)
        max_dd = st.slider("回撤熔断", -0.30, -0.05, -0.15, 0.01)

    run = st.button("运行回测", type="primary", use_container_width=True, key="bt_run")

    if run:
        with st.spinner("回测中…"):
            raw = make_universe(days=504)
            fac = calc_factors(raw)
            last_dt = fac.index.max()
            latest = (
                fac.loc[last_dt]
                .dropna(subset=["score"])
                .sort_values("score", ascending=False)
            )
            strat = FactorStrategy(top_n=top_n, weight_mode="equal")
            weights = strat.generate_weights(fac)
            cfg = RiskConfig(max_pos=max_pos, stop_loss=stop_loss, max_dd=max_dd)
            result = run_backtest(raw, weights, risk_cfg=cfg)

        st.subheader("回测指标")
        m = result["metrics"]
        keys = list(m.keys())
        for i in range(0, len(keys), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j < len(keys):
                    k = keys[i + j]
                    col.metric(k, m[k])

        fig = px.line(result["nav"], y="nav", title="净值曲线")
        fig.update_layout(
            margin=dict(l=8, r=8, t=40, b=8),
            height=240,
            font=dict(size=12, family="DM Sans"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="",
            yaxis_title="净值",
            title_font=dict(family="Space Grotesk", size=14),
        )
        fig.update_traces(line_color="#146C4B", line_width=2.2)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.subheader("最新因子截面")
        show_fac = latest[
            ["symbol", "mom_20", "mom_60", "vol_20", "vol_ratio", "mr_20", "score"]
        ].round(4)
        st.dataframe(show_fac, use_container_width=True, height=220)

        st.subheader("近期交易")
        trades = result["trades"]
        if not trades.empty:
            st.dataframe(trades.tail(30), use_container_width=True, height=220)
        else:
            st.info("无交易")
