import streamlit as st

st.set_page_config(page_title="三代傳承試算｜保單折價贈與（固定法規）", page_icon="🏛️", layout="centered")
st.title("🏛️ 三代傳承試算：無規劃 vs 有規劃（變更要保人）")
st.caption("台灣贈與稅／遺產稅 2025 年度數值已固定；本工具僅供教學示範。")

# ---------------- 固定法規（2025） ----------------
GIFT_EXEMPT = 2_440_000
GIFT_B1, GIFT_B2 = 28_110_000, 56_210_000
QD_GIFT_15, QD_GIFT_20 = 1_405_500, 4_216_000

ESTATE_EXEMPT = 13_330_000
SPOUSE_DEDUCT = 5_330_000
FUNERAL_DEDUCT = 1_380_000
LINEAL_PER = 560_000
EST_B1, EST_B2 = 56_210_000, 112_420_000
QD_EST_15, QD_EST_20 = 2_810_500, 8_431_500

def cur(n): return f"{int(n):,}"

def gift_tax(taxable: int) -> int:
    if taxable <= 0: return 0
    if taxable <= GIFT_B1: return round(taxable * 0.10)
    if taxable <= GIFT_B2: return round(taxable * 0.15 - QD_GIFT_15)
    return round(taxable * 0.20 - QD_GIFT_20)

def estate_tax_amount(taxable: int) -> int:
    if taxable <= 0: return 0
    if taxable <= EST_B1: return round(taxable * 0.10)
    if taxable <= EST_B2: return round(taxable * 0.15 - QD_EST_15)
    return round(taxable * 0.20 - QD_EST_20)

# ---------------- 輸入 ----------------
st.write("### 一、輸入參數")
c1, c2 = st.columns(2)
with c1:
    total_assets = st.number_input("第一代：總資產", min_value=0, value=200_000_000, step=1_000_000)
    premium = st.number_input("保費（第一代投入）", min_value=0, value=6_000_000, step=100_000)
    cvp = st.number_input("保價金／CVP（贈與課稅基礎）", min_value=0, value=2_000_000, step=100_000)
with c2:
    face = st.number_input("保額（第三代可得之理賠金）", min_value=0, value=30_000_000, step=1_000_000)
    donors = st.number_input("贈與人數（倍增年度免稅額；例：父母=2）", min_value=1, value=1, step=1)
    lineal_cnt_gen1 = st.number_input("第一代：直系卑親屬人數（扣除×每人560,000）", min_value=0, value=0, step=1)

chg_owner = st.checkbox("勾選：變更要保人（第一代 → 第二代）", value=True)
st.caption("被保人＝第二代；受益人＝第三代。若勾選變更要保人，第一代將在保單初期以 CVP 進行保單贈與。")

# 第二代扣除（可簡化沿用同數值；如需更細，可再延伸輸入）
with st.expander("第二代遺產扣除（如需調整）", expanded=False):
    lineal_cnt_gen2 = st.number_input("第二代：直系卑親屬人數（扣除×每人560,000）", min_value=0, value=0, step=1, key="lineal2")
    spouse_ded2 = st.number_input("第二代：配偶扣除（預設 5,330,000）", min_value=0, value=SPOUSE_DEDUCT, step=10_000, key="sp2")
    funeral_ded2 = st.number_input("第二代：喪葬費（預設 1,380,000）", min_value=0, value=FUNERAL_DEDUCT, step=10_000, key="fu2")
else_spacer = st.empty()

# ---------------- 計算（無規劃 vs 有規劃） ----------------
donors = int(donors)
L1 = int(lineal_cnt_gen1)
L2 = int(lineal_cnt_gen2 if 'lineal_cnt_gen2' in locals() else 0)
sp2 = int(spouse_ded2 if 'spouse_ded2' in locals() else SPOUSE_DEDUCT)
fu2 = int(funeral_ded2 if 'funeral_ded2' in locals() else FUNERAL_DEDUCT)

# --- 無規劃（不變更要保人） ---
# Gen1：沒有贈與；買保單後資產 = total - premium + cvp（現金轉保單資產）
gen1_assets_after_policy = total_assets - premium + cvp
gen1_estate_base_noplan = max(gen1_assets_after_policy - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - L1*LINEAL_PER, 0)
gen1_estate_tax_noplan = estate_tax_amount(gen1_estate_base_noplan)

