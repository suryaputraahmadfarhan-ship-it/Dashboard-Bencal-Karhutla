# -*- coding: utf-8 -*-
"""Dashboard Kebencanaan - Direktorat 2.3 (BIN Deputi 2) - Sumatera & Kalimantan."""
from datetime import datetime

import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Dashboard Kebencanaan - Direktorat 2.3 BIN", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="expanded")

import theme  # noqa: E402  (setelah set_page_config)
from auth import current_user, get_log, is_admin, logout, require_login, _users  # noqa: E402
from data_generator import PROVINSI, WIB, generate_all, today_wib  # noqa: E402
from data_utils import (KOLOM_TEMPLATE_BENCANA, KOLOM_TEMPLATE_HOTSPOT, PERIODE, baca_file,  # noqa: E402
                        delta_pct, fmt_compact, fmt_num, normalize_bencana, normalize_hotspot, peta_view,
                        split_periode, tgl_id, tipe_tersedia, wilayah_options, wilayah_provinsi)
from report import build_docx, build_xlsx  # noqa: E402
from theme import EMBLEM, HOTSPOT_BUCKET_COLOR, METRIK_COLOR, METRIK_LABEL, TIPE_COLOR, TIPE_ICON  # noqa: E402

MAP_STYLE = os.environ.get("MAP_STYLE", "carto-positron")  # "white-bg" bila jaringan tanpa internet

theme.inject()
user = require_login()  # berhenti di sini bila belum login


# ====================================================================== helper umum
def show(fig):
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:
        st.plotly_chart(fig, use_container_width=True)


def show_df(df, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def style(fig, h=320, legend=True):
    fig.update_layout(height=h, margin=dict(l=8, r=8, t=28, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif",
                                                              size=12, color="#0f2a5c"),
                      showlegend=legend, legend_title_text="")
    fig.update_xaxes(showgrid=False, linecolor="#dbe6f6")
    fig.update_yaxes(gridcolor="#e8eef9", zeroline=False)
    return fig


def tren_bar(labels, values, color, metric="kejadian", height=280):
    """Bar + line overlay dengan label angka di atas setiap batang.
    Dipakai untuk visualisasi tren yang mudah dibaca pimpinan."""
    labels = list(labels)
    values = list(values)
    digits = 1 if metric in ("luas_ha", "magnitudo", "tinggi_genangan_cm") else 0
    texts = [fmt_num(v, digits) for v in values]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=values, marker=dict(color=color, line=dict(color=color, width=0)),
        opacity=0.88, text=texts, textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color="#0f2a5c", family="Plus Jakarta Sans"),
        hovertemplate="<b>%{x}</b><br>%{y:,.1f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=values, mode="lines+markers",
        line=dict(color=color, width=2), marker=dict(size=6, color=color, line=dict(color="#fff", width=1.5)),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        height=height, showlegend=False, bargap=0.3,
        margin=dict(l=8, r=8, t=28, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif", size=12, color="#0f2a5c"),
    )
    fig.update_xaxes(type="category", tickangle=-30 if len(labels) > 6 else 0,
                     tickfont_size=10, showgrid=False, linecolor="#dbe6f6")
    # Headroom untuk label angka
    yv = [v for v in values if v is not None]
    ymax = max(yv) if yv else 1
    fig.update_yaxes(range=[0, ymax * 1.22 if ymax > 0 else 1],
                     gridcolor="#e8eef9", zeroline=False, showticklabels=False)
    return fig


def gabung_id(items):
    items = [str(i) for i in items]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " dan " + items[-1]


def map_scatter(df, center, zoom, height, **kw):
    """Peta dengan basemap bebas-token (carto-positron)."""
    try:
        fig = px.scatter_map(df, lat="lat", lon="lon", center=center, zoom=zoom, height=height,
                             map_style=MAP_STYLE, **kw)
    except (AttributeError, TypeError):
        fig = px.scatter_mapbox(df, lat="lat", lon="lon", center=center, zoom=zoom, height=height,
                                mapbox_style=MAP_STYLE, **kw)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def bucket_hotspot(n):
    if n > 50:
        return "> 50 hotspot"
    if n > 20:
        return "21 – 50 hotspot"
    if n > 5:
        return "6 – 20 hotspot"
    return "1 – 5 hotspot"


def hotspot_map(h, wilayah, height=430, zoom_delta=0.0):
    cnt = h.groupby("provinsi").size()
    h = h.assign(kategori=h["provinsi"].map(cnt).map(bucket_hotspot))
    center, zoom = peta_view(wilayah)
    zoom += zoom_delta
    hover = {c: True for c in ["provinsi", "confidence", "satelit", "frp"] if c in h.columns}
    hover.update({"lat": False, "lon": False, "kategori": False})
    fig = map_scatter(h, center, zoom, height, color="kategori", color_discrete_map=HOTSPOT_BUCKET_COLOR,
                      category_orders={"kategori": list(HOTSPOT_BUCKET_COLOR)}, hover_name="kabupaten",
                      hover_data=hover, opacity=0.9)
    fig.update_traces(marker=dict(size=9))
    fig.update_layout(showlegend=False)
    return fig


def legend_hotspot():
    items = "".join(f'<span><span class="dot" style="background:{c}"></span>{k}</span>'
                    for k, c in HOTSPOT_BUCKET_COLOR.items())
    st.markdown(f'<div class="legend-row">{items}</div>', unsafe_allow_html=True)


def top_hotspot_df(h, n=5):
    if h is None or h.empty:
        return pd.DataFrame(columns=["provinsi", "hotspot"])
    return (h.groupby("provinsi").size().reset_index(name="hotspot")
            .sort_values("hotspot", ascending=False).head(n).reset_index(drop=True))


def top_table_html(top):
    rows = "".join(f"<tr><td>{i + 1}</td><td>{r.provinsi}</td><td class='num'>{fmt_num(r.hotspot)}</td></tr>"
                   for i, r in enumerate(top.itertuples()))
    return ("<table class='toptable'><tr><th>No</th><th>Provinsi</th><th class='num'>Hotspot</th></tr>"
            f"{rows}</table>")


