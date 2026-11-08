"""Command-Line Interface (CLI) untuk pddikti-sdk.

Menyediakan utilitas terminal interaktif untuk pencarian data, inspeksi perguruan tinggi,
evaluasi rasio dosen-mahasiswa BAN-PT, verifikasi akreditasi, dan ringkasan metrik SINTA.
"""

import argparse
import json
import sys
from typing import Any, List, Optional

from pddikti_sdk import (
    BanptService,
    BidangStudi,
    DataAggregator,
    JenjangStudi,
    NeoFeederClient,
    PDDiktiClient,
    PerguruanTinggi,
    ProgramStudi,
    RatioAnalyzer,
    StatusKepatuhanRasio,
    export_laporan_rasio_excel,
    __version__,
)


def print_table(headers: List[str], rows: List[List[str]], title: Optional[str] = None) -> None:
    """Mencetak tabel rapi ke konsol terminal tanpa dependensi eksternal."""
    if title:
        print(f"\n=== {title} ===")

    if not rows:
        print("(Tidak ada data)")
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(val)))

    # Header row
    header_str = " | ".join(f"{h.ljust(col_widths[i])}" for i, h in enumerate(headers))
    sep_str = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

    print(header_str)
    print(sep_str)
    for row in rows:
        row_str = " | ".join(f"{str(val).ljust(col_widths[i])}" for i, val in enumerate(row))
        print(row_str)
    print()


def handle_search(args: argparse.Namespace) -> int:
    """Menangani perintah: pddikti search <keyword>"""
    keyword = " ".join(args.keyword).strip()
    if not keyword:
        print("Error: Harap berikan kata kunci pencarian. Contoh: pddikti search \"Universitas Indonesia\"")
        return 1

    use_cache = not getattr(args, "no_cache", False)
    if not args.json:
        cache_note = " (Cache dinonaktifkan)" if not use_cache else ""
        print(f"Mencari '{keyword}' di PDDikti Kemendikbudristek{cache_note}...")
    try:
        with PDDiktiClient(timeout=args.timeout) as client:
            result = client.search(keyword, use_cache=use_cache)
    except Exception as e:
        print(f"Gagal melakukan pencarian: {e}")
        return 1

    if args.json:
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
        return 0

    print(f"Total hasil ditemukan: {result.total_hits}\n")

    # Tabel Perguruan Tinggi
    if result.perguruan_tinggi and args.category in ("all", "pt"):
        pt_rows = [[item.id or "-", item.text] for item in result.perguruan_tinggi[: args.limit]]
        print_table(["ID / Hash", "Perguruan Tinggi"], pt_rows, title=f"Perguruan Tinggi (Max {args.limit})")

    # Tabel Program Studi
    if result.program_studi and args.category in ("all", "prodi"):
        prodi_rows = [[item.id or "-", item.text] for item in result.program_studi[: args.limit]]
        print_table(["ID / Hash", "Program Studi"], prodi_rows, title=f"Program Studi (Max {args.limit})")

    # Tabel Dosen
    if result.dosen and args.category in ("all", "dosen"):
        dosen_rows = [[item.id or "-", item.text] for item in result.dosen[: args.limit]]
        print_table(["ID / Hash", "Nama Dosen"], dosen_rows, title=f"Dosen (Max {args.limit})")

    # Tabel Mahasiswa
    if result.mahasiswa and args.category in ("all", "mahasiswa"):
        mhs_rows = [[item.id or "-", item.text] for item in result.mahasiswa[: args.limit]]
        print_table(["ID / Hash", "Mahasiswa"], mhs_rows, title=f"Mahasiswa (Max {args.limit})")

    return 0


