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
