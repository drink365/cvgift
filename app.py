# app.py
import io, os, datetime
import streamlit as st
import pandas as pd
from PIL import Image

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -------------------- Utils --------------------
def safe_open_image(path: str):
    """Return a PIL.Image if path is a valid image; else None."""
    if not os.path.exists(path):
        return None
    try:
        img = Image.open(path)
        img.load()  # force load to catch truncated files
        return img
    except Exception:
        return None

def safe_page_config():
    # 驗證 logo2.png 能否作為 favicon；不行就退回 emoji
    favicon = "🏛️"
    if safe_open_image("logo2.png") is not None:
        favicon = "logo2.png"
    st.set_page_config(
        page_title="三代傳承試算｜保單折價贈與（固定法規）",
        page_icon=favicon,
        layout="wide",
    )

def cur(n):
    try:
        return f"{int(round(n)):,}"
    except Exception:
        return str(n)

def gift_tax_amount(taxable: int, b1, b2, qd15, qd20) -> int:
    if taxable <= 0: return 0
    if taxable <= b1: return round(taxable * 0.10)
    if taxable <= b2: return round(taxable * 0.15 - qd15)
    return round(taxable * 0.20 - qd20)

def estate_tax_amount(taxable: int, b1, b2, qd15, qd20) -> int:
    if taxable <= 0: return 0
    if taxable <= b1: return round(taxable * 0.10)
    if taxable <= b2: return round(taxable * 0.15 - qd15)
    return round(taxable * 0.20 - qd20)

safe_page_config()

# -------------------- Header（含 Logo 防呆） --------------------
c1, c2 = st.columns([1, 5])
with c1:
    page_logo = safe_open_image("logo.png")
    if page_logo is not None:
        st.image(page_logo, use_container_width=True)
    else:
        st.markdown("### 永傳家族辦公室 Grace Family Office")
with c2:
    st.title("三代傳承試算：無規劃 vs 有規劃（變更要保人）")
    st.caption("台灣贈與稅／遺產稅 2025 年度數值固定；本工具僅供教學。")

# -------------------- 固定法規數值（2025） --------------------
GIFT_EXEMPT = 2_440_000
GIFT_B1, GIFT_B2 = 28_110_000, 56_210_000
QD_GIFT_15, QD_GIFT_20 = 1_405_500, 4_216_000

ESTATE_EXEMPT = 13_330_000
SPOUSE_DEDUCT = 5_330_000
FUNERAL_DEDUCT = 1_380_000
LINEAL_PER = 560_000
EST_B1, EST_B2 = 56_210_000, 112_420_000
QD_EST_15, QD_EST_20 = 2_810_500, 8_431_500

# -------------------- 法規級距表 --------------------
colA, colB = st.columns(2)
with colA:
    st.markdown("### 贈與稅（年免 2,440,000）")
    st.table(pd.DataFrame({
        "級距": ["10%", "15%", "20%"],
        "課稅基礎": [f"≤ {cur(GIFT_B1)}", f"{cur(GIFT_B1)} < ~ ≤ {cur(GIFT_B2)}", f"> {cur(GIFT_B2)}"]
    }))
with colB:
    st.markdown("### 遺產稅（免 13,330,000｜配偶 5,330,000｜喪葬 1,380,000｜直系 560,000/人）")
    st.table(pd.DataFrame({
        "級距": ["10%", "15%", "20%"],
        "課稅基礎": [f"≤ {cur(EST_B1)}", f"{cur(EST_B1)} < ~ ≤ {cur(EST_B2)}", f"> {cur(EST_B2)}"]
    }))

st.divider()

# -------------------- 輸入區 --------------------
left, right = st.columns(2)
with left:
    st.subheader("基礎輸入")
    total_assets = int(st.number_input("第一代：總資產", min_value=0, value=200_000_000, step=1_000_000))
    donors = int(st.number_input("贈與人數（例：父母=2）", min_value=1, value=1, step=1))
    lineal_cnt_gen1 = int(st.number_input("第一代：直系卑親屬人數", min_value=0, value=0, step=1))
    lineal_cnt_gen2 = int(st.number_input("第二代：直系卑親屬人數", min_value=0, value=0, step=1))
