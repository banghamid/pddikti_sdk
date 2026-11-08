"""Demonstrasi Penggunaan Cache SQLite Lokal pada PDDikti SDK.

Menunjukkan cara kerja:
1. Penyimpanan cache otomatis dengan TTL (Time-To-Live).
2. Peningkatan kecepatan query pada pemanggilan kedua (Cache Hit).
3. Proteksi dari batasan kuota (Rate Limit) dan pemantauan statistik cache.
"""

import time
from pddikti_sdk import PDDiktiClient, SQLiteCache


def main():
    print("=== DEMO AKSISTENSI & CACHING SQLITE PDDikti SDK ===\n")

    # Inisialisasi cache khusus untuk demo
    cache = SQLiteCache(db_path="demo_pddikti_cache.db", default_ttl=3600)

    # 1. Simpan payload simulasi hasil pencarian ke dalam cache
    keyword = "universitas gadjah mada"
    data_pt = {
        "pt": [
            {"id": "UGM_HASH_123", "text": "Universitas Gadjah Mada (PTN) - D.I. Yogyakarta"},
        ],
        "prodi": [
            {"id": "PRODI_UGM_01", "text": "Ilmu Komputer (S1) - UGM"},
            {"id": "PRODI_UGM_02", "text": "Teknologi Informasi (S1) - UGM"},
        ],
        "dosen": [],
        "mahasiswa": [],
    }

    cache.set(f"search:{keyword}", data_pt, ttl=3600, tag="search")
    print(f"[1] Data simulasi untuk '{keyword}' berhasil disimpan ke cache SQLite.")

    # 2. Query melalui PDDiktiClient dengan mengarahkan ke cache demo
    with PDDiktiClient(cache=cache) as client:
        t0 = time.perf_counter()
        hasil = client.search(keyword, use_cache=True)
        durasi_ms = (time.perf_counter() - t0) * 1000

        print(f"[2] Query dieksekusi dari cache dalam {durasi_ms:.2f} ms:")
        print(f"    - Total Temuan : {hasil.total_hits}")
        for pt in hasil.perguruan_tinggi:
            print(f"    - PT           : {pt.text} (ID: {pt.id})")
        for prodi in hasil.program_studi:
            print(f"    - Prodi        : {prodi.text}")

        # 3. Cek statistik cache
        stats = client.cache_stats()
        print("\n[3] Statistik Cache SQLite:")
        print(f"    - File Database : {stats['database_path']}")
        print(f"    - Total Entri   : {stats['total_entries']}")
        print(f"    - Hits          : {stats['hits']} kali")
        print(f"    - Misses        : {stats['misses']} kali")
        print(f"    - Hit Rate      : {stats['hit_rate_pct']}%\n")

    # Bersihkan file demo
    cache.close()
    import os
    if os.path.exists("demo_pddikti_cache.db"):
        os.remove("demo_pddikti_cache.db")
    print("[SUKSES] Demo selesai dan berkas cache sementara telah dibersihkan.")


if __name__ == "__main__":
    main()
