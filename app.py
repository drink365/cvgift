# app.py — 保單贈與稅規劃器（單一贈與人｜全中文｜金額皆為新台幣）
# 執行：streamlit run app.py

import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="保單贈與稅規劃器｜單一贈與人", layout="centered")

# ---------------- 稅制常數（可在側欄微調） ----------------
DEFAULT_EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
DEFAULT_BR10_MAX_NET = 28_110_000  # 10% 淨額上限
DEFAULT_BR15_MAX_NET = 56_210_000  # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

# 單張年繳保費上限（且預設值）
MAX_POLICY_PREM = 6_000_000

# --------- 共用：數字格式與樣式 ----------
def fmt(n: float) -> str:
    return f"{n:,.0f}"

def fmt_y(n: float) -> str:
    return f"{fmt(n)} 元"

st.markdown("""
<style>
  /* 數字用同一字重與等寬樣式，避免跳字 */
  .num { font-weight: 700; font-variant-numeric: tabular-nums; }
  .bullet { margin: 0.2rem 0; }
  /* KPI：不放大字，只加粗 */
  .kpi {display:flex; flex-direction:column; gap:2px; padding:6px 0;}
  .kpi .label {color:#5f6368; font-size:0.95rem;}
  .kpi .value {font-weight:700; font-size:1rem; line-height:1.2;}
  /* 表格內金額靠右更好讀 */
  .dataframe td:nth-child(3),
  .dataframe td:nth-child(4),
  .dataframe td:nth-child(5) { text-align:right; }
</style>
""", unsafe_allow_html=True)

def gift_tax_by_bracket(net, br10, br15):
    if net <= 0: return 0, "—"
    if net <= br10: return int(round(net * RATE_10)), "10%"
    if net <= br15:
        base = br10 * RATE_10
        extra = (net - br10) * RATE_15
        return int(round(base + extra)), "15%"
    base = br10 * RATE_10 + (br15 - br10) * RATE_15
    extra = (net - br15) * RATE_20
    return int(round(base + extra)), "20%"

# ---------------- 側欄調整 ----------------
with st.sidebar:
    st.header("參數調整")
    exemption = st.number_input("年免稅額（單一贈與人）", 0, None, DEFAULT_EXEMPTION, 10_000, format="%d")
    br10 = st.number_input("10% 淨額上限", 0, None, DEFAULT_BR10_MAX_NET, 10_000, format="%d")
    br15 = st.number_input("15% 淨額上限", 0, None, DEFAULT_BR15_MAX_NET, 10_000, format="%d")
    st.caption("若法規未來調整，於此微調即可。")

# ---------------- 標題 ----------------
st.title("保單贈與稅規劃器（單一贈與人）")
st.caption("預設採 2025（114年）台灣贈與稅級距；若為夫妻兩位贈與人，可將容量與結果視情況 ×2。所有金額單位：新台幣。")

# ---------------- 使用者目標 ----------------
st.subheader("一、輸入目標與偏好")
target_yearly_prem = st.number_input("希望透過保單規劃的年繳總保費（元/年）",
                                     min_value=0, step=100_000, value=30_000_000, format="%d")

# 單張年繳：上限與預設皆為 600 萬，可下修不可超過
unit_policy_prem = st.number_input(f"單張保單建議年繳（元/年，≤ {fmt(MAX_POLICY_PREM)})",
                                   min_value=100_000, max_value=MAX_POLICY_PREM,
                                   step=100_000, value=MAX_POLICY_PREM, format="%d")

opt_mode = st.selectbox(
    "策略取向",
    ["稅最省（第2年變更要保人）", "保額優先（第2年變更＋多繳1年）", "保額最大（第2年變更＋多繳2年）"]
)

# RPU 選項
enable_rpu = st.checkbox("啟用減額繳清（RPU）", value=True)
rpu_mode = "自動建議"
manual_year = None
if enable_rpu:
    rpu_mode = st.radio("RPU 年份選擇", ["自動建議", "手動指定"], horizontal=True)
    if rpu_mode == "手動指定":
        manual_year = st.select_slider("選擇 RPU 年（變更在第2年）", options=[2, 3, 4], value=2)

if target_yearly_prem == 0:
    st.info("請輸入年繳總保費目標。")
    st.stop()

# ---------------- 系統建議張數與節奏 ----------------
unit_policy_prem = min(unit_policy_prem, MAX_POLICY_PREM)
num_policies = max(1, math.ceil(target_yearly_prem / unit_policy_prem))
actual_yearly_prem = num_policies * unit_policy_prem

