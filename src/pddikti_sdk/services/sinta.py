"""Layanan pengaksesan dan integrasi data SINTA (Science and Technology Index)."""

from typing import Any, Dict, List, Optional
import httpx

from pddikti_sdk.exceptions import APIConnectionError, ResourceNotFoundError
from pddikti_sdk.models.sinta import (
    GarudaMetrics,
    GoogleScholarMetrics,
    IprMetrics,
    ScopusMetrics,
    SintaAuthor,
    SintaInstitution,
    SintaScore,
    WosMetrics,
)


class SintaService:
    """Implementasi sinkron untuk integrasi data SINTA."""

    DEFAULT_SINTA_URL = "https://sinta.kemdikbud.go.id"

    def __init__(self, client: Optional[httpx.Client] = None, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or self.DEFAULT_SINTA_URL).rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            headers={
                "User-Agent": "pddikti-sdk/0.2.0 (Python Academic Client)",
                "Accept": "application/json, text/html",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        """Menutup koneksi HTTP internal jika dibuat oleh SintaService."""
        if self._owns_client and self._client is not None:
            self._client.close()

    def __enter__(self) -> "SintaService":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    @staticmethod
    def _safe_int(val: Any, default: int = 0) -> int:
        if val is None or isinstance(val, bool):
            return default
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float(val: Any, default: float = 0.0) -> float:
        if val is None or isinstance(val, bool):
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def parse_author_data(self, data: Dict[str, Any]) -> SintaAuthor:
        """Membuat model SintaAuthor dari dictionary data terstruktur."""
        if not isinstance(data, dict):
            data = {}
        scores_data = data.get("scores") if isinstance(data.get("scores"), dict) else {}
        scopus_data = data.get("scopus") if isinstance(data.get("scopus"), dict) else {}
        scholar_data = data.get("scholar") if isinstance(data.get("scholar"), dict) else {}
        garuda_data = data.get("garuda") if isinstance(data.get("garuda"), dict) else {}
        wos_data = data.get("wos") if isinstance(data.get("wos"), dict) else {}
        ipr_data = data.get("ipr") if isinstance(data.get("ipr"), dict) else {}
        raw_subjects = data.get("subjects") or data.get("bidang_keahlian")
        subjects = [str(s) for s in raw_subjects] if isinstance(raw_subjects, list) else []

        return SintaAuthor(
            id=str(data.get("id") or data.get("sinta_id") or "0"),
            fullname=str(data.get("fullname") or data.get("nama") or "Unknown"),
            nidn=data.get("nidn"),
            affiliation_name=str(data.get("affiliation_name") or data.get("afiliasi_pt") or "-"),
            department_name=data.get("department_name") or data.get("afiliasi_prodi"),
            bidang_keahlian=subjects,
            scores=SintaScore(
                overall=self._safe_float(scores_data.get("overall"), 0.0),
                three_years=self._safe_float(scores_data.get("three_years"), 0.0),
                productivity_overall=self._safe_float(scores_data.get("productivity_overall"), 0.0),
                productivity_three_years=self._safe_float(scores_data.get("productivity_three_years"), 0.0),
            ),
            scopus=ScopusMetrics(
                h_index=self._safe_int(scopus_data.get("h_index"), 0),
                citations=self._safe_int(scopus_data.get("citations"), 0),
                documents=self._safe_int(scopus_data.get("documents"), 0),
                g_index=self._safe_int(scopus_data.get("g_index"), 0),
            ),
            scholar=GoogleScholarMetrics(
                h_index=self._safe_int(scholar_data.get("h_index"), 0),
                i10_index=self._safe_int(scholar_data.get("i10_index"), 0),
                citations=self._safe_int(scholar_data.get("citations"), 0),
                documents=self._safe_int(scholar_data.get("documents"), 0),
            ),
            garuda=GarudaMetrics(
                documents=self._safe_int(garuda_data.get("documents"), 0),
                citations=self._safe_int(garuda_data.get("citations"), 0),
            ),
            wos=WosMetrics(
                documents=self._safe_int(wos_data.get("documents"), 0),
                citations=self._safe_int(wos_data.get("citations"), 0),
            ),
            ipr=IprMetrics(
                patent=self._safe_int(ipr_data.get("patent"), 0),
                copyright=self._safe_int(ipr_data.get("copyright"), 0),
            ),
        )

    def parse_institution_data(self, data: Dict[str, Any]) -> SintaInstitution:
        """Membuat model SintaInstitution dari payload terstruktur."""
        if not isinstance(data, dict):
            data = {}
        peringkat_nas = data.get("peringkat_nasional")
        peringkat_3th = data.get("peringkat_3th")
        return SintaInstitution(
            sinta_id=str(data.get("id") or data.get("sinta_id") or ""),
            kode_pt=data.get("kode_pt"),
            nama=str(data.get("nama") or data.get("name") or "Unknown Institution"),
            singkatan=data.get("singkatan"),
            peringkat_nasional=self._safe_int(peringkat_nas) if peringkat_nas is not None else None,
            peringkat_3th=self._safe_int(peringkat_3th) if peringkat_3th is not None else None,
            score_overall=self._safe_float(data.get("score_overall"), 0.0),
            score_3th=self._safe_float(data.get("score_3th"), 0.0),
            jumlah_author=self._safe_int(data.get("jumlah_author"), 0),
            jumlah_departemen=self._safe_int(data.get("jumlah_departemen"), 0),
        )
