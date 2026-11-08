import pytest
from datetime import date
from pddikti_sdk.models import (
    AkreditasiInfo,
    BidangStudi,
    Dosen,
    EntityType,
    JabatanFungsional,
    JenjangStudi,
    Mahasiswa,
    PerguruanTinggi,
    PeringkatAkreditasi,
    ProgramStudi,
    SearchResult,
    SintaAuthor,
    SintaScore,
    StatusDosen,
    StatusMahasiswa,
)


def test_akreditasi_info():
    akr = AkreditasiInfo(
        peringkat=PeringkatAkreditasi.UNGGUL,
        no_sk="123/SK/BAN-PT/2023",
        tgl_kadaluarsa=date(2028, 12, 31),
    )
    assert akr.is_unggul_or_a is True
    assert akr.is_expired is False


def test_akreditasi_expired():
    akr = AkreditasiInfo(
        peringkat=PeringkatAkreditasi.B,
        tgl_kadaluarsa=date(2020, 1, 1),
    )
    assert akr.is_expired is True
    assert akr.is_unggul_or_a is False


def test_program_studi_and_pt():
    prodi = ProgramStudi(
        kode="55201",
        nama_prodi="Teknik Informatika",
        jenjang=JenjangStudi.S1,
        bidang=BidangStudi.EKSAKTA,
        dosen_count=10,
        mahasiswa_count=200,
    )
    assert prodi.rasio_dosen_mahasiswa == 20.0

    pt = PerguruanTinggi(
        kode="001001",
        nama_pt="Universitas Nusantara",
        daftar_prodi=[prodi],
        total_mahasiswa_aktif=200,
        total_dosen_tetap=10,
    )
    assert pt.rasio_agregat_kampus == 20.0
    assert pt.ringkasan_akreditasi_prodi[PeringkatAkreditasi.UNKNOWN.value] == 1


def test_dosen_dan_mahasiswa():
    dosen = Dosen(
        nidn="0012058501",
        nama_dosen="Budi Santoso, M.Kom.",
        jabatan_fungsional=JabatanFungsional.LEKTOR,
        status=StatusDosen.AKTIF,
    )
    assert dosen.nidn == "0012058501"
    assert dosen.jabatan_fungsional == JabatanFungsional.LEKTOR

    mhs = Mahasiswa(
        nim="12345678",
        nama_mahasiswa="Ahmad Dani",
        status=StatusMahasiswa.AKTIF,
        angkatan=2023,
    )
    assert mhs.nim == "12345678"
    assert mhs.status == StatusMahasiswa.AKTIF


def test_sinta_author():
    author = SintaAuthor(
        id="600123",
        fullname="Dr. Siti Aminah",
        affiliation_name="Universitas Gadjah Mada",
        scores=SintaScore(overall=500.0, three_years=200.0),
    )
    assert author.sinta_id == "600123"
    assert author.scores.overall == 500.0
