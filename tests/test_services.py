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


def test_pddikti_service_url_encoding_and_path_traversal_prevention():
    import httpx
    from pddikti_sdk.services.pddikti import PDDiktiService
    from pddikti_sdk.exceptions import ValidationError

    captured_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(200, json={"pt": [], "prodi": [], "dosen": [], "mahasiswa": []})

    client = httpx.Client(base_url="https://api-frontend.kemdikbud.go.id", transport=httpx.MockTransport(handler))
    svc = PDDiktiService(client, cache=None)

    # 1. Keyword dengan spasi, tanda tanya, pagar, atau slash harus di-URL-encode dengan aman
    svc.search_all("S1 Teknik / Mesin?foo=1#bar", use_cache=False)
    assert len(captured_urls) == 1
    assert "%2F" in captured_urls[0]
    assert "%3F" in captured_urls[0]
    assert "%23" in captured_urls[0]
    assert "?foo=1" not in captured_urls[0]

    # 2. id_pt dengan upaya path traversal atau karakter berbahaya harus ditolak dengan ValidationError
    with pytest.raises(ValidationError):
        svc.get_detail_pt("../../admin", use_cache=False)

    with pytest.raises(ValidationError):
        svc.get_prodi_list("../secret?x=1", use_cache=False)


def test_pddikti_service_rate_limit_and_invalid_json():
    import httpx
    from pddikti_sdk.services.pddikti import PDDiktiService
    from pddikti_sdk.exceptions import RateLimitError, APIConnectionError

    def rate_limit_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too Many Requests")

    client_429 = httpx.Client(base_url="https://api-frontend.kemdikbud.go.id", transport=httpx.MockTransport(rate_limit_handler))
    svc_429 = PDDiktiService(client_429, cache=None)
    with pytest.raises(RateLimitError) as exc_info:
        svc_429.search_all("UGM", use_cache=False)
    assert exc_info.value.status_code == 429

    def html_error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>502 Bad Gateway</html>")

    client_html = httpx.Client(base_url="https://api-frontend.kemdikbud.go.id", transport=httpx.MockTransport(html_error_handler))
    svc_html = PDDiktiService(client_html, cache=None)
    with pytest.raises(APIConnectionError):
        svc_html.search_all("UGM", use_cache=False)


def test_banpt_service_robust_parsing():
    # LAMSAMA mengandung substring 'SAMA' dan tidak boleh salah deteksi jika ada kata lain,
    # serta is_expired harus menghormati tanggal kedaluwarsa yang sudah lewat
    info = BanptService.parse_akreditasi_info({
        "akreditasi": "Baik",
        "lembaga": "LAMSAMA",
        "tgl_kadaluarsa": "2020-01-01",
        "tahun_sk": "tidak_valid",
    })
    assert info.peringkat == PeringkatAkreditasi.BAIK
    assert info.lembaga == LembagaAkreditasi.LAM_SAMA
    assert info.is_expired is True
    assert info.status_aktif is False
    assert info.tahun_sk is None

    # Peringkat Tidak Terakreditasi
    assert BanptService.parse_peringkat("Tidak Terakreditasi") == PeringkatAkreditasi.TIDAK_TERAKREDITASI
    assert BanptService.parse_peringkat("Belum Terakreditasi") == PeringkatAkreditasi.TIDAK_TERAKREDITASI


def test_sinta_service_null_nested_fields_and_wos():
    with SintaService() as service:
        raw = {
            "id": "999",
            "fullname": "Dr. Test",
            "affiliation_name": "UI",
            "scores": None,
            "scopus": None,
            "scholar": None,
            "garuda": None,
            "wos": {"documents": 7, "citations": 42},
            "ipr": None,
            "subjects": None,
        }
        author = service.parse_author_data(raw)
        assert author.sinta_id == "999"
        assert author.wos.documents == 7
        assert author.wos.citations == 42
        assert author.scores.overall == 0.0
        assert author.bidang_keahlian == []

