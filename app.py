# -*- coding: utf-8 -*-
"""Dashboard Karhutla - Optimalisasi Sinkronisasi Data Pusat & Daerah (Streamlit)."""
import io
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_generator import generate_all, PROVINSI

# ---------------------------------------------------------------- configurations
st.set_page_config(
    page_title="Dashboard Karhutla - Sinkronisasi Pusat & Daerah",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

SEVERITY_COLOR = {
    "Ringan": "#9ae6b4", "Sedang": "#f6e05e",
    "Berat": "#f6ad55", "Sangat Berat": "#fc8181",
}
STATUS_COLOR = {
    "Sinkron": "#48bb78",
    "Sinkron (angka OK, penyebab beda)": "#68d391",
    "Mismatch (angka beda)": "#ed8936",
    "MISS - Daerah tidak melapor": "#f56565",
    "Ekstra - Laporan daerah tanpa pusat": "#a0aec0",
}

# ---------------------------------------------------------------- helpers
def fmt_num(x, digits=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"{x:,.{digits}f}".replace(",", ".")


def load_uploaded(uploaded_file):
    try:
        if uploaded_file.name.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file)
        return pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None


def normalize_df(df):
    """Normalisasi kolom minimal yang diperlukan."""
    df = df.copy()
    # tanggal
    for c in ["tanggal", "date", "tgl"]:
        if c in df.columns:
            df["tanggal"] = pd.to_datetime(df[c], errors="coerce")
            break
    if "tanggal" not in df.columns:
        df["tanggal"] = pd.NaT
    # provinsi
    if "provinsi" not in df.columns:
        for c in ["province", "propinsi"]:
            if c in df.columns:
                df = df.rename(columns={c: "provinsi"})
    # kabupaten
    if "kabupaten" not in df.columns:
        for c in ["kab", "kota", "kab_kota"]:
            if c in df.columns:
                df = df.rename(columns={c: "kabupaten"})
    # luas
    if "luas_ha" not in df.columns:
        for c in ["luas", "area_ha", "luasan"]:
            if c in df.columns:
                df = df.rename(columns={c: "luas_ha"})
    if "luas_ha" in df.columns:
        df["luas_ha"] = pd.to_numeric(df["luas_ha"], errors="coerce")
    # lat/lon
    if "lat" not in df.columns:
        for c in ["latitude", "lintang"]:
            if c in df.columns:
                df = df.rename(columns={c: "lat"})
    if "lon" not in df.columns:
        for c in ["longitude", "bujur", "lng", "long"]:
            if c in df.columns:
                df = df.rename(columns={c: "lon"})
    # penyebab
    if "penyebab" not in df.columns and "cause" in df.columns:
        df = df.rename(columns={"cause": "penyebab"})
    # severity
    if "severity" not in df.columns and "tingkat" in df.columns:
        df = df.rename(columns={"tingkat": "severity"})
    # id
    if "id_laporan" not in df.columns:
        df["id_laporan"] = [f"UP-{i:06d}" for i in range(len(df))]
    return df


@st.cache_data(show_spinner=False)
def get_default_data(seed=42, drop_rate=0.12, mismatch_rate=0.15, extra_rate=0.08):
    return generate_all(seed, drop_rate=drop_rate, mismatch_rate=mismatch_rate,
                       extra_rate=extra_rate)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Lambang_Badan_Intelijen_Negara.svg/200px-Lambang_Badan_Intelijen_Negara.svg.png",
             width=80)
    st.title("🔥 Dashboard Karhutla")
    st.caption("Optimalisasi Sinkronisasi Data Pusat & Daerah")
    st.divider()

    data_source = st.radio(
        "Sumber data",
        ["Data Sintetis (Demo)", "Upload CSV/Excel (Pusat)", "Upload keduanya (Pusat & Daerah)"],
        index=0,
    )

    seed = 42
    if data_source == "Data Sintetis (Demo)":
        seed = st.slider("Seed data sintetis", 1, 999, 42)
        drop_rate = st.slider("Simulasi miss daerah (%)", 0, 40, 12) / 100
        mismatch_rate = st.slider("Simulasi mismatch (%)", 0, 40, 15) / 100
    else:
        drop_rate = None
        mismatch_rate = None

    st.divider()
    st.subheader("Filter")
    provinsi_filter = None
    date_range = None


