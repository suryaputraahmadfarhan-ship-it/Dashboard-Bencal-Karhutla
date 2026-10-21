# -*- coding: utf-8 -*-
"""Fungsi bantu data: normalisasi file upload, format angka/tanggal, perhitungan periode."""
import numpy as np
import pandas as pd

from data_generator import KALIMANTAN, PROVINSI, SUMATERA, TIPE_BENCANA

BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
BULAN_PANJANG = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
                 "September", "Oktober", "November", "Desember"]

PERIODE = {
    "Hari ini": 1,
    "7 hari terakhir": 7,
    "14 hari terakhir": 14,
    "30 hari terakhir": 30,
    "90 hari terakhir": 90,
    "Semua data": None,
}

KOLOM_TEMPLATE_BENCANA = ["tanggal", "provinsi", "kabupaten", "tipe_bencana",
                          "luas_ha", "magnitudo", "kedalaman_km", "tinggi_genangan_cm", "rumah_terdampak",
                          "korban_jiwa", "pengungsi", "ispa",
                          "penyebab", "status_verifikasi", "sumber", "lat", "lon"]
KOLOM_TEMPLATE_HOTSPOT = ["tanggal", "provinsi", "kabupaten", "lat", "lon", "confidence", "satelit", "frp", "sumber"]

# Kolom yang relevan ditampilkan per jenis bencana (selain kolom umum)
KOLOM_SPESIFIK = {
    "Karhutla": ["luas_ha", "ispa"],
    "Banjir": ["tinggi_genangan_cm", "rumah_terdampak", "luas_ha"],
    "Gempa": ["magnitudo", "kedalaman_km", "rumah_terdampak"],
    "Bencana Alam Lainnya": ["rumah_terdampak"],
}


