import streamlit as st

st.set_page_config(page_title="保單壓縮資產｜固定法規版（贈與＋遺產）", page_icon="📊", layout="centered")
st.title("📊 無規劃 vs 有規劃：保單折價贈與（固定法規級距與免稅額）")
st.caption("台灣贈與稅／遺產稅 2025 年度法規數值已固定；本工具僅供教學，不構成稅務建議。")

# ------------------ 固定法規參數（2025） ------------------
# 贈與稅
GIFT_EXEMPT = 2_440_000
GIFT_B1 = 28_110_000
GIFT_B2 = 56_210_000
QD_GIFT_15 = 1_405_500
QD_GIFT_20 = 4_216_000

# 遺產稅
ESTATE_EXEMPT = 13_330_000
SPOUSE_DEDUCT = 5_330_000
FUNERAL_DEDUCT = 1_380_000
LINEAL_DEDUCT_PER = 560_000
EST_B1 = 56_210_000
EST_B2 = 112_420_000
QD_EST_15 = 2_810_500
QD_EST_20 = 8_431_500

def cur(n): return f"{int(n):,}"

st.write("### 一、固定法規（2025）")
colA, colB = st.columns(2)
with colA:
    st.markdown("**贈與稅**（年免稅額固定 **2,440,000**）")
    st.table({
        "級距": ["10%", "15%", "20%"],
        "課稅基礎": [f"≤ {cur(GIFT_B1)}", f"{cur(GIFT_B1)} < ~ ≤ {cur(GIFT_B2)}", f"> {cur(GIFT_B2)}"]
    })
with colB:
    st.markdown("**遺產稅**（免稅額固定 **13,330,000**）")
    st.table({
        "級距": ["10%", "15%", "20%"],
        "課稅基礎": [f"≤ {cur(EST_B1)}", f"{cur(EST_B1)} < ~ ≤ {cur(EST_B2)}", f"> {cur(EST_B2)}"]
    })
st.caption("扣除額（固定）：配偶 5,330,000；喪葬費 1,380,000；直系卑親屬每人 560,000。")

# ------------------ 輸入區 ------------------
st.write("---")
st.subheader("二、輸入情境參數（只輸入數字，不調整法規）")
c1, c2 = st.columns(2)
with c1:
    premium = st.number_input("保費（無規劃：以保費為贈與稅稅基）", min_value=0, value=6_000_000, step=100_000)
    cvp = st.number_input("CVP（有規劃：以 CVP 為贈與稅稅基）", min_value=0, value=2_000_000, step=100_000)
    donors = st.number_input("贈與人數（倍增年度贈與免稅額；例：父母=2）", min_value=1, value=1, step=1)
with c2:
    gross_other = st.number_input("其他遺產總額（不含壽險理賠金）", min_value=0, value=120_000_000, step=1_000_000)
    insurance_payout = st.number_input("壽險理賠金（身故保險金）", min_value=0, value=20_000_000, step=500_000)
    lineal_cnt = st.number_input("直系卑親屬人數（每人 560,000 扣除）", min_value=0, value=0, step=1)

premium = int(premium); cvp = int(cvp); donors = int(donors)
gross_other = int(gross_other); insurance_payout = int(insurance_payout); lineal_cnt = int(lineal_cnt)

# ------------------ 計算函數 ------------------
def gift_tax(taxable: int) -> int:
    if taxable <= 0:
        return 0
    if taxable <= GIFT_B1:
        return round(taxable * 0.10)
    if taxable <= GIFT_B2:
        return round(taxable * 0.15 - QD_GIFT_15)
    return round(taxable * 0.20 - QD_GIFT_20)

def estate_tax_amount(taxable: int) -> int:
    if taxable <= 0:
        return 0
    if taxable <= EST_B1:
        return round(taxable * 0.10)
    if taxable <= EST_B2:
        return round(taxable * 0.15 - QD_EST_15)
    return round(taxable * 0.20 - QD_EST_20)

# ------------------ 贈與稅（無／有規劃） ------------------
gift_base_cash = max(premium - donors * GIFT_EXEMPT, 0)
gift_tax_cash = gift_tax(gift_base_cash)

gift_base_cvp = max(cvp - donors * GIFT_EXEMPT, 0)
gift_tax_cvp = gift_tax(gift_base_cvp)

# ------------------ 遺產稅（無／有規劃） ------------------
# 無規劃：理賠金列入遺產
estate_base_noplan = max(
    (gross_other + insurance_payout) - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt * LINEAL_DEDUCT_PER, 0
)
estate_tax_noplan = estate_tax_amount(estate_base_noplan)

# 有規劃：指定受益人 → 理賠金排除於遺產
estate_base_plan = max(
    gross_other - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt * LINEAL_DEDUCT_PER, 0
)
estate_tax_plan = estate_tax_amount(estate_base_plan)

# ------------------ 彙總 ------------------
total_noplan = gift_tax_cash + estate_tax_noplan
total_plan = gift_tax_cvp + estate_tax_plan
delta_total = total_noplan - total_plan

st.write("---")
st.subheader("三、總稅負對比（贈與＋遺產）")
m1, m2, m3, m4 = st.columns(4)
m1.metric("無規劃：贈與稅", cur(gift_tax_cash))
m2.metric("無規劃：遺產稅", cur(estate_tax_noplan))
m3.metric("有規劃：總稅負", cur(total_plan))
m4.metric("整體節省", cur(delta_total))

st.markdown("##### 明細表")
st.table({
    "項目": [
        "贈與：課稅基礎（無=保費 / 有=CVP）",
        "贈與：稅額（無 / 有）",
        "遺產：課稅基礎（無=含保險金 / 有=排除保險金）",
        "遺產：稅額（無 / 有）",
        "總稅負（無 / 有）",
        "整體節省（差額）",
    ],
    "金額": [
        f"{cur(gift_base_cash)} / {cur(gift_base_cvp)}",
        f"{cur(gift_tax_cash)} / {cur(gift_tax_cvp)}",
        f"{cur(estate_base_noplan)} / {cur(estate_base_plan)}",
        f"{cur(estate_tax_noplan)} / {cur(estate_tax_plan)}",
        f"{cur(total_noplan)} / {cur(total_plan)}",
        f"{cur(delta_total)}",
    ]
})

st.info("**要點**：有規劃以 CVP 為贈與稅稅基、並指定受益人排除壽險理賠金於遺產，通常可同時降低贈與稅與遺產稅的合計負擔。")