"""Client utama terpadu untuk pengaksesan data PDDikti, SINTA, akreditasi BAN-PT, dan cache SQLite."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import httpx

from pddikti_sdk.analytics.aggregator import DataAggregator
from pddikti_sdk.analytics.excel_exporter import export_laporan_rasio_excel
from pddikti_sdk.analytics.ratio import LaporanRasioPT, LaporanRasioProdi, RatioAnalyzer
from pddikti_sdk.cache.sqlite_cache import SQLiteCache
from pddikti_sdk.models.common import SearchResult
from pddikti_sdk.models.perguruan_tinggi import PerguruanTinggi, ProgramStudi
from pddikti_sdk.services.banpt import BanptService
from pddikti_sdk.services.pddikti import AsyncPDDiktiService, PDDiktiService
from pddikti_sdk.services.sinta import SintaService


class PDDiktiClient:
    """Client sinkron untuk mengakses ekosistem data PDDikti, SINTA, dan BAN-PT dengan cache lokal.

    Attributes:
        base_url: URL endpoint resmi API frontend PDDikti.
        timeout: Waktu tunggu permintaan HTTP (detik).
        cache: Instance SQLiteCache atau None jika cache dinonaktifkan.
    """

    DEFAULT_BASE_URL = "https://api-frontend.kemdikbud.go.id"
    DEFAULT_CACHE_FILE = "~/.pddikti/cache.db"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        sinta_base_url: Optional[str] = None,
        cache: Union[SQLiteCache, str, Path, bool, None] = True,
        default_ttl: int = 86400,
    ) -> None:
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

        # Inisialisasi Cache SQLite
        self._owns_cache = False
        if isinstance(cache, SQLiteCache):
            self.cache: Optional[SQLiteCache] = cache
        elif cache is True:
            self.cache = SQLiteCache(db_path=self.DEFAULT_CACHE_FILE, default_ttl=default_ttl)
            self._owns_cache = True
        elif isinstance(cache, (str, Path)):
            self.cache = SQLiteCache(db_path=cache, default_ttl=default_ttl)
            self._owns_cache = True
        else:
            self.cache = None

        default_headers = {
            "User-Agent": "pddikti-sdk/0.2.0 (Python Educational Research Client)",
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
        self._pddikti_service = PDDiktiService(self._http_client, cache=self.cache)
        self.sinta = SintaService(base_url=sinta_base_url)
        self.banpt = BanptService()
        self.analytics = RatioAnalyzer()
        self.aggregator = DataAggregator()

    def close(self) -> None:
        """Menutup koneksi client HTTP dan sub-layanan."""
        self._http_client.close()
        self.sinta.close()
        if self._owns_cache and self.cache is not None:
            self.cache.close()

    def __enter__(self) -> "PDDiktiClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def search(self, keyword: str, use_cache: bool = True) -> SearchResult:
        """Melakukan pencarian multi-entitas (PT, Prodi, Dosen, Mahasiswa).

        Args:
            keyword: Nama atau kata kunci pencarian.
            use_cache: Apakah menggunakan cache SQLite lokal.

        Returns:
            SearchResult berisi daftar item yang cocok dari masing-masing kategori.
        """
        return self._pddikti_service.search_all(keyword, use_cache=use_cache)

    def get_perguruan_tinggi(
        self,
        id_pt: str,
        include_prodi: bool = True,
        use_cache: bool = True,
    ) -> PerguruanTinggi:
        """Mengambil profil lengkap Perguruan Tinggi beserta daftar prodinya.

        Args:
            id_pt: Hash ID atau kode unik perguruan tinggi di PDDikti.
            include_prodi: Apakah menyertakan daftar program studi di dalamnya.
            use_cache: Apakah menggunakan cache SQLite lokal.

        Returns:
            Objek PerguruanTinggi yang telah terisi data statistik dan prodinya.
        """
        pt = self._pddikti_service.get_detail_pt(id_pt, use_cache=use_cache)
        if include_prodi:
            prodi_list = self._pddikti_service.get_prodi_list(id_pt, use_cache=use_cache)
            pt.daftar_prodi = prodi_list
            pt.total_prodi = len(prodi_list)
        return pt

    def get_prodi_list(self, id_pt: str, use_cache: bool = True) -> List[ProgramStudi]:
        """Mengambil daftar seluruh program studi di sebuah perguruan tinggi."""
        return self._pddikti_service.get_prodi_list(id_pt, use_cache=use_cache)

    def analyze_ratio(self, pt: PerguruanTinggi) -> LaporanRasioPT:
        """Menganalisis rasio dosen-mahasiswa seluruh program studi di perguruan tinggi.

        Args:
            pt: Objek PerguruanTinggi yang memiliki daftar_prodi.

        Returns:
            LaporanRasioPT lengkap dengan status kepatuhan BAN-PT dan deteksi anomali.
        """
        return self.analytics.evaluasi_pt(pt)

    def export_ratio_excel(
        self,
        pt: PerguruanTinggi,
        output_path: Union[str, Path] = "laporan_rasio_pddikti.xlsx",
    ) -> Path:
        """Menganalisis rasio dan mengekspor hasilnya langsung ke berkas Excel (.xlsx).

        Args:
            pt: Objek PerguruanTinggi.
            output_path: Nama atau path berkas tujuan Excel.

        Returns:
            Path absolut berkas Excel yang berhasil disimpan.
        """
        laporan = self.analyze_ratio(pt)
        return export_laporan_rasio_excel(laporan, output_path)

    def clear_cache(self, expired_only: bool = False, tag: Optional[str] = None) -> int:
        """Membersihkan entri cache lokal SQLite."""
        if self.cache:
            return self.cache.clear(expired_only=expired_only, tag=tag)
        return 0

    def cache_stats(self) -> Dict[str, Any]:
        """Mendapatkan statistik hit/miss dan ukuran berkas cache SQLite."""
        if self.cache:
            return self.cache.stats()
        return {"enabled": False}


class AsyncPDDiktiClient:
    """Client asinkron untuk performa tinggi pada analisis data massal."""

    DEFAULT_BASE_URL = "https://api-frontend.kemdikbud.go.id"
    DEFAULT_CACHE_FILE = "~/.pddikti/cache.db"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        cache: Union[SQLiteCache, str, Path, bool, None] = True,
        default_ttl: int = 86400,
    ) -> None:
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

        self._owns_cache = False
        if isinstance(cache, SQLiteCache):
            self.cache: Optional[SQLiteCache] = cache
        elif cache is True:
            self.cache = SQLiteCache(db_path=self.DEFAULT_CACHE_FILE, default_ttl=default_ttl)
            self._owns_cache = True
        elif isinstance(cache, (str, Path)):
            self.cache = SQLiteCache(db_path=cache, default_ttl=default_ttl)
            self._owns_cache = True
        else:
            self.cache = None

        default_headers = {
            "User-Agent": "pddikti-sdk/0.2.0 (Async Python Educational Research Client)",
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)

        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=default_headers,
            timeout=self.timeout,
        )
        self._pddikti_service = AsyncPDDiktiService(self._http_client, cache=self.cache)
        self.banpt = BanptService()
        self.analytics = RatioAnalyzer()
        self.aggregator = DataAggregator()

    async def close(self) -> None:
        await self._http_client.aclose()
        if self._owns_cache and self.cache is not None:
            self.cache.close()

    async def __aenter__(self) -> "AsyncPDDiktiClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def search(self, keyword: str, use_cache: bool = True) -> SearchResult:
        """Pencarian multi-entitas asinkron."""
        return await self._pddikti_service.search_all(keyword, use_cache=use_cache)

    async def get_perguruan_tinggi(
        self,
        id_pt: str,
        include_prodi: bool = True,
        use_cache: bool = True,
    ) -> PerguruanTinggi:
        """Mengambil profil lengkap Perguruan Tinggi beserta daftar prodinya secara asinkron."""
        pt = await self._pddikti_service.get_detail_pt(id_pt, use_cache=use_cache)
        if include_prodi:
            prodi_list = await self._pddikti_service.get_prodi_list(id_pt, use_cache=use_cache)
            pt.daftar_prodi = prodi_list
            pt.total_prodi = len(prodi_list)
        return pt

    async def get_prodi_list(self, id_pt: str, use_cache: bool = True) -> List[ProgramStudi]:
        """Mengambil daftar seluruh program studi di sebuah perguruan tinggi secara asinkron."""
        return await self._pddikti_service.get_prodi_list(id_pt, use_cache=use_cache)

    def analyze_ratio(self, pt: PerguruanTinggi) -> LaporanRasioPT:
        """Menganalisis rasio dosen-mahasiswa seluruh program studi di perguruan tinggi."""
        return self.analytics.evaluasi_pt(pt)

    def export_ratio_excel(
        self,
        pt: PerguruanTinggi,
        output_path: Union[str, Path] = "laporan_rasio_pddikti.xlsx",
    ) -> Path:
        """Menganalisis rasio dan mengekspor hasilnya langsung ke berkas Excel (.xlsx)."""
        laporan = self.analyze_ratio(pt)
        return export_laporan_rasio_excel(laporan, output_path)

    def clear_cache(self, expired_only: bool = False, tag: Optional[str] = None) -> int:
        """Membersihkan entri cache lokal SQLite."""
        if self.cache:
            return self.cache.clear(expired_only=expired_only, tag=tag)
        return 0

    def cache_stats(self) -> Dict[str, Any]:
        """Mendapatkan statistik hit/miss dan ukuran berkas cache SQLite."""
        if self.cache:
            return self.cache.stats()
        return {"enabled": False}