# ---------------------------------------------------------------- load data
if data_source == "Data Sintetis (Demo)":
    pusat_raw, daerah_raw, recon_raw = get_default_data(seed, drop_rate, mismatch_rate)
    # re-simulate drop/mismatch tidak diperlukan untuk demo fixed generator
    # (generator sudah pakai seed default params); tetap tampilkan
    pusat_df = pusat_raw.copy()
    daerah_df = daerah_raw.copy()
    recon_df = recon_raw.copy()
else:
    st.sidebar.subheader("Upload data Pusat")
    pusat_file = st.sidebar.file_uploader("File Pusat", type=["csv", "xlsx", "xls"], key="pusat")
    pusat_df = None
    daerah_df = None
    recon_df = None
    if pusat_file is not None:
        tmp = load_uploaded(pusat_file)
        if tmp is not None:
            pusat_df = normalize_df(tmp)
            if data_source == "Upload CSV/Excel (Pusat)":
                # tanpa daerah -> daerah = None, recon tidak tersedia
                pass
    if data_source == "Upload keduanya (Pusat & Daerah)":
        st.sidebar.subheader("Upload data Daerah")
        daerah_file = st.sidebar.file_uploader("File Daerah", type=["csv", "xlsx", "xls"], key="daerah")
        if daerah_file is not None:
            tmp = load_uploaded(daerah_file)
            if tmp is not None:
                daerah_df = normalize_df(tmp)
        if pusat_df is not None and daerah_df is not None:
            from data_generator import reconcile
            # ensure tanggal datetime
            pusat_df["tanggal"] = pd.to_datetime(pusat_df["tanggal"], errors="coerce")
            daerah_df["tanggal"] = pd.to_datetime(daerah_df["tanggal"], errors="coerce")
            recon_df = reconcile(pusat_df, daerah_df)


# fallback: jika belum ada data pusat
if pusat_df is None:
    st.info("Silakan upload file data Pusat terlebih dahulu, atau pilih mode Data Sintetis (Demo).")
    st.stop()

pusat_df["tanggal"] = pd.to_datetime(pusat_df["tanggal"], errors="coerce")
if daerah_df is not None:
    daerah_df["tanggal"] = pd.to_datetime(daerah_df["tanggal"], errors="coerce")
if recon_df is not None:
    recon_df["tanggal"] = pd.to_datetime(recon_df["tanggal"], errors="coerce")

