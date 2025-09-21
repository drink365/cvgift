# app.py — 單張保單｜第N年變更要保人（無RPU）｜實際數字稅試算＋優勢呈現
# 執行：streamlit run app.py
# 需求：pip install streamlit pandas

import pandas as pd
import streamlit as st

st.set_page_config(page_title="單張保單｜變更要保人稅試算（無RPU）", layout="centered")

# ---------- 稅制常數（114年/2025） ----------
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
    """依累進稅率計算單年贈與稅（含基稅）。回傳(稅額, 稅率字串)"""
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

# ---------- 標題與規則說明 ----------
st.title("單張保單｜變更要保人壓縮課稅（無 RPU）")
st.caption("金額單位：新台幣。稅制：年免稅 2,440,000；10% 淨額上限 28,110,000；15% 淨額上限 56,210,000。")

with st.expander("計算邏輯（點我展開）", expanded=False):
    st.markdown("""
- 家族設定：要保人一代 →（第 N 年變更）→ 二代；被保人＝二代；受益人＝三代。  
- **用保單**：第 N 年把要保人改為二代，當年**視現金價值（保價金/解約金）為贈與額**。  
- **不用保單**：同等移轉若以現金贈與，則為**第 1～N 年，每年贈與「年繳保費」**。  
- 每年可用**免稅 244 萬**，超過部分按 10%/15%/20% 計稅。  
- 本頁**只比較到變更當年**，變更後不再由一代繳保費（即不再產生一代→二代的贈與）。
""")

# ---------- 1) 使用者輸入 ----------
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
    st.warning("變更年份不可超過年期，已自動調整。")
    change_year = years

# ---------- 2) 產生年末現金價值表（預設比率，可顯示、可覆寫） ----------
# 預設比率：Y1=50%、Y2=70%、Y3=80%、Y4=85%、Y5=88%、Y6=91%、Y7=93%、Y8=95%，>8年維持95%
ratio_map = {1:0.50, 2:0.70, 3:0.80, 4:0.85, 5:0.88, 6:0.91, 7:0.93, 8:0.95}
default_rows, cum = [], 0
for y in range(1, years+1):
    cum += annual_prem
    ratio = ratio_map.get(y, 0.95)
    cv = int(round(cum * ratio))
    default_rows.append({"年度": y, "年繳保費（元）": annual_prem, "累計保費（元）": cum, "年末現金價值（元）": cv})

st.subheader("年度明細（預設比率自動生成）")
st.dataframe(
    pd.DataFrame(default_rows).assign(
        **{"年繳保費（元）": lambda d: d["年繳保費（元）"].map(fmt),
           "累計保費（元）": lambda d: d["累計保費（元）"].map(fmt),
           "年末現金價值（元）": lambda d: d["年末現金價值（元）"].map(fmt)}
    ),
    use_container_width=True
)

# ---------- 3) 稅務比較：用保單 vs 不用保單（只算到第 N 年） ----------
cv_at_change = default_rows[change_year-1]["年末現金價值（元）"]

# 用保單（第N年變更）：當年贈與 = 現金價值
gift_with_policy = cv_at_change
net_with_policy = max(0, gift_with_policy - EXEMPTION)
tax_with_policy, rate_with = gift_tax(net_with_policy)

# 不用保單：第1～N年，每年贈與 = 年繳保費
yearly_tax_list = []
total_tax_no_policy = 0
for y in range(1, change_year+1):
    net = max(0, annual_prem - EXEMPTION)
    t, rate = gift_tax(net)
    yearly_tax_list.append({"年度": y, "現金贈與（元）": annual_prem, "免稅後淨額（元）": net, "應納贈與稅（元）": t, "適用稅率": rate})
    total_tax_no_policy += t

# 節稅效果（到第N年）
tax_saving = total_tax_no_policy - tax_with_policy

st.subheader("到變更當年（N）為止的稅務對照")
colA, colB, colC = st.columns(3)
with colA:
    st.markdown("**用保單（第 N 年變更）**")
    st.metric(label="變更當年視為贈與（現金價值）", value=fmt_y(gift_with_policy))
    st.metric(label="當年應納贈與稅", value=fmt_y(tax_with_policy), delta=f"稅率 {rate_with}")
with colB:
    st.markdown("**不用保單（第1～N年現金贈與）**")
    st.metric(label="合計贈與稅（1～N年）", value=fmt_y(total_tax_no_policy))
with colC:
    st.markdown("**差異（節稅）**")
    st.metric(label="到第 N 年節省的贈與稅", value=fmt_y(tax_saving))

with st.expander("展開看『不用保單』逐年稅額", expanded=False):
    df_no = pd.DataFrame(yearly_tax_list)
    show_no = df_no.copy()
    for c in ["現金贈與（元）","免稅後淨額（元）","應納贈與稅（元）"]:
        show_no[c] = show_no[c].map(fmt_y)
    st.dataframe(show_no, use_container_width=True)

st.divider()

# ---------- 4) 說服版面：保單優勢 + 稅務優惠 ----------
st.subheader("一頁就懂：這張保單的核心價值（不只省稅）")
st.markdown(f"""
**① 保障放大（同樣現金流 ↔ 風險時刻放大為保額）**  
- 不用保單：最多就是把錢分年送出。  
- 用保單：在**需要的那一刻**，由保險把保障**放大成保額**（請用試算書對應你的商品保額）。  

**② 時間確定（現金在需要時直接到位）**  
- 給付不受市場波動影響，避免在緊急時刻折價賣資產（股權/不動產）。  
- 對企業主與資產多為不動產者，這是一道**流動性防火牆**。  

**③ 治理控管（誰拿、怎麼拿、何時拿）**  
- 先由一代掌握要保人，**第 {change_year} 年**交棒給二代；受益人與比例可設計（可搭配保險信託）以避免一次性失衡、或被外力侵蝕。  

**④ 稅務優惠（變更年認列現金價值）**  
- 用保單：只在**第 {change_year} 年**對「**現金價值**」課贈與稅（多數情況低於累計保費），上方已試算稅額。  
- 不用保單：必須在**第 1～{change_year} 年**每年對**年繳保費全額**課贈與稅。  
- 上方 KPI 已顯示：用保單到第 N 年的**稅負差**（節稅金額）。
""")

st.caption("提醒：最終保額與現金價值以保險公司試算書為準；本工具著重稅務計算與策略展示。")
