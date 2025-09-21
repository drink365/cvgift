# app.py — Taiwan Gift Tax Planner (single donor) for Policy Owner Change + Cash Gifts
# Author: Grace FO helper
# Run: streamlit run app.py

import streamlit as st
import pandas as pd

st.set_page_config(page_title="贈與稅 × 保單要保人變更｜單一贈與人試算", layout="centered")

# ------------------------- Constants (editable via UI) -------------------------
DEFAULT_EXEMPTION = 2_440_000          # 年免稅額（單一贈與人）
BRACKET_10_MAX_NET = 28_110_000        # 10% 級距淨額上限
BRACKET_15_MAX_NET = 56_210_000        # 15% 級距淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

# Helper for number formatting
def fmt(n):
    return f"{n:,.0f}"

# Gift tax calculator (piecewise with base tax)
def gift_tax(net):
    if net <= 0:
        return 0.0, 0.0, 0.0
    if net <= BRACKET_10_MAX_NET:
        return net * RATE_10, RATE_10, 0.0
    if net <= BRACKET_15_MAX_NET:
        base = BRACKET_10_MAX_NET * RATE_10
        extra = (net - BRACKET_10_MAX_NET) * RATE_15
        return base + extra, RATE_15, base
    base = BRACKET_10_MAX_NET * RATE_10 + (BRACKET_15_MAX_NET - BRACKET_10_MAX_NET) * RATE_15
    extra = (net - BRACKET_15_MAX_NET) * RATE_20
    return base + extra, RATE_20, base

# ------------------------------- Sidebar --------------------------------------
with st.sidebar:
    st.markdown("### 參數調整（如未來法規異動，可於此微調）")
    exemption = st.number_input("年免稅額（單一贈與人）", min_value=0, step=10_000, value=DEFAULT_EXEMPTION, format="%d")
    br10 = st.number_input("10% 級距淨額上限", min_value=0, step=10_000, value=BRACKET_10_MAX_NET, format="%d")
    br15 = st.number_input("15% 級距淨額上限", min_value=0, step=10_000, value=BRACKET_15_MAX_NET, format="%d")
    # 覆寫到全域（供即時計算）
    BRACKET_10_MAX_NET = br10
    BRACKET_15_MAX_NET = br15

# ------------------------------ Header ----------------------------------------
st.title("贈與稅 × 保單要保人變更｜單一贈與人試算")
st.caption("說明：本工具以 2025（114年）台灣贈與稅級距為預設，單一贈與人視角試算；夫妻欲套用 X2，將結果倍增即可。")

# ------------------------------ Inputs ----------------------------------------
st.subheader("一、保單變更要保人（當年合併計算）")
st.markdown("選擇每張保單在**第1年**或**第2年**變更要保人，用既定評價係數：第1年＝**當年保費×1/3**；第2年＝**兩年保費總額×1/4**。")

n = st.number_input("本年度要變更要保人的保單張數", min_value=0, max_value=20, value=3, step=1)
policies = []
total_ownerchange_gift = 0.0

if n > 0:
    df_rows = []
    for i in range(n):
        col1, col2, col3 = st.columns([1.4, 1.0, 1.2])
        with col1:
            annual_prem = st.number_input(f"第 {i+1} 張｜年繳保費（元）", min_value=0, step=100_000, value=0, key=f"prem_{i}")
        with col2:
            year_choice = st.selectbox(f"第 {i+1} 張｜變更時點", options=["第1年（CV=1/3×首年保費）", "第2年（CV=1/4×兩年總保費）"], key=f"year_{i}")
        with col3:
            st.write("")  # spacer
            if year_choice.startswith("第1年"):
                cv = annual_prem * (1/3)
            else:
                cv = (annual_prem * 2) * (1/4)   # 兩年總保費 × 1/4 = 年繳 × 0.5
            st.metric(label="該張贈與評價（現金價值）", value=f"${fmt(cv)}")
        total_ownerchange_gift += cv
        df_rows.append({"#": i+1,
                        "年繳保費": fmt(annual_prem),
                        "變更時點": "第1年" if year_choice.startswith("第1年") else "第2年",
                        "贈與評價（元）": fmt(cv)})
    if df_rows:
        st.dataframe(pd.DataFrame(df_rows), use_container_width=True)

