import streamlit as st
import pandas as pd

st.set_page_config(page_title="三代傳承試算 v2｜保單折價贈與（固定法規）", page_icon="🏛️", layout="centered")
st.title("🏛️ 三代傳承試算 v2：無規劃 vs 有規劃（變更要保人）")
st.caption("台灣贈與稅／遺產稅 2025 年度數值固定；本工具僅供教學。")

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

st.write("### 法規級距（固定）")
colA, colB = st.columns(2)
with colA:
    st.markdown("**贈與稅** 年免稅額 **2,440,000**")
    st.table(pd.DataFrame({
        "級距": ["10%", "15%", "20%"],
        "課稅基礎": [f"≤ {cur(GIFT_B1)}", f"{cur(GIFT_B1)} < ~ ≤ {cur(GIFT_B2)}", f"> {cur(GIFT_B2)}"]
    }))
with colB:
    st.markdown("**遺產稅** 免稅額 **13,330,000** | 配偶 **5,330,000** | 喪葬 **1,380,000** | 直系卑親屬 **560,000/人**")
    st.table(pd.DataFrame({
        "級距": ["10%", "15%", "20%"],
        "課稅基礎": [f"≤ {cur(EST_B1)}", f"{cur(EST_B1)} < ~ ≤ {cur(EST_B2)}", f"> {cur(EST_B2)}"]
    }))

# ---------------- 輸入（步驟 1 & 2） ----------------
st.write("---")
st.header("步驟 1｜輸入第一代總資產")
total_assets = int(st.number_input("第一代：總資產", min_value=0, value=200_000_000, step=1_000_000))

st.header("步驟 2｜保單規劃（第一代為要保人，被保人第二代，受益人第三代）")
c1, c2, c3 = st.columns(3)
with c1:
    premium = int(st.number_input("保費（第一代投入）", min_value=0, value=6_000_000, step=100_000))
with c2:
    cvp = int(st.number_input("保價金／CVP（贈與課稅基礎）", min_value=0, value=2_000_000, step=100_000))
with c3:
    face = int(st.number_input("保額（第三代理賠金）", min_value=0, value=30_000_000, step=1_000_000))

d1, d2 = st.columns(2)
with d1:
    donors = int(st.number_input("贈與人數（倍增年免 2,440,000；例：父母=2）", min_value=1, value=1, step=1))
with d2:
    chg_owner = st.checkbox("✔️ 變更要保人（以 CVP 贈與保單給第二代）", value=True)

st.caption("勾選後：保費自第一代總資產扣除，CVP 列入贈與計算；保單所有權轉至第二代。")

# 扣除人數
lineal_cnt_gen1 = int(st.number_input("第一代：直系卑親屬人數（扣除 × 560,000）", min_value=0, value=0, step=1))
with st.expander("（可選）第二代遺產扣除人數", expanded=False):
    lineal_cnt_gen2 = int(st.number_input("第二代：直系卑親屬人數", min_value=0, value=0, step=1))

# ---------------- 計算 ----------------
# Step 3: Gen1 Gift (only if chg_owner)
gift_base_plan = max(cvp - donors * GIFT_EXEMPT, 0) if chg_owner else 0
gift_tax_plan = gift_tax(gift_base_plan) if chg_owner else 0

# Step 4: Gen1 Estate (No plan vs Plan)
# 無規劃：買保單後資產 = total - premium + cvp（現金變保單資產）
gen1_assets_after_policy = total_assets - premium + cvp
gen1_estate_base_noplan = max(gen1_assets_after_policy - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen1*LINEAL_PER, 0)
gen1_estate_tax_noplan = estate_tax_amount(gen1_estate_base_noplan)
gen2_inherit_noplan = gen1_assets_after_policy - gen1_estate_tax_noplan

# 有規劃：完成贈與後資產 = total - premium - 贈與稅（CVP 已轉出給第二代）
gen1_assets_after_gift = (total_assets - premium) - gift_tax_plan if chg_owner else gen1_assets_after_policy
gen1_estate_base_plan = max(gen1_assets_after_gift - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen1*LINEAL_PER, 0)
gen1_estate_tax_plan = estate_tax_amount(gen1_estate_base_plan)
gen2_inherit_plan = gen1_assets_after_gift - gen1_estate_tax_plan

# Step 5: Gen2 Estate → Gen3
# 受益人指定第三代：保額不列入第二代遺產，身故時直接給第三代
gen2_estate_base_noplan = max(gen2_inherit_noplan - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2*LINEAL_PER, 0)
gen2_estate_tax_noplan = estate_tax_amount(gen2_estate_base_noplan)
gen3_final_noplan = gen2_inherit_noplan - gen2_estate_tax_noplan + face

gen2_estate_base_plan = max(gen2_inherit_plan - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2*LINEAL_PER, 0)
gen2_estate_tax_plan = estate_tax_amount(gen2_estate_base_plan)
gen3_final_plan = gen2_inherit_plan - gen2_estate_tax_plan + face

# Totals
total_tax_noplan = gen1_estate_tax_noplan + gen2_estate_tax_noplan
total_tax_plan = gift_tax_plan + gen1_estate_tax_plan + gen2_estate_tax_plan
delta_save = total_tax_noplan - total_tax_plan

# ---------------- 輸出（摘要 + 步驟表） ----------------
st.write("---")
st.header("結果摘要")
s1, s2, s3, s4 = st.columns(4)
s1.metric("第一代贈與稅（有規劃）", cur(gift_tax_plan))
s2.metric("第一代遺產稅（無／有）", f"{cur(gen1_estate_tax_noplan)} / {cur(gen1_estate_tax_plan)}")
s3.metric("第二代遺產稅（無／有）", f"{cur(gen2_estate_tax_noplan)} / {cur(gen2_estate_tax_plan)}")
s4.metric("第三代最終承接（無／有）", f"{cur(gen3_final_noplan)} / {cur(gen3_final_plan)}")

st.write("### 步驟 3～5 明細（無規劃 vs 有規劃）")
df = pd.DataFrame({
    "階段/指標": [
        "步驟3｜第一代：贈與課稅基礎（CVP－年免×人數）",
        "步驟3｜第一代：贈與稅",
        "步驟4｜第一代：遺產課稅基礎",
        "步驟4｜第一代：遺產稅",
        "步驟4→5｜第二代：承接淨額",
        "步驟5｜第二代：遺產課稅基礎",
        "步驟5｜第二代：遺產稅",
        "最終｜第三代承接（含保額理賠）",
        "合計｜總稅負（贈與＋兩代遺產）",
        "整體節省（差額）",
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
st.table(df)

st.info("閱讀方式：照著「步驟 1～5」往下看，左欄是無規劃，右欄是有規劃（變更要保人）。每一步都顯示『課稅基礎 → 稅額 → 承接淨額』，最後比較到第三代的最終承接金額與總稅負差異。")