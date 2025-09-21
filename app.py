# app.py — 單張保單｜實際數字精算贈與稅（變更要保人壓縮課稅）｜全中文
# Run: streamlit run app.py

import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="單張保單｜贈與稅試算（變更要保人）", layout="centered")

# ---------------- 固定稅制（114年/2025） ----------------
EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
BR10_NET_MAX = 28_110_000  # 10% 淨額上限
BR15_NET_MAX = 56_210_000  # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

MAX_ANNUAL_PREMIUM = 100_000_000  # 單年保費上限：1 億

def fmt(n: float) -> str:
    return f"{n:,.0f}"

def fmt_y(n: float) -> str:
    return f"{fmt(n)} 元"

def gift_tax_by_bracket(net: int):
    """依固定稅制計算當年贈與稅（含基稅）；回傳(稅額, 最高適用稅率字串)"""
    if net <= 0: return 0, "—"
    if net <= BR10_NET_MAX:
        return int(round(net * RATE_10)), "10%"
    if net <= BR15_NET_MAX:
        base = BR10_NET_MAX * RATE_10
        extra = (net - BR10_NET_MAX) * RATE_15
        return int(round(base + extra)), "15%"
    base = BR10_NET_MAX * RATE_10 + (BR15_NET_MAX - BR10_NET_MAX) * RATE_15
    extra = (net - BR15_NET_MAX) * RATE_20
    return int(round(base + extra)), "20%"

# ---------------- 標題與說明 ----------------
st.title("單張保單｜贈與稅試算（變更要保人壓縮課稅）")
st.caption("所有金額單位：新台幣。贈與稅規則：年免稅 244 萬；10% 淨額上限 2,811 萬；15% 淨額上限 5,621 萬。")

st.markdown("""
**關係設定：** 原要保人＝第一代，變更後要保人＝第二代，受益人＝第三代。  
**稅務邏輯：**
- 變更要保人當年，**視為贈與＝當日現金價值（保單價值準備金/解約金）**。  
- 變更後若仍由第一代「代繳保費」，則**每年的代繳保費**屬於當年度的**現金贈與**。  
- 每年可用一次**免稅額 2,440,000 元**，其餘按 10%/15%/20% 計稅。
""")

# ---------------- 輸入：年期、變更年、代繳終止年 ----------------
col1, col2, col3 = st.columns(3)
with col1:
    years = st.number_input("年期（年）", min_value=1, max_value=30, value=8, step=1)
with col2:
    change_year = st.number_input("第幾年『變更要保人為二代』", min_value=1, max_value=30, value=2, step=1)
with col3:
    still_fund = st.checkbox("變更後由一代代繳保費？", value=True)

fund_until_year = change_year - 1
if still_fund:
    fund_until_year = st.number_input("一代代繳『到第幾年』為止（含該年）", min_value=change_year, max_value=30, value=max(change_year, 8), step=1)

if change_year > years or (still_fund and fund_until_year > years):
    st.warning("提示：變更年/代繳終止年不可超過年期。")
    years = max(years, change_year, (fund_until_year if still_fund else years))

# ---------------- 逐年輸入：保費與現金價值 ----------------
st.subheader("逐年輸入：年繳保費 & 年末現金價值（保單價值準備金/解約金）")

# 預設：保費 6,000,000；現金價值：第1年=當年保費×1/3，第2年=累計×1/2，之後粗略遞增（可覆寫）
rows = []
cum = 0
for y in range(1, years + 1):
    prem = 6_000_000
    cum += prem
    if y == 1:
        cv = int(round(prem * (1/3)))
    elif y == 2:
        cv = int(round(cum * (1/2)))
    else:
        # 粗略示意：第3年起逐年向累計保費靠攏（0.7, 0.8, 0.9, 0.95...）
        ratio = 0.7 + min(0.25, 0.1 * (y-3))  # 0.7, 0.8, 0.9, 1.0(封頂0.95)
        ratio = min(ratio, 0.95)
        cv = int(round(cum * ratio))
    rows.append({"年度": y, "年繳保費（元）": prem, "年末現金價值（元）": cv})

df_input = pd.DataFrame(rows)
edited = st.data_editor(
    df_input,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "年度": st.column_config.NumberColumn(format="%d", disabled=True),
        "年繳保費（元）": st.column_config.NumberColumn(format="%d", min_value=0, max_value=MAX_ANNUAL_PREMIUM, step=100_000),
        "年末現金價值（元）": st.column_config.NumberColumn(format="%d", min_value=0, step=100_000),
    },
    key="input_editor"
)

# 校驗：單年保費不可超過 1 億
if (edited["年繳保費（元）"] > MAX_ANNUAL_PREMIUM).any():
    st.error("有年度的保費超過 1 億上限，請調整後再計算。")
    st.stop()

