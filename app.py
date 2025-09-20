import io
import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import datetime

st.set_page_config(page_title="三代傳承試算 v3｜保單折價贈與（固定法規）", page_icon="🏛️", layout="centered")
st.title("🏛️ 三代傳承試算 v3：無規劃 vs 有規劃（變更要保人）")
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

# ---------------- 輸入 ----------------
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

st.write("---")
total_assets = int(st.number_input("第一代：總資產", min_value=0, value=200_000_000, step=1_000_000))
premium = int(st.number_input("保費（第一代投入）", min_value=0, value=6_000_000, step=100_000))
cvp = int(st.number_input("保價金／CVP（贈與課稅基礎）", min_value=0, value=2_000_000, step=100_000))
face = int(st.number_input("保額（壽險理賠金）", min_value=0, value=30_000_000, step=1_000_000))
donors = int(st.number_input("贈與人數（例：父母=2）", min_value=1, value=1, step=1))
chg_owner = st.checkbox("✔️ 變更要保人（以 CVP 贈與保單給第二代）", value=True)
lineal_cnt_gen1 = int(st.number_input("第一代：直系卑親屬人數", min_value=0, value=0, step=1))
lineal_cnt_gen2 = int(st.number_input("第二代：直系卑親屬人數", min_value=0, value=0, step=1))
benef_to_gen3 = st.checkbox("✔️ 保額受益人指定『第三代』", value=True)

# ---------------- 計算 ----------------
gift_base_plan = max(cvp - donors * GIFT_EXEMPT, 0) if chg_owner else 0
gift_tax_plan = gift_tax(gift_base_plan) if chg_owner else 0

gen1_assets_after_policy = total_assets - premium + cvp
gen1_estate_base_noplan = max(gen1_assets_after_policy - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen1*LINEAL_PER, 0)
gen1_estate_tax_noplan = estate_tax_amount(gen1_estate_base_noplan)
gen2_inherit_noplan = gen1_assets_after_policy - gen1_estate_tax_noplan

gen1_assets_after_gift = (total_assets - premium) - gift_tax_plan if chg_owner else gen1_assets_after_policy
gen1_estate_base_plan = max(gen1_assets_after_gift - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen1*LINEAL_PER, 0)
gen1_estate_tax_plan = estate_tax_amount(gen1_estate_base_plan)
gen2_inherit_plan = gen1_assets_after_gift - gen1_estate_tax_plan

if benef_to_gen3:
    gen2_estate_base_noplan = max(gen2_inherit_noplan - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2*LINEAL_PER, 0)
    gen2_estate_tax_noplan = estate_tax_amount(gen2_estate_base_noplan)
    gen3_final_noplan = gen2_inherit_noplan - gen2_estate_tax_noplan + face

    gen2_estate_base_plan = max(gen2_inherit_plan - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2*LINEAL_PER, 0)
    gen2_estate_tax_plan = estate_tax_amount(gen2_estate_base_plan)
    gen3_final_plan = gen2_inherit_plan - gen2_estate_tax_plan + face
else:
    gen2_estate_base_noplan = max((gen2_inherit_noplan + face) - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2*LINEAL_PER, 0)
    gen2_estate_tax_noplan = estate_tax_amount(gen2_estate_base_noplan)
    gen3_final_noplan = gen2_inherit_noplan + face - gen2_estate_tax_noplan

    gen2_estate_base_plan = max((gen2_inherit_plan + face) - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2*LINEAL_PER, 0)
    gen2_estate_tax_plan = estate_tax_amount(gen2_estate_base_plan)
    gen3_final_plan = gen2_inherit_plan + face - gen2_estate_tax_plan

total_tax_noplan = gen1_estate_tax_noplan + gen2_estate_tax_noplan
total_tax_plan = gift_tax_plan + gen1_estate_tax_plan + gen2_estate_tax_plan
delta_save = total_tax_noplan - total_tax_plan

# ---------------- 輸出 ----------------
st.header("結果摘要")
s1, s2, s3, s4 = st.columns(4)
s1.metric("第一代贈與稅（有規劃）", cur(gift_tax_plan))
s2.metric("第一代遺產稅（無／有）", f"{cur(gen1_estate_tax_noplan)} / {cur(gen1_estate_tax_plan)}")
s3.metric("第二代遺產稅（無／有）", f"{cur(gen2_estate_tax_noplan)} / {cur(gen2_estate_tax_plan)}")
s4.metric("第三代最終承接（無／有）", f"{cur(gen3_final_noplan)} / {cur(gen3_final_plan)}")

# ---------------- PDF 匯出 ----------------
def build_pdf_bytes():
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    x_margin, y_margin = 15*mm, 15*mm
    y = h - y_margin

    # Brand Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_margin, y, "永傳家族辦公室 Grace Family Office")
    y -= 7*mm
    c.setFont("Helvetica", 10)
    c.drawString(x_margin, y, "《影響力》傳承策略平台 | 聯絡信箱：123@gracefo.com")
    y -= 7*mm
    c.drawString(x_margin, y, "報告日期：" + datetime.date.today().strftime("%Y-%m-%d"))
    y -= 10*mm

    # Title
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x_margin, y, "三代傳承試算報告（固定法規）")
    y -= 10*mm

    # Summary
    c.setFont("Helvetica", 11)
    c.drawString(x_margin, y, f"第一代贈與稅（有規劃）：{cur(gift_tax_plan)} 元")
    y -= 6*mm
    c.drawString(x_margin, y, f"第一代遺產稅（無／有）：{cur(gen1_estate_tax_noplan)}／{cur(gen1_estate_tax_plan)} 元")
    y -= 6*mm
    c.drawString(x_margin, y, f"第二代遺產稅（無／有）：{cur(gen2_estate_tax_noplan)}／{cur(gen2_estate_tax_plan)} 元")
    y -= 6*mm
    c.drawString(x_margin, y, f"第三代最終承接（無／有）：{cur(gen3_final_noplan)}／{cur(gen3_final_plan)} 元")
    y -= 6*mm
    c.drawString(x_margin, y, f"合計總稅負（無／有）：{cur(total_tax_noplan)}／{cur(total_tax_plan)} 元｜整體節省：{cur(delta_save)} 元")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

pdf_bytes = build_pdf_bytes()
st.download_button("⬇️ 下載 PDF 報告（含品牌抬頭）", data=pdf_bytes, file_name="三代傳承試算報告.pdf", mime="application/pdf")