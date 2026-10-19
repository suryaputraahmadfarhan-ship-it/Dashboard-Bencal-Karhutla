# -*- coding: utf-8 -*-
"""Generator data sintetis kebencanaan - Sumatera & Kalimantan (Dir 2.3 Deputi 2 BIN).

CATATAN: seluruh data di sini hanya untuk DEMO. Ganti dengan data riil melalui menu
Admin > Sumber Data.
"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

WIB = timezone(timedelta(hours=7))

PROVINSI = {
    # Sumatera (10)
    "Aceh": {"lat": 4.7, "lon": 96.8, "kab": ["Aceh Tamiang", "Aceh Timur", "Pidie"]},
    "Sumatera Utara": {"lat": 2.5, "lon": 99.0, "kab": ["Langkat", "Asahan", "Deli Serdang", "Serdang Bedagai"]},
    "Sumatera Barat": {"lat": -0.9, "lon": 100.5, "kab": ["Padang Pariaman", "Agam", "Pesisir Selatan"]},
    "Riau": {"lat": 1.6, "lon": 102.2, "kab": ["Pelalawan", "Siak", "Indragiri Hulu", "Bengkalis"]},
    "Jambi": {"lat": -1.5, "lon": 103.4, "kab": ["Muaro Jambi", "Tanjung Jabung Timur", "Sarolangun"]},
    "Sumatera Selatan": {"lat": -2.9, "lon": 104.1, "kab": ["Ogan Komering Ilir", "Musi Banyuasin", "Banyuasin"]},
    "Bengkulu": {"lat": -3.8, "lon": 102.3, "kab": ["Bengkulu Selatan", "Seluma", "Kaur"]},
    "Lampung": {"lat": -4.8, "lon": 105.0, "kab": ["Lampung Selatan", "Pringsewu", "Tanggamus"]},
    "Kepulauan Bangka Belitung": {"lat": -2.1, "lon": 106.1, "kab": ["Bangka", "Belitung", "Bangka Tengah"]},
    "Kepulauan Riau": {"lat": 1.0, "lon": 104.0, "kab": ["Bintan", "Karimun", "Natuna"]},
    # Kalimantan (5)
    "Kalimantan Barat": {"lat": -0.3, "lon": 110.5, "kab": ["Kubu Raya", "Mempawah", "Sanggau", "Pontianak"]},
    "Kalimantan Tengah": {"lat": -2.2, "lon": 113.9, "kab": ["Pulang Pisau", "Kapuas", "Katingan", "Gunung Mas"]},
    "Kalimantan Selatan": {"lat": -3.3, "lon": 115.2, "kab": ["Banjar", "Hulu Sungai Utara", "Tanah Laut"]},
    "Kalimantan Timur": {"lat": 0.5, "lon": 116.4, "kab": ["Kutai Kartanegara", "Berau", "Paser"]},
    "Kalimantan Utara": {"lat": 3.0, "lon": 116.7, "kab": ["Bulungan", "Nunukan", "Tana Tidung"]},
}

SUMATERA = list(PROVINSI.keys())[:10]
KALIMANTAN = list(PROVINSI.keys())[10:]

TIPE_BENCANA = ["Karhutla", "Banjir", "Gempa", "Bencana Alam Lainnya"]
STATUS_LAPORAN = ["Lengkap", "Belum Lengkap", "Perlu Verifikasi"]
PENYEBAB_KARHUTLA = ["Alam (kekeringan)", "Manusia (pembakaran lahan)", "Pertanian", "Perkebunan", "Tidak diketahui"]

# Bobot relatif sebaran hotspot (provinsi rawan karhutla lebih berat)
_HS_WEIGHT = {
    "Riau": 9, "Jambi": 6, "Sumatera Selatan": 10, "Kalimantan Barat": 13,
    "Kalimantan Tengah": 8, "Kalimantan Selatan": 4, "Kalimantan Timur": 5,
    "Sumatera Utara": 3, "Aceh": 2, "Lampung": 2, "Kepulauan Bangka Belitung": 2,
    "Bengkulu": 1, "Sumatera Barat": 1, "Kepulauan Riau": 1, "Kalimantan Utara": 2,
}


def today_wib():
    return datetime.now(WIB).date()


def generate_incidents(n=1400, seed=42, start=None, end=None):
    rng = np.random.default_rng(seed)
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    span = (end_ts - start_ts).days
    provs = list(PROVINSI.keys())
    p_choice = rng.choice(provs, size=n)
    rows = []
    for i, prov in enumerate(p_choice):
        info = PROVINSI[prov]
        tipe = rng.choice(TIPE_BENCANA, p=[0.47, 0.27, 0.13, 0.13])
        row = {
            "id_kejadian": f"B-{100000 + i}",
            "tanggal": start_ts + pd.Timedelta(days=int(rng.integers(0, span + 1))),
            "provinsi": prov,
            "kabupaten": rng.choice(info["kab"]),
            "lat": info["lat"] + rng.uniform(-0.6, 0.6),
            "lon": info["lon"] + rng.uniform(-0.8, 0.8),
            "tipe_bencana": tipe,
            "luas_ha": np.nan,
            "magnitudo": np.nan,
            "kedalaman_km": np.nan,
            "tinggi_genangan_cm": np.nan,
            "rumah_terdampak": np.nan,
            "korban_jiwa": 0,
            "korban_luka": 0,
            "pengungsi": 0,
            "ispa": 0,
            "status_verifikasi": rng.choice(STATUS_LAPORAN, p=[0.78, 0.14, 0.08]),
            "sumber": "Pusat (Dir 2.3 Deputi 2)",
        }
        if tipe == "Karhutla":
            row["penyebab"] = rng.choice(PENYEBAB_KARHUTLA)
            row["luas_ha"] = round(float(rng.exponential(18) + 2), 2)
            row["ispa"] = int(rng.poisson(1.8))
            row["pengungsi"] = int(rng.poisson(12))
            row["korban_jiwa"] = int(rng.poisson(0.02))
            row["korban_luka"] = int(rng.poisson(0.4))
        elif tipe == "Banjir":
            row["penyebab"] = rng.choice(["Hujan deras", "Luapan sungai", "Drainase buruk", "Topografi",
                                          "Tidak diketahui"])
            row["tinggi_genangan_cm"] = int(rng.integers(20, 220))
            row["rumah_terdampak"] = int(rng.poisson(95))
            row["luas_ha"] = round(float(rng.exponential(8) + 1), 2)
            row["pengungsi"] = int(rng.poisson(140))
            row["korban_jiwa"] = int(rng.poisson(0.08))
            row["korban_luka"] = int(rng.poisson(1.2))
        elif tipe == "Gempa":
            row["penyebab"] = rng.choice(["Tektonik", "Subduksi", "Sesar aktif", "Vulkanik", "Tidak diketahui"])
            row["magnitudo"] = round(float(np.clip(rng.normal(4.6, 0.9), 2.5, 7.8)), 1)
            row["kedalaman_km"] = int(np.clip(rng.exponential(45) + 5, 5, 300))
            row["rumah_terdampak"] = int(rng.poisson(28 if row["magnitudo"] > 5 else 3))
            row["pengungsi"] = int(rng.poisson(55 if row["magnitudo"] > 5 else 5))
            row["korban_jiwa"] = int(rng.poisson(0.15 if row["magnitudo"] > 5.5 else 0.01))
            row["korban_luka"] = int(rng.poisson(2.5 if row["magnitudo"] > 5 else 0.3))
        else:  # Bencana Alam Lainnya (longsor, puting beliung, kekeringan, dsb)
            row["penyebab"] = rng.choice(["Cuaca ekstrem", "Longsor", "Kekeringan", "Puting beliung",
                                          "Tidak diketahui"])
            row["rumah_terdampak"] = int(rng.poisson(14))
            row["pengungsi"] = int(rng.poisson(40))
            row["korban_jiwa"] = int(rng.poisson(0.06))
            row["korban_luka"] = int(rng.poisson(0.9))
        rows.append(row)
    df = pd.DataFrame(rows)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df.sort_values("tanggal").reset_index(drop=True)


def generate_hotspots(seed=42, start=None, end=None):
    rng = np.random.default_rng(seed + 7)
    provs = list(PROVINSI.keys())
    w = np.array([_HS_WEIGHT[p] for p in provs], dtype=float)
    w = w / w.sum()
    frames = []
    hid = 0
    for tgl in pd.date_range(start, end, freq="D"):
        total = int(rng.integers(60, 420))
        counts = rng.multinomial(total, w)
        for prov, c in zip(provs, counts):
            if c == 0:
                continue
            info = PROVINSI[prov]
            frames.append(pd.DataFrame({
                "id_hotspot": [f"H-{hid + k:07d}" for k in range(c)],
                "tanggal": tgl,
                "provinsi": prov,
                "kabupaten": rng.choice(info["kab"], size=c),
                "lat": info["lat"] + rng.uniform(-0.9, 0.9, size=c),
                "lon": info["lon"] + rng.uniform(-1.2, 1.2, size=c),
                "confidence": rng.choice(["Low", "Nominal", "High"], p=[0.2, 0.5, 0.3], size=c),
                "satelit": rng.choice(["MODIS", "VIIRS", "Himawari-8"], size=c),
                "frp": np.round(rng.exponential(18, size=c) + 3, 2),
                "sumber": "Satelit (Pusat)",
            }))
            hid += c
    df = pd.concat(frames, ignore_index=True)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df


def generate_all(seed=42, days=120, end=None):
    """Data demo untuk `days` hari terakhir sampai `end` (default: hari ini WIB)."""
    end_d = pd.Timestamp(end or today_wib())
    start_d = end_d - pd.Timedelta(days=days - 1)
    inc = generate_incidents(seed=seed, start=start_d, end=end_d)
    hs = generate_hotspots(seed=seed, start=start_d, end=end_d)
    return inc, hs