# ---------------- 計算：逐年贈與額、淨額與稅 ----------------
st.subheader("計算結果｜逐年贈與稅")
calc_rows = []
legal_gift_total = 0
tax_total = 0

for _, r in edited.iterrows():
    y = int(r["年度"])
    prem = int(r["年繳保費（元）"])
    cv = int(r["年末現金價值（元）"])

    gift = 0
    note = "—"
    # 變更年：視為贈與 = 現金價值
    if y == change_year:
        gift += cv
        note = "變更要保人→以當年現金價值視為贈與"
    # 變更後、且一代仍代繳之年度：當年保費視為現金贈與
    if still_fund and (y >= change_year) and (y <= fund_until_year):
        gift += prem
        note = "變更後由一代代繳保費→當年現金贈與" if y != change_year else "變更＋代繳保費皆計入"

    net = max(0, gift - EXEMPTION)
    tax, rate = gift_tax_by_bracket(net)

    legal_gift_total += gift
    tax_total += tax

    calc_rows.append({
        "年度": y,
        "當年視為贈與（元）": gift,
        "免稅後淨額（元）": net,
        "應納贈與稅（元）": tax,
        "適用稅率": rate,
        "說明": note
    })

df_calc = pd.DataFrame(calc_rows)

show = df_calc.copy()
for col in ["當年視為贈與（元）", "免稅後淨額（元）", "應納贈與稅（元）"]:
    show[col] = show[col].map(fmt_y)

st.dataframe(show, use_container_width=True)

st.markdown(
    f"""
**合計（透過保單）**  
- 法律上已完成之贈與總額：**{fmt_y(legal_gift_total)}**  
- 累計贈與稅：**{fmt_y(tax_total)}**
"""
)

# ---------------- 對照：不用保單（直接現金贈與） ----------------
st.subheader("對照｜不用保單（直接現金贈與）")
# 以「實際由一代支付的年數與金額」做公平對照：= 變更後仍代繳到 fund_until_year 的那段保費 + 變更前的保費也可納入對照（若你想比總現金流）
# 這裡提供兩個口徑：A 只比「變更後代繳段」、B 比「全期保費」
prem_series = edited["年繳保費（元）"].astype(int).tolist()

# A：僅將「實際代繳期間（變更後至 fund_until_year）」視為對照現金贈與
no_policy_stream_A = [
    (i+1, p) for i, p in enumerate(prem_series)
    if (i+1) >= change_year and (not still_fund or (i+1) <= fund_until_year)
]

# B：整張保單之保費（若想比較「完全不用保單、純現金逐年贈與」的總稅）
no_policy_stream_B = [(i+1, p) for i, p in enumerate(prem_series)]

def sum_tax_on_stream(stream):
    total = 0
    for y, amt in stream:
        net = max(0, amt - EXEMPTION)
        tax, _ = gift_tax_by_bracket(net)
        total += tax
    return total, sum(amt for _, amt in stream)

tax_A, sum_A = sum_tax_on_stream(no_policy_stream_A)
tax_B, sum_B = sum_tax_on_stream(no_policy_stream_B)

st.markdown(
    f"""
- **口徑 A（只比變更後代繳的那段現金流）**：  
  ・現金贈與總額：**{fmt_y(sum_A)}**；累計贈與稅：**{fmt_y(tax_A)}**

- **口徑 B（全期保費都改成現金贈與）**：  
  ・現金贈與總額：**{fmt_y(sum_B)}**；累計贈與稅：**{fmt_y(tax_B)}**
"""
)

# ---------------- 客戶易懂的邏輯（話術） ----------------
st.subheader("給客戶的一分鐘說明（可直接念）")
st.markdown(f"""
- 這張保單目前要保人是一代、被保人是二代、受益人是三代。  
- 我們在「第 {change_year} 年」把**要保人變更給二代**，當天的**現金價值**就被視為**當年的贈與金額**。  
- 如果變更後還是由一代代繳保費（到第 {fund_until_year if still_fund else change_year-1} 年），那些年度的保費也算是**當年的現金贈與**。  
- 每年有**免稅額 244 萬**，超過的部分按 **10%/15%/20%** 計稅；上表已用你提供的「保費與現金價值**真實數字**」逐年把稅算出來。  
- 意義：把「前幾年的投入」在變更當年**用現金價值**來認列（通常**低於累計保費**），可以**壓低課稅基礎**；  
  之後是否繼續代繳、繳到哪一年，我們就用「現金贈與」去安排每年的稅，**彈性掌握在你手上**。  
""")

st.caption("提醒：現金價值/繳清保額請以保險公司之試算書為準；本工具只做稅務計算與策略排程。")
