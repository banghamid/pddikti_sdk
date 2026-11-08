"""Contoh Integrasi Neo Feeder PDDIKTI Web Service untuk Pengembang Sistem Kampus (SIAKAD).

Menunjukkan:
1. Uji koneksi & handshake autentikasi ke server Neo Feeder lokal/kampus.
2. Pengambilan profil perguruan tinggi dan program studi.
3. Generator streaming data mahasiswa/dosen secara bertahap (iter_records).
"""

from pddikti_sdk import NeoFeederClient


def main():
    print("=== DEMO INTEGRASI NEO FEEDER PDDIKTI WEB SERVICE ===\n")

    # Inisialisasi client Neo Feeder kampus
    # Catatan: ganti URL, username, dan password sesuai server Feeder kampus Anda
    feeder = NeoFeederClient(
        base_url="http://localhost:8100/ws/live2.php",
        username="user_siakad",
        password="password_rahasia",
        timeout=60.0,
    )

    print(f"Target URL Feeder: {feeder.base_url}")
    print("Catatan: Jika server Feeder fisik sedang offline, pemanggilan jaringan akan mengembalikan status error yang aman.\n")

    # 1. Menguji koneksi
    status_koneksi = feeder.test_connection()
    print("Hasil Uji Koneksi:")
    print(f"- Status : {status_koneksi['status'].upper()}")
    print(f"- Pesan  : {status_koneksi['message']}")

    # 2. Contoh pemanggilan fungsi umum (bila terhubung):
    # profil_pt = feeder.get_profil_pt()
    # prodi_list = feeder.get_daftar_prodi()
    # for mhs in feeder.iter_records("GetBiodataMahasiswa", chunk_size=50, max_records=200):
    #     print(mhs["nama_mahasiswa"])


if __name__ == "__main__":
    main()
