# -*- coding: utf-8 -*-
"""Generator data sintetis Karhutla untuk demo dashboard sinkronisasi Pusat-Daerah."""
import numpy as np
import pandas as pd

PROVINSI = {
    "Riau": {"lat": 1.6, "lon": 102.2, "kab": ["Pelalawan", "Siak", "Indragiri Hulu", "Bengkalis"]},
    "Jambi": {"lat": -1.5, "lon": 103.4, "kab": ["Muaro Jambi", "Tanjung Jabung Timur", "Sarolangun"]},
    "Sumatera Selatan": {"lat": -2.9, "lon": 104.1, "kab": ["Ogan Komering Ilir", "Musi Banyuasin", "Banyuasin"]},
    "Kalimantan Barat": {"lat": -0.3, "lon": 110.5, "kab": ["Kubu Raya", "Mempawah", "Sanggau", "Pontianak"]},
    "Kalimantan Tengah": {"lat": -2.2, "lon": 113.9, "kab": ["Pulang Pisau", "Kapuas", "Katingan", "Gunung Mas"]},
    "Kalimantan Selatan": {"lat": -3.3, "lon": 115.2, "kab": ["Banjar", "Hulu Sungai Utara", "Tanah Laut"]},
    "Kalimantan Timur": {"lat": 0.5, "lon": 116.4, "kab": ["Kutai Kartanegara", "Berau", "Paser"]},
    "Kalimantan Utara": {"lat": 3.0, "lon": 116.7, "kab": ["Bulungan", "Nunukan"]},
    "Aceh": {"lat": 4.7, "lon": 96.8, "kab": ["Aceh Tamiang", "Aceh Timur"]},
    "Sumatera Utara": {"lat": 2.5, "lon": 99.0, "kab": ["Langkat", "Asahan", "Deli Serdang"]},
    "Papua": {"lat": -4.3, "lon": 138.0, "kab": ["Merauke", "Jayapura"]},
    "Papua Barat": {"lat": -1.5, "lon": 133.2, "kab": ["Sorong", "Manokwari"]},
    "Jawa Barat": {"lat": -6.9, "lon": 107.6, "kab": ["Bogor", "Sukabumi", "Garut"]},
    "Jawa Tengah": {"lat": -7.1, "lon": 110.4, "kab": ["Wonosobo", "Banjarnegara", "Pekalongan"]},
    "NTT": {"lat": -8.6, "lon": 121.1, "kab": ["Timor Tengah Selatan", "Kupang"]},
}

PENYEBAB = ["Alam (kekeringan)", "Manusia (pembakaran lahan)", "Pertanian (pembukaan lahan baru)",
            "Perkebunan (clearing)", "Tidak diketahui"]
SEVERITY = ["Ringan", "Sedang", "Berat", "Sangat Berat"]
STATUS_LAPORAN = ["Lengkap", "Belum Lengkap", "Perlu Verifikasi"]


def _dates(n, rng, start="2025-01-01", end="2025-10-31"):
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    span = (end_ts - start_ts).days
    offsets = rng.integers(0, span + 1, size=n)
    return [start_ts + pd.Timedelta(days=int(d)) for d in offsets]


def generate_pusat(n=420, seed=42):
    rng = np.random.default_rng(seed)
    provs = list(PROVINSI.keys())
    weights = np.array([14, 8, 10, 12, 15, 7, 9, 3, 4, 5, 6, 4, 3, 3, 4], dtype=float)
    weights = weights / weights.sum()
    p_choice = rng.choice(provs, size=n, p=weights)
    rows = []
    for i, prov in enumerate(p_choice):
        info = PROVINSI[prov]
        kab = rng.choice(info["kab"])
        rows.append({
            "id_laporan": f"P-{100000 + i}",
            "tanggal": None,
            "provinsi": prov,
            "kabupaten": kab,
            "lat": info["lat"] + rng.uniform(-0.6, 0.6),
            "lon": info["lon"] + rng.uniform(-0.8, 0.8),
            "luas_ha": round(float(rng.exponential(18) + 1), 2),
            "penyebab": rng.choice(PENYEBAB, p=[0.15, 0.40, 0.20, 0.15, 0.10]),
            "severity": rng.choice(SEVERITY, p=[0.40, 0.35, 0.20, 0.05]),
            "status_verifikasi": rng.choice(STATUS_LAPORAN, p=[0.75, 0.15, 0.10]),
            "sumber": "Pusat (BIN Deputi-2)",
        })
    df = pd.DataFrame(rows)
    df["tanggal"] = _dates(len(df), rng)
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    return df.sort_values("tanggal").reset_index(drop=True)


