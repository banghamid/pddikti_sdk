import io
import json
import sys
from pddikti_sdk.cli import create_parser, main, print_table


def test_cli_table_formatter(capsys):
    headers = ["Nama", "Peran"]
    rows = [["Budi", "Dosen"], ["Siti", "Mahasiswa"]]
    print_table(headers, rows, title="Uji Tabel")
    captured = capsys.readouterr().out
    assert "Uji Tabel" in captured
    assert "Budi" in captured
    assert "Mahasiswa" in captured


def test_cli_akreditasi_json(capsys):
    ret = main([
        "akreditasi",
        "--peringkat", "Unggul",
        "--lembaga", "LAM-INFOKOM",
        "--sk", "123/SK/2024",
        "--exp", "2029-12-31",
        "--json",
    ])
    assert ret == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["peringkat"] == "Unggul"
    assert data["lembaga"] == "LAM-INFOKOM"
    assert data["status_aktif"] is True


def test_cli_sinta_demo_json(capsys):
    ret = main(["sinta", "--demo", "--json"])
    assert ret == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert "total_author" in data
    assert data["total_author"] == 2
    assert "total_scopus_documents" in data


def test_cli_help(capsys):
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "PDDikti CLI" in captured
    assert "search" in captured
    assert "ratio" in captured
    assert "cache" in captured


def test_cli_cache_commands(monkeypatch, tmp_path, capsys):
    from pddikti_sdk.client import PDDiktiClient

    temp_db = tmp_path / "cli_test_cache.db"
    monkeypatch.setattr(PDDiktiClient, "DEFAULT_CACHE_FILE", str(temp_db))

    # Test stats
    ret_stats = main(["cache", "--json"])
    assert ret_stats == 0
    captured = capsys.readouterr().out
    stats = json.loads(captured)
    assert "database_path" in stats
    assert str(temp_db) in stats["database_path"]
    assert "total_entries" in stats

    # Test clear
    ret_clear = main(["cache", "--clear", "--json"])
    assert ret_clear == 0
    captured_clear = capsys.readouterr().out
    res = json.loads(captured_clear)
    assert "deleted" in res


