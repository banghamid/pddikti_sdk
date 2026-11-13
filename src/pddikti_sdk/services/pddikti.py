"""Layanan komunikasi data PDDikti Kemendikbudristek dengan integrasi caching lokal."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import httpx

from pddikti_sdk.cache.sqlite_cache import SQLiteCache
from pddikti_sdk.exceptions import (
    APIConnectionError,
    RateLimitError,
    ResourceNotFoundError,
    ValidationError,
)
from pddikti_sdk.models.common import EntityType, SearchHitItem, SearchResult
from pddikti_sdk.models.perguruan_tinggi import BentukPendidikan, PerguruanTinggi, ProgramStudi, StatusPT
from pddikti_sdk.models.sdm import Dosen, Mahasiswa

# Pola aman untuk ID entitas PDDikti (base64url / hash / kode numerik, tanpa path traversal)
_SAFE_ENTITY_ID_RE = re.compile(r"^[A-Za-z0-9_\-=]{1,256}$")


def _validate_entity_id(raw_id: str, field_name: str = "id_pt") -> str:
    """Memvalidasi ID entitas agar bebas dari karakter path traversal atau URL injection."""
    clean_id = (raw_id or "").strip()
    if not clean_id or ".." in clean_id or not _SAFE_ENTITY_ID_RE.match(clean_id):
        raise ValidationError(
            f"Parameter '{field_name}' tidak valid atau mengandung karakter terlarang: {raw_id!r}"
        )
    return clean_id


def _safe_int(val: Any, default: int = 0) -> int:
    """Konversi nilai ke int secara aman tanpa melempar ValueError/TypeError."""
    if val is None or isinstance(val, bool):
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _parse_search_payload(keyword: str, data: Any) -> SearchResult:
    """Mengurai payload respons pencarian menjadi objek SearchResult."""
    result = SearchResult(keyword=keyword)
    if not isinstance(data, dict):
        return result

    for item in data.get("pt") or []:
        if isinstance(item, dict):
            result.perguruan_tinggi.append(
                SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.PT, raw_data=item)
            )
    for item in data.get("prodi") or []:
        if isinstance(item, dict):
            result.program_studi.append(
                SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.PRODI, raw_data=item)
            )
    for item in data.get("dosen") or []:
        if isinstance(item, dict):
            result.dosen.append(
                SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.DOSEN, raw_data=item)
            )
    for item in data.get("mahasiswa") or []:
        if isinstance(item, dict):
            result.mahasiswa.append(
                SearchHitItem(id=item.get("id"), text=item.get("text", ""), entity_type=EntityType.MAHASISWA, raw_data=item)
            )
    return result


def _parse_pt_payload(id_pt: str, data: Any) -> PerguruanTinggi:
    """Mengurai payload detail perguruan tinggi menjadi objek PerguruanTinggi."""
    pt_info = data.get("detail", data) if isinstance(data, dict) else {}
    if not isinstance(pt_info, dict):
        pt_info = {}
    nama = pt_info.get("nama_pt") or pt_info.get("nm_lemb", "Unknown PT")
    kode = pt_info.get("kode_pt") or pt_info.get("npsn", id_pt)

    return PerguruanTinggi(
        id=id_pt,
        kode=str(kode),
        nama_pt=str(nama),
        singkatan=pt_info.get("singkatan"),
        provinsi=pt_info.get("propinsi") or pt_info.get("provinsi"),
        kab_kota=pt_info.get("kab_kota"),
        status_kepemilikan=pt_info.get("status_milik") or "Swasta",
        total_mahasiswa_aktif=_safe_int(pt_info.get("jml_mhs"), 0),
        total_dosen_tetap=_safe_int(pt_info.get("jml_dosen"), 0),
    )


def _parse_prodi_payload(data: Any) -> List[ProgramStudi]:
    """Mengurai payload daftar program studi menjadi list ProgramStudi."""
    prodi_list: List[ProgramStudi] = []
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        raw_items = data.get("prodi") or []
    else:
        raw_items = []

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        p = ProgramStudi(
            id_prodi=item.get("id_sms") or item.get("id"),
            kode=str(item.get("kode_prodi") or item.get("kode") or "-"),
            nama_prodi=str(item.get("nm_lemb") or item.get("nama_prodi") or "Unknown Prodi"),
            status=str(item.get("stat_prodi") or "Aktif"),
            dosen_count=_safe_int(item.get("jml_dosen"), 0),
            mahasiswa_count=_safe_int(item.get("jml_mhs"), 0),
        )
        prodi_list.append(p)
    return prodi_list


def _handle_http_response(resp: httpx.Response, not_found_msg: Optional[str] = None) -> Any:
    """Memeriksa kode status HTTP (404, 429, 4xx/5xx) dan mengurai JSON secara aman."""
    if resp.status_code == 404 and not_found_msg:
        raise ResourceNotFoundError(not_found_msg, status_code=404, response_body=resp.text)
    if resp.status_code == 429:
        raise RateLimitError(
            "Kuota permintaan ke PDDikti melebihi batas (HTTP 429 Too Many Requests).",
            status_code=429,
            response_body=resp.text,
        )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise APIConnectionError(
            f"HTTP error dari PDDikti: {e}",
            status_code=e.response.status_code,
            response_body=e.response.text,
        ) from e

    try:
        return resp.json()
    except ValueError as e:
        raise APIConnectionError(
            f"Respons PDDikti bukan format JSON yang valid: {e}",
            status_code=resp.status_code,
            response_body=resp.text,
        ) from e


class PDDiktiService:
    """Implementasi sinkron untuk mengakses endpoint PDDikti dengan akselerasi cache."""

    def __init__(self, client: httpx.Client, cache: Optional[SQLiteCache] = None) -> None:
        self._client = client
        self._cache = cache

    def _parse_search_data(self, keyword: str, data: Dict[str, Any]) -> SearchResult:
        return _parse_search_payload(keyword, data)

    def search_all(self, keyword: str, use_cache: bool = True) -> SearchResult:
        """Pencarian agregat multi-entitas (PT, Prodi, Dosen, Mahasiswa)."""
        clean_keyword = (keyword or "").strip()
        if not clean_keyword:
            raise ValidationError("Kata kunci pencarian tidak boleh kosong.")

        cache_key = f"search:{clean_keyword.lower()}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return _parse_search_payload(clean_keyword, cached_data)

        encoded_keyword = quote(clean_keyword, safe="")
        url = f"/hit/{encoded_keyword}"
        try:
            resp = self._client.get(url)
            data = _handle_http_response(resp)
        except httpx.RequestError as e:
            raise APIConnectionError(f"Gagal terhubung ke PDDikti: {e}") from e

        if use_cache and self._cache is not None and isinstance(data, dict):
            # Simpan hasil pencarian selama 1 jam (3600 detik)
            self._cache.set(cache_key, data, ttl=3600, tag="search")

        return _parse_search_payload(clean_keyword, data)

    def _parse_pt_data(self, id_pt: str, data: Dict[str, Any]) -> PerguruanTinggi:
        return _parse_pt_payload(id_pt, data)

    def get_detail_pt(self, id_pt: str, use_cache: bool = True) -> PerguruanTinggi:
        """Mengambil detail profil lengkap perguruan tinggi berdasarkan ID."""
        clean_id = _validate_entity_id(id_pt, "id_pt")
        cache_key = f"pt:{clean_id}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return _parse_pt_payload(clean_id, cached_data)

        encoded_id = quote(clean_id, safe="")
        url = f"/v2/detail_pt/{encoded_id}"
        try:
            resp = self._client.get(url)
            data = _handle_http_response(
                resp,
                not_found_msg=f"Perguruan tinggi dengan ID {clean_id} tidak ditemukan.",
            )
        except httpx.RequestError as e:
            raise APIConnectionError(f"Koneksi gagal: {e}") from e

        if use_cache and self._cache is not None and isinstance(data, dict):
            # Simpan profil PT selama 24 jam (86400 detik)
            self._cache.set(cache_key, data, ttl=86400, tag="pt")

        return _parse_pt_payload(clean_id, data)

    def _parse_prodi_list(self, data: Any) -> List[ProgramStudi]:
        return _parse_prodi_payload(data)

    def get_prodi_list(self, id_pt: str, use_cache: bool = True) -> List[ProgramStudi]:
        """Mengambil daftar seluruh program studi di sebuah perguruan tinggi."""
        clean_id = _validate_entity_id(id_pt, "id_pt")
        cache_key = f"prodi:{clean_id}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return _parse_prodi_payload(cached_data)

        encoded_id = quote(clean_id, safe="")
        url = f"/v2/detail_pt_prodi/{encoded_id}"
        try:
            resp = self._client.get(url)
            if resp.status_code == 404:
                return []
            data = _handle_http_response(resp)
        except (RateLimitError, APIConnectionError):
            raise
        except httpx.RequestError as e:
            raise APIConnectionError(f"Koneksi gagal saat mengambil daftar prodi: {e}") from e

        if use_cache and self._cache is not None and isinstance(data, (list, dict)):
            # Simpan daftar prodi selama 24 jam
            self._cache.set(cache_key, data, ttl=86400, tag="prodi")

        return _parse_prodi_payload(data)


class AsyncPDDiktiService:
    """Implementasi asinkron untuk mengakses endpoint PDDikti."""

    def __init__(self, client: httpx.AsyncClient, cache: Optional[SQLiteCache] = None) -> None:
        self._client = client
        self._cache = cache

    async def search_all(self, keyword: str, use_cache: bool = True) -> SearchResult:
        """Pencarian agregat multi-entitas asinkron."""
        clean_keyword = (keyword or "").strip()
        if not clean_keyword:
            raise ValidationError("Kata kunci pencarian tidak boleh kosong.")

        cache_key = f"search:{clean_keyword.lower()}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return _parse_search_payload(clean_keyword, cached_data)

        encoded_keyword = quote(clean_keyword, safe="")
        url = f"/hit/{encoded_keyword}"
        try:
            resp = await self._client.get(url)
            data = _handle_http_response(resp)
        except httpx.RequestError as e:
            raise APIConnectionError(f"Gagal terhubung ke PDDikti: {e}") from e

        if use_cache and self._cache is not None and isinstance(data, dict):
            self._cache.set(cache_key, data, ttl=3600, tag="search")

        return _parse_search_payload(clean_keyword, data)

    async def get_detail_pt(self, id_pt: str, use_cache: bool = True) -> PerguruanTinggi:
        """Mengambil detail profil lengkap perguruan tinggi secara asinkron."""
        clean_id = _validate_entity_id(id_pt, "id_pt")
        cache_key = f"pt:{clean_id}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return _parse_pt_payload(clean_id, cached_data)

        encoded_id = quote(clean_id, safe="")
        url = f"/v2/detail_pt/{encoded_id}"
        try:
            resp = await self._client.get(url)
            data = _handle_http_response(
                resp,
                not_found_msg=f"Perguruan tinggi dengan ID {clean_id} tidak ditemukan.",
            )
        except httpx.RequestError as e:
            raise APIConnectionError(f"Koneksi gagal: {e}") from e

        if use_cache and self._cache is not None and isinstance(data, dict):
            self._cache.set(cache_key, data, ttl=86400, tag="pt")

        return _parse_pt_payload(clean_id, data)

    async def get_prodi_list(self, id_pt: str, use_cache: bool = True) -> List[ProgramStudi]:
        """Mengambil daftar seluruh program studi di sebuah perguruan tinggi secara asinkron."""
        clean_id = _validate_entity_id(id_pt, "id_pt")
        cache_key = f"prodi:{clean_id}"

        if use_cache and self._cache is not None:
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                return _parse_prodi_payload(cached_data)

        encoded_id = quote(clean_id, safe="")
        url = f"/v2/detail_pt_prodi/{encoded_id}"
        try:
            resp = await self._client.get(url)
            if resp.status_code == 404:
                return []
            data = _handle_http_response(resp)
        except (RateLimitError, APIConnectionError):
            raise
        except httpx.RequestError as e:
            raise APIConnectionError(f"Koneksi gagal saat mengambil daftar prodi: {e}") from e

        if use_cache and self._cache is not None and isinstance(data, (list, dict)):
            self._cache.set(cache_key, data, ttl=86400, tag="prodi")

        return _parse_prodi_payload(data)

