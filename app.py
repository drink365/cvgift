import math
import streamlit as st

st.set_page_config(page_title="CVP 折價贈與＋台灣遺贈稅｜進階版", page_icon="🧮", layout="centered")

st.title("🧮 保單折價贈與（CVP）＋ 台灣遺產稅／贈與稅｜進階版")
st.caption("教學用途｜請以最新法令與主管機關規定為準")

with st.expander("本工具做什麼？", expanded=True):
    st.markdown("""
    - **模組 A：CVP 折價贈與比較**
      - 比較「現金贈與」 vs 「以 CVP 為稅基之保單贈與」
      - ✅ **新功能 1**：**分年贈與試算**（一次贈與 vs N 年平均） + **贈與人數**（倍增免稅額）
      - ✅ **新功能 2**：**第1年 vs 第2年 CVP** 情境切換與稅負比較
    - **模組 B：台灣遺產稅／贈與稅（累進）**
      - 2025 預設級距與免稅額，可自行調整
      - 遺產稅可勾選「指定受益人之壽險給付排除」
    - 注意：此為簡化模型，**各項扣除與特別規定**請依實際狀況處理。
    """)

tab1, tab2 = st.tabs(["① CVP 折價贈與（含分年 & 年份情境）", "② 台灣遺產稅／贈與稅"])

# ---------------------- 共用：累進贈與稅 ----------------------
def make_gift_tax_fn(b1, b2):
    """回傳台灣贈與稅計算函數（2025 預設級距下的差額稅額）。"""
    def _calc(taxable):
        if taxable <= 0:
            return 0
        if taxable <= b1:
            return round(taxable * 0.10)
        if taxable <= b2:
            return round(taxable * 0.15 - 1_405_500)
        return round(taxable * 0.20 - 4_216_000)
    return _calc

def currency(n):
    return f"{n:,.0f}"

# ----------------------
# TAB 1: CVP gift compare with new features
# ----------------------
with tab1:
    st.subheader("A. 參數輸入")
    c1, c2 = st.columns(2)
    with c1:
        premium = st.number_input("實際投入保費", min_value=0, value=6_000_000, step=100_000, format="%,d")
        cvp_y1 = st.number_input("第 1 年底 CVP", min_value=0, value=2_000_000, step=100_000, format="%,d")
        cvp_y2 = st.number_input("第 2 年底 CVP（作情境比較）", min_value=0, value=3_000_000, step=100_000, format="%,d")
    with c2:
        donors = st.number_input("贈與人數（倍增年度免稅額；例：父母各贈=2）", min_value=1, value=1, step=1)
        gift_exempt = st.number_input("台灣年度贈與免稅額（2025 預設 2,440,000）", min_value=0, value=2_440_000, step=10_000, format="%,d")
        st.markdown("**贈與稅累進級距（可自訂；2025 預設）**")
        b1 = st.number_input("10% 稅率上限", min_value=0, value=28_110_000, step=10_000, format="%,d")
        b2 = st.number_input("15% 稅率上限", min_value=0, value=56_210_000, step=10_000, format="%,d")

    gift_tax = make_gift_tax_fn(b1, b2)
    total_exemption = int(donors) * gift_exempt

    st.write("---")
    st.subheader("B. 一次贈與 vs 分年贈與（平均分攤）")

    c3, c4 = st.columns(2)
    with c3:
        split_years = st.number_input("分年年數（平均分攤；一次贈與請填 1）", min_value=1, value=1, step=1)
        use_cvp_year = st.radio("贈與稅基採用哪個年份 CVP？", ["第1年 CVP", "第2年 CVP"], horizontal=True)
    with c4:
        if use_cvp_year == "第1年 CVP":
            cvp_used = cvp_y1
        else:
            cvp_used = cvp_y2
        st.metric("採用之 CVP（稅基）", currency(cvp_used))

    # --- 一次贈與（單年）：以 CVP 為稅基
    lump_base = max(cvp_used - total_exemption, 0)
    lump_tax = gift_tax(lump_base)

    # --- 分年贈與：把 CVP 當作「總額」平均切成 N 等分，每年課一次稅；每年都有 donors * gift_exempt 的免稅額
    per_year_gift = cvp_used / split_years if split_years > 0 else 0
    per_year_base = [max(round(per_year_gift) - total_exemption, 0) for _ in range(int(split_years))]
    per_year_tax = [gift_tax(b) for b in per_year_base]
    spread_tax_total = sum(per_year_tax)

    m1, m2, m3 = st.columns(3)
    m1.metric("一次贈與：課稅基礎", currency(lump_base))
    m2.metric("一次贈與：贈與稅", currency(lump_tax))
    m3.metric("分年總稅額（N 年平均）", currency(spread_tax_total))

    st.markdown("##### 分年明細")
    st.table({
        "年度": [f"第{i+1}年" for i in range(int(split_years))],
        "每年贈與額": [currency(round(per_year_gift)) for _ in range(int(split_years))],
        "每年課稅基礎": [currency(b) for b in per_year_base],
        "每年贈與稅": [currency(t) for t in per_year_tax],
    })

    st.info("說明：台灣贈與稅之 **年度免稅額為『每位贈與人』每年計算**，所以可用「贈與人數」倍增免稅額；分年贈與可多次利用年度免稅額。**受贈人分拆在台灣本身不影響免稅額**（免稅額依贈與人計算），常見做法為「雙親分別贈與」或「跨年分散」。")

    st.write("---")
    st.subheader("C. 第 1 年 vs 第 2 年 CVP 情境比較")
    def compute_tax_for_cvp(cvp_val):
        base = max(cvp_val - total_exemption, 0)
        return gift_tax(base), base

    tax_y1, base_y1 = compute_tax_for_cvp(cvp_y1)
    tax_y2, base_y2 = compute_tax_for_cvp(cvp_y2)

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("第1年：CVP", currency(cvp_y1))
    n2.metric("第1年：稅額", currency(tax_y1))
    n3.metric("第2年：CVP", currency(cvp_y2))
    n4.metric("第2年：稅額", currency(tax_y2))

    delta = tax_y2 - tax_y1
    if delta > 0:
        st.warning(f"第2年稅額較高：+{currency(delta)}（通常因 CVP 上升）")
    elif delta < 0:
        st.success(f"第2年稅額較低：{currency(delta)}")
    else:
        st.info("兩年稅額相同。")

    st.caption("＊此處為單年一次贈與的情境比較；若搭配分年贈與，請以上方分年模組為準。")

