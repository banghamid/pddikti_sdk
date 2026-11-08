"""Client utama terpadu untuk pengaksesan data PDDikti, SINTA, dan akreditasi BAN-PT."""

from typing import Any, Dict, List, Optional
import httpx

from pddikti_sdk.analytics.aggregator import DataAggregator
from pddikti_sdk.analytics.ratio import LaporanRasioPT, LaporanRasioProdi, RatioAnalyzer
from pddikti_sdk.models.common import SearchResult
from pddikti_sdk.models.perguruan_tinggi import PerguruanTinggi, ProgramStudi
from pddikti_sdk.services.banpt import BanptService
from pddikti_sdk.services.pddikti import AsyncPDDiktiService, PDDiktiService
from pddikti_sdk.services.sinta import SintaService


class PDDiktiClient:
    """Client sinkron untuk mengakses ekosistem data PDDikti, SINTA, dan BAN-PT.

    Attributes:
        base_url: URL endpoint resmi API frontend PDDikti.
        timeout: Waktu tunggu permintaan HTTP (detik).
    """

    DEFAULT_BASE_URL = "https://api-frontend.kemdikbud.go.id"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        sinta_base_url: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

        default_headers = {
            "User-Agent": "pddikti-sdk/0.1.0 (Python Educational Research Client)",
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)

        self._http_client = httpx.Client(
            base_url=self.base_url,
            headers=default_headers,
            timeout=self.timeout,
        )

        # Inisialisasi submodule layanan
        self._pddikti_service = PDDiktiService(self._http_client)
        self.sinta = SintaService(base_url=sinta_base_url)
        self.banpt = BanptService()
        self.analytics = RatioAnalyzer()
        self.aggregator = DataAggregator()

    def close(self) -> None:
        """Menutup koneksi client HTTP."""
        self._http_client.close()

    def __enter__(self) -> "PDDiktiClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def search(self, keyword: str) -> SearchResult:
        """Melakukan pencarian multi-entitas (PT, Prodi, Dosen, Mahasiswa).

        Args:
            keyword: Nama atau kata kunci pencarian.

        Returns:
            SearchResult berisi daftar item yang cocok dari masing-masing kategori.
        """
        return self._pddikti_service.search_all(keyword)

    def get_perguruan_tinggi(self, id_pt: str, include_prodi: bool = True) -> PerguruanTinggi:
        """Mengambil profil lengkap Perguruan Tinggi beserta daftar prodinya.

        Args:
            id_pt: Hash ID atau kode unik perguruan tinggi di PDDikti.
            include_prodi: Apakah menyertakan daftar program studi di dalamnya.

        Returns:
            Objek PerguruanTinggi yang telah terisi data statistik dan prodinya.
        """
        pt = self._pddikti_service.get_detail_pt(id_pt)
        if include_prodi:
            prodi_list = self._pddikti_service.get_prodi_list(id_pt)
            pt.daftar_prodi = prodi_list
            pt.total_prodi = len(prodi_list)
        return pt

    def get_prodi_list(self, id_pt: str) -> List[ProgramStudi]:
        """Mengambil daftar seluruh program studi di sebuah perguruan tinggi."""
        return self._pddikti_service.get_prodi_list(id_pt)

    def analyze_ratio(self, pt: PerguruanTinggi) -> LaporanRasioPT:
        """Menganalisis rasio dosen-mahasiswa seluruh program studi di perguruan tinggi.

        Args:
            pt: Objek PerguruanTinggi yang memiliki daftar_prodi.

        Returns:
            LaporanRasioPT lengkap dengan status kepatuhan BAN-PT dan deteksi anomali.
        """
        return self.analytics.evaluasi_pt(pt)


class AsyncPDDiktiClient:
    """Client asinkron untuk performa tinggi pada analisis data massal."""

    DEFAULT_BASE_URL = "https://api-frontend.kemdikbud.go.id"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

        default_headers = {
            "User-Agent": "pddikti-sdk/0.1.0 (Async Python Educational Research Client)",
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)

        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=default_headers,
            timeout=self.timeout,
        )
        self._pddikti_service = AsyncPDDiktiService(self._http_client)

    async def close(self) -> None:
        await self._http_client.aclose()

    async def __aenter__(self) -> "AsyncPDDiktiClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def search(self, keyword: str) -> SearchResult:
        """Pencarian multi-entitas asinkron."""
        return await self._pddikti_service.search_all(keyword)