def agg_prov(df):
    cols = ["provinsi", "kejadian", "luas_ha", "luas_padam_ha", "luas_belum_padam_ha",
            "korban_jiwa", "pengungsi", "ispa", "rumah_terdampak"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    aggs = {"kejadian": ("tipe_bencana", "size"), "luas_ha": ("luas_ha", "sum"),
            "korban_jiwa": ("korban_jiwa", "sum"), "pengungsi": ("pengungsi", "sum"),
            "ispa": ("ispa", "sum")}
    if "luas_padam_ha" in df.columns:
        aggs["luas_padam_ha"] = ("luas_padam_ha", "sum")
    if "rumah_terdampak" in df.columns:
        aggs["rumah_terdampak"] = ("rumah_terdampak", "sum")
    out = (df.groupby("provinsi").agg(**aggs)
           .reset_index().sort_values("kejadian", ascending=False).reset_index(drop=True))
    if "luas_padam_ha" in out.columns and "luas_ha" in out.columns:
        out["luas_belum_padam_ha"] = (out["luas_ha"] - out["luas_padam_ha"]).clip(lower=0)
    return out


def agg_tipe(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["tipe_bencana", "kejadian", "luas_ha", "luas_padam_ha",
                                     "luas_belum_padam_ha", "korban_jiwa", "ispa"])
    aggs = dict(kejadian=("tipe_bencana", "size"), luas_ha=("luas_ha", "sum"),
                korban_jiwa=("korban_jiwa", "sum"), ispa=("ispa", "sum"))
    if "luas_padam_ha" in df.columns:
        aggs["luas_padam_ha"] = ("luas_padam_ha", "sum")
    out = (df.groupby("tipe_bencana").agg(**aggs)
           .reset_index().sort_values("kejadian", ascending=False).reset_index(drop=True))
    if "luas_padam_ha" in out.columns and "luas_ha" in out.columns:
        out["luas_belum_padam_ha"] = (out["luas_ha"] - out["luas_padam_ha"]).clip(lower=0)
    return out


def bersihkan(df):
    """Kolom yang tidak perlu ditampilkan/diexport; kolom all-NaN juga dibuang biar tabel bersih per jenis."""
    if df is None or df.empty:
        return df
    d = df.drop(columns=[c for c in ["id_kejadian", "lat", "lon", "korban_luka", "severity"] if c in df.columns])
    # Tambah kolom turunan 'luas_belum_padam_ha' untuk kejadian Karhutla
    if "luas_padam_ha" in d.columns and "luas_ha" in d.columns:
        belum = (pd.to_numeric(d["luas_ha"], errors="coerce")
                 - pd.to_numeric(d["luas_padam_ha"], errors="coerce"))
        d["luas_belum_padam_ha"] = belum.clip(lower=0)
    pref = ["tanggal", "provinsi", "kabupaten", "tipe_bencana",
            "magnitudo", "kedalaman_km", "tinggi_genangan_cm", "rumah_terdampak",
            "luas_ha", "luas_padam_ha", "luas_belum_padam_ha",
            "korban_jiwa", "pengungsi", "ispa",
            "penyebab", "status_verifikasi", "sumber"]
    d = d[[c for c in pref if c in d.columns] + [c for c in d.columns if c not in pref]].copy()
    for c in ["magnitudo", "kedalaman_km", "tinggi_genangan_cm", "rumah_terdampak", "luas_ha",
              "luas_padam_ha", "luas_belum_padam_ha", "ispa"]:
        if c in d.columns and d[c].isna().all():
            d = d.drop(columns=c)
    if "tanggal" in d.columns:
        d["tanggal"] = pd.to_datetime(d["tanggal"]).dt.strftime("%Y-%m-%d")
    return d


def metrik_spesifik(df):
    """Rangkuman metrik spesifik per jenis bencana (list of dict), untuk tabel detail & laporan."""
    if df is None or df.empty:
        return []
    out = []
    for tipe, g in df.groupby("tipe_bencana"):
        item = {"Jenis": tipe, "Kejadian": len(g)}
        if tipe == "Karhutla":
            if "luas_ha" in g and g["luas_ha"].notna().any():
                item["Luas (ha)"] = float(g["luas_ha"].sum())
            if "luas_padam_ha" in g and g["luas_padam_ha"].notna().any():
                padam = float(g["luas_padam_ha"].sum(skipna=True))
                total = float(g["luas_ha"].sum(skipna=True))
                item["Sudah Padam (ha)"] = padam
                item["Belum Padam (ha)"] = max(0.0, total - padam)
            if "ispa" in g:
                item["ISPA"] = int(g["ispa"].sum())
        elif tipe == "Banjir":
            if "tinggi_genangan_cm" in g and g["tinggi_genangan_cm"].notna().any():
                item["Tinggi genangan rata-rata (cm)"] = float(g["tinggi_genangan_cm"].mean())
                item["Tinggi genangan maks (cm)"] = int(g["tinggi_genangan_cm"].max())
            if "rumah_terdampak" in g and g["rumah_terdampak"].notna().any():
                item["Rumah terdampak"] = int(g["rumah_terdampak"].sum())
            if "luas_ha" in g and g["luas_ha"].notna().any():
                item["Luas (ha)"] = float(g["luas_ha"].sum())
        elif tipe == "Gempa":
            if "magnitudo" in g and g["magnitudo"].notna().any():
                item["Magnitudo rata-rata (SR)"] = float(g["magnitudo"].mean())
                item["Magnitudo maks (SR)"] = float(g["magnitudo"].max())
            if "kedalaman_km" in g and g["kedalaman_km"].notna().any():
                item["Kedalaman rata-rata (km)"] = float(g["kedalaman_km"].mean())
            if "rumah_terdampak" in g and g["rumah_terdampak"].notna().any():
                item["Rumah terdampak"] = int(g["rumah_terdampak"].sum())
        else:  # Bencana Alam Lainnya
            if "rumah_terdampak" in g and g["rumah_terdampak"].notna().any():
                item["Rumah terdampak"] = int(g["rumah_terdampak"].sum())
            if "penyebab" in g.columns:
                sub_counts = g["penyebab"].dropna().astype(str).value_counts()
                sub_counts = sub_counts[sub_counts.index.str.lower() != "tidak diketahui"]
                if len(sub_counts):
                    item["Rincian"] = ", ".join(f"{k} ({v})" for k, v in sub_counts.items())
        item["Korban jiwa"] = int(g["korban_jiwa"].sum()) if "korban_jiwa" in g else 0
        item["Pengungsi"] = int(g["pengungsi"].sum()) if "pengungsi" in g else 0
        out.append(item)
    return out


# ====================================================================== sumber data
@st.cache_data(show_spinner="Menyiapkan data demo...")
def demo_data(hari):
    return generate_all(seed=42, days=120, end=hari)


def load_data():
    if st.session_state.get("src") == "upload" and st.session_state.get("up_inc") is not None:
        return st.session_state["up_inc"], st.session_state.get("up_hs"), False
    inc, hs = demo_data(today_wib().isoformat())
    return inc, hs, True


inc_all, hs_all, is_demo = load_data()
if "dimuat" not in st.session_state:
    st.session_state["dimuat"] = datetime.now(WIB).strftime("%H.%M WIB")

# ====================================================================== sidebar
PAGES = [("🏠", "Beranda"), ("📊", "Data & Grafik"), ("🗂️", "Rekap Wilayah"),
         ("🛰️", "Sebaran Hotspot"), ("📄", "Laporan")]
if is_admin():
    PAGES.append(("⚙️", "Pengelolaan Data"))
ICON = dict((n, i) for i, n in PAGES)
names = [n for _, n in PAGES]
# Migrasi nama lama "Peta Sebaran" → "Sebaran Hotspot"
if st.session_state.get("nav") == "Peta Sebaran":
    st.session_state["nav"] = "Sebaran Hotspot"
if st.session_state.get("nav") not in names:
    st.session_state["nav"] = "Beranda"

with st.sidebar:
    st.markdown(f"""
    <div class="nav-brand"><img src="{EMBLEM}">
      <div><div class="b1">BADAN<br>INTELIJEN NEGARA</div><div class="b2">REPUBLIK INDONESIA</div></div></div>
    <div class="nav-dir"><div class="d1">DIREKTORAT 2.3</div>
      <div class="d2">Wilayah Sumatera<br>dan Kalimantan</div></div>""", unsafe_allow_html=True)
    page = st.radio("Menu", names, key="nav", label_visibility="collapsed",
                    format_func=lambda n: f"{ICON[n]}  {n}")
    st.markdown(f"""<div class="navuser"><div class="u1">👤 {user['name']}</div>
      <div class="u2">Peran: {user['role']}</div></div>""", unsafe_allow_html=True)
    if st.button("Keluar", key="logout"):
        logout()
        st.rerun()
    st.markdown('<div class="navtag">Deteksi Dini<br>untuk Stabilitas<br>Nasional</div>', unsafe_allow_html=True)

# ====================================================================== hero
end_date = inc_all["tanggal"].max().normalize()
theme.hero(tgl_id(end_date, panjang=True), st.session_state["dimuat"])
if is_demo:
    st.info("Menampilkan **data demo (sintetis)**. Angka di bawah bukan data riil.", icon="ℹ️")

# ====================================================================== halaman admin (tanpa filter)
if page == "Pengelolaan Data":
    theme.panel_title("⚙️ Pengelolaan Data & Akses", "khusus Admin")
    t1, t2, t3 = st.tabs(["Sumber Data", "Log Akses", "Akun"])

    with t1:
        st.markdown("Pilih sumber data yang ditampilkan di dashboard. Data upload hanya tersimpan selama sesi "
                    "browser Admin dan tidak ditulis ke GitHub.")
        mode = st.radio("Sumber data", ["Data demo (sintetis)", "Data upload (Pusat)"], horizontal=True,
                        index=1 if st.session_state.get("src") == "upload" else 0)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Template data bencana (CSV)",
                               pd.DataFrame(columns=KOLOM_TEMPLATE_BENCANA).to_csv(index=False).encode("utf-8"),
                               "template_bencana.csv", "text/csv")
        with c2:
            st.download_button("⬇️ Template data hotspot (CSV)",
                               pd.DataFrame(columns=KOLOM_TEMPLATE_HOTSPOT).to_csv(index=False).encode("utf-8"),
                               "template_hotspot.csv", "text/csv")
        if mode.startswith("Data upload"):
            f1 = st.file_uploader("File data bencana (CSV/Excel) - wajib", type=["csv", "xlsx", "xls"], key="f_inc")
            f2 = st.file_uploader("File hotspot (CSV/Excel) - opsional", type=["csv", "xlsx", "xls"], key="f_hs")
            if f1 is not None:
                sig = (f1.name, f1.size)
                if st.session_state.get("sig_inc") != sig:
                    try:
                        st.session_state["up_inc"] = normalize_bencana(baca_file(f1))
                        st.session_state["sig_inc"] = sig
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Gagal membaca data bencana: {e}")
            if f2 is not None:
                sig = (f2.name, f2.size)
                if st.session_state.get("sig_hs") != sig:
                    try:
                        st.session_state["up_hs"] = normalize_hotspot(baca_file(f2))
                        st.session_state["sig_hs"] = sig
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Gagal membaca data hotspot: {e}")
            if st.session_state.get("up_inc") is not None:
                if st.session_state.get("src") != "upload":
                    st.session_state["src"] = "upload"
                    st.rerun()
                st.success(f"Data upload aktif: {len(st.session_state['up_inc'])} baris kejadian"
                           + (f", {len(st.session_state['up_hs'])} titik hotspot." if st.session_state.get("up_hs")
                              is not None else "."))
            else:
                st.warning("Belum ada file bencana diunggah; dashboard masih memakai data demo.")
        else:
            if st.session_state.get("src") != "demo":
                st.session_state["src"] = "demo"
                st.rerun()

    with t2:
        log = get_log()
        if log:
            show_df(pd.DataFrame(log))
        else:
            st.caption("Belum ada aktivitas tercatat sejak aplikasi dijalankan.")
        st.caption("Log disimpan di memori server (500 peristiwa terakhir) dan hilang bila aplikasi restart.")

    with t3:
        users = _users() or {}
        show_df(pd.DataFrame([{"Username": k, "Nama": v.get("name", k), "Peran": v.get("role", "Personel")}
                              for k, v in users.items()]))
        st.markdown("""
**Menambah / mengganti akun**
1. Di komputer Anda jalankan `python hash_password.py`, masukkan password → salin blok TOML yang dihasilkan.
2. Tempel ke **Secrets** aplikasi (Streamlit Cloud: *Manage app → Settings → Secrets*).
3. Simpan; aplikasi akan memuat ulang akun. Jangan pernah menaruh password atau hash di GitHub.

**Peran:** *Admin* dapat mengelola sumber data, melihat log, dan mengunduh data mentah. *Personel* dapat melihat
dashboard serta mengunduh laporan ringkas.""")
    st.stop()

# ====================================================================== filter bar
# Sebaran Hotspot dipakem ke Karhutla (hotspot = indikator karhutla), gunakan key berbeda
# agar pilihan jenis bencana di halaman lain tidak terpengaruh.
with st.container(border=True):
    f1, f2, f3 = st.columns(3)
    if page == "Sebaran Hotspot":
        f1.selectbox("Jenis Bencana", ["Karhutla"], key="f_tipe_hotspot",
                     disabled=True, help="Dipakem ke Karhutla karena hotspot adalah indikator karhutla.")
        tipe = "Karhutla"
    else:
        tipe = f1.selectbox("Jenis Bencana", ["Semua"] + tipe_tersedia(inc_all), key="f_tipe")
    periode = f2.selectbox("Periode", list(PERIODE), key="f_periode")
    wilayah = f3.selectbox("Wilayah", wilayah_options(sorted(inc_all["provinsi"].dropna().unique())),
                           key="f_wilayah")

days = PERIODE[periode]
prov_list = wilayah_provinsi(wilayah)
inc_f = inc_all if tipe == "Semua" else inc_all[inc_all["tipe_bencana"] == tipe]
if prov_list:
    inc_f = inc_f[inc_f["provinsi"].isin(prov_list)]
cur, prev = split_periode(inc_f, end_date, days)

hs_f = hs_today = hs_prevday = hs_period = None
hs_end = None
if hs_all is not None and not hs_all.empty:
    hs_f = hs_all[hs_all["provinsi"].isin(prov_list)] if prov_list else hs_all
    hs_end = hs_all["tanggal"].max().normalize()
    d_ = hs_f["tanggal"].dt.normalize()
    hs_today = hs_f[d_ == hs_end]
    hs_prevday = hs_f[d_ == hs_end - pd.Timedelta(days=1)]
    hs_period, _ = split_periode(hs_f, hs_end, days)
wil_label = "Sumatera dan Kalimantan" if wilayah == "Sumatera & Kalimantan" else wilayah


