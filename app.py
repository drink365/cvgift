# app.py — 單張保單｜第 N 年變更要保人（無 RPU）｜實際數字稅試算＋優勢呈現
# 需求：pip install streamlit pandas
# 執行：streamlit run app.py

import pandas as pd
import streamlit as st

st.set_page_config(page_title="單張保單｜變更要保人稅試算（無 RPU）", layout="centered")

# ---------------- 稅制常數（114年/2025） ----------------
EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
BR10_NET_MAX = 28_110_000  # 10% 淨額上限
BR15_NET_MAX = 56_210_000  # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

MAX_ANNUAL_PREM = 100_000_000  # 單年保費上限：1 億

# ---------------- 共用樣式與工具 ----------------
st.markdown("""
<style>
.kpi {border:1px solid #ECECF3; border-radius:10px; padding:12px 14px; background:#FAFAFD;}
.kpi .label {color:#5f6368; font-size:0.95rem; margin-bottom:6px;}
.kpi .value {font-weight:700; font-variant-numeric: tabular-nums; font-size:1.05rem; line-height:1.3;}
.kpi .note  {color:#16a34a; font-size:0.9rem; margin-top:4px;}
</style>
""", unsafe_allow_html=True)

def kpi(label: str, value: str, note: str = ""):
    html = f'<div class="kpi"><div class="label">{label}</div>' \
           f'<div class="value">{value}</div>'
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
st.title("單張保單｜變更要保人壓縮課稅（無 RPU）")
st.caption("金額單位：新台幣。稅制：年免稅 2,440,000；10% 淨額上限 28,110,000；15% 淨額上限 56,210,000。")

with st.expander("計算邏輯（點我展開）", expanded=False):
    st.markdown("""
- 關係：**要保人**一代 →（第 N 年變更）→ 二代；**被保人**二代；**受益人**三代。  
- **用保單**：第 N 年把要保人改為二代，當年**視現金價值（保價金/解約金）為贈與額**。  
- **不用保單**：若不用保單、但要達到同等移轉，則為**第 1～N 年，每年贈與「年繳保費」**。  
- 每年可用**免稅 2,440,000 元**，超過部分按 **10% / 15% / 20%** 計稅。  
- 本頁只比較**到變更當年**；變更後不再由一代繳保費（不再產生一代→二代的贈與）。
""")

# ---------------- 1) 使用者輸入 ----------------
col1, col2, col3 = st.columns(3)
with col1:
    years = st.number_input("年期（年）", min_value=1, max_value=40, value=8, step=1)
with col2:
    annual_prem = st.number_input("年繳保費（元）", min_value=0, max_value=MAX_ANNUAL_PREM,
                                  value=6_000_000, step=100_000, format="%d")
with col3:
    change_year = st.number_input("變更要保人年份（N）", min_value=1, max_value=40,
                                  value=2, step=1)

if annual_prem > MAX_ANNUAL_PREM:
    st.error("年繳保費不可超過 1 億。")
    st.stop()
if change_year > years:
    st.warning("變更年份不可超過年期，已自動調整為年期。")
    change_year = years

# ---------------- 2) 自動生成「年末現金價值」表 ----------------
ratio_map = {1:0.50, 2:0.70, 3:0.80, 4:0.85, 5:0.88, 6:0.91, 7:0.93, 8:0.95}
rows, cum = [], 0
for y in range(1, years+1):
    cum += annual_prem
    ratio = ratio_map.get(y, 0.95)
    cv = int(round(cum * ratio))
    rows.append({"年度": y,
                 "年繳保費（元）": annual_prem,
                 "累計保費（元）": cum,
                 "年末現金價值（元）": cv})
df_years = pd.DataFrame(rows)

st.subheader("年度明細（依預設比率自動生成，可直接作為客戶說明）")
st.dataframe(
    df_years.assign(
        **{"年繳保費（元）": lambda d: d["年繳保費（元）"].map(fmt),
           "累計保費（元）": lambda d: d["累計保費（元）"].map(fmt),
           "年末現金價值（元）": lambda d: d["年末現金價值（元）"].map(fmt)}
    ),
    use_container_width=True
)

