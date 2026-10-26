# -*- coding: utf-8 -*-
"""Supabase client untuk persistensi laporan antar user & reboot.

Dashboard tetap jalan tanpa Supabase (fallback ke session_state) — fungsi
`is_configured()` memberitahu apakah backend persisten aktif.
"""
from datetime import datetime, date

import pandas as pd
import streamlit as st

try:
    from supabase import create_client, Client  # type: ignore
    _HAS_SUPABASE = True
except Exception:  # noqa: BLE001
    _HAS_SUPABASE = False

TABLE = "laporan_teks"


def is_configured():
    """True jika secrets.supabase.{url,key} ada dan package supabase tersedia."""
    if not _HAS_SUPABASE:
        return False
    try:
        cfg = st.secrets.get("supabase", {})
        return bool(cfg.get("url") and cfg.get("key"))
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def _client() -> "Client | None":
    if not is_configured():
        return None
    cfg = st.secrets["supabase"]
    try:
        return create_client(cfg["url"], cfg["key"])
    except Exception as e:  # noqa: BLE001
        st.session_state["_supabase_err"] = str(e)
        return None


def status_text():
    """Status pendek untuk ditampilkan di UI admin / caption."""
    if not _HAS_SUPABASE:
        return "paket `supabase` belum ter-install"
    if not is_configured():
        return "secrets.supabase belum di-set"
    if _client() is None:
        return "gagal konek: " + st.session_state.get("_supabase_err", "unknown")
    return "terhubung"


# ------------------------------------------------------------------ write
def _record_to_row(ek, rec_meta):
    """Konversi hasil ekstraksi + metadata menjadi dict kolom tabel Supabase.
    Jika terdeteksi >1 provinsi/jenis, baris pertama saja (sisanya diringkas di teks)."""
    angka = ek.get("angka", {}) or {}
    prov = ek["provinsi"][0] if ek["provinsi"] else None
    kab = ek["kabupaten"][0] if ek["kabupaten"] else None
    jenis = ek["jenis_bencana"][0] if ek["jenis_bencana"] else None
    tgl = ek.get("tanggal")
    luas = angka.get("luas_ha")
    padam = angka.get("luas_padam_ha")
    belum = angka.get("luas_belum_padam_ha")
    if luas is not None and padam is not None and belum is None:
        belum = max(0.0, float(luas) - float(padam))
    return {
        "petugas":        rec_meta.get("petugas"),
        "subdit":         rec_meta.get("subdit"),
        "judul":          rec_meta.get("judul"),
        "sumber":         rec_meta.get("sumber"),
        "tanggal_kejadian": tgl.isoformat() if isinstance(tgl, (date, datetime)) else None,
        "provinsi":       prov,
        "kabupaten":      kab,
        "jenis_bencana":  jenis,
        "luas_ha":        float(luas) if luas is not None else None,
        "luas_padam_ha":  float(padam) if padam is not None else None,
        "luas_belum_padam_ha": float(belum) if belum is not None else None,
        "korban_jiwa":    int(angka.get("korban_jiwa", 0) or 0),
        "pengungsi":      int(angka.get("pengungsi", 0) or 0),
        "ispa":           int(angka.get("ispa", 0) or 0),
        "rumah_terdampak": float(angka["rumah_terdampak"]) if "rumah_terdampak" in angka else None,
        "tinggi_genangan_cm": float(angka["tinggi_genangan_cm"]) if "tinggi_genangan_cm" in angka else None,
        "magnitudo":      float(angka["magnitudo"]) if "magnitudo" in angka else None,
        "kedalaman_km":   float(angka["kedalaman_km"]) if "kedalaman_km" in angka else None,
        "hotspot":        int(angka["hotspot"]) if "hotspot" in angka else None,
        "teks_asli":      ek.get("teks_asli", ""),
    }