def handle_pt(args: argparse.Namespace) -> int:
    """Menangani perintah: pddikti pt <id_pt>"""
    id_pt = args.id_pt.strip()
    use_cache = not getattr(args, "no_cache", False)
    if not args.json:
        cache_note = " (Cache dinonaktifkan)" if not use_cache else ""
        print(f"Mengambil profil Perguruan Tinggi (ID: {id_pt}){cache_note}...")

    try:
        with PDDiktiClient(timeout=args.timeout) as client:
            pt = client.get_perguruan_tinggi(id_pt, include_prodi=not args.no_prodi, use_cache=use_cache)
    except Exception as e:
        print(f"Gagal mengambil detail PT: {e}")
        return 1

    if args.json:
        print(json.dumps(pt.model_dump(), indent=2, ensure_ascii=False))
        return 0

    print(f"\n========================================================")
    print(f"PROFIL PERGURUAN TINGGI")
    print(f"========================================================")
    print(f"Nama Kampus     : {pt.nama}")
    print(f"Kode / NPSN     : {pt.kode_pt}")
    print(f"Provinsi / Kota : {pt.provinsi or '-'} / {pt.kab_kota or '-'}")
    print(f"Kepemilikan     : {pt.status_kepemilikan}")
    print(f"Total Mahasiswa : {pt.total_mahasiswa_aktif:,}")
    print(f"Total Dosen     : {pt.total_dosen_tetap:,}")
    print(f"Rasio Kampus    : 1 : {pt.rasio_agregat_kampus}")
    print(f"Total Prodi     : {len(pt.daftar_prodi)}")

    if pt.daftar_prodi and not args.no_prodi:
        rows = [
            [
                p.kode_prodi,
                p.nama,
                p.status,
                str(p.jumlah_dosen),
                str(p.jumlah_mahasiswa_aktif),
                f"1:{p.rasio_dosen_mahasiswa}",
            ]
            for p in pt.daftar_prodi
        ]
        print_table(
            ["Kode", "Nama Program Studi", "Status", "Dosen", "Mhs Aktif", "Rasio"],
            rows,
            title="Daftar Program Studi",
        )

    return 0


def handle_ratio(args: argparse.Namespace) -> int:
    """Menangani perintah: pddikti ratio <id_pt>"""
    id_pt = args.id_pt.strip()
    use_cache = not getattr(args, "no_cache", False)
    if not args.json:
        cache_note = " (Cache dinonaktifkan)" if not use_cache else ""
        print(f"Melakukan evaluasi rasio kepatuhan BAN-PT untuk PT: {id_pt}{cache_note}...")

    try:
        with PDDiktiClient(timeout=args.timeout) as client:
            pt = client.get_perguruan_tinggi(id_pt, include_prodi=True, use_cache=use_cache)
            laporan = client.analyze_ratio(pt)
    except Exception as e:
        print(f"Gagal menganalisis rasio PT: {e}")
        return 1

    if args.json:
        print(json.dumps(laporan.model_dump(), indent=2, ensure_ascii=False))
        return 0

    print(f"\n========================================================")
    print(f"LAPORAN KEPATUHAN RASIO DOSEN-MAHASISWA (BAN-PT)")
    print(f"========================================================")
    print(f"Kampus           : {laporan.nama_pt} ({laporan.kode_pt})")
    print(f"Total Dosen      : {laporan.total_dosen:,}")
    print(f"Total Mahasiswa  : {laporan.total_mahasiswa:,}")
    print(f"Rasio Agregat PT : 1 : {laporan.rasio_agregat}")
    print("\nRingkasan Status Prodi:")
    for status, count in laporan.sebaran_status_prodi.items():
        print(f"  - {status}: {count} prodi")

    if laporan.prodi_anomali:
        print(f"\n[PERINGATAN] DITEMUKAN {len(laporan.prodi_anomali)} PRODI ANOMALI EKSTRIM:")
        rows = [
            [p.kode_prodi, p.nama_prodi, str(p.jumlah_dosen), str(p.jumlah_mahasiswa), f"1:{p.rasio_aktual}"]
            for p in laporan.prodi_anomali
        ]
        print_table(["Kode", "Program Studi", "Dosen", "Mhs", "Rasio"], rows)

    if laporan.prodi_defisit and not args.only_anomalies:
        print(f"\nPRODI DEFISIT DOSEN ({len(laporan.prodi_defisit)} prodi melebihi batas toleransi):")
        rows = [
            [p.kode_prodi, p.nama_prodi, str(p.jumlah_dosen), str(p.jumlah_mahasiswa), f"1:{p.rasio_aktual}"]
            for p in laporan.prodi_defisit
        ]
        print_table(["Kode", "Program Studi", "Dosen", "Mhs", "Rasio"], rows)

    if getattr(args, "export", None):
        try:
            excel_path = export_laporan_rasio_excel(laporan, args.export)
            print(f"\n[SUKSES] Laporan Excel berhasil disimpan di: {excel_path}")
        except Exception as e:
            print(f"\n[GAGAL] Gagal mengekspor laporan Excel: {e}")

    return 0


