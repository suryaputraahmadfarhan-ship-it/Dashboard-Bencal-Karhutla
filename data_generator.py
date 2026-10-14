# -*- coding: utf-8 -*-
"""Generator data sintetis Bencana Alam - wilayah Sumatera & Kalimantan (Dir 2.3 BIN)."""
import numpy as np
import pandas as pd

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

TIPE_BENCANA = ["Karhutla", "Banjir", "Gempa", "Bencana Alam Lainnya"]
SEVERITY = ["Ringan", "Sedang", "Berat", "Sangat Berat"]
STATUS_LAPORAN = ["Lengkap", "Belum Lengkap", "Perlu Verifikasi"]
PENYEBAB_KARHUTLA = ["Alam (kekeringan)", "Manusia (pembakaran lahan)", "Pertanian", "Perkebunan", "Tidak diketahui"]


def _dates(n, rng, start="2025-01-01", end="2025-10-31"):
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    span = (end_ts - start_ts).days
    offsets = rng.integers(0, span + 1, size=n)
    return [start_ts + pd.Timedelta(days=int(d)) for d in offsets]


def generate_incidents(n=480, seed=42):
    rng = np.random.default_rng(seed)
    provs = list(PROVINSI.keys())
    weights = np.ones(len(provs)) / len(provs)
    p_choice = rng.choice(provs, size=n, p=weights)
    rows = []
    for i, prov in enumerate(p_choice):
        info = PROVINSI[prov]
        kab = rng.choice(info["kab"])
        tipe = rng.choice(TIPE_BENCANA, p=[0.30, 0.35, 0.15, 0.20])
        rows.append({
            "id_kejadian": f"B-{100000 + i}",
            "tanggal": None,
            "provinsi": prov,
            "kabupaten": kab,
            "lat": info["lat"] + rng.uniform(-0.6, 0.6),
            "lon": info["lon"] + rng.uniform(-0.8, 0.8),
            "tipe_bencana": tipe,
            "luas_ha": round(float(rng.exponential(14) + 1), 2),
            "korban_jiwa": int(rng.poisson(0.3)),
            "korban_luka": int(rng.poisson(2.5)),
            "pengungsi": int(rng.poisson(35)),
            "ispa": int(rng.poisson(12 if tipe == "Karhutla" else 2)),
            "penyebab": (
                rng.choice(PENYEBAB_KARHUTLA) if tipe == "Karhutla"
                else rng.choice(["Hujan deras", "Luapan sungai", "Drainase buruk", "Topografi", "Tidak diketahui"]) if tipe == "Banjir"
                else rng.choice(["Tektonik", "Subduksi", "Sesar aktif", "Vulkanik", "Tidak diketahui"]) if tipe == "Gempa"
                else rng.choice(["Cuaca ekstrem", "Longsor", "Kekeringan", "Tidal wave", "Tidak diketahui"])
            ),
            "status_verifikasi": rng.choice(STATUS_LAPORAN, p=[0.78, 0.14, 0.08]),
            "sumber": "Pusat (Dir 2.3 Deputi 2)",
        })
    df = pd.DataFrame(rows)
    df["tanggal"] = _dates(len(df), rng)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df.sort_values("tanggal").reset_index(drop=True)


def generate_hotspots(seed=42, start="2025-01-01", end="2025-10-31"):
    rng = np.random.default_rng(seed + 7)
    provs = ["Riau", "Jambi", "Sumatera Selatan", "Kalimantan Barat", "Kalimantan Tengah",
             "Kalimantan Selatan", "Kalimantan Timur", "Sumatera Utara", "Aceh", "Lampung"]
    rows = []
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    span = (end_ts - start_ts).days
    # 1-3 hotspots per day
    n_days = min(span + 1, 120)
    chosen_days = sorted(rng.choice(range(span + 1), size=n_days, replace=False))
    hid = 0
    for d in chosen_days:
        tgl = start_ts + pd.Timedelta(days=int(d))
        n_hs = int(rng.integers(1, 6))
        for _ in range(n_hs):
            prov = rng.choice(provs)
            info = PROVINSI[prov]
            rows.append({
                "id_hotspot": f"H-{hid:06d}",
                "tanggal": tgl,
                "provinsi": prov,
                "kabupaten": rng.choice(info["kab"]),
                "lat": info["lat"] + rng.uniform(-0.9, 0.9),
                "lon": info["lon"] + rng.uniform(-1.2, 1.2),
                "confidence": rng.choice(["Low", "Nominal", "High"], p=[0.2, 0.5, 0.3]),
                "satelit": rng.choice(["MODIS", "VIIRS", "Himawari-8"]),
                "frp": round(float(rng.exponential(18) + 3), 2),
                "sumber": "Satelit (Pusat)",
            })
            hid += 1
    df = pd.DataFrame(rows)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df.sort_values("tanggal").reset_index(drop=True)


def generate_all(seed=42, start="2025-01-01", end="2025-10-31"):
    inc = generate_incidents(n=480, seed=seed)
    inc = inc[(inc["tanggal"] >= pd.Timestamp(start)) & (inc["tanggal"] <= pd.Timestamp(end))]
    hs = generate_hotspots(seed=seed, start=start, end=end)
    return inc.reset_index(drop=True), hs.reset_index(drop=True)