# ------------------------------------------------------------------ format
def fmt_num(x, digits=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"{x:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_compact(x, digits=1):
    """Format angka ringkas untuk KPI: 1.234 → '1,2 rb', 1.250.000 → '1,25 jt'. Nilai kecil pakai fmt_num."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    ax = abs(x)
    if ax >= 1_000_000:
        return fmt_num(x / 1_000_000, digits) + " jt"
    if ax >= 10_000:
        return fmt_num(x / 1_000, digits) + " rb"
    if ax >= 1_000:
        return fmt_num(x, 0)
    if ax < 10 and (not float(x).is_integer()):
        return fmt_num(x, digits)
    return fmt_num(x, 0)


def tgl_id(ts, panjang=False):
    ts = pd.Timestamp(ts)
    if panjang:
        return f"{ts.day} {BULAN_PANJANG[ts.month - 1]} {ts.year}"
    return f"{ts.day} {BULAN[ts.month - 1]}"


def delta_pct(cur, prev):
    """Persentase perubahan; None bila periode pembanding kosong."""
    if prev is None or prev == 0:
        return None
    return (cur - prev) / prev * 100


# ------------------------------------------------------------------ wilayah
def wilayah_options(provinsi_tersedia):
    return ["Sumatera & Kalimantan", "Sumatera", "Kalimantan"] + sorted(provinsi_tersedia)


def wilayah_provinsi(wilayah):
    """Daftar provinsi untuk pilihan wilayah; None = semua."""
    if wilayah == "Sumatera & Kalimantan":
        return None
    if wilayah == "Sumatera":
        return SUMATERA
    if wilayah == "Kalimantan":
        return KALIMANTAN
    return [wilayah]


def peta_view(wilayah, df=None):
    """(center, zoom) untuk peta sesuai wilayah."""
    if wilayah == "Sumatera & Kalimantan":
        return {"lat": -0.5, "lon": 107.5}, 3.7
    if wilayah == "Sumatera":
        return {"lat": -0.5, "lon": 102.0}, 4.6
    if wilayah == "Kalimantan":
        return {"lat": 0.3, "lon": 114.0}, 5.0
    if wilayah in PROVINSI:
        return {"lat": PROVINSI[wilayah]["lat"], "lon": PROVINSI[wilayah]["lon"]}, 6.0
    return {"lat": -0.5, "lon": 108.5}, 3.7


# ------------------------------------------------------------------ periode
def split_periode(df, end, days):
    """Kembalikan (periode_ini, periode_sebelumnya). days=None -> semua data, tanpa pembanding."""
    if df is None or df.empty:
        return df, None
    end = pd.Timestamp(end).normalize()
    if days is None:
        return df, None
    start = end - pd.Timedelta(days=days - 1)
    pstart = start - pd.Timedelta(days=days)
    t = df["tanggal"].dt.normalize()
    cur = df[(t >= start) & (t <= end)]
    prev = df[(t >= pstart) & (t < start)]
    return cur, prev


# ------------------------------------------------------------------ upload
def _rename_first(df, target, candidates):
    if target in df.columns:
        return df
    for c in candidates:
        if c in df.columns:
            return df.rename(columns={c: target})
    return df


def _norm_tipe(v):
    s = str(v).lower()
    if any(k in s for k in ["karhutla", "kebakaran", "fire", "hotspot"]):
        return "Karhutla"
    if "banjir" in s or "flood" in s:
        return "Banjir"
    if "gempa" in s or "earthquake" in s:
        return "Gempa"
    return "Bencana Alam Lainnya"


def normalize_bencana(df):
    d = df.copy()
    d.columns = [str(c).strip().lower().replace(" ", "_") for c in d.columns]
    d = _rename_first(d, "tanggal", ["date", "tgl", "date_time", "waktu"])
    d = _rename_first(d, "provinsi", ["province", "propinsi", "prov"])
    d = _rename_first(d, "kabupaten", ["kab", "kota", "kab_kota", "kabupaten_kota"])
    d = _rename_first(d, "tipe_bencana", ["tipe", "jenis", "jenis_bencana", "type", "disaster_type"])
    d = _rename_first(d, "luas_ha", ["luas", "area_ha", "luasan", "luas_terdampak", "luas_terdampak_ha"])
    d = _rename_first(d, "magnitudo", ["magnitude", "mag", "mw", "sr", "skala_richter"])
    d = _rename_first(d, "kedalaman_km", ["kedalaman", "depth", "depth_km"])
    d = _rename_first(d, "tinggi_genangan_cm", ["tinggi_genangan", "tinggi_air", "genangan", "genangan_cm",
                                                 "tinggi_banjir"])
    d = _rename_first(d, "rumah_terdampak", ["rumah", "rumah_rusak", "jumlah_rumah", "rumah_terdampak_unit",
                                              "rumah_terkena"])
    d = _rename_first(d, "lat", ["latitude", "lintang"])
    d = _rename_first(d, "lon", ["longitude", "bujur", "lng", "long"])
    d = _rename_first(d, "korban_jiwa", ["korban_meninggal", "meninggal", "dead", "fatalities", "korban"])
    d = _rename_first(d, "ispa", ["ispa_cases", "dampak_ispa", "kasus_ispa"])

    missing = [c for c in ["tanggal", "provinsi"] if c not in d.columns]
    if missing:
        raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(missing))

    d["tanggal"] = pd.to_datetime(d["tanggal"], errors="coerce")
    d = d.dropna(subset=["tanggal"])
    d["provinsi"] = d["provinsi"].astype(str).str.strip().str.title()
    d["tipe_bencana"] = d["tipe_bencana"].map(_norm_tipe) if "tipe_bencana" in d.columns else "Bencana Alam Lainnya"
    # kolom numerik berbasis NaN (biar sum/mean mengabaikan jenis bencana yang tidak relevan)
    for c in ["luas_ha", "magnitudo", "kedalaman_km", "tinggi_genangan_cm", "rumah_terdampak", "lat", "lon"]:
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d.columns else np.nan
    for c in ["korban_jiwa", "pengungsi", "ispa"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int) if c in d.columns else 0
    for c, default in [("kabupaten", "-"), ("penyebab", "-"), ("status_verifikasi", "Perlu Verifikasi"),
                       ("sumber", "Upload")]:
        if c not in d.columns:
            d[c] = default
    return d.reset_index(drop=True)


def normalize_hotspot(df):
    d = df.copy()
    d.columns = [str(c).strip().lower().replace(" ", "_") for c in d.columns]
    d = _rename_first(d, "tanggal", ["date", "tgl", "acq_date", "waktu"])
    d = _rename_first(d, "provinsi", ["province", "propinsi", "prov"])
    d = _rename_first(d, "kabupaten", ["kab", "kota", "kab_kota", "kabupaten_kota"])
    d = _rename_first(d, "lat", ["latitude", "lintang"])
    d = _rename_first(d, "lon", ["longitude", "bujur", "lng", "long"])
    d = _rename_first(d, "satelit", ["satellite", "sat"])
    missing = [c for c in ["tanggal", "provinsi", "lat", "lon"] if c not in d.columns]
    if missing:
        raise ValueError("Kolom wajib hotspot tidak ditemukan: " + ", ".join(missing))
    d["tanggal"] = pd.to_datetime(d["tanggal"], errors="coerce")
    d = d.dropna(subset=["tanggal"])
    d["provinsi"] = d["provinsi"].astype(str).str.strip().str.title()
    d["lat"] = pd.to_numeric(d["lat"], errors="coerce")
    d["lon"] = pd.to_numeric(d["lon"], errors="coerce")
    d = d.dropna(subset=["lat", "lon"])
    if "kabupaten" not in d.columns:
        d["kabupaten"] = "-"
    d["frp"] = pd.to_numeric(d["frp"], errors="coerce").fillna(0) if "frp" in d.columns else 0.0
    if "confidence" not in d.columns:
        d["confidence"] = "Nominal"
    if "satelit" not in d.columns:
        d["satelit"] = "-"
    return d.reset_index(drop=True)


def baca_file(f):
    name = f.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(f)
    return pd.read_csv(f)


def tipe_tersedia(df):
    ada = set(df["tipe_bencana"].unique())
    return [t for t in TIPE_BENCANA if t in ada] + sorted(ada - set(TIPE_BENCANA))
