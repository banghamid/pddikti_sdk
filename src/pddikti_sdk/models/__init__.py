"""Model data pddikti_sdk."""

from pddikti_sdk.models.common import EntityType, SearchHitItem, SearchResult
from pddikti_sdk.models.akreditasi import (
    AkreditasiInfo,
    LembagaAkreditasi,
    PeringkatAkreditasi,
)
from pddikti_sdk.models.perguruan_tinggi import (
    BentukPendidikan,
    BidangStudi,
    JenjangStudi,
    PerguruanTinggi,
    ProgramStudi,
    StatusPT,
)
from pddikti_sdk.models.sdm import (
    Dosen,
    JabatanFungsional,
    Mahasiswa,
    RiwayatPendidikan,
    StatusDosen,
    StatusMahasiswa,
)
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

__all__ = [
    "EntityType",
    "SearchHitItem",
    "SearchResult",
    "AkreditasiInfo",
    "LembagaAkreditasi",
    "PeringkatAkreditasi",
    "BentukPendidikan",
    "BidangStudi",
    "JenjangStudi",
    "PerguruanTinggi",
    "ProgramStudi",
    "StatusPT",
    "Dosen",
    "JabatanFungsional",
    "Mahasiswa",
    "RiwayatPendidikan",
    "StatusDosen",
    "StatusMahasiswa",
    "GarudaMetrics",
    "GoogleScholarMetrics",
    "IprMetrics",
    "ScopusMetrics",
    "SintaAuthor",
    "SintaInstitution",
    "SintaScore",
    "WosMetrics",
]
