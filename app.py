# app.py — 單張保單｜第1/第2年變更要保人｜實際數字算贈與稅＋說服力展示（無 RPU）
# 需求：pip install streamlit pandas

import pandas as pd
import streamlit as st

st.set_page_config(page_title="單張保單：變更要保人｜贈與稅試算（無 RPU）", layout="centered")

# ---------------- 稅制常數（114年/2025） ----------------
EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
BR10_NET_MAX = 28_110_000  # 10% 淨額上限
BR15_NET_MAX = 56_210_000  # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

MAX_ANNUAL_PREM = 100_000_000  # 單年保費上限：1 億

def fmt(n: float) -> str:
    return f"{n:,.0f}"

def fmt_y(n: float) -> str:
    return f"{fmt(n)} 元"

def gift_tax(net: int):
    """依累進稅率計算當年贈與稅（含基稅）。回傳(稅額, 稅率字串)"""
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

# ---------------- 標題與規則說明 ----------------
st.title("單張保單｜變更要保人壓縮課稅（無 RPU）")
st.caption("金額單位：新台幣。稅制：年免稅 2,440,000；10% 淨額上限 28,110,000；15% 淨額上限 56,210,000。")

with st.expander("規則怎麼算？點我展開", expanded=False):
    st.markdown("""
- **關係設定**：原要保人＝一代，被保人＝二代，受益人＝三代。  
- **變更年**：把要保人由一代改為二代，**當年視為贈與＝當日現金價值（保價金/解約金）**。  
- **變更後代繳保費**：若仍由一代出錢繳保費，該年度保費屬**現金贈與**。  
- 每年可用**免稅 244 萬**，超過部分依 10% / 15% / 20% 累進計稅。
- 本工具不做 RPU；只比較**第1年變更** vs **第2年變更**的策略影響。
""")

# ---------------- 1) 基本參數 ----------------
col1, col2, col3 = st.columns([1,1,1])
with col1:
    years = st.number_input("年期（年）", min_value=1, max_value=30, value=8, step=1)
with col2:
    change_year = st.selectbox("變更要保人年份", options=[1,2], index=1)  # 預設第2年
with col3:
    fund_until_year = st.number_input("一代代繳到第幾年（含）", min_value=change_year, max_value=30, value=years, step=1)

st.subheader("逐年輸入：年繳保費與年末現金價值（保價金/解約金）")
# 預設示意：年繳 6,000,000；第1年現金價值≈首年×1/3；第2年≈累計×1/2；其後逐年上升（可覆寫）
rows = []
cum = 0
for y in range(1, years+1):
    prem = 6_000_000
    cum += prem
    if y == 1:
        cv = int(round(prem * (1/3)))
    elif y == 2:
        cv = int(round(cum * (1/2)))
    else:
        ratio = min(0.95, 0.6 + 0.1*(y-1))  # 0.7,0.8,0.9,1.0→上限設0.95
        cv = int(round(cum * ratio))
    rows.append({"年度": y, "年繳保費（元）": prem, "年末現金價值（元）": cv})

df_input = pd.DataFrame(rows)
edited = st.data_editor(
    df_input,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "年度": st.column_config.NumberColumn(format="%d", disabled=True),
        "年繳保費（元）": st.column_config.NumberColumn(format="%d", min_value=0, max_value=MAX_ANNUAL_PREM, step=100_000),
        "年末現金價值（元）": st.column_config.NumberColumn(format="%d", min_value=0, step=100_000),
    },
    key="input_table"
)

# 驗證：單年保費<=1億
if (edited["年繳保費（元）"] > MAX_ANNUAL_PREM).any():
    st.error("有年度保費超過 1 億上限，請調整後再試。")
    st.stop()

# ---------------- 2) 計算（依法條邏輯） ----------------
st.subheader("逐年稅額試算（依你輸入的真實數字）")
calc_rows = []
gift_total = 0
tax_total = 0
prem_total = 0

for _, r in edited.iterrows():
    y   = int(r["年度"])
    prem= int(r["年繳保費（元）"])
    cv  = int(r["年末現金價值（元）"])
    prem_total += prem

    gift = 0
    note = "—"

    if y == change_year:
        gift += cv
        note = "變更要保人→以當年現金價值視為贈與"

    if (y >= change_year) and (y <= fund_until_year):
        gift += prem
        note = "變更後由一代代繳保費→當年現金贈與" if y != change_year else "變更＋代繳保費皆計入"

    net = max(0, gift - EXEMPTION)
    tax, rate = gift_tax(net)

    gift_total += gift
    tax_total  += tax

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
for col in ["當年視為贈與（元）","免稅後淨額（元）","應納贈與稅（元）"]:
    show[col] = show[col].map(fmt_y)
st.dataframe(show, use_container_width=True)

st.markdown(f"""
**透過保單（本策略）合計**  
- 法律上視為已贈與總額：**{fmt_y(gift_total)}**  
- 累計贈與稅：**{fmt_y(tax_total)}**
""")

# ---------------- 3) 不用保單（對照） ----------------
st.subheader("對照：不用保單（改成直接現金贈與）")
# 公平做法：用「變更後你實際代繳到 fund_until_year 的那些年」作對照（A），也提供全期保費（B）
streamA = [(int(r["年度"]), int(r["年繳保費（元）"])) for _, r in edited.iterrows()
           if (int(r["年度"]) >= change_year) and (int(r["年度"]) <= fund_until_year)]
streamB = [(int(r["年度"]), int(r["年繳保費（元）"])) for _, r in edited.iterrows()]

def sum_tax(stream):
    total_tax = 0
    total_amt = 0
    for _, amt in stream:
        net = max(0, amt - EXEMPTION)
        t, _ = gift_tax(net)
        total_tax += t
        total_amt += amt
    return total_amt, total_tax

amtA, taxA = sum_tax(streamA)
amtB, taxB = sum_tax(streamB)

st.markdown(f"""
- **口徑 A**（僅比較「變更後你實際代繳」那段現金流）：  
  ・現金贈與總額：**{fmt_y(amtA)}**；累計贈與稅：**{fmt_y(taxA)}**

- **口徑 B**（全期保費全部改為現金贈與）：  
  ・現金贈與總額：**{fmt_y(amtB)}**；累計贈與稅：**{fmt_y(taxB)}**
""")

st.divider()

# ---------------- 4) 說服客戶：保單優勢 + 稅務優惠（簡明話術） ----------------
st.subheader("一頁就懂：為什麼要用保單（除了節稅）")
st.markdown(f"""
**① 放大（保障倍數）**  
- 同樣的現金流，保險把「事件發生當下」的現金**放大到保額**（請用試算書告知對應保額），常見遠高於單純把錢分年送出去。  

**② 確定（現金到位的時間與金額）**  
- 給付在最需要的時點直接入帳，不受市況影響，不用急賣資產。這是家族資金的**流動性保險絲**。  

**③ 控管（治理與規則）**  
- 先由一代掌握要保人身分，**第 {change_year} 年**再交棒給二代；受益人與比例可設計（可搭配保險信託）以防一次性失衡。  

**④ 稅務優惠（搭配變更要保人）**  
- 變更當年只對「**當日現金價值**」課贈與稅（多數情況低於累計保費），之後若一代代繳，逐年用**免稅 244 萬+10% 級距**消化。  
- 對照「不用保單」：完全以現金贈與，**每年全額進入課稅基礎**。  
- 上表已用你的**真實數字**算出兩種口徑（A/B）的稅差，方便當場對比。
""")

st.caption("備註：最終保額與現金價值以保險公司試算書為準。本工具僅提供稅務計算與策略展示。")
