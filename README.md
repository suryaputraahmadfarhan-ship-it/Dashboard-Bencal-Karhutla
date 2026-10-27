# Dashboard Kebencanaan - Direktorat 2.3 (BIN Deputi 2)

Monitoring kejadian bencana (karhutla, banjir, gempa, bencana alam lainnya) dan hotspot di
15 provinsi Sumatera & Kalimantan, dengan login **Admin** dan **Personel**.

## Menjalankan
```
pip install -r requirements.txt
streamlit run app.py
```
Aplikasi butuh akun di `.streamlit/secrets.toml` (lihat `.streamlit/secrets.toml.example`).
Buat hash password dengan `python hash_password.py`. **Jangan commit secrets.toml.**

## Struktur
- `app.py` - aplikasi utama (login, navigasi, halaman)
- `auth.py`, `auth_hash.py`, `hash_password.py` - login, hash PBKDF2, pembuat hash
- `theme.py` - tampilan (CSS, kartu KPI)
- `data_generator.py` - data demo sintetis
- `data_utils.py` - normalisasi file upload, format, periode
- `report.py` - laporan Word (.docx) dan Excel
- `.streamlit/config.toml` - tema dan pengaturan

## Kolom data kejadian (template upload)
Kolom umum: `tanggal, provinsi, kabupaten, tipe_bencana, korban_jiwa, pengungsi, penyebab, status_verifikasi, sumber, lat, lon`.

Kolom spesifik per jenis (isi kolom yang relevan saja, sisanya boleh kosong):
- **Karhutla**: `luas_ha`, `ispa`
- **Banjir**: `tinggi_genangan_cm`, `rumah_terdampak`, `luas_ha` (opsional)
- **Gempa**: `magnitudo` (SR), `kedalaman_km`, `rumah_terdampak`
- **Bencana Alam Lainnya**: `rumah_terdampak`

Alias didukung: `magnitude`/`mw`/`sr` → `magnitudo`, `depth` → `kedalaman_km`, `genangan` → `tinggi_genangan_cm`, `rumah_rusak` → `rumah_terdampak`. Kolom numerik yang dikosongkan dianggap "tidak berlaku" dan diabaikan saat agregasi, jadi gempa tanpa `luas_ha` tidak merusak total luas terdampak.

## Peran
- **Admin**: semua halaman + Pengelolaan Data (upload, log akses, daftar akun) + unduh data mentah
- **Personel**: Beranda, Data & Grafik, Peta, Rekap Wilayah, Laporan (Word & rekap Excel)

Mode peta tanpa internet: set environment `MAP_STYLE=white-bg`.
