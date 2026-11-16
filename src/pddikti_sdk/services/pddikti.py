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
from pddikti_sdk.models.perguruan_tinggi import (
    BentukPendidikan,
    BidangStudi,
    JenjangStudi,
    PerguruanTinggi,
    ProgramStudi,
    StatusPT,
)
from pddikti_sdk.models.sdm import Dosen, Mahasiswa
from pddikti_sdk.services.banpt import BanptService
from pddikti_sdk.services.sinta import _safe_int

# Pola aman untuk ID entitas PDDikti (base64url / hash / kode numerik, tanpa path traversal)
_SAFE_ENTITY_ID_RE = re.compile(r"^[A-Za-z0-9_\-=]{1,256}$")
MAX_KEYWORD_LENGTH = 256
MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_ERROR_BODY_CHARS = 2048

_EKSAKTA_KEYWORDS = (
    "teknik",
    "informatika",
    "komputer",
    "sistem informasi",
    "kedokteran",
    "kesehatan",
    "keperawatan",
    "kebidanan",
    "farmasi",
    "matematika",
    "fisika",
    "kimia",
    "biologi",
    "statistika",
    "arsitektur",
    "pertanian",
    "peternakan",
    "kehutanan",
    "kelautan",
    "perikanan",
    "gizi",
    "sains",
)


def _validate_entity_id(raw_id: str, field_name: str = "id_pt") -> str:
    """Memvalidasi ID entitas agar bebas dari karakter path traversal atau URL injection."""
    clean_id = (raw_id or "").strip()
    if not clean_id or ".." in clean_id or not _SAFE_ENTITY_ID_RE.match(clean_id):
        raise ValidationError(
            f"Parameter '{field_name}' tidak valid atau mengandung karakter terlarang: {raw_id!r}"
        )
    return clean_id


def _parse_jenjang(raw: Any) -> JenjangStudi:
    """Menormalkan label jenjang pendidikan PDDikti ke enum JenjangStudi."""
    if isinstance(raw, JenjangStudi):
        return raw
    if not raw or not str(raw).strip():
        return JenjangStudi.S1

    clean = str(raw).strip().upper()
    if "D4" in clean or "D-IV" in clean or "DIV" in clean or "SARJANA TERAPAN" in clean:
        return JenjangStudi.D4
    if "S2 TERAPAN" in clean or "MAGISTER TERAPAN" in clean:
        return JenjangStudi.S2_TERAPAN
    if "S3 TERAPAN" in clean or "DOKTOR TERAPAN" in clean:
        return JenjangStudi.S3_TERAPAN
    if "SPESIALIS-2" in clean or "SPESIALIS 2" in clean or "SP-2" in clean or "SP2" in clean or "SUBSPESIALIS" in clean:
        return JenjangStudi.SPESIALIS_2
    if "SPESIALIS" in clean or "SP-1" in clean or "SP1" in clean:
        return JenjangStudi.SPESIALIS_1
    if "PROFESI" in clean:
        return JenjangStudi.PROFESI
    if "D1" in clean or "D-I" in clean or "DIPLOMA I" in clean:
        return JenjangStudi.D1
    if "D2" in clean or "D-II" in clean or "DIPLOMA II" in clean:
        return JenjangStudi.D2
    if "D3" in clean or "D-III" in clean or "DIPLOMA III" in clean:
        return JenjangStudi.D3
    if "S2" in clean or "MAGISTER" in clean or "PASCASARJANA" in clean:
        return JenjangStudi.S2
    if "S3" in clean or "DOKTOR" in clean:
        return JenjangStudi.S3
    if "S1" in clean or "SARJANA" in clean:
        return JenjangStudi.S1
    return JenjangStudi.LAINNYA


