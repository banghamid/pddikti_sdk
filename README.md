# PDDikti SDK

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-e92063.svg)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/tests-16%20passed-brightgreen.svg)]()

**PDDikti SDK** adalah pustaka Python modern, terawat, dan dilengkapi sistem *type safety* lengkap (Pydantic V2) untuk mengakses dan menganalisis data ekosistem pendidikan tinggi Indonesia: **PDDikti Kemendikbudristek**, **Publikasi & Metrik SINTA**, **Akreditasi BAN-PT & Lembaga Akreditasi Mandiri (LAM)**, serta **Mesin Analisis Rasio Kepatuhan Dosen-Mahasiswa**.

Dirancang khusus untuk membantu **peneliti sosial**, **jurnalis data**, **analis kebijakan publik**, dan **pengembang sistem informasi kampus** dalam membaca serta mengevaluasi tren pendidikan tinggi di Indonesia.

---

## 🎯 Fitur Utama

1. **🏛️ Data Agregat Perguruan Tinggi & Prodi:**
   - Pencarian multi-entitas cerdas (Mahasiswa, Dosen, PT, Program Studi).
   - Profil lengkap PT, sebaran jenjang studi (D3, D4, S1, S2, S3), dan status keaktifan.
2. **🔬 Integrasi Publikasi & Metrik SINTA:**
   - Skor SINTA Author & Institusi (*Overall*, *3-Years*, *Productivity Score*).
   - Metrik publikasi multi-basis data: Scopus (*h-index*, sitasi, dokumen), Google Scholar, GARUDA, Web of Science (WoS), serta Kekayaan Intelektual (Paten & Hak Cipta).
3. **📜 Akreditasi BAN-PT & Lembaga Akreditasi Mandiri (LAM):**
   - Normalisasi status peringkat (Unggul, Baik Sekali, Baik, A, B, C).
   - Dukungan multi-lembaga: BAN-PT, LAM-INFOKOM, LAM-PTKes, LAMEMBA, LAMDIK, LAM Teknik, LAMSAMA.
   - Pengecekan otomatis masa berlaku SK akreditasi (*expiration detector*).
4. **📊 Mesin Evaluasi Rasio Dosen-Mahasiswa (`RatioAnalyzer`):**
   - Standar BAN-PT untuk rumpun **Eksakta / Teknik / Kesehatan** (Ideal $\le$ 1:20, toleransi s.d. 1:35) dan **Sosial / Humaniora** (Ideal $\le$ 1:30, toleransi s.d. 1:45).
   - Deteksi otomatis anomali ekstrim (> 1:100 atau prodi aktif tanpa dosen tetap terdaftar) serta rekomendasi kebutuhan formasi dosen.
5. **⚡ Arsitektur Dual-Mode & Integrasi Neo Feeder Kampus:**
   - **Mode Publik:** `PDDiktiClient` & `AsyncPDDiktiClient` untuk data publik Dikti, SINTA, dan akreditasi BAN-PT dengan akselerasi cache SQLite.
   - **Mode Kampus:** `NeoFeederClient` & `AsyncNeoFeederClient` untuk komunikasi langsung ke server Feeder internal kampus (`ws/live2.php` atau `ws/sandbox2.php`), dilengkapi *handshake token* otomatis, *auto-retry* saat sesi habis, dan streaming data mahasiswa/dosen bertahap (`iter_records`).
6. **📊 Ekspor Laporan & Tooling:**
   - Ekspor laporan kepatuhan rasio ke Excel (.xlsx) dengan pewarnaan mutu BAN-PT otomatis.
   - Konversi mudah ke Pandas DataFrame.

---

## 📦 Instalasi

```bash
pip install pddikti-sdk
```

Atau instalasi mode pengembang dari repositori:

```bash
git clone https://github.com/banghamid/pddikti_sdk.git
cd pddikti_sdk
pip install -e .
```

---

## 💻 Antarmuka Baris Perintah (CLI Tool: `pddikti-cli` / `pddikti`)

`pddikti-sdk` dilengkapi dengan antarmuka terminal interaktif yang dapat langsung dijalankan tanpa menulis kode Python:

