# app.py — 保單規劃｜用同樣現金流，更聰明完成贈與（簡易模式｜高資產語氣＋高雅配色）
# 執行：streamlit run app.py
# 需求：pip install streamlit pandas

import pandas as pd
import streamlit as st

st.set_page_config(page_title="保單規劃｜用同樣現金流，更聰明完成贈與", layout="centered")

# ---------------- 稅制常數（114年/2025） ----------------
EXEMPTION    = 2_440_000   # 年免稅額（單一贈與人）
BR10_NET_MAX = 28_110_000  # 10% 淨額上限
BR15_NET_MAX = 56_210_000  # 15% 淨額上限
RATE_10, RATE_15, RATE_20 = 0.10, 0.15, 0.20

MAX_ANNUAL   = 100_000_000  # 每年現金投入上限：1 億

# ---------------- 初始化 Session State ----------------
DEFAULTS = {"years": 8, "annual_cash": 10_000_000, "change_year": 2}  # 預設 1,000 萬
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 預設比率（示意）：Y1=50%、Y2=70%、Y3=80%、Y4=85%、Y5=88%、Y6=91%、Y7=93%、Y8=95%，>8 年維持 95%
RATIO_MAP = {1:0.50, 2:0.70, 3:0.80, 4:0.85, 5:0.88, 6:0.91, 7:0.93, 8:0.95}

# ---------------- 低調高雅的樣式 ----------------
st.markdown(
    '''
<style>
:root {
  --ink:#0f172a;         /* 海軍藍（標題/強調字） */
  --sub:#475569;         /* 次要文字 */
  --line:#E6E8EF;        /* 分隔線 */
  --bg:#FAFBFD;          /* 淺底 */
  --gold:#C8A96A;        /* 香檳金重點色 */
  --emerald:#059669;     /* 穩健綠（提示） */
}
html, body, [class*="css"]  { color: var(--ink); }
h1, h2, h3 { color: var(--ink) !important; letter-spacing: .3px; }
hr.custom { border:none; border-top:1px solid var(--line); margin: 12px 0 6px 0; }
.small { color: var(--sub); font-size:0.95rem; line-height:1.6; }
.kpi {
  border:1px solid var(--line);
  border-left:5px solid var(--gold);
  border-radius:12px;
  padding:14px 16px;
  background:#fff;
  box-shadow:0 1px 2px rgba(10,22,70,.04);
}
.kpi .label { color:var(--sub); font-size:0.95rem; margin-bottom:6px; }
.kpi .value { font-weight:700; font-variant-numeric:tabular-nums; font-size:1.05rem; line-height:1.3; }
.kpi .note { color:var(--emerald); font-size:0.9rem; margin-top:4px; }
.tag {
  display:inline-block; padding:2px 8px; border:1px solid var(--line);
  border-radius:999px; font-size:0.82rem; color:var(--sub); background:#fff; margin-right:8px;
}
.section { background:var(--bg); border:1px solid var(--line); border-radius:14px; padding:16px; }
</style>
''',
    unsafe_allow_html=True
)

def card(label: str, value: str, note: str = ""):
    html = (
        f'<div class="kpi"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
    )
    if note:
        html += f'<div class="note">{note}</div>'
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

# ---------------- 標題、稅制、決策摘要 ----------------
st.title("保單規劃｜用同樣現金流，更聰明完成贈與")
st.caption("單位：新台幣。稅制假設（114年/2025）：年免稅 2,440,000；10% 淨額上限 28,110,000；15% 淨額上限 56,210,000。")

# 先讀取目前變更年份（供摘要動態帶入）
change_preview = st.session_state["change_year"]

st.markdown(
    f"""
<div class="small">
<b>決策摘要：</b><br>
• 同額現金流，於第 <b>{change_preview}</b> 年以<b>現金價值</b>認列贈與，通常低於累計投入，<b>稅務更有效率</b>。<br>
• <b>保單規劃</b>可在需要時把 <b>1 元保費 → ＞1 元保額</b>（依試算/核保），並可<b>指定受益人</b>，定向傳承。<br>
• <b>現金贈與</b>需自第 <b>1～{change_preview}</b> 年逐年課稅；下方指標已呈現差異。
</div>
""",
    unsafe_allow_html=True
)
st.markdown('<hr class="custom">', unsafe_allow_html=True)

