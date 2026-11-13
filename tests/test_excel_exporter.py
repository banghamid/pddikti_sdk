import os
from pathlib import Path
import pytest
import openpyxl

from pddikti_sdk.analytics import (
    ExcelReportGenerator,
    LaporanRasioPT,
    LaporanRasioProdi,
    RatioAnalyzer,
    StatusKepatuhanRasio,
    export_laporan_rasio_excel,
)
from pddikti_sdk.models import (
    BidangStudi,
    JenjangStudi,
    PerguruanTinggi,
    ProgramStudi,
)


def test_excel_export_file_creation(tmp_path):
    p1 = ProgramStudi(
        kode="55201",
        nama_prodi="Teknik Informatika",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=10,
        mahasiswa_count=180,  # Ideal (1:18)
    )
    p2 = ProgramStudi(
        kode="61201",
        nama_prodi="Manajemen",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.NON_EKSAKTA,
        dosen_count=5,
        mahasiswa_count=280,  # Defisit (1:56 > 45)
    )
    p3 = ProgramStudi(
        kode="74201",
        nama_prodi="Ilmu Hukum",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.NON_EKSAKTA,
        dosen_count=2,
        mahasiswa_count=320,  # Anomali (> 1:100)
    )

    pt = PerguruanTinggi(
        kode="001001",
        nama_pt="Universitas Contoh Laporan",
        daftar_prodi=[p1, p2, p3],
    )

    laporan = RatioAnalyzer.evaluasi_pt(pt)
    assert len(laporan.daftar_prodi) == 3

    out_file = tmp_path / "laporan_uji.xlsx"
    saved_path = export_laporan_rasio_excel(laporan, out_file)

    assert saved_path.exists()
    assert saved_path.is_file()
    assert saved_path.stat().st_size > 0

    # Buka kembali workbook Excel untuk verifikasi struktur & styling
    wb = openpyxl.load_workbook(saved_path)
    assert "Ringkasan Eksekutif" in wb.sheetnames
    assert "Detail Program Studi" in wb.sheetnames

    # Verifikasi Sheet Ringkasan
    ws_sum = wb["Ringkasan Eksekutif"]
    assert "Universitas Contoh Laporan" in str(ws_sum["C6"].value)
    assert ws_sum["C7"].value == "001001"

    # Verifikasi Sheet Detail
    ws_det = wb["Detail Program Studi"]
    assert ws_det.max_row >= 4  # Header + 3 prodi

    # Cek nilai baris
    prodi_names = [ws_det.cell(row=r, column=3).value for r in range(2, ws_det.max_row + 1)]
    assert "Teknik Informatika" in prodi_names
    assert "Manajemen" in prodi_names
    assert "Ilmu Hukum" in prodi_names

    # Cek pewarnaan status di kolom 9
    fill_colors = [ws_det.cell(row=r, column=9).fill.start_color.rgb for r in range(2, ws_det.max_row + 1)]
    # Setidaknya ada warna fill yang diterapkan (bukan None atau transparan)
    assert any(c is not None for c in fill_colors)
    wb.close()


def test_excel_export_sanitizes_formula_injection(tmp_path):
    p_malicious = ProgramStudi(
        kode="=CMD|' /C calc'!A0",
        nama_prodi="+SUM(1,1)*cmd",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=5,
        mahasiswa_count=100,
    )
    pt = PerguruanTinggi(
        kode="-001001",
        nama_pt="@Universitas EvilFormula()",
        daftar_prodi=[p_malicious],
    )
    laporan = RatioAnalyzer.evaluasi_pt(pt)
    out_file = tmp_path / "subdir" / "aman_formula.xlsx"
    saved_path = export_laporan_rasio_excel(laporan, out_file)

    wb = openpyxl.load_workbook(saved_path)
    ws_sum = wb["Ringkasan Eksekutif"]
    ws_det = wb["Detail Program Studi"]

    # Nilai yang diawali karakter formula (=, +, -, @) harus di-prefiks dengan tanda kutip tunggal (')
    assert str(ws_sum["C6"].value).startswith("'")
    assert str(ws_sum["C7"].value).startswith("'")
    assert str(ws_det.cell(row=2, column=2).value).startswith("'")
    assert str(ws_det.cell(row=2, column=3).value).startswith("'")
    wb.close()

