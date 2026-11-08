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
        self._client = client or httpx.Client(
            base_url=self.base_url,
            headers={
                "User-Agent": "pddikti-sdk/0.1.0 (Python Academic Client)",
                "Accept": "application/json, text/html",
            },
            timeout=30.0,
        )

    def parse_author_data(self, data: Dict[str, Any]) -> SintaAuthor:
        """Membuat model SintaAuthor dari dictionary data terstruktur."""
        scores_data = data.get("scores", {})
        scopus_data = data.get("scopus", {})
        scholar_data = data.get("scholar", {})
        garuda_data = data.get("garuda", {})
        ipr_data = data.get("ipr", {})

        return SintaAuthor(
            id=str(data.get("id") or data.get("sinta_id", "0")),
            fullname=data.get("fullname") or data.get("nama", "Unknown"),
            nidn=data.get("nidn"),
            affiliation_name=data.get("affiliation_name") or data.get("afiliasi_pt", "-"),
            department_name=data.get("department_name") or data.get("afiliasi_prodi"),
            bidang_keahlian=data.get("subjects", []),
            scores=SintaScore(
                overall=float(scores_data.get("overall", 0.0)),
                three_years=float(scores_data.get("three_years", 0.0)),
                productivity_overall=float(scores_data.get("productivity_overall", 0.0)),
                productivity_three_years=float(scores_data.get("productivity_three_years", 0.0)),
            ),
            scopus=ScopusMetrics(
                h_index=int(scopus_data.get("h_index", 0)),
                citations=int(scopus_data.get("citations", 0)),
                documents=int(scopus_data.get("documents", 0)),
                g_index=int(scopus_data.get("g_index", 0)),
            ),
            scholar=GoogleScholarMetrics(
                h_index=int(scholar_data.get("h_index", 0)),
                i10_index=int(scholar_data.get("i10_index", 0)),
                citations=int(scholar_data.get("citations", 0)),
                documents=int(scholar_data.get("documents", 0)),
            ),
            garuda=GarudaMetrics(
                documents=int(garuda_data.get("documents", 0)),
                citations=int(garuda_data.get("citations", 0)),
            ),
            ipr=IprMetrics(
                patent=int(ipr_data.get("patent", 0)),
                copyright=int(ipr_data.get("copyright", 0)),
            ),
        )

    def parse_institution_data(self, data: Dict[str, Any]) -> SintaInstitution:
        """Membuat model SintaInstitution dari payload terstruktur."""
        return SintaInstitution(
            sinta_id=str(data.get("id") or data.get("sinta_id", "")),
            kode_pt=data.get("kode_pt"),
            nama=data.get("nama") or data.get("name", "Unknown Institution"),
            singkatan=data.get("singkatan"),
            peringkat_nasional=data.get("peringkat_nasional"),
            peringkat_3th=data.get("peringkat_3th"),
            score_overall=float(data.get("score_overall", 0.0)),
            score_3th=float(data.get("score_3th", 0.0)),
            jumlah_author=int(data.get("jumlah_author", 0)),
            jumlah_departemen=int(data.get("jumlah_departemen", 0)),
        )