# ====================================================================== helper filter kondisional
def _metrik_tren(tp):
    """Daftar (metrik, judul, agregasi) untuk chart tren bulanan per jenis spesifik."""
    if tp == "Karhutla":
        return [("kejadian", "Jumlah Kejadian Karhutla", "count"),
                ("luas_ha", "Luas Terbakar (ha)", "sum"),
                ("luas_padam_ha", "Luas Sudah Padam (ha)", "sum"),
                ("ispa", "Kasus ISPA", "sum")]
    if tp == "Banjir":
        return [("kejadian", "Jumlah Kejadian Banjir", "count"),
                ("rumah_terdampak", "Rumah Terdampak", "sum"),
                ("tinggi_genangan_cm", "Tinggi Genangan Rata-rata (cm)", "mean"),
                ("pengungsi", "Pengungsi", "sum")]
    if tp == "Gempa":
        return [("kejadian", "Jumlah Kejadian Gempa", "count"),
                ("magnitudo", "Magnitudo Maksimum (SR)", "max"),
                ("rumah_terdampak", "Rumah Terdampak", "sum"),
                ("korban_jiwa", "Korban Jiwa", "sum")]
    # Bencana Alam Lainnya
    return [("kejadian", "Jumlah Kejadian", "count"),
            ("rumah_terdampak", "Rumah Terdampak", "sum"),
            ("pengungsi", "Pengungsi", "sum"),
            ("korban_jiwa", "Korban Jiwa", "sum")]


def pakai_hotspot():
    return tipe in ("Semua", "Karhutla")


def pakai_ispa():
    return tipe in ("Semua", "Karhutla")


# ====================================================================== analisis otomatis (narasi)
def _ringkasan_untuk(cur_df, prev_df, jenis_lap, hs_today_df, hs_prevday_df, hs_end_ts, wil_label_):
    """Versi reusable dari ringkasan() — dipakai juga untuk laporan per-jenis."""
    if cur_df is None or cur_df.empty:
        return ("Tidak ada kejadian tercatat pada periode dan filter yang dipilih.", [])
    n = len(cur_df)
    prev_n = len(prev_df) if prev_df is not None else None
    d = delta_pct(n, prev_n)
    if d is None:
        tren = "belum dapat dibandingkan dengan periode sebelumnya"
    elif d > 2:
        tren = f"tren meningkat ({fmt_num(abs(d), 1)}%) dibandingkan periode sebelumnya"
    elif d < -2:
        tren = f"tren menurun ({fmt_num(abs(d), 1)}%) dibandingkan periode sebelumnya"
    else:
        tren = "kondisi relatif stabil dibandingkan periode sebelumnya"
    dom = cur_df["tipe_bencana"].value_counts()
    teks = (f"Secara umum, kejadian bencana di wilayah {wil_label_} menunjukkan {tren}. "
            f"Jenis bencana terbanyak adalah {dom.index[0]} ({fmt_num(dom.iloc[0])} dari {fmt_num(n)} kejadian).")
    top5 = cur_df.groupby("provinsi").size().sort_values(ascending=False).head(5)
    if len(top5):
        teks += (" Lima provinsi dengan kejadian terbanyak: "
                 + gabung_id([f"{p} ({fmt_num(v)})" for p, v in top5.items()]) + ".")
    perh = []
    use_hotspot = jenis_lap in ("Semua", "Karhutla")
    use_ispa = jenis_lap in ("Semua", "Karhutla")
    if use_hotspot and hs_today_df is not None and not hs_today_df.empty:
        top3 = top_hotspot_df(hs_today_df, 3)
        teks += (f" Sebaran hotspot pada {tgl_id(hs_end_ts)} paling terkonsentrasi di "
                 f"{gabung_id(top3['provinsi'])}.")
        a_ = hs_today_df.groupby("provinsi").size()
        b_ = hs_prevday_df.groupby("provinsi").size() if hs_prevday_df is not None else pd.Series(dtype=int)
        naik = (a_ - b_.reindex(a_.index).fillna(0)).sort_values(ascending=False)
        naik = naik[naik > 0].head(2)
        if len(naik):
            perh.append("Peningkatan hotspot dibandingkan hari sebelumnya di "
                        + gabung_id([f"{p} (+{int(v)})" for p, v in naik.items()]) + ".")
    if use_ispa and "ispa" in cur_df.columns:
        ispa = cur_df.groupby("provinsi")["ispa"].sum().sort_values(ascending=False)
        if ispa.sum() > 0:
            perh.append(f"Dampak kesehatan (ISPA) tercatat {fmt_num(ispa.sum())} kasus, terbanyak di "
                        f"{ispa.index[0]} ({fmt_num(ispa.iloc[0])} kasus); perlu diantisipasi.")
    if jenis_lap in ("Semua", "Karhutla") and "luas_padam_ha" in cur_df.columns:
        lp = pd.to_numeric(cur_df["luas_padam_ha"], errors="coerce").sum(skipna=True)
        lt = pd.to_numeric(cur_df["luas_ha"], errors="coerce").sum(skipna=True)
        if lt > 0:
            belum = max(0.0, lt - lp)
            if belum > 0:
                pct_belum = (belum / lt) * 100
                perh.append(f"Luas belum padam {fmt_num(belum, 1)} ha ({fmt_num(pct_belum, 1)}% dari "
                            f"total {fmt_num(lt, 1)} ha) — perlu akselerasi pemadaman.")
            else:
                perh.append(f"Seluruh lahan terbakar ({fmt_num(lt, 1)} ha) telah dilaporkan padam.")
    if jenis_lap in ("Semua", "Banjir", "Gempa", "Bencana Alam Lainnya") and "rumah_terdampak" in cur_df.columns:
        rt = cur_df.groupby("provinsi")["rumah_terdampak"].sum(min_count=1).dropna().sort_values(ascending=False)
        if rt.sum() > 0:
            perh.append(f"Rumah terdampak tercatat {fmt_num(rt.sum())} unit, terbanyak di "
                        f"{rt.index[0]} ({fmt_num(rt.iloc[0])} unit).")
    if jenis_lap == "Banjir" and "tinggi_genangan_cm" in cur_df.columns:
        tg = pd.to_numeric(cur_df["tinggi_genangan_cm"], errors="coerce").dropna()
        if len(tg):
            perh.append(f"Tinggi genangan rata-rata {fmt_num(tg.mean(), 0)} cm "
                        f"(maksimum {fmt_num(tg.max(), 0)} cm).")
    if jenis_lap == "Gempa" and "magnitudo" in cur_df.columns:
        mg = pd.to_numeric(cur_df["magnitudo"], errors="coerce").dropna()
        if len(mg):
            perh.append(f"Magnitudo rata-rata {fmt_num(mg.mean(), 1)} SR "
                        f"(maksimum {fmt_num(mg.max(), 1)} SR).")
    # Breakdown sub-tipe untuk Bencana Alam Lainnya (laporan)
    if jenis_lap in ("Semua", "Bencana Alam Lainnya") and "penyebab" in cur_df.columns:
        lain = cur_df[cur_df["tipe_bencana"] == "Bencana Alam Lainnya"]
        if len(lain):
            sub = lain["penyebab"].dropna().astype(str).value_counts()
            sub = sub[sub.index.str.lower() != "tidak diketahui"]
            if len(sub):
                desc = ", ".join(f"{k} ({v})" for k, v in sub.head(5).items())
                perh.append(f"Rincian 'Bencana Alam Lainnya' meliputi: {desc}.")
    kj = cur_df.groupby("provinsi")["korban_jiwa"].sum().sort_values(ascending=False)
    if kj.sum() > 0:
        perh.append(f"Korban jiwa tercatat {fmt_num(kj.sum())} orang, terbanyak di {kj.index[0]} "
                    f"({fmt_num(kj.iloc[0])} orang).")
    return teks, perh[:4]


def ringkasan():
    if cur is None or cur.empty:
        return ("Tidak ada kejadian tercatat pada periode dan filter yang dipilih.", [])
    n = len(cur)
    d = delta_pct(n, len(prev) if prev is not None else None)
    if d is None:
        tren = "belum dapat dibandingkan dengan periode sebelumnya"
    elif d > 2:
        tren = f"tren meningkat ({fmt_num(abs(d), 1)}%) dibandingkan periode sebelumnya"
    elif d < -2:
        tren = f"tren menurun ({fmt_num(abs(d), 1)}%) dibandingkan periode sebelumnya"
    else:
        tren = "kondisi relatif stabil dibandingkan periode sebelumnya"
    dom = cur["tipe_bencana"].value_counts()
    teks = (f"Secara umum, kejadian bencana di wilayah {wil_label} menunjukkan {tren}. "
            f"Jenis bencana terbanyak adalah {dom.index[0]} ({fmt_num(dom.iloc[0])} dari {fmt_num(n)} kejadian).")
    top5 = (cur.groupby("provinsi").size().sort_values(ascending=False).head(5))
    if len(top5):
        teks += (" Lima provinsi dengan kejadian terbanyak: "
                 + gabung_id([f"{p} ({fmt_num(v)})" for p, v in top5.items()]) + ".")
    perhatian = []
    if pakai_hotspot() and hs_today is not None and not hs_today.empty:
        top3 = top_hotspot_df(hs_today, 3)
        teks += (f" Sebaran hotspot pada {tgl_id(hs_end)} paling terkonsentrasi di "
                 f"{gabung_id(top3['provinsi'])}.")
        a = hs_today.groupby("provinsi").size()
        b = hs_prevday.groupby("provinsi").size() if hs_prevday is not None else pd.Series(dtype=int)
        naik = (a - b.reindex(a.index).fillna(0)).sort_values(ascending=False)
        naik = naik[naik > 0].head(2)
        if len(naik):
            perhatian.append("Peningkatan hotspot dibandingkan hari sebelumnya di "
                             + gabung_id([f"{p} (+{int(v)})" for p, v in naik.items()]) + ".")
        else:
            perhatian.append("Tidak ada peningkatan hotspot berarti dibandingkan hari sebelumnya.")
    if pakai_ispa():
        ispa = cur.groupby("provinsi")["ispa"].sum().sort_values(ascending=False)
        if ispa.sum() > 0:
            perhatian.append(f"Dampak kesehatan (ISPA) tercatat {fmt_num(ispa.sum())} kasus, terbanyak di "
                             f"{ispa.index[0]} ({fmt_num(ispa.iloc[0])} kasus); perlu diantisipasi.")
    if pakai_hotspot() and "luas_padam_ha" in cur.columns:
        lp = pd.to_numeric(cur["luas_padam_ha"], errors="coerce").sum(skipna=True)
        lt = pd.to_numeric(cur["luas_ha"], errors="coerce").sum(skipna=True)
        if lt > 0:
            belum = max(0.0, lt - lp)
            if belum > 0:
                perhatian.append(f"Luas belum padam {fmt_num(belum, 1)} ha "
                                 f"({fmt_num(belum / lt * 100, 1)}% dari {fmt_num(lt, 1)} ha total terbakar).")
    if tipe in ("Semua", "Banjir", "Gempa", "Bencana Alam Lainnya") and "rumah_terdampak" in cur.columns:
        rt = cur.groupby("provinsi")["rumah_terdampak"].sum(min_count=1).dropna().sort_values(ascending=False)
        if rt.sum() > 0:
            perhatian.append(f"Rumah terdampak tercatat {fmt_num(rt.sum())} unit, terbanyak di "
                             f"{rt.index[0]} ({fmt_num(rt.iloc[0])} unit).")
    # Breakdown sub-tipe untuk 'Bencana Alam Lainnya'
    if tipe in ("Semua", "Bencana Alam Lainnya") and "penyebab" in cur.columns:
        lain = cur[cur["tipe_bencana"] == "Bencana Alam Lainnya"]
        if len(lain):
            sub = lain["penyebab"].dropna().astype(str).value_counts()
            sub = sub[sub.index.str.lower() != "tidak diketahui"]
            if len(sub):
                desc = ", ".join(f"{k} ({v})" for k, v in sub.head(4).items())
                perhatian.append(f"Rincian 'Bencana Alam Lainnya' meliputi: {desc}.")
    if tipe == "Banjir" and "tinggi_genangan_cm" in cur.columns:
        tg = pd.to_numeric(cur["tinggi_genangan_cm"], errors="coerce").dropna()
        if len(tg):
            perhatian.append(f"Tinggi genangan rata-rata {fmt_num(tg.mean(), 0)} cm "
                             f"(maksimum {fmt_num(tg.max(), 0)} cm).")
    if tipe == "Gempa" and "magnitudo" in cur.columns:
        mg = pd.to_numeric(cur["magnitudo"], errors="coerce").dropna()
        if len(mg):
            perhatian.append(f"Magnitudo rata-rata {fmt_num(mg.mean(), 1)} SR "
                             f"(maksimum {fmt_num(mg.max(), 1)} SR).")
    kj = cur.groupby("provinsi")["korban_jiwa"].sum().sort_values(ascending=False)
    if kj.sum() > 0:
        perhatian.append(f"Korban jiwa tercatat {fmt_num(kj.sum())} orang, terbanyak di {kj.index[0]} "
                         f"({fmt_num(kj.iloc[0])} orang).")
    return teks, perhatian[:4]


