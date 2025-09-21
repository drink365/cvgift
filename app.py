# app.py — Policy Gift-Tax Planner (Single Donor)
# 功能：輸入「想移轉的年繳總保費」→ 自動建議保單張數、變更要保人年（Y1/Y2）、
#       以及 RPU（減額繳清）年（當年/第3年/第4年），並試算每年的贈與稅。
# 規則：預設 2025（114年）台灣贈與稅級距；單一贈與人。夫妻要用 → 結果 ×2。

import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="保單贈與稅規劃器｜單一贈與人", layout="centered")

# -------------------- 稅制常數（可在側欄微調） --------------------
DEFAULT_EXEMPTION = 2_440_000            # 年免稅額（單一贈與人）
DEFAULT_BR10_MAX_NET = 28_110_000        # 10% 淨額上限
DEFAULT_BR15_MAX_NET = 56_210_000        # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

def fmt(n):  # 千分位
    return f"{n:,.0f}"

def gift_tax_by_bracket(net, br10, br15):
    """回傳(稅額, 適用最高邏輯稅率字串)；含基稅處理"""
    if net <= 0:
        return 0, "—"
    if net <= br10:
        return int(round(net * RATE_10)), "10%"
    if net <= br15:
        base = br10 * RATE_10
        extra = (net - br10) * RATE_15
        return int(round(base + extra)), "15%"
    base = br10 * RATE_10 + (br15 - br10) * RATE_15
    extra = (net - br15) * RATE_20
    return int(round(base + extra)), "20%"

# -------------------- 側欄調整 --------------------
with st.sidebar:
    st.header("參數調整")
    exemption = st.number_input("年免稅額（單一贈與人）", 0, None, DEFAULT_EXEMPTION, 10_000, format="%d")
    br10 = st.number_input("10% 淨額上限", 0, None, DEFAULT_BR10_MAX_NET, 10_000, format="%d")
    br15 = st.number_input("15% 淨額上限", 0, None, DEFAULT_BR15_MAX_NET, 10_000, format="%d")
    st.caption("若法規未來調整，於此微調即可。")

# -------------------- Header --------------------
st.title("保單贈與稅規劃器（單一贈與人）")
st.caption("說明：以 2025（114年）台灣贈與稅級距為預設。夫妻雙贈與人 → 結果理論上可 ×2。")

# -------------------- 使用者目標輸入 --------------------
st.subheader("1｜輸入你的移轉目標與偏好")
target_yearly_prem = st.number_input("希望透過保單規劃的『**年繳總保費**』目標（元/年）", min_value=0, step=100_000, value=12_000_000, format="%d")
unit_policy_prem   = st.number_input("單張保單『建議年繳』大小（元/年）", min_value=100_000, step=100_000, value=1_200_000, format="%d")
opt_mode = st.selectbox(
    "策略取向",
    ["稅最省（第2年變更要保人）", "保額優先（第2年變更＋多繳1年再RPU）", "保額最大（第2年變更＋多繳2年再RPU）"]
)
st.caption(
    "- 稅最省：第2年變更後**當年即 RPU**，立刻停繳（保額較小，稅最低）。\n"
    "- 保額優先：第2年變更後**再繳1年**，第3年 RPU（保額↑，多一年的10%稅）。\n"
    "- 保額最大：第2年變更後**再繳2年**，第4年 RPU（保額↑↑，多兩年的10%稅）。"
)

# -------------------- 建議張數與配置 --------------------
if target_yearly_prem == 0:
    st.info("請輸入年繳總保費目標。")
    st.stop()

num_policies = max(1, math.ceil(target_yearly_prem / unit_policy_prem))
# 真正使用的年繳總保費（向上取整張）
actual_yearly_prem = num_policies * unit_policy_prem

st.markdown("### 2｜系統建議的張數與分配")
st.write(f"- 系統依你設定的單張年繳 {fmt(unit_policy_prem)} 元，建議購買 **{num_policies} 張**。")
st.write(f"- 對應的『年繳總保費（實際）』：**${fmt(actual_yearly_prem)} / 年**。")
st.write("- 規則：全部由**原要保人**（贈與人）先繳第1與第2年保費，第2年**同日變更要保人**（壓縮評價＝年繳×0.5）。")

# -------------------- 贈與稅排程（年視角） --------------------
st.subheader("3｜年度贈與稅排程（單一贈與人）")
plan_rows = []

