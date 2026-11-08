import pytest
from pddikti_sdk.client import PDDiktiClient


def test_client_init():
    client = PDDiktiClient()
    assert client.base_url == "https://api-frontend.kemdikbud.go.id"
    assert client.timeout == 30.0
    client.close()


def test_client_context_manager():
    with PDDiktiClient(base_url="https://custom-api.example.com", timeout=10.0) as client:
        assert client.base_url == "https://custom-api.example.com"
        assert client.timeout == 10.0