narasi, perhatian = ringkasan()


def kpi_values():
    """KPI dinamis sesuai jenis bencana yang difilter.
    Setiap item: (label, value, prev, digits, unit, icon, cls)."""
    pv = prev if prev is not None else None

    def tot(df, col):
        if df is None or df.empty or col not in df.columns:
            return 0.0
        s = pd.to_numeric(df[col], errors="coerce")
        return float(s.sum(skipna=True))

    def avg(df, col):
        if df is None or df.empty or col not in df.columns:
            return 0.0
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        return float(s.mean()) if len(s) else 0.0

    def mx(df, col):
        if df is None or df.empty or col not in df.columns:
            return 0.0
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        return float(s.max()) if len(s) else 0.0

    kejadian = ("Jumlah Kejadian", len(cur), len(pv) if pv is not None else None, 0, "", "🔔", "blue")
    luas = ("Luas Terdampak", tot(cur, "luas_ha"),
            tot(pv, "luas_ha") if pv is not None else None, 1, "ha", "🗺️", "teal")
    korban = ("Korban Jiwa", tot(cur, "korban_jiwa"),
              tot(pv, "korban_jiwa") if pv is not None else None, 0, "jiwa", "👤", "orange")
    ispa = ("Dampak (ISPA)", tot(cur, "ispa"),
            tot(pv, "ispa") if pv is not None else None, 0, "kasus", "🫁", "purple")
    pengungsi = ("Pengungsi", tot(cur, "pengungsi"),
                 tot(pv, "pengungsi") if pv is not None else None, 0, "orang", "🧳", "amber")
    rumah = ("Rumah Terdampak", tot(cur, "rumah_terdampak"),
             tot(pv, "rumah_terdampak") if pv is not None else None, 0, "unit", "🏠", "rose")
    if tipe == "Banjir":
        tgen = ("Tinggi Genangan Maks", mx(cur, "tinggi_genangan_cm"),
                mx(pv, "tinggi_genangan_cm") if pv is not None else None, 0, "cm", "🌊", "slate")
        return [kejadian, rumah, tgen, korban]
    if tipe == "Gempa":
        mag = ("Magnitudo Maks", mx(cur, "magnitudo"),
               mx(pv, "magnitudo") if pv is not None else None, 1, "SR", "🌋", "slate")
        return [kejadian, mag, rumah, korban]
    if tipe == "Bencana Alam Lainnya":
        return [kejadian, rumah, pengungsi, korban]
    if tipe == "Karhutla":
        # Karhutla fokus pada status pemadaman
        padam = tot(cur, "luas_padam_ha")
        padam_pv = tot(pv, "luas_padam_ha") if pv is not None else None
        belum = max(0.0, tot(cur, "luas_ha") - padam)
        belum_pv = (max(0.0, tot(pv, "luas_ha") - padam_pv)
                    if pv is not None and padam_pv is not None else None)
        luas_terbakar = ("Luas Terbakar", tot(cur, "luas_ha"),
                         tot(pv, "luas_ha") if pv is not None else None, 1, "ha", "🔥", "orange")
        sudah_padam = ("Sudah Padam", padam, padam_pv, 1, "ha", "✅", "teal")
        belum_padam = ("Belum Padam", belum, belum_pv, 1, "ha", "⚠️", "rose")
        return [luas_terbakar, sudah_padam, belum_padam, ispa]
    # Semua
    return [kejadian, luas, korban, ispa]


KPIS = kpi_values()


def kpi_row():
    cols = st.columns(4)
    for col, (label, v, pv, dg, unit, ic, cls) in zip(cols, KPIS):
        v_str = fmt_compact(v, dg) if v is not None and v >= 10_000 else fmt_num(v, dg)
        col.markdown(theme.kpi(ic, label, v_str, delta_pct(v, pv), cls, unit), unsafe_allow_html=True)


# ====================================================================== BERANDA
if page == "Beranda":
    kpi_row()
    st.write("")

    # Baris 1 — Peta Kejadian Bencana (semua jenis sesuai filter), full-width
    # ----- Row 1: Peta Kejadian Bencana (FULL WIDTH) -----
    with st.container(border=True):
        theme.panel_title("📍 Peta Kejadian Bencana", f"({periode.lower()} · {tipe})")
        md = cur.dropna(subset=["lat", "lon"]) if {"lat", "lon"} <= set(cur.columns) else cur.iloc[0:0]
        if md.empty:
            st.caption("Tidak ada data dengan koordinat pada filter ini.")
        else:
            st.markdown(f'<div class="psub">{wil_label} · {fmt_num(len(md))} titik kejadian</div>',
                        unsafe_allow_html=True)
            luas_sanitized = pd.to_numeric(md.get("luas_ha"), errors="coerce").fillna(1.0)
            luas_sanitized = luas_sanitized.replace([np.inf, -np.inf], 1.0).clip(lower=1.0).astype(float)
            md2 = md.assign(luas_plot=luas_sanitized.values,
                            tipe_bencana=md["tipe_bencana"].fillna("Bencana Alam Lainnya").astype(str))
            hover = {"provinsi": True, "tipe_bencana": True, "luas_plot": False,
                     "lat": False, "lon": False}
            if "luas_ha" in md2.columns:
                hover["luas_ha"] = ":.1f"
            if "korban_jiwa" in md2.columns:
                hover["korban_jiwa"] = True
            if pakai_ispa() and "ispa" in md2.columns:
                hover["ispa"] = True
            center, zoom = peta_view(wilayah)
            fig_m = map_scatter(md2, center, zoom, 520, color="tipe_bencana",
                                color_discrete_map=TIPE_COLOR, size="luas_plot", size_max=22,
                                hover_name="kabupaten", opacity=0.78, hover_data=hover)
            fig_m.update_layout(legend=dict(orientation="h", y=1.02, x=0, title_text=""))
            show(fig_m)
    st.write("")

    # ----- Row 2: 5 Provinsi Teratas | Tren Kejadian | Jenis Bencana -----
    col_prov, col_tren, col_jenis = st.columns([1, 1.1, 1.1])

    with col_prov, st.container(border=True):
        theme.panel_title("🏷️ 5 Provinsi Teratas", "(kejadian terbanyak)")
        if cur.empty:
            st.caption("Tidak ada data pada filter ini.")
        else:
            top_prov = (cur.groupby("provinsi").size().reset_index(name="kejadian")
                        .sort_values("kejadian", ascending=False).head(5).reset_index(drop=True))
            rows_html = "".join(
                f"<tr><td>{i + 1}</td><td>{r.provinsi}</td>"
                f"<td class='num'>{fmt_num(r.kejadian)}</td></tr>"
                for i, r in enumerate(top_prov.itertuples()))
            st.markdown(
                "<table class='toptable'><tr><th>No</th><th>Provinsi</th>"
                f"<th class='num'>Kejadian</th></tr>{rows_html}</table>",
                unsafe_allow_html=True)

    with col_tren, st.container(border=True):
        if days is None or days > 30:
            gran = "bulanan"
        elif days > 14:
            gran = "mingguan"
        else:
            gran = "harian"
        theme.panel_title("📊 Tren Kejadian", f"(tren {gran})")
        if cur.empty:
            st.caption("Tidak ada data pada filter ini.")
        else:
            if days is not None and days <= 14:
                idx = pd.date_range(end_date - pd.Timedelta(days=max(days - 1, 0)), end_date)
                s = cur.groupby(cur["tanggal"].dt.normalize()).size().reindex(idx, fill_value=0)
                labels = [tgl_id(i) for i in s.index]
            elif days is not None and days <= 30:
                s = cur.groupby(cur["tanggal"].dt.to_period("W").dt.start_time).size()
                labels = [tgl_id(i) for i in s.index]
            else:
                s = cur.groupby(cur["tanggal"].dt.to_period("M").dt.start_time).size()
                labels = [i.strftime("%b %Y") for i in s.index]
            show(tren_bar(labels, list(s.values), METRIK_COLOR["kejadian"], "kejadian", height=280))

    with col_jenis, st.container(border=True):
        theme.panel_title("🧭 Jenis Bencana", "(Jumlah Kejadian)")
        if cur.empty:
            st.caption("Tidak ada data pada filter ini.")
        else:
            g = cur["tipe_bencana"].value_counts()
            fig = go.Figure(go.Pie(labels=g.index, values=g.values, hole=0.62, sort=False,
                                   marker_colors=[TIPE_COLOR.get(k, "#64748b") for k in g.index],
                                   textinfo="percent", textfont_size=11))
            style(fig, 220, legend=False)
            fig.add_annotation(text=f"<b style='font-size:20px'>{fmt_num(len(cur))}</b><br>Kejadian",
                               showarrow=False, font=dict(size=11))
            show(fig)
            html = ""
            for k, v in g.items():
                c = TIPE_COLOR.get(k, "#64748b")
                html += (f'<div class="tipe-row"><div class="tipe-ic" style="background:{c}22">'
                         f'{TIPE_ICON.get(k, "•")}</div><div class="nm">{k}</div>'
                         f'<div class="vl">{fmt_num(v)}</div>'
                         f'<div class="pc">({fmt_num(v / len(cur) * 100, 1)}%)</div></div>')
            st.markdown(html, unsafe_allow_html=True)
    st.write("")

    # ----- Row 3: Ringkasan Kondisi (full-width, dengan perhatian di dalam) -----
    with st.container(border=True):
        theme.panel_title("📝 Ringkasan Kondisi")
        st.markdown(f'<div class="note"><p>{narasi}</p></div>', unsafe_allow_html=True)
        if perhatian:
            li = "".join(f"<li>{p}</li>" for p in perhatian)
            st.markdown(f'<div class="attn"><div class="h">⚠️ Perhatian</div><ul>{li}</ul></div>',
                        unsafe_allow_html=True)
        st.button("Lihat Detail Data  ›", type="primary", key="detail",
                  on_click=lambda: st.session_state.update(nav="Data & Grafik"))

