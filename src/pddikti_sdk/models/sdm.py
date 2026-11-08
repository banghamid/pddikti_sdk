"""Model data Sumber Daya Manusia (SDM) perguruan tinggi: Dosen dan Mahasiswa."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JabatanFungsional(str, Enum):
    TENAGA_PENGAJAR = "Tenaga Pengajar"
    ASISTEN_AHLI = "Asisten Ahli"
    LEKTOR = "Lektor"
    LEKTOR_KEPALA = "Lektor Kepala"
    GURU_BESAR = "Guru Besar / Profesor"
    TIDAK_ADA = "Tidak Memiliki Jabatan Fungsional"


class StatusDosen(str, Enum):
    AKTIF = "Aktif"
    STUDI_LANJUT = "Tugas Belajar / Studi Lanjut"
    CUTI = "Cuti"
    KELUAR = "Keluar / Mengundurkan Diri"
    PENSIUN = "Pensiun"
    ALMARHUM = "Almarhum"
    UNKNOWN = "Tidak Diketahui"


class StatusMahasiswa(str, Enum):
    AKTIF = "Aktif"
    LULUS = "Lulus"
    CUTI = "Cuti"
    NON_AKTIF = "Non-Aktif"
    DROP_OUT = "Drop Out / Dikeluarkan"
    MENGUNDURKAN_DIRI = "Mengundurkan Diri"
    HILANG = "Hilang"
    UNKNOWN = "Tidak Diketahui"


class RiwayatPendidikan(BaseModel):
    """Riwayat pendidikan formal dosen."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    jenjang: str
    gelar_akademik: Optional[str] = None
    nama_institusi: str
    tahun_lulus: Optional[int] = None


class Dosen(BaseModel):
    """Profil dosen terdaftar di PDDikti."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: Optional[str] = Field(None, alias="id_dosen")
    nidn: Optional[str] = Field(None, alias="nidn")
    nidk: Optional[str] = None
    nama: str = Field(..., alias="nama_dosen")
    nama_pt: Optional[str] = None
    nama_prodi: Optional[str] = None
    status: StatusDosen = StatusDosen.AKTIF
    ikatan_kerja: str = "Dosen Tetap"
    pendidikan_terakhir: str = "S2"
    jabatan_fungsional: JabatanFungsional = JabatanFungsional.LEKTOR
    sinta_id: Optional[str] = None
    riwayat_pendidikan: List[RiwayatPendidikan] = Field(default_factory=list)


class Mahasiswa(BaseModel):
    """Profil mahasiswa terdaftar di PDDikti."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: Optional[str] = Field(None, alias="id_mahasiswa")
    nim: str = Field(..., alias="nim")
    nama: str = Field(..., alias="nama_mahasiswa")
    nama_pt: Optional[str] = None
    nama_prodi: Optional[str] = None
    jenjang: str = "S1"
    angkatan: Optional[int] = None
    semester_masuk: Optional[str] = None
    status: StatusMahasiswa = StatusMahasiswa.AKTIF
    jenis_kelamin: Optional[str] = None
