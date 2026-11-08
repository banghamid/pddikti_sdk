"""Model data akreditasi perguruan tinggi dan program studi (BAN-PT & Lembaga Akreditasi Mandiri/LAM)."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PeringkatAkreditasi(str, Enum):
    UNGGUL = "Unggul"
    BAIK_SEKALI = "Baik Sekali"
    BAIK = "Baik"
    A = "A"
    B = "B"
    C = "C"
    TIDAK_TERAKREDITASI = "Tidak Terakreditasi"
    KEDALUWARSA = "Kedaluwarsa"
    PROSES = "Dalam Proses"
    UNKNOWN = "Tidak Diketahui"


class LembagaAkreditasi(str, Enum):
    BAN_PT = "BAN-PT"
    LAM_PTKES = "LAM-PTKes"
    LAM_INFOKOM = "LAM-INFOKOM"
    LAMEMBA = "LAMEMBA"
    LAMDIK = "LAMDIK"
    LAM_TEKNIK = "LAM Teknik"
    LAM_SAMA = "LAMSAMA"
    LAINNYA = "Lainnya"


class AkreditasiInfo(BaseModel):
    """Informasi sertifikasi akreditasi BAN-PT atau LAM."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    peringkat: PeringkatAkreditasi = PeringkatAkreditasi.UNKNOWN
    lembaga: LembagaAkreditasi = LembagaAkreditasi.BAN_PT
    nomor_sk: Optional[str] = Field(None, alias="no_sk")
    tanggal_sk: Optional[date] = None
    tanggal_kedaluwarsa: Optional[date] = Field(None, alias="tgl_kadaluarsa")
    tahun_sk: Optional[int] = None
    status_aktif: bool = True

    @property
    def is_expired(self) -> bool:
        """Mengecek apakah masa berlaku sertifikat akreditasi telah terlampaui."""
        if not self.tanggal_kedaluwarsa:
            return False
        today = date.today()
        return today > self.tanggal_kedaluwarsa

    @property
    def is_unggul_or_a(self) -> bool:
        """Memeriksa apakah akreditasi berada pada tingkat tertinggi (Unggul atau A)."""
        return self.peringkat in (PeringkatAkreditasi.UNGGUL, PeringkatAkreditasi.A)
