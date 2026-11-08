"""Layanan komunikasi data PDDikti Kemendikbudristek."""

from typing import Any, Dict, List, Optional
import httpx

from pddikti_sdk.exceptions import APIConnectionError, ResourceNotFoundError
from pddikti_sdk.models.common import EntityType, SearchHitItem, SearchResult
from pddikti_sdk.models.perguruan_tinggi import BentukPendidikan, PerguruanTinggi, ProgramStudi, StatusPT
from pddikti_sdk.models.sdm import Dosen, Mahasiswa


class PDDiktiService:
    """Implementasi sinkron untuk mengakses endpoint PDDikti."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def search_all(self, keyword: str) -> SearchResult:
        """Pencarian agregat multi-entitas (PT, Prodi, Dosen, Mahasiswa)."""
        clean_keyword = keyword.strip()
        url = f"/hit/{clean_keyword}"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise APIConnectionError(f"HTTP error saat pencarian: {e}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise APIConnectionError(f"Gagal terhubung ke PDDikti: {e}")

        result = SearchResult(keyword=clean_keyword)
        
        # PDDikti API mengembalikan format dictionary dengan key: 'pt', 'prodi', 'dosen', 'mahasiswa'
        for item in data.get("pt", []):
            result.perguruan_tinggi.append(
                SearchHitItem(
                    id=item.get("id"),
                    text=item.get("text", ""),
                    entity_type=EntityType.PT,
                    raw_data=item,
                )
            )
        for item in data.get("prodi", []):
            result.program_studi.append(
                SearchHitItem(
                    id=item.get("id"),
                    text=item.get("text", ""),
                    entity_type=EntityType.PRODI,
                    raw_data=item,
                )
            )
        for item in data.get("dosen", []):
            result.dosen.append(
                SearchHitItem(
                    id=item.get("id"),
                    text=item.get("text", ""),
                    entity_type=EntityType.DOSEN,
                    raw_data=item,
                )
            )
        for item in data.get("mahasiswa", []):
            result.mahasiswa.append(
                SearchHitItem(
                    id=item.get("id"),
                    text=item.get("text", ""),
                    entity_type=EntityType.MAHASISWA,
                    raw_data=item,
                )
            )

        return result

    def get_detail_pt(self, id_pt: str) -> PerguruanTinggi:
        """Mengambil detail profil lengkap perguruan tinggi berdasarkan ID."""
        url = f"/v2/detail_pt/{id_pt}"
        try:
            resp = self._client.get(url)
            if resp.status_code == 404:
                raise ResourceNotFoundError(f"Perguruan tinggi dengan ID {id_pt} tidak ditemukan.")
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise APIConnectionError(f"HTTP error: {e}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise APIConnectionError(f"Koneksi gagal: {e}")

        # Parsing payload PDDikti
        pt_info = data.get("detail", data) if isinstance(data, dict) else {}
        nama = pt_info.get("nama_pt") or pt_info.get("nm_lemb", "Unknown PT")
        kode = pt_info.get("kode_pt") or pt_info.get("npsn", id_pt)

        pt = PerguruanTinggi(
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

        return pt

    def get_prodi_list(self, id_pt: str) -> List[ProgramStudi]:
        """Mengambil daftar seluruh program studi di sebuah perguruan tinggi."""
        url = f"/v2/detail_pt_prodi/{id_pt}"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

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


class AsyncPDDiktiService:
    """Implementasi asinkron untuk mengakses endpoint PDDikti."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def search_all(self, keyword: str) -> SearchResult:
        clean_keyword = keyword.strip()
        url = f"/hit/{clean_keyword}"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise APIConnectionError(f"HTTP error saat pencarian: {e}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise APIConnectionError(f"Gagal terhubung ke PDDikti: {e}")

        result = SearchResult(keyword=clean_keyword)
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
