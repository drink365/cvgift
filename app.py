# app.py — 用同樣現金流，更聰明完成贈與｜單張保單一鍵試算（簡易/專家雙模式，穩定版）
# 執行：streamlit run app.py
# 需求：pip install streamlit pandas

import pandas as pd
import streamlit as st

st.set_page_config(page_title="用同樣現金流，更聰明完成贈與｜單張保單一鍵試算", layout="centered")

# ---------------- 稅制常數（114年/2025） ----------------
EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
BR10_NET_MAX = 28_110_000  # 10% 淨額上限（淨額）
BR15_NET_MAX = 56_210_000  # 15% 淨額上限（淨額）
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

MAX_ANNUAL   = 100_000_000  # 單年現金投入上限：1 億

# ---------------- 先初始化 Session State（避免直接賦值引發例外） ----------------
DEFAULTS = {"years": 8, "annual_cash": 6_000_000, "change_year": 2, "simple_mode": True}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 預設比率：Y1=50%、Y2=70%、Y3=80%、Y4=85%、Y5=88%、Y6=91%、Y7=93%、Y8=95%，>8 年維持 95%
RATIO_MAP = {1:0.50, 2:0.70, 3:0.80, 4:0.85, 5:0.88, 6:0.91, 7:0.93, 8:0.95}

# ---------------- 樣式與小工具 ----------------
st.markdown("""
<style>
.kpi {border:1px solid #ECECF3; border-radius:10px; padding:12px 14px; background:#FAFAFD;}
.kpi .label {color:#5f6368; font-size:0.95rem; margin-bottom:6px;}
.kpi .value {font-weight:700; font-variant-numeric: tabular-nums; font-size:1.05rem; line-height:1.3;}
.kpi .note  {color:#16a34a; font-size:0.9rem; margin-top:4px;}
.small {color:#5f6368; font-size:0.92rem;}
</style>
""", unsafe_allow_html=True)

def card(label: str, value: str, note: str = ""):
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
st.title("用同樣現金流，更聰明完成贈與")
st.caption("單位：新台幣。稅制假設（114年/2025）：年免稅 2,440,000；10% 淨額上限 28,110,000；15% 淨額上限 56,210,000。")

with st.expander("計算邏輯（點我展開）", expanded=False):
    st.markdown("""
- 家族設定：要保人一代 →（第 N 年變更）→ 二代；被保人二代；受益人三代。  
- **用保單**：第 N 年把要保人改到孩子名下，當年以**現金價值（保價金/解約金）**認列贈與。  
- **不用保單（對照）**：若以**現金贈與**達成同等規模的移轉，則在第 1～N 年逐年贈與現金，依當年免稅額與累進稅率課稅。  
- 本頁只比較**到變更當年**；變更後不再由一代繳保費（不再產生一代→二代的贈與）。
""")

# ---------------- 模式切換（用 state 綁定） ----------------
st.session_state.simple_mode = st.toggle("簡易模式", value=st.session_state.simple_mode)

# ---------------- 一鍵情境：用 callback 安全設定 state ----------------
def apply_preset(y: int, a: int, c: int):
    st.session_state.update({"years": y, "annual_cash": a, "change_year": c})

colb1, colb2 = st.columns(2)
with colb1:
    st.button("一鍵情境：600 萬×8 年｜第 2 年變更",
              on_click=apply_preset, args=(8, 6_000_000, 2))
with colb2:
    st.button("一鍵情境：600 萬×8 年｜第 1 年變更",
              on_click=apply_preset, args=(8, 6_000_000, 1))

# ---------------- 1) 三個輸入（以 state 為預設值） ----------------
col1, col2, col3 = st.columns(3)
with col1:
    years = st.number_input("年期（年）", min_value=1, max_value=40,
                            value=st.session_state.years, step=1, key="years_input")
with col2:
    annual = st.number_input("每年要投入多少現金（元）", min_value=0, max_value=MAX_ANNUAL,
                             value=st.session_state.annual_cash, step=100_000, format="%d", key="annual_input")
with col3:
    change_year = st.number_input("第幾年把保單改到孩子名下（N）", min_value=1, max_value=40,
                                  value=st.session_state.change_year, step=1, key="change_input")

# 同步回 state（避免型別/時序問題）
st.session_state.years = int(years)
st.session_state.annual_cash = int(annual)
st.session_state.change_year = int(change_year)

# 邏輯校驗
if st.session_state.annual_cash > MAX_ANNUAL:
    st.error("每年投入不可超過 1 億。"); st.stop()
if st.session_state.change_year > st.session_state.years:
    st.warning("變更年份不可超過年期，已自動調整為年期。")
    st.session_state.change_year = st.session_state.years

years = st.session_state.years
annual = st.session_state.annual_cash
change_year = st.session_state.change_year

# ---------------- 2) 自動生成：年末現金價值（預設比率） ----------------
rows, cum = [], 0
for y in range(1, years+1):
    cum += annual
    ratio = RATIO_MAP.get(y, 0.95)
    cv = int(round(cum * ratio))
    rows.append({"年度": y, "每年投入（元）": annual, "累計投入（元）": cum, "年末現金價值（元）": cv})
df_years = pd.DataFrame(rows)

# ---------------- 3) 稅務比較（算到第 N 年） ----------------
cv_at_change = int(df_years.loc[df_years["年度"] == change_year, "年末現金價值（元）"].iloc[0])

