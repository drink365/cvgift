# app.py — 用同樣現金流，更聰明完成贈與｜單張保單一鍵試算（簡易模式・高階版面）
# 執行：streamlit run app.py
# 需求：pip install streamlit pandas

import pandas as pd
import streamlit as st

st.set_page_config(page_title="用同樣現金流，更聰明完成贈與｜單張保單一鍵試算", layout="centered")

# ---------------- 稅制常數（114年/2025） ----------------
EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
BR10_NET_MAX = 28_110_000  # 10% 淨額上限
BR15_NET_MAX = 56_210_000  # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

MAX_ANNUAL   = 100_000_000  # 單年現金投入上限：1 億

# ---------------- 先初始化 Session State ----------------
DEFAULTS = {"years": 8, "annual_cash": 6_000_000, "change_year": 2}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 預設比率：Y1=50%、Y2=70%、Y3=80%、Y4=85%、Y5=88%、Y6=91%、Y7=93%、Y8=95%，>8 年維持 95%
RATIO_MAP = {1:0.50, 2:0.70, 3:0.80, 4:0.85, 5:0.88, 6:0.91, 7:0.93, 8:0.95}

# ---------------- 版面樣式（沉穩墨綠 × 香檳金） ----------------
st.markdown(
    '''
<style>
:root{
  --ink:#0f172a;           /* 深墨 */
  --soft:#f7f7fa;          /* 柔白 */
  --pine:#123b34;          /* 墨綠 */
  --pine-40:#e7efed;       /* 墨綠極淺 */
  --champ:#bfa06a;         /* 香檳金 */
  --graph:#5f6368;         /* 次要字 */
}
html,body [class^="css"]{font-family: "Noto Sans TC", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang TC", "Heiti TC", "Microsoft JhengHei", sans-serif;}
h1, h2, h3{color:var(--pine);}
.block-container{padding-top:1.8rem; padding-bottom:3rem;}
/* Title bar */
.app-title{
  border-left:6px solid var(--champ);
  padding-left:12px; margin-bottom:8px;
}
/* Subtitle */
.caption{color:var(--graph);}
/* KPI cards */
.kpi{
  border:1px solid var(--pine-40);
  border-radius:14px; background:#fff;
  padding:14px 16px; box-shadow:0 2px 10px rgba(18,59,52,.04);
}
.kpi .label{color:var(--graph); font-size:0.95rem; margin-bottom:6px;}
.kpi .value{font-weight:700; font-variant-numeric: tabular-nums; font-size:1.08rem; line-height:1.3; color:var(--ink);}
.kpi .note{color:var(--pine); font-size:0.9rem; margin-top:4px;}
.small{color:var(--graph); font-size:0.95rem;}
/* Section divider */
.hr{height:1px; background:linear-gradient(90deg, rgba(191,160,106,.45), rgba(191,160,106,.05)); margin:18px 0;}
/* Expander tweak */
[role="button"][data-baseweb="accordion"]{border-radius:12px; border:1px solid var(--pine-40);}
</style>
''',
    unsafe_allow_html=True
)

def card(label: str, value: str, note: str = ""):
    html = (
        f'<div class="kpi"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
    )
    if note:
        html += f'<div class="note">{note}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def fmt(n: float) -> str:
    return f"{n:,.0f}"

def fmt_y(n: float) -> str:
    return f"{fmt(n)} 元"

def gift_tax(net: int):
    """依累進稅率計算單年贈與稅（含基稅）。回傳 (稅額, 稅率字串)"""
    if net <= 0:
        return 0, "—"
    if net <= BR10_NET_MAX:
        return int(round(net * RATE_10)), "10%"
    if net <= BR15_NET_MAX:
        base = BR10_NET_MAX * RATE_10
        extra = (net - BR10_NET_MAX) * RATE_15
        return int(round(base + extra)), "15%"
    base = BR10_NET_MAX * RATE_10 + (BR15_NET_MAX - BR10_NET_MAX) * RATE_15
    extra = (net - BR15_NET_MAX) * RATE_20
    return int(round(base + extra)), "20%"

# ---------------- 標題與簡介 ----------------
