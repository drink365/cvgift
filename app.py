# app.py — 保單規劃（極簡輸入版）
# 執行：streamlit run app.py
# 需求：pip install streamlit pandas

import streamlit as st

st.set_page_config(page_title="保單規劃｜極簡輸入", layout="wide")

# ---------------- 預設常數 ----------------
MAX_ANNUAL = 100_000_000  # 年繳保費上限（防呆）

DEFAULTS = {
    "annual_prem": 10_000_000,  # 年繳保費：預設 1,000 萬
    "change_year": 1,           # 第幾年變更要保人：1～6（預設 1）

    # 三年保價金（年末現金價值）：預設值
    "y1_cv": 5_000_000,
    "y2_cv": 14_000_000,
    "y3_cv": 24_000_000,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- 樣式（簡潔） ----------------
st.markdown(
    """
<style>
:root { --ink:#0f172a; --sub:#475569; --line:#E6E8EF; --bg:#FAFBFD; --gold:#C8A96A; }
.block-container { max-width:980px; padding-top:1rem; padding-bottom:2rem; }
h1,h2,h3 { letter-spacing:.3px; }
.hr { border:none; border-top:1px solid var(--line); margin:16px 0; }
.note { color:var(--sub); font-size:.92rem; }
.kpi{ border:1px solid var(--line); border-left:5px solid var(--gold); border-radius:12px; padding:12px 14px; background:#fff; }
.kpi .label{ color:var(--sub); font-size:.92rem; margin-bottom:6px;}
.kpi .value{ font-weight:700; font-variant-numeric:tabular-nums; font-size:1.05rem; }
</style>
""",
    unsafe_allow_html=True
)

# ---------------- 行為：年繳保費變更時清空保價 ----------------
def _on_prem_change():
    """當年繳保費變更時，自動清空第 1～3 年保價金。"""
    st.session_state.y1_cv = 0
    st.session_state.y2_cv = 0
    st.session_state.y3_cv = 0

# ---------------- 標題 ----------------
st.title("保單規劃｜極簡輸入")
st.caption("請輸入年繳保費、變更年度與前三年保價金；其餘功能已移除，保留最核心的輸入邏輯。")

# ---------------- 輸入區 ----------------
with st.container():
    c1, c2 = st.columns([2, 1])

    with c1:
        st.number_input(
            "年繳保費（元）",
            min_value=0,
            max_value=MAX_ANNUAL,
            step=100_000,
            format="%d",
            key="annual_prem",
            on_change=_on_prem_change,
            help="預設 10,000,000（1,000 萬）。如改動，系統會把 1~3 年保價金清空為 0，請自行輸入。"
        )
    with c2:
        st.number_input(
            "第幾年變更要保人（交棒）",
            min_value=1,
            max_value=6,
            step=1,
            key="change_year",
            help="預設第 1 年，最多第 6 年。"
        )

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# 根據年繳保費，動態計算三年保價金的上限
p = int(st.session_state.annual_prem)
max_y1 = p * 1
max_y2 = p * 2
max_y3 = p * 3

# 若目前值高於上限（例如用戶先輸入保價金再降低保費），主動壓回上限
if st.session_state.y1_cv > max_y1:
    st.session_state.y1_cv = max_y1
if st.session_state.y2_cv > max_y2:
    st.session_state.y2_cv = max_y2
if st.session_state.y3_cv > max_y3:
    st.session_state.y3_cv = max_y3

st.subheader("前三年保價金（年末現金價值）")
st.markdown('<p class="note">限制：第 1 年 ≤ 年繳保費；第 2 年 ≤ 2 × 年繳保費；第 3 年 ≤ 3 × 年繳保費。</p>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.number_input(
        "第 1 年保價金（元）",
        min_value=0,
        max_value=max_y1,
        step=100_000,
        format="%d",
        key="y1_cv"
    )
with c2:
    st.number_input(
        "第 2 年保價金（元）",
        min_value=0,
        max_value=max_y2,
        step=100_000,
        format="%d",
        key="y2_cv"
    )
with c3:
    st.number_input(
        "第 3 年保價金（元）",
        min_value=0,
        max_value=max_y3,
        step=100_000,
        format="%d",
        key="y3_cv"
    )

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# 簡要展示目前設定（方便核對）
def _fmt(n: int) -> str:
    return f"{n:,.0f}"

colA, colB, colC, colD = st.columns(4)
with colA:
    st.markdown('<div class="kpi"><div class="label">年繳保費</div>'
                f'<div class="value">{_fmt(p)} 元</div></div>', unsafe_allow_html=True)
with colB:
    st.markdown('<div class="kpi"><div class="label">變更要保人年度</div>'
                f'<div class="value">第 {int(st.session_state.change_year)} 年</div></div>', unsafe_allow_html=True)
with colC:
    st.markdown('<div class="kpi"><div class="label">第 1 年保價金</div>'
                f'<div class="value">{_fmt(int(st.session_state.y1_cv))} 元</div></div>', unsafe_allow_html=True)
with colD:
    st.markdown('<div class="kpi"><div class="label">第 2 / 第 3 年保價金</div>'
                f'<div class="value">{_fmt(int(st.session_state.y2_cv))} ／ {_fmt(int(st.session_state.y3_cv))} 元</div></div>', unsafe_allow_html=True)

st.markdown(
    '<p class="note">＊此版僅保留欄位與限制邏輯，未含其他試算或敘述模組。</p>',
    unsafe_allow_html=True
)
