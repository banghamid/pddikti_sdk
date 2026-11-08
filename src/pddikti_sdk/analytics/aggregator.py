"""Modul agregasi data untuk jurnalis data dan peneliti sosial."""

from typing import Any, Dict, List, Optional
from pddikti_sdk.models.perguruan_tinggi import PerguruanTinggi
from pddikti_sdk.models.sinta import SintaAuthor, SintaInstitution


class DataAggregator:
    """Helper agregasi data untuk keperluan analisis statistik & visualisasi."""

    @staticmethod
    def ringkas_sebaran_wilayah(daftar_pt: List[PerguruanTinggi]) -> Dict[str, Dict[str, Any]]:
        """Meringkas jumlah PT, total mahasiswa, dan dosen per provinsi/wilayah."""
        rekap: Dict[str, Dict[str, Any]] = {}
        for pt in daftar_pt:
            wilayah = pt.provinsi or pt.wilayah or "Lainnya"
            if wilayah not in rekap:
                rekap[wilayah] = {
                    "jumlah_pt": 0,
                    "total_mahasiswa": 0,
                    "total_dosen": 0,
                    "prodi_total": 0,
                }
            rekap[wilayah]["jumlah_pt"] += 1
            rekap[wilayah]["total_mahasiswa"] += pt.total_mahasiswa_aktif
            rekap[wilayah]["total_dosen"] += pt.total_dosen_tetap
            rekap[wilayah]["prodi_total"] += pt.total_prodi or len(pt.daftar_prodi)

        for w, val in rekap.items():
            val["rasio_rata_rata"] = (
                round(val["total_mahasiswa"] / val["total_dosen"], 2)
                if val["total_dosen"] > 0
                else 0.0
            )
        return rekap

    @staticmethod
    def ringkas_produktivitas_sinta(authors: List[SintaAuthor]) -> Dict[str, Any]:
        """Meringkas metrik produktivitas riset dari sekumpulan dosen/peneliti."""
        if not authors:
            return {"total_author": 0}

        total_scopus_docs = sum(a.scopus.documents for a in authors)
        total_scopus_cits = sum(a.scopus.citations for a in authors)
        total_scholar_cits = sum(a.scholar.citations for a in authors)
        total_patents = sum(a.ipr.patent for a in authors)
        total_score_3yr = sum(a.scores.three_years for a in authors)

        return {
            "total_author": len(authors),
            "total_scopus_documents": total_scopus_docs,
            "total_scopus_citations": total_scopus_cits,
            "total_scholar_citations": total_scholar_cits,
            "total_paten_terdaftar": total_patents,
            "rata_rata_skor_3tahun": round(total_score_3yr / len(authors), 2),
            "h_index_scopus_tertinggi": max(a.scopus.h_index for a in authors),
        }

    @staticmethod
    def to_dataframe(items: List[Any]):
        """Mengonversi daftar model pddikti_sdk ke Pandas DataFrame (jika library pandas tersedia)."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Library 'pandas' belum terpasang. Jalankan `pip install pandas` untuk menggunakan fitur ini."
            )

        dicts = [
            item.model_dump() if hasattr(item, "model_dump") else item.__dict__
            for item in items
        ]
        return pd.json_normalize(dicts)
