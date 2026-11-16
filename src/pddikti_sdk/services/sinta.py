"""Layanan pengaksesan dan integrasi data SINTA (Science and Technology Index)."""

import ipaddress
import math
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

from pddikti_sdk.exceptions import APIConnectionError, ResourceNotFoundError, ValidationError
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


def _validate_http_url(
    url: str,
    field_name: str = "base_url",
    allow_insecure_http: bool = False,
) -> str:
    """Memvalidasi URL HTTP/HTTPS terhadap skema tidak aman, kredensial tertanam, dan SSRF."""
    if not isinstance(url, str) or not url.strip():
        raise ValidationError(f"Parameter '{field_name}' tidak boleh kosong.")
    clean_url = url.strip().rstrip("/")
    parsed = urlparse(clean_url)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https") or not parsed.netloc:
        raise ValidationError(
            f"Parameter '{field_name}' harus berupa URL HTTP/HTTPS yang valid: {url!r}"
        )
    if parsed.username is not None or parsed.password is not None:
        raise ValidationError(
            f"Parameter '{field_name}' tidak boleh menyertakan kredensial pada URL."
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValidationError(f"Parameter '{field_name}' tidak memiliki hostname yang valid.")

    try:
        ip_obj = ipaddress.ip_address(hostname)
        if ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified:
            raise ValidationError(
                f"Parameter '{field_name}' mengarah ke alamat IP terlarang (SSRF/metadata): {hostname!r}"
            )
        is_loopback = ip_obj.is_loopback
    except ValueError:
        is_loopback = hostname in ("localhost", "localhost.localdomain") or hostname.endswith(".localhost")

    if scheme == "http" and not is_loopback and not allow_insecure_http:
        raise ValidationError(
            f"Parameter '{field_name}' menggunakan HTTP tidak terenkripsi untuk host remote; "
            "gunakan HTTPS atau set allow_insecure_http=True."
        )

    return clean_url


def _safe_int(val: Any, default: int = 0, min_value: Optional[int] = None) -> int:
    """Konversi nilai ke int secara aman terhadap NaN, Infinity, None, dan tipe tidak valid."""
    if val is None or isinstance(val, bool):
        return default
    try:
        num = float(val)
        if not math.isfinite(num):
            return default
        result = int(num)
    except (ValueError, TypeError, OverflowError):
        return default
    if min_value is not None and result < min_value:
        return min_value
    return result


def _safe_float(val: Any, default: float = 0.0, min_value: Optional[float] = None) -> float:
    """Konversi nilai ke float secara aman terhadap NaN, Infinity, None, dan tipe tidak valid."""
    if val is None or isinstance(val, bool):
        return default
    try:
        result = float(val)
        if not math.isfinite(result):
            return default
    except (ValueError, TypeError, OverflowError):
        return default
    if min_value is not None and result < min_value:
        return min_value
    return result


class SintaService:
    """Implementasi sinkron untuk integrasi data SINTA."""

    DEFAULT_SINTA_URL = "https://sinta.kemdikbud.go.id"

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        base_url: Optional[str] = None,
        allow_insecure_http: bool = False,
    ) -> None:
        raw_url = self.DEFAULT_SINTA_URL if base_url is None else base_url
        self.base_url = _validate_http_url(
            raw_url,
            "sinta_base_url",
            allow_insecure_http=allow_insecure_http,
        )
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            headers={
                "User-Agent": "pddikti-sdk/0.2.0 (Python Academic Client)",
                "Accept": "application/json, text/html",
            },
            timeout=30.0,
            follow_redirects=False,
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
        return _safe_int(val, default=default, min_value=0)

    @staticmethod
    def _safe_float(val: Any, default: float = 0.0) -> float:
        return _safe_float(val, default=default, min_value=0.0)

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
