import time
from pathlib import Path
import pytest

from pddikti_sdk.cache import SQLiteCache
from pddikti_sdk.client import PDDiktiClient


def test_sqlite_cache_set_and_get():
    cache = SQLiteCache(db_path=":memory:", default_ttl=3600)
    cache.set("test_key", {"kampus": "UGM", "skor": 95}, tag="pt")

    result = cache.get("test_key")
    assert result is not None
    assert result["kampus"] == "UGM"
    assert result["skor"] == 95

    # Cek stats
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0
    assert stats["total_entries"] == 1


def test_sqlite_cache_miss():
    cache = SQLiteCache(db_path=":memory:")
    assert cache.get("kunci_tidak_ada") is None

    stats = cache.stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0


def test_sqlite_cache_expiration():
    # TTL 1 detik
    cache = SQLiteCache(db_path=":memory:", default_ttl=1)
    cache.set("exp_key", "data sementara", ttl=1)

    assert cache.get("exp_key") == "data sementara"
    time.sleep(1.1)
    # Setelah 1.1 detik harus sudah kedaluwarsa (None)
    assert cache.get("exp_key") is None


def test_sqlite_cache_delete_and_clear():
    cache = SQLiteCache(db_path=":memory:")
    cache.set("k1", "val1", tag="tag_a")
    cache.set("k2", "val2", tag="tag_b")
    cache.set("k3", "val3", tag="tag_a")

    assert cache.stats()["total_entries"] == 3

    # Hapus satu
    deleted = cache.delete("k1")
    assert deleted is True
    assert cache.get("k1") is None
    assert cache.stats()["total_entries"] == 2

    # Clear tag_a
    cache.clear(tag="tag_a")
    assert cache.get("k3") is None
    assert cache.get("k2") == "val2"

    # Clear semua
    cache.clear()
    assert cache.stats()["total_entries"] == 0


def test_client_with_custom_cache(tmp_path):
    db_file = tmp_path / "custom_pddikti.db"
    cache = SQLiteCache(db_path=db_file)

    # Simpan data manual ke cache untuk mensimulasikan query
    cache.set("search:ugm", {"pt": [{"id": "123", "text": "Universitas Gadjah Mada"}]}, tag="search")

    with PDDiktiClient(cache=cache) as client:
        # Panggil search dengan keyword 'ugm' yang sudah ada di cache
        res = client.search("ugm", use_cache=True)
        assert res.total_hits == 1
        assert res.perguruan_tinggi[0].text == "Universitas Gadjah Mada"

        # Verifikasi statistik cache hit meningkat
        stats = client.cache_stats()
        assert stats["hits"] >= 1