# ====================================================================== DATA & GRAFIK
elif page == "Data & Grafik":
    kpi_row()
    st.write("")
    if cur.empty:
        st.warning("Tidak ada data pada filter ini.")
        st.stop()
    t1, t2, t3 = st.tabs(["Ringkasan Grafik", "Tren Waktu", "Tabel Data"])
    with t1:
        # Jika filter spesifik ke 1 jenis, bar "per Jenis" hanya 1 batang (tidak informatif).
        # Ganti dengan tren bulanan multi-metrik dinamis.
        if tipe == "Semua":
            gt = agg_tipe(cur).copy()
            extra = {}
            for col_name, src_col in [("rumah_terdampak", "rumah_terdampak"), ("pengungsi", "pengungsi")]:
                if src_col in cur.columns:
                    extra[col_name] = cur.groupby("tipe_bencana")[src_col].sum(min_count=1)
            for k, v in extra.items():
                gt[k] = gt["tipe_bencana"].map(v).fillna(0)
            charts = [("kejadian", "Jumlah Kejadian per Jenis"),
                      ("luas_ha", "Luas Terdampak (ha) per Jenis"),
                      ("korban_jiwa", "Korban Jiwa per Jenis"),
                      ("ispa", "Kasus ISPA per Jenis")]
            c1, c2 = st.columns(2)
            for col, (y, title) in zip([c1, c2, c1, c2], charts):
                with col, st.container(border=True):
                    theme.panel_title(title)
                    if y not in gt.columns:
                        st.caption("Tidak ada data untuk metrik ini.")
                        continue
                    fig = px.bar(gt, x="tipe_bencana", y=y, color="tipe_bencana", color_discrete_map=TIPE_COLOR,
                                 text_auto=".1f" if y == "luas_ha" else True)
                    fig.update_traces(textposition="outside", cliponaxis=False)
                    fig.update_xaxes(title=None)
                    fig.update_yaxes(title=None)
                    show(style(fig, 280, legend=False))
        else:
            # TREN per metrik untuk jenis spesifik — >30 hari = bulanan
            series = _metrik_tren(tipe)
            if days is None or days > 30:
                freq, label_fmt, granularity = "M", "%b %Y", "bulanan"
            elif days > 14:
                freq, label_fmt, granularity = "W", "%d %b", "mingguan"
            else:
                freq, label_fmt, granularity = "D", "%d %b", "harian"
            tt = cur.copy()
            tt["periode_grup"] = tt["tanggal"].dt.to_period(freq).dt.start_time
            c1, c2 = st.columns(2)
            for col, (metric, title, agg_func) in zip([c1, c2, c1, c2], series):
                with col, st.container(border=True):
                    theme.panel_title(title, f"(tren {granularity})")
                    if metric == "kejadian":
                        g = tt.groupby("periode_grup").size().reset_index(name="val")
                    elif metric not in tt.columns:
                        st.caption("Tidak ada data untuk metrik ini.")
                        continue
                    else:
                        s = pd.to_numeric(tt[metric], errors="coerce")
                        if agg_func == "mean":
                            g = s.groupby(tt["periode_grup"]).mean().reset_index(name="val")
                        elif agg_func == "max":
                            g = s.groupby(tt["periode_grup"]).max().reset_index(name="val")
                        else:
                            g = s.groupby(tt["periode_grup"]).sum(min_count=1).reset_index(name="val")
                        g["val"] = g["val"].fillna(0)
                    if g.empty or g["val"].sum() == 0:
                        st.caption("Belum ada nilai pada metrik ini.")
                        continue
                    g["label"] = g["periode_grup"].dt.strftime(label_fmt)
                    warna_m = METRIK_COLOR.get(metric, "#2563eb")
                    show(tren_bar(g["label"], g["val"], warna_m, metric))
        with st.container(border=True):
            theme.panel_title("Kejadian per Provinsi", "(15 teratas)")
            gp = agg_prov(cur).head(15).iloc[::-1]
            fig = px.bar(gp, x="kejadian", y="provinsi", orientation="h", text="kejadian",
                         color_discrete_sequence=[METRIK_COLOR["kejadian"]])
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_xaxes(title=None)
            fig.update_yaxes(title=None)
            show(style(fig, 440, legend=False))
        with st.container(border=True):
            theme.panel_title("Metrik Spesifik per Jenis Bencana",
                              "(magnitudo untuk gempa, tinggi genangan untuk banjir, dll)")
            ms = metrik_spesifik(cur)
            if ms:
                dfm = pd.DataFrame(ms)
                for c in dfm.select_dtypes(include="float").columns:
                    dfm[c] = dfm[c].round(2)
                show_df(dfm)
            else:
                st.caption("Tidak ada data pada filter ini.")
    with t2:
        # Granularity: >30 hari = bulanan, >7 = mingguan, else harian — konsisten di seluruh dashboard
        if days is None or days > 30:
            freq, label_fmt, granularity = "M", "%b %Y", "bulanan"
        elif days > 14:
            freq, label_fmt, granularity = "W", "%d %b", "mingguan"
        else:
            freq, label_fmt, granularity = "D", "%d %b", "harian"
        tt = cur.copy()
        tt["periode_grup"] = tt["tanggal"].dt.to_period(freq).dt.start_time

        # 1) Tren kejadian per jenis — stacked bar, warna per jenis (TIPE_COLOR)
        with st.container(border=True):
            theme.panel_title(f"Kejadian per Jenis Bencana", f"(tren {granularity})")
            g = tt.groupby(["periode_grup", "tipe_bencana"]).size().reset_index(name="kejadian")
            if g.empty:
                st.caption("Tidak ada data.")
            else:
                g["label"] = g["periode_grup"].dt.strftime(label_fmt)
                total_per_periode = g.groupby("label")["kejadian"].sum()
                fig = go.Figure()
                for tp in [t for t in ["Karhutla", "Banjir", "Gempa", "Bencana Alam Lainnya"]
                           if t in g["tipe_bencana"].values]:
                    sub = g[g["tipe_bencana"] == tp]
                    # Teks per segmen; sembunyikan kalau 0
                    seg_text = [str(int(v)) if int(v) > 0 else "" for v in sub["kejadian"]]
                    fig.add_trace(go.Bar(
                        x=sub["label"], y=sub["kejadian"], name=tp,
                        marker=dict(color=TIPE_COLOR.get(tp, "#64748b"),
                                    line=dict(color="rgba(255,255,255,.7)", width=1)),
                        text=seg_text, textposition="inside", insidetextanchor="middle",
                        textfont=dict(size=11, color="#ffffff", family="Plus Jakarta Sans"),
                        hovertemplate=f"<b>%{{x}}</b><br>{tp}: %{{y}} kejadian<extra></extra>",
                    ))
                # Total label di atas setiap stack
                labels_sorted = sorted(g["label"].unique(), key=lambda s: g[g["label"] == s]["periode_grup"].iloc[0])
                fig.add_trace(go.Scatter(
                    x=labels_sorted,
                    y=[total_per_periode[l] for l in labels_sorted],
                    text=[f"<b>{fmt_num(total_per_periode[l])}</b>" for l in labels_sorted],
                    mode="text", textposition="top center",
                    textfont=dict(size=13, color="#0f2a5c", family="Plus Jakarta Sans"),
                    showlegend=False, hoverinfo="skip", name="total",
                ))
                ymax = int(total_per_periode.max()) if len(total_per_periode) else 1
                fig.update_layout(
                    barmode="stack", height=380, bargap=0.3,
                    margin=dict(l=8, r=8, t=32, b=8), uniformtext=dict(minsize=10, mode="hide"),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif", size=12, color="#0f2a5c"),
                    legend=dict(orientation="h", y=1.08, x=0, title_text=""),
                )
                fig.update_xaxes(type="category", tickangle=-30 if len(labels_sorted) > 6 else 0,
                                 showgrid=False, linecolor="#dbe6f6")
                fig.update_yaxes(range=[0, ymax * 1.2 if ymax else 1], gridcolor="#e8eef9", zeroline=False,
                                 showticklabels=False)
                show(fig)

        # 2) Tren metrik dampak — pakai METRIK_COLOR (korban=merah, ispa=ungu, dll)
        agg_cols = {"korban_jiwa": ("korban_jiwa", "sum"), "luas_ha": ("luas_ha", "sum"),
                    "ispa": ("ispa", "sum")}
        if "rumah_terdampak" in tt.columns:
            agg_cols["rumah_terdampak"] = ("rumah_terdampak", "sum")
        if "pengungsi" in tt.columns:
            agg_cols["pengungsi"] = ("pengungsi", "sum")
        if "tinggi_genangan_cm" in tt.columns:
            agg_cols["tinggi_genangan_cm"] = ("tinggi_genangan_cm", "mean")
        w = tt.groupby("periode_grup").agg(**agg_cols).reset_index()
        w["label"] = w["periode_grup"].dt.strftime(label_fmt)

        if tipe == "Banjir":
            series = ["rumah_terdampak", "tinggi_genangan_cm", "pengungsi", "korban_jiwa"]
        elif tipe == "Gempa":
            series = ["rumah_terdampak", "korban_jiwa", "pengungsi"]
        elif tipe == "Bencana Alam Lainnya":
            series = ["rumah_terdampak", "pengungsi", "korban_jiwa"]
        else:
            series = ["luas_ha", "korban_jiwa", "ispa"]

        cols = st.columns(len(series))
        for col, metric in zip(cols, series):
            with col, st.container(border=True):
                theme.panel_title(f"{METRIK_LABEL.get(metric, metric)}", f"(tren {granularity})")
                if metric not in w.columns:
                    st.caption("Tidak ada data.")
                    continue
                vals = w[metric].fillna(0)
                if vals.sum() == 0:
                    st.caption("Belum ada nilai pada metrik ini.")
                    continue
                show(tren_bar(w["label"], vals, METRIK_COLOR.get(metric, "#2563eb"), metric, height=260))
    with t3:
        st.markdown("**Data kejadian (sesuai filter)**")
        show_df(bersihkan(cur), height=360)
        st.markdown("**Profil kualitas data**")
        rows = [{"Sumber": "Kejadian", "Jumlah Record": len(cur), "Kolom": cur.shape[1],
                 "Nilai Kosong": int(cur.isna().sum().sum()),
                 "% Kosong": round(cur.isna().sum().sum() / max(cur.size, 1) * 100, 2),
                 "Tanpa Koordinat": int(cur[["lat", "lon"]].isna().any(axis=1).sum())
                 if {"lat", "lon"} <= set(cur.columns) else 0}]
        if hs_period is not None and not hs_period.empty:
            rows.append({"Sumber": "Hotspot", "Jumlah Record": len(hs_period), "Kolom": hs_period.shape[1],
                         "Nilai Kosong": int(hs_period.isna().sum().sum()),
                         "% Kosong": round(hs_period.isna().sum().sum() / max(hs_period.size, 1) * 100, 2),
                         "Tanpa Koordinat": int(hs_period[["lat", "lon"]].isna().any(axis=1).sum())})
        show_df(pd.DataFrame(rows))

