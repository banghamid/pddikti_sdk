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


def test_pddikti_service_handles_inf_nan_and_rich_prodi_pt_fields():
    import httpx
    from pddikti_sdk.models import BidangStudi, JenjangStudi
    from pddikti_sdk.services.pddikti import PDDiktiService

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/v2/detail_pt/" in url:
            return httpx.Response(
                200,
                json={
                    "nama_pt": "Institut Teknologi Uji",
                    "kode_pt": "001002",
                    "wilayah": "LLDIKTI Wilayah IV",
                    "akreditasi": "Unggul",
                    "jml_mhs": "inf",
                    "jml_dosen": "nan",
                },
            )
        return httpx.Response(
            200,
            json=[
                {
                    "id_sms": "P1",
                    "kode_prodi": "55201",
                    "nm_lemb": "Teknik Informatika",
                    "jenjang": "S2",
                    "akreditasi": "Baik Sekali",
                    "jml_dosen": 10,
                    "jml_mhs": 150,
                },
                {
                    "id_sms": "P2",
                    "kode_prodi": "61201",
                    "nm_lemb": "Ilmu Hukum",
                    "nm_jenj_didik": "Sarjana Terapan",
                    "jml_dosen": "inf",
                    "jml_mhs": -20,
                },
            ],
        )

    client = httpx.Client(base_url="https://api-frontend.kemdikbud.go.id", transport=httpx.MockTransport(handler))
    svc = PDDiktiService(client, cache=None)

    pt = svc.get_detail_pt("PT123", use_cache=False)
    assert pt.total_mahasiswa_aktif == 0
    assert pt.total_dosen_tetap == 0
    assert pt.wilayah == "LLDIKTI Wilayah IV"
    assert pt.akreditasi is not None
    assert pt.akreditasi.peringkat == PeringkatAkreditasi.UNGGUL

    prodis = svc.get_prodi_list("PT123", use_cache=False)
    assert len(prodis) == 2
    assert prodis[0].jenjang == JenjangStudi.S2
    assert prodis[0].bidang == BidangStudi.EKSAKTA
    assert prodis[0].akreditasi is not None
    assert prodis[0].akreditasi.peringkat == PeringkatAkreditasi.BAIK_SEKALI

    assert prodis[1].jenjang == JenjangStudi.D4
    assert prodis[1].bidang == BidangStudi.NON_EKSAKTA
    assert prodis[1].jumlah_dosen == 0
    assert prodis[1].jumlah_mahasiswa_aktif == 0


def test_sinta_service_validates_url_and_handles_nan_inf():
    import math
    from pddikti_sdk.exceptions import ValidationError

    with pytest.raises(ValidationError):
        SintaService(base_url="file:///etc/passwd")

    with SintaService() as service:
        author = service.parse_author_data({
            "id": "100",
            "fullname": "Dr. Edge",
            "affiliation_name": "UGM",
            "scores": {"overall": "nan", "three_years": "inf"},
            "scopus": {"h_index": "inf", "citations": -5, "documents": "nan"},
        })
        assert math.isfinite(author.scores.overall) and author.scores.overall == 0.0
        assert math.isfinite(author.scores.three_years) and author.scores.three_years == 0.0
        assert author.scopus.h_index == 0
        assert author.scopus.citations == 0
        assert author.scopus.documents == 0


def test_pddikti_service_dos_keyword_length_and_response_size_cap(monkeypatch):
    import httpx
    from pddikti_sdk.exceptions import APIConnectionError, ValidationError
    from pddikti_sdk.services import pddikti as pddikti_mod
    from pddikti_sdk.services.pddikti import PDDiktiService

    # 1. Keyword terlalu panjang ditolak untuk mencegah URL/cache bloat
    client = httpx.Client(
        base_url="https://api-frontend.kemdikbud.go.id",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={})),
    )
    svc = PDDiktiService(client, cache=None)
    with pytest.raises(ValidationError):
        svc.search_all("a" * 300, use_cache=False)

    # 2. Respons melebihi batas ukuran (DoS memori) harus ditolak
    with monkeypatch.context() as mp:
        mp.setattr(pddikti_mod, "MAX_RESPONSE_BYTES", 64)
        big_client = httpx.Client(
            base_url="https://api-frontend.kemdikbud.go.id",
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"pt": [{"id": "1", "text": "X" * 200}]})),
        )
        big_svc = PDDiktiService(big_client, cache=None)
        with pytest.raises(APIConnectionError):
            big_svc.search_all("UI", use_cache=False)

    # 3. Error body dipotong agar tidak memicu information disclosure / memory bloat
    err_client = httpx.Client(
        base_url="https://api-frontend.kemdikbud.go.id",
        transport=httpx.MockTransport(lambda req: httpx.Response(500, text="E" * 5000)),
    )
    err_svc = PDDiktiService(err_client, cache=None)
    with pytest.raises(APIConnectionError) as exc_info:
        err_svc.search_all("UI", use_cache=False)
    assert len(exc_info.value.response_body) <= 2048

    # 4. SintaService menolak cleartext HTTP remote kecuali allow_insecure_http=True
    with pytest.raises(ValidationError):
        SintaService(base_url="http://sinta.example.com")
    with SintaService(base_url="http://sinta.example.com", allow_insecure_http=True) as sinta_http:
        assert sinta_http.base_url == "http://sinta.example.com"



