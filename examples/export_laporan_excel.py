"""Contoh Pembuatan Laporan Kepatuhan Rasio BAN-PT dalam Format Excel (.xlsx).

Menghasilkan dokumen spreadsheet Microsoft Excel lengkap dengan:
1. Lembar Ringkasan Eksekutif (Profil Institusi & Sebaran Mutu).
2. Lembar Detail Program Studi dengan pewarnaan otomatis:
   - Hijau  : Ideal
   - Biru   : Memenuhi Toleransi
   - Kuning : Defisit Dosen
   - Merah  : Anomali Ekstrim
"""

from pathlib import Path
from pddikti_sdk import (
    BidangStudi,
    JenjangStudi,
    PerguruanTinggi,
    ProgramStudi,
    RatioAnalyzer,
    export_laporan_rasio_excel,
)


def main():
    print("=== MEMBUAT LAPORAN EXCEL KEPATUHAN RASIO BAN-PT ===\n")

    # Siapkan data perguruan tinggi sampel
    daftar_prodi = [
        ProgramStudi(
            kode="55201",
            nama_prodi="Teknik Informatika",
            jenjang=JenjangStudi.S1,
            bidang=BidangStudi.EKSAKTA,
            dosen_count=12,
            mahasiswa_count=216,  # 1:18 (Ideal)
        ),
        ProgramStudi(
            kode="21201",
            nama_prodi="Teknik Mesin",
            jenjang=JenjangStudi.S1,
            bidang=BidangStudi.EKSAKTA,
            dosen_count=10,
            mahasiswa_count=320,  # 1:32 (Memenuhi batas toleransi eksakta 35)
        ),
        ProgramStudi(
            kode="61201",
            nama_prodi="Manajemen",
            jenjang=JenjangStudi.S1,
            bidang=BidangStudi.NON_EKSAKTA,
            dosen_count=14,
            mahasiswa_count=420,  # 1:30 (Ideal non-eksakta)
        ),
        ProgramStudi(
            kode="62201",
            nama_prodi="Akuntansi",
            jenjang=JenjangStudi.S1,
            bidang=BidangStudi.NON_EKSAKTA,
            dosen_count=6,
            mahasiswa_count=330,  # 1:55 (Defisit dosen > 45)
        ),
        ProgramStudi(
            kode="74201",
            nama_prodi="Ilmu Hukum",
            jenjang=JenjangStudi.S1,
            bidang=BidangStudi.NON_EKSAKTA,
            dosen_count=3,
            mahasiswa_count=390,  # 1:130 (Anomali ekstrim > 1:100)
        ),
        ProgramStudi(
            kode="86201",
            nama_prodi="Pendidikan Guru Sekolah Dasar",
            jenjang=JenjangStudi.S1,
            bidang=BidangStudi.NON_EKSAKTA,
            dosen_count=0,
            mahasiswa_count=85,  # 0 dosen tetap (Anomali kritis)
        ),
    ]

    pt = PerguruanTinggi(
        kode="001099",
        nama_pt="Universitas Pembangunan Nusantara",
        daftar_prodi=daftar_prodi,
    )

    # 1. Evaluasi rasio
    laporan = RatioAnalyzer.evaluasi_pt(pt)
    print(f"Kampus           : {laporan.nama_pt}")
    print(f"Total Dosen      : {laporan.total_dosen} | Total Mahasiswa: {laporan.total_mahasiswa}")
    print(f"Rasio Agregat PT : 1 : {laporan.rasio_agregat}\n")

    # 2. Ekspor ke Excel
    output_file = Path("laporan_kepatuhan_banpt_contoh.xlsx")
    hasil_path = export_laporan_rasio_excel(laporan, output_file)

    print(f"[SUKSES] File Excel berhasil dibuat:")
    print(f"-> Lokasi: {hasil_path}")


if __name__ == "__main__":
    main()