# 用保單（第 N 年變更）：當年視為贈與 = 現金價值
gift_with_policy = cv_at_change
net_with_policy = max(0, gift_with_policy - EXEMPTION)
tax_with_policy, rate_with = gift_tax(net_with_policy)

# 不用保單：第 1～N 年逐年「現金贈與」（對照口徑）
total_tax_no_policy = 0
yearly_tax_list = []
for y in range(1, change_year+1):
    net = max(0, annual - EXEMPTION)
    t, rate = gift_tax(net)
    total_tax_no_policy += t
    yearly_tax_list.append({
        "年度": y,
        "現金贈與（元）": annual,
        "免稅後淨額（元）": net,
        "應納贈與稅（元）": t,
        "適用稅率": rate
    })

tax_saving = total_tax_no_policy - tax_with_policy

# ---------------- 4) 簡易模式的話術＋重點指標 ----------------
st.markdown(
    f'<div class="small">用保單：第 <b>{change_year}</b> 年改到孩子名下，當年以 <b>現金價值</b> 認列贈與（通常低於累計投入）。'
    f'　不用保單：第 <b>1～{change_year}</b> 年逐年以 <b>現金贈與</b> 達成移轉，逐年課稅。</div>',
    unsafe_allow_html=True
)
st.write("")

colA, colB, colC = st.columns(3)
with colA:
    st.markdown("**用保單（第 N 年變更）**")
    card("變更當年視為贈與（現金價值）", fmt_y(gift_with_policy))
    card("當年應納贈與稅", fmt_y(tax_with_policy), note=f"稅率 {rate_with}")
with colB:
    st.markdown("**不用保單（第 1～N 年現金贈與）**")
    card("合計贈與稅（1～N 年）", fmt_y(total_tax_no_policy))
with colC:
    st.markdown("**差異（節稅）**")
    card("到第 N 年節省的贈與稅", fmt_y(tax_saving))

# ---------------- 5) 專家用：明細展開（依模式顯示） ----------------
if st.session_state.simple_mode:
    with st.expander("想看公式與年度明細？（專家用）", expanded=False):
        st.markdown("**年度明細（依預設比率自動生成）**")
        st.dataframe(
            df_years.assign(
                **{"每年投入（元）": lambda d: d["每年投入（元）"].map(fmt),
                   "累計投入（元）": lambda d: d["累計投入（元）"].map(fmt),
                   "年末現金價值（元）": lambda d: d["年末現金價值（元）"].map(fmt)}
            ),
            use_container_width=True
        )

        st.markdown("**不用保單：逐年現金贈與的稅額**")
        df_no = pd.DataFrame(yearly_tax_list)
        show_no = df_no.copy()
        for c in ["現金贈與（元）","免稅後淨額（元）","應納贈與稅（元）"]:
            show_no[c] = show_no[c].map(fmt_y)
        st.dataframe(show_no, use_container_width=True)
else:
    st.subheader("年度明細（依預設比率自動生成）")
    st.dataframe(
        df_years.assign(
            **{"每年投入（元）": lambda d: d["每年投入（元）"].map(fmt),
               "累計投入（元）": lambda d: d["累計投入（元）"].map(fmt),
               "年末現金價值（元）": lambda d: d["年末現金價值（元）"].map(fmt)}
        ),
        use_container_width=True
    )
    st.subheader("不用保單：逐年現金贈與的稅額")
    df_no = pd.DataFrame(yearly_tax_list)
    show_no = df_no.copy()
    for c in ["現金贈與（元）","免稅後淨額（元）","應納贈與稅（元）"]:
        show_no[c] = show_no[c].map(fmt_y)
    st.dataframe(show_no, use_container_width=True)

st.divider()

# ---------------- 6) 一頁就懂：為什麼要用保單（除了節稅） ----------------
st.subheader("為什麼要用保單（除了節稅）")
st.markdown(f"""
**① 放大與配置（同樣現金流，家族資源更有效）**  
- 不用保單：最多把錢分年送出。  
- 用保單：在**需要的那一刻**，由保險把保障**放大成保額**（依商品與試算書），提高資本效率與家庭安全網。  

**② 時間確定（現金在需要時直接到位）**  
- 給付不受市場波動影響，避免在緊急時刻折價賣資產（股權/不動產）。  
- 對企業主與資產多為不動產者，這是一道**流動性防火牆**。  

**③ 治理控管（誰拿、怎麼拿、何時拿）**  
- ① 先由一代掌握要保人，在**第 {change_year} 年**交棒給二代；受益人與比例可設計（可搭配保險信託）避免一次性失衡或被外力侵蝕。  
- ② 透過**保單贈與（含變更要保人）**可做到**帳戶獨立管理**，與一般銀行往來混同切割；亦具**婚姻財富治理**功能，清楚界定資金的專屬性與用途（如教育金、長照金）。  

**④ 稅務效果（變更年認列現金價值）**  
- 用保單：只在**第 {change_year} 年**對「**現金價值**」課贈與稅（多數情況低於累計投入），因此**到第 N 年稅更有效率**。  
- 不用保單：第 1～{change_year} 年逐年以**現金贈與**進行移轉，各年依免稅額與累進稅率課稅；上方指標已呈現差異。
""")

st.caption("提示：年末現金價值與最終保額以保險公司試算書為準；本工具著重稅務計算與策略展示。")
