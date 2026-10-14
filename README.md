# Dashboard Karhutla - Sinkronisasi Data Pusat & Daerah

Aplikasi Streamlit untuk monitoring kebakaran hutan dan lahan (Karhutla) serta
rekonsiliasi/sinkronisasi data antara Pusat dan Daerah, guna meminimalisir miss data
dan meningkatkan akurasi & efektivitas penyusunan laporan bencana.

## Fitur Utama

- KPI: total kejadian, luas lahan, provinsi/kabupaten terdampak, miss data, tingkat sinkronisasi
- Peta persebaran karhutla (scatter geo)
- Analisis: per provinsi, penyebab, severity, distribusi luas
- Rekonsiliasi Pusat vs Daerah: status Sinkron / Mismatch / Miss / Ekstra
- Tren waktu (bulanan & mingguan)
- Profil kualitas data & miss data per provinsi
- Upload data sendiri (CSV/Excel Pusat dan Daerah) dengan normalisasi kolom otomatis
- Export laporan rekonsiliasi (CSV & Excel multi-sheet)

## Cara Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Mode Data

1. **Data Sintetis (Demo)**: data contoh Indonesia (provinsi rawan karhutla) dengan simulasi miss/mismatch.
2. **Upload CSV/Excel**: gunakan kolom seperti `tanggal, provinsi, kabupaten, lat, lon, luas_ha, penyebab, severity`.

## Struktur Proyek

- `app.py` - aplikasi Streamlit
- `data_generator.py` - generator data sintetis + fungsi `reconcile`
- `requirements.txt` - dependensi
