"""Layanan komunikasi data PDDikti Kemendikbudristek dengan integrasi caching lokal."""

from typing import Any, Dict, List, Optional
import httpx

from pddikti_sdk.cache.sqlite_cache import SQLiteCache
from pddikti_sdk.exceptions import APIConnectionError, ResourceNotFoundError
from pddikti_sdk.models.common import EntityType, SearchHitItem, SearchResult
from pddikti_sdk.models.perguruan_tinggi import BentukPendidikan, PerguruanTinggi, ProgramStudi, StatusPT
from pddikti_sdk.models.sdm import Dosen, Mahasiswa


class PDDiktiService:
    """Implementasi sinkron untuk mengakses endpoint PDDikti dengan akselerasi cache."""

    def __init__(self, client: httpx.Client, cache: Optional[SQLiteCache] = None) -> None:
        self._client = client
        self._cache = cache

    def _parse_search_data(self, keyword: str, data: Dict[str, Any]) -> SearchResult:
        result = SearchResult(keyword=keyword)
        for item in data.get("pt", []):
            result.perguruan_tinggi.append(
                SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.PT, raw_data=item)
            )
        for item in data.get("prodi", []):
            result.program_studi.append(
                SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.PRODI, raw_data=item)
            )
        for item in data.get("dosen", []):
            result.dosen.append(
                SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.DOSEN, raw_data=item)
            )
        for item in data.get("mahasiswa", []):
            result.mahasiswa.append(
                SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.MAHASISWA, raw_data=item)
            )
        return result

    def search_all(self, keyword: str, use_cache: bool = True) -> SearchResult:
        """Pencarian agregat multi-entitas (PT, Prodi, Dosen, Mahasiswa)."""
        clean_keyword = keyword.strip()
        cache_key = f"search:{clean_keyword.lower()}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return self._parse_search_data(clean_keyword, cached_data)

        url = f"/hit/{clean_keyword}"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise APIConnectionError(f"HTTP error saat pencarian: {e}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise APIConnectionError(f"Gagal terhubung ke PDDikti: {e}")

        if use_cache and self._cache is not None and isinstance(data, dict):
            # Simpan hasil pencarian selama 1 jam (3600 detik)
            self._cache.set(cache_key, data, ttl=3600, tag="search")

        return self._parse_search_data(clean_keyword, data)

    def _parse_pt_data(self, id_pt: str, data: Dict[str, Any]) -> PerguruanTinggi:
        pt_info = data.get("detail", data) if isinstance(data, dict) else {}
        nama = pt_info.get("nama_pt") or pt_info.get("nm_lemb", "Unknown PT")
        kode = pt_info.get("kode_pt") or pt_info.get("npsn", id_pt)

        return PerguruanTinggi(
            id=id_pt,
            kode=kode,
            nama_pt=nama,
            singkatan=pt_info.get("singkatan"),
            provinsi=pt_info.get("propinsi") or pt_info.get("provinsi"),
            kab_kota=pt_info.get("kab_kota"),
            status_kepemilikan=pt_info.get("status_milik", "Swasta"),
            total_mahasiswa_aktif=int(pt_info.get("jml_mhs", 0) or 0),
            total_dosen_tetap=int(pt_info.get("jml_dosen", 0) or 0),
        )

    def get_detail_pt(self, id_pt: str, use_cache: bool = True) -> PerguruanTinggi:
        """Mengambil detail profil lengkap perguruan tinggi berdasarkan ID."""
        clean_id = id_pt.strip()
        cache_key = f"pt:{clean_id}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return self._parse_pt_data(clean_id, cached_data)

        url = f"/v2/detail_pt/{clean_id}"
        try:
            resp = self._client.get(url)
            if resp.status_code == 404:
                raise ResourceNotFoundError(f"Perguruan tinggi dengan ID {clean_id} tidak ditemukan.")
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise APIConnectionError(f"HTTP error: {e}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise APIConnectionError(f"Koneksi gagal: {e}")

        if use_cache and self._cache is not None and isinstance(data, dict):
            # Simpan profil PT selama 24 jam (86400 detik)
            self._cache.set(cache_key, data, ttl=86400, tag="pt")

        return self._parse_pt_data(clean_id, data)

    def _parse_prodi_list(self, data: Any) -> List[ProgramStudi]:
        prodi_list: List[ProgramStudi] = []
        raw_items = data if isinstance(data, list) else data.get("prodi", [])
        for item in raw_items:
            p = ProgramStudi(
                id_prodi=item.get("id_sms") or item.get("id"),
                kode=item.get("kode_prodi") or item.get("kode", "-"),
                nama_prodi=item.get("nm_lemb") or item.get("nama_prodi", "Unknown Prodi"),
                status=item.get("stat_prodi", "Aktif"),
                dosen_count=int(item.get("jml_dosen", 0) or 0),
                mahasiswa_count=int(item.get("jml_mhs", 0) or 0),
            )
            prodi_list.append(p)
        return prodi_list

    def get_prodi_list(self, id_pt: str, use_cache: bool = True) -> List[ProgramStudi]:
        """Mengambil daftar seluruh program studi di sebuah perguruan tinggi."""
        clean_id = id_pt.strip()
        cache_key = f"prodi:{clean_id}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return self._parse_prodi_list(cached_data)

        url = f"/v2/detail_pt_prodi/{clean_id}"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        if use_cache and self._cache is not None:
            # Simpan daftar prodi selama 24 jam
            self._cache.set(cache_key, data, ttl=86400, tag="prodi")

        return self._parse_prodi_list(data)


class AsyncPDDiktiService:
    """Implementasi asinkron untuk mengakses endpoint PDDikti."""

    def __init__(self, client: httpx.AsyncClient, cache: Optional[SQLiteCache] = None) -> None:
        self._client = client
        self._cache = cache

    async def search_all(self, keyword: str, use_cache: bool = True) -> SearchResult:
        clean_keyword = keyword.strip()
        cache_key = f"search:{clean_keyword.lower()}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                res = SearchResult(keyword=clean_keyword)
                for item in cached_data.get("pt", []):
                    res.perguruan_tinggi.append(SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.PT, raw_data=item))
                for item in cached_data.get("prodi", []):
                    res.program_studi.append(SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.PRODI, raw_data=item))
                for item in cached_data.get("dosen", []):
                    res.dosen.append(SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.DOSEN, raw_data=item))
                for item in cached_data.get("mahasiswa", []):
                    res.mahasiswa.append(SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.MAHASISWA, raw_data=item))
                return res

        url = f"/hit/{clean_keyword}"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise APIConnectionError(f"HTTP error saat pencarian: {e}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise APIConnectionError(f"Gagal terhubung ke PDDikti: {e}")

        if use_cache and self._cache is not None and isinstance(data, dict):
            self._cache.set(cache_key, data, ttl=3600, tag="search")

        res = SearchResult(keyword=clean_keyword)
        for item in data.get("pt", []):
            res.perguruan_tinggi.append(SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.PT, raw_data=item))
        for item in data.get("prodi", []):
            res.program_studi.append(SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.PRODI, raw_data=item))
        for item in data.get("dosen", []):
            res.dosen.append(SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.DOSEN, raw_data=item))
        for item in data.get("mahasiswa", []):
            res.mahasiswa.append(SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.MAHASISWA, raw_data=item))
        return res
