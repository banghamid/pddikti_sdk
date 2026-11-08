import asyncio
from unittest.mock import MagicMock, patch
import pytest

from pddikti_sdk.feeder import AsyncNeoFeederClient, FeederException, NeoFeederClient


def test_feeder_client_init():
    client = NeoFeederClient(
        base_url="http://192.168.1.100:8082/ws/live2.php",
        username="admin_kampus",
        password="secretpassword",
        timeout=45.0,
    )
    assert client.base_url == "http://192.168.1.100:8082/ws/live2.php"
    assert client.username == "admin_kampus"
    assert client.timeout == 45.0


def test_feeder_get_token_success():
    client = NeoFeederClient(username="test_user", password="test_password")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "error_code": 0,
        "error_desc": "",
        "data": {"token": "dummy_token_abc_123"},
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp):
        token = client.get_token()
        assert token == "dummy_token_abc_123"


def test_feeder_get_token_auth_failed():
    client = NeoFeederClient(username="wrong_user", password="wrong_password")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "error_code": 102,
        "error_desc": "Username atau Password salah",
        "data": None,
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(FeederException) as exc_info:
            client.get_token(force_refresh=True)
        assert exc_info.value.error_code == 102
        assert "Username atau Password salah" in exc_info.value.error_desc


def test_feeder_execute_and_token_refresh():
    client = NeoFeederClient(username="test_user", password="test_password")
    client._token = "old_expired_token"

    # Panggilan 1: error_code 100 (token expired)
    # Panggilan 2: GetToken refresh
    # Panggilan 3: retry execute berhasil
    resp_expired = MagicMock()
    resp_expired.json.return_value = {
        "error_code": 100,
        "error_desc": "Token expired or invalid",
        "data": None,
    }
    resp_expired.raise_for_status = MagicMock()

    resp_token = MagicMock()
    resp_token.json.return_value = {
        "error_code": 0,
        "error_desc": "",
        "data": {"token": "new_fresh_token_xyz"},
    }
    resp_token.raise_for_status = MagicMock()

    resp_success = MagicMock()
    resp_success.json.return_value = {
        "error_code": 0,
        "error_desc": "",
        "data": [{"nama_pt": "Politeknik Contoh", "kode_pt": "005001"}],
    }
    resp_success.raise_for_status = MagicMock()

    with patch("httpx.Client.post", side_effect=[resp_expired, resp_token, resp_success]):
        result = client.execute("GetProfilPT")
        assert result["error_code"] == 0
        assert result["data"][0]["kode_pt"] == "005001"
        assert client._token == "new_fresh_token_xyz"


def test_feeder_iter_records():
    client = NeoFeederClient()
    client._token = "valid_token"

    chunk_1 = {"error_code": 0, "data": [{"id": 1}, {"id": 2}]}
    chunk_2 = {"error_code": 0, "data": [{"id": 3}]}
    chunk_3 = {"error_code": 0, "data": []}

    with patch.object(client, "execute", side_effect=[chunk_1, chunk_2, chunk_3]):
        records = list(client.iter_records("GetBiodataMahasiswa", chunk_size=2))
        assert len(records) == 3
        assert records[0]["id"] == 1
        assert records[2]["id"] == 3


def test_feeder_test_connection_success():
    client = NeoFeederClient()
    with patch.object(client, "get_token", return_value="dummy_token_123456"):
        with patch.object(client, "execute", return_value={"data": [{"nama_pt": "Kampus Sukses"}]}):
            res = client.test_connection()
            assert res["status"] == "connected"
            assert "dummy_toke..." in res["token_preview"]


def test_async_feeder_execute():
    client = AsyncNeoFeederClient()
    client._token = "valid_async_token"

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"error_code": 0, "data": [{"prodi": "Informatika"}]}
    mock_resp.raise_for_status = MagicMock()

    async def _test():
        with patch("httpx.AsyncClient.post", return_value=mock_resp):
            res = await client.execute("GetProdi")
            assert res["data"][0]["prodi"] == "Informatika"

    asyncio.run(_test())
