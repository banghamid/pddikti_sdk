"""Model data SINTA (Science and Technology Index) Kemendikbudristek."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SintaScore(BaseModel):
    """Rincian skor SINTA seorang author atau institusi."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    overall: float = 0.0
    three_years: float = 0.0
    productivity_overall: float = 0.0
    productivity_three_years: float = 0.0


class ScopusMetrics(BaseModel):
    """Metrik sitasi dan publikasi terindeks Scopus."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    h_index: int = 0
    citations: int = 0
    documents: int = 0
    g_index: int = 0


class GoogleScholarMetrics(BaseModel):
    """Metrik sitasi dan publikasi Google Scholar."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    h_index: int = 0
    i10_index: int = 0
    citations: int = 0
    documents: int = 0


class GarudaMetrics(BaseModel):
    """Metrik publikasi terindeks di portal nasional GARUDA."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    documents: int = 0
    citations: int = 0


class WosMetrics(BaseModel):
    """Metrik publikasi Web of Science (Clarivate)."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    documents: int = 0
    citations: int = 0


class IprMetrics(BaseModel):
    """Kekayaan Intelektual (Paten dan Hak Cipta terdaftar)."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    patent: int = 0
    copyright: int = 0


class SintaAuthor(BaseModel):
    """Profil peneliti / dosen pada sistem SINTA."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    sinta_id: str = Field(..., alias="id")
    nama: str = Field(..., alias="fullname")
    nidn: Optional[str] = None
    afiliasi_pt: str = Field(..., alias="affiliation_name")
    afiliasi_prodi: Optional[str] = Field(None, alias="department_name")
    bidang_keahlian: List[str] = Field(default_factory=list)
    scores: SintaScore = Field(default_factory=SintaScore)
    scopus: ScopusMetrics = Field(default_factory=ScopusMetrics)
    scholar: GoogleScholarMetrics = Field(default_factory=GoogleScholarMetrics)
    garuda: GarudaMetrics = Field(default_factory=GarudaMetrics)
    wos: WosMetrics = Field(default_factory=WosMetrics)
    ipr: IprMetrics = Field(default_factory=IprMetrics)


class SintaInstitution(BaseModel):
    """Profil institusi dan peringkat agregat publikasi pada sistem SINTA."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    sinta_id: str
    kode_pt: Optional[str] = None
    nama: str
    singkatan: Optional[str] = None
    peringkat_nasional: Optional[int] = None
    peringkat_3th: Optional[int] = None
    score_overall: float = 0.0
    score_3th: float = 0.0
    jumlah_author: int = 0
    jumlah_departemen: int = 0