st.divider()

st.subheader("二、當年現金贈與（如：直接資助保費）")
cash_gift = st.number_input("本年度欲另外進行的現金贈與總額（元）", min_value=0, step=100_000, value=0, format="%d")

st.divider()

st.subheader("三、合併計算（本年度）")
gross_gift = total_ownerchange_gift + cash_gift
net_gift = max(0.0, gross_gift - exemption)
tax, applied_rate, base_tax = gift_tax(net_gift)

colA, colB, colC = st.columns(3)
with colA:
    st.metric("合併贈與總額（元）", f"${fmt(gross_gift)}")
with colB:
    st.metric("扣除免稅額後之應稅額（元）", f"${fmt(net_gift)}")
with colC:
    rate_label = "10%" if applied_rate == RATE_10 else ("15%" if applied_rate == RATE_15 else ("20%" if applied_rate == RATE_20 else "—"))
    st.metric("適用稅率", rate_label)

st.markdown(f"### ➤ 本年度**應納贈與稅**：**${fmt(tax)}**")

with st.expander("試算細節"):
    st.write(f"- 單一贈與人免稅額：${fmt(exemption)}")
    st.write(f"- 10% 淨額上限：${fmt(BRACKET_10_MAX_NET)}；15% 上限：${fmt(BRACKET_15_MAX_NET)}")
    st.write(f"- 若進入 15%/20% 級距，已含基礎稅額（10%段/15%段）再加超額部分。")

st.divider()

# --------------------------- Capacity under 10% -------------------------------
st.subheader("四、在 10% 稅率內的「承作上限」參考（單一贈與人）")
cap_gross_at_10 = exemption + BRACKET_10_MAX_NET  # 244萬 + 2,811萬 = 3,055萬
cap_cash = cap_gross_at_10
cap_prem_y1 = cap_gross_at_10 * 3          # 第1年變更：評價=年繳×1/3 → 年繳上限=3×cap
cap_prem_y2_each_year = cap_gross_at_10 * 2 # 第2年變更：評價=兩年總×1/4 → 年繳上限=2×cap（等額連繳）

cap_df = pd.DataFrame([
    {"情境": "直接現金贈與（當年）", "10% 稅率內之承作上限（元）": fmt(cap_cash), "說明": "合併金額（含免稅）不超過此值，淨額即 ≤10% 門檻"},
    {"情境": "第1年變更要保人（CV=1/3）", "10% 稅率內之承作上限（元）": fmt(cap_prem_y1), "說明": "可支援的『首年年繳保費』上限"},
    {"情境": "第2年變更要保人（CV=1/4）", "10% 稅率內之承作上限（元）": fmt(cap_prem_y2_each_year), "說明": "可支援的『每年年繳保費』上限（連繳2年）"},
])
st.dataframe(cap_df, use_container_width=True)

st.info(
    "小提醒：本工具為單一贈與人視角。若夫妻各自為贈與人，理論上可將上限與試算結果 **×2**。"
)

st.divider()

# ------------------------------ Notes -----------------------------------------
st.markdown(
    """
### 使用說明
- 「變更要保人」的贈與評價以當年**現金價值（解約金）**近似：  
  - 第1年變更：**年繳保費 × 1/3**  
  - 第2年變更：**兩年累計保費 × 1/4**（等於 **年繳 × 0.5**）
- 合併試算：本年度所有變更與現金贈與將**合併**，套用一位贈與人的免稅額與級距計稅。  
- 實務申報：贈與行為發生後 **30 日內**申報；建議向保險公司索取變更當日的**現金價值/解約金證明**備查。  
- 免責：本工具為規劃試算，實際以保單條款、試算書、與主管機關規定為準。
"""
)