```bash
# 1. Bantuan dan daftar perintah
pddikti --help

# 2. Pencarian data multi-entitas
pddikti search "Universitas Indonesia"
pddikti search "Teknik Informatika" --category prodi --limit 5

# 3. Inspeksi profil Perguruan Tinggi
pddikti pt <ID_KAMPUS_HASH>

# 4. Evaluasi kepatuhan rasio dosen-mahasiswa BAN-PT
pddikti ratio <ID_KAMPUS_HASH>
pddikti ratio <ID_KAMPUS_HASH> --only-anomalies
pddikti ratio <ID_KAMPUS_HASH> --export laporan_mutu.xlsx

# 5. Verifikasi peringkat & masa kedaluwarsa akreditasi BAN-PT / LAM
pddikti akreditasi --peringkat "Unggul" --lembaga "LAM-INFOKOM" --sk "999/SK/2024" --exp "2029-05-20"

# 6. Simulasi agregasi riset SINTA
pddikti sinta --demo

# 7. Output JSON mentah (cocok untuk scripting dan pipe ke jq)
pddikti search "UGM" --json
pddikti akreditasi --peringkat "A" --json

# 8. Manajemen & Pemantauan Cache SQLite
pddikti cache --stats
pddikti cache --clear
pddikti search "ITB" --no-cache

# 9. Integrasi Neo Feeder Kampus (Web Service SIAKAD)
pddikti feeder test --url http://localhost:8082/ws/live2.php -u user_feeder -p pass_feeder
pddikti feeder query GetProfilPT --url http://localhost:8082/ws/live2.php -u user_feeder -p pass_feeder
```

---

## 🚀 Panduan Penggunaan Python SDK

### 1. Pencarian Agregat & Profil Perguruan Tinggi

```python
from pddikti_sdk import PDDiktiClient

# Menggunakan cache SQLite bawaan (~/.pddikti/cache.db) dengan TTL 24 jam
with PDDiktiClient(cache=True) as client:
    # Query pertama: mengambil data dari jaringan PDDikti dan menyimpannya di SQLite
    hasil = client.search("Universitas Indonesia")
    print(f"Total temuan: {hasil.total_hits}")

    # Query kedua dengan kata kunci sama: < 5 ms dari cache lokal tanpa beban jaringan
    hasil_cepat = client.search("Universitas Indonesia")

    # Cek metrik hit & ukuran database cache
    stats = client.cache_stats()
    print(f"Cache Hit Rate: {stats['hit_rate_pct']}% | Total Entri: {stats['total_entries']}")
```

---

### 2. Evaluasi Rasio Dosen-Mahasiswa & Deteksi Anomali

```python
from pddikti_sdk import (
    PDDiktiClient,
    PerguruanTinggi,
    ProgramStudi,
    JenjangStudi,
    BidangStudi,
    RatioAnalyzer,
    export_laporan_rasio_excel,
)

# Simulasi data Program Studi
prodi_hukum = ProgramStudi(
    kode="74201",
    nama_prodi="Ilmu Hukum",
    jenjang=JenjangStudi.S1,
    bidang=BidangStudi.NON_EKSAKTA,
    dosen_count=3,
    mahasiswa_count=390,  # Rasio 1:130 (anomali)
)

pt = PerguruanTinggi(
    kode="001001",
    nama_pt="Universitas Contoh",
    daftar_prodi=[prodi_hukum],
)

# 1. Evaluasi kepatuhan rasio BAN-PT
laporan = RatioAnalyzer.evaluasi_pt(pt)

print(f"Rasio Agregat Kampus: 1 : {laporan.rasio_agregat}")
for anomali in laporan.prodi_anomali:
    print(f"[PERINGATAN] {anomali.nama_prodi}: {anomali.rekomendasi}")

# 2. Ekspor Laporan Excel Berformat Warna Otomatis (.xlsx)
file_excel = export_laporan_rasio_excel(laporan, "laporan_kepatuhan_banpt.xlsx")
print(f"Laporan Excel tersimpan: {file_excel}")
```

---

### 3. Analisis Produktivitas Riset Dosen (SINTA & Scopus)