# ---------------- 3) 稅務比較：用保單 vs 不用保單（算到第 N 年） ----------------
cv_at_change = int(df_years.loc[df_years["年度"] == change_year, "年末現金價值（元）"].iloc[0])

# 用保單：第 N 年變更 → 當年視為贈與 = 現金價值
gift_with_policy = cv_at_change
net_with_policy = max(0, gift_with_policy - EXEMPTION)
tax_with_policy, rate_with = gift_tax(net_with_policy)

# 不用保單：第 1～N 年每年贈與 = 年繳保費
total_tax_no_policy = 0
yearly_tax_list = []
for y in range(1, change_year+1):
    net = max(0, annual_prem - EXEMPTION)
    t, rate = gift_tax(net)
    total_tax_no_policy += t
    yearly_tax_list.append({
        "年度": y,
        "現金贈與（元）": annual_prem,
        "免稅後淨額（元）": net,
        "應納贈與稅（元）": t,
        "適用稅率": rate
    })

tax_saving = total_tax_no_policy - tax_with_policy

st.subheader("到變更當年（N）為止的稅務對照")
colA, colB, colC = st.columns(3)
with colA:
    st.markdown("**用保單（第 N 年變更）**")
    kpi("變更當年視為贈與（現金價值）", fmt_y(gift_with_policy))
    kpi("當年應納贈與稅", fmt_y(tax_with_policy), note=f"稅率 {rate_with}")
with colB:
    st.markdown("**不用保單（第 1～N 年現金贈與）**")
    kpi("合計贈與稅（1～N 年）", fmt_y(total_tax_no_policy))
with colC:
    st.markdown("**差異（節稅）**")
    kpi("到第 N 年節省的贈與稅", fmt_y(tax_saving))

with st.expander("展開看『不用保單』逐年稅額", expanded=False):
    df_no = pd.DataFrame(yearly_tax_list)
    show_no = df_no.copy()
    for c in ["現金贈與（元）","免稅後淨額（元）","應納贈與稅（元）"]:
        show_no[c] = show_no[c].map(fmt_y)
    st.dataframe(show_no, use_container_width=True)

st.divider()

# ---------------- 4) 一頁就懂：保單核心價值（不只省稅） ----------------
st.subheader("一頁就懂：這張保單的核心價值（不只省稅）")
st.markdown(f"""
**① 保障放大（同樣現金流 ↔ 風險時刻放大為保額）**  
- 不用保單：最多就是把錢分年送出。  
- 用保單：在**需要的那一刻**，由保險把保障**放大成保額**（請用試算書對應你的商品保額）。  

**② 時間確定（現金在需要時直接到位）**  
- 給付不受市場波動影響，避免在緊急時刻折價賣資產（股權/不動產）。  
- 對企業主與資產多為不動產者，這是一道**流動性防火牆**。  

**③ 治理控管（誰拿、怎麼拿、何時拿）**  
- ① 先由一代掌握要保人，**第 {change_year} 年**交棒給二代；受益人與比例可設計（可搭配保險信託）以避免一次性失衡、或被外力侵蝕。  
- ② 透過**保單贈與（含變更要保人）**可做到**帳戶獨立管理**，與一般銀行往來帳戶分離，降低資金混同風險；亦可作為**婚姻財富治理**的工具，釐清贈與資金之**專屬性與用途**（如教育金、長照金），提高法律與財務上的可辨識性。  

**④ 稅務優惠（變更年認列現金價值）**  
- 用保單：只在**第 {change_year} 年**對「**現金價值**」課贈與稅（多數情況低於累計保費），上方 KPI 已顯示稅額。  
- 不用保單：必須在**第 1～{change_year} 年**每年對**年繳保費全額**課贈與稅。  
- 上方 KPI 也呈現：到第 N 年的**稅負差（節稅金額）**。
""")

st.caption("提醒：年末現金價值與最終保額以保險公司試算書為準；本工具著重稅務計算與策略展示。")