with st.expander("計算邏輯（供參）", expanded=False):
    st.markdown(
        f'''
- 規劃設定：要保人第一代 →（第 **{change_preview} 年**變更）→ 第二代；被保人第二代；受益人第三代。  
- **保單規劃**：於第 **{change_preview} 年**變更要保人，以當時**現金價值（保價金/解約金）**認列贈與。  
- **現金贈與**：以現金達成同額移轉，需在第 **1～{change_preview} 年**逐年課稅。  
- 本試算僅比較**變更當年之前**之稅負差；變更後不再由第一代繳費。
'''
    )

# ---------------- 一鍵情境（callback 設定 state） ----------------
def apply_preset(y: int, a: int, c: int):
    st.session_state.update({"years": y, "annual_cash": a, "change_year": c})

c1, c2 = st.columns(2)
with c1:
    st.button("一鍵示範：1,000 萬 × 8 年｜第 2 年變更", on_click=apply_preset, args=(8, 10_000_000, 2))
with c2:
    st.button("一鍵示範：1,000 萬 × 8 年｜第 1 年變更", on_click=apply_preset, args=(8, 10_000_000, 1))

# ---------------- 三個輸入（以 state 為預設值） ----------------
col1, col2, col3 = st.columns(3)
with col1:
    years = st.number_input("年期（年）", min_value=1, max_value=40,
                            value=st.session_state.years, step=1, key="years_input")
with col2:
    annual = st.number_input("每年投入現金（元）", min_value=0, max_value=MAX_ANNUAL,
                             value=st.session_state.annual_cash, step=100_000, format="%d", key="annual_input")
with col3:
    change_year = st.number_input("第幾年變更要保人（交棒）", min_value=1, max_value=40,
                                  value=st.session_state.change_year, step=1, key="change_input")

# 回存 state 與基礎校驗
st.session_state.years = int(years)
st.session_state.annual_cash = int(annual)
st.session_state.change_year = int(change_year)

if st.session_state.annual_cash > MAX_ANNUAL:
    st.error("每年投入金額不可超過 1 億元。")
    st.stop()
if st.session_state.change_year > st.session_state.years:
    st.warning("變更年份不可晚於年期，已自動校正為年期。")
    st.session_state.change_year = st.session_state.years

years       = st.session_state.years
annual      = st.session_state.annual_cash
change_year = st.session_state.change_year

# ---------------- 依比率生成年度現金價值 ----------------
rows, cum = [], 0
for y in range(1, years + 1):
    cum += annual
    ratio = RATIO_MAP.get(y, 0.95)
    cv = int(round(cum * ratio))
    rows.append({"年度": y, "每年投入（元）": annual, "累計投入（元）": cum, "年末現金價值（元）": cv})
df_years = pd.DataFrame(rows)

# ---------------- 稅務比較至「第 change_year 年」 ----------------
cv_at_change = int(df_years.loc[df_years["年度"] == change_year, "年末現金價值（元）"].iloc[0])

# 保單規劃：第 change_year 年視為贈與 = 現金價值
gift_with_policy   = cv_at_change
net_with_policy    = max(0, gift_with_policy - EXEMPTION)
tax_with_policy, rate_with = gift_tax(net_with_policy)

# 現金贈與：第 1～change_year 年逐年現金贈與（對照口徑）
total_tax_no_policy = 0
yearly_tax_list = []
for y in range(1, change_year + 1):
    net = max(0, annual - EXEMPTION)
    t, rate = gift_tax(net)
    total_tax_no_policy += t
    yearly_tax_list.append({
        "年度": y, "現金贈與（元）": annual, "免稅後淨額（元）": net, "應納贈與稅（元）": t, "適用稅率": rate
    })

tax_saving = total_tax_no_policy - tax_with_policy

