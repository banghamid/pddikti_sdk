import pytest
from pddikti_sdk.analytics import (
    DataAggregator,
    RatioAnalyzer,
    StatusKepatuhanRasio,
)
from pddikti_sdk.models import (
    BidangStudi,
    JenjangStudi,
    PerguruanTinggi,
    ProgramStudi,
    ScopusMetrics,
    SintaAuthor,
    SintaScore,
)


def test_ratio_analyzer_prodi_ideal():
    prodi = ProgramStudi(
        kode="55201",
        nama_prodi="Teknik Sipil",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=10,
        mahasiswa_count=180,  # 1:18 -> ideal eksakta (<= 1:20)
    )
    laporan = RatioAnalyzer.evaluasi_prodi(prodi)
    assert laporan.status == StatusKepatuhanRasio.IDEAL
    assert laporan.rasio_aktual == 18.0


def test_ratio_analyzer_prodi_defisit():
    prodi = ProgramStudi(
        kode="55202",
        nama_prodi="Arsitektur",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=10,
        mahasiswa_count=380,  # 1:38 -> melebihi toleransi eksakta (35.0)
    )
    laporan = RatioAnalyzer.evaluasi_prodi(prodi)
    assert laporan.status == StatusKepatuhanRasio.DEFISIT_DOSEN
    assert laporan.rasio_aktual == 38.0


def test_ratio_analyzer_anomali():
    prodi = ProgramStudi(
        kode="61201",
        nama_prodi="Akuntansi",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.NON_EKSAKTA,
        dosen_count=0,
        mahasiswa_count=150,  # 0 dosen tapi 150 mahasiswa
    )
    laporan = RatioAnalyzer.evaluasi_prodi(prodi)
    assert laporan.status == StatusKepatuhanRasio.ANOMALI_EKSTRIM


def test_ratio_analyzer_pt():
    p1 = ProgramStudi(
        kode="01",
        nama_prodi="Prodi A",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=10,
        mahasiswa_count=200,
    )
    p2 = ProgramStudi(
        kode="02",
        nama_prodi="Prodi B",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.NON_EKSAKTA,
        dosen_count=2,
        mahasiswa_count=300,  # Rasio 150 -> anomali
    )
    pt = PerguruanTinggi(
        kode="001",
        nama_pt="Universitas Tes",
        daftar_prodi=[p1, p2],
    )
    laporan_pt = RatioAnalyzer.evaluasi_pt(pt)
    assert laporan_pt.total_dosen == 12
    assert laporan_pt.total_mahasiswa == 500
    assert len(laporan_pt.prodi_anomali) == 1
    assert laporan_pt.prodi_anomali[0].kode_prodi == "02"


def test_data_aggregator_sinta():
    authors = [
        SintaAuthor(
            id="1",
            fullname="Author 1",
            affiliation_name="PT A",
            scores=SintaScore(three_years=100.0),
            scopus=ScopusMetrics(documents=5, citations=20, h_index=3),
        ),
        SintaAuthor(
            id="2",
            fullname="Author 2",
            affiliation_name="PT A",
            scores=SintaScore(three_years=300.0),
            scopus=ScopusMetrics(documents=15, citations=80, h_index=7),
        ),
    ]
    rekap = DataAggregator.ringkas_produktivitas_sinta(authors)
    assert rekap["total_author"] == 2
    assert rekap["total_scopus_documents"] == 20
    assert rekap["total_scopus_citations"] == 100
    assert rekap["rata_rata_skor_3tahun"] == 200.0
    assert rekap["h_index_scopus_tertinggi"] == 7


def test_ratio_analyzer_exact_ideal_deficit_needed():
    # Eksakta ideal = 20.0, toleransi = 35.0
    # Jika mhs = 400 (pas kelipatan 20) dan dosen = 10 (rasio 1:40 > 35),
    # untuk mencapai rasio ideal 1:20 dibutuhkan tepat (400 / 20) - 10 = 10 dosen, bukan 11.
    prodi = ProgramStudi(
        kode="55201",
        nama_prodi="Teknik Elektro",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=10,
        mahasiswa_count=400,
    )
    laporan = RatioAnalyzer.evaluasi_prodi(prodi)
    assert laporan.status == StatusKepatuhanRasio.DEFISIT_DOSEN
    assert "minimal 10 dosen" in laporan.rekomendasi


def test_ratio_analyzer_negative_values_no_zero_division():
    prodi_zero_neg = ProgramStudi(
        kode="99",
        nama_prodi="Prodi Korup",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=0,
        mahasiswa_count=-5,
    )
    laporan = RatioAnalyzer.evaluasi_prodi(prodi_zero_neg)
    assert laporan.status == StatusKepatuhanRasio.TIDAK_ADA_DATA
    assert laporan.rasio_aktual == 0.0

    prodi_neg_dosen = ProgramStudi(
        kode="98",
        nama_prodi="Prodi Negatif",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.NON_EKSAKTA,
        dosen_count=-2,
        mahasiswa_count=10,
    )
    laporan2 = RatioAnalyzer.evaluasi_prodi(prodi_neg_dosen)
    assert laporan2.status == StatusKepatuhanRasio.TIDAK_ADA_DATA
    assert laporan2.rasio_aktual == 0.0


def test_data_aggregator_empty_sinta_and_wilayah_whitespace():
    rekap_kosong = DataAggregator.ringkas_produktivitas_sinta([])
    expected_keys = {
        "total_author",
        "total_scopus_documents",
        "total_scopus_citations",
        "total_scholar_citations",
        "total_paten_terdaftar",
        "rata_rata_skor_3tahun",
        "h_index_scopus_tertinggi",
    }
    assert expected_keys.issubset(rekap_kosong.keys())
    assert rekap_kosong["total_author"] == 0
    assert rekap_kosong["total_scopus_documents"] == 0
    assert rekap_kosong["rata_rata_skor_3tahun"] == 0.0

    pt1 = PerguruanTinggi(kode="1", nama_pt="PT 1", provinsi=" Jawa Barat ", total_mahasiswa_aktif=100, total_dosen_tetap=10)
    pt2 = PerguruanTinggi(kode="2", nama_pt="PT 2", provinsi="Jawa Barat", total_mahasiswa_aktif=100, total_dosen_tetap=10)
    pt3 = PerguruanTinggi(kode="3", nama_pt="PT 3", provinsi="   ", total_mahasiswa_aktif=50, total_dosen_tetap=5)

    wilayah_rekap = DataAggregator.ringkas_sebaran_wilayah([pt1, pt2, pt3])
    assert "Jawa Barat" in wilayah_rekap
    assert wilayah_rekap["Jawa Barat"]["jumlah_pt"] == 2
    assert "Lainnya" in wilayah_rekap
    assert wilayah_rekap["Lainnya"]["jumlah_pt"] == 1