# Year 1：不變更 → 不構成贈與
plan_rows.append({"年度": "第1年", "贈與標的": "—（不變更）", "贈與額（元）": 0, "免稅後淨額（元）": 0, "應納稅（元）": 0, "適用稅率": "—"})

# Year 2：變更要保人（第2年評價 = 兩年總保費×1/4 = 年繳×0.5）
gift_y2 = int(round(actual_yearly_prem * 0.5))
net_y2 = max(0, gift_y2 - exemption)
tax_y2, rate_y2 = gift_tax_by_bracket(net_y2, br10, br15)
plan_rows.append({"年度": "第2年", "贈與標的": "變更要保人（CV=年繳×0.5）", "贈與額（元）": gift_y2, "免稅後淨額（元）": net_y2, "應納稅（元）": tax_y2, "適用稅率": rate_y2})

# 之後是否還要再贈與現金來繳保費，視策略取向
extra_years_after_change = {"稅最省（第2年變更要保人）": 0,
                            "保額優先（第2年變更＋多繳1年再RPU）": 1,
                            "保額最大（第2年變更＋多繳2年再RPU）": 2}[opt_mode]

for k in range(extra_years_after_change):
    year = f"第{3+k}年"
    gift_cash = actual_yearly_prem  # 每年要幫新要保人繳的保費
    net = max(0, gift_cash - exemption)
    tax, rate = gift_tax_by_bracket(net, br10, br15)
    plan_rows.append({"年度": year, "贈與標的": "現金贈與（供新要保人繳保費）", "贈與額（元）": gift_cash,
                      "免稅後淨額（元）": net, "應納稅（元）": tax, "適用稅率": rate})

# RPU 年
rpu_year = 2 + extra_years_after_change
plan_rows.append({"年度": f"第{rpu_year}年", "贈與標的": "減額繳清（RPU）", "贈與額（元）": 0,
                  "免稅後淨額（元）": 0, "應納稅（元）": 0, "適用稅率": "—"})

df_plan = pd.DataFrame(plan_rows)
# 顯示
show_df = df_plan.copy()
for col in ["贈與額（元）", "免稅後淨額（元）", "應納稅（元）"]:
    show_df[col] = show_df[col].map(fmt)

st.dataframe(show_df, use_container_width=True)

# 總結
total_tax = df_plan["應納稅（元）"].sum()
st.markdown(
    f"**兩年（含變更年）至 RPU 年的累計應納贈與稅**："
    f"**${fmt(total_tax)}**（單一贈與人）。\n\n"
    f"若為夫妻兩位贈與人，理論上可 **×2 容量** 或將保費與贈與分攤到兩人，"
    f"使每人的稅率多半維持在 **10%** 段。"
)

st.divider()

# -------------------- 可承作上限與風險提示 --------------------
st.subheader("4｜在 10% 稅率內的承作上限（參考，單一贈與人）")
cap_gross_10 = exemption + br10                   # 3,055萬
cap_y2_yearly = cap_gross_10 * 2                  # 第2年變更：年繳上限 = 2×cap
cap_y1_first = cap_gross_10 * 3                   # 第1年變更：首年年繳上限 = 3×cap

st.write(f"- 如果採 **第2年變更**：在 10% 內單一贈與人每年可承作的『年繳總保費上限』約 **${fmt(cap_y2_yearly)}**。")
st.write(f"- 如果採 **第1年變更**：在 10% 內單一贈與人『首年年繳上限』約 **${fmt(cap_y1_first)}**。")
st.info("本頁採用『第2年變更』為基準進行建議（通常總稅最省、金流最順）。如需第1年變更模式，我可另開版。")

st.divider()

st.subheader("5｜說明與提醒")
st.markdown(
    """
- **變更要保人的贈與評價**：以變更當日的**現金價值（解約金）**近似。本工具預設第1年=保費×1/3；第2年=兩年保費總額×1/4（=年繳×0.5）。  
- **RPU（減額繳清）**：不再需要現金繳費，但保額會依當時現金價值等比例縮小。實際繳清後保額請以商品試算書為準。  
- **申報**：贈與行為發生後 **30 日內**申報；請向保險公司索取**變更當日之現金價值證明**。  
- **實務建議**：若你有兩位贈與人（夫妻），將保單與贈與分攤到兩人，可更容易把年度淨額控制在 **2,811 萬**以內，鎖在 **10%** 稅率。
"""
)
