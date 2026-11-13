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