# ====================================================================== SEBARAN HOTSPOT
elif page == "Sebaran Hotspot":
    st.caption("🔥 Hotspot (titik api) merupakan indikator **karhutla**; halaman ini "
               "fokus pada karhutla terlepas dari pilihan filter jenis bencana.")
    if hs_f is None or hs_f.empty:
        st.warning("Data hotspot belum tersedia pada filter ini.")
    else:
        # Pilih tanggal hotspot (default: terbaru)
        tgls = sorted(hs_f["tanggal"].dt.normalize().unique(), reverse=True)
        pick = st.selectbox("Tanggal hotspot", tgls, format_func=lambda x: tgl_id(x, True))
        hd = hs_f[hs_f["tanggal"].dt.normalize() == pd.Timestamp(pick)]
        hd_prev = hs_f[hs_f["tanggal"].dt.normalize() == pd.Timestamp(pick) - pd.Timedelta(days=1)]

        # KPI ringkas hotspot
        total_hd = len(hd)
        total_prev = len(hd_prev)
        delta_hs = delta_pct(total_hd, total_prev if total_prev > 0 else None)
        n_prov_aktif = hd["provinsi"].nunique() if total_hd else 0
        top1 = hd["provinsi"].value_counts().head(1)
        high_conf = int((hd["confidence"].astype(str).str.lower() == "high").sum()) if "confidence" in hd.columns else 0

        c_k1, c_k2, c_k3, c_k4 = st.columns(4)
        with c_k1:
            st.markdown(theme.kpi("🛰️", "Total Titik Hotspot", fmt_num(total_hd),
                                   delta_hs, "orange", "titik"), unsafe_allow_html=True)
        with c_k2:
            st.markdown(theme.kpi("🗺️", "Provinsi Terdampak", fmt_num(n_prov_aktif),
                                   None, "blue", "provinsi"), unsafe_allow_html=True)
        with c_k3:
            lb = top1.index[0] if len(top1) else "-"
            st.markdown(theme.kpi("🔥", "Provinsi Hotspot Tertinggi", lb,
                                   None, "rose", f"{fmt_num(top1.iloc[0])} titik" if len(top1) else ""),
                        unsafe_allow_html=True)
        with c_k4:
            st.markdown(theme.kpi("⚠️", "Keyakinan Tinggi", fmt_num(high_conf),
                                   None, "amber", "titik"), unsafe_allow_html=True)
        st.write("")

        # Peta hotspot + rincian
        a, b = st.columns([2.4, 1])
        with a, st.container(border=True):
            theme.panel_title("Sebaran Titik Hotspot",
                              f"({tgl_id(pick, True)} · {fmt_num(len(hd))} titik)")
            show(hotspot_map(hd, wilayah, 520))
            legend_hotspot()
        with b, st.container(border=True):
            theme.panel_title("Rincian Hotspot", "(hari dipilih)")
            st.markdown("**5 Provinsi Tertinggi**")
            st.markdown(top_table_html(top_hotspot_df(hd)), unsafe_allow_html=True)
            if "confidence" in hd.columns and len(hd):
                cg = hd["confidence"].value_counts()
                fig = go.Figure(go.Pie(labels=cg.index, values=cg.values, hole=0.55,
                                       marker_colors=["#93c5fd", "#2563eb", "#1e3a8a"][:len(cg)],
                                       textinfo="label+percent"))
                fig.update_layout(title_text="Tingkat Keyakinan", showlegend=False)
                show(style(fig, 240, legend=False))

        # Analisis: tren hotspot + top provinsi (gunakan hs_period yg sudah terfilter periode)
        hs_scope = hs_period if hs_period is not None and not hs_period.empty else hs_f
        if days is None or days > 30:
            freq, label_fmt, gran_h = "M", "%b %Y", "bulanan"
        elif days > 14:
            freq, label_fmt, gran_h = "W", "%d %b", "mingguan"
        else:
            freq, label_fmt, gran_h = "D", "%d %b", "harian"

        c_t1, c_t2 = st.columns(2)
        with c_t1, st.container(border=True):
            theme.panel_title(f"Tren Hotspot {gran_h.capitalize()}", f"({periode.lower()})")
            tt_h = hs_scope.copy()
            tt_h["grp"] = tt_h["tanggal"].dt.to_period(freq).dt.start_time
            g = tt_h.groupby("grp").size().reset_index(name="hotspot")
            g["label"] = g["grp"].dt.strftime(label_fmt)
            show(tren_bar(g["label"], list(g["hotspot"]), METRIK_COLOR["hotspot"], "hotspot", height=280))
        with c_t2, st.container(border=True):
            theme.panel_title("Top 10 Provinsi", f"({periode.lower()})")
            top_g = (hs_scope.groupby("provinsi").size().reset_index(name="hotspot")
                     .sort_values("hotspot", ascending=True).tail(10))
            fig = px.bar(top_g, x="hotspot", y="provinsi", orientation="h", text="hotspot",
                         color_discrete_sequence=[METRIK_COLOR["hotspot"]])
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_xaxes(title=None, showgrid=False)
            fig.update_yaxes(title=None)
            show(style(fig, 320, legend=False))

        # Analisis naratif ringkas
        with st.container(border=True):
            theme.panel_title("Analisis Hotspot")
            naik_prov = (hd.groupby("provinsi").size()
                         - hd_prev.groupby("provinsi").size().reindex(hd["provinsi"].unique()).fillna(0))
            naik_prov = naik_prov.sort_values(ascending=False)
            kenaikan = naik_prov[naik_prov > 0].head(3)
            analisis = [
                f"Pada {tgl_id(pick, True)} tercatat <b>{fmt_num(total_hd)}</b> titik hotspot di "
                f"{wil_label}, tersebar di <b>{n_prov_aktif}</b> provinsi."
            ]
            if total_prev > 0:
                pct = (total_hd - total_prev) / total_prev * 100
                arah = "meningkat" if pct > 0 else "menurun" if pct < 0 else "stabil"
                analisis.append(f"Dibandingkan hari sebelumnya ({fmt_num(total_prev)} titik), "
                                f"jumlah hotspot {arah} <b>{fmt_num(abs(pct), 1)}%</b>.")
            if len(kenaikan):
                naik_desc = ", ".join(f"{p} (+{int(v)})" for p, v in kenaikan.items())
                analisis.append(f"Peningkatan terbesar terjadi di {naik_desc} — perlu "
                                "pengawasan intensif dan koordinasi tim pemadaman.")
            if high_conf > 0:
                pct_hc = high_conf / total_hd * 100 if total_hd else 0
                analisis.append(f"Dari total titik, <b>{fmt_num(high_conf)} titik ({fmt_num(pct_hc, 1)}%)</b> "
                                "berkeyakinan tinggi (High confidence) — indikasi api aktif yang perlu "
                                "verifikasi lapangan segera.")
            html = "".join(f"<p>• {t}</p>" for t in analisis)
            st.markdown(f'<div class="note">{html}</div>', unsafe_allow_html=True)