with right:
    st.subheader("保單規劃")
    premium = int(st.number_input("保費（第一代投入）", min_value=0, value=6_000_000, step=100_000))
    cvp = int(st.number_input("保價金／CVP（贈與課稅基礎）", min_value=0, value=2_000_000, step=100_000))
    face = int(st.number_input("保額（壽險理賠金）", min_value=0, value=30_000_000, step=1_000_000))
    chg_owner = st.checkbox("✔️ 變更要保人（CVP 贈與給第二代）", value=True)
    benef_to_gen3 = st.checkbox(
        "✔️ 保額受益人指定第三代",
        value=True,
        help="勾選：保額不列入第二代遺產；未勾：保額列入第二代遺產課稅基礎"
    )

# -------------------- 計算核心 --------------------
# 步驟3：第一代贈與（僅勾選變更要保人才會發生）
gift_base_plan = max(cvp - donors * GIFT_EXEMPT, 0) if chg_owner else 0
gift_tax_plan = gift_tax_amount(gift_base_plan, GIFT_B1, GIFT_B2, QD_GIFT_15, QD_GIFT_20) if chg_owner else 0

# 步驟4：第一代遺產（無／有規劃）
# 無規劃：買保單後資產 = total - premium + cvp（現金換成保單資產）
gen1_assets_after_policy = total_assets - premium + cvp
gen1_estate_base_noplan = max(
    gen1_assets_after_policy - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen1 * LINEAL_PER, 0
)
gen1_estate_tax_noplan = estate_tax_amount(gen1_estate_base_noplan, EST_B1, EST_B2, QD_EST_15, QD_EST_20)
gen2_inherit_noplan = gen1_assets_after_policy - gen1_estate_tax_noplan

# 有規劃：完成贈與後資產 = total - premium - 贈與稅（CVP 轉出到第二代）
gen1_assets_after_gift = (total_assets - premium) - gift_tax_plan if chg_owner else gen1_assets_after_policy
gen1_estate_base_plan = max(
    gen1_assets_after_gift - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen1 * LINEAL_PER, 0
)
gen1_estate_tax_plan = estate_tax_amount(gen1_estate_base_plan, EST_B1, EST_B2, QD_EST_15, QD_EST_20)
gen2_inherit_plan = gen1_assets_after_gift - gen1_estate_tax_plan

# 步驟5：第二代遺產 → 第三代最終承接
if benef_to_gen3:
    # 保額不列入第二代遺產
    gen2_estate_base_noplan = max(
        gen2_inherit_noplan - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2 * LINEAL_PER, 0
    )
    gen2_estate_tax_noplan = estate_tax_amount(gen2_estate_base_noplan, EST_B1, EST_B2, QD_EST_15, QD_EST_20)
    gen3_final_noplan = gen2_inherit_noplan - gen2_estate_tax_noplan + face

    gen2_estate_base_plan = max(
        gen2_inherit_plan - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2 * LINEAL_PER, 0
    )
    gen2_estate_tax_plan = estate_tax_amount(gen2_estate_base_plan, EST_B1, EST_B2, QD_EST_15, QD_EST_20)
    gen3_final_plan = gen2_inherit_plan - gen2_estate_tax_plan + face
else:
    # 保額列入第二代遺產
    gen2_estate_base_noplan = max(
        (gen2_inherit_noplan + face) - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2 * LINEAL_PER, 0
    )
    gen2_estate_tax_noplan = estate_tax_amount(gen2_estate_base_noplan, EST_B1, EST_B2, QD_EST_15, QD_EST_20)
    gen3_final_noplan = gen2_inherit_noplan + face - gen2_estate_tax_noplan

    gen2_estate_base_plan = max(
        (gen2_inherit_plan + face) - ESTATE_EXEMPT - SPOUSE_DEDUCT - FUNERAL_DEDUCT - lineal_cnt_gen2 * LINEAL_PER, 0
    )
    gen2_estate_tax_plan = estate_tax_amount(gen2_estate_base_plan, EST_B1, EST_B2, QD_EST_15, QD_EST_20)
    gen3_final_plan = gen2_inherit_plan + face - gen2_estate_tax_plan

# 總稅負與差額
total_tax_noplan = gen1_estate_tax_noplan + gen2_estate_tax_noplan
total_tax_plan = gift_tax_plan + gen1_estate_tax_plan + gen2_estate_tax_plan
delta_save = total_tax_noplan - total_tax_plan

st.divider()

