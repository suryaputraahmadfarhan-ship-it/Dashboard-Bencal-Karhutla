# -*- coding: utf-8 -*-
"""Pembuat laporan: Word (.docx) format Intel Brief Direktorat 2.3, dan Excel multi-sheet.

Format mengikuti contoh pimpinan: Header → LAMPIRAN → INDIKASI (per provinsi: Perkembangan /
Dampak / Upaya Pemerintah / Penindakan) → ANALISIS → DAMPAK → UPAYA → SARAN TINDAK → Autentikasi.
"""
import io

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from data_utils import fmt_num, tgl_id

NAVY = RGBColor(0x0F, 0x2A, 0x5C)


# ============================================================= util
def _shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _table(doc, header, rows, widths=None, num_cols=()):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        _shade(c, "12307A")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            run = p.add_run(str(v))
            run.font.size = Pt(10)
            if i in num_cols:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    return t


def _ambang(doc, teks, bold=False, italic=False, size=11, color=None, indent=0, after=0):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(indent) if indent else None
    p.paragraph_format.space_after = Pt(after)
    r = p.add_run(teks)
    r.bold = bold
    r.italic = italic
    r.font.size = Pt(size)
    if color is not None:
        r.font.color.rgb = color
    return p


def _bullet(doc, teks, level=0):
    p = doc.add_paragraph(teks, style="List Bullet")
    p.paragraph_format.left_indent = Cm(0.75 + 0.5 * level)
    for r in p.runs:
        r.font.size = Pt(11)
    return p