# ---------------------------------------------------------------- sidebar filters (isi setelah data load)
with st.sidebar:
    all_provs = sorted(pusat_df["provinsi"].dropna().unique().tolist())
    prov_sel = st.multiselect("Provinsi", all_provs, default=[])
    valid_dates = pusat_df["tanggal"].dropna()
    if len(valid_dates) > 0:
        dmin = valid_dates.min().date()
        dmax = valid_dates.max().date()
    else:
        dmin = date(2025, 1, 1); dmax = date(2025, 12, 31)
    dr = st.date_input("Rentang tanggal", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    if not isinstance(dr, (tuple, list)):
        dr = (dr, dr)
    st.divider()
    st.caption("Deputi 2 - Laporan Aktualisasi")

# apply filters
mask_p = pd.Series(True, index=pusat_df.index)
if prov_sel:
    mask_p &= pusat_df["provinsi"].isin(prov_sel)
if isinstance(dr, (tuple, list)) and len(dr) == 2:
    start_d, end_d = dr
    mask_p &= pusat_df["tanggal"].between(pd.Timestamp(start_d), pd.Timestamp(end_d))
pusat_f = pusat_df[mask_p].copy()

if daerah_df is not None:
    mask_d = pd.Series(True, index=daerah_df.index)
    if prov_sel:
        mask_d &= daerah_df["provinsi"].isin(prov_sel)
    if isinstance(dr, (tuple, list)) and len(dr) == 2:
        mask_d &= daerah_df["tanggal"].between(pd.Timestamp(start_d), pd.Timestamp(end_d))
    daerah_f = daerah_df[mask_d].copy()
else:
    daerah_f = None

if recon_df is not None:
    mask_r = pd.Series(True, index=recon_df.index)
    if prov_sel:
        mask_r &= recon_df["provinsi"].isin(prov_sel)
    if isinstance(dr, (tuple, list)) and len(dr) == 2:
        mask_r &= recon_df["tanggal"].between(pd.Timestamp(start_d), pd.Timestamp(end_d))
    recon_f = recon_df[mask_r].copy()
else:
    recon_f = None

# ---------------------------------------------------------------- header
st.title("🔥 Dashboard Kebakaran Hutan dan Lahan (Karhutla)")
st.markdown(
    "**Optimalisasi Sinkronisasi Data Pusat dan Daerah** — monitoring akurasi & efektivitas "
    "penyusunan laporan bencana alam/karhutla, meminimalisir miss data."
)

# ---------------------------------------------------------------- KPIs
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total Kejadian (Pusat)", f"{len(pusat_f):,}".replace(",", "."))
with col2:
    st.metric("Total Luas (ha)", fmt_num(pusat_f["luas_ha"].sum() if "luas_ha" in pusat_f else 0, 1))
with col3:
    st.metric("Provinsi Terdampak", pusat_f["provinsi"].nunique() if "provinsi" in pusat_f else 0)
with col4:
    st.metric("Kabupaten Terdampak", pusat_f["kabupaten"].nunique() if "kabupaten" in pusat_f else 0)
with col5:
    avg = pusat_f["luas_ha"].mean() if "luas_ha" in pusat_f else 0
    st.metric("Rata-rata Luas (ha)", fmt_num(avg, 2))
with col6:
    miss_count = 0
    if recon_f is not None:
        miss_count = (recon_f["status"] == "MISS - Daerah tidak melapor").sum()
    st.metric("Miss Data (Daerah)", int(miss_count))

if recon_f is not None:
    total_keys = len(recon_f)
    n_sinkron = (recon_f["status"].str.startswith("Sinkron")).sum()
    n_miss = (recon_f["status"] == "MISS - Daerah tidak melapor").sum()
    n_mismatch = (recon_f["status"] == "Mismatch (angka beda)").sum()
    n_extra = (recon_f["status"] == "Ekstra - Laporan daerah tanpa pusat").sum()
    sync_rate = (n_sinkron / total_keys * 100) if total_keys else 0

    st.subheader("Indikator Sinkronisasi Pusat–Daerah")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Key Rekonsiliasi", f"{total_keys:,}".replace(",", "."))
    c2.metric("Sinkron", f"{n_sinkron}", delta=f"{sync_rate:.1f}%")
    c3.metric("Mismatch", f"{n_mismatch}", delta_color="inverse")
    c4.metric("Miss (Daerah)", f"{n_miss}", delta_color="inverse")
    c5.metric("Ekstra (Daerah)", f"{n_extra}", delta_color="inverse")

    # progress bar sinkronisasi
    st.progress(min(sync_rate / 100, 1.0), text=f"Tingkat Sinkronisasi: {sync_rate:.1f}%")

# ---------------------------------------------------------------- Tabs
tabs = st.tabs(["🗺️ Peta", "📊 Analisis", "🔄 Sinkronisasi", "📈 Tren Waktu", "📋 Data & Kualitas", "⬇️ Export"])

# ---------------- Tab Peta
with tabs[0]:
    st.subheader("Peta Persebaran Karhutla")
    colA, colB = st.columns([3, 1])
    with colA:
        df_map = pusat_f.copy()
        if not df_map.empty and "lat" in df_map and "lon" in df_map:
            size_col = "luas_ha" if "luas_ha" in df_map else None
            color_col = "severity" if "severity" in df_map else None
            fig = px.scatter_geo(
                df_map, lat="lat", lon="lon",
                size=size_col, color=color_col,
                hover_name="kabupaten" if "kabupaten" in df_map else None,
                hover_data={"provinsi": True, "luas_ha": True, "tanggal": True, "penyebab": True},
                color_discrete_map=SEVERITY_COLOR,
                size_max=40,
                projection="natural earth",
            )
            # zoom ke Indonesia
            fig.update_geos(center=dict(lat=-2, lon=118), projection_scale=4.5,
                            showland=True, landcolor="#e8e8e8",
                            showocean=True, oceancolor="#dbeafe",
                            showcountries=True, countrycolor="#999")
            fig.update_layout(height=560, margin=dict(l=0, r=0, t=20, b=0),
                              legend_title="Severity")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Data tidak memiliki kolom latitude/longitude.")
    with colB:
        st.markdown("**Rekap per Provinsi**")
        if "provinsi" in pusat_f:
            g = pusat_f.groupby("provinsi").agg(kejadian=("id_laporan", "count"),
                                               luas=("luas_ha", "sum")).reset_index()
            g = g.sort_values("luas", ascending=False).head(12)
            st.dataframe(g, use_container_width=True, hide_index=True)

# ---------------- Tab Analisis
with tabs[1]:
    st.subheader("Analisis Karhutla")
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        if "provinsi" in pusat_f:
            g = pusat_f.groupby("provinsi").size().reset_index(name="kejadian").sort_values("kejadian", ascending=True)
            fig = px.bar(g, x="kejadian", y="provinsi", orientation="h",
                         title="Jumlah Kejadian per Provinsi", color="kejadian",
                         color_continuous_scale="Reds")
            fig.update_layout(height=420, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with r1c2:
        if "penyebab" in pusat_f:
            g = pusat_f.groupby("penyebab").size().reset_index(name="kejadian")
            fig = px.pie(g, values="kejadian", names="penyebab", title="Penyebab Karhutla",
                         hole=0.45, color_discrete_sequence=px.colors.sequential.Reds_r)
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        if "severity" in pusat_f:
            g = pusat_f.groupby("severity").size().reset_index(name="kejadian")
            fig = px.bar(g, x="severity", y="kejadian", title="Distribusi Severity",
                         color="severity", color_discrete_map=SEVERITY_COLOR)
            fig.update_layout(height=360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with r2c2:
        if "luas_ha" in pusat_f:
            fig = px.histogram(pusat_f, x="luas_ha", nbins=40, title="Distribusi Luas Lahan (ha)",
                               color_discrete_sequence=["#dd6b20"])
            fig.update_layout(height=360)
            st.plotly_chart(fig, use_container_width=True)

# ---------------- Tab Sinkronisasi
with tabs[2]:
    st.subheader("Rekonsiliasi & Sinkronisasi Pusat–Daerah")
    if recon_f is None:
        st.warning("Sinkronisasi memerlukan data Pusat dan Daerah. Pilih mode upload keduanya atau data sintetis.")
    else:
        # status distribution
        c1, c2 = st.columns([1, 2])
        with c1:
            g = recon_f["status"].value_counts().reset_index()
            g.columns = ["status", "jumlah"]
            fig = px.pie(g, values="jumlah", names="status", title="Status Rekonsiliasi",
                         color="status", color_discrete_map=STATUS_COLOR, hole=0.4)
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            # mismatch per provinsi stacked
            g2 = recon_f.groupby(["provinsi", "status"]).size().reset_index(name="jumlah")
            fig = px.bar(g2, x="provinsi", y="jumlah", color="status",
                         color_discrete_map=STATUS_COLOR,
                         title="Status Rekonsiliasi per Provinsi",
                         barmode="stack")
            fig.update_layout(height=380, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Daftar Miss Data (Daerah tidak melapor)")
        miss_df = recon_f[recon_f["status"] == "MISS - Daerah tidak melapor"]
        if miss_df.empty:
            st.success("Tidak ada miss data pada filter ini. 🎉")
        else:
            show_cols = ["tanggal", "provinsi", "kabupaten", "luas_pusat", "penyebab_pusat", "severity_pusat"]
            st.dataframe(miss_df[show_cols].sort_values("tanggal"), use_container_width=True, hide_index=True)
            st.caption(f"Total miss: {len(miss_df)} kejadian.")

        st.markdown("#### Daftar Mismatch (angka berbeda)")
        mm_df = recon_f[recon_f["status"] == "Mismatch (angka beda)"]
        if mm_df.empty:
            st.success("Tidak ada mismatch angka.")
        else:
            show_cols = ["tanggal", "provinsi", "kabupaten", "luas_pusat", "luas_daerah", "selisih_ha",
                         "penyebab_pusat", "penyebab_daerah"]
            st.dataframe(mm_df[show_cols].sort_values("selisih_ha", key=lambda s: s.abs(), ascending=False),
                         use_container_width=True, hide_index=True)

        st.markdown("#### Laporan Ekstra Daerah (tanpa data pusat)")
        ex_df = recon_f[recon_f["status"] == "Ekstra - Laporan daerah tanpa pusat"]
        if not ex_df.empty:
            show_cols = ["tanggal", "provinsi", "kabupaten", "luas_daerah", "penyebab_daerah"]
            st.dataframe(ex_df[show_cols].sort_values("tanggal"), use_container_width=True, hide_index=True)

# ---------------- Tab Tren Waktu
with tabs[3]:
    st.subheader("Tren Waktu Karhutla")
    if "tanggal" in pusat_f and pusat_f["tanggal"].notna().any():
        ts = pusat_f.copy()
        ts["bulan"] = ts["tanggal"].dt.to_period("M").astype(str)
        g = ts.groupby("bulan").agg(kejadian=("id_laporan", "count"), luas=("luas_ha", "sum")).reset_index()
        g = g.sort_values("bulan")
        fig = px.line(g, x="bulan", y=["kejadian", "luas"], title="Tren Kejadian & Luas per Bulan",
                      markers=True)
        fig.update_layout(height=420, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # mingguan
        ts2 = pusat_f.copy()
        ts2["minggu"] = ts2["tanggal"].dt.to_period("W").astype(str)
        g2 = ts2.groupby("minggu").size().reset_index(name="kejadian").sort_values("minggu")
        fig2 = px.area(g2, x="minggu", y="kejadian", title="Tren Kejadian Mingguan", color_discrete_sequence=["#e53e3e"])
        fig2.update_layout(height=360, xaxis_tickangle=-60)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Kolom tanggal tidak tersedia.")

# ---------------- Tab Data & Kualitas
with tabs[4]:
    st.subheader("Data & Kualitas Data")
    st.markdown("**Pusat**")
    st.dataframe(pusat_f, use_container_width=True, height=260)
    if daerah_df is not None:
        st.markdown("**Daerah (filter)**")
        st.dataframe(daerah_f, use_container_width=True, height=260)

    st.markdown("#### Profil Kualitas Data")
    q_rows = []
    for name, df_ in [("Pusat", pusat_f), ("Daerah", daerah_f if daerah_f is not None else pd.DataFrame())]:
        if df_.empty:
            continue
        q_rows.append({
            "Sumber": name,
            "Jumlah Record": len(df_),
            "Kolom": len(df_.columns),
            "Missing Values (seluruh sel)": int(df_.isna().sum().sum()),
            "% Missing": round(df_.isna().sum().sum() / max(df_.size, 1) * 100, 2),
            "Duplikat (key)": int(df_.duplicated(subset=["provinsi", "kabupaten", "tanggal"]).sum()) if "provinsi" in df_ else 0,
            "Tanpa Koordinat": int(df_[["lat", "lon"]].isna().any(axis=1).sum()) if all(c in df_ for c in ["lat", "lon"]) else 0,
        })
    st.dataframe(pd.DataFrame(q_rows), use_container_width=True, hide_index=True)

    # top wilayah miss
    if recon_f is not None:
        st.markdown("#### Top Provinsi dengan Miss Data Terbanyak")
        mg = recon_f[recon_f["status"] == "MISS - Daerah tidak melapor"].groupby("provinsi").size().reset_index(name="miss")
        if not mg.empty:
            mg = mg.sort_values("miss", ascending=False).head(10)
            fig = px.bar(mg, x="provinsi", y="miss", title="Miss Data per Provinsi", color="miss",
                         color_continuous_scale="Reds")
            fig.update_layout(height=360, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

# ---------------- Tab Export
with tabs[5]:
    st.subheader("Export Laporan Rekonsiliasi")
    if recon_f is None:
        st.info("Memerlukan data rekonsiliasi.")
    else:
        # pilihan format
        export_df = recon_f.copy()
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Rekonsiliasi (CSV)", csv_bytes,
                           file_name="rekonsiliasi_karhutla.csv", mime="text/csv")
        # excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            export_df.to_excel(w, index=False, sheet_name="Rekonsiliasi")
            pusat_f.to_excel(w, index=False, sheet_name="Pusat")
            if daerah_f is not None:
                daerah_f.to_excel(w, index=False, sheet_name="Daerah")
            # summary per provinsi
            if "provinsi" in pusat_f:
                summ = pusat_f.groupby("provinsi").agg(
                    kejadian=("id_laporan", "count"), luas_ha=("luas_ha", "sum")).reset_index()
                summ.to_excel(w, index=False, sheet_name="Rekap Provinsi")
        st.download_button("⬇️ Download Laporan Lengkap (Excel)", buf.getvalue(),
                           file_name="laporan_karhutla.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.success("File siap diunduh. Gunakan untuk laporan aktualisasi / lampiran.")

st.divider()
st.caption("Dashboard Karhutla — Deputi 2 BIN | Latsar Aktualisasi | Sumber data: sistim Pusat & Daerah (sintetis untuk demo)")