# ----------------------
# TAB 2: Estate & Gift Tax Taiwan (same as v1 with small clarifications)
# ----------------------
with tab2:
    st.subheader("台灣贈與稅 / 遺產稅（簡化版）")
    mode = st.radio("選擇稅別", ["贈與稅（累進）", "遺產稅（累進）"], horizontal=True)

    if mode.startswith("贈與"):
        st.markdown("**年度免稅額（預設 2,440,000）與級距（2025）**")
        g_ex = st.number_input("年度贈與免稅額", min_value=0, value=2_440_000, step=10_000, format="%,d")
        g_b1 = st.number_input("10% 稅率上限", min_value=0, value=28_110_000, step=10_000, format="%,d", key="gb1")
        g_b2 = st.number_input("15% 稅率上限", min_value=0, value=56_210_000, step=10_000, format="%,d", key="gb2")
        gift_amount = st.number_input("本次贈與（淨額）", min_value=0, value=6_000_000, step=100_000, format="%,d")

        taxable = max(gift_amount - g_ex, 0)
        gift_tax_v2 = make_gift_tax_fn(g_b1, g_b2)
        tax = gift_tax_v2(taxable)

        c1, c2, c3 = st.columns(3)
        c1.metric("課稅基礎（扣除免稅額）", currency(taxable))
        c2.metric("應納贈與稅", currency(tax))
        eff = (tax / gift_amount) if gift_amount else 0
        c3.metric("名目稅負率（稅/贈與）", f"{eff:.2%}" if gift_amount else "—")

        st.caption("備註：台灣贈與稅之 **年度免稅額為每位贈與人** 計算；受贈人多寡不影響免稅額，但不同贈與人可各自適用免稅額。")

    else:
        st.markdown("**遺產稅免稅額（預設 13,330,000）與級距（2025）**")
        e_ex = st.number_input("遺產免稅額", min_value=0, value=13_330_000, step=10_000, format="%,d")
        e_b1 = st.number_input("10% 稅率上限", min_value=0, value=56_210_000, step=10_000, format="%,d", key="eb1")
        e_b2 = st.number_input("15% 稅率上限", min_value=0, value=112_420_000, step=10_000, format="%,d", key="eb2")

        st.markdown("**可選扣除（簡化）**")
        spouse = st.number_input("配偶扣除（預設 5,330,000）", min_value=0, value=5_330_000, step=10_000, format="%,d")
        funeral = st.number_input("喪葬費用（預設 1,380,000）", min_value=0, value=1_380_000, step=10_000, format="%,d")
        lineal = st.number_input("直系卑親屬扣除（每人 560,000；此處輸入總額）", min_value=0, value=0, step=10_000, format="%,d")

        st.markdown("**保單給付是否排除於遺產？（遺贈稅法第16條第9款）**")
        insurance_excluded = st.checkbox("排除支付予『指定受益人』之壽險給付", value=True)
        insurance_amount = st.number_input("可排除之壽險給付金額", min_value=0, value=0, step=100_000, format="%,d")

        gross_estate = st.number_input("遺產總額（含可歸屬財產）", min_value=0, value=120_000_000, step=1_000_000, format="%,d")

        excluded = insurance_amount if insurance_excluded else 0
        net_base = max(gross_estate - excluded - e_ex - spouse - funeral - lineal, 0)

        def calc_estate(t):
            if t <= 0:
                return 0
            if t <= e_b1:
                return round(t * 0.10)
            if t <= e_b2:
                return round(t * 0.15 - 2_810_500)
            return round(t * 0.20 - 8_431_500)

        estate_tax = calc_estate(net_base)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("排除項（壽險等）", currency(excluded))
        c2.metric("扣除後課稅基礎", currency(net_base))
        c3.metric("應納遺產稅", currency(estate_tax))
        eff = (estate_tax / gross_estate) if gross_estate else 0
        c4.metric("名目稅負率（稅/遺產）", f"{eff:.2%}" if gross_estate else "—")

st.write("---")
st.caption("資料來源：MOF/NTB 公告（2025 級距、免稅額），遺贈稅法第16條第9款（指定受益人壽險給付排除）。本工具僅供教學參考。")