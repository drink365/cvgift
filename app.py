# app.py — 保單贈與稅規劃器（單一贈與人｜可分批變更＋最終保額對照｜固定稅制｜全中文）
# 執行：streamlit run app.py

import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="保單贈與稅規劃器｜單一贈與人", layout="centered")

# ---------------- 固定稅制常數（114年/2025 制） ----------------
EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
BR10_NET_MAX = 28_110_000  # 10% 淨額上限
BR15_NET_MAX = 56_210_000  # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

# 單張年繳保費上限（且預設值）
MAX_POLICY_PREM = 6_000_000

# ---------------- 共用樣式與格式 ----------------
def fmt(n: float) -> str:
    return f"{n:,.0f}"

def fmt_y(n: float) -> str:
    return f"{fmt(n)} 元"

st.markdown("""
<style>
  .num { font-weight: 700; font-variant-numeric: tabular-nums; }
  .bullet { margin: 0.2rem 0; }
  .kpi {display:flex; flex-direction:column; gap:2px; padding:6px 0;}
  .kpi .label {color:#5f6368; font-size:0.95rem;}
  .kpi .value {font-weight:700; font-size:1rem; line-height:1.2;}
  .dataframe td:nth-child(3),
  .dataframe td:nth-child(4),
  .dataframe td:nth-child(5) { text-align:right; }
  .note { background:#f7f7fb; border:1px solid #ececf3; padding:12px 14px; border-radius:8px; }
</style>
""", unsafe_allow_html=True)

def gift_tax_by_bracket(net: int):
    """依固定稅制計算贈與稅（含基稅）；回傳(稅額, 稅率字串)"""
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

# ---------------- 標題與稅制說明 ----------------
st.title("保單贈與稅規劃器（單一贈與人）")
st.caption("所有金額單位：新台幣。若為夫妻兩位贈與人，可視情況將容量與結果 ×2。")