st.markdown(
    f"""
    <ul>
      <li class="bullet">單張年繳上限 <span class="num">{fmt(MAX_POLICY_PREM)}</span>，你設定每張 <span class="num">{fmt(unit_policy_prem)}</span>。</li>
      <li class="bullet">建議購買 <span class="num">{num_policies} 張</span>；實際年繳總保費：<span class="num">{fmt(actual_yearly_prem)}</span> / 年。</li>
      <li class="bullet">節奏：原要保人繳第1與第2年保費；<b>第2年同日變更要保人</b>（評價＝年繳 × 0.5）。</li>
    </ul>
    """,
    unsafe_allow_html=True
)
if unit_policy_prem >= MAX_POLICY_PREM and target_yearly_prem > MAX_POLICY_PREM:
    st.warning("已套用單張上限 6,000,000 元；如需更高總額度，系統會自動增加張數。")

# ---------------- 年度稅排程 ----------------
st.subheader("二、年度贈與稅排程（單一贈與人）")
plan_rows = []

# 第1年：不變更
plan_rows.append({"年度": "第1年", "贈與標的": "—（不變更）",
                  "贈與額": 0, "免稅後淨額": 0, "應納贈與稅": 0, "適用稅率": "—"})

# 第2年：變更（CV=年繳×0.5）
gift_y2 = int(round(actual_yearly_prem * 0.5))
net_y2  = max(0, gift_y2 - exemption)
tax_y2, rate_y2 = gift_tax_by_bracket(net_y2, br10, br15)
plan_rows.append({"年度": "第2年", "贈與標的": "變更要保人（評價＝年繳×0.5）",
                  "贈與額": gift_y2, "免稅後淨額": net_y2, "應納贈與稅": tax_y2, "適用稅率": rate_y2})

# 根據策略決定變更後再贈與幾年、以及 RPU 年
strategy_to_extra_years = {
    "稅最省（第2年變更要保人）": 0,
    "保額優先（第2年變更＋多繳1年）": 1,
    "保額最大（第2年變更＋多繳2年）": 2
}
extra_years = strategy_to_extra_years[opt_mode]

# RPU 年
if enable_rpu:
    rpu_year = (2 + extra_years) if (rpu_mode == "自動建議") else manual_year
else:
    rpu_year = None

# 變更後的現金贈與（供新要保人繳保費）直到 RPU 前一年；
# 若不啟用 RPU，示意列出 2 年
max_follow_years = extra_years if enable_rpu else 2
for k in range(max_follow_years):
    year_num = 3 + k
    gift_cash = actual_yearly_prem
    net = max(0, gift_cash - exemption)
    tax, rate = gift_tax_by_bracket(net, br10, br15)
    plan_rows.append({"年度": f"第{year_num}年", "贈與標的": "現金贈與（供新要保人繳保費）",
                      "贈與額": gift_cash, "免稅後淨額": net, "應納贈與稅": tax, "適用稅率": rate})

# RPU 列
if rpu_year is not None:
    plan_rows.append({"年度": f"第{rpu_year}年", "贈與標的": "減額繳清（RPU）",
                      "贈與額": 0, "免稅後淨額": 0, "應納贈與稅": 0, "適用稅率": "—"})

df_plan = pd.DataFrame(plan_rows)

# 顯示（加上「元」字樣）
show_df = df_plan.copy()
for col in ["贈與額", "免稅後淨額", "應納贈與稅"]:
    show_df[col] = show_df[col].map(fmt_y)
st.dataframe(show_df, use_container_width=True)

total_tax = int(df_plan["應納贈與稅"].sum())
rpu_note = f"；RPU 年：第{rpu_year}年" if rpu_year is not None else "；未啟用 RPU"
st.markdown(f"**至目前排程的累計應納贈與稅**：**{fmt_y(total_tax)}**（單一贈與人）{rpu_note}。")

st.divider()

# ---------------- 10% 內之承作上限參考 ----------------
st.subheader("三、在 10% 稅率內的承作上限（單一贈與人）")
cap_gross_10   = exemption + br10        # 244萬 + 2,811萬 = 3,055萬
cap_y2_yearly  = cap_gross_10 * 2        # 第2年變更：年繳上限 = 2×cap
cap_y1_first   = cap_gross_10 * 3        # 第1年變更：首年年繳上限 = 3×cap
st.write(f"- 若採第2年變更：每年可承作之年繳上限約 **{fmt_y(cap_y2_yearly)}**。")
st.write(f"- 若採第1年變更：首年可承作之年繳上限約 **{fmt_y(cap_y1_first)}**。")
st.info("本頁以『第2年變更』為基準，通常總稅最低、金流最順。")

st.divider()

st.subheader("四、說明與提醒")
st.markdown("""
- 變更要保人的贈與評價以變更當日的現金價值（解約金）近似：第1年＝保費×1/3；第2年＝兩年保費總額×1/4（=年繳×0.5）。  
- 啟用 RPU 後，RPU 年起停止現金繳費，但保額會依當時現金價值等比例縮小；繳清後保額請以保險公司試算書為準。  
- 贈與行為發生後 30 日內申報；請向保險公司索取變更當日之現金價值證明。  
- 若為夫妻兩位贈與人，可把保費/贈與分攤至兩人，使每位的年度淨額多數情況能控制在 2,811 萬內，以鎖定 10% 稅率。
""")