def _infer_bidang_studi(nama_prodi: str, raw_bidang: Any = None) -> BidangStudi:
    """Menentukan rumpun BidangStudi dari payload eksplisit atau kata kunci nama prodi."""
    if isinstance(raw_bidang, BidangStudi):
        return raw_bidang
    if raw_bidang and str(raw_bidang).strip():
        clean = str(raw_bidang).strip().upper()
        if "CAMPURAN" in clean:
            return BidangStudi.CAMPURAN
        if "NON" in clean or "SOSIAL" in clean or "HUMANIORA" in clean or "SENI" in clean:
            return BidangStudi.NON_EKSAKTA
        if "EKSAKTA" in clean or "TEKNIK" in clean or "KESEHATAN" in clean:
            return BidangStudi.EKSAKTA

    nama_lower = (nama_prodi or "").lower()
    if any(kw in nama_lower for kw in _EKSAKTA_KEYWORDS):
        return BidangStudi.EKSAKTA
    return BidangStudi.NON_EKSAKTA


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
    has_akreditasi = any(pt_info.get(k) for k in ("akreditasi", "peringkat", "status_akreditasi"))
    akreditasi = BanptService.parse_akreditasi_info(pt_info) if has_akreditasi else None

    return PerguruanTinggi(
        id=id_pt,
        kode=str(kode),
        nama_pt=str(nama),
        singkatan=pt_info.get("singkatan"),
        wilayah=pt_info.get("wilayah") or pt_info.get("lldikti"),
        provinsi=pt_info.get("propinsi") or pt_info.get("provinsi"),
        kab_kota=pt_info.get("kab_kota"),
        status_kepemilikan=pt_info.get("status_milik") or "Swasta",
        akreditasi=akreditasi,
        total_mahasiswa_aktif=_safe_int(pt_info.get("jml_mhs"), 0, min_value=0),
        total_dosen_tetap=_safe_int(pt_info.get("jml_dosen"), 0, min_value=0),
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
        nama_prodi = str(item.get("nm_lemb") or item.get("nama_prodi") or "Unknown Prodi")
        jenjang = _parse_jenjang(item.get("jenjang") or item.get("nm_jenj_didik") or item.get("namajenjang"))
        bidang = _infer_bidang_studi(nama_prodi, item.get("bidang"))
        has_akreditasi = any(item.get(k) for k in ("akreditasi", "peringkat", "status_akreditasi"))
        akreditasi = BanptService.parse_akreditasi_info(item) if has_akreditasi else None

        p = ProgramStudi(
            id_prodi=item.get("id_sms") or item.get("id"),
            kode=str(item.get("kode_prodi") or item.get("kode") or "-"),
            nama_prodi=nama_prodi,
            jenjang=jenjang,
            bidang=bidang,
            akreditasi=akreditasi,
            status=str(item.get("stat_prodi") or "Aktif"),
            dosen_count=_safe_int(item.get("jml_dosen"), 0, min_value=0),
            mahasiswa_count=_safe_int(item.get("jml_mhs"), 0, min_value=0),
        )
        prodi_list.append(p)
    return prodi_list


def _validate_keyword(keyword: str) -> str:
    """Memvalidasi kata kunci pencarian agar tidak kosong dan tidak melebihi batas panjang."""
    clean_keyword = (keyword or "").strip()
    if not clean_keyword:
        raise ValidationError("Kata kunci pencarian tidak boleh kosong.")
    if len(clean_keyword) > MAX_KEYWORD_LENGTH:
        raise ValidationError(
            f"Kata kunci pencarian melebihi batas maksimal {MAX_KEYWORD_LENGTH} karakter."
        )
    return clean_keyword


def _handle_http_response(resp: httpx.Response, not_found_msg: Optional[str] = None) -> Any:
    """Memeriksa ukuran respons, kode status HTTP (404, 429, 4xx/5xx), dan mengurai JSON secara aman."""
    if len(resp.content) > MAX_RESPONSE_BYTES:
        raise APIConnectionError(
            f"Ukuran respons PDDikti ({len(resp.content)} bytes) melebihi batas aman {MAX_RESPONSE_BYTES} bytes.",
            status_code=resp.status_code,
        )

    safe_body = resp.text[:MAX_ERROR_BODY_CHARS]
    if resp.status_code == 404 and not_found_msg:
        raise ResourceNotFoundError(not_found_msg, status_code=404, response_body=safe_body)
    if resp.status_code == 429:
        raise RateLimitError(
            "Kuota permintaan ke PDDikti melebihi batas (HTTP 429 Too Many Requests).",
            status_code=429,
            response_body=safe_body,
        )
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise APIConnectionError(
            f"HTTP error dari PDDikti: {e}",
            status_code=e.response.status_code,
            response_body=safe_body,
        ) from e

    try:
        return resp.json()
    except ValueError as e:
        raise APIConnectionError(
            f"Respons PDDikti bukan format JSON yang valid: {e}",
            status_code=resp.status_code,
            response_body=safe_body,
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
        clean_keyword = _validate_keyword(keyword)

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
        clean_keyword = _validate_keyword(keyword)

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

