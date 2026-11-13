"""Modul analisis kepatuhan dan anomali rasio dosen-mahasiswa sesuai standar nasional."""

from enum import Enum
import math
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from pddikti_sdk.models.perguruan_tinggi import BidangStudi, ProgramStudi, PerguruanTinggi


class StatusKepatuhanRasio(str, Enum):
    IDEAL = "Ideal (Sesuai Standar Mutu)"
    MEMENUHI = "Memenuhi Batas Toleransi"
    DEFISIT_DOSEN = "Defisit Dosen (Rasio Terlalu Gemuk)"
    ANOMALI_EKSTRIM = "Anomali Ekstrim (> 1:100 atau Tanpa Dosen)"
    UNDER_ENROLLED = "Mahasiswa Sangat Sedikit (< 1:2)"
    TIDAK_ADA_DATA = "Data Tidak Lengkap"


class LaporanRasioProdi(BaseModel):
    """Hasil analisis rasio dosen-mahasiswa untuk sebuah Program Studi."""
    model_config = ConfigDict(populate_by_name=True)

    kode_prodi: str
    nama_prodi: str
    jenjang: str
    bidang: BidangStudi
    jumlah_dosen: int
    jumlah_mahasiswa: int
    rasio_aktual: float
    status: StatusKepatuhanRasio
    rekomendasi: str


class LaporanRasioPT(BaseModel):
    """Hasil analisis rasio dosen-mahasiswa tingkat Perguruan Tinggi."""
    model_config = ConfigDict(populate_by_name=True)

    kode_pt: str
    nama_pt: str
    total_dosen: int
    total_mahasiswa: int
    rasio_agregat: float
    sebaran_status_prodi: Dict[str, int]
    daftar_prodi: List[LaporanRasioProdi] = Field(default_factory=list)
    prodi_defisit: List[LaporanRasioProdi] = Field(default_factory=list)
    prodi_anomali: List[LaporanRasioProdi] = Field(default_factory=list)


class RatioAnalyzer:
    """Mesin analisis rasio dosen dan mahasiswa berdasarkan standar BAN-PT."""

    # Standar rasio nasional ideal & toleransi maksimal
    AMBANG_BATAS = {
        BidangStudi.EKSAKTA: {
            "ideal": 20.0,
            "toleransi": 35.0,
        },
        BidangStudi.NON_EKSAKTA: {
            "ideal": 30.0,
            "toleransi": 45.0,
        },
        BidangStudi.CAMPURAN: {
            "ideal": 25.0,
            "toleransi": 40.0,
        },
    }

    @classmethod
    def evaluasi_prodi(cls, prodi: ProgramStudi) -> LaporanRasioProdi:
        """Mengevaluasi rasio satu program studi."""
        dosen = prodi.jumlah_dosen
        mhs = prodi.jumlah_mahasiswa_aktif
        bidang = prodi.bidang

        if dosen == 0 and mhs == 0:
            status = StatusKepatuhanRasio.TIDAK_ADA_DATA
            rekomendasi = "Data dosen dan mahasiswa aktif tercatat 0."
            rasio = 0.0
        elif dosen == 0 and mhs > 0:
            status = StatusKepatuhanRasio.ANOMALI_EKSTRIM
            rekomendasi = f"PERINGATAN KRITIS: Memiliki {mhs} mahasiswa aktif namun 0 dosen tetap terdaftar."
            rasio = float(mhs)
        elif dosen > 0 and mhs == 0:
            status = StatusKepatuhanRasio.UNDER_ENROLLED
            rekomendasi = f"Memiliki {dosen} dosen tetapi tidak memiliki mahasiswa aktif terdaftar."
            rasio = 0.0
        else:
            rasio = round(mhs / dosen, 2)
            ambang = cls.AMBANG_BATAS.get(bidang, cls.AMBANG_BATAS[BidangStudi.CAMPURAN])

            if rasio > 100.0:
                status = StatusKepatuhanRasio.ANOMALI_EKSTRIM
                rekomendasi = f"Rasio 1:{rasio} melampaui batas wajar 1:100. Beban mengajar dosen tidak proporsional."
            elif rasio > ambang["toleransi"]:
                status = StatusKepatuhanRasio.DEFISIT_DOSEN
                dosen_dibutuhkan = max(1, math.ceil(mhs / ambang["ideal"]) - dosen)
                rekomendasi = f"Rasio 1:{rasio} melebihi batas toleransi 1:{ambang['toleransi']}. Disarankan menambah minimal {dosen_dibutuhkan} dosen."
            elif rasio > ambang["ideal"]:
                status = StatusKepatuhanRasio.MEMENUHI
                rekomendasi = f"Rasio 1:{rasio} masih dalam batas toleransi akreditasi, mendekati batas ideal 1:{ambang['ideal']}."
            elif rasio < 2.0:
                status = StatusKepatuhanRasio.UNDER_ENROLLED
                rekomendasi = f"Rasio 1:{rasio} sangat rendah (< 1:2), perlu evaluasi keterisian mahasiswa baru."
            else:
                status = StatusKepatuhanRasio.IDEAL
                rekomendasi = f"Rasio 1:{rasio} sangat ideal dan memenuhi standar mutu akreditasi (<= 1:{ambang['ideal']})."

        return LaporanRasioProdi(
            kode_prodi=prodi.kode_prodi,
            nama_prodi=prodi.nama,
            jenjang=prodi.jenjang.value if hasattr(prodi.jenjang, "value") else str(prodi.jenjang),
            bidang=bidang,
            jumlah_dosen=dosen,
            jumlah_mahasiswa=mhs,
            rasio_aktual=rasio,
            status=status,
            rekomendasi=rekomendasi,
        )

    @classmethod
    def evaluasi_pt(cls, pt: PerguruanTinggi) -> LaporanRasioPT:
        """Mengevaluasi seluruh program studi di sebuah perguruan tinggi."""
        laporan_prodi: List[LaporanRasioProdi] = []
        sebaran: Dict[str, int] = {}
        defisit: List[LaporanRasioProdi] = []
        anomali: List[LaporanRasioProdi] = []

        for p in pt.daftar_prodi:
            lp = cls.evaluasi_prodi(p)
            laporan_prodi.append(lp)
            s_val = lp.status.value
            sebaran[s_val] = sebaran.get(s_val, 0) + 1

            if lp.status == StatusKepatuhanRasio.DEFISIT_DOSEN:
                defisit.append(lp)
            elif lp.status == StatusKepatuhanRasio.ANOMALI_EKSTRIM:
                anomali.append(lp)

        total_d = pt.total_dosen_tetap or sum(p.jumlah_dosen for p in pt.daftar_prodi)
        total_m = pt.total_mahasiswa_aktif or sum(p.jumlah_mahasiswa_aktif for p in pt.daftar_prodi)
        rasio_pt = round(total_m / total_d, 2) if total_d > 0 else 0.0

        return LaporanRasioPT(
            kode_pt=pt.kode_pt,
            nama_pt=pt.nama,
            total_dosen=total_d,
            total_mahasiswa=total_m,
            rasio_agregat=rasio_pt,
            sebaran_status_prodi=sebaran,
            daftar_prodi=laporan_prodi,
            prodi_defisit=defisit,
            prodi_anomali=anomali,
        )