# ====================================================================== REKAP WILAYAH
elif page == "Rekap Wilayah":
    base = agg_prov(cur)
    daftar = prov_list or list(PROVINSI)
    daftar = [p for p in daftar if p in set(inc_all["provinsi"]) or p in PROVINSI]
    tabel = base.set_index("provinsi").reindex(daftar).fillna(0).reset_index()
    # Hotspot hanya untuk jenis "Semua" / "Karhutla"
    if pakai_hotspot() and hs_period is not None and not hs_period.empty:
        tabel["hotspot"] = tabel["provinsi"].map(hs_period.groupby("provinsi").size()).fillna(0).astype(int)
    # Tinggi genangan rata-rata untuk Banjir
    if tipe == "Banjir" and "tinggi_genangan_cm" in cur.columns:
        tg = cur.groupby("provinsi")["tinggi_genangan_cm"].mean().round(0)
        tabel["tinggi_genangan_cm"] = tabel["provinsi"].map(tg).fillna(0).astype(int)
    # Magnitudo maks untuk Gempa
    if tipe == "Gempa" and "magnitudo" in cur.columns:
        mg = cur.groupby("provinsi")["magnitudo"].max().round(1)
        tabel["magnitudo_maks"] = tabel["provinsi"].map(mg).fillna(0)
    # Status pemadaman karhutla (padam / belum padam)
    if tipe in ("Semua", "Karhutla") and "luas_padam_ha" in cur.columns:
        if "luas_padam_ha" not in tabel.columns:
            tabel["luas_padam_ha"] = tabel["provinsi"].map(
                cur.groupby("provinsi")["luas_padam_ha"].sum(min_count=1)).fillna(0)
        tabel["luas_belum_padam_ha"] = (tabel["luas_ha"] - tabel["luas_padam_ha"]).clip(lower=0)

    for c in ["kejadian", "korban_jiwa", "pengungsi", "ispa", "rumah_terdampak"]:
        if c in tabel.columns:
            tabel[c] = tabel[c].astype(int)
    # Urutan GEOGRAFIS: Sumatera utara→selatan (Aceh→Lampung) lalu Kalimantan — ikut urutan PROVINSI dict
    urutan = {p: i for i, p in enumerate(PROVINSI.keys())}
    tabel["_ord"] = tabel["provinsi"].map(urutan).fillna(999)
    tabel = tabel.sort_values("_ord").drop(columns="_ord").reset_index(drop=True)

    # Kolom yang ditampilkan sesuai jenis bencana
    kolom_umum = ["provinsi", "kejadian", "korban_jiwa", "pengungsi"]
    if tipe in ("Semua", "Karhutla"):
        kolom_tampil = kolom_umum + ["luas_ha", "luas_padam_ha", "luas_belum_padam_ha", "ispa"]
        if "hotspot" in tabel.columns:
            kolom_tampil.append("hotspot")
    elif tipe == "Banjir":
        kolom_tampil = kolom_umum + ["rumah_terdampak"]
        if "tinggi_genangan_cm" in tabel.columns:
            kolom_tampil.append("tinggi_genangan_cm")
    elif tipe == "Gempa":
        kolom_tampil = kolom_umum + ["rumah_terdampak"]
        if "magnitudo_maks" in tabel.columns:
            kolom_tampil.append("magnitudo_maks")
    else:  # Bencana Alam Lainnya
        kolom_tampil = kolom_umum + ["rumah_terdampak"]
    kolom_tampil = [c for c in kolom_tampil if c in tabel.columns]
    tabel_tampil = tabel[kolom_tampil]

    with st.container(border=True):
        theme.panel_title("Rekap per Provinsi", f"({periode.lower()} · {wil_label} · {tipe})")
        cfg = {
            "provinsi": "Provinsi",
            "kejadian": st.column_config.ProgressColumn("Kejadian", min_value=0,
                                                        max_value=max(int(tabel["kejadian"].max()), 1), format="%d"),
            "luas_ha": st.column_config.NumberColumn("Luas Terbakar (ha)", format="%.1f"),
            "luas_padam_ha": st.column_config.NumberColumn("Sudah Padam (ha)", format="%.1f"),
            "luas_belum_padam_ha": st.column_config.NumberColumn("Belum Padam (ha)", format="%.1f"),
            "korban_jiwa": "Korban Jiwa", "pengungsi": "Pengungsi", "ispa": "ISPA",
            "rumah_terdampak": "Rumah Terdampak", "hotspot": "Hotspot (periode)",
            "tinggi_genangan_cm": st.column_config.NumberColumn("Tinggi Genangan Rata² (cm)", format="%d"),
            "magnitudo_maks": st.column_config.NumberColumn("Magnitudo Maks (SR)", format="%.1f"),
        }
        show_df(tabel_tampil, column_config=cfg, height=min(40 + 35 * len(tabel_tampil), 600))
    pilih = st.selectbox("Lihat rincian provinsi", tabel["provinsi"].tolist())
    d = cur[cur["provinsi"] == pilih]
    a, b = st.columns([1.1, 1])

    with a, st.container(border=True):
        if tipe == "Semua":
            theme.panel_title(f"Komposisi Jenis Bencana - {pilih}")
            if d.empty:
                st.caption("Tidak ada kejadian pada periode ini.")
            else:
                g = d["tipe_bencana"].value_counts().reset_index()
                g.columns = ["tipe_bencana", "kejadian"]
                fig = px.bar(g, x="tipe_bencana", y="kejadian", color="tipe_bencana",
                             color_discrete_map=TIPE_COLOR, text="kejadian")
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_xaxes(title=None)
                fig.update_yaxes(title=None)
                show(style(fig, 300, legend=False))
        else:
            # Filter spesifik → tren kejadian jenis itu di provinsi (threshold konsisten 30/7 hari)
            if days is None or days > 30:
                freq, label_fmt, granularity = "M", "%b %Y", "bulanan"
            elif days > 14:
                freq, label_fmt, granularity = "W", "%d %b", "mingguan"
            else:
                freq, label_fmt, granularity = "D", "%d %b", "harian"
            theme.panel_title(f"Tren Kejadian {tipe} - {pilih}", f"({granularity})")
            if d.empty:
                st.caption("Tidak ada kejadian pada periode ini.")
            else:
                dd = d.copy()
                dd["grp"] = dd["tanggal"].dt.to_period(freq).dt.start_time
                g = dd.groupby("grp").size().reset_index(name="kejadian")
                g["label"] = g["grp"].dt.strftime(label_fmt)
                show(tren_bar(g["label"], list(g["kejadian"]), METRIK_COLOR["kejadian"], "kejadian", height=300))

    with b, st.container(border=True):
        theme.panel_title(f"Kabupaten/Kota - {pilih}")
        if d.empty:
            st.caption("Tidak ada kejadian pada periode ini.")
        else:
            # Kolom "Jenis Bencana" per kabupaten agar tidak ambigu
            def _jenis_lengkap(df_kab):
                """Tampilkan jenis bencana per kabupaten; untuk 'Bencana Alam Lainnya'
                sertakan sub-tipe dari kolom penyebab. Mis. 'Bencana Alam Lainnya (Longsor,
                Kekeringan)'."""
                items = []
                for tp in sorted(df_kab["tipe_bencana"].unique()):
                    if tp == "Bencana Alam Lainnya" and "penyebab" in df_kab.columns:
                        sub = (df_kab[df_kab["tipe_bencana"] == tp]["penyebab"]
                               .dropna().astype(str).unique().tolist())
                        sub = [s for s in sub if s and s.lower() != "tidak diketahui"]
                        if sub:
                            items.append(f"{tp} ({', '.join(sorted(set(sub)))})")
                            continue
                    items.append(tp)
                return ", ".join(items)

            jenis_kab = (d.groupby("kabupaten")
                         .apply(_jenis_lengkap).reset_index(name="jenis_bencana"))
            aggs = {"kejadian": ("tipe_bencana", "size"), "luas_ha": ("luas_ha", "sum"),
                    "korban_jiwa": ("korban_jiwa", "sum"), "pengungsi": ("pengungsi", "sum"),
                    "ispa": ("ispa", "sum")}
            if "luas_padam_ha" in d.columns:
                aggs["luas_padam_ha"] = ("luas_padam_ha", "sum")
            if "rumah_terdampak" in d.columns:
                aggs["rumah_terdampak"] = ("rumah_terdampak", "sum")
            gk = (d.groupby("kabupaten").agg(**aggs).reset_index()
                  .merge(jenis_kab, on="kabupaten")
                  .sort_values("kejadian", ascending=False))
            if "luas_padam_ha" in gk.columns and "luas_ha" in gk.columns:
                gk["luas_belum_padam_ha"] = (gk["luas_ha"] - gk["luas_padam_ha"]).clip(lower=0)
            # susun ulang kolom
            cols_order = ["kabupaten", "jenis_bencana", "kejadian", "luas_ha", "luas_padam_ha",
                          "luas_belum_padam_ha", "korban_jiwa", "pengungsi", "ispa", "rumah_terdampak"]
            gk = gk[[c for c in cols_order if c in gk.columns]]
            for c in ["korban_jiwa", "pengungsi", "ispa", "rumah_terdampak"]:
                if c in gk.columns:
                    gk[c] = gk[c].fillna(0).astype(int)
            if tipe in ("Banjir", "Gempa", "Bencana Alam Lainnya"):
                for c in ["luas_ha", "luas_padam_ha", "luas_belum_padam_ha", "ispa"]:
                    if c in gk.columns:
                        gk = gk.drop(columns=c)
            for c in ["luas_ha", "luas_padam_ha", "luas_belum_padam_ha", "ispa", "rumah_terdampak"]:
                if c in gk.columns and gk[c].sum() == 0:
                    gk = gk.drop(columns=c)
            show_df(gk, column_config={
                "kabupaten": "Kabupaten/Kota",
                "jenis_bencana": st.column_config.TextColumn("Jenis Bencana", width="medium"),
                "kejadian": "Kejadian",
                "luas_ha": st.column_config.NumberColumn("Luas Terbakar (ha)", format="%.1f"),
                "luas_padam_ha": st.column_config.NumberColumn("Sudah Padam (ha)", format="%.1f"),
                "luas_belum_padam_ha": st.column_config.NumberColumn("Belum Padam (ha)", format="%.1f"),
                "korban_jiwa": "Korban Jiwa", "pengungsi": "Pengungsi",
                "ispa": "ISPA", "rumah_terdampak": "Rumah Terdampak",
            })

