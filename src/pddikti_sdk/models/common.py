"""Model umum dan struktur hasil pencarian agregat."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    PT = "perguruan_tinggi"
    PRODI = "program_studi"
    DOSEN = "dosen"
    MAHASISWA = "mahasiswa"


class SearchHitItem(BaseModel):
    """Item hasil pencarian global dari API PDDikti."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: Optional[str] = Field(None, alias="id")
    text: str = Field(..., alias="text")
    entity_type: Optional[EntityType] = None
    raw_data: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Koleksi hasil pencarian agregat multi-entitas."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    keyword: str
    perguruan_tinggi: List[SearchHitItem] = Field(default_factory=list)
    program_studi: List[SearchHitItem] = Field(default_factory=list)
    dosen: List[SearchHitItem] = Field(default_factory=list)
    mahasiswa: List[SearchHitItem] = Field(default_factory=list)

    @property
    def total_hits(self) -> int:
        return (
            len(self.perguruan_tinggi)
            + len(self.program_studi)
            + len(self.dosen)
            + len(self.mahasiswa)
        )