def handle_akreditasi(args: argparse.Namespace) -> int:
    """Menangani perintah: pddikti akreditasi --peringkat <peringkat> [--lembaga <lembaga>] [--exp <YYYY-MM-DD>]"""
    data = {
        "akreditasi": args.peringkat,
        "lembaga": args.lembaga or "BAN-PT",
        "no_sk": args.sk,
        "tgl_kadaluarsa": args.exp,
    }
    info = BanptService.parse_akreditasi_info(data)

    if args.json:
        print(json.dumps(info.model_dump(), indent=2, default=str, ensure_ascii=False))
        return 0

    print(f"\n=== HASIL VERIFIKASI AKREDITASI ===")
    print(f"Peringkat Terstandar : {info.peringkat.value}")
    print(f"Lembaga Akreditasi   : {info.lembaga.value}")
    print(f"Nomor SK             : {info.nomor_sk or '-'}")
    print(f"Tanggal Kedaluwarsa  : {info.tanggal_kedaluwarsa or '-'}")
    print(f"Status Masa Berlaku  : {'KEDALUWARSA' if info.is_expired else 'AKTIF / BERLAKU'}")
    print(f"Tingkat Tertinggi    : {'Ya (Unggul / A)' if info.is_unggul_or_a else 'Bukan Unggul/A'}\n")
    return 0


def handle_demo_sinta(args: argparse.Namespace) -> int:
    """Menampilkan simulasi metrik riset SINTA dan Scopus."""
    from pddikti_sdk import SintaAuthor, SintaScore, ScopusMetrics, GoogleScholarMetrics, IprMetrics

    dummy_authors = [
        SintaAuthor(
            id="6001234",
            fullname="Prof. Dr. Ir. Budi Rahardjo, M.Sc.",
            affiliation_name="Institut Teknologi Nusantara",
            department_name="Informatika",
            scores=SintaScore(overall=2150.0, three_years=780.0),
            scopus=ScopusMetrics(h_index=14, citations=620, documents=28),
            scholar=GoogleScholarMetrics(h_index=20, citations=1450, documents=52),
            ipr=IprMetrics(patent=3, copyright=6),
        ),
        SintaAuthor(
            id="6005678",
            fullname="Dr. Maya Safitri, S.Kom., M.T.",
            affiliation_name="Institut Teknologi Nusantara",
            department_name="Informatika",
            scores=SintaScore(overall=1420.0, three_years=510.0),
            scopus=ScopusMetrics(h_index=9, citations=310, documents=16),
            scholar=GoogleScholarMetrics(h_index=15, citations=790, documents=34),
            ipr=IprMetrics(patent=1, copyright=4),
        ),
    ]

    rekap = DataAggregator.ringkas_produktivitas_sinta(dummy_authors)

    if args.json:
        print(json.dumps(rekap, indent=2, ensure_ascii=False))
        return 0

    print(f"\n=== DEMO SIMULASI PRODUKTIVITAS RISET SINTA ===")

    rows = [
        [a.sinta_id, a.nama, str(a.scores.three_years), str(a.scopus.documents), str(a.scopus.citations), str(a.scopus.h_index)]
        for a in dummy_authors
    ]
    print_table(["SINTA ID", "Nama Author", "Score 3-Yr", "Scopus Docs", "Scopus Cit", "H-Index"], rows, title="Daftar Peneliti")

    print(f"Total Author Riset     : {rekap['total_author']}")
    print(f"Total Dokumen Scopus   : {rekap['total_scopus_documents']}")
    print(f"Total Sitasi Scopus    : {rekap['total_scopus_citations']}")
    print(f"Total Paten Terdaftar  : {rekap['total_paten_terdaftar']}")
    print(f"Rata-rata Skor 3-Tahun : {rekap['rata_rata_skor_3tahun']}\n")
    return 0