st.markdown(
    f"""
    <div class="note">
      <b>本工具採用之贈與稅規則（114年/2025）</b><br>
      ・年免稅額：<span class="num">{fmt(EXEMPTION)}</span><br>
      ・累進稅率（以「淨額＝贈與總額−免稅額」計）：<br>
        &nbsp;&nbsp;— 淨額 ≤ <span class="num">{fmt(BR10_NET_MAX)}</span> ：10%<br>
        &nbsp;&nbsp;— {fmt(BR10_NET_MAX+1)} ～ {fmt(BR15_NET_MAX)} ：15%（含 10% 基礎稅額）<br>
        &nbsp;&nbsp;— ＞ <span class="num">{fmt(BR15_NET_MAX)}</span> ：20%（含 10%＋15% 基礎稅額）<br>
      ・要保人變更之贈與評價：第1年＝年繳×1/3；第2年＝兩年保費總額×1/4（＝年繳×0.5）。實務仍以保險公司試算書為準。
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------- 一、輸入目標與偏好 ----------------
st.subheader("一、輸入目標與偏好")

# 年期（用於不用保單之對照）
policy_years = st.number_input("年期（年）", min_value=1, max_value=30, value=8, step=1)

target_yearly_prem = st.number_input(
    "希望透過保單規劃的年繳總保費（元/年）",
    min_value=0, step=100_000, value=30_000_000, format="%d"
)

unit_policy_prem = st.number_input(
    f"單張保單建議年繳（元/年，≤ {fmt(MAX_POLICY_PREM)})",
    min_value=100_000, max_value=MAX_POLICY_PREM,
    step=100_000, value=MAX_POLICY_PREM, format="%d"
)

# 變更節奏與 RPU
opt_mode = st.selectbox(
    "策略取向（影響 RPU 時點與是否需要續贈現金）",
    ["稅最省（第2年變更為主）", "保額優先（第2年變更＋多繳1年）", "保額最大（第2年變更＋多繳2年）"]
)
enable_rpu = st.checkbox("啟用減額繳清（RPU）", value=True)
rpu_mode = "自動建議"
manual_year = None
if enable_rpu:
    rpu_mode = st.radio("RPU 年份選擇", ["自動建議", "手動指定"], horizontal=True)
    if rpu_mode == "手動指定":
        manual_year = st.select_slider("選擇 RPU 年（相對於變更在第2年）", options=[2, 3, 4], value=2)

# 受益人最後拿到的保額（用試算書填入）
st.subheader("（選填）受益人最後拿到的保額")
benefit_full = st.number_input("不做 RPU、繼續繳滿的預計保額（元）", min_value=0, step=1_000_000, value=90_000_000, format="%d")
col_b2, col_b3, col_b4 = st.columns(3)
with col_b2:
    benefit_rpu2 = st.number_input("第2年 RPU 預估保額（元）", min_value=0, step=1_000_000, value=0, format="%d")
with col_b3:
    benefit_rpu3 = st.number_input("第3年 RPU 預估保額（元）", min_value=0, step=1_000_000, value=0, format="%d")
with col_b4:
    benefit_rpu4 = st.number_input("第4年 RPU 預估保額（元）", min_value=0, step=1_000_000, value=0, format="%d")

if target_yearly_prem == 0:
    st.info("請輸入年繳總保費目標。")
    st.stop()

# ---------------- 二、系統建議張數與「分批變更」 ----------------
unit_policy_prem = min(unit_policy_prem, MAX_POLICY_PREM)
num_policies = max(1, math.ceil(target_yearly_prem / unit_policy_prem))
actual_yearly_prem = num_policies * unit_policy_prem

st.markdown(
    f"""
    <ul>
      <li class="bullet">單張年繳上限 <span class="num">{fmt(MAX_POLICY_PREM)}</span>，你設定每張 <span class="num">{fmt(unit_policy_prem)}</span>。</li>
      <li class="bullet">建議購買 <span class="num">{num_policies} 張</span>；實際年繳總保費：<span class="num">{fmt(actual_yearly_prem)}</span> / 年。</li>
    </ul>
    """,
    unsafe_allow_html=True
)

# 第1年先變更幾張（0～全部）
y1_change = st.slider("第1年先變更的張數（其餘在第2年變更）",
                      min_value=0, max_value=num_policies, value=0, step=1)
y2_change = num_policies - y1_change

# RPU 年決策
strategy_to_extra_years = {
    "稅最省（第2年變更為主）": 0,
    "保額優先（第2年變更＋多繳1年）": 1,
    "保額最大（第2年變更＋多繳2年）": 2
}
extra_years = strategy_to_extra_years[opt_mode]
if enable_rpu:
    rpu_year = (2 + extra_years) if (rpu_mode == "自動建議") else manual_year
else:
    rpu_year = None

# ---------------- 三、年度贈與稅排程（含分批變更） ----------------
st.subheader("二、年度贈與稅排程（單一贈與人）")

rows = []

# 第1年
if y1_change == 0:
    rows.append({"年度": "第1年", "贈與標的": "—（不變更）", "贈與額": 0,
                 "免稅後淨額": 0, "應納贈與稅": 0, "適用稅率": "—"})
else:
    gift_y1 = int(round(y1_change * unit_policy_prem * (1/3)))  # 第1年評價=年繳×1/3
    net_y1  = max(0, gift_y1 - EXEMPTION)
    tax_y1, rate_y1 = gift_tax_by_bracket(net_y1)
    rows.append({"年度": "第1年", "贈與標的": f"變更要保人（{y1_change} 張；評價＝年繳×1/3）",
                 "贈與額": gift_y1, "免稅後淨額": net_y1, "應納贈與稅": tax_y1, "適用稅率": rate_y1})

# 第2年：變更剩餘張數 + 若第1年已變更那批需由上一代資助保費，列入現金贈與
gift_y2_change = int(round(y2_change * unit_policy_prem * 0.5))  # 第2年評價=年繳×0.5
gift_y2_cash   = 0
if y1_change > 0 and (not enable_rpu or (enable_rpu and rpu_year is not None and rpu_year > 2)):
    gift_y2_cash = y1_change * unit_policy_prem  # 幫第1年已變更之保單，繳第2年保費

gift_y2_total = gift_y2_change + gift_y2_cash
net_y2        = max(0, gift_y2_total - EXEMPTION)
tax_y2, rate_y2 = gift_tax_by_bracket(net_y2)

desc_y2 = f"變更要保人（{y2_change} 張；評價＝年繳×0.5）"
if gift_y2_cash > 0:
    desc_y2 += f" ＋ 現金贈與（為第1年已變更之 {y1_change} 張繳保費）"
rows.append({"年度": "第2年", "贈與標的": desc_y2,
             "贈與額": gift_y2_total, "免稅後淨額": net_y2,
             "應納贈與稅": tax_y2, "適用稅率": rate_y2})

# 第3年
gift_y3_total = 0
if not enable_rpu or (enable_rpu and rpu_year is not None and rpu_year > 3):
    total_changed = y1_change + y2_change
    gift_y3_total = total_changed * unit_policy_prem
if gift_y3_total > 0:
    net_y3  = max(0, gift_y3_total - EXEMPTION)
    tax_y3, rate_y3 = gift_tax_by_bracket(net_y3)
    rows.append({"年度": "第3年", "贈與標的": "現金贈與（為全部已變更之保單繳保費）",
                 "贈與額": gift_y3_total, "免稅後淨額": net_y3,
                 "應納贈與稅": tax_y3, "適用稅率": rate_y3})

# 第4年（示意到第4年）
gift_y4_total = 0
if not enable_rpu or (enable_rpu and rpu_year is not None and rpu_year > 4):
    total_changed = y1_change + y2_change
    gift_y4_total = total_changed * unit_policy_prem
if gift_y4_total > 0:
    net_y4  = max(0, gift_y4_total - EXEMPTION)
    tax_y4, rate_y4 = gift_tax_by_bracket(net_y4)
    rows.append({"年度": "第4年", "贈與標的": "現金贈與（為全部已變更之保單繳保費）",
                 "贈與額": gift_y4_total, "免稅後淨額": net_y4,
                 "應納贈與稅": tax_y4, "適用稅率": rate_y4})

# RPU 列（若有啟用）
if enable_rpu and rpu_year is not None:
    rows.append({"年度": f"第{rpu_year}年", "贈與標的": "減額繳清（RPU）",
                 "贈與額": 0, "免稅後淨額": 0, "應納贈與稅": 0, "適用稅率": "—"})

df = pd.DataFrame(rows)
show = df.copy()
for col in ["贈與額", "免稅後淨額", "應納贈與稅"]:
    show[col] = show[col].map(fmt_y)
st.dataframe(show, use_container_width=True)

# ---------------- 四、合計與對照：法律移轉 vs 經濟價值 ----------------
# 法律上已完成的贈與總額（= 當年度所有「贈與額」加總）
legal_total_with_policy = int(df["贈與額"].sum())
total_tax_with_policy   = int(df["應納贈與稅"].sum())

# 經濟上最終價值：依是否 RPU/哪一年 RPU 帶入對應保額
if enable_rpu and rpu_year is not None:
    final_benefit = {2: benefit_rpu2, 3: benefit_rpu3, 4: benefit_rpu4}.get(rpu_year, 0)
    final_benefit_note = f"RPU 年：第{rpu_year}年"
else:
    final_benefit = benefit_full
    final_benefit_note = "不做 RPU／繼續繳滿"

# 「完全不透過保單」對照（同年期、同年繳現金直接贈與）
no_policy_annual_gift = actual_yearly_prem
no_policy_annual_net  = max(0, no_policy_annual_gift - EXEMPTION)
no_policy_annual_tax, _rate = gift_tax_by_bracket(no_policy_annual_net)
legal_total_no_policy = int(no_policy_annual_gift * policy_years)
total_tax_no_policy   = int(no_policy_annual_tax * policy_years)
economic_no_policy    = legal_total_no_policy  # 經濟上就是拿到現金總額

st.markdown("### 三、總結對照")
st.markdown(
    f"""
- **不用保單（直接現金贈與）**  
  ・法律上移轉金額合計：**{fmt_y(legal_total_no_policy)}**  
  ・累計贈與稅：**{fmt_y(total_tax_no_policy)}**  
  ・經濟上最終拿到：**{fmt_y(economic_no_policy)}**（現金分年入帳）

- **透過保單（本頁設定）**  
  ・法律上移轉金額合計（含變更＋續年現金贈與）：**{fmt_y(legal_total_with_policy)}**  
  ・累計贈與稅：**{fmt_y(total_tax_with_policy)}**  
  ・經濟上最終拿到（受益人）：**{fmt_y(final_benefit)}**（{final_benefit_note}）
""")

st.info("提醒：最終保額/RPU 後保額須以保險公司試算書為準；本頁以第1年=×1/3、第2年=×0.5 為保守近似做壓縮評價。")