def insert(ek, rec_meta):
    """Simpan satu laporan ke Supabase. Return (ok: bool, id|err_msg)."""
    cli = _client()
    if cli is None:
        return False, status_text()
    try:
        row = _record_to_row(ek, rec_meta)
        res = cli.table(TABLE).insert(row).execute()
        return True, (res.data[0]["id"] if res.data else None)
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def delete(laporan_id):
    cli = _client()
    if cli is None:
        return False, status_text()
    try:
        cli.table(TABLE).update({"deleted": True}).eq("id", int(laporan_id)).execute()
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, str(e)


# ------------------------------------------------------------------ read
@st.cache_data(ttl=30, show_spinner=False)
def fetch_all():
    """Ambil semua laporan aktif (deleted=false) sebagai DataFrame."""
    cli = _client()
    if cli is None:
        return pd.DataFrame()
    try:
        res = (cli.table(TABLE)
               .select("*")
               .eq("deleted", False)
               .order("tanggal_kejadian", desc=True)
               .limit(5000)
               .execute())
        if not res.data:
            return pd.DataFrame()
        df = pd.DataFrame(res.data)
        if "tanggal_kejadian" in df.columns:
            df["tanggal_kejadian"] = pd.to_datetime(df["tanggal_kejadian"], errors="coerce")
        return df
    except Exception as e:  # noqa: BLE001
        st.session_state["_supabase_err"] = str(e)
        return pd.DataFrame()


def to_inc_df(df_sb):
    """Konversi tabel Supabase ke format `inc` yang dipakai dashboard
    (kolom tipe_bencana, tanggal, lat, lon, luas_ha, dsb)."""
    if df_sb is None or df_sb.empty:
        return pd.DataFrame()
    out = pd.DataFrame({
        "id_kejadian": "LP-" + df_sb["id"].astype(str),
        "tanggal":     pd.to_datetime(df_sb["tanggal_kejadian"], errors="coerce"),
        "provinsi":    df_sb["provinsi"].fillna("-"),
        "kabupaten":   df_sb["kabupaten"].fillna("-"),
        "tipe_bencana": df_sb["jenis_bencana"].fillna("Bencana Alam Lainnya"),
        "luas_ha":     pd.to_numeric(df_sb.get("luas_ha"), errors="coerce"),
        "luas_padam_ha": pd.to_numeric(df_sb.get("luas_padam_ha"), errors="coerce"),
        "magnitudo":   pd.to_numeric(df_sb.get("magnitudo"), errors="coerce"),
        "kedalaman_km": pd.to_numeric(df_sb.get("kedalaman_km"), errors="coerce"),
        "tinggi_genangan_cm": pd.to_numeric(df_sb.get("tinggi_genangan_cm"), errors="coerce"),
        "rumah_terdampak": pd.to_numeric(df_sb.get("rumah_terdampak"), errors="coerce"),
        "korban_jiwa": pd.to_numeric(df_sb.get("korban_jiwa"), errors="coerce").fillna(0).astype(int),
        "pengungsi":   pd.to_numeric(df_sb.get("pengungsi"), errors="coerce").fillna(0).astype(int),
        "ispa":        pd.to_numeric(df_sb.get("ispa"), errors="coerce").fillna(0).astype(int),
        "penyebab":    df_sb.get("jenis_bencana").apply(
            lambda j: j if j not in ("Karhutla", "Banjir", "Gempa", None) else "-"),
        "status_verifikasi": "Perlu Verifikasi",
        "sumber":      "Laporan Teks (" + df_sb.get("subdit").fillna("-").astype(str) + ")",
    })
    out = out.dropna(subset=["tanggal"]).copy()
    # Lat/lon fallback dari PROVINSI (biar titik muncul di peta)
    try:
        from data_generator import PROVINSI
        out["lat"] = out["provinsi"].map(lambda p: PROVINSI.get(p, {}).get("lat"))
        out["lon"] = out["provinsi"].map(lambda p: PROVINSI.get(p, {}).get("lon"))
    except Exception:  # noqa: BLE001
        out["lat"] = None
        out["lon"] = None
    return out


def clear_cache():
    """Clear cache fetch (dipakai setelah insert/delete)."""
    try:
        fetch_all.clear()
    except Exception:
        pass
