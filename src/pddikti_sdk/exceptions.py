"""Definisi hierarki exception untuk pddikti_sdk."""

from typing import Any, Optional


class PDDiktiError(Exception):
    """Base exception untuk semua kesalahan pddikti_sdk."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[Any] = None) -> None:
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)


class APIConnectionError(PDDiktiError):
    """Terjadi ketika gagal terhubung ke server/endpoint layanan."""
    pass


class ResourceNotFoundError(PDDiktiError):
    """Terjadi ketika entitas (PT, Prodi, Dosen, Mahasiswa, atau Author SINTA) tidak ditemukan."""
    pass


class RateLimitError(PDDiktiError):
    """Terjadi ketika kuota permintaan melebihi batas (HTTP 429)."""
    pass


class ValidationError(PDDiktiError):
    """Terjadi ketika payload atau data respon tidak valid sesuai skema."""
    pass
