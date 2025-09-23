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

# ---------------- 初始化 Session State ----------------
DEFAULTS = {
    "change_year": 1,           # 第幾年變更要保人（交棒）— 1~6

    # 年繳保費（= 每年保費）
    "y1_prem": 10_000_000,      # 預設 1,000 萬
    "y2_prem": 10_000_000,      # 仍維持內部等於第 1 年
    "y3_prem": 10_000_000,

    # 前三年年末現金價值（預設）
    "y1_cv":   5_000_000,
    "y2_cv":  14_000_000,
    "y3_cv":  24_000_000,

    # 供延伸年度推估使用（仍保留，不變）
    "ratio_map": None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 年末現金價值預設比率（可依商品微調；延伸到第 10 年）— 保留原行為
DEFAULT_RATIO_MAP = {1:0.50, 2:0.70, 3:0.80, 4:0.85, 5:0.88, 6:0.91, 7:0.93, 8:0.95, 9:0.97, 10:0.98}

# ---------------- 樣式（保留不變） ----------------
st.markdown(
    """
<style>
:root { --ink:#0f172a; --sub:#475569; --line:#E6E8EF; --bg:#FAFBFD; --gold:#C8A96A; --emerald:#059669; }
.block-container { max-width:1320px; padding-top:1rem; padding-bottom:2rem; }
hr.custom{ border:none; border-top:1px solid var(--line); margin:12px 0 6px; }
.small{ color:var(--sub); font-size:.95rem; line-height:1.6; }
.kpi{ border:1px solid var(--line); border-left:5px solid var(--gold); border-radius:12px; padding:14px 16px; background:#fff; box-shadow:0 1px 2px rgba(10,22,70,.04);}
.kpi .label{ color:var(--sub); font-size:.95rem; margin-bottom:6px;}
.kpi .value{ font-weight:700; font-variant-numeric:tabular-nums; font-size:1.05rem; }
.kpi .note{ color:var(--emerald); font-size:.9rem; margin-top:4px; }
.section{ background:var(--bg); border:1px solid var(--line); border-radius:14px; padding:16px; }
.footer-note{ margin-top:18px; padding:14px 16px; border:1px dashed var(--line); background:#fff; border-radius:12px; color:#334155; font-size:.92rem; }
.note-inline{ color:#64748b; font-size:.9rem; margin-left:.5rem; }
.badge{ display:inline-block; padding:2px 8px; border:1px solid var(--line); border-radius:999px; font-size:.78rem; color:#0f172a; background:#fff;}
</style>
""",
    unsafe_allow_html=True
)

def card(label: str, value: str, note: str = ""):
    html = f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div>'
    if note: html += f'<div class="note">{note}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def fmt(n: float) -> str: return f"{n:,.0f}"
def fmt_y(n: float) -> str: return f"{fmt(n)} 元"

def tax_calc(net:int):
    """累進稅率計算；回傳(應納稅額, 適用稅率字串)"""
    if net <= 0: return 0, "—"
    if net <= BR10_NET_MAX: return int(round(net * RATE_10)), "10%"
    if net <= BR15_NET_MAX:
        base = BR10_NET_MAX * RATE_10
        extra = (net - BR10_NET_MAX) * RATE_15
        return int(round(base + extra)), "15%"
    base = BR10_NET_MAX * RATE_10 + (BR15_NET_MAX - BR10_NET_MAX) * RATE_15
    extra = (net - BR15_NET_MAX) * RATE_20
    return int(round(base + extra)), "20%"

# --- 行為：改第 1 年保費時（年繳保費）— 依你的新規則：清空前三年保價金 ---
def _sync_from_y1():
    p = int(st.session_state.y1_prem)
    st.session_state.y2_prem = p
    st.session_state.y3_prem = p
    # 清空：改由用戶自行輸入保價
    st.session_state.y1_cv = 0
    st.session_state.y2_cv = 0
    st.session_state.y3_cv = 0

# ---------------- 標題與摘要（保留不變） ----------------
st.title("保單規劃｜用同樣現金流，更聰明完成贈與")
st.caption("單位：新台幣。稅制假設（114年/2025）：年免稅 2,440,000；10% 淨額上限 28,110,000；15% 淨額上限 56,210,000。")

with st.expander("規劃摘要", expanded=True):
    st.markdown(
        """
- 規劃設定：要保人第一代 → 變更為第二代；被保人第二代；受益人第三代。  
- 保單規劃：於變更要保人年度，以當時**保單價值準備金**認列贈與。  
- 現金贈與：以現金達成同額移轉，逐年課稅。  
- 本試算僅比較**變更當年之前**之稅負差；變更後不再由第一代繳費。
        """
    )

# ----------------（只改這段）輸入欄位：年繳保費、變更年、前三年保價金 ----------------
row_top = st.columns([3, 1, 1])
with row_top[0]:
    st.number_input(
        "第幾年變更要保人（交棒）",
        min_value=1, max_value=6, step=1, key="change_year",
        help="預設第 1 年，最多第 6 年。"
    )
with row_top[1]:
    col_minus, col_plus = st.columns(2)
    with col_minus:
        if st.button("◀ 年 -1", use_container_width=True):
            st.session_state.change_year = max(1, int(st.session_state.change_year) - 1)
    with col_plus:
        if st.button("年 +1 ▶", use_container_width=True):
            st.session_state.change_year = min(6, int(st.session_state.change_year) + 1)
with row_top[2]:
    st.markdown('<span class="badge">示範工具</span>', unsafe_allow_html=True)

st.markdown('<hr class="custom">', unsafe_allow_html=True)

# 年繳保費（改動即清空 1~3 年保價金）
st.number_input(
    "年繳保費（元）",
    min_value=0, max_value=MAX_ANNUAL,
    step=100_000, format="%d",
    key="y1_prem", on_change=_sync_from_y1,
    help="預設 10,000,000（1,000 萬）。如改動，系統會把第 1～3 年保價金清空為 0，請自行輸入。"
)

# 根據年繳保費動態限制各年保價金上限：1x/2x/3x
p = int(st.session_state.y1_prem)
max_y1 = p * 1
max_y2 = p * 2
max_y3 = p * 3

st.subheader("前三年保價金（年末現金價值）")
c1, c2, c3 = st.columns(3)
with c1:
    st.number_input("第 1 年保價金（元）", min_value=0, max_value=max_y1, step=100_000, format="%d", key="y1_cv")
with c2:
    st.number_input("第 2 年保價金（元）", min_value=0, max_value=max_y2, step=100_000, format="%d", key="y2_cv")
with c3:
    st.number_input("第 3 年保價金（元）", min_value=0, max_value=max_y3, step=100_000, format="%d", key="y3_cv")

# （保留原本行為）寫回鎖定的保費值（顯示用 display 欄位已移除，但內部仍同步）
st.session_state.y2_prem = st.session_state.y1_prem
st.session_state.y3_prem = st.session_state.y1_prem

# ---------------- 年期推導（保留原則：至少8年、至多10年） ----------------
change_year = int(st.session_state.change_year)
years = min(10, max(8, change_year))

# ---------------- 生成年度序列（每年保費 = 年繳保費）— 保留不變 ----------------
def build_schedule(years_total: int):
    rows, cum = [], 0
    p1 = int(st.session_state.y1_prem)
    ratio_map = st.session_state.ratio_map or DEFAULT_RATIO_MAP
    for y in range(1, years_total+1):
        premium = p1
        cum += premium
        if y == 1:
            cv = int(st.session_state.y1_cv)
        elif y == 2:
            cv = int(st.session_state.y2_cv)
        elif y == 3:
            cv = int(st.session_state.y3_cv)
        else:
            ratio = ratio_map.get(y, ratio_map.get(max(ratio_map.keys()), 0.98))
            cv = int(round(cum * ratio))
        rows.append({"年度": y, "每年投入（元）": premium, "累計投入（元）": cum, "年末現金價值（元）": cv})
    return pd.DataFrame(rows)

df_years = build_schedule(years)

# ---------------- 稅務與金額（至第 change_year 年）— 保留不變 ----------------
cv_at_change = int(df_years.loc[df_years["年度"] == change_year, "年末現金價值（元）"].iloc[0])
nominal_transfer_to_N = int(df_years.loc[df_years["年度"] <= change_year, "每年投入（元）"].sum())

gift_with_policy = cv_at_change
net_with_policy  = max(0, gift_with_policy - EXEMPTION)
tax_with_policy, rate_with = tax_calc(net_with_policy)

total_tax_no_policy, yearly_tax_list = 0, []
for _, r in df_years[df_years["年度"] <= change_year].iterrows():
    annual_i = int(r["每年投入（元）"])
    net = max(0, annual_i - EXEMPTION)
    t, rate = tax_calc(net)
    total_tax_no_policy += t
    yearly_tax_list.append({
        "年度": int(r["年度"]),
        "現金贈與（元）": annual_i,
        "免稅後淨額（元）": net,
        "應納贈與稅（元）": t,
        "適用稅率": rate
    })

tax_saving = total_tax_no_policy - tax_with_policy
display_saving = tax_saving
saving_label = "節省之贈與稅" if tax_saving >= 0 else "增加之贈與稅"

# ---------------- 警示/提醒（僅微調條件：不再檢查 clear_cv_mode） ----------------
if cv_at_change == 0 and change_year <= 3:
    st.info("建議輸入第 1～3 年的『年末現金價值』以符合商品試算書，避免保單方案的稅負被低估。")

# ---------------- 指標卡（保留不變） ----------------
st.markdown('<hr class="custom">', unsafe_allow_html=True)
colA, colB, colC = st.columns(3)
with colA:
    st.markdown(f"**保單規劃（第 {change_year} 年變更）**")
    card(f"累積移轉（名目）至第 {change_year} 年", fmt_y(nominal_transfer_to_N), note="= 實際投入總和")
    card("變更當年視為贈與（保單價值準備金）", fmt_y(gift_with_policy),
         note="以保單價值準備金認列，非名目投入總和")
    card("當年度應納贈與稅", fmt_y(tax_with_policy), note=f"稅率 {rate_with}")
with colB:
    st.markdown(f"**現金贈與（第 1～{change_year} 年）**")
    card(f"累積移轉（名目）至第 {change_year} 年", fmt_y(nominal_transfer_to_N), note="= 實際投入總和")
    card(f"累計贈與稅（至第 {change_year} 年）", fmt_y(total_tax_no_policy))
with colC:
    st.markdown("**稅負差異**")
    card(f"至第 {change_year} 年{saving_label}", fmt_y(abs(display_saving)))

# ---------------- 明細（保留不變） ----------------
with st.expander("年度明細與逐年稅額（專家檢視）", expanded=False):
    st.markdown("**年度現金價值（前三年可覆寫；其後依比率推估）**")
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
    st.markdown("**現金贈與：逐年稅額（第 1～變更年）**")
    df_no = pd.DataFrame(sorted(yearly_tax_list, key=lambda x: x["年度"]))
    show_no = df_no.copy()
    for c in ["現金贈與（元）", "免稅後淨額（元）", "應納贈與稅（元）"]:
        show_no[c] = show_no[c].map(fmt_y)
    st.dataframe(show_no, use_container_width=True, hide_index=True)

# ---------------- 顧問話術（保留不變） ----------------
with st.expander("一鍵生成｜顧問講解話術（複製貼上）", expanded=False):
    lines = [
        f"以同樣的現金流，若在第 {change_year} 年變更要保人，當年度以保單價值準備金認列贈與 {fmt_y(gift_with_policy)}。",
        f"若改以現金逐年贈與至第 {change_year} 年，累計贈與稅約 {fmt_y(total_tax_no_policy)}；採保單規劃同年度稅額約 {fmt_y(tax_with_policy)}。",
        f"因此至第 {change_year} 年「{saving_label.replace('之贈與稅','')}」約 {fmt_y(abs(display_saving))}，同時保單可作為未來稅源與分配工具。"
    ]
    st.write("\n\n".join(f"• {t}" for t in lines))
    st.caption("＊以上內容為示範講稿，請依個案條款、核保／保全規定調整。")

# ---------------- 贈與完成後：可達成之效果（保留不變） ----------------
st.subheader("贈與完成後：可達成之效果")
st.markdown(
    f"""
**保單規劃**

1️⃣ **降低應稅資產**  
透過保單設計，可有效降低第一代應稅資產 **{fmt_y(gift_with_policy)}**（以第 {change_year} 年保單價值準備金為準），達到節稅效果。

2️⃣ **壓縮一代資產**  
透過變更要保人方式，靈活規劃資產歸屬，避免資產過度集中在一代名下。

3️⃣ **預留二代稅源**  
保單身故保險金可作為稅源預備金，避免後代因繳稅問題被迫處分資產。

4️⃣ **資產放大效果**  
存在銀行，一塊錢就是一塊錢；但放進保單，可透過身價保障產生倍數效果。  
（至第 {change_year} 年名目累積投入 **{fmt_y(nominal_transfer_to_N)}**，同年認列贈與 **{fmt_y(gift_with_policy)}**。）

5️⃣ **資產公平調控**  
銀行存款依民法須平均分配，但保單受益人可彈性規劃，對資產差異較大的子女，能做差額補強。

6️⃣ **指定受益分配**  
保單具備指定受益人的彈性，能精準落實傳承意圖。

7️⃣ **遺產外快現金**  
保險金屬於遺產外的即時現金，繼承人可快速取得，緩解資金需求。

8️⃣ **分期給付的靈活性**  
保單可透過類信託的方式進行分期給付，不僅能保障資產分配的秩序，還能避免額外的信託管理費用，更具成本效益。

— 另外：以現金逐年贈與至第 {change_year} 年，累計贈與稅約 **{fmt_y(total_tax_no_policy)}**；採保單規劃同年度稅額約 **{fmt_y(tax_with_policy)}**，**{saving_label}**約 **{fmt_y(abs(display_saving))}**。
"""
)

# ---------------- 重要提醒（保留不變） ----------------
st.markdown(
    """
<div class="footer-note">
<b>重要提醒：</b>本頁內容僅為示範與教育性說明參考，實際權利義務以<strong>保單條款</strong>、
保險公司<strong>核保／保全規定</strong>與<strong>個別化規劃文件</strong>為準。稅制數值採目前假設，
若法規調整，請以最新公告為準。
</div>
""",
    unsafe_allow_html=True
)
