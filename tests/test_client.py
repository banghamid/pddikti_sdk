import asyncio
import pytest
from pddikti_sdk.client import AsyncPDDiktiClient, PDDiktiClient


def test_client_init_and_subservices():
    client = PDDiktiClient()
    assert client.base_url == "https://api-frontend.kemdikbud.go.id"
    assert client.timeout == 30.0
    assert client.sinta is not None
    assert client.banpt is not None
    assert client.analytics is not None
    assert client.aggregator is not None
    client.close()


def test_client_context_manager():
    with PDDiktiClient(base_url="https://custom.example.com", timeout=15.0) as client:
        assert client.base_url == "https://custom.example.com"
        assert client.timeout == 15.0


def test_async_client_context_manager():
    async def _runner():
        async with AsyncPDDiktiClient(base_url="https://async.example.com", cache=False) as client:
            assert client.base_url == "https://async.example.com"

    asyncio.run(_runner())


def test_async_client_parity_methods(tmp_path):
    async def _runner():
        db_file = tmp_path / "async_cache.db"
        async with AsyncPDDiktiClient(cache=db_file) as client:
            assert client.cache is not None
            # Pre-populate cache for detail PT and prodi list
            client.cache.set(
                "pt:PT123",
                {"nama_pt": "Universitas Async", "kode_pt": "001002", "jml_mhs": 200, "jml_dosen": 10},
                tag="pt",
            )
            client.cache.set(
                "prodi:PT123",
                [{"id_sms": "P1", "kode_prodi": "55201", "nm_lemb": "Informatika", "jml_dosen": 10, "jml_mhs": 200}],
                tag="prodi",
            )
            pt = await client.get_perguruan_tinggi("PT123", include_prodi=True)
            assert pt.nama == "Universitas Async"
            assert len(pt.daftar_prodi) == 1

            laporan = client.analyze_ratio(pt)
            assert laporan.total_dosen == 10

            stats = client.cache_stats()
            assert stats["hits"] == 2

            deleted = client.clear_cache()
            assert deleted == 2

    asyncio.run(_runner())


def test_client_validates_url_and_timeout():
    from pddikti_sdk.exceptions import ValidationError

    for bad_url in ["file:///etc/passwd", "ftp://example.com", "javascript:alert(1)", "not-a-url", "https://"]:
        with pytest.raises(ValidationError):
            PDDiktiClient(base_url=bad_url, cache=False)
        with pytest.raises(ValidationError):
            AsyncPDDiktiClient(base_url=bad_url, cache=False)

    with pytest.raises(ValidationError):
        PDDiktiClient(sinta_base_url="file:///tmp", cache=False)
    with pytest.raises(ValidationError):
        AsyncPDDiktiClient(sinta_base_url="file:///tmp", cache=False)

    for bad_timeout in [0, -5.0, float("nan"), float("inf")]:
        with pytest.raises(ValidationError):
            PDDiktiClient(timeout=bad_timeout, cache=False)
        with pytest.raises(ValidationError):
            AsyncPDDiktiClient(timeout=bad_timeout, cache=False)


def test_async_client_has_sinta_subservice():
    async def _runner():
        async with AsyncPDDiktiClient(
            base_url="https://async.example.com",
            sinta_base_url="https://sinta.example.com/",
            cache=False,
        ) as client:
            assert client.sinta is not None
            assert client.sinta.base_url == "https://sinta.example.com"

    asyncio.run(_runner())


def test_client_rejects_insecure_remote_http_and_ssrf_urls():
    from pddikti_sdk.exceptions import ValidationError

    # Remote cleartext HTTP harus ditolak secara default
    with pytest.raises(ValidationError):
        PDDiktiClient(base_url="http://api.example.com", cache=False)
    with pytest.raises(ValidationError):
        AsyncPDDiktiClient(base_url="http://api.example.com", cache=False)

    # Jika diizinkan eksplisit, HTTP remote tetap bisa digunakan
    with PDDiktiClient(base_url="http://api.example.com", allow_insecure_http=True, cache=False) as c:
        assert c.base_url == "http://api.example.com"

    # Loopback HTTP diizinkan untuk pengembangan lokal
    with PDDiktiClient(base_url="http://localhost:8080", cache=False) as c_local:
        assert c_local.base_url == "http://localhost:8080"

    # Kredensial tertanam di URL dan IP metadata/link-local/unspecified harus ditolak (SSRF)
    for dangerous_url in [
        "https://user:secret@api.example.com",
        "https://169.254.169.254/latest/meta-data",
        "http://169.254.169.254",
        "http://0.0.0.0:8000",
    ]:
        with pytest.raises(ValidationError):
            PDDiktiClient(base_url=dangerous_url, cache=False)


def test_client_rejects_crlf_in_headers():
    from pddikti_sdk.exceptions import ValidationError

    with pytest.raises(ValidationError):
        PDDiktiClient(headers={"X-Custom": "val\r\nX-Injected: evil"}, cache=False)

    with pytest.raises(ValidationError):
        AsyncPDDiktiClient(headers={"Bad\nHeader": "val"}, cache=False)



