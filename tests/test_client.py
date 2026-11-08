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
        async with AsyncPDDiktiClient(base_url="https://async.example.com") as client:
            assert client.base_url == "https://async.example.com"

    asyncio.run(_runner())
