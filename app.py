# app.py — 保單贈與稅規劃器（單一贈與人｜可分批變更｜全中文）
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
        &nbsp;&nbsp;— ＞ {fmt(BR15_NET_MAX)} ：20%（含 10%＋15% 基礎稅額）<br>
      ・要保人變更之贈與評價：第1年＝年繳×1/3；第2年＝兩年保費總額×1/4（＝年繳×0.5）。實務仍以保險公司試算書為準。
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------- 一、輸入目標與偏好 ----------------
st.subheader("一、輸入目標與偏好")

target_yearly_prem = st.number_input("希望透過保單規劃的年繳總保費（元/年）",
                                     min_value=0, step=100_000, value=30_000_000, format="%d")

unit_policy_prem = st.number_input(f"單張保單建議年繳（元/年，≤ {fmt(MAX_POLICY_PREM)})",
                                   min_value=100_000, max_value=MAX_POLICY_PREM,
                                   step=100_000, value=MAX_POLICY_PREM, format="%d")

# 變更節奏：可指定「第1年先變更幾張」，其餘在第2年變更
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

# 新增：第1年先變更幾張（0～全部）
y1_change = st.slider("第1年欲先變更的張數（其餘將在第2年變更）",
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

# 第1年：變更 y1_change 張（若=0，則只顯示不變更）
if y1_change == 0:
    rows.append({"年度": "第1年", "贈與標的": "—（不變更）", "贈與額": 0,
                 "免稅後淨額": 0, "應納贈與稅": 0, "適用稅率": "—"})
else:
    gift_y1 = int(round(y1_change * unit_policy_prem * (1/3)))  # 第1年評價=年繳×1/3
    net_y1  = max(0, gift_y1 - EXEMPTION)
    tax_y1, rate_y1 = gift_tax_by_bracket(net_y1)
    rows.append({"年度": "第1年", "贈與標的": f"變更要保人（{y1_change} 張；評價＝年繳×1/3）",
                 "贈與額": gift_y1, "免稅後淨額": net_y1, "應納贈與稅": tax_y1, "適用稅率": rate_y1})

# 第2年：變更 y2_change 張；同時可能需贈與「第1年已變更那批」的年繳保費（若 RPU 晚於第2年）
gift_y2_change = int(round(y2_change * unit_policy_prem * 0.5))  # 第2年評價=年繳×0.5
gift_y2_cash   = 0
if y1_change > 0 and (not enable_rpu or (enable_rpu and rpu_year is not None and rpu_year > 2)):
    gift_y2_cash = y1_change * unit_policy_prem  # 幫第1年已變更之保單，繳第2年保費

gift_y2_total = gift_y2_change + gift_y2_cash
net_y2        = max(0, gift_y2_total - (0 if y1_change>0 else EXEMPTION) )  # 免稅額每年一次：這裡第2年仍可用一次免稅額
# 說明：上面可依需求改為每年都使用 EXEMPTION；此處保持「每年各自一次」邏輯
net_y2        = max(0, gift_y2_total - EXEMPTION)
tax_y2, rate_y2 = gift_tax_by_bracket(net_y2)

desc_y2 = f"變更要保人（{y2_change} 張；評價＝年繳×0.5）"
if gift_y2_cash > 0:
    desc_y2 += f" ＋ 現金贈與（為第1年已變更之 {y1_change} 張繳保費）"
rows.append({"年度": "第2年", "贈與標的": desc_y2,
             "贈與額": gift_y2_total, "免稅後淨額": net_y2,
             "應納贈與稅": tax_y2, "適用稅率": rate_y2})

# 第3年：若 RPU 晚於第3年，則要幫「第1年批＋第2年批」繳保費
gift_y3_total = 0
if not enable_rpu or (enable_rpu and rpu_year is not None and rpu_year > 3):
    gift_y3_total = (y1_change + y2_change) * unit_policy_prem
if gift_y3_total > 0:
    net_y3  = max(0, gift_y3_total - EXEMPTION)
    tax_y3, rate_y3 = gift_tax_by_bracket(net_y3)
    rows.append({"年度": "第3年", "贈與標的": "現金贈與（為全部已變更之保單繳保費）",
                 "贈與額": gift_y3_total, "免稅後淨額": net_y3,
                 "應納贈與稅": tax_y3, "適用稅率": rate_y3})

# 第4年：若 RPU 在第4年之後，仍需再贈與一次（本工具上限示意至第4年）
gift_y4_total = 0
if not enable_rpu or (enable_rpu and rpu_year is not None and rpu_year > 4):
    gift_y4_total = (y1_change + y2_change) * unit_policy_prem
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

total_tax = int(df["應納贈與稅"].sum())
rpu_note = f"；RPU 年：第{rpu_year}年" if enable_rpu and rpu_year is not None else "；未啟用 RPU"
st.markdown(f"**至目前排程的累計應納贈與稅**：**{fmt_y(total_tax)}**（單一贈與人）{rpu_note}。")

st.divider()

# ---------------- 10% 內之承作上限參考 ----------------
st.subheader("三、在 10% 稅率內的承作上限（單一贈與人）")
cap_gross_10   = EXEMPTION + BR10_NET_MAX      # 244萬 + 2,811萬 = 3,055萬
cap_y2_yearly  = cap_gross_10 * 2              # 第2年變更：年繳上限 = 2×cap
cap_y1_first   = cap_gross_10 * 3              # 第1年變更：首年年繳上限 = 3×cap
st.write(f"- 若第2年變更：每年可承作之年繳上限約 **{fmt_y(cap_y2_yearly)}**。")
st.write(f"- 若第1年變更：首年可承作之年繳上限約 **{fmt_y(cap_y1_first)}**。")
st.info("此頁以第1/第2年係數近似；若需第3年以後才變更，建議改以保險公司試算書之『當年現金價值』直接輸入估算。")

st.divider()

st.subheader("四、說明與提醒")
st.markdown("""
- 可用滑桿決定「第1年先變更幾張」，其餘在第2年變更；系統會自動把變更後、RPU 前需續繳的保費列為當年的現金贈與。  
- RPU（減額繳清）勾選後，可自動或手動設定在第2/3/4年；RPU 年起停止現金繳費，但保額會依當時現金價值等比例縮小。  
- 贈與行為發生後 30 日內申報；請向保險公司索取變更當日之現金價值證明。  
- 夫妻兩位贈與人可把保費/贈與分攤至兩人，使每位年度淨額較容易維持在 10% 級距內。
""")
