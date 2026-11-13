"""Layanan pemrosesan dan verifikasi akreditasi BAN-PT & Lembaga Akreditasi Mandiri (LAM)."""

from datetime import date
from typing import Any, Dict, Optional

from pddikti_sdk.models.akreditasi import (
    AkreditasiInfo,
    LembagaAkreditasi,
    PeringkatAkreditasi,
)


class BanptService:
    """Helper untuk parsing dan normalisasi status akreditasi nasional."""

    @staticmethod
    def parse_peringkat(text: Optional[str]) -> PeringkatAkreditasi:
        """Menormalkan string akreditasi menjadi Enum PeringkatAkreditasi terstandar."""
        if not text:
            return PeringkatAkreditasi.UNKNOWN

        clean = text.strip().upper()
        if "TIDAK TERAKREDITASI" in clean or "BELUM TERAKREDITASI" in clean or clean in ("TT", "-"):
            return PeringkatAkreditasi.TIDAK_TERAKREDITASI
        elif "UNGGUL" in clean:
            return PeringkatAkreditasi.UNGGUL
        elif "BAIK SEKALI" in clean:
            return PeringkatAkreditasi.BAIK_SEKALI
        elif clean == "BAIK" or clean.startswith("BAIK "):
            return PeringkatAkreditasi.BAIK
        elif clean in ("A", "TERAKREDITASI A", "PERINGKAT A"):
            return PeringkatAkreditasi.A
        elif clean in ("B", "TERAKREDITASI B", "PERINGKAT B"):
            return PeringkatAkreditasi.B
        elif clean in ("C", "TERAKREDITASI C", "PERINGKAT C"):
            return PeringkatAkreditasi.C
        elif "KADALUARSA" in clean or "KEDALUWARSA" in clean:
            return PeringkatAkreditasi.KEDALUWARSA
        elif "PROSES" in clean:
            return PeringkatAkreditasi.PROSES
        return PeringkatAkreditasi.UNKNOWN

    @classmethod
    def parse_akreditasi_info(cls, data: Dict[str, Any]) -> AkreditasiInfo:
        """Membuat model AkreditasiInfo dari dictionary respons API."""
        if not isinstance(data, dict):
            data = {}
        peringkat_raw = (
            data.get("akreditasi")
            or data.get("peringkat")
            or data.get("status_akreditasi")
        )
        peringkat = cls.parse_peringkat(peringkat_raw)

        # Lembaga
        lembaga_raw = str(data.get("lembaga") or "BAN-PT").strip().upper()
        lembaga = LembagaAkreditasi.BAN_PT
        if "INFOKOM" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAM_INFOKOM
        elif "PTKES" in lembaga_raw or "KESEHATAN" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAM_PTKES
        elif "EMBA" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAMEMBA
        elif "LAMDIK" in lembaga_raw or "KEPENDIDIKAN" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAMDIK
        elif "TEKNIK" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAM_TEKNIK
        elif "LAMSAMA" in lembaga_raw or "LAM-SAMA" in lembaga_raw or "LAM SAMA" in lembaga_raw or "SAINS ALAM" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAM_SAMA
        elif "BAN-PT" in lembaga_raw or "BAN PT" in lembaga_raw or "BANPT" in lembaga_raw:
            lembaga = LembagaAkreditasi.BAN_PT
        elif lembaga_raw:
            lembaga = LembagaAkreditasi.LAINNYA

        # Tanggal kadaluarsa
        tgl_str = data.get("tgl_kadaluarsa") or data.get("tanggal_kedaluwarsa")
        tgl_obj: Optional[date] = None
        if isinstance(tgl_str, date):
            tgl_obj = tgl_str
        elif tgl_str and isinstance(tgl_str, str):
            try:
                # Format YYYY-MM-DD
                tgl_obj = date.fromisoformat(tgl_str.strip()[:10])
            except ValueError:
                tgl_obj = None

        # Tahun SK
        tahun_raw = data.get("tahun_sk")
        tahun_sk: Optional[int] = None
        if tahun_raw is not None and not isinstance(tahun_raw, bool):
            try:
                tahun_sk = int(str(tahun_raw).strip())
            except (ValueError, TypeError):
                tahun_sk = None

        # Status aktif memperhitungkan flag is_expired dan tanggal kedaluwarsa aktual
        explicit_expired = bool(data.get("is_expired", False))
        date_expired = tgl_obj is not None and date.today() > tgl_obj
        is_expired = explicit_expired or date_expired or (peringkat == PeringkatAkreditasi.KEDALUWARSA)

        return AkreditasiInfo(
            peringkat=peringkat,
            lembaga=lembaga,
            no_sk=data.get("no_sk") or data.get("nomor_sk"),
            tgl_kadaluarsa=tgl_obj,
            tahun_sk=tahun_sk,
            status_aktif=not is_expired,
        )
