# app.py — 保單規劃｜用同樣現金流，更聰明完成贈與
# 執行：streamlit run app.py
# 需求：pip install streamlit pandas

import pandas as pd
import streamlit as st

st.set_page_config(page_title="保單規劃｜用同樣現金流，更聰明完成贈與", layout="wide")

# ---------------- 稅制常數（114年/2025） ----------------
EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
BR10_NET_MAX = 28_110_000  # 10% 淨額上限
BR15_NET_MAX = 56_210_000  # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

MAX_ANNUAL   = 100_000_000  # 每年現金投入上限：1 億

# ---------------- 初始化 Session State（只用 State 設定預設值；避免 value= 再指定） ----------------
DEFAULTS = {
    "years_input": 8,            # 年期（年）
    "annual_input": 10_000_000,  # 每年投入（元）
    "change_input": 1,           # 預設第 1 年變更要保人
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 年末現金價值預設比率（可依商品微調）
RATIO_MAP = {1:0.50, 2:0.70, 3:0.80, 4:0.85, 5:0.88, 6:0.91, 7:0.93, 8:0.95}

# ---------------- 樣式（含寬版容器、KPI 卡、提示） ----------------
st.markdown(
    """
<style>
:root {
  --ink:#0f172a; --sub:#475569; --line:#E6E8EF; --bg:#FAFBFD;
  --gold:#C8A96A; --gold-ink:#3f3a2a; --emerald:#059669;
}
.block-container { max-width:1320px; padding-top:1rem; padding-bottom:2rem; }
html, body, [class*="css"] { color:var(--ink); }
h1,h2,h3{ color:var(--ink)!important; letter-spacing:.3px; }
hr.custom{ border:none; border-top:1px solid var(--line); margin:12px 0 6px; }
.small{ color:var(--sub); font-size:.95rem; line-height:1.6; }

/* KPI 卡 */
.kpi{ border:1px solid var(--line); border-left:5px solid var(--gold);
  border-radius:12px; padding:14px 16px; background:#fff;
  box-shadow:0 1px 2px rgba(10,22,70,.04);}
.kpi .label{ color:var(--sub); font-size:.95rem; margin-bottom:6px;}
.kpi .value{ font-weight:700; font-variant-numeric:tabular-nums; font-size:1.05rem; }
.kpi .note{ color:var(--emerald); font-size:.9rem; margin-top:4px; }

/* 標籤與區塊 */
.tag{ display:inline-block; padding:2px 8px; border:1px solid var(--line);
  border-radius:999px; font-size:.82rem; color:var(--sub); background:#fff; margin-right:8px; }
.section{ background:var(--bg); border:1px solid var(--line); border-radius:14px; padding:16px; }

/* 頁尾聲明 */
.footer-note{
  margin-top:18px; padding:14px 16px; border:1px dashed var(--line);
  background:#fff; border-radius:12px; color:#334155; font-size:.92rem;
}
.footer-note b{ color:#111827; }
</style>
""",
    unsafe_allow_html=True
)

def card(label: str, value: str, note: str = ""):
    html = f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div>'
    if note: html += f'<div class="note">{note}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def fmt(n: float) -> str:
    return f"{n:,.0f}"

def fmt_y(n: float) -> str:
    return f"{fmt(n)} 元"

def gift_tax(net: int):
    """依累進稅率計算單年贈與稅（含基稅）。回傳 (稅額, 稅率字串)"""
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

# ---------------- 標題 ----------------
st.title("保單規劃｜用同樣現金流，更聰明完成贈與")
st.caption("單位：新台幣。稅制假設（114年/2025）：年免稅 2,440,000；10% 淨額上限 28,110,000；15% 淨額上限 56,210,000。")

# ---------------- 規劃摘要（預設展開） ----------------
with st.expander("規劃摘要", expanded=True):
    st.markdown(
        '''
- 規劃設定：要保人第一代 → 變更為第二代；被保人第二代；受益人第三代。  
- 保單規劃：於變更要保人年度，以當時**保單價值準備金**認列贈與。  
- 現金贈與：以現金達成同額移轉，逐年課稅。  
- 本試算僅比較**變更當年之前**之稅負差；變更後不再由第一代繳費。
'''
    )

# ---------------- 三個輸入（不使用 value=，只用 Session State 預設） ----------------
col1, col2, col3 = st.columns(3)
with col1:
    st.number_input(
        "年期（年）", min_value=1, max_value=40, step=1,
        key="years_input",
        help="保單繳費年期或試算年期"
    )
with col2:
    st.number_input(
        "每年投入現金（元）", min_value=0, max_value=MAX_ANNUAL, step=100_000, format="%d",
        key="annual_input",
        help="單一贈與人每年以現金投入之金額（上限 1 億）"
    )
with col3:
    st.number_input(
        "第幾年變更要保人（交棒）", min_value=1, max_value=40, step=1,
        key="change_input",
        help="在此年度以前由第一代繳費，該年度辦理要保人變更"
    )

# 讀取使用者輸入
years       = int(st.session_state.years_input)
annual      = int(st.session_state.annual_input)
change_year = int(st.session_state.change_input)

# 基本校驗與自動校正
if annual > MAX_ANNUAL:
    st.error("每年投入金額不可超過 1 億元。")
    st.stop()
if change_year > years:
    st.warning("變更年份不可晚於年期，已自動校正為年期。")
    change_year = years
    st.session_state.change_input = years  # 回寫界面

# ---------------- 依比率生成年度現金價值 ----------------
rows, cum = [], 0
for y in range(1, years + 1):
    cum += annual
    ratio = RATIO_MAP.get(y, 0.95)
    cv = int(round(cum * ratio))
    rows.append({"年度": y, "每年投入（元）": annual, "累計投入（元）": cum, "年末現金價值（元）": cv})
df_years = pd.DataFrame(rows)

# ---------------- 稅務與金額（算到第 change_year 年） ----------------
cv_at_change = int(df_years.loc[df_years["年度"] == change_year, "年末現金價值（元）"].iloc[0])

# 「名目」累積移轉金額（兩種方式一致）：至第 change_year 年的累計投入
nominal_transfer_to_N = annual * change_year

# 保單規劃（第 change_year 年變更）
gift_with_policy = cv_at_change                         # 稅務認列金額
net_with_policy  = max(0, gift_with_policy - EXEMPTION)
tax_with_policy, rate_with = gift_tax(net_with_policy)

# 現金贈與（第 1～change_year 年）
total_tax_no_policy, yearly_tax_list = 0, []
for y in range(1, change_year + 1):
    net = max(0, annual - EXEMPTION)
    t, rate = gift_tax(net)
    total_tax_no_policy += t
    yearly_tax_list.append({
        "年度": y, "現金贈與（元）": annual, "免稅後淨額（元）": net, "應納贈與稅（元）": t, "適用稅率": rate
    })

tax_saving = total_tax_no_policy - tax_with_policy

# ---------------- 兩行扼要說明 ----------------
st.markdown(
    f"""
<div class="section small">
<span class="tag">保單規劃</span>
於第 <b>{change_year}</b> 年完成要保人變更，當年度以 <b>保單價值準備金</b> 認列贈與（通常低於累計投入）。<br>
<span class="tag">現金贈與</span>
需於第 <b>1～{change_year}</b> 年逐年以 <b>現金贈與</b> 達成移轉，各年分別課稅。
</div>
""",
    unsafe_allow_html=True
)
st.markdown('<hr class="custom">', unsafe_allow_html=True)

# ---------------- 指標小卡（動態呈現“第 N 年”） ----------------
colA, colB, colC = st.columns(3)

def card_fmt_money(v): return fmt(v) + " 元"

with colA:
    st.markdown(f"**保單規劃（第 {change_year} 年變更）**")
    card(f"累積移轉（名目）至第 {change_year} 年", card_fmt_money(nominal_transfer_to_N), note="= 累計投入")
    card("變更當年視為贈與（保單價值準備金）", card_fmt_money(gift_with_policy))
    card("當年度應納贈與稅", card_fmt_money(tax_with_policy), note=f"稅率 {rate_with}")

with colB:
    st.markdown(f"**現金贈與（第 1～{change_year} 年）**")
    card(f"累積移轉（名目）至第 {change_year} 年", card_fmt_money(nominal_transfer_to_N), note="= 累計投入")
    card(f"累計贈與稅（至第 {change_year} 年）", card_fmt_money(total_tax_no_policy))

with colC:
    st.markdown("**稅負差異**")
    card(f"至第 {change_year} 年節省之贈與稅", card_fmt_money(tax_saving))

# ---------------- 明細（預設收合；索引隱藏） ----------------
st.write("")  # 空行
with st.expander("年度明細與逐年稅額（專家檢視）", expanded=False):
    st.markdown("**年度現金價值（依預設比率推估）**")
    st.dataframe(
        df_years.assign(
            **{
                "每年投入（元）": lambda d: d["每年投入（元）"].map(fmt),
                "累計投入（元）": lambda d: d["累計投入（元）"].map(fmt),
                "年末現金價值（元）": lambda d: d["年末現金價值（元）"].map(fmt),
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("**現金贈與：逐年稅額**")
    df_no = pd.DataFrame(yearly_tax_list)
    show_no = df_no.copy()
    for c in ["現金贈與（元）", "免稅後淨額（元）", "應納贈與稅（元）"]:
        show_no[c] = show_no[c].map(lambda x: fmt(x) + " 元")
    st.dataframe(
        show_no,
        use_container_width=True,
        hide_index=True,
    )

st.markdown('<hr class="custom">', unsafe_allow_html=True)

# ---------------- 規劃效果 ----------------
st.subheader("規劃效果")
st.markdown(
    f"""
**① 現金流不變，家族保障更具規模**  
- 現金贈與：每投入 **1 元**僅能**等值移轉 1 元**，缺乏保障槓桿，且給付時點與資金到位**不具確定性**（需視資產流動性與市場狀況）。  
- 保單規劃：每投入 **1 元**可在約定事件或時點**轉化為超過 1 元的保額**（依商品試算與核保而定），形成**保障槓桿**；並可**指定受益人**，達到**定向傳承**。  

**② 資金到位的確定性**  
- 保險給付不受市場波動與資產流動性影響，可避免於壓力時點折價出售股權或不動產，形同建立**流動性防火牆**。  

**③ 治理與控管**  
- 以您設定的交棒節點（第 {change_year} 年）變更要保人，受益人與比例得事前規劃；可搭配保險信託以分期撥付、抑制外界干擾。  
- 透過**保單贈與（含變更要保人）**可維持**帳戶獨立**並降低與銀行往來帳戶的混同風險；亦有助於**婚姻財富治理**，明確標示用途（如教育金、長照金）。  

**④ 稅務效率**  
- 保單規劃：僅於第 {change_year} 年就「**保單價值準備金**」計贈與稅（多數情況低於累計投入），稅負效率通常更佳。  
- 現金贈與：需於第 1～{change_year} 年逐年就現金贈與課稅；上方指標已呈現兩者差異。
"""
)

# ---------------- 重要提醒（頁面最下方） ----------------
st.markdown(
    """
<div class="footer-note">
<b>重要提醒：</b>本頁內容僅為示範與教育性說明參考，實際權利義務以<strong>保單條款</strong>、保險公司<strong>核保／保全規定</strong>、
以及您與專業顧問完成之<strong>個別化規劃文件</strong>為準。稅制數值採目前假設，若法規調整，請以最新公告為準。
</div>
""",
    unsafe_allow_html=True
)
