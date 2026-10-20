# -*- coding: utf-8 -*-
"""Tema visual dashboard (mengikuti mockup): sidebar navy BIN, kartu KPI pastel, panel putih."""
import base64
import os

import streamlit as st

_FALLBACK_EMBLEM = ("https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/"
                    "Lambang_Badan_Intelijen_Negara.svg/120px-Lambang_Badan_Intelijen_Negara.svg.png")


def _embed_image(filename, mime):
    """Embed gambar lokal sebagai data URI; aman saat offline / tanpa akses ke internet."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", filename)
    try:
        with open(path, "rb") as f:
            return f"data:{mime};base64," + base64.b64encode(f.read()).decode("ascii")
    except FileNotFoundError:
        return None


EMBLEM = _embed_image("bin_logo.png", "image/png") or _FALLBACK_EMBLEM

TIPE_COLOR = {
    "Karhutla": "#f97316",
    "Banjir": "#2563eb",
    "Gempa": "#16a34a",
    "Bencana Alam Lainnya": "#8b5cf6",
}
TIPE_ICON = {"Karhutla": "🔥", "Banjir": "🌊", "Gempa": "🌋", "Bencana Alam Lainnya": "🌪️"}

HOTSPOT_BUCKET_COLOR = {
    "> 50 hotspot": "#dc2626",
    "21 – 50 hotspot": "#f97316",
    "6 – 20 hotspot": "#facc15",
    "1 – 5 hotspot": "#10b981",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root{
  --navy:#0b1f4d; --navy2:#12307a; --blue:#1d4ed8; --ink:#0f2a5c; --muted:#5b6f94;
  --line:#dbe6f6; --bg:#f3f7fd;
}
.stApp{ background: linear-gradient(180deg,#eaf1fc 0%, #f6f9fe 40%, #ffffff 100%); }
.stApp, .stApp p, .stApp li, .stApp label, .stApp button, .stApp input, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.hero *, .kpi *, .ptitle, .nav-brand *, .navuser *, .toptable *, .legend-row *, .note *{
  font-family:'Plus Jakarta Sans','Segoe UI',system-ui,sans-serif;
}
.block-container{ padding: 1.2rem 1.6rem 2rem 1.6rem; max-width: 1700px; }
header[data-testid="stHeader"]{ background: transparent; }

/* ------------------------------------------------ sidebar */
section[data-testid="stSidebar"]{
  background: linear-gradient(180deg, var(--navy) 0%, var(--navy2) 100%);
  border-right: 0;
}
section[data-testid="stSidebar"] > div{ padding-top: .6rem; }
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] div{ color:#eaf1ff; }
.nav-brand{ display:flex; gap:12px; align-items:center; padding:6px 4px 14px 4px;
  border-bottom:1px solid rgba(255,255,255,.18); margin-bottom:14px; }
.nav-brand img{ width:58px; height:58px; }
.nav-brand .b1{ font-weight:800; font-size:13.5px; line-height:1.25; color:#fff; }
.nav-brand .b2{ font-size:11.5px; letter-spacing:.6px; color:#b9cdf5; }
.nav-dir{ padding:2px 4px 14px 4px; color:#fff; }
.nav-dir .d1{ font-weight:800; font-size:15px; }
.nav-dir .d2{ font-size:13px; color:#cfe0ff; line-height:1.4; }

/* menu navigasi (st.radio) tampil seperti tombol menu */
section[data-testid="stSidebar"] div[role="radiogroup"]{ gap:6px; }
section[data-testid="stSidebar"] div[role="radiogroup"] label{
  width:100%; padding:11px 14px; border-radius:10px; cursor:pointer; margin:0;
  transition: background .15s ease;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover{ background: rgba(255,255,255,.10); }
section[data-testid="stSidebar"] div[role="radiogroup"] label > div > div:first-child{ display:none; }
section[data-testid="stSidebar"] div[role="radiogroup"] label > div{ gap:0; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){
  background: #2563eb; box-shadow: 0 4px 14px rgba(37,99,235,.45);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label p{ font-size:14.5px; font-weight:600; color:#fff; }
.navuser{ margin-top:14px; padding:12px 14px; border-radius:12px; background: rgba(255,255,255,.08);
  border:1px solid rgba(255,255,255,.14); }
.navuser .u1{ font-weight:700; font-size:14px; color:#fff; }
.navuser .u2{ font-size:12px; color:#b9cdf5; }
.navtag{ margin-top:26px; padding:0 6px; font-style:italic; font-weight:700; color:#d8e5ff;
  font-size:16px; line-height:1.35; transform: rotate(-4deg); transform-origin:left; }
section[data-testid="stSidebar"] .stButton > button{
  width:100%; background: rgba(255,255,255,.10); color:#fff; border:1px solid rgba(255,255,255,.25);
  border-radius:10px; font-weight:600; }
section[data-testid="stSidebar"] .stButton > button:hover{ background: rgba(255,255,255,.2); border-color:#fff; }

/* ------------------------------------------------ hero */
.hero{ display:flex; align-items:center; justify-content:space-between; gap:22px; flex-wrap:wrap;
  padding:8px 4px 14px 4px; }
.hero-l{ display:flex; align-items:center; gap:16px; }
.hero-shield{ width:62px; height:62px; border-radius:16px; display:flex; align-items:center; justify-content:center;
  font-size:30px; background: linear-gradient(135deg,#1d4ed8,#3b82f6); box-shadow:0 8px 20px rgba(29,78,216,.35); }
.hero-t{ font-weight:800; font-size:34px; line-height:1.05; color:var(--ink); letter-spacing:-.5px; }
.hero-s{ font-weight:600; font-size:17px; color:#1c3d82; margin-top:4px; }
.hero-w{ font-size:14.5px; color:var(--muted); margin-top:2px; }
.hero-m{ padding:6px 16px; border-left:1px solid var(--line); color:var(--muted); font-size:13px; line-height:1.5; }
.hero-m b{ color:var(--ink); font-size:15px; }
.hero-r{ display:flex; align-items:center; gap:12px; }
.hero-r img{ width:52px; }
.hero-bin{ font-weight:800; font-size:30px; color:#12307a; letter-spacing:1px; padding-right:12px;
  border-right:2px solid var(--line); }
.hero-dir{ font-size:13px; color:var(--muted); line-height:1.3; }
.hero-dir b{ color:#12307a; font-size:16px; }

/* ------------------------------------------------ panel (st.container border) */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background:#fff; border:1px solid var(--line) !important; border-radius:16px !important;
  box-shadow: 0 4px 18px rgba(18,48,122,.06);
}
.ptitle{ font-weight:700; font-size:18px; color:var(--ink); margin-bottom:2px; }
.ptitle span{ font-weight:500; color:var(--muted); font-size:15px; }
.psub{ color:var(--muted); font-size:13px; margin-bottom:8px; }

/* ------------------------------------------------ KPI */
.kpi{ display:flex; gap:14px; align-items:center; padding:16px 18px; border-radius:16px;
  border:1px solid; box-shadow: 0 4px 16px rgba(18,48,122,.05); height:100%; overflow:hidden; }
.kpi > div:nth-child(2){ min-width:0; flex:1; }
.kpi-ic{ width:52px; height:52px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:24px; flex:0 0 52px; }
.kpi-lb{ font-weight:600; font-size:14px; color:#1c3d82; margin-bottom:2px; line-height:1.25; }
.kpi-v{ font-weight:800; font-size:clamp(22px, 2.1vw, 32px); line-height:1.1; color:var(--ink);
  letter-spacing:-.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.kpi-v small{ font-size:.55em; font-weight:700; letter-spacing:0; margin-left:4px; color:#1c3d82; }
.kpi-d{ font-size:12px; color:var(--muted); margin-top:3px; line-height:1.35; }
.kpi-d b.up{ color:#dc2626; } .kpi-d b.down{ color:#16a34a; } .kpi-d b.flat{ color:var(--muted); }
.kpi-blue{ background:#eaf2ff; border-color:#cfe0fb; } .kpi-blue .kpi-ic{ background:#2563eb; }
.kpi-teal{ background:#e6f7f4; border-color:#c4ece5; } .kpi-teal .kpi-ic{ background:#0d9488; }
.kpi-orange{ background:#fff1e6; border-color:#fbd9bd; } .kpi-orange .kpi-ic{ background:#f97316; }
.kpi-purple{ background:#f1ebff; border-color:#ddd0fa; } .kpi-purple .kpi-ic{ background:#8b5cf6; }
.kpi-rose{ background:#ffecef; border-color:#fcccd4; } .kpi-rose .kpi-ic{ background:#e11d48; }
.kpi-amber{ background:#fff6dd; border-color:#fde9a9; } .kpi-amber .kpi-ic{ background:#d97706; }
.kpi-slate{ background:#eef2f8; border-color:#d4def0; } .kpi-slate .kpi-ic{ background:#475569; }

/* ------------------------------------------------ tabel top 5 / legenda */
.toptable{ width:100%; border-collapse:collapse; font-size:12.5px; table-layout:auto; }
.toptable td, .toptable th{ white-space:nowrap; }
.subhead{ font-weight:700; font-size:13.5px; color:var(--ink); margin:2px 0 8px 0; line-height:1.3; }
.toptable th{ text-align:left; color:var(--muted); font-weight:600; padding:6px 5px; border-bottom:1px solid var(--line);
  font-size:12.5px; }
.toptable td{ padding:9px 5px; border-bottom:1px solid #eef3fb; color:var(--ink); }
.toptable td.num{ text-align:right; font-weight:700; color:#dc2626; } .toptable th.num{ text-align:right; }
.legend-row{ display:flex; flex-wrap:wrap; gap:6px 16px; font-size:12.5px; color:var(--muted); margin-top:4px; }
.dot{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; }
.tipe-row{ display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:1px solid #eef3fb; font-size:13.5px;
  color:var(--ink); }
.tipe-row .nm{ flex:1; } .tipe-row .vl{ font-weight:700; } .tipe-row .pc{ color:var(--muted); width:62px; text-align:right; }
.tipe-ic{ width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; }

/* ------------------------------------------------ ringkasan */
.note p{ color:#1f3560; font-size:14.5px; line-height:1.65; margin:0 0 12px 0; }
.attn{ background:#fff7e8; border:1px solid #fde2b0; border-radius:12px; padding:14px 16px; margin:10px 0 14px 0; }
.attn .h{ font-weight:700; color:#b45309; margin-bottom:6px; }
.attn ul{ margin:0; padding-left:18px; } .attn li{ font-size:13.5px; color:#1f3560; margin-bottom:5px; }

/* tombol utama */
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"], .stFormSubmitButton > button{
  background: linear-gradient(90deg,#1d4ed8,#2563eb); border:0; color:#fff; font-weight:700; border-radius:12px;
  padding:.6rem 1rem; box-shadow:0 6px 16px rgba(29,78,216,.30);
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover{ filter:brightness(1.08); color:#fff; }

/* filter bar */
div[data-testid="stSelectbox"] label p{ font-size:12.5px; color:var(--muted); font-weight:600; }

@media (max-width: 900px){
  .hero-t{ font-size:26px; } .hero-m{ border-left:0; padding-left:0; } .kpi-v{ font-size:30px; }
}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(data_per, diperbarui):
    st.markdown(f"""
    <div class="hero">
      <div class="hero-l">
        <div class="hero-shield">🛡️</div>
        <div>
          <div class="hero-t">Dashboard Kebencanaan</div>
          <div class="hero-s">Monitoring Kejadian dan Dampak Bencana</div>
          <div class="hero-w">Wilayah Sumatera dan Kalimantan (15 Provinsi)</div>
        </div>
      </div>
      <div class="hero-m">📅 <b>Data per {data_per}</b><br>Diperbarui: {diperbarui}</div>
      <div class="hero-r">
        <img src="{EMBLEM}">
        <div class="hero-bin">BIN</div>
        <div class="hero-dir"><b>DIREKTORAT 2.3</b><br>Sumatera &amp; Kalimantan</div>
      </div>
    </div>""", unsafe_allow_html=True)


def kpi(icon, label, value, delta, cls, unit=""):
    """delta: persentase perubahan vs periode sebelumnya (None = tidak ada pembanding).
    Kenaikan dampak bencana ditandai merah, penurunan hijau."""
    if delta is None:
        d = '<b class="flat">–</b> tidak ada pembanding'
    elif abs(delta) < 0.05:
        d = '<b class="flat">▬ 0,0%</b> dari periode sebelumnya'
    else:
        arrow, c = ("▲", "up") if delta > 0 else ("▼", "down")
        txt = f"{abs(delta):.1f}".replace(".", ",")
        d = f'<b class="{c}">{arrow} {txt}%</b> dari periode sebelumnya'
    u = f"<small>{unit}</small>" if unit else ""
    return f"""
    <div class="kpi kpi-{cls}">
      <div class="kpi-ic">{icon}</div>
      <div><div class="kpi-lb">{label}</div><div class="kpi-v">{value}{u}</div><div class="kpi-d">{d}</div></div>
    </div>"""


def panel_title(text, sub=None):
    s = f" <span>{sub}</span>" if sub else ""
    st.markdown(f'<div class="ptitle">{text}{s}</div>', unsafe_allow_html=True)