# -------------------- 結果摘要（表格，不再用 metric） --------------------
st.subheader("📊 結果摘要")
summary_df = pd.DataFrame({
    "項目": [
        "第一代贈與稅（有規劃）",
        "第一代遺產稅（無 / 有）",
        "第二代遺產稅（無 / 有）",
        "第三代最終承接（無 / 有）",
        "合計總稅負（無 / 有）",
        "整體節省（差額）",
    ],
    "金額": [
        f"{cur(gift_tax_plan)}",
        f"{cur(gen1_estate_tax_noplan)} / {cur(gen1_estate_tax_plan)}",
        f"{cur(gen2_estate_tax_noplan)} / {cur(gen2_estate_tax_plan)}",
        f"{cur(gen3_final_noplan)} / {cur(gen3_final_plan)}",
        f"{cur(total_tax_noplan)} / {cur(total_tax_plan)}",
        f"{cur(delta_save)}",
    ]
})
st.table(summary_df)

# -------------------- 步驟 3～5 明細（無規劃 vs 有規劃） --------------------
st.subheader("步驟 3～5 明細（無規劃 vs 有規劃）")
detail_df = pd.DataFrame({
    "階段/指標": [
        "步驟3｜第一代：贈與課稅基礎（CVP－年免×人數）",
        "步驟3｜第一代：贈與稅",
        "步驟4｜第一代：遺產課稅基礎",
        "步驟4｜第一代：遺產稅",
        "步驟4→5｜第二代：承接淨額",
        "步驟5｜第二代：遺產課稅基礎",
        "步驟5｜第二代：遺產稅",
        "最終｜第三代承接（依受益人設定）",
        "合計｜總稅負（贈與＋兩代遺產）",
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
    ]
})
st.dataframe(detail_df, use_container_width=True)

# -------------------- PDF 匯出（使用 NotoSansTC 若存在） --------------------
st.subheader("報告匯出（使用根目錄檔：logo.png / logo2.png / NotoSansTC-Regular.ttf）")

def build_pdf_bytes():
    # 字型：存在才註冊；失敗退回 Helvetica
    font_name = "Helvetica"
    if os.path.exists("NotoSansTC-Regular.ttf"):
        try:
            pdfmetrics.registerFont(TTFont("NotoSansTC", "NotoSansTC-Regular.ttf"))
            font_name = "NotoSansTC"
        except Exception:
            font_name = "Helvetica"

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    x_margin, y_margin = 15*mm, 15*mm
    y = h - y_margin

    # Logo + 抬頭（用 Pillow 讀圖再轉 bytes，避免 ReportLab 直接讀檔失敗）
    x_text = x_margin
    pil_logo = safe_open_image("logo.png")
    if pil_logo is not None:
        bio = io.BytesIO()
        pil_logo.save(bio, format="PNG")
        bio.seek(0)
        try:
            img = ImageReader(bio)
            c.drawImage(img, x_margin, y-12*mm, width=30*mm, height=12*mm,
                        preserveAspectRatio=True, mask='auto')
            x_text = x_margin + 32*mm
        except Exception:
            pass

    c.setFont(font_name, 14)
    c.drawString(x_text, y, "永傳家族辦公室 Grace Family Office")
    y -= 7*mm
    c.setFont(font_name, 10)
    c.drawString(x_text, y, "《影響力》傳承策略平台｜Email: 123@gracefo.com")
    y -= 7*mm
    c.drawString(x_text, y, "報告日期：" + datetime.date.today().strftime("%Y-%m-%d"))
    y -= 10*mm

    c.setFont(font_name, 13)
    c.drawString(x_margin, y, "三代傳承試算報告（固定法規）")
    y -= 10*mm

    c.setFont(font_name, 11)
    lines = [
        f"第一代贈與稅（有規劃）：{cur(gift_tax_plan)} 元",
        f"第一代遺產稅（無／有）：{cur(gen1_estate_tax_noplan)}／{cur(gen1_estate_tax_plan)} 元",
        f"第二代遺產稅（無／有）：{cur(gen2_estate_tax_noplan)}／{cur(gen2_estate_tax_plan)} 元",
        f"第三代最終承接（無／有）：{cur(gen3_final_noplan)}／{cur(gen3_final_plan)} 元",
        f"合計總稅負（無／有）：{cur(total_tax_noplan)}／{cur(total_tax_plan)} 元",
        f"整體節省（差額）：{cur(delta_save)} 元",
    ]
    for t in lines:
        c.drawString(x_margin, y, t)
        y -= 6*mm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

pdf_bytes = build_pdf_bytes()
st.download_button(
    "⬇️ 下載 PDF 報告",
    data=pdf_bytes,
    file_name="三代傳承試算報告.pdf",
    mime="application/pdf"
)
