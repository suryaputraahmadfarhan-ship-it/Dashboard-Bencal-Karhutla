# -*- coding: utf-8 -*-
"""Pembuat laporan: Word (.docx) siap kirim ke pimpinan, dan Excel multi-sheet."""
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


def build_docx(ctx):
    """ctx: dict berisi periode, wilayah, jenis, data_per, kpi (list), narasi, perhatian (list),
    per_tipe (DataFrame), per_prov (DataFrame), top_hotspot (DataFrame), pembuat, demo (bool)."""
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(11)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("BADAN INTELIJEN NEGARA REPUBLIK INDONESIA")
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = NAVY
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Deputi 2 · Direktorat 2.3")
    r.font.size = Pt(11)

    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run("LAPORAN SINGKAT KONDISI KEBENCANAAN")
    r.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = NAVY
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Wilayah Sumatera dan Kalimantan").italic = True

    meta = [("Periode", ctx["periode"]), ("Wilayah", ctx["wilayah"]), ("Jenis bencana", ctx["jenis"]),
            ("Data per", ctx["data_per"]), ("Disusun oleh", ctx["pembuat"])]
    t = doc.add_table(rows=0, cols=2)
    for k, v in meta:
        c = t.add_row().cells
        c[0].text = k
        c[1].text = f": {v}"
        c[0].width, c[1].width = Cm(3.6), Cm(12.4)
    if ctx.get("demo"):
        p = doc.add_paragraph()
        r = p.add_run("Catatan: laporan ini dibuat dari DATA DEMO (sintetis), bukan data riil.")
        r.bold = True
        r.font.color.rgb = RGBColor(0xB4, 0x53, 0x09)

    doc.add_heading("1. Indikator Utama", level=2)
    _table(doc, ["Indikator", "Nilai", "Perubahan vs periode sebelumnya"],
           ctx["kpi"], widths=[6, 4, 6], num_cols=(1,))

    doc.add_heading("2. Ringkasan Kondisi", level=2)
    doc.add_paragraph(ctx["narasi"])
    if ctx["perhatian"]:
        p = doc.add_paragraph()
        p.add_run("Hal yang perlu diperhatikan:").bold = True
        for item in ctx["perhatian"]:
            doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("3. Rekap per Jenis Bencana", level=2)
    rows = []
    for item in ctx.get("spesifik") or []:
        tipe = item["Jenis"]
        info_parts = []
        if tipe == "Karhutla":
            if "Luas (ha)" in item:
                info_parts.append(f"Luas {fmt_num(item['Luas (ha)'], 1)} ha")
            if "ISPA" in item:
                info_parts.append(f"ISPA {fmt_num(item['ISPA'])} kasus")
        elif tipe == "Banjir":
            if "Tinggi genangan rata-rata (cm)" in item:
                info_parts.append(f"Tinggi genangan rata-rata {fmt_num(item['Tinggi genangan rata-rata (cm)'], 0)} cm"
                                  + (f" (maks {fmt_num(item['Tinggi genangan maks (cm)'])} cm)"
                                     if "Tinggi genangan maks (cm)" in item else ""))
            if "Rumah terdampak" in item:
                info_parts.append(f"{fmt_num(item['Rumah terdampak'])} rumah terdampak")
            if "Luas (ha)" in item:
                info_parts.append(f"luas {fmt_num(item['Luas (ha)'], 1)} ha")
        elif tipe == "Gempa":
            if "Magnitudo rata-rata (SR)" in item:
                s = f"Magnitudo rata-rata {fmt_num(item['Magnitudo rata-rata (SR)'], 1)} SR"
                if "Magnitudo maks (SR)" in item:
                    s += f" (maks {fmt_num(item['Magnitudo maks (SR)'], 1)})"
                info_parts.append(s)
            if "Kedalaman rata-rata (km)" in item:
                info_parts.append(f"kedalaman rata-rata {fmt_num(item['Kedalaman rata-rata (km)'], 0)} km")
            if "Rumah terdampak" in item:
                info_parts.append(f"{fmt_num(item['Rumah terdampak'])} rumah terdampak")
        else:
            if "Rumah terdampak" in item:
                info_parts.append(f"{fmt_num(item['Rumah terdampak'])} rumah terdampak")
        rows.append([tipe, fmt_num(item["Kejadian"]), fmt_num(item.get("Korban jiwa", 0)),
                     fmt_num(item.get("Pengungsi", 0)), "; ".join(info_parts) if info_parts else "-"])
    if rows:
        _table(doc, ["Jenis bencana", "Kejadian", "Korban jiwa", "Pengungsi", "Info spesifik"],
               rows, widths=[3.5, 2, 2.5, 2.5, 6], num_cols=(1, 2, 3))
    else:
        doc.add_paragraph("Tidak ada kejadian pada periode ini.")

    doc.add_heading("4. Lima Provinsi dengan Kejadian Terbanyak", level=2)
    pp = ctx["per_prov"].head(5)
    _table(doc, ["No", "Provinsi", "Kejadian", "Luas (ha)", "Korban jiwa", "ISPA"],
           [[i + 1, r.provinsi, fmt_num(r.kejadian), fmt_num(r.luas_ha, 1), fmt_num(r.korban_jiwa), fmt_num(r.ispa)]
            for i, r in enumerate(pp.itertuples())], widths=[1.2, 5, 2.5, 3, 2.5, 2], num_cols=(2, 3, 4, 5))

    th = ctx["top_hotspot"]
    if th is not None and len(th):
        doc.add_heading(f"5. Hotspot Tertinggi ({ctx['hotspot_tgl']})", level=2)
        _table(doc, ["No", "Provinsi", "Jumlah hotspot"],
               [[i + 1, r.provinsi, fmt_num(r.hotspot)] for i, r in enumerate(th.itertuples())],
               widths=[1.5, 8, 4], num_cols=(2,))

    doc.add_paragraph()
    p = doc.add_paragraph()
    r = p.add_run("Dokumen ini dihasilkan otomatis dari Dashboard Kebencanaan Direktorat 2.3 dan perlu "
                  "diverifikasi petugas sebelum disampaikan.")
    r.italic = True
    r.font.size = Pt(9)

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
