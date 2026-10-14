# -*- coding: utf-8 -*-
"""Dashboard Bencana Alam - Direktorat 2.3 (BIN Deputi 2) - Sumatera & Kalimantan."""
import io
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from data_generator import generate_all, PROVINSI, TIPE_BENCANA

st.set_page_config(
    page_title="Dashboard Bencana Alam - Dir 2.3 BIN",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- tema biru
st.markdown("""
<style>
:root { --bin-blue: #1e3a8a; --bin-blue2: #2563eb; }
.stApp { background: linear-gradient(180deg, #f0f6ff 0%, #ffffff 60%); }
div[data-testid="stMetric"] {
  background: #ffffff; border: 1px solid #bfdbfe; border-radius: 12px;
  padding: 10px 12px; box-shadow: 0 2px 8px rgba(30,58,138,0.06);
}
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%); color: #ffffff; }
section[data-testid="stSidebar"] * { color: #ffffff !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stDateInput label,
section[data-testid="stSidebar"] .stRadio label { color: #ffffff !important; }
h1, h2, h3 { color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

TIPE_COLOR = {"Karhutla": "#dc2626", "Banjir": "#2563eb", "Gempa": "#7c3aed", "Bencana Alam Lainnya": "#0891b2"}

# ---------------------------------------------------------------- helper
def fmt_num(x, digits=0):
    if x is None or (isinstance(x, float) and (np.isnan(x))):
        return "-"
    return f"{x:,.{digits}f}".replace(",", ".")


def load_uploaded(f):
    try:
        if f.name.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(f)
        return pd.read_csv(f)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None


def normalize_df(df):
    df = df.copy()
    for c in ["tanggal", "date", "tgl", "date_time"]:
        if c in df.columns:
            df["tanggal"] = pd.to_datetime(df[c], errors="coerce")
            break
    if "tanggal" not in df.columns:
        df["tanggal"] = pd.NaT
    if "provinsi" not in df.columns:
        for c in ["province", "propinsi", "prov"]:
            if c in df.columns:
                df = df.rename(columns={c: "provinsi"})
    if "kabupaten" not in df.columns:
        for c in ["kab", "kota", "kab_kota", "kabupaten_kota"]:
            if c in df.columns:
                df = df.rename(columns={c: "kabupaten"})
    if "tipe_bencana" not in df.columns:
        for c in ["tipe", "jenis", "jenis_bencana", "type", "disaster_type"]:
            if c in df.columns:
                df = df.rename(columns={c: "tipe_bencana"})
    if "tipe_bencana" not in df.columns:
        df["tipe_bencana"] = "Bencana Alam Lainnya"
    if "luas_ha" not in df.columns:
        for c in ["luas", "area_ha", "luasan", "luas_terdampak", "luas_terdampak_ha", "affected_area"]:
            if c in df.columns:
                df = df.rename(columns={c: "luas_ha"})
    if "luas_ha" in df.columns:
        df["luas_ha"] = pd.to_numeric(df["luas_ha"], errors="coerce")
    if "lat" not in df.columns:
        for c in ["latitude", "lintang"]:
            if c in df.columns:
                df = df.rename(columns={c: "lat"})
    if "lon" not in df.columns:
        for c in ["longitude", "bujur", "lng", "long"]:
            if c in df.columns:
                df = df.rename(columns={c: "lon"})
    # korban jiwa
    if "korban_jiwa" not in df.columns:
        for c in ["korban_meninggal", "meninggal", "dead", "fatalities", "korban"]:
            if c in df.columns:
                df = df.rename(columns={c: "korban_jiwa"})
    if "korban_jiwa" not in df.columns:
        df["korban_jiwa"] = 0
    # korban luka -> tetap dihapus dari tampilan/export, tapi simpan underlying jika ada
    if "korban_luka" not in df.columns:
        for c in ["luka", "injured", "injuries"]:
            if c in df.columns:
                df = df.rename(columns={c: "korban_luka"})
    if "korban_luka" not in df.columns:
        df["korban_luka"] = 0
    # ISPA
    if "ispa" not in df.columns:
        for c in ["ispa_cases", "ispa", "dampak_ispa", "kasus_ispa"]:
            if c in df.columns:
                df = df.rename(columns={c: "ispa"})
    if "ispa" not in df.columns:
        df["ispa"] = 0
    for c in ["korban_jiwa", "korban_luka", "ispa"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    if "pengungsi" not in df.columns:
        df["pengungsi"] = 0
    else:
        df["pengungsi"] = pd.to_numeric(df["pengungsi"], errors="coerce").fillna(0).astype(int)
    # status
    if "status_verifikasi" not in df.columns:
        df["status_verifikasi"] = "Perlu Verifikasi"
    # id (opsional, akan dibersihkan saat tampil)
    if "id_kejadian" not in df.columns:
        for c in ["id", "id_laporan", "incident_id"]:
            if c in df.columns:
                df = df.rename(columns={c: "id_kejadian"})
    if "id_kejadian" not in df.columns:
        df["id_kejadian"] = [f"B-{i:06d}" for i in range(len(df))]
    return df


def _clean_data(df):
    """Bersihkan kolom yang tidak perlu tampil/export: id, lat, lon, korban_luka, severity."""
    if df is None or df.empty:
        return df
    d = df.copy()
    drop_cols = [c for c in ["id_kejadian", "lat", "lon", "korban_luka", "severity"] if c in d.columns]
    d = d.drop(columns=drop_cols, errors="ignore")
    # urutan kolom yang rapi
    preferred = ["tanggal", "provinsi", "kabupaten", "tipe_bencana", "luas_ha",
                 "korban_jiwa", "pengungsi", "ispa", "penyebab", "status_verifikasi", "sumber"]
    cols = [c for c in preferred if c in d.columns] + [c for c in d.columns if c not in preferred]
    return d[cols]


@st.cache_data(show_spinner=False)
def get_default_data(seed=42):
    inc, hs = generate_all(seed=seed)
    return inc, hs


# ---------------------------------------------------------------- header
st.markdown("""
<div style="display:flex; align-items:center; gap:18px; padding:10px 0 6px 0;">
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Lambang_Badan_Intelijen_Negara.svg/120px-Lambang_Badan_Intelijen_Negara.svg.png" width="70"/>
  <div>
    <div style="font-size:13px; color:#1e3a8a; font-weight:600; letter-spacing:0.5px;">
      BADAN INTELIJEN NEGARA &middot; DEPUTI 2 &middot; DIREKTORAT 2.3
    </div>
    <h1 style="margin:0; color:#1e3a8a;">Dashboard Bencana Alam</h1>
    <div style="color:#334155; font-size:14px;">
      Wilayah Kerja: Sumatera &amp; Kalimantan &nbsp;|&nbsp; Monitoring Kejadian, Luas Terdampak, Korban, dan Dampak (ISPA)
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Lambang_Badan_Intelijen_Negara.svg/120px-Lambang_Badan_Intelijen_Negara.svg.png", width=70)
    st.title("🛰️ Dashboard Bencana")
    st.caption("Direktorat 2.3 - Deputi 2 BIN")
    st.divider()

    data_source = st.radio("Sumber Data", ["Data Sintetis (Demo)", "Upload CSV/Excel (Pusat)"], index=0)

    seed = 42
    if data_source == "Data Sintetis (Demo)":
        seed = st.slider("Seed Data", 1, 999, 42)

    st.divider()
    st.subheader("Filter")
    tipe_sel = None
    prov_sel = None

# ---------------------------------------------------------------- load data
if data_source == "Data Sintetis (Demo)":
    inc_raw, hs_raw = get_default_data(seed)
    pusat_df = inc_raw.copy()
    hotspot_df = hs_raw.copy()
else:
    st.sidebar.subheader("Upload Data Pusat")
    pusat_file = st.sidebar.file_uploader("File Data Pusat (Bencana)", type=["csv", "xlsx", "xls"], key="pusat")
    pusat_df = None
    hotspot_df = None
    if pusat_file is not None:
        tmp = load_uploaded(pusat_file)
        if tmp is not None:
            pusat_df = normalize_df(tmp)
            hotspot_file = st.sidebar.file_uploader("File Hotspot (opsional)", type=["csv", "xlsx", "xls"], key="hs")
            if hotspot_file is not None:
                htmp = load_uploaded(hotspot_file)
                if htmp is not None:
                    hotspot_df = normalize_df(htmp)

if pusat_df is None:
    st.info("Silakan upload file data pusat, atau pilih mode Data Sintetis (Demo).")
    st.stop()

pusat_df["tanggal"] = pd.to_datetime(pusat_df["tanggal"], errors="coerce")
if hotspot_df is not None:
    hotspot_df["tanggal"] = pd.to_datetime(hotspot_df["tanggal"], errors="coerce")

with st.sidebar:
    all_tipe = [t for t in TIPE_BENCANA if t in pusat_df["tipe_bencana"].unique()] or sorted(pusat_df["tipe_bencana"].dropna().unique().tolist())
    tipe_sel = st.multiselect("Tipe Bencana", all_tipe, default=all_tipe)
    all_provs = sorted(pusat_df["provinsi"].dropna().unique().tolist())
    prov_sel = st.multiselect("Provinsi", all_provs, default=[])
    valid_dates = pusat_df["tanggal"].dropna()
    dmin = valid_dates.min().date() if len(valid_dates) else date(2025, 1, 1)
    dmax = valid_dates.max().date() if len(valid_dates) else date(2025, 12, 31)
    dr = st.date_input("Rentang Tanggal", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    if not isinstance(dr, (tuple, list)):
        dr = (dr, dr)

mask = pd.Series(True, index=pusat_df.index)
if tipe_sel:
    mask &= pusat_df["tipe_bencana"].isin(tipe_sel)
if prov_sel:
    mask &= pusat_df["provinsi"].isin(prov_sel)
if isinstance(dr, (tuple, list)) and len(dr) == 2:
    mask &= pusat_df["tanggal"].between(pd.Timestamp(dr[0]), pd.Timestamp(dr[1]))
pusat_f = pusat_df[mask].copy()

if hotspot_df is not None:
    hmask = pd.Series(True, index=hotspot_df.index)
    if prov_sel:
        hmask &= hotspot_df["provinsi"].isin(prov_sel)
    if isinstance(dr, (tuple, list)) and len(dr) == 2:
        hmask &= hotspot_df["tanggal"].between(pd.Timestamp(dr[0]), pd.Timestamp(dr[1]))
    hotspot_f = hotspot_df[hmask].copy()
else:
    hotspot_f = None

# ---------------------------------------------------------------- KPI
st.subheader("Indikator Utama")
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Total Kejadian", fmt_num(len(pusat_f)))
with c2:
    st.metric("Total Luas Terdampak (ha)", fmt_num(pusat_f["luas_ha"].sum() if "luas_ha" in pusat_f else 0, 1))
with c3:
    st.metric("Total Korban (Jiwa)", fmt_num(pusat_f["korban_jiwa"].sum() if "korban_jiwa" in pusat_f else 0))
with c4:
    st.metric("Kasus ISPA", fmt_num(pusat_f["ispa"].sum() if "ispa" in pusat_f else 0))
with c5:
    st.metric("Provinsi Terdampak", pusat_f["provinsi"].nunique() if "provinsi" in pusat_f else 0)
with c6:
    hs_today = 0
    if hotspot_f is not None and not hotspot_f.empty:
        last_d = hotspot_f["tanggal"].max()
        hs_today = (hotspot_f["tanggal"].dt.date == last_d.date()).sum()
    st.metric("Hotspot (hari terakhir data)", fmt_num(hs_today))

tabs = st.tabs(["🗺️ Peta", "📊 Analisis", "🔥 Hotspot", "📈 Tren", "📋 Data", "⬇️ Export"])

def _display_date(df):
    d = df.copy()
    if "tanggal" in d.columns:
        d["tanggal"] = pd.to_datetime(d["tanggal"], errors="coerce").dt.strftime("%Y-%m-%d")
    return d


# ---------------- Tab Peta
with tabs[0]:
    st.subheader("Peta Kejadian Bencana (Sumatera & Kalimantan)")
    if pusat_f.empty:
        st.warning("Tidak ada data.")
    else:
        fig = px.scatter_geo(
            pusat_f, lat="lat", lon="lon",
            color="tipe_bencana", size="luas_ha",
            hover_name="kabupaten", hover_data={"provinsi": True, "tipe_bencana": True,
                                              "luas_ha": True, "tanggal": True,
                                              "korban_jiwa": True, "ispa": True},
            color_discrete_map=TIPE_COLOR, size_max=34,
            projection="natural earth",
        )
        fig.update_geos(fitbounds="locations",
                        showland=True, landcolor="#eaf2ff",
                        showocean=True, oceancolor="#f0f7ff",
                        showcountries=True, countrycolor="#94a3b8")
        fig.update_layout(height=580, margin=dict(l=0, r=0, t=20, b=0),
                          legend_title="Tipe Bencana")
        st.plotly_chart(fig, use_container_width=True)

    colA, colB = st.columns([1, 1])
    with colA:
        if "provinsi" in pusat_f:
            g = pusat_f.groupby("provinsi").size().reset_index(name="kejadian").sort_values("kejadian", ascending=False).head(15)
            g["kejadian_label"] = g["kejadian"]
            fig = px.bar(g, x="kejadian", y="provinsi", orientation="h",
                         title="Kejadian per Provinsi", color="kejadian",
                         color_continuous_scale="Blues", text="kejadian_label")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=420, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with colB:
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana").size().reset_index(name="kejadian")
            fig = px.pie(g, values="kejadian", names="tipe_bencana", title="Komposisi Tipe Bencana",
                         color="tipe_bencana", color_discrete_map=TIPE_COLOR, hole=0.45,
                         textinfo="value+percent")
            fig.update_traces(textposition="inside")
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

# ---------------- Tab Analisis
with tabs[1]:
    st.subheader("Analisis: Kejadian, Luas Terdampak, Korban, Dampak (ISPA)")
    r1, r2 = st.columns(2)
    with r1:
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana").agg(kejadian=("id_kejadian", "count") if False else ("tipe_bencana", "size"),
                                                   luas=("luas_ha", "sum")).reset_index()
            # rename count column properly
            g = pusat_f.groupby("tipe_bencana").size().reset_index(name="kejadian").merge(
                pusat_f.groupby("tipe_bencana")["luas_ha"].sum().reset_index(name="luas"), on="tipe_bencana")
            fig = px.bar(g, x="tipe_bencana", y=["kejadian", "luas"], barmode="group",
                         title="Jumlah Kejadian & Luas Terdampak per Tipe", text_auto=True)
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
    with r2:
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana")["korban_jiwa"].sum().reset_index(name="korban")
            fig = px.bar(g, x="tipe_bencana", y="korban", title="Korban (Jiwa) per Tipe Bencana",
                         color="tipe_bencana", color_discrete_map=TIPE_COLOR, text="korban")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    r3, r4 = st.columns(2)
    with r3:
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana")["ispa"].sum().reset_index(name="ispa")
            fig = px.bar(g, x="tipe_bencana", y="ispa", title="Kasus ISPA per Tipe Bencana",
                         color="tipe_bencana", color_discrete_map=TIPE_COLOR, text="ispa")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with r4:
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana").agg(luas=("luas_ha", "sum")).reset_index()
            g["luas_label"] = g["luas"].round(1)
            fig = px.bar(g, x="tipe_bencana", y="luas", title="Luas Terdampak per Tipe",
                         color="tipe_bencana", color_discrete_map=TIPE_COLOR, text="luas_label")
            fig.update_traces(textposition="outside")
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Rekap per Provinsi")
    if "provinsi" in pusat_f:
        g = pusat_f.groupby("provinsi").agg(
            kejadian=("tipe_bencana", "size"),
            luas_ha=("luas_ha", "sum"),
            korban_jiwa=("korban_jiwa", "sum"),
            ispa=("ispa", "sum"),
        ).reset_index().sort_values("kejadian", ascending=False)
        st.dataframe(g, use_container_width=True, hide_index=True)

# ---------------- Tab Hotspot
with tabs[2]:
    st.subheader("Sebaran Hotspot (Sumatera & Kalimantan)")
    if hotspot_f is None or hotspot_f.empty:
        st.warning("Data hotspot tidak tersedia. (Upload file hotspot di sidebar atau gunakan mode Sintetis.)")
    else:
        dates = sorted(hotspot_f["tanggal"].dt.date.unique().tolist(), reverse=True)
        pick = st.selectbox("Tanggal Hotspot", dates, index=0)
        hdf = hotspot_f[hotspot_f["tanggal"].dt.date == pick]
        h1, h2 = st.columns([3, 1])
        with h1:
            fig = px.scatter_geo(
                hdf, lat="lat", lon="lon", color="confidence",
                size="frp" if "frp" in hdf else None, hover_name="kabupaten",
                hover_data={"provinsi": True, "satelit": True, "frp": True, "confidence": True},
                projection="natural earth",
                color_discrete_map={"Low": "#93c5fd", "Nominal": "#2563eb", "High": "#1e3a8a"},
                text=hdf["provinsi"].str[:3] if False else None,
            )
            fig.update_geos(fitbounds="locations",
                            showland=True, landcolor="#eaf2ff", showocean=True, oceancolor="#f0f7ff",
                            showcountries=True, countrycolor="#94a3b8")
            fig.update_layout(height=520, margin=dict(l=0, r=0, t=20, b=0),
                              title=f"Hotspot {pick} (n={len(hdf)})")
            st.plotly_chart(fig, use_container_width=True)
        with h2:
            st.metric("Hotspot tgl ini", fmt_num(len(hdf)))
            if "provinsi" in hdf:
                g = hdf.groupby("provinsi").size().reset_index(name="hotspot").sort_values("hotspot", ascending=False)
                g["label"] = g["hotspot"]
                figbar = px.bar(g, x="hotspot", y="provinsi", orientation="h", text="label",
                                title="Hotspot per Provinsi", color="hotspot", color_continuous_scale="Blues")
                figbar.update_traces(textposition="outside")
                figbar.update_layout(height=320, showlegend=False)
                st.plotly_chart(figbar, use_container_width=True)
            if "confidence" in hdf:
                cg = hdf["confidence"].value_counts().reset_index()
                cg.columns = ["confidence", "jumlah"]
                fig2 = px.pie(cg, values="jumlah", names="confidence", title="Confidence Hotspot",
                              color_discrete_sequence=["#93c5fd", "#2563eb", "#1e3a8a"], hole=0.4,
                              textinfo="value")
                fig2.update_layout(height=260)
                st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Tren Hotspot Harian")
        if hotspot_f is not None:
            ts = hotspot_f.copy()
            ts["tgl"] = ts["tanggal"].dt.date
            g = ts.groupby("tgl").size().reset_index(name="hotspot")
            fig = px.area(g, x="tgl", y="hotspot", title="Jumlah Hotspot per Hari",
                          color_discrete_sequence=["#2563eb"], text="hotspot")
            fig.update_traces(textposition="top center")
            fig.update_layout(height=340)
            st.plotly_chart(fig, use_container_width=True)

# ---------------- Tab Tren
with tabs[3]:
    st.subheader("Tren Waktu per Bencana")
    if "tanggal" in pusat_f and pusat_f["tanggal"].notna().any():
        # Tren bulanan terpisah per tipe
        ts = pusat_f.copy()
        ts["bulan"] = ts["tanggal"].dt.to_period("M").astype(str)
        g = ts.groupby(["bulan", "tipe_bencana"]).size().reset_index(name="kejadian")
        fig = px.line(g, x="bulan", y="kejadian", color="tipe_bencana",
                      facet_col="tipe_bencana", facet_col_wrap=2,
                      title="Tren Kejadian Bulanan per Tipe Bencana", markers=True, text="kejadian")
        fig.update_traces(textposition="top center")
        fig.update_layout(height=480, xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Tren bulanan gabungan
        ts2 = pusat_f.copy()
        ts2["bulan"] = ts2["tanggal"].dt.to_period("M").astype(str)
        g2 = ts2.groupby("bulan").agg(kejadian=("tipe_bencana", "size"),
                                      luas=("luas_ha", "sum"),
                                      korban=("korban_jiwa", "sum"),
                                      ispa=("ispa", "sum")).reset_index().sort_values("bulan")
        fig2 = px.line(g2, x="bulan", y=["kejadian", "luas", "korban", "ispa"], title="Tren Bulanan (Gabungan)",
                      markers=True)
        fig2.update_layout(height=420, xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

        # Tren mingguan per tipe
        ts3 = pusat_f.copy()
        ts3["minggu"] = ts3["tanggal"].dt.to_period("W").astype(str)
        g3 = ts3.groupby(["minggu", "tipe_bencana"]).size().reset_index(name="kejadian")
        fig3 = px.area(g3, x="minggu", y="kejadian", color="tipe_bencana",
                       title="Tren Kejadian Mingguan per Tipe Bencana",
                       color_discrete_map=TIPE_COLOR)
        fig3.update_layout(height=360, xaxis_tickangle=-60)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Kolom tanggal tidak tersedia.")

# ---------------- Tab Data
with tabs[4]:
    st.subheader("Data & Kualitas Data")
    st.markdown("**Data Pusat (filter)**")
    st.dataframe(_display_date(_clean_data(pusat_f)), use_container_width=True, height=280)
    if hotspot_f is not None:
        st.markdown("**Data Hotspot (filter)**")
        st.dataframe(_display_date(hotspot_f), use_container_width=True, height=220)

    st.markdown("#### Profil Kualitas Data")
    q_rows = []
    for name, df_ in [("Pusat", pusat_f), ("Hotspot", hotspot_f if hotspot_f is not None else pd.DataFrame())]:
        if df_.empty:
            continue
        q_rows.append({
            "Sumber": name,
            "Jumlah Record": len(df_),
            "Kolom": len(df_.columns),
            "Missing Values": int(df_.isna().sum().sum()),
            "% Missing": round(df_.isna().sum().sum() / max(df_.size, 1) * 100, 2),
            "Tanpa Koordinat": int(df_[["lat", "lon"]].isna().any(axis=1).sum()) if all(c in df_ for c in ["lat", "lon"]) else 0,
        })
    st.dataframe(pd.DataFrame(q_rows), use_container_width=True, hide_index=True)

# ---------------- Tab Export
with tabs[5]:
    st.subheader("Export Laporan")
    template_cols = ["tanggal", "provinsi", "kabupaten", "tipe_bencana", "luas_ha",
                     "korban_jiwa", "pengungsi", "ispa", "penyebab", "status_verifikasi", "sumber"]
    hotspot_cols = ["id_hotspot", "tanggal", "provinsi", "kabupaten", "lat", "lon",
                    "confidence", "satelit", "frp", "sumber"]
    tmpl = pd.DataFrame(columns=template_cols)
    htmpl = pd.DataFrame(columns=hotspot_cols)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Template Bencana (CSV)", tmpl.to_csv(index=False).encode("utf-8"),
                           file_name="template_bencana.csv", mime="text/csv")
    with c2:
        st.download_button("⬇️ Template Hotspot (CSV)", htmpl.to_csv(index=False).encode("utf-8"),
                           file_name="template_hotspot.csv", mime="text/csv")

    st.markdown("#### Export per Tipe Bencana (Karhutla / Banjir / Gempa / Bencana Lainnya)")
    if "tipe_bencana" in pusat_f:
        tipe_list = ["Karhutla", "Banjir", "Gempa", "Bencana Alam Lainnya"]
        available = [t for t in tipe_list if t in pusat_f["tipe_bencana"].unique().tolist()]
        if available:
            tipe_choice = st.selectbox("Pilih tipe untuk CSV", available)
            sub = _clean_data(pusat_f[pusat_f["tipe_bencana"] == tipe_choice])
            st.download_button(f"⬇️ Download CSV: {tipe_choice}", sub.to_csv(index=False).encode("utf-8"),
                               file_name=f"data_{tipe_choice.lower().replace(' ', '_')}.csv", mime="text/csv")
            st.caption(f"Jumlah record {tipe_choice}: {len(sub)}")

    csv_bytes = _clean_data(pusat_f).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Gabungan (CSV - filter saat ini)", csv_bytes,
                       file_name="data_bencana_gabungan.csv", mime="text/csv")

    st.markdown("#### Download Excel (terpisah per tipe + gabungan)")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        _clean_data(pusat_f).to_excel(w, index=False, sheet_name="Gabungan")
        if "tipe_bencana" in pusat_f:
            for t in pusat_f["tipe_bencana"].unique():
                nm = t[:28]
                _clean_data(pusat_f[pusat_f["tipe_bencana"] == t]).to_excel(w, index=False, sheet_name=nm)
        if hotspot_f is not None:
            hotspot_f.to_excel(w, index=False, sheet_name="Hotspot")
        if "provinsi" in pusat_f:
            summ = pusat_f.groupby("provinsi").agg(
                kejadian=("tipe_bencana", "size"), luas_ha=("luas_ha", "sum"),
                korban_jiwa=("korban_jiwa", "sum"),
                ispa=("ispa", "sum")).reset_index()
            summ.to_excel(w, index=False, sheet_name="Rekap Provinsi")
        if "tipe_bencana" in pusat_f:
            summ2 = pusat_f.groupby("tipe_bencana").agg(
                kejadian=("tipe_bencana", "size"), luas_ha=("luas_ha", "sum"),
                korban_jiwa=("korban_jiwa", "sum"),
                ispa=("ispa", "sum")).reset_index()
            summ2.to_excel(w, index=False, sheet_name="Rekap Tipe")
    st.download_button("⬇️ Download Laporan Lengkap (Excel)", buf.getvalue(),
                       file_name="laporan_bencana.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.success("File siap diunduh. Sheet: Gabungan, per tipe, Hotspot, Rekap Provinsi, Rekap Tipe.")

st.divider()
st.caption("Dashboard Bencana Alam — Direktorat 2.3 Deputi 2 BIN | Latihan Aktualisasi | Wilayah Sumatera & Kalimantan")