def handle_cache(args: argparse.Namespace) -> int:
    """Menangani perintah: pddikti cache [--stats | --clear | --expired-only]"""
    with PDDiktiClient() as client:
        if args.clear:
            deleted = client.clear_cache(expired_only=args.expired_only)
            if args.json:
                print(json.dumps({"deleted": deleted}))
            else:
                scope = "yang telah kedaluwarsa" if args.expired_only else "secara keseluruhan"
                print(f"[SUKSES] Berhasil membersihkan {deleted} entri cache SQLite ({scope}).")
            return 0

        stats = client.cache_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
            return 0

        print(f"\n=== STATISTIK CACHE SQLITE PDDikti ===")
        print(f"Lokasi Database  : {stats.get('database_path')}")
        print(f"Total Entri      : {stats.get('total_entries', 0):,}")
        print(f"Entri Aktif      : {stats.get('active_entries', 0):,}")
        print(f"Entri Kedaluwarsa: {stats.get('expired_entries', 0):,}")
        print(f"Ukuran Berkas    : {stats.get('file_size_kb', 0.0)} KB")
        print(f"Hit Count        : {stats.get('hits', 0):,} kali")
        print(f"Miss Count       : {stats.get('misses', 0):,} kali")
        print(f"Hit Rate         : {stats.get('hit_rate_pct', 0.0)}%\n")
    return 0


