# -*- coding: utf-8 -*-
"""Dashboard Bencana Alam - Dir 2.3 (BIN Deputi 2) - Wilayah Sumatera & Kalimantan."""
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

# ---------------------------------------------------------------- blue theme
st.markdown("""
<style>
:root {
  --bin-blue: #1e3a8a;
  --bin-blue2: #2563eb;
  --bin-light: #dbeafe;
}
.stApp { background: linear-gradient(180deg, #f0f6ff 0%, #ffffff 60%); }
div[data-testid="stMetric"] {
  background: #ffffff;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  padding: 10px 12px;
  box-shadow: 0 2px 8px rgba(30,58,138,0.06);
}
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%);
  color: #ffffff;
}
section[data-testid="stSidebar"] * { color: #ffffff !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stDateInput label,
section[data-testid="stSidebar"] .stRadio label { color: #ffffff !important; }
h1, h2, h3 { color: #1e3a8a; }
.badge {
  display:inline-block; padding:4px 10px; border-radius:999px;
  background:#dbeafe; color:#1e3a8a; font-weight:600; font-size:12px;
}
</style>
""", unsafe_allow_html=True)

TIPE_COLOR = {"Karhutla": "#dc2626", "Banjir": "#2563eb", "Bencana Alam Lainnya": "#0891b2"}
SEVERITY_COLOR = {"Ringan": "#93c5fd", "Sedang": "#3b82f6", "Berat": "#1d4ed8", "Sangat Berat": "#1e3a8a"}