# ====================================================================== LAPORAN
elif page == "Laporan":
    kpi_row()
    st.write("")

    # Data basis "wilayah+periode saja" (tanpa filter tipe), supaya tiap tombol per-jenis
    # bisa ambil subset tipe sendiri.
    inc_wilayah = inc_all[inc_all["provinsi"].isin(prov_list)] if prov_list else inc_all
    cur_all, prev_all = split_periode(inc_wilayah, end_date, days)
    daftar_prov = prov_list or list(PROVINSI)
    jenis_available = [t for t in ["Karhutla", "Banjir", "Gempa", "Bencana Alam Lainnya"]
                       if t in set(cur_all["tipe_bencana"])] if not cur_all.empty else []

    def _build_ctx(jenis_laporan):
        """Bangun ctx laporan untuk satu jenis (atau 'Semua'='Gabungan')."""
        if jenis_laporan == "Semua":
            cur_j, prev_j = cur_all, prev_all
        else:
            cur_j = cur_all[cur_all["tipe_bencana"] == jenis_laporan]
            prev_j = prev_all[prev_all["tipe_bencana"] == jenis_laporan] if prev_all is not None else None

        per_tipe_j = agg_tipe(cur_j)
        per_prov_j = agg_prov(cur_j)
        # Urutan GEOGRAFIS (Aceh→Lampung lalu Kalimantan) sesuai PROVINSI dict
        urutan_prov = {p: i for i, p in enumerate(PROVINSI)}
        per_prov_full_j = (per_prov_j.set_index("provinsi")
                           .reindex(daftar_prov).fillna(0).reset_index())
        per_prov_full_j["_ord"] = per_prov_full_j["provinsi"].map(urutan_prov).fillna(999)
        per_prov_full_j = (per_prov_full_j.sort_values("_ord").drop(columns="_ord")
                           .reset_index(drop=True))
        for c in ["kejadian", "korban_jiwa", "pengungsi", "ispa", "rumah_terdampak"]:
            if c in per_prov_full_j.columns:
                per_prov_full_j[c] = per_prov_full_j[c].astype(int)

        prov_per_jenis_j = {}
        for tp, g in cur_j.groupby("tipe_bencana"):
            top_g = (g.groupby("provinsi").size().reset_index(name="kejadian")
                     .sort_values("kejadian", ascending=False).head(3))
            prov_per_jenis_j[tp] = top_g

        # KPI versi laporan — pakai aturan dinamis seperti kpi_values() tetapi untuk cur_j
        def tot(df, col):
            if df is None or df.empty or col not in df.columns:
                return 0.0
            return float(pd.to_numeric(df[col], errors="coerce").sum(skipna=True))

        def mx(df, col):
            if df is None or df.empty or col not in df.columns:
                return 0.0
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            return float(s.max()) if len(s) else 0.0

        if jenis_laporan == "Banjir":
            kpis_j = [("Jumlah Kejadian", len(cur_j), len(prev_j) if prev_j is not None else None, 0, ""),
                      ("Rumah Terdampak", tot(cur_j, "rumah_terdampak"),
                       tot(prev_j, "rumah_terdampak") if prev_j is not None else None, 0, "unit"),
                      ("Tinggi Genangan Maks", mx(cur_j, "tinggi_genangan_cm"),
                       mx(prev_j, "tinggi_genangan_cm") if prev_j is not None else None, 0, "cm"),
                      ("Korban Jiwa", tot(cur_j, "korban_jiwa"),
                       tot(prev_j, "korban_jiwa") if prev_j is not None else None, 0, "jiwa")]
        elif jenis_laporan == "Gempa":
            kpis_j = [("Jumlah Kejadian", len(cur_j), len(prev_j) if prev_j is not None else None, 0, ""),
                      ("Magnitudo Maks", mx(cur_j, "magnitudo"),
                       mx(prev_j, "magnitudo") if prev_j is not None else None, 1, "SR"),
                      ("Rumah Terdampak", tot(cur_j, "rumah_terdampak"),
                       tot(prev_j, "rumah_terdampak") if prev_j is not None else None, 0, "unit"),
                      ("Korban Jiwa", tot(cur_j, "korban_jiwa"),
                       tot(prev_j, "korban_jiwa") if prev_j is not None else None, 0, "jiwa")]
        elif jenis_laporan == "Bencana Alam Lainnya":
            kpis_j = [("Jumlah Kejadian", len(cur_j), len(prev_j) if prev_j is not None else None, 0, ""),
                      ("Rumah Terdampak", tot(cur_j, "rumah_terdampak"),
                       tot(prev_j, "rumah_terdampak") if prev_j is not None else None, 0, "unit"),
                      ("Pengungsi", tot(cur_j, "pengungsi"),
                       tot(prev_j, "pengungsi") if prev_j is not None else None, 0, "orang"),
                      ("Korban Jiwa", tot(cur_j, "korban_jiwa"),
                       tot(prev_j, "korban_jiwa") if prev_j is not None else None, 0, "jiwa")]
        else:  # Semua & Karhutla
            kpis_j = [("Jumlah Kejadian", len(cur_j), len(prev_j) if prev_j is not None else None, 0, ""),
                      ("Luas Terdampak", tot(cur_j, "luas_ha"),
                       tot(prev_j, "luas_ha") if prev_j is not None else None, 1, "ha"),
                      ("Korban Jiwa", tot(cur_j, "korban_jiwa"),
                       tot(prev_j, "korban_jiwa") if prev_j is not None else None, 0, "jiwa"),
                      ("Dampak (ISPA)", tot(cur_j, "ispa"),
                       tot(prev_j, "ispa") if prev_j is not None else None, 0, "kasus")]
        kpi_rows_j = []
        for label, v, pv, dg, unit in kpis_j:
            dlt = delta_pct(v, pv)
            kpi_rows_j.append([label, f"{fmt_num(v, dg)} {unit}".strip(),
                               "-" if dlt is None else (f"{'naik' if dlt > 0 else 'turun'} {fmt_num(abs(dlt), 1)}%"
                                                        if abs(dlt) >= 0.05 else "tetap")])

        # Narasi + perhatian per-jenis
        narasi_j, perhatian_j = _ringkasan_untuk(cur_j, prev_j, jenis_laporan,
                                                 hs_today if jenis_laporan in ("Semua", "Karhutla") else None,
                                                 hs_prevday if jenis_laporan in ("Semua", "Karhutla") else None,
                                                 hs_end if jenis_laporan in ("Semua", "Karhutla") else None,
                                                 wil_label)

        # Hotspot full (semua 15 provinsi) untuk Semua/Karhutla
        hotspot_full_j = None
        top_h_j = None
        if jenis_laporan in ("Semua", "Karhutla") and hs_today is not None and not hs_today.empty:
            hotspot_full_j = (hs_today.groupby("provinsi").size().reset_index(name="hotspot")
                              .set_index("provinsi").reindex(daftar_prov).fillna(0).astype({"hotspot": int})
                              .reset_index().sort_values("hotspot", ascending=False).reset_index(drop=True))
            top_h_j = top_hotspot_df(hs_today)

        return {"periode": periode, "wilayah": wil_label, "jenis": jenis_laporan,
                "data_per": tgl_id(end_date, True), "kpi": kpi_rows_j,
                "narasi": narasi_j, "perhatian": perhatian_j,
                "per_tipe": per_tipe_j, "per_prov": per_prov_j,
                "per_prov_full": per_prov_full_j, "prov_per_jenis": prov_per_jenis_j,
                "spesifik": metrik_spesifik(cur_j),
                "top_hotspot": top_h_j, "hotspot_full": hotspot_full_j,
                "hotspot_tgl": tgl_id(hs_end) if hs_end is not None else "",
                "pembuat": f"{user['name']} ({user['role']})", "demo": is_demo,
                # Untuk format intel brief
                "df_cur": cur_j,
                "hs_today_df": hs_today if jenis_laporan in ("Semua", "Karhutla") else None}

    tab_laporan, tab_buat = st.tabs(["📄 Unduh Laporan", "✍️ Buat Laporan dari Teks"])

    with tab_laporan:
        with st.container(border=True):
            theme.panel_title("📄 Laporan untuk Pimpinan", f"({periode.lower()} · {wil_label})")
            st.markdown(f'<div class="note"><p>{narasi}</p></div>', unsafe_allow_html=True)
            if perhatian:
                li = "".join(f"<li>{p}</li>" for p in perhatian)
                st.markdown(f'<div class="attn"><div class="h">⚠️ Perhatian</div><ul>{li}</ul></div>',
                            unsafe_allow_html=True)
            stamp = today_wib().strftime("%Y%m%d")

            st.markdown("##### Unduh Laporan Word (.docx) per Jenis Bencana")
            st.caption("Masing-masing berisi 15 provinsi lengkap. Pilih yang relevan untuk pimpinan.")

            # Baris 1: Gabungan (primary) + Karhutla
            r1 = st.columns(2)
            with r1[0]:
                st.download_button("📘 Laporan Gabungan (semua jenis)",
                                   build_docx(_build_ctx("Semua")),
                                   f"laporan_gabungan_{stamp}.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   type="primary", use_container_width=True, key="dl_gab")
            with r1[1]:
                disabled = "Karhutla" not in jenis_available
                st.download_button("🔥 Laporan Karhutla",
                                   build_docx(_build_ctx("Karhutla")) if not disabled else b"",
                                   f"laporan_karhutla_{stamp}.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   use_container_width=True, disabled=disabled, key="dl_kar")

            # Baris 2: Banjir + Gempa + Lainnya
            r2 = st.columns(3)
            with r2[0]:
                disabled = "Banjir" not in jenis_available
                st.download_button("🌊 Laporan Banjir",
                                   build_docx(_build_ctx("Banjir")) if not disabled else b"",
                                   f"laporan_banjir_{stamp}.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   use_container_width=True, disabled=disabled, key="dl_ban")
            with r2[1]:
                disabled = "Gempa" not in jenis_available
                st.download_button("🌋 Laporan Gempa",
                                   build_docx(_build_ctx("Gempa")) if not disabled else b"",
                                   f"laporan_gempa_{stamp}.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   use_container_width=True, disabled=disabled, key="dl_gem")
            with r2[2]:
                disabled = "Bencana Alam Lainnya" not in jenis_available
                st.download_button("🌪️ Laporan Bencana Lainnya",
                                   build_docx(_build_ctx("Bencana Alam Lainnya")) if not disabled else b"",
                                   f"laporan_bencana_lainnya_{stamp}.docx",
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                   use_container_width=True, disabled=disabled, key="dl_lain")

            st.markdown("---")
            st.markdown("##### Unduhan lain (Excel & Data mentah)")
            per_tipe_all = agg_tipe(cur_all)
            per_prov_all = agg_prov(cur_all)
            # Urut geografis (Aceh→Lampung→Kalimantan) sesuai PROVINSI dict
            urutan_prov_all = {p: i for i, p in enumerate(PROVINSI)}
            per_prov_full_all = (per_prov_all.set_index("provinsi")
                                 .reindex(daftar_prov).fillna(0).reset_index())
            per_prov_full_all["_ord"] = per_prov_full_all["provinsi"].map(urutan_prov_all).fillna(999)
            per_prov_full_all = (per_prov_full_all.sort_values("_ord").drop(columns="_ord")
                                 .reset_index(drop=True))
            sheets = {"Rekap Provinsi (15)": per_prov_full_all, "Rekap Jenis": per_tipe_all}
            if is_admin():
                sheets = {"Data Kejadian": bersihkan(cur_all), **sheets}
                if hs_period is not None:
                    sheets["Hotspot"] = bersihkan(hs_period.assign(tanggal=hs_period["tanggal"]))
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("📊 Rekap Lengkap (Excel .xlsx)", build_xlsx(sheets),
                                   f"rekap_kebencanaan_{stamp}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            with c2:
                if is_admin():
                    st.download_button("📁 Data mentah (CSV)",
                                       bersihkan(cur_all).to_csv(index=False).encode("utf-8"),
                                       f"data_kejadian_{stamp}.csv", "text/csv",
                                       use_container_width=True)
                else:
                    st.caption("Data mentah hanya dapat diunduh Admin.")

    with tab_buat:
        from laporan_teks import render_tab_buat_laporan  # noqa: WPS433
        render_tab_buat_laporan(user, is_admin())

st.divider()
st.caption("Dashboard Kebencanaan · Direktorat 2.3 Deputi 2 BIN · Wilayah Sumatera & Kalimantan")