# ---------------- 兩行扼要說明（以具體年份呈現） ----------------
st.markdown(
    f'''
<div class="section small">
<span class="tag">保單規劃</span>
第 <b>{change_year}</b> 年變更要保人，當年度以 <b>現金價值</b> 認列贈與（通常低於累計投入）。<br>
<span class="tag">現金贈與</span>
需自第 <b>1～{change_year}</b> 年逐年移轉，各年分別課稅。
</div>
''',
    unsafe_allow_html=True
)
st.markdown('<hr class="custom">', unsafe_allow_html=True)

# ---------------- 關鍵指標小卡 ----------------
colA, colB, colC = st.columns(3)
with colA:
    st.markdown("**保單規劃（第 {} 年變更）**".format(change_year))
    card("變更當年視為贈與（現金價值）", fmt_y(gift_with_policy))
    card("當年度應納贈與稅", fmt_y(tax_with_policy), note=f"稅率 {rate_with}")
with colB:
    st.markdown("**現金贈與（第 1～{} 年）**".format(change_year))
    card("累計贈與稅（至第 {} 年）".format(change_year), fmt_y(total_tax_no_policy))
with colC:
    st.markdown("**稅負差異**")
    card("至第 {} 年節省之贈與稅".format(change_year), fmt_y(tax_saving),
         note="同額現金流條件下的差異，未含商品紅利/保額等效應")

# ---------------- 空行（你指定的）＋ 明細（預設收合） ----------------
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
    )
    st.markdown("**現金贈與：逐年稅額**")
    df_no = pd.DataFrame(yearly_tax_list)
    show_no = df_no.copy()
    for c in ["現金贈與（元）", "免稅後淨額（元）", "應納贈與稅（元）"]:
        show_no[c] = show_no[c].map(fmt_y)
    st.dataframe(show_no, use_container_width=True)

st.markdown('<hr class="custom">', unsafe_allow_html=True)

# ---------------- 名詞小辭典（一句話看懂） ----------------
with st.expander("名詞小辭典（一句話看懂）", expanded=False):
    st.markdown(
        """
- **現金價值**：保單年末可解約領回的金額（示意比率已於上文表格說明）。  
- **定向傳承**：可事先指定受益人與比例，資金直達指定對象。  
- **帳戶獨立**：與一般銀行往來分開，降低資金混同與糾紛風險。  
- **流動性防火牆**：避免在不利時點賣資產，必要時仍有現金可用。  
        """
    )

# ---------------- 規劃效果（已白話 10%，維持專業口吻） ----------------
st.subheader("規劃效果")
st.markdown(
    f"""
**① 同額現金，效益更大**  
- <b>現金贈與：</b>每投入 1 元僅等值移轉 1 元，缺乏保障槓桿；給付時點與資金到位受市場/流動性影響。  
- <b>保單規劃：</b>每 1 元保費可在約定事件/時點轉化為<b>超過 1 元的保額</b>（依試算與核保），並可<b>指定受益人</b>，達到<b>定向傳承</b>。

**② 關鍵時間點，現金確定到位**  
- 保險給付不受市場波動影響；必要時點現金即時到位，降低在壓力情境下折價處分資產的機率。  

**③ 秩序與治理**  
- 於第 <b>{change_year}</b> 年完成要保人變更，交棒節奏明確；受益人與比例可事前設計（必要時搭配保險信託）以分層/分期撥付。  
- 透過<b>帳戶獨立</b>與用途標示，降低與一般銀行往來帳戶的混同風險；亦有助於婚姻財富治理。  

**④ 稅務效率**  
- <b>保單規劃：</b>僅就第 <b>{change_year}</b> 年的<b>現金價值</b>計贈與稅，多數情況較逐年現金贈與更有效率。  
- <b>現金贈與：</b>第 1～{change_year} 年逐年課稅；差異如上方指標所示。
"""
)

st.caption("註：年末現金價值與最終保額仍以保險公司試算書為準；本工具著重稅務邏輯與資金路徑之展示。")