# ---------------------------------------------------------------- helpers
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
    # tanggal
    for c in ["tanggal", "date", "tgl"]:
        if c in df.columns:
            df["tanggal"] = pd.to_datetime(df[c], errors="coerce")
            break
    if "tanggal" not in df.columns:
        df["tanggal"] = pd.NaT
    # provinsi
    if "provinsi" not in df.columns:
        for c in ["province", "propinsi", "prov"]:
            if c in df.columns:
                df = df.rename(columns={c: "provinsi"})
    # kabupaten
    if "kabupaten" not in df.columns:
        for c in ["kab", "kota", "kab_kota", "kabupaten_kota"]:
            if c in df.columns:
                df = df.rename(columns={c: "kabupaten"})
    # tipe bencana
    if "tipe_bencana" not in df.columns:
        for c in ["tipe", "jenis", "jenis_bencana", "type"]:
            if c in df.columns:
                df = df.rename(columns={c: "tipe_bencana"})
    if "tipe_bencana" not in df.columns:
        df["tipe_bencana"] = "Bencana Alam Lainnya"
    # luas
    if "luas_ha" not in df.columns:
        for c in ["luas", "area_ha", "luasan", "luas_terdampak", "luas_terdampak_ha"]:
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
    # korban
    if "korban_jiwa" not in df.columns:
        for c in ["korban_meninggal", "meninggal", "dead", "korban"]:
            if c in df.columns:
                df = df.rename(columns={c: "korban_jiwa"})
    if "korban_jiwa" not in df.columns:
        df["korban_jiwa"] = 0
    if "korban_luka" not in df.columns:
        for c in ["luka", "injured"]:
            if c in df.columns:
                df = df.rename(columns={c: "korban_luka"})
    if "korban_luka" not in df.columns:
        df["korban_luka"] = 0
    # ispa
    if "ispa_cases" not in df.columns:
        for c in ["ispa", "dampak_ispa", "kasus_ispa"]:
            if c in df.columns:
                df = df.rename(columns={c: "ispa_cases"})
    if "ispa_cases" not in df.columns:
        df["ispa_cases"] = 0
    # numeric
    for c in ["korban_jiwa", "korban_luka", "ispa_cases"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    # pengungsi
    if "pengungsi" not in df.columns:
        df["pengungsi"] = 0
    else:
        df["pengungsi"] = pd.to_numeric(df["pengungsi"], errors="coerce").fillna(0).astype(int)
    # severity
    if "severity" not in df.columns and "tingkat" in df.columns:
        df = df.rename(columns={"tingkat": "severity"})
    if "severity" not in df.columns:
        df["severity"] = "Sedang"
    # id
    if "id_kejadian" not in df.columns:
        for c in ["id", "id_laporan"]:
            if c in df.columns:
                df = df.rename(columns={c: "id_kejadian"})
    if "id_kejadian" not in df.columns:
        df["id_kejadian"] = [f"B-{i:06d}" for i in range(len(df))]
    # status
    if "status_verifikasi" not in df.columns:
        df["status_verifikasi"] = "Perlu Verifikasi"
    return df


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
    <h1 style="margin:0; color:#1e3a8a;">Dashboard Monitoring Bencana Alam</h1>
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
    st.caption("Dir 2.3 - Deputi 2 BIN")
    st.divider()

    data_source = st.radio("Sumber data", ["Data Sintetis (Demo)", "Upload CSV/Excel (Pusat)"], index=0)

    seed = 42
    if data_source == "Data Sintetis (Demo)":
        seed = st.slider("Seed data", 1, 999, 42)

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
    st.sidebar.subheader("Upload data Pusat")
    pusat_file = st.sidebar.file_uploader("File Pusat (Bencana)", type=["csv", "xlsx", "xls"], key="pusat")
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
    st.info("Silakan upload file data Pusat, atau pilih mode Data Sintetis (Demo).")
    st.stop()

pusat_df["tanggal"] = pd.to_datetime(pusat_df["tanggal"], errors="coerce")
if hotspot_df is not None:
    hotspot_df["tanggal"] = pd.to_datetime(hotspot_df["tanggal"], errors="coerce")

# sidebar filters
with st.sidebar:
    all_tipe = [t for t in TIPE_BENCANA if t in pusat_df["tipe_bencana"].unique()] or sorted(pusat_df["tipe_bencana"].dropna().unique().tolist())
    tipe_sel = st.multiselect("Tipe Bencana", all_tipe, default=all_tipe)
    all_provs = sorted(pusat_df["provinsi"].dropna().unique().tolist())
    prov_sel = st.multiselect("Provinsi", all_provs, default=[])
    valid_dates = pusat_df["tanggal"].dropna()
    dmin = valid_dates.min().date() if len(valid_dates) else date(2025, 1, 1)
    dmax = valid_dates.max().date() if len(valid_dates) else date(2025, 12, 31)
    dr = st.date_input("Rentang tanggal", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    if not isinstance(dr, (tuple, list)):
        dr = (dr, dr)

# apply filters
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

# ---------------------------------------------------------------- KPIs
st.subheader("Indikator Utama")
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Total Kejadian", fmt_num(len(pusat_f)))
with c2:
    st.metric("Total Luas Terdampak (ha)", fmt_num(pusat_f["luas_ha"].sum() if "luas_ha" in pusat_f else 0, 1))
with c3:
    korban = (pusat_f["korban_jiwa"].sum() if "korban_jiwa" in pusat_f else 0) + (pusat_f["korban_luka"].sum() if "korban_luka" in pusat_f else 0)
    st.metric("Total Korban", fmt_num(korban))
with c4:
    st.metric("Kasus ISPA", fmt_num(pusat_f["ispa_cases"].sum() if "ispa_cases" in pusat_f else 0))
with c5:
    st.metric("Provinsi Terdampak", pusat_f["provinsi"].nunique() if "provinsi" in pusat_f else 0)
with c6:
    hs_today = 0
    if hotspot_f is not None and not hotspot_f.empty:
        last_d = hotspot_f["tanggal"].max()
        hs_today = (hotspot_f["tanggal"].dt.date == last_d.date()).sum()
    st.metric("Hotspot (hari terakhir data)", fmt_num(hs_today))

tabs = st.tabs(["🗺️ Peta", "📊 Analisis", "🔥 Hotspot", "📈 Tren", "📋 Data", "⬇️ Export"])

# ---------------- Tab Peta
with tabs[0]:
    st.subheader("Peta Kejadian Bencana")
    if pusat_f.empty:
        st.warning("Tidak ada data.")
    else:
        fig = px.scatter_geo(
            pusat_f, lat="lat", lon="lon",
            color="tipe_bencana", size="luas_ha",
            hover_name="kabupaten", hover_data={"provinsi": True, "tipe_bencana": True,
                                              "luas_ha": True, "tanggal": True,
                                              "korban_jiwa": True, "ispa_cases": True},
            color_discrete_map=TIPE_COLOR, size_max=34,
            projection="natural earth",
        )
        fig.update_geos(center=dict(lat=0.5, lon=110), projection_scale=5.2,
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
            fig = px.bar(g, x="kejadian", y="provinsi", orientation="h",
                         title="Kejadian per Provinsi", color="kejadian",
                         color_continuous_scale="Blues")
            fig.update_layout(height=420, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with colB:
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana").size().reset_index(name="kejadian")
            fig = px.pie(g, values="kejadian", names="tipe_bencana", title="Komposisi Tipe Bencana",
                         color="tipe_bencana", color_discrete_map=TIPE_COLOR, hole=0.45)
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

# ---------------- Tab Analisis
with tabs[1]:
    st.subheader("Analisis: Kejadian, Luas Terdampak, Korban, Dampak (ISPA)")
    r1, r2 = st.columns(2)
    with r1:
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana").agg(kejadian=("id_kejadian", "count"),
                                                   luas=("luas_ha", "sum")).reset_index()
            fig = px.bar(g, x="tipe_bencana", y=["kejadian", "luas"], barmode="group",
                         title="Jumlah Kejadian & Luas Terdampak per Tipe")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
    with r2:
        if "severity" in pusat_f:
            g = pusat_f.groupby("severity").size().reset_index(name="kejadian")
            fig = px.bar(g, x="severity", y="kejadian", title="Distribusi Severity",
                         color="severity", color_discrete_map=SEVERITY_COLOR)
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    r3, r4 = st.columns(2)
    with r3:
        # Korban per tipe
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana").agg(korban_jiwa=("korban_jiwa", "sum"),
                                                   korban_luka=("korban_luka", "sum")).reset_index()
            fig = px.bar(g, x="tipe_bencana", y=["korban_jiwa", "korban_luka"], barmode="group",
                         title="Korban (Jiwa & Luka) per Tipe Bencana",
                         color_discrete_sequence=["#dc2626", "#f97316"])
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
    with r4:
        # ISPA per tipe (terutama karhutla)
        if "tipe_bencana" in pusat_f:
            g = pusat_f.groupby("tipe_bencana")["ispa_cases"].sum().reset_index()
            fig = px.bar(g, x="tipe_bencana", y="ispa_cases", title="Kasus ISPA per Tipe Bencana",
                         color="tipe_bencana", color_discrete_map=TIPE_COLOR)
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Rekap per Provinsi")
    if "provinsi" in pusat_f:
        g = pusat_f.groupby("provinsi").agg(
            kejadian=("id_kejadian", "count"),
            luas_ha=("luas_ha", "sum"),
            korban_jiwa=("korban_jiwa", "sum"),
            korban_luka=("korban_luka", "sum"),
            ispa_cases=("ispa_cases", "sum"),
        ).reset_index().sort_values("kejadian", ascending=False)
        st.dataframe(g, use_container_width=True, hide_index=True)

# ---------------- Tab Hotspot
with tabs[2]:
    st.subheader("🔥 Sebaran Hotspot")
    if hotspot_f is None or hotspot_f.empty:
        st.warning("Data hotspot tidak tersedia. (Upload file hotspot di sidebar atau gunakan mode Sintetis.)")
    else:
        # pilih tanggal
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
            )
            fig.update_geos(center=dict(lat=0.5, lon=110), projection_scale=5.2,
                            showland=True, landcolor="#eaf2ff", showocean=True, oceancolor="#f0f7ff",
                            showcountries=True, countrycolor="#94a3b8")
            fig.update_layout(height=520, margin=dict(l=0, r=0, t=20, b=0),
                              title=f"Hotspot {pick} (n={len(hdf)})")
            st.plotly_chart(fig, use_container_width=True)
        with h2:
            st.metric("Hotspot tgl ini", fmt_num(len(hdf)))
            if "provinsi" in hdf:
                g = hdf.groupby("provinsi").size().reset_index(name="hotspot").sort_values("hotspot", ascending=False)
                st.dataframe(g, use_container_width=True, hide_index=True)
            if "confidence" in hdf:
                cg = hdf["confidence"].value_counts().reset_index()
                cg.columns = ["confidence", "jumlah"]
                fig2 = px.pie(cg, values="jumlah", names="confidence", title="Confidence Hotspot",
                              color_discrete_sequence=["#93c5fd", "#2563eb", "#1e3a8a"], hole=0.4)
                fig2.update_layout(height=260)
                st.plotly_chart(fig2, use_container_width=True)

        # tren hotspot harian
        st.markdown("#### Tren Hotspot Harian")
        if hotspot_f is not None:
            ts = hotspot_f.copy()
            ts["tgl"] = ts["tanggal"].dt.date
            g = ts.groupby("tgl").size().reset_index(name="hotspot")
            fig = px.area(g, x="tgl", y="hotspot", title="Jumlah Hotspot per Hari",
                          color_discrete_sequence=["#2563eb"])
            fig.update_layout(height=340)
            st.plotly_chart(fig, use_container_width=True)

# ---------------- Tab Tren
with tabs[3]:
    st.subheader("Tren Waktu")
    if "tanggal" in pusat_f and pusat_f["tanggal"].notna().any():
        ts = pusat_f.copy()
        ts["bulan"] = ts["tanggal"].dt.to_period("M").astype(str)
        g = ts.groupby("bulan").agg(kejadian=("id_kejadian", "count"),
                                    luas=("luas_ha", "sum"),
                                    korban=("korban_jiwa", "sum"),
                                    ispa=("ispa_cases", "sum")).reset_index().sort_values("bulan")
        fig = px.line(g, x="bulan", y=["kejadian", "luas", "korban", "ispa"], title="Tren Bulanan",
                      markers=True)
        fig.update_layout(height=440, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        ts2 = pusat_f.copy()
        ts2["minggu"] = ts2["tanggal"].dt.to_period("W").astype(str)
        g2 = ts2.groupby("minggu").size().reset_index(name="kejadian").sort_values("minggu")
        fig2 = px.area(g2, x="minggu", y="kejadian", title="Tren Kejadian Mingguan", color_discrete_sequence=["#1e3a8a"])
        fig2.update_layout(height=340, xaxis_tickangle=-60)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Kolom tanggal tidak tersedia.")

# ---------------- Tab Data
with tabs[4]:
    st.subheader("Data & Kualitas Data")
    st.markdown("**Data Pusat (filter)**")
    st.dataframe(pusat_f, use_container_width=True, height=280)
    if hotspot_f is not None:
        st.markdown("**Data Hotspot (filter)**")
        st.dataframe(hotspot_f, use_container_width=True, height=220)

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
    template_cols = ["id_kejadian", "tanggal", "provinsi", "kabupaten", "lat", "lon",
                     "tipe_bencana", "luas_ha", "korban_jiwa", "korban_luka", "pengungsi",
                     "ispa_cases", "penyebab", "severity", "status_verifikasi", "sumber"]
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

    # export data saat ini
    csv_bytes = pusat_f.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Data Bencana (CSV)", csv_bytes,
                       file_name="data_bencana.csv", mime="text/csv")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pusat_f.to_excel(w, index=False, sheet_name="Bencana")
        if hotspot_f is not None:
            hotspot_f.to_excel(w, index=False, sheet_name="Hotspot")
        if "provinsi" in pusat_f:
            summ = pusat_f.groupby("provinsi").agg(
                kejadian=("id_kejadian", "count"), luas_ha=("luas_ha", "sum"),
                korban_jiwa=("korban_jiwa", "sum"), korban_luka=("korban_luka", "sum"),
                ispa_cases=("ispa_cases", "sum")).reset_index()
            summ.to_excel(w, index=False, sheet_name="Rekap Provinsi")
        if "tipe_bencana" in pusat_f:
            summ2 = pusat_f.groupby("tipe_bencana").agg(
                kejadian=("id_kejadian", "count"), luas_ha=("luas_ha", "sum"),
                korban_jiwa=("korban_jiwa", "sum"), korban_luka=("korban_luka", "sum"),
                ispa_cases=("ispa_cases", "sum")).reset_index()
            summ2.to_excel(w, index=False, sheet_name="Rekap Tipe")
    st.download_button("⬇️ Download Laporan Lengkap (Excel)", buf.getvalue(),
                       file_name="laporan_bencana.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.success("File siap diunduh untuk laporan/pimpinan.")

st.divider()
st.caption("Dashboard Bencana Alam — Dir 2.3 Deputi 2 BIN | Latsar Aktualisasi | Wilayah Sumatera & Kalimantan")