```python
from pddikti_sdk import SintaService, DataAggregator

sinta = SintaService()

author = sinta.parse_author_data({
    "id": "6001234",
    "fullname": "Dr. Ir. Ahmad Santoso, M.T.",
    "affiliation_name": "Institut Teknologi Nusantara",
    "scores": {"overall": 1250.5, "three_years": 480.0},
    "scopus": {"h_index": 8, "citations": 230, "documents": 18},
    "scholar": {"h_index": 14, "citations": 620, "documents": 35},
    "ipr": {"patent": 2, "copyright": 5},
})

print(f"Author: {author.nama} | SINTA 3Yr: {author.scores.three_years}")
print(f"Scopus H-Index: {author.scopus.h_index} | Citations: {author.scopus.citations}")
```

---

### 4. Verifikasi Status Akreditasi BAN-PT & LAM

```python
from pddikti_sdk import BanptService

akreditasi = BanptService.parse_akreditasi_info({
    "akreditasi": "Unggul",
    "lembaga": "LAM-INFOKOM",
    "no_sk": "112/SK/LAM-INFOKOM/Akred/S/X/2024",
    "tgl_kadaluarsa": "2029-10-15",
})

print(f"Peringkat : {akreditasi.peringkat.value} ({akreditasi.lembaga.value})")
print(f"Status    : {'Aktif' if not akreditasi.is_expired else 'Kedaluwarsa'}")
```

### 5. Integrasi Sistem Kampus (Neo Feeder Web Service)

```python
from pddikti_sdk import NeoFeederClient

# Inisialisasi koneksi ke server Feeder kampus
feeder = NeoFeederClient(
    base_url="http://localhost:8082/ws/live2.php",
    username="operator_kampus",
    password="password_rahasia",
)

# 1. Uji koneksi dan periksa token
status = feeder.test_connection()
print(f"Status Feeder: {status['status']}")

# 2. Ambil profil PT kampus
profil = feeder.get_profil_pt()
print(f"Kampus: {profil.get('nama_perguruan_tinggi')}")

# 3. Stream data mahasiswa bertahap (aman memori untuk ribuan data)
for mhs in feeder.iter_records("GetBiodataMahasiswa", chunk_size=100, max_records=500):
    print(f"[{mhs['nim']}] {mhs['nama_mahasiswa']}")
```

---

## 📁 Struktur Repositori

```text
pddikti_sdk/
├── src/
│   └── pddikti_sdk/
│       ├── __init__.py          # Entrypoint & ekspor publik
│       ├── client.py            # PDDiktiClient & AsyncPDDiktiClient
│       ├── exceptions.py        # Hierarki exception khusus
│       ├── models/              # Validasi model berbasis Pydantic V2
│       │   ├── common.py        # Model entitas & hasil pencarian
│       │   ├── perguruan_tinggi.py # Profil PT, Prodi, Statistik
│       │   ├── sdm.py           # Model Dosen & Mahasiswa
│       │   ├── akreditasi.py    # BAN-PT & Lembaga Akreditasi Mandiri (LAM)
│       │   └── sinta.py         # Author SINTA, Scopus, Scholar, H-Index
│       ├── services/            # Service integrasi endpoint
│       │   ├── pddikti.py       # PDDikti frontend API client (sync/async)
│       │   ├── sinta.py         # SINTA parser & service
│       │   └── banpt.py         # Akreditasi parser & validator
│       └── analytics/           # Analisis untuk jurnalis & periset
│           ├── ratio.py         # Rasio dosen-mahasiswa & detektor anomali
│           └── aggregator.py    # Agregator sebaran wilayah & DataFrame converter
├── examples/
│   ├── analisis_rasio_dosen_mahasiswa.py
│   └── analisis_sinta_dan_akreditasi.py
├── tests/
│   ├── test_models.py
│   ├── test_analytics.py
│   ├── test_services.py
│   └── test_client.py
├── pyproject.toml
└── README.md
```

---

## 🧪 Menjalankan Pengujian

```bash
pytest -v
```

---

## 📄 Lisensi

Didistribusikan di bawah lisensi [MIT License](LICENSE). Hak Cipta (c) 2026 banghamid.