# Gen2 承接（無規劃）：
gen2_inherit_noplan = total_assets - premium + cvp - gen1_estate_tax_noplan  # estate paid out of the estate
# Gen2 遺產稅（無規劃；保額於第二代身故時直接給第三代，不列入第二代遺產）
gen2_estate_base_noplan = max(gen2_inherit_noplan - ESTATE_EXEMPT - sp2 - fu2 - L2*LINEAL_PER, 0)
gen2_estate_tax_noplan = estate_tax_amount(gen2_estate_base_noplan)
# 第三代最終（無規劃）：繼承第二代淨額 + 保額理賠（指定受益人）
gen3_final_noplan = gen2_inherit_noplan - gen2_estate_tax_noplan + face

# --- 有規劃（變更要保人：以 CVP 贈與） ---
gift_base_plan = max(cvp - donors*GIFT_EXEMPT, 0) if chg_owner else 0
gift_tax_plan = gift_tax(gift_base_plan) if chg_owner else 0

# 第一代在完成贈與後持有資產：
# 起點：購入後 total - premium + cvp；贈與把 CVP 轉出 → total - premium；再付贈與稅
gen1_assets_after_gift = (total_assets - premium) - gift_tax_plan if chg_owner else gen1_assets_after_policy

gen1_estate_base_plan = max(gen1_assets_after_gift - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - L1*LINEAL_PER, 0)
gen1_estate_tax_plan = estate_tax_amount(gen1_estate_base_plan)

# Gen2 承接（有規劃）：
gen2_inherit_plan = gen1_assets_after_gift - gen1_estate_tax_plan
# Gen2 遺產（有規劃）：不含保額；保額在第二代身故時直接給第三代
gen2_estate_base_plan = max(gen2_inherit_plan - ESTATE_EXEMPT - sp2 - fu2 - L2*LINEAL_PER, 0)
gen2_estate_tax_plan = estate_tax_amount(gen2_estate_base_plan)
gen3_final_plan = gen2_inherit_plan - gen2_estate_tax_plan + face

# 整體對比
total_tax_noplan = gen1_estate_tax_noplan + gen2_estate_tax_noplan  # （無贈與稅）
total_tax_plan = gift_tax_plan + gen1_estate_tax_plan + gen2_estate_tax_plan
delta_save = total_tax_noplan - total_tax_plan

st.write("---")
st.subheader("二、結果一覽（關鍵數字）")
a,b,c,d = st.columns(4)
a.metric("第一代贈與稅（有規劃）", cur(gift_tax_plan))
b.metric("第一代遺產稅（無／有）", f"{cur(gen1_estate_tax_noplan)} / {cur(gen1_estate_tax_plan)}")
c.metric("第二代遺產稅（無／有）", f"{cur(gen2_estate_tax_noplan)} / {cur(gen2_estate_tax_plan)}")
d.metric("第三代最終承接（無／有）", f"{cur(gen3_final_noplan)} / {cur(gen3_final_plan)}")

st.write("### 三、分段明細（無規劃 vs 有規劃）")
st.table({
    "階段": [
        "第一代：贈與課稅基礎（CVP－免稅額×贈與人）",
        "第一代：贈與稅",
        "第一代：遺產課稅基礎",
        "第一代：遺產稅",
        "第二代：承接淨額",
        "第二代：遺產課稅基礎",
        "第二代：遺產稅",
        "第三代：最終承接（含保額理賠）",
        "總稅負（贈與＋兩代遺產）",
        "整體節省（規劃－未規劃）",
    ],
    "無規劃": [
        "—",
        "—",
        cur(gen1_estate_base_noplan),
        cur(gen1_estate_tax_noplan),
        cur(gen2_inherit_noplan),
        cur(gen2_estate_base_noplan),
        cur(gen2_estate_tax_noplan),
        cur(gen3_final_noplan),
        cur(total_tax_noplan),
        "—",
    ],
    "有規劃（變更要保人）": [
        cur(gift_base_plan),
        cur(gift_tax_plan),
        cur(gen1_estate_base_plan),
        cur(gen1_estate_tax_plan),
        cur(gen2_inherit_plan),
        cur(gen2_estate_base_plan),
        cur(gen2_estate_tax_plan),
        cur(gen3_final_plan),
        cur(total_tax_plan),
        cur(delta_save),
    ]
})

st.info("要點：保單在第一代即以 CVP 作贈與，壓低贈與稅基；保額於第二代身故時直達第三代，通常不列入第二代遺產。整體上可同時降低兩代遺產稅與贈與稅的合計負擔。")