def handle_feeder(args: argparse.Namespace) -> int:
    """Menangani perintah: pddikti feeder <action>"""
    url = getattr(args, "url", "http://localhost:8082/ws/live2.php")
    user = getattr(args, "user", "")
    password = getattr(args, "password", "")

    client = NeoFeederClient(base_url=url, username=user, password=password, timeout=getattr(args, "timeout", 60.0))

    if args.feeder_action == "test":
        print(f"Menguji koneksi ke Neo Feeder pada {url}...")
        res = client.test_connection()
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0
        print(f"Status Koneksi : {res.get('status').upper()}")
        print(f"Pesan          : {res.get('message')}")
        if res.get("token_preview"):
            print(f"Token Otentikasi: {res.get('token_preview')}")
        return 0 if res.get("status") == "connected" else 1

    elif args.feeder_action == "query":
        act = args.act
        kwargs = {}
        if getattr(args, "filter", None):
            kwargs["filter"] = args.filter
        if getattr(args, "limit", None):
            kwargs["limit"] = args.limit

        res = client.execute(act, **kwargs)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Membangun argument parser CLI pddikti."""
    parser = argparse.ArgumentParser(
        prog="pddikti",
        description="PDDikti CLI - Tool Terminal Modern untuk Data Pendidikan Tinggi Indonesia, SINTA & BAN-PT.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"pddikti-sdk v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Perintah yang tersedia")

    # Command: search
    parser_search = subparsers.add_parser("search", help="Cari data Perguruan Tinggi, Prodi, Dosen, atau Mahasiswa")
    parser_search.add_argument("keyword", nargs="+", help="Kata kunci pencarian")
    parser_search.add_argument("-l", "--limit", type=int, default=10, help="Jumlah maksimal item ditampilkan (default: 10)")
    parser_search.add_argument("-c", "--category", choices=["all", "pt", "prodi", "dosen", "mahasiswa"], default="all", help="Kategori filter")
    parser_search.add_argument("--no-cache", action="store_true", help="Lewati pembacaan cache lokal dan paksa permintaan jaringan baru")
    parser_search.add_argument("--timeout", type=float, default=30.0, help="Batas waktu koneksi HTTP (detik)")
    parser_search.add_argument("--json", action="store_true", help="Keluarkan output dalam format JSON mentah")

    # Command: pt
    parser_pt = subparsers.add_parser("pt", help="Inspeksi profil lengkap Perguruan Tinggi")
    parser_pt.add_argument("id_pt", help="Hash ID atau kode unik Perguruan Tinggi di PDDikti")
    parser_pt.add_argument("--no-prodi", action="store_true", help="Jangan tampilkan daftar program studi")
    parser_pt.add_argument("--no-cache", action="store_true", help="Lewati pembacaan cache lokal")
    parser_pt.add_argument("--timeout", type=float, default=30.0, help="Batas waktu koneksi HTTP (detik)")
    parser_pt.add_argument("--json", action="store_true", help="Keluarkan output dalam format JSON")

    # Command: ratio
    parser_ratio = subparsers.add_parser("ratio", help="Evaluasi rasio kepatuhan dosen-mahasiswa standar BAN-PT")
    parser_ratio.add_argument("id_pt", help="Hash ID atau kode unik Perguruan Tinggi")
    parser_ratio.add_argument("--only-anomalies", action="store_true", help="Hanya tampilkan prodi dengan anomali ekstrim")
    parser_ratio.add_argument("-e", "--export", help="Nama atau path file output Excel (.xlsx) untuk laporan berformat rapi")
    parser_ratio.add_argument("--no-cache", action="store_true", help="Lewati pembacaan cache lokal")
    parser_ratio.add_argument("--timeout", type=float, default=30.0, help="Batas waktu koneksi HTTP (detik)")
    parser_ratio.add_argument("--json", action="store_true", help="Keluarkan output dalam format JSON")

    # Command: akreditasi
    parser_akr = subparsers.add_parser("akreditasi", help="Normalisasi dan verifikasi masa berlaku akreditasi BAN-PT/LAM")
    parser_akr.add_argument("--peringkat", required=True, help="Contoh: 'Unggul', 'Baik Sekali', 'A', 'B'")
    parser_akr.add_argument("--lembaga", default="BAN-PT", help="Contoh: 'BAN-PT', 'LAM-INFOKOM', 'LAM-PTKes', 'LAMEMBA'")
    parser_akr.add_argument("--sk", help="Nomor SK Akreditasi")
    parser_akr.add_argument("--exp", help="Tanggal kedaluwarsa format YYYY-MM-DD")
    parser_akr.add_argument("--json", action="store_true", help="Keluarkan output dalam format JSON")

    # Command: sinta
    parser_sinta = subparsers.add_parser("sinta", help="Inspeksi metrik publikasi SINTA & Scopus")
    parser_sinta.add_argument("--demo", action="store_true", default=True, help="Tampilkan simulasi agregasi riset SINTA")
    parser_sinta.add_argument("--json", action="store_true", help="Keluarkan output dalam format JSON")

    # Command: cache
    parser_cache = subparsers.add_parser("cache", help="Kelola dan pantau cache SQLite lokal")
    parser_cache.add_argument("--stats", action="store_true", default=True, help="Tampilkan statistik penggunaan cache (default)")
    parser_cache.add_argument("--clear", action="store_true", help="Hapus seluruh rekaman cache SQLite")
    parser_cache.add_argument("--expired-only", action="store_true", help="Hanya hapus entri yang telah kedaluwarsa")
    parser_cache.add_argument("--json", action="store_true", help="Keluarkan statistik dalam format JSON")

    # Command: feeder
    parser_feeder = subparsers.add_parser("feeder", help="Konektor web service Neo Feeder PDDIKTI kampus")
    sub_feeder = parser_feeder.add_subparsers(dest="feeder_action", help="Aksi Feeder")

    # feeder test
    feeder_test = sub_feeder.add_parser("test", help="Uji konektivitas dan autentikasi ke server Feeder")
    feeder_test.add_argument("--url", default="http://localhost:8082/ws/live2.php", help="URL Feeder (default: http://localhost:8082/ws/live2.php)")
    feeder_test.add_argument("-u", "--user", default="", help="Username / Kode Pengguna Feeder")
    feeder_test.add_argument("-p", "--password", default="", help="Password Pengguna Feeder")
    feeder_test.add_argument("--json", action="store_true", help="Keluarkan output JSON")

    # feeder query
    feeder_query = sub_feeder.add_parser("query", help="Jalankan pemanggilan fungsi RPC Feeder")
    feeder_query.add_argument("act", help="Nama fungsi (misal: 'GetProfilPT', 'GetBiodataMahasiswa')")
    feeder_query.add_argument("--url", default="http://localhost:8082/ws/live2.php", help="URL Feeder")
    feeder_query.add_argument("-u", "--user", default="", help="Username Feeder")
    feeder_query.add_argument("-p", "--password", default="", help="Password Feeder")
    feeder_query.add_argument("--filter", help="Filter string (misal: id_prodi='123')")
    feeder_query.add_argument("--limit", type=int, default=10, help="Jumlah maksimal data")

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """Titik masuk utama aplikasi CLI."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 0

    if parsed_args.command == "search":
        return handle_search(parsed_args)
    elif parsed_args.command == "pt":
        return handle_pt(parsed_args)
    elif parsed_args.command == "ratio":
        return handle_ratio(parsed_args)
    elif parsed_args.command == "akreditasi":
        return handle_akreditasi(parsed_args)
    elif parsed_args.command == "sinta":
        return handle_demo_sinta(parsed_args)
    elif parsed_args.command == "cache":
        return handle_cache(parsed_args)
    elif parsed_args.command == "feeder":
        if not parsed_args.feeder_action:
            parser_feeder.print_help()
            return 0
        return handle_feeder(parsed_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
