# PDDikti SDK

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Python SDK modern dan mudah digunakan untuk berinteraksi dengan data PDDikti (Pangkalan Data Pendidikan Tinggi) Kemendikbudristek.

---

## Fitur Utama

- 🚀 **Ringan & Cepat:** Menggunakan `httpx` untuk performa permintaan HTTP yang optimal.
- 🛡️ **Validasi Data:** Terintegrasi dengan model `pydantic` untuk parsing dan validasi data.
- 🔍 **Pencarian Komprehensif:** Mendukung pencarian Mahasiswa, Dosen, Perguruan Tinggi, dan Program Studi.
- 📦 **Modern Packaging:** Sesuai standar PEP 517 / PEP 621 menggunakan `pyproject.toml`.

---

## Instalasi

```bash
pip install pddikti-sdk
```

Atau instalasi langsung untuk development:

```bash
git clone https://github.com/banghamid/pddikti_sdk.git
cd pddikti_sdk
pip install -e .
```

---

## Contoh Penggunaan Cepat

```python
from pddikti_sdk import PDDiktiClient

# Inisialisasi client
with PDDiktiClient() as client:
    # Pencarian kata kunci
    hasil = client.search("Universitas Gadjah Mada")
    print(hasil)
```

---

## Struktur Repositori

```text
pddikti_sdk/
├── src/
│   └── pddikti_sdk/
│       ├── __init__.py
│       └── client.py
├── tests/
│   ├── __init__.py
│   └── test_client.py
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

---

## Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).
