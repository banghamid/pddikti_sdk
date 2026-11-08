import pytest
from pddikti_sdk.models import (
    LembagaAkreditasi,
    PeringkatAkreditasi,
)
from pddikti_sdk.services import BanptService, SintaService


def test_banpt_service_parse_peringkat():
    assert BanptService.parse_peringkat("Unggul") == PeringkatAkreditasi.UNGGUL
    assert BanptService.parse_peringkat("Baik Sekali") == PeringkatAkreditasi.BAIK_SEKALI
    assert BanptService.parse_peringkat("A") == PeringkatAkreditasi.A
    assert BanptService.parse_peringkat("B") == PeringkatAkreditasi.B
    assert BanptService.parse_peringkat("Kadaluarsa") == PeringkatAkreditasi.KEDALUWARSA
    assert BanptService.parse_peringkat("Tidak Ada") == PeringkatAkreditasi.UNKNOWN


def test_banpt_service_parse_akreditasi_info():
    data = {
        "akreditasi": "Unggul",
        "lembaga": "LAM-INFOKOM",
        "no_sk": "999/SK/2024",
        "tgl_kadaluarsa": "2029-05-20",
    }
    info = BanptService.parse_akreditasi_info(data)
    assert info.peringkat == PeringkatAkreditasi.UNGGUL
    assert info.lembaga == LembagaAkreditasi.LAM_INFOKOM
    assert info.nomor_sk == "999/SK/2024"
    assert info.is_expired is False


def test_sinta_service_parse_author():
    service = SintaService()
    raw = {
        "id": "123456",
        "fullname": "Prof. Budi",
        "affiliation_name": "Institut Teknologi Bandung",
        "scores": {"overall": 1500, "three_years": 600},
        "scopus": {"h_index": 12, "citations": 450, "documents": 25},
    }
    author = service.parse_author_data(raw)
    assert author.sinta_id == "123456"
    assert author.nama == "Prof. Budi"
    assert author.scores.overall == 1500.0
    assert author.scopus.h_index == 12
