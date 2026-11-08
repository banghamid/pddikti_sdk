"""Contoh Analisis Rasio Dosen-Mahasiswa untuk Jurnalis Data & Peneliti Kampus.

Menghitung rasio dosen terhadap mahasiswa berdasarkan data PDDikti
dan mengevaluasi kepatuhan terhadap standar akreditasi BAN-PT.
"""

from pddikti_sdk import (
    BidangStudi,
    JenjangStudi,
    PerguruanTinggi,
    ProgramStudi,
    RatioAnalyzer,
    StatusKepatuhanRasio,
)


def main():
    print("=== SIMULASI ANALISIS RASIO DOSEN-MAHASISWA (BAN-PT) ===\n")

    # Simulasi data Perguruan Tinggi dengan beberapa prodi
    prodi_informatika = ProgramStudi(
        kode="55201",
        nama_prodi="Teknik Informatika",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=12,
        mahasiswa_count=360,  # Rasio 1:30 (batas toleransi eksakta)
    )

    prodi_manajemen = ProgramStudi(
        kode="61201",
        nama_prodi="Manajemen",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.NON_EKSAKTA,
        dosen_count=15,
        mahasiswa_count=450,  # Rasio 1:30 (ideal non-eksakta)
    )

    prodi_hukum = ProgramStudi(
        kode="74201",
        nama_prodi="Ilmu Hukum",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.NON_EKSAKTA,
        dosen_count=4,
        mahasiswa_count=480,  # Rasio 1:120 (Anomali ekstrim / defisit dosen parah)
    )

    kampus = PerguruanTinggi(
        kode="001001",
        nama_pt="Universitas Contoh Indonesia",
        daftar_prodi=[prodi_informatika, prodi_manajemen, prodi_hukum],
    )

    # Menjalankan mesin analisis rasio
    laporan = RatioAnalyzer.evaluasi_pt(kampus)

    print(f"Kampus: {laporan.nama_pt}")
    print(f"Total Dosen: {laporan.total_dosen} | Total Mahasiswa: {laporan.total_mahasiswa}")
    print(f"Rasio Agregat Kampus: 1 : {laporan.rasio_agregat}\n")

    print("--- Detail Evaluasi Program Studi ---")
    for prodi in kampus.daftar_prodi:
        eval_prodi = RatioAnalyzer.evaluasi_prodi(prodi)
        print(f"[{eval_prodi.kode_prodi}] {eval_prodi.nama_prodi} ({eval_prodi.jenjang})")
        print(f"  - Bidang      : {eval_prodi.bidang.value}")
        print(f"  - Dosen : Mhs : {eval_prodi.jumlah_dosen} dosen vs {eval_prodi.jumlah_mahasiswa} mhs")
        print(f"  - Rasio       : 1 : {eval_prodi.rasio_aktual}")
        print(f"  - Status      : {eval_prodi.status.value}")
        print(f"  - Rekomendasi : {eval_prodi.rekomendasi}\n")

    if laporan.prodi_anomali:
        print("[PERINGATAN] TEMUAN ANOMALI EKSTRIM:")
        for anomali in laporan.prodi_anomali:
            print(f"  - {anomali.nama_prodi}: Rasio 1:{anomali.rasio_aktual} ({anomali.rekomendasi})")


if __name__ == "__main__":
    main()
