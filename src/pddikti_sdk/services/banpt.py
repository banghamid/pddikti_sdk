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
        if "UNGGUL" in clean:
            return PeringkatAkreditasi.UNGGUL
        elif "BAIK SEKALI" in clean:
            return PeringkatAkreditasi.BAIK_SEKALI
        elif clean == "BAIK" or clean.startswith("BAIK "):
            return PeringkatAkreditasi.BAIK
        elif clean == "A":
            return PeringkatAkreditasi.A
        elif clean == "B":
            return PeringkatAkreditasi.B
        elif clean == "C":
            return PeringkatAkreditasi.C
        elif "KADALUARSA" in clean or "KEDALUWARSA" in clean:
            return PeringkatAkreditasi.KEDALUWARSA
        elif "PROSES" in clean:
            return PeringkatAkreditasi.PROSES
        return PeringkatAkreditasi.UNKNOWN

    @classmethod
    def parse_akreditasi_info(cls, data: Dict[str, Any]) -> AkreditasiInfo:
        """Membuat model AkreditasiInfo dari dictionary respons API."""
        peringkat_raw = (
            data.get("akreditasi")
            or data.get("peringkat")
            or data.get("status_akreditasi")
        )
        peringkat = cls.parse_peringkat(peringkat_raw)

        # Lembaga
        lembaga_raw = (data.get("lembaga") or "BAN-PT").upper()
        lembaga = LembagaAkreditasi.BAN_PT
        if "INFOKOM" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAM_INFOKOM
        elif "PTKES" in lembaga_raw or "KESEHATAN" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAM_PTKES
        elif "EMBA" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAMEMBA
        elif "DIK" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAMDIK
        elif "TEKNIK" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAM_TEKNIK
        elif "SAMA" in lembaga_raw:
            lembaga = LembagaAkreditasi.LAM_SAMA

        # Tanggal kadaluarsa
        tgl_str = data.get("tgl_kadaluarsa") or data.get("tanggal_kedaluwarsa")
        tgl_obj = None
        if tgl_str and isinstance(tgl_str, str):
            try:
                # Format YYYY-MM-DD
                tgl_obj = date.fromisoformat(tgl_str[:10])
            except ValueError:
                tgl_obj = None

        return AkreditasiInfo(
            peringkat=peringkat,
            lembaga=lembaga,
            no_sk=data.get("no_sk") or data.get("nomor_sk"),
            tgl_kadaluarsa=tgl_obj,
            tahun_sk=int(data.get("tahun_sk")) if data.get("tahun_sk") else None,
            status_aktif=not data.get("is_expired", False),
        )
