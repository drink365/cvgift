import streamlit as st

st.set_page_config(page_title="保單壓縮資產｜有無規劃一鍵比較（含遺產稅）", page_icon="📊", layout="centered")
st.title("📊 有無規劃一鍵比較：保單折價贈與（含遺產稅排除效果）")
st.caption("台灣贈與稅／遺產稅（2025 累進）簡化模型｜請以最新法令與專業意見為準")

with st.expander("本工具做什麼？", expanded=True):
    st.markdown("""
    - 只做 **一件事**：比較 **無規劃** vs **有規劃** 的總稅負差異。  
      - **無規劃**：直接現金贈與（以保費為稅基），且身故時壽險理賠金可能**列入遺產**。  
      - **有規劃**：先繳保費→以 **CVP** 贈與保單（變更要保人），並**指定受益人**，壽險理賠金**排除於遺產**。  
    - 即使 **CVP > 年免稅額**、進入較高級距，只要 CVP 遠小於保費，通常仍顯著節稅。
    """)

# ------------------ Inputs ------------------
st.subheader("一、贈與稅參數（有／無規劃對比）")
c1, c2 = st.columns(2)
with c1:
    premium = st.number_input("保費（無規劃稅基）", min_value=0, value=6000000, step=100000)
    cvp = st.number_input("CVP（有規劃稅基）", min_value=0, value=2000000, step=100000)
    donors = st.number_input("贈與人數（倍增年度免稅額；例：父母=2）", min_value=1, value=1, step=1)
with c2:
    gift_exempt = st.number_input("年度贈與免稅額（預設 2,440,000）", min_value=0, value=2440000, step=10000)
    st.markdown("**贈與稅級距（2025 可自訂）**")
    g_b1 = st.number_input("10% 稅率上限", min_value=0, value=28110000, step=10000)
    g_b2 = st.number_input("15% 稅率上限", min_value=0, value=56210000, step=10000)

premium = int(premium); cvp = int(cvp); donors = int(donors)
gift_exempt = int(gift_exempt); g_b1 = int(g_b1); g_b2 = int(g_b2)

def gift_tax(taxable: int, b1: int, b2: int) -> int:
    if taxable <= 0:
        return 0
    if taxable <= b1:
        return round(taxable * 0.10)
    if taxable <= b2:
        return round(taxable * 0.15 - 1_405_500)
    return round(taxable * 0.20 - 4_216_000)

def currency(n): return f"{int(n):,}"

# 無規劃：以保費為稅基
gift_base_cash = max(premium - donors * gift_exempt, 0)
gift_tax_cash = gift_tax(gift_base_cash, g_b1, g_b2)

# 有規劃：以 CVP 為稅基（變更要保人）
gift_base_cvp = max(cvp - donors * gift_exempt, 0)
gift_tax_cvp = gift_tax(gift_base_cvp, g_b1, g_b2)

st.write("---")
st.subheader("二、遺產稅參數（同頁面延伸，不是另一個工具）")
st.caption("指定受益人之壽險理賠金在台灣可排除於遺產（遺贈稅法第16條第9款）。")

e1, e2 = st.columns(2)
with e1:
    gross_other = st.number_input("其他遺產總額（不含壽險理賠金）", min_value=0, value=120000000, step=1000000)
    insurance_payout = st.number_input("壽險理賠金（身故保險金）", min_value=0, value=20000000, step=500000)
    exclude_insurance = st.checkbox("有規劃：指定受益人 → 壽險排除於遺產", value=True)
with e2:
    estate_exempt = st.number_input("遺產免稅額（預設 13,330,000）", min_value=0, value=13330000, step=10000)
    e_b1 = st.number_input("10% 稅率上限", min_value=0, value=56210000, step=10000)
    e_b2 = st.number_input("15% 稅率上限", min_value=0, value=112420000, step=10000)
    spouse = st.number_input("配偶扣除（預設 5,330,000）", min_value=0, value=5330000, step=10000)
    funeral = st.number_input("喪葬費（預設 1,380,000）", min_value=0, value=1380000, step=10000)
    lineal = st.number_input("直系卑親屬扣除（總額）", min_value=0, value=0, step=10000)

gross_other = int(gross_other); insurance_payout = int(insurance_payout)
estate_exempt = int(estate_exempt); e_b1 = int(e_b1); e_b2 = int(e_b2)
spouse = int(spouse); funeral = int(funeral); lineal = int(lineal)

def estate_tax_amount(taxable: int, b1: int, b2: int) -> int:
    if taxable <= 0:
        return 0
    if taxable <= b1:
        return round(taxable * 0.10)
    if taxable <= b2:
        return round(taxable * 0.15 - 2_810_500)
    return round(taxable * 0.20 - 8_431_500)

# 無規劃：理賠金列入遺產
estate_base_noplan = max((gross_other + insurance_payout) - estate_exempt - spouse - funeral - lineal, 0)
estate_tax_noplan = estate_tax_amount(estate_base_noplan, e_b1, e_b2)

# 有規劃：指定受益人，理賠金排除
excluded = insurance_payout if exclude_insurance else 0
estate_base_plan = max((gross_other + insurance_payout - excluded) - estate_exempt - spouse - funeral - lineal, 0)
estate_tax_plan = estate_tax_amount(estate_base_plan, e_b1, e_b2)

st.write("---")
st.subheader("三、總稅負對比（贈與＋遺產）")
cA, cB, cC = st.columns(3)
total_noplan = gift_tax_cash + estate_tax_noplan
total_plan = gift_tax_cvp + estate_tax_plan
delta_total = total_noplan - total_plan

cA.metric("無規劃：總稅負", currency(total_noplan))
cB.metric("有規劃：總稅負", currency(total_plan))
cC.metric("整體節省（總稅差）", currency(delta_total))

st.markdown("##### 明細表")
st.table({
    "項目": [
        "贈與：課稅基礎（無規劃=保費 / 有規劃=CVP）",
        "贈與：稅額（無 / 有）",
        "遺產：課稅基礎（無=含保險金 / 有=排除保險金）",
        "遺產：稅額（無 / 有）",
        "總稅負（無 / 有）",
        "整體節省（差額）",
    ],
    "金額": [
        f"{currency(gift_base_cash)} / {currency(gift_base_cvp)}",
        f"{currency(gift_tax_cash)} / {currency(gift_tax_cvp)}",
        f"{currency(estate_base_noplan)} / {currency(estate_base_plan)}",
        f"{currency(estate_tax_noplan)} / {currency(estate_tax_plan)}",
        f"{currency(total_noplan)} / {currency(total_plan)}",
        f"{currency(delta_total)}"
    ]
})

st.info("""
**結論提示：**  
- **贈與稅面**：有規劃以 **CVP** 為稅基，多數情況顯著低於以 **保費** 為稅基。  
- **遺產稅面**：指定受益人之壽險理賠金可排除於遺產，降低遺產稅基。  
- 合規提醒：各項免稅額、扣除額與級距會依年度調整；實務請以主管機關公告與專業建議為準。
""")