def _label_isi(doc, label, isi, indent=1.0):
    """Baris 'Label: isi.' dengan label bold."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(indent)
    p.paragraph_format.space_after = Pt(2)
    rl = p.add_run(f"{label}: ")
    rl.bold = True
    rl.font.size = Pt(11)
    ri = p.add_run(isi)
    ri.font.size = Pt(11)
    return p


# ============================================================= header & footer
def _header(doc, ctx):
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(11)

    _ambang(doc, "BADAN INTELIJEN NEGARA", bold=True, size=12, color=NAVY, after=0)
    _ambang(doc, "DIREKTORAT 23", bold=True, size=12, color=NAVY, indent=1.0, after=4)
    doc.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    jenis = ctx.get("jenis", "Semua")
    judul_map = {
        "Semua": "LAPORAN KEBENCANAAN (GABUNGAN) DI WILAYAH SUMATERA DAN KALIMANTAN",
        "Karhutla": "LAPORAN KARHUTLA DI WILAYAH SUMATERA DAN KALIMANTAN",
        "Banjir": "LAPORAN BANJIR DI WILAYAH SUMATERA DAN KALIMANTAN",
        "Gempa": "LAPORAN GEMPA DI WILAYAH SUMATERA DAN KALIMANTAN",
        "Bencana Alam Lainnya": "LAPORAN BENCANA ALAM LAINNYA DI WILAYAH SUMATERA DAN KALIMANTAN",
    }
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run(judul_map.get(jenis, f"LAPORAN {jenis.upper()} DI WILAYAH SUMATERA DAN KALIMANTAN"))
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = NAVY

    # Keterangan periode & tanggal data
    _ambang(doc, f"Periode: {ctx['periode']}   ·   Data per: {ctx['data_per']}   ·   "
                 f"Wilayah: {ctx['wilayah']}", italic=True, size=10, after=10)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    if ctx.get("demo"):
        _ambang(doc, "Catatan: dokumen ini dibuat dari DATA DEMO (sintetis), bukan data riil.",
                bold=True, size=10, color=RGBColor(0xB4, 0x53, 0x09))

    _ambang(doc, "LAMPIRAN :", bold=True, size=12, color=NAVY, after=4)


def _autentikasi(doc, ctx):
    doc.add_paragraph()
    _ambang(doc, "Autentikasi :", bold=True, size=11, color=NAVY, after=2)
    _ambang(doc, f"Disusun oleh: {ctx.get('pembuat', '-')}", size=10, after=0)
    _ambang(doc, "Diverifikasi oleh: Kabag TU Direktorat 2.3 (_______________________)", size=10, after=0)
    _ambang(doc, "Disetujui oleh: Direktur 2.3 Deputi 2 BIN (_______________________)", size=10, after=10)
    _ambang(doc, "Dokumen ini dihasilkan otomatis dari Dashboard Kebencanaan Direktorat 2.3 "
                 "dan perlu diverifikasi petugas sebelum disampaikan ke pimpinan.",
            italic=True, size=9)


# ============================================================= generator deskripsi per provinsi
def _desc_perkembangan(prov, jenis, g, hs_prov):
    """Narasi 'Perkembangan' untuk provinsi tertentu, basis dari data agregat `g` (DataFrame baris per provinsi)."""
    n = int(g["kejadian"].iloc[0]) if len(g) else 0
    kabs = g.get("daftar_kabupaten", pd.Series([""])).iloc[0] if "daftar_kabupaten" in g.columns else ""
    jml_kab = int(g.get("jml_kab", pd.Series([0])).iloc[0]) if "jml_kab" in g.columns else 0

    bits = []
    if jenis == "Karhutla":
        luas = float(g["luas_ha"].iloc[0]) if "luas_ha" in g.columns else 0
        s = f"Tercatat {fmt_num(n)} kejadian karhutla seluas ±{fmt_num(luas, 2)} Ha"
        if jml_kab:
            s += f" di {jml_kab} kabupaten/kota"
        if kabs:
            s += f", dengan sebaran utama di {kabs}"
        s += "."
        bits.append(s)
        if hs_prov is not None and hs_prov > 0:
            bits.append(f"Pada data pantauan satelit terakhir, tercatat {fmt_num(hs_prov)} titik hotspot di "
                        f"wilayah {prov}.")
    elif jenis == "Banjir":
        rt = int(g.get("rumah_terdampak", pd.Series([0])).iloc[0] or 0)
        tg = float(g.get("tinggi_genangan_cm", pd.Series([0])).iloc[0] or 0)
        s = f"Tercatat {fmt_num(n)} kejadian banjir"
        if jml_kab:
            s += f" di {jml_kab} kabupaten/kota"
        if kabs:
            s += f", dengan konsentrasi di {kabs}"
        s += "."
        bits.append(s)
        detail = []
        if tg:
            detail.append(f"tinggi genangan rata-rata ±{fmt_num(tg, 0)} cm")
        if rt:
            detail.append(f"{fmt_num(rt)} rumah terdampak/terendam")
        if detail:
            bits.append("Dampak fisik: " + ", ".join(detail) + ".")
    elif jenis == "Gempa":
        mag = float(g.get("magnitudo_maks", pd.Series([0])).iloc[0] or 0)
        kdl = float(g.get("kedalaman_rata", pd.Series([0])).iloc[0] or 0)
        rt = int(g.get("rumah_terdampak", pd.Series([0])).iloc[0] or 0)
        s = f"Tercatat {fmt_num(n)} kejadian gempa"
        if mag:
            s += f" dengan magnitudo tertinggi {fmt_num(mag, 1)} SR"
        if kdl:
            s += f" (kedalaman rata-rata ±{fmt_num(kdl, 0)} km)"
        if jml_kab:
            s += f", tersebar di {jml_kab} kabupaten/kota"
        s += "."
        bits.append(s)
        if rt:
            bits.append(f"Teridentifikasi {fmt_num(rt)} rumah terdampak akibat guncangan.")
    else:  # Bencana Alam Lainnya
        rt = int(g.get("rumah_terdampak", pd.Series([0])).iloc[0] or 0)
        s = f"Tercatat {fmt_num(n)} kejadian bencana alam lainnya"
        if jml_kab:
            s += f" di {jml_kab} kabupaten/kota"
        if kabs:
            s += f" (antara lain di {kabs})"
        s += "."
        bits.append(s)
        if rt:
            bits.append(f"Dampak fisik mencakup {fmt_num(rt)} rumah terdampak.")
    return " ".join(bits) if bits else "Belum terdapat data signifikan pada periode pelaporan."


def _desc_dampak(prov, jenis, g):
    kj = int(g.get("korban_jiwa", pd.Series([0])).iloc[0] or 0)
    pg = int(g.get("pengungsi", pd.Series([0])).iloc[0] or 0)
    ispa = int(g.get("ispa", pd.Series([0])).iloc[0] or 0)
    bits = []
    if jenis == "Karhutla":
        if ispa:
            bits.append(f"Kabut asap karhutla berdampak pada kesehatan masyarakat, tercatat {fmt_num(ispa)} "
                        f"kasus ISPA di wilayah {prov}.")
        else:
            bits.append(f"Secara umum belum terdapat kasus ISPA signifikan akibat karhutla di {prov} "
                        f"pada periode pelaporan.")
        if kj:
            bits.append(f"Dilaporkan {fmt_num(kj)} korban jiwa akibat kejadian ini.")
        if pg:
            bits.append(f"Sebanyak {fmt_num(pg)} warga mengungsi untuk menghindari paparan asap.")
    elif jenis == "Banjir":
        detail = []
        if pg:
            detail.append(f"{fmt_num(pg)} warga mengungsi")
        if kj:
            detail.append(f"{fmt_num(kj)} korban jiwa dilaporkan")
        if detail:
            bits.append("Dampak sosial-kemanusiaan: " + "; ".join(detail) + ".")
        bits.append("Gangguan aktivitas warga meliputi terputusnya akses jalan, kerusakan sarana publik, "
                    "serta terhambatnya aktivitas ekonomi.")
    elif jenis == "Gempa":
        detail = []
        if kj:
            detail.append(f"{fmt_num(kj)} korban jiwa")
        if pg:
            detail.append(f"{fmt_num(pg)} pengungsi")
        if detail:
            bits.append("Dampak terhadap masyarakat: " + "; ".join(detail) + ".")
        else:
            bits.append("Belum ada laporan korban jiwa pada periode ini; dampak lebih dominan pada "
                        "kerusakan bangunan.")
    else:
        if kj:
            bits.append(f"Tercatat {fmt_num(kj)} korban jiwa pada periode pelaporan.")
        if pg:
            bits.append(f"Sebanyak {fmt_num(pg)} warga mengungsi.")
        if not bits:
            bits.append("Dampak terbatas pada kerusakan fisik dan gangguan aktivitas warga di lokasi kejadian.")
    return " ".join(bits)


def _upaya_pemerintah(jenis):
    base = {
        "Karhutla": ("Pemadaman dilakukan oleh armada gabungan daerah (BPBD, TNI/Polri, Manggala Agni) "
                     "serta difasilitasi Operasi Modifikasi Cuaca (OMC) dan water bombing dari pusat. "
                     "BINDA wilayah terkait aktif memperkuat deteksi dini dan sosialisasi larangan "
                     "membuka lahan dengan cara dibakar."),
        "Banjir": ("Penanganan dilakukan melalui penyaluran bantuan logistik oleh BPBD setempat dan BNPB, "
                   "pembukaan dapur umum, serta evakuasi warga pada titik rawan. BINDA wilayah terkait "
                   "memperkuat pemantauan debit sungai dan deteksi dini curah hujan ekstrem."),
        "Gempa": ("Tim gabungan BPBD, TNI/Polri, dan SAR melakukan asesmen cepat kerusakan dan penyediaan "
                  "kebutuhan dasar bagi warga terdampak. BINDA wilayah terkait memperkuat koordinasi "
                  "dengan BMKG untuk pemantauan gempa susulan."),
        "Bencana Alam Lainnya": ("Penanganan dilakukan oleh BPBD setempat bersama TNI/Polri untuk evakuasi, "
                                 "distribusi logistik, dan perbaikan sarana vital. BINDA wilayah terkait "
                                 "memperkuat pemetaan daerah rawan dan sistem peringatan dini."),
    }
    return base.get(jenis, base["Bencana Alam Lainnya"])


def _penindakan(jenis):
    base = {
        "Karhutla": ("Mayoritas kejadian terjadi akibat kelalaian warga dan praktik pembukaan lahan dengan "
                     "cara dibakar. Penegakan hukum terus dioptimalkan oleh Polda setempat bersama KLHK "
                     "melalui penyelidikan sumber api dan penyegelan konsesi yang terbakar."),
        "Banjir": ("Investigasi penyebab banjir mencakup pemeriksaan kondisi tata ruang, drainase, serta "
                   "potensi pelanggaran alih fungsi lahan dan aktivitas yang mengganggu daerah tangkapan air."),
        "Gempa": ("Fokus penanganan pada rehabilitasi sarana vital dan verifikasi standar bangunan tahan "
                  "gempa; pendalaman dilakukan terkait kesesuaian konstruksi di daerah terdampak."),
        "Bencana Alam Lainnya": ("Pendalaman penyebab diperlukan untuk memetakan apakah terdapat unsur "
                                 "kelalaian atau pelanggaran yang perlu ditindaklanjuti pihak berwenang."),
    }
    return base.get(jenis, base["Bencana Alam Lainnya"])


# ============================================================= templat ANALISIS / DAMPAK / UPAYA / SARAN
def _analisis(jenis, ctx):
    cur_total = sum(int(r.kejadian) for r in ctx["per_prov_full"].itertuples())
    ispa_total = int(ctx["per_prov_full"]["ispa"].sum()) if "ispa" in ctx["per_prov_full"].columns else 0
    kj_total = int(ctx["per_prov_full"]["korban_jiwa"].sum()) if "korban_jiwa" in ctx["per_prov_full"].columns else 0
    teks = []
    if jenis == "Karhutla":
        teks.append(f"Pada periode {ctx['periode']}, tercatat total {fmt_num(cur_total)} kejadian karhutla di "
                    f"wilayah {ctx['wilayah']}. Penanganan menjadi perhatian pemerintah pusat dan daerah "
                    "melalui penetapan status siaga/tanggap darurat, pembentukan satgas, penguatan "
                    "koordinasi lintas sektor, serta dukungan anggaran dan peralatan.")
        teks.append("Karhutla berpotensi menimbulkan dampak ekonomi dan sosial melalui kerusakan lahan "
                    "pertanian, perkebunan dan kehutanan, terganggunya transportasi, distribusi barang "
                    "dan aktivitas masyarakat, serta meningkatnya risiko gangguan kesehatan terutama "
                    "pada kelompok rentan.")
        if ispa_total:
            teks.append(f"Dampak kesehatan tercatat {fmt_num(ispa_total)} kasus ISPA kumulatif. "
                        "Pemanfaatan teknologi melalui pemantauan hotspot berbasis satelit, Fire Danger "
                        "Rating System (FDRS), patroli udara, helikopter water bombing, Operasi Modifikasi "
                        "Cuaca (OMC) dan pemantauan kualitas udara dioptimalkan.")
    elif jenis == "Banjir":
        teks.append(f"Pada periode {ctx['periode']}, tercatat total {fmt_num(cur_total)} kejadian banjir di "
                    f"wilayah {ctx['wilayah']}. Pola kejadian menunjukkan keterkaitan dengan curah hujan "
                    "ekstrem, luapan sungai, serta tingkat kesiapsiagaan infrastruktur drainase.")
        teks.append("Banjir berdampak pada mobilitas warga, kerusakan rumah dan sarana publik, serta "
                    "potensi gangguan distribusi logistik di wilayah terdampak.")
        if kj_total:
            teks.append(f"Dilaporkan {fmt_num(kj_total)} korban jiwa pada periode ini; evaluasi "
                        "kesiapsiagaan dan respons darurat perlu diperkuat.")
    elif jenis == "Gempa":
        teks.append(f"Pada periode {ctx['periode']}, tercatat total {fmt_num(cur_total)} kejadian gempa di "
                    f"wilayah {ctx['wilayah']}. Pola kedalaman dan magnitudo menjadi indikator utama "
                    "untuk menakar risiko kerusakan dan korban.")
        teks.append("Dampak gempa mencakup kerusakan bangunan, gangguan aktivitas ekonomi, dan risiko "
                    "gempa susulan yang memerlukan kesiapan evakuasi berkelanjutan.")
    elif jenis == "Bencana Alam Lainnya":
        teks.append(f"Pada periode {ctx['periode']}, tercatat total {fmt_num(cur_total)} kejadian bencana "
                    "alam lainnya (longsor, puting beliung, kekeringan, dsb). Pola kejadian umumnya "
                    "berkaitan dengan kondisi cuaca ekstrem dan karakteristik topografi wilayah.")
        teks.append("Pemetaan daerah rawan, penguatan sistem peringatan dini, dan edukasi masyarakat "
                    "menjadi kunci mitigasi risiko ke depan.")
    else:  # Semua
        teks.append(f"Pada periode {ctx['periode']}, tercatat total {fmt_num(cur_total)} kejadian bencana "
                    f"(seluruh jenis) di wilayah {ctx['wilayah']}. Karhutla, banjir, gempa, dan bencana "
                    "lainnya menunjukkan pola yang bervariasi antarwilayah dan memerlukan pendekatan "
                    "penanganan yang berbeda.")
        teks.append("Pemerintah pusat dan daerah terus memperkuat koordinasi lintas sektor melalui "
                    "penetapan status siaga, pembentukan satgas gabungan, dukungan anggaran, dan "
                    "pemanfaatan teknologi deteksi dini.")
    return teks


def _dampak_potensial(jenis):
    base_karhutla = [
        "Berpotensi terjadi penurunan kualitas udara yang lebih luas akibat sebaran asap karhutla, "
        "termasuk hingga wilayah Kepri dan negara tetangga, yang dapat mengganggu kesehatan dan aktivitas "
        "masyarakat.",
        "Berpotensi terjadi gangguan transportasi udara akibat menurunnya visibility di sejumlah bandara "
        "utama di Sumatera dan Kalimantan.",
        "Berpotensi terjadi gangguan transportasi laut dan perairan akibat menurunnya jarak pandang, yang "
        "dapat menghambat aktivitas nelayan, pelayaran dan distribusi barang antarwilayah.",
        "Berpotensi terjadi peningkatan gangguan kesehatan masyarakat akibat paparan asap, terutama "
        "kelompok rentan, seiring meningkatnya kasus ISPA di wilayah terdampak.",
        "Berpotensi terjadi gangguan kegiatan pendidikan akibat kualitas udara yang tidak sehat, berupa "
        "penerapan BDR/PJJ dan pembatasan aktivitas luar ruangan di sejumlah wilayah.",
        "Berpotensi terjadi kerugian ekonomi akibat terganggunya aktivitas perkebunan, pertanian, "
        "perdagangan, distribusi barang dan mobilitas masyarakat.",
        "Berpotensi terjadi kerusakan ekosistem akibat kebakaran berulang pada lahan gambut, perkebunan "
        "dan kawasan hutan, termasuk kawasan konservasi.",
        "Berpotensi meningkatkan keresahan masyarakat dan tuntutan terhadap pemerintah terkait penanganan "
        "karhutla apabila kebakaran dan dampaknya berlangsung berkepanjangan.",
    ]
    base_banjir = [
        "Berpotensi terjadi perluasan wilayah terdampak banjir seiring kondisi curah hujan ekstrem dan "
        "kejenuhan tanah.",
        "Berpotensi terjadi kerusakan infrastruktur publik (jalan, jembatan, drainase) dan rumah warga "
        "yang menambah beban rehabilitasi.",
        "Berpotensi terjadi gangguan distribusi logistik dan aktivitas ekonomi akibat terputusnya akses "
        "antarwilayah.",
        "Berpotensi terjadi peningkatan penyakit menular pasca-banjir (diare, DBD, leptospirosis) di "
        "wilayah terdampak.",
        "Berpotensi terjadi keresahan sosial akibat lambatnya penanganan pengungsi dan distribusi bantuan.",
        "Berpotensi terjadi kerugian pertanian/perikanan akibat lahan tergenang dan rusaknya tambak/kolam.",
    ]
    base_gempa = [
        "Berpotensi terjadi gempa susulan dengan skala yang dapat memperparah kerusakan bangunan rentan.",
        "Berpotensi terjadi kerusakan bangunan publik (sekolah, rumah sakit, pasar) yang mengganggu "
        "pelayanan masyarakat.",
        "Berpotensi terjadi kerugian ekonomi akibat terhentinya aktivitas produksi, perdagangan dan jasa.",
        "Berpotensi terjadi trauma psikis pada masyarakat terdampak yang memerlukan dukungan kesehatan jiwa.",
        "Berpotensi terjadi keresahan masyarakat terkait kualitas konstruksi bangunan di daerah rawan.",
    ]
    base_lain = [
        "Berpotensi terjadi perluasan dampak ke wilayah sekitar seiring kondisi cuaca dan karakteristik "
        "topografi.",
        "Berpotensi terjadi kerusakan rumah dan sarana publik yang menambah beban rehabilitasi.",
        "Berpotensi terjadi gangguan aktivitas warga dan terputusnya akses pada titik tertentu.",
        "Berpotensi terjadi keresahan masyarakat apabila penanganan dan pemulihan berlangsung lambat.",
    ]
    base_gabungan = base_karhutla[:4] + base_banjir[:2] + base_gempa[:2]
    return {
        "Karhutla": base_karhutla, "Banjir": base_banjir, "Gempa": base_gempa,
        "Bencana Alam Lainnya": base_lain, "Semua": base_gabungan,
    }.get(jenis, base_lain)


def _upaya(jenis):
    """Daftar langkah 'UPAYA' — Deputi II memerintahkan Kabinda Wilayah Sumakal untuk..."""
    jenis_text = {"Karhutla": "karhutla", "Banjir": "banjir", "Gempa": "gempa",
                  "Bencana Alam Lainnya": "bencana alam lainnya"}.get(jenis, "kebencanaan")
    langkah = [
        f"Melakukan monitoring, pendalaman dan pemetaan wilayah rawan, kejadian berulang, pola sebaran, "
        f"serta dampak kesehatan terkait {jenis_text} sebagai bahan deteksi dan peringatan dini.",
        "Berkoordinasi dengan BPBD, BMKG, TNI/Polri, Pemda dan dinas terkait untuk memperkuat pemantauan, "
        "patroli, kesiapsiagaan personel/peralatan serta penanganan di lapangan.",
        f"Berkoordinasi dengan Pemda dan sektor swasta terkait untuk meningkatkan kesiapsiagaan, sarana "
        f"prasarana, patroli pencegahan dan dukungan penanganan {jenis_text} serta mendorong penegakan "
        "hukum sesuai peraturan yang berlaku.",
        "Melakukan pendalaman terhadap sumber dan indikasi penyebab, kepemilikan lahan/aset, pola "
        "kejadian berulang serta perkembangan penindakan hukum guna memperkuat deteksi dan cegah dini.",
        "Melakukan penggalangan tokoh masyarakat, tokoh adat, dan komunitas relawan untuk memperkuat "
        "edukasi, pencegahan, pelaporan dini dan partisipasi masyarakat.",
        "Melakukan peninjauan lapangan dan menyiagakan tim respons cepat untuk edukasi masyarakat serta "
        "pelaporan dini.",
        "Berkoordinasi dengan media massa untuk memperkuat publikasi informasi secara cepat, faktual dan "
        "berimbang serta mengantisipasi berkembangnya narasi negatif.",
        "Melakukan patroli siber terhadap hoaks dan narasi provokasi, serta melaksanakan amplifikasi "
        f"narasi positif terkait penanganan {jenis_text}.",
    ]
    if jenis == "Karhutla":
        langkah.insert(0, "Melakukan monitoring dan pendalaman perkembangan hotspot, titik api, kualitas "
                       "udara, serta kasus ISPA sebagai bahan deteksi dan peringatan dini.")
    elif jenis == "Banjir":
        langkah.insert(0, "Melakukan monitoring kondisi sungai, curah hujan, dan titik rawan banjir sebagai "
                       "bahan deteksi dan peringatan dini.")
    elif jenis == "Gempa":
        langkah.insert(0, "Melakukan monitoring aktivitas seismik, gempa susulan, dan kondisi bangunan "
                       "vital di wilayah terdampak sebagai bahan deteksi dan peringatan dini.")
    return langkah


def _saran_tindak(jenis):
    saran = {
        "Karhutla": [
            "Kementerian Kehutanan meningkatkan pemetaan dan pengawasan terhadap lokasi karhutla "
            "berulang, khususnya pada kawasan hutan, perkebunan dan lahan gambut, dengan memanfaatkan "
            "data hotspot dan riwayat kejadian.",
            "Polri memperkuat penyelidikan dan penegakan hukum terhadap kejadian karhutla dengan "
            "menelusuri tidak hanya pelaku pembakaran di lapangan, tetapi juga kepemilikan atau "
            "penguasaan lahan serta pihak yang bertanggung jawab.",
            "Pemerintah Daerah bersama Satgas Karhutla meningkatkan kesiapsiagaan menghadapi periode "
            "kemarau dan kondisi cuaca berisiko melalui patroli darat, pemantauan hotspot berkala, "
            "dan percepatan pemadaman.",
            "BNPB/BPBD bersama TNI-Polri memastikan kesiapan personel dan sarana pemadaman, termasuk "
            "ketersediaan sumber air dan akses menuju lokasi rawan, terutama pada wilayah gambut.",
            "Instansi Kesehatan meningkatkan pemantauan kualitas udara dan kondisi kesehatan masyarakat "
            "di wilayah terdampak karhutla serta memperkuat penyampaian peringatan kesehatan sebagai "
            "langkah mitigasi.",
            "Instansi Pendidikan bersama Pemerintah Daerah menyiapkan langkah penyesuaian kegiatan "
            "belajar mengajar pada wilayah terdampak kabut asap, termasuk penerapan pembelajaran "
            "jarak jauh apabila diperlukan.",
            "Pemerintah Daerah bersama tokoh adat, kelompok masyarakat dan organisasi lingkungan "
            "memperkuat koordinasi serta pelibatan masyarakat dalam pencegahan dan pelaporan dini "
            "karhutla.",
        ],
        "Banjir": [
            "Kementerian PUPR mempercepat revitalisasi tanggul, bendung, dan sistem drainase pada "
            "wilayah rawan banjir yang teridentifikasi dari pola kejadian berulang.",
            "Pemerintah Daerah memperkuat Early Warning System (EWS) banjir berbasis komunitas, "
            "menyiapkan jalur dan titik evakuasi, serta memperkuat sosialisasi tanggap bencana.",
            "BNPB/BPBD bersama TNI-Polri memastikan kesiapan personel, perahu karet, dapur umum, dan "
            "logistik darurat di titik rawan banjir.",
            "Instansi Kesehatan mempersiapkan posko kesehatan dan stok obat untuk mengantisipasi "
            "penyakit pasca-banjir (diare, DBD, leptospirosis).",
            "Kementerian LHK mengevaluasi tata guna lahan dan alih fungsi kawasan hulu sebagai bagian "
            "dari pencegahan banjir jangka panjang.",
            "BMKG memperkuat kualitas prakiraan curah hujan ekstrem dan diseminasi informasi ke "
            "pemerintah daerah dan masyarakat.",
        ],
        "Gempa": [
            "BMKG memperkuat sistem monitoring seismik dan diseminasi informasi gempa secara cepat ke "
            "pemerintah daerah dan masyarakat.",
            "Pemerintah Daerah mengevaluasi kesesuaian standar bangunan tahan gempa, terutama pada "
            "fasilitas publik vital (sekolah, rumah sakit, pasar).",
            "BNPB/BPBD bersama TNI-Polri dan Basarnas memastikan kesiapan tim respons cepat, logistik, "
            "serta jalur evakuasi di daerah rawan gempa.",
            "Kementerian PUPR mengevaluasi infrastruktur vital pasca-gempa untuk mencegah kerusakan "
            "lanjutan akibat gempa susulan.",
            "Instansi Kesehatan menyiapkan posko kesehatan dan dukungan psikososial bagi warga "
            "terdampak gempa.",
        ],
        "Bencana Alam Lainnya": [
            "Pemerintah Daerah memperkuat pemetaan daerah rawan bencana (longsor, puting beliung, "
            "kekeringan) dan sosialisasi mitigasi.",
            "BMKG memperkuat prakiraan cuaca ekstrem dan diseminasi peringatan dini ke pemerintah "
            "daerah dan masyarakat.",
            "BNPB/BPBD bersama TNI-Polri memastikan kesiapan personel dan logistik tanggap darurat "
            "pada wilayah rawan.",
            "Kementerian LHK/PUPR mengevaluasi faktor tata ruang dan tata guna lahan yang berpotensi "
            "meningkatkan risiko bencana.",
            "Instansi Kesehatan menyiapkan layanan medis darurat dan pemantauan kondisi kesehatan "
            "warga terdampak.",
        ],
    }
    saran["Semua"] = (saran["Karhutla"][:3] + saran["Banjir"][:2] + saran["Gempa"][:2])
    return saran.get(jenis, saran["Bencana Alam Lainnya"])


# ============================================================= bangun INDIKASI per provinsi
def _bangun_perprovinsi_agg(ctx, df_cur, hs_today_df):
    """Hitung agregasi per provinsi + daftar kabupaten + hotspot (untuk Perkembangan/Dampak)."""
    if df_cur is None or df_cur.empty:
        return pd.DataFrame()
    g = df_cur.groupby("provinsi").agg(
        kejadian=("tipe_bencana", "size"),
        luas_ha=("luas_ha", "sum"),
        korban_jiwa=("korban_jiwa", "sum"),
        pengungsi=("pengungsi", "sum"),
        ispa=("ispa", "sum"),
    )
    if "rumah_terdampak" in df_cur.columns:
        g["rumah_terdampak"] = df_cur.groupby("provinsi")["rumah_terdampak"].sum(min_count=1)
    if "tinggi_genangan_cm" in df_cur.columns:
        g["tinggi_genangan_cm"] = df_cur.groupby("provinsi")["tinggi_genangan_cm"].mean()
    if "magnitudo" in df_cur.columns:
        g["magnitudo_maks"] = df_cur.groupby("provinsi")["magnitudo"].max()
    if "kedalaman_km" in df_cur.columns:
        g["kedalaman_rata"] = df_cur.groupby("provinsi")["kedalaman_km"].mean()

    kabs = df_cur.groupby("provinsi")["kabupaten"].agg(
        lambda s: ", ".join(sorted(set(s))[:4]) + (" dan lainnya" if len(set(s)) > 4 else "")).rename(
        "daftar_kabupaten")
    jmlkab = df_cur.groupby("provinsi")["kabupaten"].nunique().rename("jml_kab")
    g = g.join(kabs).join(jmlkab)

    if hs_today_df is not None and not hs_today_df.empty:
        hs_count = hs_today_df.groupby("provinsi").size().rename("hotspot")
        g = g.join(hs_count, how="left")
    else:
        g["hotspot"] = 0
    g = g.sort_values("kejadian", ascending=False).reset_index()
    return g


# ============================================================= main entry
def build_docx(ctx):
    """Bangun laporan intel brief Direktorat 2.3 dari ctx."""
    doc = Document()
    _header(doc, ctx)

    jenis = ctx.get("jenis", "Semua")
    df_cur = ctx.get("df_cur")  # DataFrame kejadian untuk periode & jenis terpilih
    hs_today_df = ctx.get("hs_today_df")

    # 1. INDIKASI
    _ambang(doc, "INDIKASI", bold=True, size=12, color=NAVY, after=4)
    pp = _bangun_perprovinsi_agg(ctx, df_cur, hs_today_df)
    if pp.empty:
        _ambang(doc, "Tidak terdapat data kejadian pada periode dan filter yang dipilih.", indent=1.0)
    elif jenis == "Semua":
        # Gabungan: susun per JENIS → per PROVINSI
        for tp in ["Karhutla", "Banjir", "Gempa", "Bencana Alam Lainnya"]:
            df_tp = df_cur[df_cur["tipe_bencana"] == tp] if df_cur is not None else None
            if df_tp is None or df_tp.empty:
                continue
            pp_tp = _bangun_perprovinsi_agg(ctx, df_tp, hs_today_df if tp == "Karhutla" else None)
            _ambang(doc, f"A. {tp}", bold=True, size=11, color=NAVY, indent=0.75, after=2)
            for r in pp_tp.itertuples():
                g_row = pp_tp[pp_tp["provinsi"] == r.provinsi]
                _ambang(doc, f"Provinsi {r.provinsi}", bold=True, size=11, indent=1.0, after=2)
                hs_v = int(getattr(r, "hotspot", 0) or 0)
                _label_isi(doc, "Perkembangan", _desc_perkembangan(r.provinsi, tp, g_row, hs_v), indent=1.5)
                _label_isi(doc, "Dampak", _desc_dampak(r.provinsi, tp, g_row), indent=1.5)
                _label_isi(doc, "Upaya Pemerintah", _upaya_pemerintah(tp), indent=1.5)
                _label_isi(doc, "Penindakan", _penindakan(tp), indent=1.5)
    else:
        for r in pp.itertuples():
            g_row = pp[pp["provinsi"] == r.provinsi]
            _ambang(doc, f"Provinsi {r.provinsi}", bold=True, size=11, indent=0.75, after=2)
            hs_v = int(getattr(r, "hotspot", 0) or 0)
            _label_isi(doc, "Perkembangan", _desc_perkembangan(r.provinsi, jenis, g_row, hs_v), indent=1.25)
            _label_isi(doc, "Dampak", _desc_dampak(r.provinsi, jenis, g_row), indent=1.25)
            _label_isi(doc, "Upaya Pemerintah", _upaya_pemerintah(jenis), indent=1.25)
            _label_isi(doc, "Penindakan", _penindakan(jenis), indent=1.25)

    # 2. ANALISIS
    doc.add_paragraph()
    _ambang(doc, "ANALISIS", bold=True, size=12, color=NAVY, after=4)
    for para in _analisis(jenis, ctx):
        _ambang(doc, para, indent=0.75, after=4)

    # 3. DAMPAK
    _ambang(doc, "DAMPAK", bold=True, size=12, color=NAVY, after=4)
    for d in _dampak_potensial(jenis):
        _bullet(doc, d)

    # 4. UPAYA
    _ambang(doc, "UPAYA", bold=True, size=12, color=NAVY, after=4)
    _ambang(doc, "Mencermati hal tersebut di atas, Deputi II memerintahkan Kabinda Wilayah Sumakal "
                 "untuk melakukan langkah-langkah sebagai berikut:", indent=0.75, after=4)
    for u in _upaya(jenis):
        _bullet(doc, u)

    # 5. SARAN TINDAK
    _ambang(doc, "SARAN TINDAK", bold=True, size=12, color=NAVY, after=4)
    for s in _saran_tindak(jenis):
        _bullet(doc, s)

    # Autentikasi
    _autentikasi(doc, ctx)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_xlsx(sheets):
    """sheets: dict nama_sheet -> DataFrame."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in sheets.items():
            if df is None:
                continue
            df.to_excel(w, index=False, sheet_name=name[:31])
            ws = w.sheets[name[:31]]
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col[:200]) + 2
                ws.column_dimensions[col[0].column_letter].width = min(max(width, 10), 40)
            ws.freeze_panes = "A2"
    return buf.getvalue()
