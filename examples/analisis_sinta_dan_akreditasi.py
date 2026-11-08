"""Contoh Integrasi Metrik Publikasi SINTA & Verifikasi Akreditasi BAN-PT."""

from datetime import date
from pddikti_sdk import (
    AkreditasiInfo,
    BanptService,
    DataAggregator,
    LembagaAkreditasi,
    PeringkatAkreditasi,
    SintaAuthor,
    SintaScore,
    ScopusMetrics,
    GoogleScholarMetrics,
    IprMetrics,
)


def main():
    print("=== INTEGRASI SINTA KEMDIKBUDRISTEK & AKREDITASI BAN-PT ===\n")

    # 1. Parsing Akreditasi BAN-PT
    akreditasi_data = {
        "akreditasi": "Unggul",
        "lembaga": "LAM-INFOKOM",
        "no_sk": "112/SK/LAM-INFOKOM/Akred/S/X/2024",
        "tgl_kadaluarsa": "2029-10-15",
    }
    akr = BanptService.parse_akreditasi_info(akreditasi_data)
    print(f"Status Akreditasi : {akr.peringkat.value} ({akr.lembaga.value})")
    print(f"Nomor SK          : {akr.nomor_sk}")
    print(f"Masa Berlaku      : s.d. {akr.tanggal_kedaluwarsa}")
    print(f"Apakah Kedaluwarsa: {'Ya' if akr.is_expired else 'Tidak (Aktif)'}\n")

    # 2. Simulasi Data Peneliti SINTA
    peneliti_1 = SintaAuthor(
        id="6001234",
        fullname="Dr. Ir. Ahmad Santoso, M.T.",
        nidn="0012058001",
        affiliation_name="Institut Teknologi Nusantara",
        department_name="Informatika",
        scores=SintaScore(overall=1250.5, three_years=480.0),
        scopus=ScopusMetrics(h_index=8, citations=230, documents=18),
        scholar=GoogleScholarMetrics(h_index=14, citations=620, documents=35),
        ipr=IprMetrics(patent=2, copyright=5),
    )

    peneliti_2 = SintaAuthor(
        id="6005678",
        fullname="Prof. Dr. Siti Rahmawati, M.Sc.",
        nidn="0021087502",
        affiliation_name="Institut Teknologi Nusantara",
        department_name="Informatika",
        scores=SintaScore(overall=2410.0, three_years=890.0),
        scopus=ScopusMetrics(h_index=15, citations=780, documents=32),
        scholar=GoogleScholarMetrics(h_index=22, citations=1850, documents=60),
        ipr=IprMetrics(patent=4, copyright=8),
    )

    authors = [peneliti_1, peneliti_2]

    # Agregasi riset departemen
    ringkasan = DataAggregator.ringkas_produktivitas_sinta(authors)
    print("--- Ringkasan Produktivitas Riset Departemen ---")
    print(f"Total Peneliti        : {ringkasan['total_author']}")
    print(f"Total Dokumen Scopus  : {ringkasan['total_scopus_documents']}")
    print(f"Total Sitasi Scopus   : {ringkasan['total_scopus_citations']}")
    print(f"Total Sitasi Scholar  : {ringkasan['total_scholar_citations']}")
    print(f"Total Paten Terdaftar : {ringkasan['total_paten_terdaftar']}")
    print(f"Rata-rata Skor 3-Th   : {ringkasan['rata_rata_skor_3tahun']}")
    print(f"H-Index Scopus Puncak : {ringkasan['h_index_scopus_tertinggi']}")


if __name__ == "__main__":
    main()
