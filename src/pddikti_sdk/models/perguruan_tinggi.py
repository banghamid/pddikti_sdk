"""Model data Perguruan Tinggi, Program Studi, dan agregasi statistik institusi."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from pddikti_sdk.models.akreditasi import AkreditasiInfo, PeringkatAkreditasi


class BentukPendidikan(str, Enum):
    UNIVERSITAS = "Universitas"
    INSTITUT = "Institut"
    POLITEKNIK = "Politeknik"
    SEKOLAH_TINGGI = "Sekolah Tinggi"
    AKADEMI = "Akademi"
    AKADEMI_KOMUNITAS = "Akademi Komunitas"
    LAINNYA = "Lainnya"


class StatusPT(str, Enum):
    AKTIF = "Aktif"
    PEMBINAAN = "Dalam Pembinaan"
    ALAM_TUTUP = "Tutup"
    MERGER = "Alih Bentuk / Merger"
    UNKNOWN = "Tidak Diketahui"


class JenjangStudi(str, Enum):
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4 / Sarjana Terapan"
    S1 = "S1"
    PROFESI = "Profesi"
    SPESIALIS_1 = "Spesialis-1"
    SPESIALIS_2 = "Spesialis-2"
    S2 = "S2"
    S2_TERAPAN = "S2 Terapan"
    S3 = "S3"
    S3_TERAPAN = "S3 Terapan"
    LAINNYA = "Lainnya"


class BidangStudi(str, Enum):
    EKSAKTA = "Eksakta / Teknik / Kesehatan"
    NON_EKSAKTA = "Sosial / Humaniora / Seni"
    CAMPURAN = "Campuran"


class ProgramStudi(BaseModel):
    """Informasi Program Studi dalam lingkup Perguruan Tinggi."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: Optional[str] = Field(None, alias="id_prodi")
    kode_prodi: str = Field(..., alias="kode")
    nama: str = Field(..., alias="nama_prodi")
    jenjang: JenjangStudi = JenjangStudi.S1
    status: str = "Aktif"
    bidang: BidangStudi = BidangStudi.NON_EKSAKTA
    akreditasi: Optional[AkreditasiInfo] = None
    jumlah_dosen: int = Field(0, alias="dosen_count")
    jumlah_mahasiswa_aktif: int = Field(0, alias="mahasiswa_count")

    @property
    def rasio_dosen_mahasiswa(self) -> float:
        """Menghitung rasio dosen terhadap mahasiswa (1 dosen melayani X mahasiswa)."""
        if self.jumlah_dosen <= 0:
            return 0.0
        return round(self.jumlah_mahasiswa_aktif / self.jumlah_dosen, 2)


class PerguruanTinggi(BaseModel):
    """Data profil lengkap Perguruan Tinggi (PT)."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: Optional[str] = Field(None, alias="id_pt")
    kode_pt: str = Field(..., alias="kode")
    nama: str = Field(..., alias="nama_pt")
    singkatan: Optional[str] = None
    bentuk: BentukPendidikan = BentukPendidikan.UNIVERSITAS
    status: StatusPT = StatusPT.AKTIF
    status_kepemilikan: str = "Swasta"  # PTN / PTS / PTK
    wilayah: Optional[str] = None       # LLDIKTI / Wilayah
    provinsi: Optional[str] = None
    kab_kota: Optional[str] = None
    akreditasi: Optional[AkreditasiInfo] = None
    daftar_prodi: List[ProgramStudi] = Field(default_factory=list)

    # Statistik Agregat
    total_mahasiswa_aktif: int = 0
    total_dosen_tetap: int = 0
    total_prodi: int = 0

    @property
    def rasio_agregat_kampus(self) -> float:
        """Rasio agregat kampus (total mahasiswa aktif / total dosen tetap)."""
        if self.total_dosen_tetap <= 0:
            return 0.0
        return round(self.total_mahasiswa_aktif / self.total_dosen_tetap, 2)

    @property
    def ringkasan_akreditasi_prodi(self) -> Dict[str, int]:
        """Menghitung sebaran akreditasi program studi di PT ini."""
        dist: Dict[str, int] = {}
        for prodi in self.daftar_prodi:
            p = prodi.akreditasi.peringkat.value if prodi.akreditasi else PeringkatAkreditasi.UNKNOWN.value
            dist[p] = dist.get(p, 0) + 1
        return dist
