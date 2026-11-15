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


def test_cli_table_sanitizes_ansi_and_newlines(capsys):
    print_table(
        ["ID", "Nama"],
        [["1", "\x1b[31mEvil\x1b[0m\r\nRow"]],
        title="Tabel\x1b[2JAman",
    )
    out = capsys.readouterr().out
    assert "\x1b" not in out
    assert "Evil Row" in out


def test_cli_ratio_json_with_export_and_error_exit(monkeypatch, tmp_path, capsys):
    from pddikti_sdk.client import PDDiktiClient
    from pddikti_sdk.models import BidangStudi, JenjangStudi, PerguruanTinggi, ProgramStudi

    sample_pt = PerguruanTinggi(
        kode="001001",
        nama_pt="Universitas CLI",
        daftar_prodi=[
            ProgramStudi(
                kode="55201",
                nama_prodi="Informatika",
                jenjang=JenjangStudi.S1,
                bidang=BidangStudi.EKSAKTA,
                dosen_count=10,
                mahasiswa_count=200,
            )
        ],
    )
    monkeypatch.setattr(PDDiktiClient, "get_perguruan_tinggi", lambda self, id_pt, include_prodi=True, use_cache=True: sample_pt)
    monkeypatch.setattr(PDDiktiClient, "DEFAULT_CACHE_FILE", str(tmp_path / "cli_ratio.db"))

    out_xlsx = tmp_path / "rasio_cli.xlsx"
    ret = main(["ratio", "PT123", "--json", "--export", str(out_xlsx)])
    assert ret == 0
    assert out_xlsx.exists()
    data = json.loads(capsys.readouterr().out)
    assert data["kode_pt"] == "001001"

    # Jika export gagal, exit code harus 1
    def _fail_export(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("pddikti_sdk.cli.export_laporan_rasio_excel", _fail_export)
    ret_err = main(["ratio", "PT123", "--json", "--export", str(out_xlsx)])
    assert ret_err == 1


def test_cli_search_negative_limit(monkeypatch, tmp_path, capsys):
    from pddikti_sdk.client import PDDiktiClient
    from pddikti_sdk.models import EntityType, SearchHitItem, SearchResult

    fake_result = SearchResult(
        keyword="UI",
        perguruan_tinggi=[
            SearchHitItem(id="1", text="UI Satu", entity_type=EntityType.PT),
            SearchHitItem(id="2", text="UI Dua", entity_type=EntityType.PT),
        ],
    )
    monkeypatch.setattr(PDDiktiClient, "search", lambda self, kw, use_cache=True: fake_result)
    monkeypatch.setattr(PDDiktiClient, "DEFAULT_CACHE_FILE", str(tmp_path / "cli_search.db"))

    ret = main(["search", "UI", "--limit", "-1"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "UI Satu" not in out
    assert "UI Dua" not in out



