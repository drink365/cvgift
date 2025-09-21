# app.py — Taiwan Gift Tax Planner (single donor) for Policy Owner Change + Cash Gifts
# Run: streamlit run app.py

import streamlit as st
import pandas as pd

st.set_page_config(page_title="贈與稅 × 保單要保人變更｜單一贈與人試算", layout="centered")

# ------------------------- Constants (editable via UI) -------------------------
DEFAULT_EXEMPTION = 2_440_000          # 年免稅額（單一贈與人）
DEFAULT_BRACKET_10_MAX_NET = 28_110_000  # 10% 級距淨額上限
DEFAULT_BRACKET_15_MAX_NET = 56_210_000  # 15% 級距淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

def fmt(n: float) -> str:
    return f"{n:,.0f}"

def gift_tax(net: float, br10: int, br15: int):
    if net <= 0:
        return 0.0, 0.0, 0.0
    if net <= br10:
        return net * RATE_10, RATE_10, 0.0
    if net <= br15:
        base = br10 * RATE_10
        extra = (net - br10) * RATE_15
        return base + extra, RATE_15, base
    base = br10 * RATE_10 + (br15 - br10) * RATE_15
    extra = (net - br15) * RATE_20
    return base + extra, RATE_20, base

# ------------------------------- Sidebar --------------------------------------
with st.sidebar:
    st.markdown("### 參數調整（若法規異動可在此微調）")
    exemption = st.number_input("年免稅額（單一贈與人）", min_value=0, step=10_000,
                                value=DEFAULT_EXEMPTION, format="%d")
    br10 = st.number_input("10% 級距淨額上限", min_value=0, step=10_000,
                           value=DEFAULT_BRACKET_10_MAX_NET, format="%d")
    br15 = st.number_input("15% 級距淨額上限", min_value=0, step=10_000,
                           value=DEFAULT_BRACKET_15_MAX_NET, format="%d")

# ------------------------------ Header ----------------------------------------
st.title("贈與稅 × 保單要保人變更｜單一贈與人試算")
st.caption("說明：預設採 2025（114年）台灣贈與稅級距；夫妻欲套用 X2，將結果倍增即可。")

# ------------------------------ Inputs ----------------------------------------
st.subheader("一、保單變更要保人（當年合併計算）")
st.markdown("第1年評價＝**年繳×1/3**；第2年評價＝**兩年累計保費×1/4**（等於年繳×0.5）。")

n = st.number_input("本年度要變更要保人的保單張數", min_value=0, max_value=20, value=3, step=1)
total_ownerchange_gift = 0.0
rows = []

for i in range(n):
    c1, c2, c3 = st.columns([1.4, 1.1, 1.2])
    with c1:
        prem = st.number_input(f"第 {i+1} 張｜年繳保費（元）", min_value=0, step=100_000,
                               value=0, key=f"prem_{i}")
    with c2:
        when = st.selectbox(f"第 {i+1} 張｜變更時點",
                            ["第1年（CV=1/3×首年保費）", "第2年（CV=1/4×兩年總保費）"],
                            key=f"yr_{i}")
    if when.startswith("第1年"):
        cv = prem * (1/3)
    else:
        cv = (prem * 2) * (1/4)  # 兩年總保費 × 1/4 = 年繳 × 0.5
    total_ownerchange_gift += cv
    with c3:
        st.metric("贈與評價（現金價值）", f"${fmt(cv)}")
    rows.append({"#": i+1, "年繳保費": fmt(prem),
                 "變更時點": "第1年" if when.startswith("第1年") else "第2年",
                 "贈與評價（元）": fmt(cv)})

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

st.divider()

st.subheader("二、當年現金贈與（如：直接資助保費）")
cash_gift = st.number_input("本年度欲另外進行的現金贈與總額（元）",
                            min_value=0, step=100_000, value=0, format="%d")

st.divider()

st.subheader("三、合併計算（本年度）")
gross = total_ownerchange_gift + cash_gift
net = max(0.0, gross - exemption)
tax, applied_rate, base_tax = gift_tax(net, br10, br15)

cA, cB, cC = st.columns(3)
with cA:
    st.metric("合併贈與總額（元）", f"${fmt(gross)}")
with cB:
    st.metric("扣除免稅額後之應稅額（元）", f"${fmt(net)}")
with cC:
    rate_label = "10%" if applied_rate == RATE_10 else ("15%" if applied_rate == RATE_15 else ("20%" if applied_rate == RATE_20 else "—"))
    st.metric("適用稅率", rate_label)

st.markdown(f"### ➤ 本年度**應納贈與稅**：**${fmt(tax)}**")

with st.expander("試算細節"):
    # 分成兩條列出，避免 % 與數字黏連造成渲染異常
    st.markdown(f"- 單一贈與人免稅額：**${fmt(exemption)}**")
    st.markdown(f"- **10%** 淨額上限：**${fmt(br10)}**")
    st.markdown(f"- **15%** 淨額上限：**${fmt(br15)}**")
    st.markdown("- 若進入 **15%/20%** 級距，已含基礎稅額（10%段/15%段）再加超額部分。")

st.divider()

# --------------------------- Capacity under 10% -------------------------------
st.subheader("四、在 10% 稅率內的承作上限（單一贈與人）")
cap_gross_at_10 = exemption + br10              # 244萬 + 2,811萬 = 3,055萬
cap_cash = cap_gross_at_10
cap_prem_y1 = cap_gross_at_10 * 3               # 第1年變更：評價=年繳×1/3 → 年繳上限=3×cap
cap_prem_y2_each_year = cap_gross_at_10 * 2     # 第2年變更：評價=兩年總×1/4 → 年繳上限=2×cap（等額連繳）

cap_df = pd.DataFrame([
    {"情境": "直接現金贈與（當年）", "10% 稅率內之承作上限（元）": fmt(cap_cash), "說明": "合併金額（含免稅）不超過此值，淨額即 ≤10% 門檻"},
    {"情境": "第1年變更要保人（CV=1/3）", "10% 稅率內之承作上限（元）": fmt(cap_prem_y1), "說明": "可支援的『首年年繳保費』上限"},
    {"情境": "第2年變更要保人（CV=1/4）", "10% 稅率內之承作上限（元）": fmt(cap_prem_y2_each_year), "說明": "可支援的『每年年繳保費』上限（連繳2年）"},
])
st.dataframe(cap_df, use_container_width=True)

st.info("本工具為**單一贈與人**視角。若夫妻兩人各自為贈與人，理論上可將上限與結果 **×2**。")

st.divider()

st.markdown(
    """
### 使用說明
- 「變更要保人」的贈與評價以當年**現金價值（解約金）**近似：  
  - 第1年：**年繳 × 1/3**  
  - 第2年：**兩年累計保費 × 1/4**（≈ 年繳 × 0.5）
- 合併試算：本年度所有變更與現金贈與將**合併**，套用一位贈與人的免稅額與級距計稅。  
- 申報提醒：贈與行為發生後 **30 日內**申報；建議向保險公司索取**變更當日的現金價值證明**備查。  
- 免責：本工具為規劃試算；實務以保單條款、試算書與主管機關規定為準。
"""
)
