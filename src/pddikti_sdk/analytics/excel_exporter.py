"""Modul ekspor laporan kepatuhan rasio BAN-PT ke format spreadsheet Microsoft Excel (.xlsx).

Menyediakan pemformatan visual otomatis dengan palet warna status akreditasi:
- Hijau: Ideal (Sesuai Standar Mutu)
- Biru: Memenuhi Batas Toleransi
- Kuning: Defisit Dosen (Perlu Penambahan Dosen)
- Merah: Anomali Ekstrim (> 1:100 atau Mahasiswa Aktif Tanpa Dosen)
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from pddikti_sdk.analytics.ratio import LaporanRasioPT, StatusKepatuhanRasio

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class ExcelReportGenerator:
    """Generator dokumen Excel untuk laporan kepatuhan rasio mutu BAN-PT."""

    # Palet warna status mutu (Soft fill dengan teks terbaca)
    STYLE_MAP = {
        StatusKepatuhanRasio.IDEAL: {
            "fill": "E2EFDA",  # Soft Green
            "font_color": "276A3C",
            "bold": False,
        },
        StatusKepatuhanRasio.MEMENUHI: {
            "fill": "DDEBF7",  # Soft Blue
            "font_color": "1F4E78",
            "bold": False,
        },
        StatusKepatuhanRasio.DEFISIT_DOSEN: {
            "fill": "FFF2CC",  # Soft Yellow
            "font_color": "7F6000",
            "bold": True,
        },
        StatusKepatuhanRasio.ANOMALI_EKSTRIM: {
            "fill": "FCE4D6",  # Soft Red/Orange
            "font_color": "C00000",
            "bold": True,
        },
        StatusKepatuhanRasio.UNDER_ENROLLED: {
            "fill": "EDEDED",  # Soft Gray
            "font_color": "595959",
            "bold": False,
        },
        StatusKepatuhanRasio.TIDAK_ADA_DATA: {
            "fill": "F2F2F2",
            "font_color": "7F7F7F",
            "bold": False,
        },
    }

    @classmethod
    def export(
        cls,
        laporan: LaporanRasioPT,
        output_path: Union[str, Path] = "laporan_rasio_pddikti.xlsx",
    ) -> Path:
        """Mengekspor LaporanRasioPT ke file Excel berformat rapi.

        Args:
            laporan: Objek LaporanRasioPT yang dihasilkan oleh RatioAnalyzer.
            output_path: Lokasi file output .xlsx yang ingin dibuat.

        Returns:
            Path absolut file Excel yang berhasil disimpan.

        Raises:
            ImportError: Jika modul openpyxl belum terpasang di sistem.
        """
        if not HAS_OPENPYXL:
            raise ImportError(
                "Modul 'openpyxl' diperlukan untuk ekspor Excel. "
                "Silakan jalankan: pip install openpyxl"
            )

        wb = openpyxl.Workbook()
        path = Path(output_path).resolve()

        # Styles umum
        thin_side = Side(style="thin", color="D9D9D9")
        data_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        header_border = Border(
            left=Side(style="thin", color="1B365D"),
            right=Side(style="thin", color="1B365D"),
            top=Side(style="medium", color="1B365D"),
            bottom=Side(style="medium", color="1B365D"),
        )

        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="1F4E78")
        subtitle_font = Font(name="Calibri", size=11, italic=True, color="595959")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=11)

        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")

        # ---------------------------------------------------------------------
        # Sheet 1: Ringkasan Eksekutif
        # ---------------------------------------------------------------------
        ws_summary = wb.active
        ws_summary.title = "Ringkasan Eksekutif"
        ws_summary.views.sheetView[0].showGridLines = True

        # Header Title
        ws_summary["B2"] = "LAPORAN EVALUASI RASIO DOSEN-MAHASISWA"
        ws_summary["B2"].font = title_font
        ws_summary["B3"] = f"Berdasarkan Standar Kepatuhan BAN-PT & Rekapitulasi Data PDDikti (Dibuat: {datetime.now().strftime('%d-%m-%Y %H:%M')})"
        ws_summary["B3"].font = subtitle_font

        # Profil Perguruan Tinggi
        profile_rows = [
            ("Nama Perguruan Tinggi", laporan.nama_pt),
            ("Kode / NPSN Kampus", laporan.kode_pt),
            ("Total Dosen Tetap", laporan.total_dosen),
            ("Total Mahasiswa Aktif", laporan.total_mahasiswa),
            ("Rasio Agregat Kampus", f"1 : {laporan.rasio_agregat}"),
        ]

        ws_summary["B5"] = "PROFIL INSTITUSI"
        ws_summary["B5"].font = bold_font

        for idx, (label, val) in enumerate(profile_rows, start=6):
            ws_summary[f"B{idx}"] = label
            ws_summary[f"B{idx}"].font = bold_font
            ws_summary[f"B{idx}"].border = data_border
            ws_summary[f"B{idx}"].fill = PatternFill(start_color="F2F2F2", fill_type="solid")

            ws_summary[f"C{idx}"] = val
            ws_summary[f"C{idx}"].font = regular_font
            ws_summary[f"C{idx}"].border = data_border
            if isinstance(val, int):
                ws_summary[f"C{idx}"].number_format = "#,##0"
                ws_summary[f"C{idx}"].alignment = align_right

        # Sebaran Kepatuhan Mutu Prodi
        ws_summary["E5"] = "SEBARAN STATUS PROGRAM STUDI"
        ws_summary["E5"].font = bold_font

        ws_summary["E6"] = "Kategori Kepatuhan Mutu"
        ws_summary["E6"].font = header_font
        ws_summary["E6"].fill = header_fill
        ws_summary["E6"].alignment = align_left
        ws_summary["E6"].border = header_border

        ws_summary["F6"] = "Jumlah Prodi"
        ws_summary["F6"].font = header_font
        ws_summary["F6"].fill = header_fill
        ws_summary["F6"].alignment = align_center
        ws_summary["F6"].border = header_border

        r_idx = 7
        for status_enum, style in cls.STYLE_MAP.items():
            count = laporan.sebaran_status_prodi.get(status_enum.value, 0)
            ws_summary[f"E{r_idx}"] = status_enum.value
            ws_summary[f"E{r_idx}"].font = Font(name="Calibri", size=10, bold=style["bold"], color=style["font_color"])
            ws_summary[f"E{r_idx}"].fill = PatternFill(start_color=style["fill"], fill_type="solid")
            ws_summary[f"E{r_idx}"].border = data_border

            ws_summary[f"F{r_idx}"] = count
            ws_summary[f"F{r_idx}"].font = Font(name="Calibri", size=10, bold=True)
            ws_summary[f"F{r_idx}"].alignment = align_center
            ws_summary[f"F{r_idx}"].fill = PatternFill(start_color=style["fill"], fill_type="solid")
            ws_summary[f"F{r_idx}"].border = data_border
            r_idx += 1

        # Rekomendasi Penting
        ws_summary[f"B{r_idx+2}"] = "CATATAN & TEMUAN PENTING:"
        ws_summary[f"B{r_idx+2}"].font = bold_font

        note_1 = f"- Terdeteksi {len(laporan.prodi_anomali)} program studi dengan ANOMALI EKSTRIM (rasio > 1:100 atau tanpa dosen tetap)."
        note_2 = f"- Terdapat {len(laporan.prodi_defisit)} program studi mengalami DEFISIT DOSEN (melebihi batas toleransi akreditasi)."
        ws_summary[f"B{r_idx+3}"] = note_1
        ws_summary[f"B{r_idx+3}"].font = Font(name="Calibri", size=10, color="C00000" if laporan.prodi_anomali else "000000")
        ws_summary[f"B{r_idx+4}"] = note_2
        ws_summary[f"B{r_idx+4}"].font = Font(name="Calibri", size=10, color="7F6000" if laporan.prodi_defisit else "000000")

        # ---------------------------------------------------------------------
        # Sheet 2: Rincian Program Studi
        # ---------------------------------------------------------------------
        ws_detail = wb.create_sheet(title="Detail Program Studi")
        ws_detail.views.sheetView[0].showGridLines = True

        headers = [
            ("No", 6, align_center),
            ("Kode Prodi", 14, align_center),
            ("Nama Program Studi", 34, align_left),
            ("Jenjang", 12, align_center),
            ("Rumpun Bidang", 28, align_left),
            ("Dosen", 10, align_right),
            ("Mahasiswa", 14, align_right),
            ("Rasio Aktual", 14, align_center),
            ("Status Kepatuhan BAN-PT", 30, align_left),
            ("Rekomendasi Formasi / Mutu", 50, align_left),
        ]

        # Tulis Header
        for col_idx, (col_name, col_width, col_align) in enumerate(headers, start=1):
            cell = ws_detail.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = align_center
            cell.border = header_border
            ws_detail.column_dimensions[get_column_letter(col_idx)].width = col_width

        ws_detail.freeze_panes = "A2"

        # Kumpulkan seluruh program studi untuk dicatat dalam lembar kerja
        all_prodi = laporan.daftar_prodi if laporan.daftar_prodi else (laporan.prodi_anomali + laporan.prodi_defisit)

        row_num = 2
        for idx, p in enumerate(all_prodi, start=1):
            st_style = cls.STYLE_MAP.get(p.status, cls.STYLE_MAP[StatusKepatuhanRasio.TIDAK_ADA_DATA])
            row_fill = PatternFill(start_color=st_style["fill"], fill_type="solid")
            status_font = Font(name="Calibri", size=10, bold=st_style["bold"], color=st_style["font_color"])

            row_values = [
                (idx, align_center, None),
                (p.kode_prodi, align_center, None),
                (p.nama_prodi, align_left, None),
                (p.jenjang, align_center, None),
                (p.bidang.value if hasattr(p.bidang, "value") else str(p.bidang), align_left, None),
                (p.jumlah_dosen, align_right, "#,##0"),
                (p.jumlah_mahasiswa, align_right, "#,##0"),
                (f"1 : {p.rasio_aktual}", align_center, None),
                (p.status.value, align_left, None),
                (p.rekomendasi, align_left, None),
            ]

            for c_idx, (val, alignment, num_fmt) in enumerate(row_values, start=1):
                c = ws_detail.cell(row=row_num, column=c_idx, value=val)
                c.alignment = alignment
                c.border = data_border
                c.fill = row_fill
                if c_idx == 9:  # Kolom Status
                    c.font = status_font
                elif c_idx in (6, 7, 8):
                    c.font = bold_font
                else:
                    c.font = regular_font

                if num_fmt:
                    c.number_format = num_fmt

            row_num += 1

        # Atur lebar kolom sheet 1
        ws_summary.column_dimensions["A"].width = 4
        ws_summary.column_dimensions["B"].width = 28
        ws_summary.column_dimensions["C"].width = 36
        ws_summary.column_dimensions["D"].width = 6
        ws_summary.column_dimensions["E"].width = 34
        ws_summary.column_dimensions["F"].width = 16

        wb.save(path)
        return path


def export_laporan_rasio_excel(
    laporan: LaporanRasioPT,
    output_path: Union[str, Path] = "laporan_rasio_pddikti.xlsx",
) -> Path:
    """Fungsi helper untuk mengekspor LaporanRasioPT ke file Excel."""
    return ExcelReportGenerator.export(laporan, output_path)