def generate_daerah(pusat_df, seed=7, drop_rate=0.12, mismatch_rate=0.15, extra_rate=0.08):
    rng = np.random.default_rng(seed)
    base = pusat_df.copy()
    # drop sebagian -> miss data daerah
    keep_mask = rng.random(len(base)) > drop_rate
    daerah = base[keep_mask].copy()
    # ubah id & sumber
    daerah["id_laporan"] = [f"D-{200000 + i}" for i in range(len(daerah))]
    daerah["sumber"] = "Daerah"
    # mismatch luas pada sebagian
    mismatch_idx = rng.choice(daerah.index, size=int(len(daerah) * mismatch_rate), replace=False)
    daerah.loc[mismatch_idx, "luas_ha"] = daerah.loc[mismatch_idx, "luas_ha"].apply(
        lambda x: round(float(x) * rng.uniform(0.7, 1.35), 2))
    # mismatch penyebab ringan
    if len(mismatch_idx) > 0:
        daerah.loc[mismatch_idx[: len(mismatch_idx) // 3], "penyebab"] = rng.choice(
            PENYEBAB, size=len(mismatch_idx) // 3)
    # extra records daerah
    n_extra = int(len(pusat_df) * extra_rate)
    extra = generate_pusat(n=n_extra, seed=seed + 99)
    extra["id_laporan"] = [f"D-{300000 + i}" for i in range(len(extra))]
    extra["sumber"] = "Daerah"
    daerah = pd.concat([daerah, extra], ignore_index=True)
    daerah["status_verifikasi"] = rng.choice(STATUS_LAPORAN, size=len(daerah), p=[0.6, 0.25, 0.15])
    return daerah.sort_values("tanggal").reset_index(drop=True)


def reconcile(pusat_df, daerah_df):
    p = pusat_df.copy()
    d = daerah_df.copy()
    p["_key"] = p["provinsi"].astype(str) + "|" + p["kabupaten"].astype(str) + "|" + p["tanggal"].dt.strftime("%Y-%m-%d")
    d["_key"] = d["provinsi"].astype(str) + "|" + d["kabupaten"].astype(str) + "|" + d["tanggal"].dt.strftime("%Y-%m-%d")

    # agregasi per key (rata2/sum) - perbandingan record-level
    results = []
    keys_p = set(p["_key"])
    keys_d = set(d["_key"])

    for key in sorted(keys_p | keys_d):
        in_p = key in keys_p
        in_d = key in keys_d
        if in_p and in_d:
            pr = p[p["_key"] == key].iloc[0]
            dr = d[d["_key"] == key].iloc[0]
            luas_p = float(pr["luas_ha"])
            luas_d = float(dr["luas_ha"])
            tol = 0.10 * max(luas_p, 1)
            if abs(luas_p - luas_d) <= tol and pr["penyebab"] == dr["penyebab"]:
                status = "Sinkron"
            elif abs(luas_p - luas_d) <= tol:
                status = "Sinkron (angka OK, penyebab beda)"
            else:
                status = "Mismatch (angka beda)"
            results.append({
                "key": key, "tanggal": pr["tanggal"], "provinsi": pr["provinsi"],
                "kabupaten": pr["kabupaten"], "di_pusat": True, "di_daerah": True,
                "luas_pusat": luas_p, "luas_daerah": luas_d,
                "selisih_ha": round(luas_p - luas_d, 2),
                "penyebab_pusat": pr["penyebab"], "penyebab_daerah": dr["penyebab"],
                "severity_pusat": pr["severity"],
                "status": status,
            })
        elif in_p and not in_d:
            pr = p[p["_key"] == key].iloc[0]
            results.append({
                "key": key, "tanggal": pr["tanggal"], "provinsi": pr["provinsi"],
                "kabupaten": pr["kabupaten"], "di_pusat": True, "di_daerah": False,
                "luas_pusat": float(pr["luas_ha"]), "luas_daerah": None,
                "selisih_ha": float(pr["luas_ha"]),
                "penyebab_pusat": pr["penyebab"], "penyebab_daerah": None,
                "severity_pusat": pr["severity"],
                "status": "MISS - Daerah tidak melapor",
            })
        else:
            dr = d[d["_key"] == key].iloc[0]
            results.append({
                "key": key, "tanggal": dr["tanggal"], "provinsi": dr["provinsi"],
                "kabupaten": dr["kabupaten"], "di_pusat": False, "di_daerah": True,
                "luas_pusat": None, "luas_daerah": float(dr["luas_ha"]),
                "selisih_ha": -float(dr["luas_ha"]),
                "penyebab_pusat": None, "penyebab_daerah": dr["penyebab"],
                "severity_pusat": None,
                "status": "Ekstra - Laporan daerah tanpa pusat",
            })

    rdf = pd.DataFrame(results)
    if "tanggal" in rdf.columns:
        rdf["tanggal"] = pd.to_datetime(rdf["tanggal"])
    return rdf


def generate_all(seed=42, drop_rate=0.12, mismatch_rate=0.15, extra_rate=0.08):
    pusat = generate_pusat(seed=seed)
    daerah = generate_daerah(pusat, seed=seed + 1, drop_rate=drop_rate,
                            mismatch_rate=mismatch_rate, extra_rate=extra_rate)
    recon = reconcile(pusat, daerah)
    return pusat, daerah, recon
